import uuid
from typing import Optional, Dict, Any
from datetime import datetime

from sqlalchemy import String, Boolean, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import text

from shared.models.base import SystemEntity


class UserStatus:
    """User status constants."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


class AuthProvider:
    """Authentication provider constants."""
    LOCAL = "local"
    OAUTH = "oauth"
    SAML = "saml"


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
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    user_metadata: Mapped[Dict[str, Any]] = mapped_column("user_metadata", JSONB, nullable=True, server_default=text("'{}'::jsonb"))
    
    # Relationships - specify foreign_keys to avoid ambiguity with UserRole.assigned_by
    roles = relationship("UserRole", back_populates="user", cascade="all, delete-orphan", foreign_keys="[UserRole.user_id]")
    
    @property
    def full_name(self) -> str:
        """Get user's full name from first_name and last_name."""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        elif self.last_name:
            return self.last_name
        return self.email.split('@')[0]  # Fallback to email username
    
    @property
    def is_system_admin(self) -> bool:
        """Check if user has system admin role."""
        # Check is_superuser flag first
        if self.is_superuser:
            return True
            
        # Backward compatibility: admin@example.com is always super admin
        if self.email == "admin@example.com":
            return True
        
        # Guard against lazy loading errors in async context
        try:
            # Inspection of _sa_instance_state is a safe way to check if relationship is loaded
            from sqlalchemy.orm import attributes
            if 'roles' in attributes.instance_dict(self):
                for user_role in self.roles:
                    # Check for super_admin or admin role
                    if user_role.role and user_role.role.name in ("super_admin", "admin"):
                        return True
        except Exception:
            pass
            
        return False
    
    def has_permission(self, permission: str) -> bool:
        """
        Check if user has a specific permission.
        
        This is a placeholder. Use PermissionService for actual permission checks.
        """
        # Super admins have all permissions
        if self.is_system_admin:
            return True
            
        # TODO: Implement actual permission checking via PermissionService
        return False
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, username={self.username})>"
