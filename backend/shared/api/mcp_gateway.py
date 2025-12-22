"""
MCP Gateway API endpoints for the AI Agent Framework.

This module provides REST API endpoints for managing MCP server connections
and tool integrations.
"""

from typing import List, Optional, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPBearer

from ..models.tool import (
    MCPServerRequest, MCPServerResponse, MCPServerStatus
)
from ..services.mcp_gateway import MCPGatewayService
from ..services.auth import get_current_user_with_tenant
from ..models.user import User
from ..logging.config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/mcp", tags=["MCP Gateway"])
security = HTTPBearer()


@router.post("/servers/", response_model=MCPServerResponse, status_code=status.HTTP_201_CREATED)
async def create_mcp_server(
    server_request: MCPServerRequest,
    current_user: User = Depends(get_current_user_with_tenant),
    mcp_service: MCPGatewayService = Depends(MCPGatewayService)
):
    """Create a new MCP server configuration."""
    try:
        server = await mcp_service.create_mcp_server(
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            server_request=server_request
        )
        
        logger.info(
            "MCP server created via API",
            server_id=str(server.id),
            server_name=server.name,
            user_id=str(current_user.id)
        )
        
        return server
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            "Failed to create MCP server",
            error=str(e),
            user_id=str(current_user.id)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create MCP server"
        )


@router.get("/servers/", response_model=List[MCPServerResponse])
async def list_mcp_servers(
    status: Optional[MCPServerStatus] = Query(None, description="Filter by server status"),
    category: Optional[str] = Query(None, description="Filter by category"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of servers to return"),
    offset: int = Query(0, ge=0, description="Number of servers to skip"),
    current_user: User = Depends(get_current_user_with_tenant),
    mcp_service: MCPGatewayService = Depends(MCPGatewayService)
):
    """List MCP servers with optional filtering."""
    try:
        servers = await mcp_service.list_mcp_servers(
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            status=status,
            category=category,
            limit=limit,
            offset=offset
        )
        
        return servers
        
    except Exception as e:
        logger.error(
            "Failed to list MCP servers",
            error=str(e),
            user_id=str(current_user.id)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list MCP servers"
        )


@router.get("/servers/{server_id}", response_model=MCPServerResponse)
async def get_mcp_server(
    server_id: UUID,
    current_user: User = Depends(get_current_user_with_tenant),
    mcp_service: MCPGatewayService = Depends(MCPGatewayService)
):
    """Get an MCP server by ID."""
    try:
        server = await mcp_service.get_mcp_server(
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            server_id=server_id
        )
        
        if not server:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="MCP server not found"
            )
        
        return server
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to get MCP server",
            server_id=str(server_id),
            error=str(e),
            user_id=str(current_user.id)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get MCP server"
        )


@router.put("/servers/{server_id}", response_model=MCPServerResponse)
async def update_mcp_server(
    server_id: UUID,
    server_request: MCPServerRequest,
    current_user: User = Depends(get_current_user_with_tenant),
    mcp_service: MCPGatewayService = Depends(MCPGatewayService)
):
    """Update an existing MCP server."""
    try:
        server = await mcp_service.update_mcp_server(
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            server_id=server_id,
            server_request=server_request
        )
        
        logger.info(
            "MCP server updated via API",
            server_id=str(server_id),
            user_id=str(current_user.id)
        )
        
        return server
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            "Failed to update MCP server",
            server_id=str(server_id),
            error=str(e),
            user_id=str(current_user.id)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update MCP server"
        )


@router.delete("/servers/{server_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mcp_server(
    server_id: UUID,
    current_user: User = Depends(get_current_user_with_tenant),
    mcp_service: MCPGatewayService = Depends(MCPGatewayService)
):
    """Delete an MCP server."""
    try:
        deleted = await mcp_service.delete_mcp_server(
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            server_id=server_id
        )
        
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="MCP server not found"
            )
        
        logger.info(
            "MCP server deleted via API",
            server_id=str(server_id),
            user_id=str(current_user.id)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to delete MCP server",
            server_id=str(server_id),
            error=str(e),
            user_id=str(current_user.id)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete MCP server"
        )


@router.post("/servers/{server_id}/connect")
async def connect_to_server(
    server_id: UUID,
    current_user: User = Depends(get_current_user_with_tenant),
    mcp_service: MCPGatewayService = Depends(MCPGatewayService)
):
    """Manually connect to an MCP server."""
    try:
        connection_result = await mcp_service.connect_to_server(
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            server_id=server_id
        )
        
        logger.info(
            "MCP server connection attempted via API",
            server_id=str(server_id),
            status=connection_result["connection_status"],
            user_id=str(current_user.id)
        )
        
        return connection_result
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            "Failed to connect to MCP server",
            server_id=str(server_id),
            error=str(e),
            user_id=str(current_user.id)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to connect to MCP server"
        )


