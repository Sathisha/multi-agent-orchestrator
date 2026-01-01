from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum

from sqlalchemy import String, Boolean, DateTime, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.models.base import SystemEntity

class UserStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"

class AuthProvider(str, Enum):
    LOCAL = "local"
    GOOGLE = "google"
    GITHUB = "github"

class User(SystemEntity):
    __tablename__ = "users"
    
    username: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    
    status: Mapped[str] = mapped_column(String(50), nullable=False, default=UserStatus.ACTIVE, index=True)
    auth_provider: Mapped[str] = mapped_column(String(50), nullable=False, default=AuthProvider.LOCAL)
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    user_metadata: Mapped[Dict[str, Any]] = mapped_column("user_metadata", JSONB, nullable=True, server_default=text("'{}'::jsonb"))
    
    # Relationships
    roles = relationship("UserRole", back_populates="user", cascade="all, delete-orphan")
    # tenants = relationship("TenantUser", back_populates="user")
    
    def has_permission(self, resource_type: str, action: str) -> bool:
        """Check if user has permission."""
        # This needs full implementation with roles and permissions
        for user_role in self.roles:
            role = user_role.role
            for permission in role.permissions:
                if permission.resource == resource_type and permission.action == action:
                    return True
        return False
