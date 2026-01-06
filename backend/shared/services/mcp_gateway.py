"""
MCP Gateway Service for the AI Agent Framework.

This service implements the Model Context Protocol (MCP) for connecting to
external MCP servers and managing tool integrations.
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from uuid import UUID, uuid4

import aiohttp
import websockets
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..database import get_database_session
from ..models.tool import MCPServer, MCPServerStatus, Tool, ToolType, ToolStatus
from ..models.tool import MCPServerRequest, MCPServerResponse
from ..models.audit import AuditLog, AuditEventType
from ..logging.config import get_logger

logger = get_logger(__name__)


class MCPConnectionError(Exception):
    """Exception raised when MCP server connection fails."""
    pass


class MCPAuthenticationError(Exception):
    """Exception raised when MCP server authentication fails."""
    pass


class MCPProtocolError(Exception):
    """Exception raised when MCP protocol communication fails."""
    pass


class MCPGatewayService:
    """Service for managing MCP server connections and tool discovery."""
    
    def __init__(self):
        self._connections = {}  # Active MCP server connections
        self._health_check_tasks = {}  # Background health check tasks
        self._discovery_cache = {}  # Tool discovery cache
        self._session_pool = {}  # HTTP session pool
    
    async def create_mcp_server(
        self,
        user_id: UUID,
        server_request: MCPServerRequest
    ) -> MCPServerResponse:
        """Create a new MCP server configuration."""
        async with get_database_session() as session:
            # Check if server name already exists
            existing_server = await session.execute(
                select(MCPServer).where(
                    MCPServer.name == server_request.name
                )
            )
            if existing_server.scalar_one_or_none():
                raise ValueError(f"MCP server with name '{server_request.name}' already exists")
            
            # Create MCP server instance
            mcp_server = MCPServer(
                id=uuid4(),
                created_by=user_id,
                updated_by=user_id,
                **server_request.model_dump()
            )
            
            session.add(mcp_server)
            await session.commit()
            await session.refresh(mcp_server)
            
            # Log audit event
            await self._log_audit_event(
                session=session,
                event_type=AuditEventType.MCP_SERVER_CONNECTED,
                user_id=user_id,
                resource_id=str(mcp_server.id),
                details={
                    "server_name": mcp_server.name,
                    "url": mcp_server.url,
                    "protocol": mcp_server.protocol
                }
            )
            
            # Start background connection attempt
            asyncio.create_task(self._connect_to_server(mcp_server))
            
            logger.info(
                "MCP server created successfully",
                server_id=str(mcp_server.id),
                server_name=mcp_server.name,
                user_id=str(user_id)
            )
            
            return MCPServerResponse.model_validate(mcp_server)
    
    async def get_mcp_server(
        self,
        user_id: UUID,
        server_id: UUID
    ) -> Optional[MCPServerResponse]:
        """Get an MCP server by ID."""
        async with get_database_session() as session:
            result = await session.execute(
                select(MCPServer)
                .options(selectinload(MCPServer.tools))
                .where(
                    MCPServer.id == server_id
                )
            )
            server = result.scalar_one_or_none()
            
            if not server:
                return None
            
            return MCPServerResponse.model_validate(server)
    
    async def list_mcp_servers(
        self,
        user_id: UUID,
        status: Optional[MCPServerStatus] = None,
        category: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[MCPServerResponse]:
        """List MCP servers with optional filtering."""
        async with get_database_session() as session:
            query = select(MCPServer)
            
            # Apply filters
            if status:
                query = query.where(MCPServer.status == status)
            if category:
                query = query.where(MCPServer.category == category)
            
            # Apply pagination
            query = query.offset(offset).limit(limit).order_by(MCPServer.created_at.desc())
            
            result = await session.execute(query)
            servers = result.scalars().all()
            
            return [MCPServerResponse.model_validate(server) for server in servers]
    
    async def update_mcp_server(
        self,
        user_id: UUID,
        server_id: UUID,
        server_request: MCPServerRequest
    ) -> MCPServerResponse:
        """Update an existing MCP server."""
        async with get_database_session() as session:
            # Get existing server
            result = await session.execute(
                select(MCPServer).where(
                    MCPServer.id == server_id
                )
            )
            server = result.scalar_one_or_none()
            
            if not server:
                raise ValueError(f"MCP server with ID {server_id} not found")
            
            # Store old values for audit
            old_values = {
                "name": server.name,
                "url": server.url,
                "status": server.status
            }
            
            # Update server fields
            update_data = server_request.model_dump(exclude_unset=True)
            for field, value in update_data.items():
                if hasattr(server, field):
                    setattr(server, field, value)
            
            server.updated_by = user_id
            server.updated_at = datetime.utcnow()
            
            await session.commit()
            await session.refresh(server)
            
            # Reconnect if connection details changed
            if any(field in update_data for field in ['url', 'protocol', 'auth_type', 'auth_config']):
                await self._disconnect_from_server(server_id)
                asyncio.create_task(self._connect_to_server(server))
            
            # Log audit event
            await self._log_audit_event(
                session=session,
                event_type=AuditEventType.MCP_SERVER_CONNECTED,
                user_id=user_id,
                resource_id=str(server.id),
                details={
                    "server_name": server.name,
                    "old_values": old_values,
                    "new_values": {
                        "name": server.name,
                        "url": server.url,
                        "status": server.status
                    }
                }
            )
            
            logger.info(
                "MCP server updated successfully",
                server_id=str(server.id),
                server_name=server.name,
                user_id=str(user_id)
            )
            
            return MCPServerResponse.model_validate(server)
    
    async def delete_mcp_server(
        self,
        user_id: UUID,
        server_id: UUID
    ) -> bool:
        """Delete an MCP server."""
        async with get_database_session() as session:
            # Get existing server
            result = await session.execute(
                select(MCPServer).where(
                    MCPServer.id == server_id
                )
            )
            server = result.scalar_one_or_none()
            
            if not server:
                return False
            
            # Store server info for audit
            server_info = {
                "server_name": server.name,
                "url": server.url,
                "protocol": server.protocol
            }
            
            # Disconnect from server
            await self._disconnect_from_server(server_id)
            
            await session.delete(server)
            await session.commit()
            
            # Log audit event
            await self._log_audit_event(
                session=session,
                event_type=AuditEventType.MCP_SERVER_DISCONNECTED,
                user_id=user_id,
                resource_id=str(server_id),
                details=server_info
            )
            
            logger.info(
                "MCP server deleted successfully",
                server_id=str(server_id),
                user_id=str(user_id)
            )
            
            return True
    
    async def connect_to_server(
        self,
        user_id: UUID,
        server_id: UUID
    ) -> Dict[str, Any]:
        """Manually connect to an MCP server."""
        async with get_database_session() as session:
            # Get server
            result = await session.execute(
                select(MCPServer).where(
                    MCPServer.id == server_id
                )
            )
            server = result.scalar_one_or_none()
            
            if not server:
                raise ValueError(f"MCP server with ID {server_id} not found")
            
            # Attempt connection
            connection_result = await self._connect_to_server(server)
            
            return {
                "server_id": str(server_id),
                "server_name": server.name,
                "connection_status": connection_result["status"],
                "message": connection_result.get("message", ""),
                "connected_at": datetime.utcnow().isoformat()
            }
    
    async def discover_tools(
        self,
        user_id: UUID,
        server_id: UUID,
        force_refresh: bool = False
    ) -> Dict[str, Any]:
        """Discover available tools on an MCP server."""
        cache_key = f"{server_id}"
        
        # Check cache first
        if not force_refresh and cache_key in self._discovery_cache:
            cache_entry = self._discovery_cache[cache_key]
            if datetime.utcnow() - cache_entry["timestamp"] < timedelta(minutes=5):
                return cache_entry["data"]
        
        async with get_database_session() as session:
            # Get server
            result = await session.execute(
                select(MCPServer).where(
                    MCPServer.id == server_id
                )
            )
            server = result.scalar_one_or_none()
            
            if not server:
                raise ValueError(f"MCP server with ID {server_id} not found")
            
            if server.status != MCPServerStatus.CONNECTED:
                raise MCPConnectionError(f"MCP server is not connected (status: {server.status})")
            
            # Discover tools
            discovered_tools = await self._discover_server_tools(server)
            
            # Update cache
            self._discovery_cache[cache_key] = {
                "timestamp": datetime.utcnow(),
                "data": discovered_tools
            }
            
            # Sync discovered tools to database
            await self._sync_discovered_tools(session, server, discovered_tools["tools"])
            
            logger.info(
                "Tools discovered successfully",
                server_id=str(server_id),
                tool_count=len(discovered_tools["tools"])
            )
            
            return discovered_tools
    
    async def call_mcp_tool(
        self,
        user_id: UUID,
        server_id: UUID,
        tool_name: str,
        inputs: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Call a tool on an MCP server."""
        async with get_database_session() as session:
            # Get server
            result = await session.execute(
                select(MCPServer).where(
                    MCPServer.id == server_id
                )
            )
            server = result.scalar_one_or_none()
            
            if not server:
                raise ValueError(f"MCP server with ID {server_id} not found")
            
            if server.status != MCPServerStatus.CONNECTED:
                raise MCPConnectionError(f"MCP server is not connected (status: {server.status})")
            
            # Execute tool call
            start_time = time.time()
            
            try:
                result = await self._call_server_tool(server, tool_name, inputs, context)
                execution_time = int((time.time() - start_time) * 1000)
                
                # Update server statistics
                server.total_requests += 1
                server.successful_requests += 1
                
                if server.average_response_time:
                    server.average_response_time = int(
                        (server.average_response_time + execution_time) / 2
                    )
                else:
                    server.average_response_time = execution_time
                
                await session.commit()
                
                # Log audit event
                await self._log_audit_event(
                    session=session,
                    event_type=AuditEventType.MCP_CALL_MADE,
                    user_id=user_id,
                    resource_id=str(server.id),
                    details={
                        "server_name": server.name,
                        "tool_name": tool_name,
                        "execution_time_ms": execution_time,
                        "inputs": inputs,
                        "outputs": result
                    }
                )
                
                logger.info(
                    "MCP tool called successfully",
                    server_id=str(server_id),
                    tool_name=tool_name,
                    execution_time_ms=execution_time
                )
                
                return {
                    "server_id": str(server_id),
                    "tool_name": tool_name,
                    "status": "success",
                    "result": result,
                    "execution_time": execution_time,
                    "called_at": datetime.utcnow().isoformat()
                }
                
            except Exception as e:
                execution_time = int((time.time() - start_time) * 1000)
                
                # Update error statistics
                server.total_requests += 1
                server.failed_requests += 1
                server.last_error = str(e)
                server.last_error_at = datetime.utcnow()
                server.error_count += 1
                
                await session.commit()
                
                logger.error(
                    "MCP tool call failed",
                    server_id=str(server_id),
                    tool_name=tool_name,
                    error=str(e),
                    execution_time_ms=execution_time
                )
                
                return {
                    "server_id": str(server_id),
                    "tool_name": tool_name,
                    "status": "error",
                    "error": str(e),
                    "execution_time": execution_time,
                    "called_at": datetime.utcnow().isoformat()
                }
    
    async def _connect_to_server(self, server: MCPServer) -> Dict[str, Any]:
        """Connect to an MCP server."""
        
        try:
            # Update status to connecting
            async with get_database_session() as session:
                await session.merge(server)
                server.status = MCPServerStatus.CONNECTING
                await session.commit()
            
            # Attempt connection based on protocol
            if server.protocol in ['http', 'https']:
                connection_result = await self._connect_http_server(server)
            elif server.protocol in ['ws', 'wss']:
                connection_result = await self._connect_websocket_server(server)
            else:
                raise MCPProtocolError(f"Unsupported protocol: {server.protocol}")
            
            if connection_result["success"]:
                # Update status to connected
                async with get_database_session() as session:
                    await session.merge(server)
                    server.status = MCPServerStatus.CONNECTED
                    server.last_connected_at = datetime.utcnow()
                    server.last_health_check_at = datetime.utcnow()
                    server.error_count = 0
                    server.last_error = None
                    
                    # Update server info if available
                    if "server_info" in connection_result:
                        server.server_info = connection_result["server_info"]
                    if "capabilities" in connection_result:
                        server.capabilities = connection_result["capabilities"]
                    
                    await session.commit()
                
                # Start health check task
                self._start_health_check_task(server)
                
                logger.info(
                    "Connected to MCP server successfully",
                    server_id=str(server.id),
                    server_name=server.name,
                    url=server.url
                )
                
                return {"status": "connected", "message": "Successfully connected to MCP server"}
            else:
                raise MCPConnectionError(connection_result.get("error", "Connection failed"))
                
        except Exception as e:
            # Update status to error
            async with get_database_session() as session:
                await session.merge(server)
                server.status = MCPServerStatus.ERROR
                server.last_error = str(e)
                server.last_error_at = datetime.utcnow()
                server.error_count += 1
                await session.commit()
            
            logger.error(
                "Failed to connect to MCP server",
                server_id=str(server.id),
                server_name=server.name,
                url=server.url,
                error=str(e)
            )
            
            return {"status": "error", "message": str(e)}
    
    async def _connect_http_server(self, server: MCPServer) -> Dict[str, Any]:
        """Connect to HTTP-based MCP server."""
        
        try:
            # Create HTTP session if not exists
            if server.id not in self._session_pool:
                timeout = aiohttp.ClientTimeout(total=server.timeout_seconds)
                self._session_pool[server.id] = aiohttp.ClientSession(timeout=timeout)
            
            session = self._session_pool[server.id]
            
            # Prepare authentication headers
            headers = {"Content-Type": "application/json"}
            if server.auth_type and server.auth_config:
                headers.update(self._prepare_auth_headers(server))
            
            # Test connection with server info endpoint
            info_url = f"{server.url.rstrip('/')}/info"
            
            async with session.get(info_url, headers=headers) as response:
                if response.status == 200:
                    server_info = await response.json()
                    return {
                        "success": True,
                        "server_info": server_info,
                        "capabilities": server_info.get("capabilities", {})
                    }
                elif response.status == 401:
                    raise MCPAuthenticationError("Authentication failed")
                else:
                    raise MCPConnectionError(f"Server returned status {response.status}")
                    
        except aiohttp.ClientError as e:
            return {"success": False, "error": f"HTTP connection error: {str(e)}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _connect_websocket_server(self, server: MCPServer) -> Dict[str, Any]:
        """Connect to WebSocket-based MCP server."""
        
        try:
            # Prepare connection headers
            headers = {}
            if server.auth_type and server.auth_config:
                headers.update(self._prepare_auth_headers(server))
            
            # Connect to WebSocket
            websocket = await websockets.connect(
                server.url,
                extra_headers=headers,
                timeout=server.timeout_seconds
            )
            
            # Store connection
            self._connections[server.id] = websocket
            
            # Send initial handshake
            handshake_message = {
                "jsonrpc": "2.0",
                "method": "initialize",
                "params": {
                    "protocolVersion": "1.0",
                    "clientInfo": {
                        "name": "AI Agent Framework",
                        "version": "1.0.0"
                    }
                },
                "id": str(uuid4())
            }
            
            await websocket.send(json.dumps(handshake_message))
            
            # Wait for response
            response = await asyncio.wait_for(
                websocket.recv(),
                timeout=server.timeout_seconds
            )
            
            response_data = json.loads(response)
            
            if "error" in response_data:
                raise MCPProtocolError(f"Handshake failed: {response_data['error']}")
            
            server_info = response_data.get("result", {})
            
            return {
                "success": True,
                "server_info": server_info,
                "capabilities": server_info.get("capabilities", {})
            }
            
        except websockets.exceptions.WebSocketException as e:
            return {"success": False, "error": f"WebSocket connection error: {str(e)}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _disconnect_from_server(self, server_id: UUID):
        """Disconnect from an MCP server."""
        
        # Stop health check task
        if server_id in self._health_check_tasks:
            self._health_check_tasks[server_id].cancel()
            del self._health_check_tasks[server_id]
        
        # Close WebSocket connection
        if server_id in self._connections:
            try:
                await self._connections[server_id].close()
            except:
                pass
            del self._connections[server_id]
        
        # Close HTTP session
        if server_id in self._session_pool:
            try:
                await self._session_pool[server_id].close()
            except:
                pass
            del self._session_pool[server_id]
        
        # Update server status
        async with get_database_session() as session:
            result = await session.execute(
                select(MCPServer).where(MCPServer.id == server_id)
            )
            server = result.scalar_one_or_none()
            
            if server:
                server.status = MCPServerStatus.DISCONNECTED
                await session.commit()
    
    def _prepare_auth_headers(self, server: MCPServer) -> Dict[str, str]:
        """Prepare authentication headers for MCP server."""
        
        headers = {}
        
        if server.auth_type == "bearer" and "token" in server.auth_config:
            headers["Authorization"] = f"Bearer {server.auth_config['token']}"
        elif server.auth_type == "api_key" and "api_key" in server.auth_config:
            key_name = server.auth_config.get("key_name", "X-API-Key")
            headers[key_name] = server.auth_config["api_key"]
        elif server.auth_type == "basic" and "username" in server.auth_config:
            import base64
            credentials = f"{server.auth_config['username']}:{server.auth_config.get('password', '')}"
            encoded_credentials = base64.b64encode(credentials.encode()).decode()
            headers["Authorization"] = f"Basic {encoded_credentials}"
        
        return headers
    
    def _start_health_check_task(self, server: MCPServer):
        """Start background health check task for a server."""
        
        async def health_check_loop():
            while True:
                try:
                    await asyncio.sleep(server.health_check_interval)
                    await self._perform_health_check(server)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(
                        "Health check failed",
                        server_id=str(server.id),
                        error=str(e)
                    )
        
        task = asyncio.create_task(health_check_loop())
        self._health_check_tasks[server.id] = task
    
    async def _perform_health_check(self, server: MCPServer):
        """Perform health check on an MCP server."""
        
        try:
            if server.protocol in ['http', 'https']:
                await self._http_health_check(server)
            elif server.protocol in ['ws', 'wss']:
                await self._websocket_health_check(server)
            
            # Update health check timestamp
            async with get_database_session() as session:
                await session.merge(server)
                server.last_health_check_at = datetime.utcnow()
                await session.commit()
                
        except Exception as e:
            # Update error status
            async with get_database_session() as session:
                await session.merge(server)
                server.status = MCPServerStatus.ERROR
                server.last_error = str(e)
                server.last_error_at = datetime.utcnow()
                server.error_count += 1
                await session.commit()
            
            # Attempt reconnection
            asyncio.create_task(self._connect_to_server(server))
    
    async def _http_health_check(self, server: MCPServer):
        """Perform HTTP health check."""
        
        if server.id not in self._session_pool:
            return
        
        session = self._session_pool[server.id]
        headers = {"Content-Type": "application/json"}
        
        if server.auth_type and server.auth_config:
            headers.update(self._prepare_auth_headers(server))
        
        health_url = f"{server.url.rstrip('/')}/health"
        
        async with session.get(health_url, headers=headers) as response:
            if response.status != 200:
                raise MCPConnectionError(f"Health check failed with status {response.status}")
    
    async def _websocket_health_check(self, server: MCPServer):
        """Perform WebSocket health check."""
        
        if server.id not in self._connections:
            return
        
        websocket = self._connections[server.id]
        
        # Send ping message
        ping_message = {
            "jsonrpc": "2.0",
            "method": "ping",
            "id": str(uuid4())
        }
        
        await websocket.send(json.dumps(ping_message))
        
        # Wait for pong response
        response = await asyncio.wait_for(
            websocket.recv(),
            timeout=server.timeout_seconds
        )
        
        response_data = json.loads(response)
        
        if "error" in response_data:
            raise MCPProtocolError(f"Health check failed: {response_data['error']}")
    
    async def _discover_server_tools(self, server: MCPServer) -> Dict[str, Any]:
        """Discover available tools on an MCP server."""
        
        try:
            if server.protocol in ['http', 'https']:
                return await self._http_discover_tools(server)
            elif server.protocol in ['ws', 'wss']:
                return await self._websocket_discover_tools(server)
            else:
                raise MCPProtocolError(f"Unsupported protocol: {server.protocol}")
                
        except Exception as e:
            logger.error(
                "Tool discovery failed",
                server_id=str(server.id),
                error=str(e)
            )
            return {"tools": [], "capabilities": [], "error": str(e)}
    
    async def _http_discover_tools(self, server: MCPServer) -> Dict[str, Any]:
        """Discover tools via HTTP."""
        
        if server.id not in self._session_pool:
            raise MCPConnectionError("No active HTTP session")
        
        session = self._session_pool[server.id]
        headers = {"Content-Type": "application/json"}
        
        if server.auth_type and server.auth_config:
            headers.update(self._prepare_auth_headers(server))
        
        tools_url = f"{server.url.rstrip('/')}/tools"
        
        async with session.get(tools_url, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                return {
                    "tools": data.get("tools", []),
                    "capabilities": data.get("capabilities", []),
                    "server_info": data.get("server_info", {})
                }
            else:
                raise MCPConnectionError(f"Tool discovery failed with status {response.status}")
    
    async def _websocket_discover_tools(self, server: MCPServer) -> Dict[str, Any]:
        """Discover tools via WebSocket."""
        
        if server.id not in self._connections:
            raise MCPConnectionError("No active WebSocket connection")
        
        websocket = self._connections[server.id]
        
        # Send tools discovery message
        discovery_message = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "id": str(uuid4())
        }
        
        await websocket.send(json.dumps(discovery_message))
        
        # Wait for response
        response = await asyncio.wait_for(
            websocket.recv(),
            timeout=server.timeout_seconds
        )
        
        response_data = json.loads(response)
        
        if "error" in response_data:
            raise MCPProtocolError(f"Tool discovery failed: {response_data['error']}")
        
        result = response_data.get("result", {})
        
        return {
            "tools": result.get("tools", []),
            "capabilities": result.get("capabilities", []),
            "server_info": result.get("server_info", {})
        }
    
    async def _sync_discovered_tools(
        self,
        session: AsyncSession,
        server: MCPServer,
        discovered_tools: List[Dict[str, Any]]
    ):
        """Sync discovered tools to the database."""
        
        for tool_info in discovered_tools:
            # Check if tool already exists
            existing_tool = await session.execute(
                select(Tool).where(
                    and_(
                        Tool.mcp_server_id == server.id,
                        Tool.mcp_tool_name == tool_info["name"]
                    )
                )
            )
            
            if not existing_tool.scalar_one_or_none():
                # Create new tool entry
                tool = Tool(
                    id=uuid4(),
                    name=f"{server.name}_{tool_info['name']}",
                    display_name=tool_info.get("display_name", tool_info["name"]),
                    description=tool_info.get("description", ""),
                    tool_type=ToolType.MCP_SERVER,
                    status=ToolStatus.ACTIVE,
                    mcp_server_id=server.id,
                    mcp_tool_name=tool_info["name"],
                    input_schema=tool_info.get("input_schema", {}),
                    output_schema=tool_info.get("output_schema", {}),
                    parameters=tool_info.get("parameters", {}),
                    capabilities=tool_info.get("capabilities", []),
                    category=tool_info.get("category", "mcp"),
                    created_by=None,  # System-created
                    updated_by=None
                )
                
                session.add(tool)
        
        await session.commit()
    
    async def _call_server_tool(
        self,
        server: MCPServer,
        tool_name: str,
        inputs: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Call a tool on an MCP server."""
        
        if server.protocol in ['http', 'https']:
            return await self._http_call_tool(server, tool_name, inputs, context)
        elif server.protocol in ['ws', 'wss']:
            return await self._websocket_call_tool(server, tool_name, inputs, context)
        else:
            raise MCPProtocolError(f"Unsupported protocol: {server.protocol}")
    
    async def _http_call_tool(
        self,
        server: MCPServer,
        tool_name: str,
        inputs: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Call tool via HTTP."""
        
        if server.id not in self._session_pool:
            raise MCPConnectionError("No active HTTP session")
        
        session = self._session_pool[server.id]
        headers = {"Content-Type": "application/json"}
        
        if server.auth_type and server.auth_config:
            headers.update(self._prepare_auth_headers(server))
        
        call_url = f"{server.url.rstrip('/')}/tools/{tool_name}/call"
        
        payload = {
            "inputs": inputs,
            "context": context or {}
        }
        
        async with session.post(call_url, json=payload, headers=headers) as response:
            if response.status == 200:
                return await response.json()
            else:
                error_text = await response.text()
                raise MCPProtocolError(f"Tool call failed with status {response.status}: {error_text}")
    
    async def _websocket_call_tool(
        self,
        server: MCPServer,
        tool_name: str,
        inputs: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Call tool via WebSocket."""
        
        if server.id not in self._connections:
            raise MCPConnectionError("No active WebSocket connection")
        
        websocket = self._connections[server.id]
        
        # Send tool call message
        call_message = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": inputs,
                "context": context or {}
            },
            "id": str(uuid4())
        }
        
        await websocket.send(json.dumps(call_message))
        
        # Wait for response
        response = await asyncio.wait_for(
            websocket.recv(),
            timeout=server.timeout_seconds
        )
        
        response_data = json.loads(response)
        
        if "error" in response_data:
            raise MCPProtocolError(f"Tool call failed: {response_data['error']}")
        
        return response_data.get("result", {})