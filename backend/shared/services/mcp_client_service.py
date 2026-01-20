
from typing import Dict, Any, List, Optional
import httpx
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.sse import sse_client

import os
import json
import logging

logger = logging.getLogger(__name__)

class MCPClientService:
    """
    Service to connect to external MCP servers and introspect capabilities
    """

    async def connect_and_discover(
        self,
        url: str,
        transport: str = "http",  # http, sse, websocket, stdio
        auth_config: Optional[Dict[str, Any]] = None,
        env_vars: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Connect to MCP server, perform initialization handshake, and discover capabilities.
        Returns a dictionary with tools, resources, prompts, and server info.
        """
        
        # Prepare discovery result structure
        result = {
            "tools": [],
            "resources": [],
            "prompts": [],
            "server_info": {},
            "capabilities": []
        }

        try:
            if transport == "stdio":
                # Assuming internal bridge or local execution
                # For now, we only support the known bridge structure or custom command
                # This part might need adaptation depending on how "stdio" is exposed to the service
                # If it's the bridge, we might use WebSocket instead
               pass
            
            # For HTTP / SSE
            elif transport in ["sse", "http", "streamable-http"]:
                async with sse_client(url) as (read_stream, write_stream):
                    async with ClientSession(read_stream, write_stream) as session:
                        await session.initialize()
                        result = await self._discover_capabilities(session)
            
            # WebSocket transport would go here if using raw WS or bridge
            
            return result

        except Exception as e:
            logger.error(f"Failed to discover MCP capabilities from {url}: {e}")
            raise e

    async def _discover_capabilities(self, session: ClientSession) -> Dict[str, Any]:
        """Internal helper to fetch all capabilities from an initialized session"""
        
        # Get Tools
        tools_result = await session.list_tools()
        tools = [{"name": t.name, "description": t.description, "input_schema": t.inputSchema} for t in tools_result.tools]
        
        # Get Resources
        resources_result = await session.list_resources()
        resources = [{"uri": r.uri, "name": r.name, "description": r.description} for r in resources_result.resources]
        
        # Get Prompts
        prompts_result = await session.list_prompts()
        prompts = [{"name": p.name, "description": p.description, "arguments": [a.model_dump() for a in p.arguments] if p.arguments else []} for p in prompts_result.prompts]
        
        return {
            "tools": tools,
            "resources": resources,
            "prompts": prompts,
            "server_info": {}, # Session doesn't strictly expose server info object in same way, but handshake does
            "capabilities": [] # derived from above
        }

    async def read_resource(self, url: str, transport: str, uri: str) -> Any:
        try:
            async with sse_client(url) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    result = await session.read_resource(uri)
                    return result
        except Exception as e:
            logger.error(f"Failed to read resource {uri} from {url}: {e}")
            raise e

    async def get_prompt(self, url: str, transport: str, name: str, args: Dict) -> Any:
        try:
            async with sse_client(url) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    result = await session.get_prompt(name, arguments=args)
                    return result
        except Exception as e:
            logger.error(f"Failed to get prompt {name} from {url}: {e}")
            raise e
    
    async def call_tool(self, url: str, transport: str, name: str, args: Dict) -> Any:
        try:
            async with sse_client(url) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    result = await session.call_tool(name, arguments=args)
                    return result
        except Exception as e:
             logger.error(f"Failed to call tool {name} on {url}: {e}")
             raise e
