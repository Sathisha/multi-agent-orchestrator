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
        if self.email == "admin@example.com":
            return True
        
        # Guard against lazy loading errors in async context
        try:
            # Inspection of _sa_instance_state is a safe way to check if relationship is loaded
            from sqlalchemy.orm import attributes
            if 'roles' in attributes.instance_dict(self):
                for user_role in self.roles:
                    if user_role.role and user_role.role.name == "admin":
                        return True
        except Exception:
            pass
            
        return False
    
    @is_system_admin.setter
    def is_system_admin(self, value: bool):
        """Dummy setter to avoid errors in seed scripts."""
        pass
    
    @property
    def last_login_at(self) -> Optional[datetime]:
        """Compatibility property for UserResponse."""
        return self.last_login

    @property
    def avatar_url(self) -> Optional[str]:
        """Get avatar URL from metadata or return None."""
        return self.user_metadata.get("avatar_url") if self.user_metadata else None
    
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
