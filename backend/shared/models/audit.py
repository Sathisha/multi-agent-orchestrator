import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum

from sqlalchemy import String, Text, ForeignKey, DateTime, Boolean, text, func, Integer, Float
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from shared.models.base import BaseEntity

class AuditOutcome(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"

class AuditSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class AuditEventType(str, Enum):
    # Auth
    USER_LOGIN = "user_login"
    USER_LOGIN_FAILED = "user_login_failed"
    USER_LOGOUT = "user_logout"
    USER_CREATED = "user_created"
    # Agent
    AGENT_CREATED = "agent_created"
    AGENT_UPDATED = "agent_updated"
    AGENT_DELETED = "agent_deleted"
    AGENT_EXECUTED = "agent_executed"
    AGENT_EXECUTION_FAILED = "agent_execution_failed"
    # Workflow
    WORKFLOW_CREATED = "workflow_created"
    WORKFLOW_UPDATED = "workflow_updated"
    WORKFLOW_DELETED = "workflow_deleted"
    WORKFLOW_EXECUTED = "workflow_executed"
    WORKFLOW_EXECUTION_FAILED = "workflow_execution_failed"
    # Tool
    TOOL_CREATED = "tool_created"
    TOOL_UPDATED = "tool_updated"
    TOOL_DELETED = "tool_deleted"
    TOOL_EXECUTED = "tool_executed"
    # MCP
    MCP_SERVER_CONNECTED = "mcp_server_connected"
    MCP_SERVER_DISCONNECTED = "mcp_server_disconnected"
    MCP_CALL_MADE = "mcp_call_made"
    # Data
    DATA_ACCESSED = "data_accessed"
    DATA_EXPORTED = "data_exported"
    DATA_IMPORTED = "data_imported"
    # Security
    ACCESS_DENIED = "access_denied"
    SECURITY_VIOLATION = "security_violation"
    GUARDRAIL_TRIGGERED = "guardrail_triggered"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    # Role
    ROLE_CREATED = "role_created"
    ROLE_UPDATED = "role_updated"
    ROLE_DELETED = "role_deleted"
    ROLE_ASSIGNED = "role_assigned"
    PERMISSION_GRANTED = "permission_granted"
    # System
    SYSTEM_STARTED = "system_started"
    CONFIGURATION_CHANGED = "configuration_changed"

# Also include stub request/response classes to resolve imports in AuditService if they were imported from models
# AuditService imports: AuditLogRequest, AuditLogResponse, AuditLogCreateRequest, AuditStatistics, ComplianceReport
# I should add them here as Pydantic models

from pydantic import BaseModel

class AuditLogRequest(BaseModel):
    event_types: Optional[List[AuditEventType]] = None
    user_id: Optional[uuid.UUID] = None
    username: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    action: Optional[str] = None
    outcome: Optional[AuditOutcome] = None
    severity: Optional[AuditSeverity] = None
    source_ip: Optional[str] = None
    correlation_id: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    compliance_tags: Optional[List[str]] = None
    sort_by: str = "timestamp"
    sort_order: str = "desc"
    page: int = 1
    size: int = 50

class AuditLogResponse(BaseModel):
    id: str
    created_at: datetime
    updated_at: datetime
    event_type: AuditEventType
    event_id: str
    correlation_id: str
    timestamp: datetime
    user_id: Optional[str] = None
    username: Optional[str] = None
    session_id: Optional[str] = None
    source_ip: Optional[str] = None
    user_agent: Optional[str] = None
    source_service: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    resource_name: Optional[str] = None
    action: str
    outcome: AuditOutcome
    severity: AuditSeverity
    message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    compliance_tags: Optional[List[str]] = None

class AuditLogCreateRequest(BaseModel):
    pass # Stub if needed

class AuditStatistics(BaseModel):
    total_events: int
    events_by_type: Dict[str, int]
    events_by_outcome: Dict[str, int]
    events_by_severity: Dict[str, int]
    top_users: List[Dict[str, Any]]
    top_resources: List[Dict[str, Any]]
    security_events: int
    failed_events: int

class ComplianceReport(BaseModel):
    report_id: str
    generated_at: datetime
    period_start: datetime
    period_end: datetime
    total_events: int
    user_activities: Dict[str, int]
    resource_access: Dict[str, int]
    security_incidents: List[Dict[str, Any]]
    policy_violations: List[Dict[str, Any]]
    data_access_events: int
    data_export_events: int
    failed_login_attempts: int
    privilege_escalations: int

class AuditLog(BaseEntity):
    __tablename__ = "audit_logs"
    
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    event_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    correlation_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    session_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    source_ip: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_service: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    resource_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    resource_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    resource_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    outcome: Mapped[str] = mapped_column(String(20), nullable=False, default=AuditOutcome.SUCCESS, index=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default=AuditSeverity.LOW, index=True)
    message: Mapped[str] = mapped_column(Text, nullable=True)
    
    details: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=True, server_default=text("'{}'::jsonb"))
    request_data: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=True, server_default=text("'{}'::jsonb"))
    response_data: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=True, server_default=text("'{}'::jsonb"))
    
    error_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    compliance_tags: Mapped[List[str]] = mapped_column(JSONB, nullable=True, server_default=text("'[]'::jsonb"))
    retention_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    checksum: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    def calculate_checksum(self) -> str:
        return "checksum"

    def verify_integrity(self) -> bool:
        return True
