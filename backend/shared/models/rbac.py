import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime

from sqlalchemy import String, Boolean, Text, ForeignKey, Table, Column, text, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.models.base import BaseEntity, SystemEntity
from shared.database.connection import Base

# Association table for Role-Permission
role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", UUID(as_uuid=True), ForeignKey("roles.id"), primary_key=True),
    Column("permission_id", UUID(as_uuid=True), ForeignKey("permissions.id"), primary_key=True)
)

class Permission(SystemEntity):
    __tablename__ = "permissions"
    
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    resource: Mapped[str] = mapped_column(String(100), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    conditions: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=True, server_default=text("'{}'::jsonb"))

class Role(SystemEntity):
    __tablename__ = "roles"
    
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    display_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    permission_level: Mapped[Optional[int]] = mapped_column(nullable=True, index=True)
    is_system_role: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    permissions = relationship("Permission", secondary=role_permissions, backref="roles")

class UserRole(Base):
    __tablename__ = "user_roles"
    
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    role_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)
    id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True, server_default=text('gen_random_uuid()'))
    assigned_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    assigned_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, server_default=text('CURRENT_TIMESTAMP'))
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    user = relationship("User", back_populates="roles", foreign_keys=[user_id])
    role = relationship("Role", foreign_keys=[role_id])
