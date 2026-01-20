from enum import Enum
from typing import Optional, List, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator
from sqlalchemy import String, Text, ForeignKey, text, Integer, Float, DateTime
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.models.base import BaseEntity

class ToolType(str, Enum):
    CUSTOM = "custom"
    MCP_SERVER = "mcp_server"

class ToolStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    ARCHIVED = "archived"

class Tool(BaseEntity):
    __tablename__ = "tools"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    version: Mapped[str] = mapped_column(String(50), default="1.0.0")
    tool_type: Mapped[ToolType] = mapped_column(String(50), default=ToolType.CUSTOM)
    status: Mapped[ToolStatus] = mapped_column(String(50), default=ToolStatus.DRAFT)
    
    # Code execution (Custom tools)
    code: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    entry_point: Mapped[Optional[str]] = mapped_column(String(255), default="execute")
    
    # Schemas
    input_schema: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=text("'{}'::jsonb"))
    output_schema: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=text("'{}'::jsonb"))
    
    # Configuration
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    tags: Mapped[List[str]] = mapped_column(JSONB, default=text("'[]'::jsonb"))
    capabilities: Mapped[List[str]] = mapped_column(JSONB, default=text("'[]'::jsonb"))
    tool_config_metadata: Mapped[Dict[str, Any]] = mapped_column("tool_metadata", JSONB, default=text("'{}'::jsonb"))
    
    # Metrics
    usage_count: Mapped[int] = mapped_column(Integer, default=0)
    last_used_at: Mapped[Optional[DateTime]] = mapped_column(DateTime(timezone=True), nullable=True)
    average_execution_time: Mapped[Optional[int]] = mapped_column(Integer, nullable=True) # ms
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=30)
    
    # Validation
    last_validated_at: Mapped[Optional[DateTime]] = mapped_column(DateTime(timezone=True), nullable=True)
    validation_errors: Mapped[List[str]] = mapped_column(JSONB, default=text("'[]'::jsonb"))
    
    # Relations
    # For now assuming MCP server relation is optional or stubbed if MCP model missing
    # mcp_server_id: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("mcp_servers.id"), nullable=True)
    # mcp_server = relationship("MCPServer", back_populates="tools", lazy="selectin") 

    # Since I don't have MCPServer model yet, I will comment out mcp_server usage in service if needed.
    


# Pydantic Models for Request/Response
class ToolRequest(BaseModel):
    name: str
    description: Optional[str] = None
    version: Optional[str] = "1.0.0"
    tool_type: ToolType = ToolType.CUSTOM
    code: Optional[str] = None
    input_schema: Optional[Dict[str, Any]] = {}
    output_schema: Optional[Dict[str, Any]] = {}
    category: Optional[str] = None
    tags: Optional[List[str]] = []
    capabilities: Optional[List[str]] = []
    timeout_seconds: Optional[int] = 30

class ToolResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    version: str
    tool_type: ToolType
    status: ToolStatus
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    category: Optional[str]
    tags: List[str]
    capabilities: List[str]
    usage_count: int
    last_used_at: Optional[Any] # datetime
    average_execution_time: Optional[int]
    last_validated_at: Optional[Any] # datetime
    validation_errors: List[str]
    created_at: Any
    updated_at: Any

    class Config:
        from_attributes = True

class ToolDiscoveryResponse(BaseModel):
    available_tools: List[ToolResponse]
    categories: List[str]
    capabilities: List[str]

class ToolExecutionRequest(BaseModel):
    tool_id: UUID
    inputs: Dict[str, Any]
    context: Optional[Dict[str, Any]] = None
    timeout_override: Optional[int] = None

class ToolExecutionResponse(BaseModel):
    tool_id: str
    execution_id: str
    status: str
    outputs: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time: Optional[int] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None

class MCPServerStatus(str, Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    MAINTENANCE = "maintenance"

class MCPServer(BaseEntity):
    __tablename__ = "mcp_servers"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    base_url: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[str] = mapped_column(String(50), default="1.0.0")
    status: Mapped[MCPServerStatus] = mapped_column(String(50), default=MCPServerStatus.DISCONNECTED)
    
    # Configuration
    auth_config: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=text("'{}'::jsonb"))
    env_vars: Mapped[Dict[str, str]] = mapped_column(JSONB, default=text("'{}'::jsonb"))
    protocol: Mapped[str] = mapped_column(String(50), default="websocket") # http, sse, websocket, stdio
    
    # Discovery
    capabilities: Mapped[List[str]] = mapped_column(JSONB, default=text("'[]'::jsonb"))
    resources: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, default=text("'[]'::jsonb"))
    prompts: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, default=text("'[]'::jsonb"))
    server_info: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=text("'{}'::jsonb"))
    
    last_connected_at: Mapped[Optional[DateTime]] = mapped_column(DateTime(timezone=True), nullable=True)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    last_health_check_at: Mapped[Optional[DateTime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    success_rate: Mapped[float] = mapped_column(Float, default=100.0)
    total_requests: Mapped[int] = mapped_column(Integer, default=0)
    successful_requests: Mapped[int] = mapped_column(Integer, default=0)
    failed_requests: Mapped[int] = mapped_column(Integer, default=0)
    average_response_time: Mapped[float] = mapped_column(Float, default=0.0)


class MCPServerRequest(BaseModel):
    name: str
    description: Optional[str] = None
    base_url: str
    version: Optional[str] = "1.0.0"
    auth_config: Optional[Dict[str, Any]] = {}
    env_vars: Optional[Dict[str, str]] = {}
    protocol: Optional[str] = "websocket"

class MCPServerResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    base_url: str
    version: str
    status: MCPServerStatus
    protocol: str
    capabilities: List[str]
    resources: List[Dict[str, Any]] = []
    prompts: List[Dict[str, Any]] = []
    server_info: Dict[str, Any] = {}
    env_vars: Dict[str, str] = {}
    auth_config: Dict[str, Any] = {} # be careful exposing this? maybe sanitize
    
    last_connected_at: Optional[Any]
    error_count: int
    tool_count: Optional[int] = 0
    created_at: Any
    updated_at: Any

    class Config:
        from_attributes = True
