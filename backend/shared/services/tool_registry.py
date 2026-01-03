"""
Tool Registry Service for the AI Agent Framework.

This service manages custom tools and their lifecycle including validation,
registration, and execution.
"""

import asyncio
import json
import logging
import subprocess
import tempfile
import time
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from uuid import UUID, uuid4

from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..database import get_database_session
from ..models.tool import Tool, ToolType, ToolStatus, ToolRequest, ToolResponse
from ..models.audit import AuditLog, AuditEventType
from ..services.base import BaseService
from ..services.validation import ValidationService
# from ..services.rbac import RBACService # RBAC Disabled for single-tenant simplified
from ..logging.config import get_logger

logger = get_logger(__name__)


class ToolValidationError(Exception):
    """Exception raised when tool validation fails."""
    pass


class ToolExecutionError(Exception):
    """Exception raised when tool execution fails."""
    pass


class ToolRegistryService(BaseService):
    """Service for managing custom tools and tool registry."""
    
    def __init__(self, session: Optional[AsyncSession] = None):
        super().__init__(session, Tool)
        self.validation_service = ValidationService()
        self._execution_cache = {}
        self._validation_cache = {}
    
    async def create_tool(
        self,
        user_id: str,
        tool_request: ToolRequest
    ) -> ToolResponse:
        """Create a new custom tool."""
        
        async with get_database_session() as session:
            # Check if tool name already exists
            existing_tool = await session.execute(
                select(Tool).where(Tool.name == tool_request.name)
            )
            if existing_tool.scalar_one_or_none():
                raise ValueError(f"Tool with name '{tool_request.name}' already exists")
            
            # Create tool instance
            tool = Tool(
                id=uuid4(),
                created_by=UUID(user_id) if user_id else None,
                updated_by=UUID(user_id) if user_id else None,
                **tool_request.model_dump()
            )
            
            # Validate tool if code is provided
            if tool.code:
                validation_result = await self._validate_tool_code(tool)
                if not validation_result.is_valid:
                    tool.status = ToolStatus.ERROR
                    tool.validation_errors = validation_result.errors
                else:
                    tool.status = ToolStatus.DRAFT
                    tool.last_validated_at = datetime.utcnow()
            
            session.add(tool)
            await session.commit()
            await session.refresh(tool)
            
            logger.info(
                "Tool created successfully",
                tool_id=str(tool.id),
                tool_name=tool.name,
                user_id=str(user_id)
            )
            
            return ToolResponse.model_validate(tool)
    
    async def get_tool(
        self,
        tool_id: UUID
    ) -> Optional[ToolResponse]:
        """Get a tool by ID."""
        
        async with get_database_session() as session:
            result = await session.execute(
                select(Tool).where(Tool.id == tool_id)
            )
            tool = result.scalar_one_or_none()
            
            if not tool:
                return None
            
            return ToolResponse.model_validate(tool)
    
    async def list_tools(
        self,
        tool_type: Optional[ToolType] = None,
        status: Optional[ToolStatus] = None,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[ToolResponse]:
        """List tools with optional filtering."""
        
        async with get_database_session() as session:
            query = select(Tool)
            
            # Apply filters
            if tool_type:
                query = query.where(Tool.tool_type == tool_type)
            if status:
                query = query.where(Tool.status == status)
            if category:
                query = query.where(Tool.category == category)
            if tags:
                for tag in tags:
                    query = query.where(Tool.tags.contains([tag]))
            
            # Apply pagination
            query = query.offset(offset).limit(limit).order_by(Tool.created_at.desc())
            
            result = await session.execute(query)
            tools = result.scalars().all()
            
            return [ToolResponse.model_validate(tool) for tool in tools]
    
    async def update_tool(
        self,
        user_id: str,
        tool_id: UUID,
        tool_request: ToolRequest
    ) -> ToolResponse:
        """Update an existing tool."""
        
        async with get_database_session() as session:
            # Get existing tool
            result = await session.execute(select(Tool).where(Tool.id == tool_id))
            tool = result.scalar_one_or_none()
            
            if not tool:
                raise ValueError(f"Tool with ID {tool_id} not found")
            
            # Update tool fields
            update_data = tool_request.model_dump(exclude_unset=True)
            for field, value in update_data.items():
                if hasattr(tool, field):
                    setattr(tool, field, value)
            
            tool.updated_by = UUID(user_id) if user_id else None
            tool.updated_at = datetime.utcnow()
            
            # Re-validate if code changed
            if 'code' in update_data and tool.code:
                validation_result = await self._validate_tool_code(tool)
                if not validation_result.is_valid:
                    tool.status = ToolStatus.ERROR
                    tool.validation_errors = validation_result.errors
                else:
                    tool.status = ToolStatus.DRAFT
                    tool.last_validated_at = datetime.utcnow()
                    tool.validation_errors = []
            
            await session.commit()
            await session.refresh(tool)
            
            return ToolResponse.model_validate(tool)
    
    async def delete_tool(
        self,
        tool_id: UUID
    ) -> bool:
        """Delete a tool."""
        
        async with get_database_session() as session:
            result = await session.execute(select(Tool).where(Tool.id == tool_id))
            tool = result.scalar_one_or_none()
            
            if not tool:
                return False
            
            await session.delete(tool)
            await session.commit()
            
            return True
    
    async def validate_tool(
        self,
        tool_id: UUID
    ) -> Dict[str, Any]:
        """Validate a tool's code and configuration."""
        
        async with get_database_session() as session:
            result = await session.execute(select(Tool).where(Tool.id == tool_id))
            tool = result.scalar_one_or_none()
            
            if not tool:
                raise ValueError(f"Tool with ID {tool_id} not found")
            
            validation_result = await self._validate_tool_code(tool)
            
            tool.last_validated_at = datetime.utcnow()
            tool.validation_errors = validation_result.errors
            
            if validation_result.is_valid:
                if tool.status == ToolStatus.ERROR:
                    tool.status = ToolStatus.DRAFT
            else:
                tool.status = ToolStatus.ERROR
            
            await session.commit()
            
            return {
                "tool_id": str(tool_id),
                "is_valid": validation_result.is_valid,
                "errors": validation_result.errors,
                "validated_at": tool.last_validated_at.isoformat()
            }
    
    async def execute_tool(
        self,
        user_id: str,
        tool_id: UUID,
        inputs: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
        timeout_override: Optional[int] = None
    ) -> Dict[str, Any]:
        """Execute a tool with given inputs."""
        
        async with get_database_session() as session:
            result = await session.execute(select(Tool).where(Tool.id == tool_id))
            tool = result.scalar_one_or_none()
            
            if not tool:
                raise ValueError(f"Tool with ID {tool_id} not found")
            
            # Allow executing drafts for testing?
            # if tool.status != ToolStatus.ACTIVE:
            #     raise ToolExecutionError(f"Tool is not active (status: {tool.status})")
            
            execution_id = str(uuid4())
            start_time = time.time()
            
            try:
                if tool.input_schema:
                    await self.validation_service.validate_json_schema(inputs, tool.input_schema)
                
                if tool.tool_type == ToolType.CUSTOM:
                    outputs = await self._execute_custom_tool(tool, inputs, context, timeout_override)
                elif tool.tool_type == ToolType.MCP_SERVER:
                    outputs = await self._execute_mcp_tool(tool, inputs, context, timeout_override)
                else:
                    raise ToolExecutionError(f"Unsupported tool type: {tool.tool_type}")
                
                execution_time = int((time.time() - start_time) * 1000)
                
                tool.usage_count += 1
                tool.last_used_at = datetime.utcnow()
                
                if tool.average_execution_time:
                    tool.average_execution_time = int((tool.average_execution_time + execution_time) / 2)
                else:
                    tool.average_execution_time = execution_time
                
                await session.commit()
                
                return {
                    "tool_id": str(tool_id),
                    "execution_id": execution_id,
                    "status": "success",
                    "outputs": outputs,
                    "execution_time": execution_time,
                    "started_at": datetime.fromtimestamp(start_time).isoformat(),
                    "completed_at": datetime.utcnow().isoformat()
                }
                
            except Exception as e:
                execution_time = int((time.time() - start_time) * 1000)
                return {
                    "tool_id": str(tool_id),
                    "execution_id": execution_id,
                    "status": "error",
                    "error": str(e),
                    "execution_time": execution_time,
                    "started_at": datetime.fromtimestamp(start_time).isoformat(),
                    "completed_at": datetime.utcnow().isoformat()
                }
    
    async def get_tool_templates(self) -> List[Dict[str, Any]]:
        """Get available tool templates for development."""
        return [
            {
                "name": "weather_template",
                "display_name": "Weather Checker Template",
                "description": "API-based weather lookup template using Open-Meteo",
                "code": "def execute(inputs, context=None):\n    import httpx\n    location = inputs.get('location', 'London')\n    geo_url = f\"https://geocoding-api.open-meteo.com/v1/search?name={location}&count=1&language=en&format=json\"\n    with httpx.Client(timeout=10.0) as client:\n        geo_res = client.get(geo_url)\n        if geo_res.status_code != 200 or not geo_res.json().get('results'):\n            return {\"error\": f\"Could not find location: {location}\"}\n        res = geo_res.json()['results'][0]\n        lat, lon = res['latitude'], res['longitude']\n        w_url = f\"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true\"\n        w_res = client.get(w_url)\n        if w_res.status_code != 200: return {\"error\": \"Weather service unavailable\"}\n        w_data = w_res.json()['current_weather']\n        return {\n            \"location\": res['name'],\n            \"temperature\": w_data['temperature'],\n            \"condition_code\": w_data['weathercode']\n        }",
                "input_schema": {
                    "type": "object",
                    "properties": {"location": {"type": "string"}},
                    "required": ["location"]
                }
            },
            {
                "name": "wikipedia_template",
                "display_name": "Wikipedia Search Template",
                "description": "API-based Wikipedia lookup template",
                "code": "def execute(inputs, context=None):\n    import httpx\n    query = inputs.get('query')\n    url = f\"https://en.wikipedia.org/api/rest_v1/page/summary/{query.replace(' ', '_')}\"\n    with httpx.Client(timeout=10.0) as client:\n        res = client.get(url)\n        if res.status_code != 200: return {\"error\": \"Wikipedia service error\"}\n        data = res.json()\n        return {\n            \"title\": data.get('title'),\n            \"summary\": data.get('extract')\n        }",
                "input_schema": {
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"]
                }
            }
        ]
    
    async def discover_tools(
        self,
        include_mcp: bool = True
    ) -> Dict[str, Any]:
        """Discover available tools and capabilities."""
        
        async with get_database_session() as session:
            tools_query = select(Tool).where(Tool.status == ToolStatus.ACTIVE)
            
            if not include_mcp:
                tools_query = tools_query.where(Tool.tool_type != ToolType.MCP_SERVER)
            
            result = await session.execute(tools_query)
            tools = result.scalars().all()
            
            categories = set()
            capabilities = set()
            
            for tool in tools:
                if tool.category:
                    categories.add(tool.category)
                if tool.capabilities:
                    capabilities.update(tool.capabilities)
            
            return {
                "available_tools": [ToolResponse.model_validate(tool) for tool in tools],
                "categories": sorted(list(categories)),
                "capabilities": sorted(list(capabilities)),
                "total_count": len(tools)
            }

    async def _validate_tool_code(self, tool: Tool) -> 'ValidationResult':
        if not tool.code:
            return ValidationResult(is_valid=False, errors=["Tool code is required"])
        
        errors = []
        try:
            compile(tool.code, f"<tool_{tool.name}>", "exec")
            if "def execute(" not in tool.code:
                errors.append("Tool must define an 'execute' function")
        except SyntaxError as e:
            errors.append(f"Syntax error: {str(e)}")
        except Exception as e:
            errors.append(f"Validation error: {str(e)}")
        
        return ValidationResult(is_valid=len(errors) == 0, errors=errors)

    async def _execute_custom_tool(self, tool, inputs, context, timeout_override):
        # Simply mocked execution as unsafe subprocess execution needs more care in refactor
        # But keeping structure:
        if not tool.code: return {"error": "No code"}
        # For simplicity in this environment, we might skip actual execution or keep it minimal
        # The original used subprocess, which is fine if environment allows python.
        
        # Creating temp file...
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(tool.code)
            temp_file = f.name
        
        execution_script = f'''
import json
import sys
import importlib.util
from datetime import datetime

# Mock context
sys.path.insert(0, '.')

try:
    spec = importlib.util.spec_from_file_location("tool_module", r"{temp_file}")
    tool_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tool_module)
    
    inputs = {json.dumps(inputs)}
    context = {json.dumps(context or {})}
    
    result = tool_module.execute(inputs, context)
    print(json.dumps({{"status": "success", "result": result}}))
except Exception as e:
    print(json.dumps({{"status": "error", "error": str(e)}}))
'''
        # We need to run this command.
        # Check if python is available in container. It is.
        proc = await asyncio.create_subprocess_exec(
            'python', '-c', execution_script,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        
        import os
        try: os.unlink(temp_file)
        except: pass

        if proc.returncode != 0:
            raise ToolExecutionError(f"Execution failed: {stderr.decode()}")
        
        try:
            res = json.loads(stdout.decode())
            if res['status'] == 'error':
                 raise ToolExecutionError(res['error'])
            return res['result']
        except json.JSONDecodeError:
             raise ToolExecutionError(f"Invalid output: {stdout.decode()}")

    async def _execute_mcp_tool(self, tool, inputs, context, timeout):
        return {"status": "not_implemented"}

class ValidationResult:
    def __init__(self, is_valid: bool, errors: List[str]):
        self.is_valid = is_valid
        self.errors = errors