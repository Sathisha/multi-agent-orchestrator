"""
MCP Bridge Discovery API - Dynamically discover available MCP servers from the bridge.
"""

from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException
import httpx
import os

router = APIRouter(prefix="/mcp-bridge", tags=["MCP Bridge Discovery"])

# Get bridge URL from environment or use default
BRIDGE_URL = os.getenv("MCP_BRIDGE_URL", "http://ai-agent-framework-mcp-bridge:8000")


@router.get("/discover")
async def discover_available_servers():
    """
    Discover available MCP servers from the bridge by querying its /servers endpoint.
    Returns a list of server names and their configurations.
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BRIDGE_URL}/servers", timeout=5.0)
            response.raise_for_status()
            servers_config = response.json()
            
            # Transform into a more UI-friendly format
            available_servers = []
            for name, config in servers_config.items():
                available_servers.append({
                    "name": name,
                    "display_name": _format_display_name(name),
                    "command": config.get("command"),
                    "requires_env": bool(config.get("env", {})),
                    "env_vars": list(config.get("env", {}).keys()),
                    "websocket_url": f"ws://ai-agent-framework-mcp-bridge:8000/mcp/{name}"
                })
            
            return {
                "bridge_url": BRIDGE_URL,
                "available": True,
                "servers": available_servers
            }
            
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Bridge service unavailable: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to discover servers: {str(e)}"
        )


@router.get("/health")
async def check_bridge_health():
    """Check if the MCP bridge is running and healthy"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BRIDGE_URL}/health", timeout=3.0)
            response.raise_for_status()
            return {
                "status": "available",
                "bridge_url": BRIDGE_URL,
                "bridge_response": response.json()
            }
    except Exception as e:
        return {
            "status": "unavailable", 
            "bridge_url": BRIDGE_URL,
            "error": str(e)
        }


def _format_display_name(server_name: str) -> str:
    """Convert server name to a user-friendly display name"""
    # filesystem -> Filesystem
    # brave-search -> Brave Search
    # fetch -> Fetch
    return ' '.join(word.capitalize() for word in server_name.replace('-', ' ').replace('_', ' ').split())
