"""
Tool Registry API endpoints for the AI Agent Framework.

This module provides REST API endpoints for managing custom tools and tool registry.
"""

from typing import List, Optional, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPBearer

from ..models.tool import (
    ToolRequest, ToolResponse, ToolExecutionRequest, ToolExecutionResponse,
    ToolDiscoveryResponse, ToolType, ToolStatus
)
from ..services.tool_registry import ToolRegistryService
from ..services.auth import get_current_user_with_tenant
from ..models.user import User
from ..logging.config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/tools", tags=["Tool Registry"])
security = HTTPBearer()


@router.post("/", response_model=ToolResponse, status_code=status.HTTP_201_CREATED)
async def create_tool(
    tool_request: ToolRequest,
    current_user: User = Depends(get_current_user_with_tenant),
    tool_service: ToolRegistryService = Depends(ToolRegistryService)
):
    """Create a new custom tool."""
    try:
        tool = await tool_service.create_tool(
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            tool_request=tool_request
        )
        
        logger.info(
            "Tool created via API",
            tool_id=str(tool.id),
            tool_name=tool.name,
            user_id=str(current_user.id)
        )
        
        return tool
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            "Failed to create tool",
            error=str(e),
            user_id=str(current_user.id)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create tool"
        )


@router.get("/", response_model=List[ToolResponse])
async def list_tools(
    tool_type: Optional[ToolType] = Query(None, description="Filter by tool type"),
    status: Optional[ToolStatus] = Query(None, description="Filter by tool status"),
    category: Optional[str] = Query(None, description="Filter by category"),
    tags: Optional[List[str]] = Query(None, description="Filter by tags"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of tools to return"),
    offset: int = Query(0, ge=0, description="Number of tools to skip"),
    current_user: User = Depends(get_current_user_with_tenant),
    tool_service: ToolRegistryService = Depends(ToolRegistryService)
):
    """List tools with optional filtering."""
    try:
        tools = await tool_service.list_tools(
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            tool_type=tool_type,
            status=status,
            category=category,
            tags=tags,
            limit=limit,
            offset=offset
        )
        
        return tools
        
    except Exception as e:
        logger.error(
            "Failed to list tools",
            error=str(e),
            user_id=str(current_user.id)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list tools"
        )


@router.get("/{tool_id}", response_model=ToolResponse)
async def get_tool(
    tool_id: UUID,
    current_user: User = Depends(get_current_user_with_tenant),
    tool_service: ToolRegistryService = Depends(ToolRegistryService)
):
    """Get a tool by ID."""
    try:
        tool = await tool_service.get_tool(
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            tool_id=tool_id
        )
        
        if not tool:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tool not found"
            )
        
        return tool
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to get tool",
            tool_id=str(tool_id),
            error=str(e),
            user_id=str(current_user.id)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get tool"
        )


@router.put("/{tool_id}", response_model=ToolResponse)
async def update_tool(
    tool_id: UUID,
    tool_request: ToolRequest,
    current_user: User = Depends(get_current_user_with_tenant),
    tool_service: ToolRegistryService = Depends(ToolRegistryService)
):
    """Update an existing tool."""
    try:
        tool = await tool_service.update_tool(
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            tool_id=tool_id,
            tool_request=tool_request
        )
        
        logger.info(
            "Tool updated via API",
            tool_id=str(tool_id),
            user_id=str(current_user.id)
        )
        
        return tool
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            "Failed to update tool",
            tool_id=str(tool_id),
            error=str(e),
            user_id=str(current_user.id)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update tool"
        )


@router.delete("/{tool_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tool(
    tool_id: UUID,
    current_user: User = Depends(get_current_user_with_tenant),
    tool_service: ToolRegistryService = Depends(ToolRegistryService)
):
    """Delete a tool."""
    try:
        deleted = await tool_service.delete_tool(
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            tool_id=tool_id
        )
        
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tool not found"
            )
        
        logger.info(
            "Tool deleted via API",
            tool_id=str(tool_id),
            user_id=str(current_user.id)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to delete tool",
            tool_id=str(tool_id),
            error=str(e),
            user_id=str(current_user.id)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete tool"
        )


@router.post("/{tool_id}/validate")
async def validate_tool(
    tool_id: UUID,
    current_user: User = Depends(get_current_user_with_tenant),
    tool_service: ToolRegistryService = Depends(ToolRegistryService)
):
    """Validate a tool's code and configuration."""
    try:
        validation_result = await tool_service.validate_tool(
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            tool_id=tool_id
        )
        
        logger.info(
            "Tool validated via API",
            tool_id=str(tool_id),
            is_valid=validation_result["is_valid"],
            user_id=str(current_user.id)
        )
        
        return validation_result
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            "Failed to validate tool",
            tool_id=str(tool_id),
            error=str(e),
            user_id=str(current_user.id)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to validate tool"
        )


@router.post("/{tool_id}/execute", response_model=ToolExecutionResponse)
async def execute_tool(
    tool_id: UUID,
    execution_request: ToolExecutionRequest,
    current_user: User = Depends(get_current_user_with_tenant),
    tool_service: ToolRegistryService = Depends(ToolRegistryService)
):
    """Execute a tool with given inputs."""
    try:
        execution_result = await tool_service.execute_tool(
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            tool_id=execution_request.tool_id,
            inputs=execution_request.inputs,
            context=execution_request.context,
            timeout_override=execution_request.timeout_override
        )
        
        logger.info(
            "Tool executed via API",
            tool_id=str(tool_id),
            execution_id=execution_result["execution_id"],
            status=execution_result["status"],
            user_id=str(current_user.id)
        )
        
        return ToolExecutionResponse(**execution_result)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            "Failed to execute tool",
            tool_id=str(tool_id),
            error=str(e),
            user_id=str(current_user.id)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to execute tool"
        )


@router.get("/templates/", response_model=List[Dict[str, Any]])
async def get_tool_templates(
    current_user: User = Depends(get_current_user_with_tenant),
    tool_service: ToolRegistryService = Depends(ToolRegistryService)
):
    """Get available tool templates for development."""
    try:
        templates = await tool_service.get_tool_templates()
        
        return templates
        
    except Exception as e:
        logger.error(
            "Failed to get tool templates",
            error=str(e),
            user_id=str(current_user.id)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get tool templates"
        )


@router.get("/discover/", response_model=ToolDiscoveryResponse)
async def discover_tools(
    include_mcp: bool = Query(True, description="Include MCP server tools"),
    current_user: User = Depends(get_current_user_with_tenant),
    tool_service: ToolRegistryService = Depends(ToolRegistryService)
):
    """Discover available tools and capabilities."""
    try:
        discovery_result = await tool_service.discover_tools(
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            include_mcp=include_mcp
        )
        
        return ToolDiscoveryResponse(
            available_tools=discovery_result["available_tools"],
            categories=discovery_result["categories"],
            capabilities=discovery_result["capabilities"]
        )
        
    except Exception as e:
        logger.error(
            "Failed to discover tools",
            error=str(e),
            user_id=str(current_user.id)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to discover tools"
        )