@router.get("/servers/{server_id}/discover")
async def discover_server_tools(
    server_id: UUID,
    force_refresh: bool = Query(False, description="Force refresh of tool discovery cache"),
    current_user: User = Depends(get_current_user_with_tenant),
    mcp_service: MCPGatewayService = Depends(MCPGatewayService)
):
    """Discover available tools on an MCP server."""
    try:
        discovery_result = await mcp_service.discover_tools(
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            server_id=server_id,
            force_refresh=force_refresh
        )
        
        logger.info(
            "MCP server tools discovered via API",
            server_id=str(server_id),
            tool_count=len(discovery_result.get("tools", [])),
            user_id=str(current_user.id)
        )
        
        return discovery_result
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            "Failed to discover MCP server tools",
            server_id=str(server_id),
            error=str(e),
            user_id=str(current_user.id)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to discover MCP server tools"
        )


@router.post("/servers/{server_id}/tools/{tool_name}/call")
async def call_mcp_tool(
    server_id: UUID,
    tool_name: str,
    inputs: Dict[str, Any],
    context: Optional[Dict[str, Any]] = None,
    current_user: User = Depends(get_current_user_with_tenant),
    mcp_service: MCPGatewayService = Depends(MCPGatewayService)
):
    """Call a tool on an MCP server."""
    try:
        call_result = await mcp_service.call_mcp_tool(
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            server_id=server_id,
            tool_name=tool_name,
            inputs=inputs,
            context=context
        )
        
        logger.info(
            "MCP tool called via API",
            server_id=str(server_id),
            tool_name=tool_name,
            status=call_result["status"],
            user_id=str(current_user.id)
        )
        
        return call_result
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            "Failed to call MCP tool",
            server_id=str(server_id),
            tool_name=tool_name,
            error=str(e),
            user_id=str(current_user.id)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to call MCP tool"
        )


@router.get("/servers/{server_id}/health")
async def check_server_health(
    server_id: UUID,
    current_user: User = Depends(get_current_user_with_tenant),
    mcp_service: MCPGatewayService = Depends(MCPGatewayService)
):
    """Check the health status of an MCP server."""
    try:
        server = await mcp_service.get_mcp_server(
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            server_id=server_id
        )
        
        if not server:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="MCP server not found"
            )
        
        health_status = {
            "server_id": str(server_id),
            "server_name": server.name,
            "status": server.status,
            "last_connected_at": server.last_connected_at.isoformat() if server.last_connected_at else None,
            "last_health_check_at": server.last_health_check_at.isoformat() if server.last_health_check_at else None,
            "error_count": server.error_count,
            "last_error": server.last_error,
            "success_rate": server.success_rate,
            "total_requests": server.total_requests,
            "successful_requests": server.successful_requests,
            "failed_requests": server.failed_requests,
            "average_response_time": server.average_response_time
        }
        
        return health_status
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to check MCP server health",
            server_id=str(server_id),
            error=str(e),
            user_id=str(current_user.id)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check MCP server health"
        )


@router.get("/protocols/")
async def get_supported_protocols():
    """Get list of supported MCP protocols."""
    return {
        "protocols": [
            {
                "name": "http",
                "description": "HTTP-based MCP communication",
                "default_port": 80,
                "secure": False
            },
            {
                "name": "https",
                "description": "HTTPS-based MCP communication",
                "default_port": 443,
                "secure": True
            },
            {
                "name": "ws",
                "description": "WebSocket-based MCP communication",
                "default_port": 80,
                "secure": False
            },
            {
                "name": "wss",
                "description": "Secure WebSocket-based MCP communication",
                "default_port": 443,
                "secure": True
            }
        ],
        "auth_types": [
            {
                "name": "none",
                "description": "No authentication required"
            },
            {
                "name": "basic",
                "description": "HTTP Basic authentication",
                "required_fields": ["username", "password"]
            },
            {
                "name": "bearer",
                "description": "Bearer token authentication",
                "required_fields": ["token"]
            },
            {
                "name": "api_key",
                "description": "API key authentication",
                "required_fields": ["api_key", "key_name"]
            },
            {
                "name": "oauth2",
                "description": "OAuth 2.0 authentication",
                "required_fields": ["client_id", "client_secret", "token_url"]
            }
        ]
    }