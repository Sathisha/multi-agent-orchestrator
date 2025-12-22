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
from ..services.rbac import RBACService
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
    
    def __init__(self):
        super().__init__()
        self.validation_service = ValidationService()
        self.rbac_service = RBACService()
        self._execution_cache = {}
        self._validation_cache = {}
    
    async def create_tool(
        self,
        tenant_id: UUID,
        user_id: UUID,
        tool_request: ToolRequest
    ) -> ToolResponse:
        """Create a new custom tool."""
        
        # Check permissions
        await self.rbac_service.check_permission(
            user_id=user_id,
            resource="tool",
            action="create",
            tenant_id=tenant_id
        )
        
        async with get_database_session() as session:
            # Check if tool name already exists for this tenant
            existing_tool = await session.execute(
                select(Tool).where(
                    and_(
                        Tool.tenant_id == tenant_id,
                        Tool.name == tool_request.name
                    )
                )
            )
            if existing_tool.scalar_one_or_none():
                raise ValueError(f"Tool with name '{tool_request.name}' already exists")
            
            # Create tool instance
            tool = Tool(
                id=uuid4(),
                tenant_id=tenant_id,
                created_by=user_id,
                updated_by=user_id,
                **tool_request.model_dump(exclude={'tenant_id'})
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
            
            # Log audit event
            await self._log_audit_event(
                session=session,
                event_type=AuditEventType.TOOL_CREATED,
                user_id=user_id,
                tenant_id=tenant_id,
                resource_id=str(tool.id),
                details={
                    "tool_name": tool.name,
                    "tool_type": tool.tool_type,
                    "status": tool.status
                }
            )
            
            logger.info(
                "Tool created successfully",
                tool_id=str(tool.id),
                tool_name=tool.name,
                tenant_id=str(tenant_id),
                user_id=str(user_id)
            )
            
            return ToolResponse.model_validate(tool)
    
    async def get_tool(
        self,
        tenant_id: UUID,
        user_id: UUID,
        tool_id: UUID
    ) -> Optional[ToolResponse]:
        """Get a tool by ID."""
        
        # Check permissions
        await self.rbac_service.check_permission(
            user_id=user_id,
            resource="tool",
            action="read",
            tenant_id=tenant_id
        )
        
        async with get_database_session() as session:
            result = await session.execute(
                select(Tool)
                .options(selectinload(Tool.mcp_server))
                .where(
                    and_(
                        Tool.id == tool_id,
                        Tool.tenant_id == tenant_id
                    )
                )
            )
            tool = result.scalar_one_or_none()
            
            if not tool:
                return None
            
            return ToolResponse.model_validate(tool)
    
    async def list_tools(
        self,
        tenant_id: UUID,
        user_id: UUID,
        tool_type: Optional[ToolType] = None,
        status: Optional[ToolStatus] = None,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[ToolResponse]:
        """List tools with optional filtering."""
        
        # Check permissions
        await self.rbac_service.check_permission(
            user_id=user_id,
            resource="tool",
            action="read",
            tenant_id=tenant_id
        )
        
        async with get_database_session() as session:
            query = select(Tool).where(Tool.tenant_id == tenant_id)
            
            # Apply filters
            if tool_type:
                query = query.where(Tool.tool_type == tool_type)
            if status:
                query = query.where(Tool.status == status)
            if category:
                query = query.where(Tool.category == category)
            if tags:
                # Filter by tags using JSONB contains
                for tag in tags:
                    query = query.where(Tool.tags.contains([tag]))
            
            # Apply pagination
            query = query.offset(offset).limit(limit).order_by(Tool.created_at.desc())
            
            result = await session.execute(query)
            tools = result.scalars().all()
            
            return [ToolResponse.model_validate(tool) for tool in tools]
    
    async def update_tool(
        self,
        tenant_id: UUID,
        user_id: UUID,
        tool_id: UUID,
        tool_request: ToolRequest
    ) -> ToolResponse:
        """Update an existing tool."""
        
        # Check permissions
        await self.rbac_service.check_permission(
            user_id=user_id,
            resource="tool",
            action="update",
            tenant_id=tenant_id
        )
        
        async with get_database_session() as session:
            # Get existing tool
            result = await session.execute(
                select(Tool).where(
                    and_(
                        Tool.id == tool_id,
                        Tool.tenant_id == tenant_id
                    )
                )
            )
            tool = result.scalar_one_or_none()
            
            if not tool:
                raise ValueError(f"Tool with ID {tool_id} not found")
            
            # Store old values for audit
            old_values = {
                "name": tool.name,
                "version": tool.version,
                "status": tool.status
            }
            
            # Update tool fields
            update_data = tool_request.model_dump(exclude_unset=True)
            for field, value in update_data.items():
                if hasattr(tool, field):
                    setattr(tool, field, value)
            
            tool.updated_by = user_id
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
            
            # Log audit event
            await self._log_audit_event(
                session=session,
                event_type=AuditEventType.TOOL_UPDATED,
                user_id=user_id,
                tenant_id=tenant_id,
                resource_id=str(tool.id),
                details={
                    "tool_name": tool.name,
                    "old_values": old_values,
                    "new_values": {
                        "name": tool.name,
                        "version": tool.version,
                        "status": tool.status
                    }
                }
            )
            
            logger.info(
                "Tool updated successfully",
                tool_id=str(tool.id),
                tool_name=tool.name,
                tenant_id=str(tenant_id),
                user_id=str(user_id)
            )
            
            return ToolResponse.model_validate(tool)
    
    async def delete_tool(
        self,
        tenant_id: UUID,
        user_id: UUID,
        tool_id: UUID
    ) -> bool:
        """Delete a tool."""
        
        # Check permissions
        await self.rbac_service.check_permission(
            user_id=user_id,
            resource="tool",
            action="delete",
            tenant_id=tenant_id
        )
        
        async with get_database_session() as session:
            # Get existing tool
            result = await session.execute(
                select(Tool).where(
                    and_(
                        Tool.id == tool_id,
                        Tool.tenant_id == tenant_id
                    )
                )
            )
            tool = result.scalar_one_or_none()
            
            if not tool:
                return False
            
            # Store tool info for audit
            tool_info = {
                "tool_name": tool.name,
                "tool_type": tool.tool_type,
                "version": tool.version
            }
            
            await session.delete(tool)
            await session.commit()
            
            # Log audit event
            await self._log_audit_event(
                session=session,
                event_type=AuditEventType.TOOL_DELETED,
                user_id=user_id,
                tenant_id=tenant_id,
                resource_id=str(tool_id),
                details=tool_info
            )
            
            logger.info(
                "Tool deleted successfully",
                tool_id=str(tool_id),
                tenant_id=str(tenant_id),
                user_id=str(user_id)
            )
            
            return True
    
    async def validate_tool(
        self,
        tenant_id: UUID,
        user_id: UUID,
        tool_id: UUID
    ) -> Dict[str, Any]:
        """Validate a tool's code and configuration."""
        
        # Check permissions
        await self.rbac_service.check_permission(
            user_id=user_id,
            resource="tool",
            action="update",
            tenant_id=tenant_id
        )
        
        async with get_database_session() as session:
            # Get tool
            result = await session.execute(
                select(Tool).where(
                    and_(
                        Tool.id == tool_id,
                        Tool.tenant_id == tenant_id
                    )
                )
            )
            tool = result.scalar_one_or_none()
            
            if not tool:
                raise ValueError(f"Tool with ID {tool_id} not found")
            
            # Validate tool
            validation_result = await self._validate_tool_code(tool)
            
            # Update tool validation status
            tool.last_validated_at = datetime.utcnow()
            tool.validation_errors = validation_result.errors
            
            if validation_result.is_valid:
                if tool.status == ToolStatus.ERROR:
                    tool.status = ToolStatus.DRAFT
            else:
                tool.status = ToolStatus.ERROR
            
            await session.commit()
            
            logger.info(
                "Tool validation completed",
                tool_id=str(tool_id),
                is_valid=validation_result.is_valid,
                error_count=len(validation_result.errors)
            )
            
            return {
                "tool_id": str(tool_id),
                "is_valid": validation_result.is_valid,
                "errors": validation_result.errors,
                "validated_at": tool.last_validated_at.isoformat()
            }
    
    async def execute_tool(
        self,
        tenant_id: UUID,
        user_id: UUID,
        tool_id: UUID,
        inputs: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
        timeout_override: Optional[int] = None
    ) -> Dict[str, Any]:
        """Execute a tool with given inputs."""
        
        # Check permissions
        await self.rbac_service.check_permission(
            user_id=user_id,
            resource="tool",
            action="execute",
            tenant_id=tenant_id
        )
        
        async with get_database_session() as session:
            # Get tool
            result = await session.execute(
                select(Tool).where(
                    and_(
                        Tool.id == tool_id,
                        Tool.tenant_id == tenant_id
                    )
                )
            )
            tool = result.scalar_one_or_none()
            
            if not tool:
                raise ValueError(f"Tool with ID {tool_id} not found")
            
            if tool.status != ToolStatus.ACTIVE:
                raise ToolExecutionError(f"Tool is not active (status: {tool.status})")
            
            # Execute tool
            execution_id = str(uuid4())
            start_time = time.time()
            
            try:
                # Validate inputs against schema
                if tool.input_schema:
                    await self.validation_service.validate_json_schema(inputs, tool.input_schema)
                
                # Execute tool based on type
                if tool.tool_type == ToolType.CUSTOM:
                    outputs = await self._execute_custom_tool(tool, inputs, context, timeout_override)
                elif tool.tool_type == ToolType.MCP_SERVER:
                    outputs = await self._execute_mcp_tool(tool, inputs, context, timeout_override)
                else:
                    raise ToolExecutionError(f"Unsupported tool type: {tool.tool_type}")
                
                execution_time = int((time.time() - start_time) * 1000)  # milliseconds
                
                # Update usage statistics
                tool.usage_count += 1
                tool.last_used_at = datetime.utcnow()
                
                # Update average execution time
                if tool.average_execution_time:
                    tool.average_execution_time = int(
                        (tool.average_execution_time + execution_time) / 2
                    )
                else:
                    tool.average_execution_time = execution_time
                
                await session.commit()
                
                # Log audit event
                await self._log_audit_event(
                    session=session,
                    event_type=AuditEventType.TOOL_EXECUTED,
                    user_id=user_id,
                    tenant_id=tenant_id,
                    resource_id=str(tool.id),
                    details={
                        "tool_name": tool.name,
                        "execution_id": execution_id,
                        "execution_time_ms": execution_time,
                        "inputs": inputs,
                        "outputs": outputs
                    }
                )
                
                logger.info(
                    "Tool executed successfully",
                    tool_id=str(tool_id),
                    execution_id=execution_id,
                    execution_time_ms=execution_time
                )
                
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
                
                logger.error(
                    "Tool execution failed",
                    tool_id=str(tool_id),
                    execution_id=execution_id,
                    error=str(e),
                    execution_time_ms=execution_time
                )
                
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
        
        templates = [
            {
                "name": "simple_function",
                "display_name": "Simple Function Tool",
                "description": "A basic function-based tool template",
                "code": '''def execute(inputs, context=None):
    """
    Simple tool execution function.
    
    Args:
        inputs (dict): Tool inputs
        context (dict): Execution context
        
    Returns:
        dict: Tool outputs
    """
    # Your tool logic here
    result = inputs.get("input_value", "")
    
    return {
        "output_value": f"Processed: {result}",
        "status": "success"
    }''',
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "input_value": {
                            "type": "string",
                            "description": "Input value to process"
                        }
                    },
                    "required": ["input_value"]
                },
                "output_schema": {
                    "type": "object",
                    "properties": {
                        "output_value": {
                            "type": "string",
                            "description": "Processed output value"
                        },
                        "status": {
                            "type": "string",
                            "description": "Execution status"
                        }
                    }
                }
            },
            {
                "name": "data_processor",
                "display_name": "Data Processing Tool",
                "description": "Template for data processing tools",
                "code": '''import json
from typing import Dict, Any, List

def execute(inputs: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Data processing tool.
    
    Args:
        inputs: Tool inputs containing data to process
        context: Execution context
        
    Returns:
        dict: Processed data results
    """
    data = inputs.get("data", [])
    operation = inputs.get("operation", "count")
    
    if operation == "count":
        result = len(data)
    elif operation == "sum" and all(isinstance(x, (int, float)) for x in data):
        result = sum(data)
    elif operation == "filter":
        filter_value = inputs.get("filter_value")
        result = [item for item in data if item != filter_value]
    else:
        raise ValueError(f"Unsupported operation: {operation}")
    
    return {
        "result": result,
        "operation": operation,
        "input_count": len(data)
    }''',
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "data": {
                            "type": "array",
                            "description": "Data to process"
                        },
                        "operation": {
                            "type": "string",
                            "enum": ["count", "sum", "filter"],
                            "description": "Operation to perform"
                        },
                        "filter_value": {
                            "description": "Value to filter out (for filter operation)"
                        }
                    },
                    "required": ["data", "operation"]
                },
                "output_schema": {
                    "type": "object",
                    "properties": {
                        "result": {
                            "description": "Processing result"
                        },
                        "operation": {
                            "type": "string",
                            "description": "Operation performed"
                        },
                        "input_count": {
                            "type": "integer",
                            "description": "Number of input items"
                        }
                    }
                }
            }
        ]
        
        return templates
    
    async def discover_tools(
        self,
        tenant_id: UUID,
        user_id: UUID,
        include_mcp: bool = True
    ) -> Dict[str, Any]:
        """Discover available tools and capabilities."""
        
        # Check permissions
        await self.rbac_service.check_permission(
            user_id=user_id,
            resource="tool",
            action="read",
            tenant_id=tenant_id
        )
        
        async with get_database_session() as session:
            # Get all active tools
            tools_query = select(Tool).where(
                and_(
                    Tool.tenant_id == tenant_id,
                    Tool.status == ToolStatus.ACTIVE
                )
            )
            
            if not include_mcp:
                tools_query = tools_query.where(Tool.tool_type != ToolType.MCP_SERVER)
            
            result = await session.execute(tools_query)
            tools = result.scalars().all()
            
            # Get unique categories and capabilities
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
        """Validate tool code for syntax and basic requirements."""
        
        if not tool.code:
            return ValidationResult(is_valid=False, errors=["Tool code is required"])
        
        errors = []
        
        try:
            # Check Python syntax
            compile(tool.code, f"<tool_{tool.name}>", "exec")
            
            # Check for required execute function
            if "def execute(" not in tool.code:
                errors.append("Tool must define an 'execute' function")
            
            # Check for proper imports (basic validation)
            lines = tool.code.split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith('import ') or line.startswith('from '):
                    # Check for potentially dangerous imports
                    dangerous_modules = ['os', 'subprocess', 'sys', '__import__']
                    for module in dangerous_modules:
                        if module in line:
                            errors.append(f"Potentially dangerous import detected: {module}")
            
        except SyntaxError as e:
            errors.append(f"Syntax error: {str(e)}")
        except Exception as e:
            errors.append(f"Validation error: {str(e)}")
        
        return ValidationResult(is_valid=len(errors) == 0, errors=errors)
    
    async def _execute_custom_tool(
        self,
        tool: Tool,
        inputs: Dict[str, Any],
        context: Optional[Dict[str, Any]],
        timeout_override: Optional[int]
    ) -> Dict[str, Any]:
        """Execute a custom Python tool."""
        
        if not tool.code or not tool.entry_point:
            raise ToolExecutionError("Tool code or entry point not defined")
        
        # Create a temporary file with the tool code
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(tool.code)
            temp_file = f.name
        
        try:
            # Create execution script
            execution_script = f'''
import json
import sys
sys.path.insert(0, '.')

# Import the tool module
import importlib.util
spec = importlib.util.spec_from_file_location("tool_module", "{temp_file}")
tool_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool_module)

# Execute the tool
inputs = {json.dumps(inputs)}
context = {json.dumps(context or {})}

try:
    result = tool_module.execute(inputs, context)
    print(json.dumps({{"status": "success", "result": result}}))
except Exception as e:
    print(json.dumps({{"status": "error", "error": str(e)}}))
'''
            
            # Execute with timeout
            timeout = timeout_override or tool.timeout_seconds
            
            process = await asyncio.create_subprocess_exec(
                'python', '-c', execution_script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
                
                if process.returncode != 0:
                    raise ToolExecutionError(f"Tool execution failed: {stderr.decode()}")
                
                # Parse result
                result_data = json.loads(stdout.decode())
                
                if result_data["status"] == "error":
                    raise ToolExecutionError(result_data["error"])
                
                return result_data["result"]
                
            except asyncio.TimeoutError:
                process.kill()
                raise ToolExecutionError(f"Tool execution timed out after {timeout} seconds")
                
        finally:
            # Clean up temporary file
            import os
            try:
                os.unlink(temp_file)
            except:
                pass
    
    async def _execute_mcp_tool(
        self,
        tool: Tool,
        inputs: Dict[str, Any],
        context: Optional[Dict[str, Any]],
        timeout_override: Optional[int]
    ) -> Dict[str, Any]:
        """Execute a tool via MCP server."""
        
        if not tool.mcp_server_id or not tool.mcp_tool_name:
            raise ToolExecutionError("MCP server or tool name not configured")
        
        # This will be implemented when we create the MCP gateway service
        # For now, return a placeholder
        return {
            "message": "MCP tool execution not yet implemented",
            "tool_name": tool.mcp_tool_name,
            "inputs": inputs
        }


class ValidationResult:
    """Tool validation result."""
    
    def __init__(self, is_valid: bool, errors: List[str]):
        self.is_valid = is_valid
        self.errors = errors