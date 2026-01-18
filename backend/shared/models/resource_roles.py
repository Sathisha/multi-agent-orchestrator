"""Resource role models for agent and workflow access control."""

from uuid import UUID
from datetime import datetime

from sqlalchemy import String, ForeignKey, DateTime, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.database.connection import Base


class AgentRole(Base):
    """Association table between agents and roles with access type."""
    
    __tablename__ = "agent_roles"
    
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, server_default=text('gen_random_uuid()'))
    agent_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)
    role_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), nullable=False, index=True)
    access_type: Mapped[str] = mapped_column(String(50), nullable=False)  # 'view', 'execute', 'modify'
    created_by: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text('CURRENT_TIMESTAMP'), nullable=False)
    
    # Relationships
    agent = relationship("Agent", backref="agent_roles")
    role = relationship("Role", backref="agent_roles")
    creator = relationship("User", foreign_keys=[created_by])
    
    def __repr__(self) -> str:
        return f"<AgentRole(agent_id={self.agent_id}, role_id={self.role_id}, access={self.access_type})>"


class WorkflowRole(Base):
    """Association table between workflows (chains) and roles with access type."""
    
    __tablename__ = "workflow_roles"
    
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, server_default=text('gen_random_uuid()'))
    workflow_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("chains.id", ondelete="CASCADE"), nullable=False, index=True)
    role_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), nullable=False, index=True)
    access_type: Mapped[str] = mapped_column(String(50), nullable=False)  # 'view', 'execute', 'modify'
    workflow_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False, index=True)
    role_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), nullable=False, index=True)
    access_type: Mapped[str] = mapped_column(String(50), nullable=False)  # 'view', 'execute', 'modify'
    created_by: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text('CURRENT_TIMESTAMP'), nullable=False)
    
    # Relationships
    workflow = relationship("Workflow", backref="workflow_roles")
    role = relationship("Role", backref="workflow_roles")
    creator = relationship("User", foreign_keys=[created_by])
    
    def __repr__(self) -> str:
        return f"<WorkflowRole(workflow_id={self.workflow_id}, role_id={self.role_id}, access={self.access_type})>"
