import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum

from sqlalchemy import String, Text, ForeignKey, Integer, DateTime, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from shared.models.base import TenantEntity


class WorkflowStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class ExecutionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"
    TIMEOUT = "timeout"


class ExecutionPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class NodeType(str, Enum):
    START = "start"
    END = "end"
    TASK = "task"
    GATEWAY = "gateway"


class Workflow(TenantEntity):
    __tablename__ = "workflows"
    
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    version: Mapped[str] = mapped_column(String(50), nullable=False, default="1.0.0")
    
    bpmn_xml: Mapped[str] = mapped_column(Text, nullable=False)
    process_definition_key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    
    status: Mapped[str] = mapped_column(String(50), default="draft", nullable=False, index=True)
    tags: Mapped[List[str]] = mapped_column(JSONB, nullable=True, server_default=text("'[]'::jsonb"))
    category: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    
    input_schema: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=True, server_default=text("'{}'::jsonb"))
    output_schema: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=True, server_default=text("'{}'::jsonb"))
    default_variables: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=True, server_default=text("'{}'::jsonb"))
    
    timeout_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    max_concurrent_executions: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    retry_policy: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=True, server_default=text("'{}'::jsonb"))
    
    required_agents: Mapped[List[str]] = mapped_column(JSONB, nullable=True, server_default=text("'[]'::jsonb"))
    required_tools: Mapped[List[str]] = mapped_column(JSONB, nullable=True, server_default=text("'[]'::jsonb"))
    required_mcp_servers: Mapped[List[str]] = mapped_column(JSONB, nullable=True, server_default=text("'[]'::jsonb"))


class WorkflowExecution(TenantEntity):
    __tablename__ = "workflow_executions"
    
    workflow_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workflows.id"), nullable=False, index=True)
    execution_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False, index=True)
    priority: Mapped[str] = mapped_column(String(50), default="normal", nullable=False)
    
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    input_data: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=True, server_default=text("'{}'::jsonb"))
    output_data: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=True, server_default=text("'{}'::jsonb"))
    variables: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=True, server_default=text("'{}'::jsonb"))
    
    current_node_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    completed_nodes: Mapped[List[str]] = mapped_column(JSONB, nullable=True, server_default=text("'[]'::jsonb"))
    active_nodes: Mapped[List[str]] = mapped_column(JSONB, nullable=True, server_default=text("'[]'::jsonb"))
    
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_details: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=True, server_default=text("'{}'::jsonb"))
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    triggered_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    trigger_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    correlation_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)


class ExecutionLog(TenantEntity):
    __tablename__ = "execution_logs"
    
    execution_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workflow_executions.id"), nullable=False, index=True)
    node_id: Mapped[str] = mapped_column(String(255), nullable=False)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    level: Mapped[str] = mapped_column(String(20), default="INFO", nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    
    input_data: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=True)
    output_data: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=True)
    variables: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=True)
    
    agent_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    tool_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    error_details: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=True)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
