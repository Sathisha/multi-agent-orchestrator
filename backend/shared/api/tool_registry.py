"""
Tool Registry API endpoints for the AI Agent Framework.
"""

from typing import List, Optional, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_async_db
from ..models.tool import (
    ToolRequest, ToolResponse, ToolExecutionRequest, ToolExecutionResponse,
    ToolDiscoveryResponse, ToolType, ToolStatus
)
from ..services.tool_registry import ToolRegistryService
from ..services.auth import get_current_user
from ..models.user import User
from ..logging.config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/tools", tags=["Tool Registry"])
security = HTTPBearer()


def get_tool_registry_service(
    session: AsyncSession = Depends(get_async_db),
) -> ToolRegistryService:
    """Get ToolRegistryService with the current database session."""
    return ToolRegistryService(session)


@router.post("/", response_model=ToolResponse, status_code=status.HTTP_201_CREATED)
async def create_tool(
    tool_request: ToolRequest,
    current_user: User = Depends(get_current_user),
    tool_service: ToolRegistryService = Depends(get_tool_registry_service)
):
    """Create a new custom tool."""
    try:
        tool = await tool_service.create_tool(
            user_id=str(current_user.id),
            tool_request=tool_request
        )
        return tool
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create tool: {e}")
        raise HTTPException(status_code=500, detail="Failed to create tool")


@router.get("/", response_model=List[ToolResponse])
async def list_tools(
    tool_type: Optional[ToolType] = Query(None),
    status: Optional[ToolStatus] = Query(None),
    category: Optional[str] = Query(None),
    tags: Optional[List[str]] = Query(None),
    limit: int = 100,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    tool_service: ToolRegistryService = Depends(get_tool_registry_service)
):
    """List tools with optional filtering."""
    try:
        return await tool_service.list_tools(
            tool_type=tool_type,
            status=status,
            category=category,
            tags=tags,
            limit=limit,
            offset=offset
        )
    except Exception as e:
        logger.error(f"Failed to list tools: {e}")
        raise HTTPException(status_code=500, detail="Failed to list tools")


@router.get("/{tool_id}", response_model=ToolResponse)
async def get_tool(
    tool_id: UUID,
    current_user: User = Depends(get_current_user),
    tool_service: ToolRegistryService = Depends(get_tool_registry_service)
):
    """Get a tool by ID."""
    tool = await tool_service.get_tool(tool_id)
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")
    return tool


@router.put("/{tool_id}", response_model=ToolResponse)
async def update_tool(
    tool_id: UUID,
    tool_request: ToolRequest,
    current_user: User = Depends(get_current_user),
    tool_service: ToolRegistryService = Depends(get_tool_registry_service)
):
    """Update an existing tool."""
    try:
        return await tool_service.update_tool(
            user_id=str(current_user.id),
            tool_id=tool_id,
            tool_request=tool_request
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to update tool: {e}")
        raise HTTPException(status_code=500, detail="Failed to update tool")


@router.delete("/{tool_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tool(
    tool_id: UUID,
    current_user: User = Depends(get_current_user),
    tool_service: ToolRegistryService = Depends(get_tool_registry_service)
):
    """Delete a tool."""
    success = await tool_service.delete_tool(tool_id)
    if not success:
        raise HTTPException(status_code=404, detail="Tool not found")


@router.post("/{tool_id}/validate")
async def validate_tool(
    tool_id: UUID,
    current_user: User = Depends(get_current_user),
    tool_service: ToolRegistryService = Depends(get_tool_registry_service)
):
    """Validate a tool's code."""
    try:
        return await tool_service.validate_tool(tool_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{tool_id}/execute", response_model=ToolExecutionResponse)
async def execute_tool(
    tool_id: UUID,
    execution_request: ToolExecutionRequest,
    current_user: User = Depends(get_current_user),
    tool_service: ToolRegistryService = Depends(get_tool_registry_service)
):
    """Execute a tool."""
    try:
        return await tool_service.execute_tool(
            user_id=str(current_user.id),
            tool_id=tool_id,
            inputs=execution_request.inputs,
            context=execution_request.context,
            timeout_override=execution_request.timeout_override
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to execute tool: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/templates/", response_model=List[Dict[str, Any]])
async def get_tool_templates(
    current_user: User = Depends(get_current_user),
    tool_service: ToolRegistryService = Depends(get_tool_registry_service)
):
    return await tool_service.get_tool_templates()

@router.get("/discover/", response_model=ToolDiscoveryResponse)
async def discover_tools(
    include_mcp: bool = Query(True),
    current_user: User = Depends(get_current_user),
    tool_service: ToolRegistryService = Depends(get_tool_registry_service)
):
    return await tool_service.discover_tools(include_mcp=include_mcp)
