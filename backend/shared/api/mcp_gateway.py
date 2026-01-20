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
from ..services.auth import get_current_user, get_current_user_with_tenant
from ..models.user import User
from ..logging.config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/mcp-servers", tags=["MCP Gateway"])
security = HTTPBearer()


@router.post("/", response_model=MCPServerResponse, status_code=status.HTTP_201_CREATED)
async def create_mcp_server(
    server_request: MCPServerRequest,
    current_user: User = Depends(get_current_user),
    mcp_service: MCPGatewayService = Depends(MCPGatewayService)
):
    """Create a new MCP server configuration."""
    try:
        server = await mcp_service.create_mcp_server(
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


@router.get("/", response_model=List[MCPServerResponse])
async def list_mcp_servers(
    status: Optional[MCPServerStatus] = Query(None, description="Filter by server status"),
    category: Optional[str] = Query(None, description="Filter by category"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of servers to return"),
    offset: int = Query(0, ge=0, description="Number of servers to skip"),
    current_user: User = Depends(get_current_user),
    mcp_service: MCPGatewayService = Depends(MCPGatewayService)
):
    """List MCP servers with optional filtering."""
    try:
        servers = await mcp_service.list_mcp_servers(
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


@router.get("/{server_id}", response_model=MCPServerResponse)
async def get_mcp_server(
    server_id: UUID,
    current_user: User = Depends(get_current_user),
    mcp_service: MCPGatewayService = Depends(MCPGatewayService)
):
    """Get an MCP server by ID."""
    try:
        server = await mcp_service.get_mcp_server(
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


@router.put("/{server_id}", response_model=MCPServerResponse)
async def update_mcp_server(
    server_id: UUID,
    server_request: MCPServerRequest,
    current_user: User = Depends(get_current_user),
    mcp_service: MCPGatewayService = Depends(MCPGatewayService)
):
    """Update an existing MCP server."""
    try:
        server = await mcp_service.update_mcp_server(
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


@router.delete("/{server_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mcp_server(
    server_id: UUID,
    current_user: User = Depends(get_current_user),
    mcp_service: MCPGatewayService = Depends(MCPGatewayService)
):
    """Delete an MCP server."""
    try:
        deleted = await mcp_service.delete_mcp_server(
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


@router.post("/{server_id}/connect")
async def connect_to_server(
    server_id: UUID,
    current_user: User = Depends(get_current_user),
    mcp_service: MCPGatewayService = Depends(MCPGatewayService)
):
    """Manually connect (introspect) to an MCP server."""
    try:
        # We use introspection as the "connect" action now
        server = await mcp_service.introspect_existing_server(
            user_id=current_user.id,
            server_id=server_id
        )
        
        logger.info(
            "MCP server connection/introspection successful",
            server_id=str(server_id),
            user_id=str(current_user.id)
        )
        
        return {
            "server_id": str(server.id),
            "server_name": server.name,
            "connection_status": "connected",
            "message": "Successfully connected and introspected server",
            "connected_at": server.last_connected_at.isoformat() if server.last_connected_at else None
        }
        
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
        # Return error status but as 200 so UI can show it gracefully? 
        # Or 500? Existing was 500.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to connect to MCP server: {str(e)}"
        )


@router.post("/{server_id}/introspect", response_model=MCPServerResponse)
async def introspect_server(
    server_id: UUID,
    current_user: User = Depends(get_current_user),
    mcp_service: MCPGatewayService = Depends(MCPGatewayService)
):
    """Trigger full introspection of an MCP server."""
    try:
        server = await mcp_service.introspect_existing_server(
            user_id=current_user.id,
            server_id=server_id
        )
        return server
    except Exception as e:
        logger.error(f"Failed to introspect server {server_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{server_id}/resources/read")
async def read_resource(
    server_id: UUID,
    uri: str = Query(..., description="URI of the resource to read"),
    current_user: User = Depends(get_current_user),
    mcp_service: MCPGatewayService = Depends(MCPGatewayService)
):
    """Read a specific resource from an MCP server."""
    try:
        # Get server first to check protocol/url
        server = await mcp_service.get_mcp_server(current_user.id, server_id)
        if not server:
            raise HTTPException(status_code=404, detail="Server not found")
            
        result = await mcp_service.mcp_client.read_resource(
            url=server.base_url,
            transport=server.protocol,
            uri=uri
        )
        return result
    except Exception as e:
        logger.error(f"Failed to read resource {uri}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{server_id}/prompts/{prompt_name}/get")
async def get_prompt(
    server_id: UUID,
    prompt_name: str,
    arguments: Dict[str, str] = {},
    current_user: User = Depends(get_current_user),
    mcp_service: MCPGatewayService = Depends(MCPGatewayService)
):
    """Get a prompt from an MCP server."""
    try:
        server = await mcp_service.get_mcp_server(current_user.id, server_id)
        if not server:
             raise HTTPException(status_code=404, detail="Server not found")
             
        result = await mcp_service.mcp_client.get_prompt(
            url=server.base_url,
            transport=server.protocol,
            name=prompt_name,
            args=arguments
        )
        return result
    except Exception as e:
        logger.error(f"Failed to get prompt {prompt_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
