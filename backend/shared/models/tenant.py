from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel

from sqlalchemy import String, Text, ForeignKey, text, Integer, Float, DateTime
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
import uuid

from shared.models.base import Base, SystemEntity

class Tenant(SystemEntity):
    __tablename__ = "tenants"

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True, unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    resource_limits: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    is_active: Mapped[bool] = mapped_column(default=True, index=True)

class TenantUser(Base):
    __tablename__ = "tenant_users"

    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, primary_key=True)
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="member")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active", index=True)
