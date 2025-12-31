"""
Role-Based Access Control (RBAC) Service - Basic Framework

This module provides basic RBAC functionality including:
- Role and permission management
- User role assignment
- Permission checking
- Basic policy enforcement

This can be extended later with Casbin integration for advanced policy management.
"""

import logging
from typing import List, Optional, Dict, Any, Set
from uuid import UUID, uuid4
from datetime import datetime

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models.user import User
from ..models.rbac import Role, Permission, user_roles

logger = logging.getLogger(__name__)


class RBACService:
    """Basic Role-Based Access Control service."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    # Role Management
    
    async def create_role(
        self,
        name: str,
        description: str,
        tenant_id: Optional[UUID] = None,
        permissions: Optional[List[str]] = None
    ) -> Role:
        """Create a new role."""
        # Check if role already exists
        existing_role = await self.get_role_by_name(name, tenant_id)
        if existing_role:
            raise ValueError(f"Role '{name}' already exists")
        
        role = Role(
            id=uuid4(),
            name=name,
            description=description,
            tenant_id=tenant_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        self.session.add(role)
        
        # Add permissions if provided
        if permissions:
            for perm_name in permissions:
                permission = await self.get_or_create_permission(perm_name)
                role.permissions.append(permission)
        
        await self.session.commit()
        await self.session.refresh(role)
        
        logger.info(f"Created role: {name} (tenant: {tenant_id})")
        return role
    
    async def get_role_by_name(self, name: str, tenant_id: Optional[UUID] = None) -> Optional[Role]:
        """Get role by name and tenant."""
        query = select(Role).where(
            Role.name == name,
            Role.tenant_id == tenant_id,
            Role.is_deleted == False
        ).options(selectinload(Role.permissions))
        
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_role_by_id(self, role_id: UUID) -> Optional[Role]:
        """Get role by ID."""
        query = select(Role).where(
            Role.id == role_id,
            Role.is_deleted == False
        ).options(selectinload(Role.permissions))
        
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def list_roles(self, tenant_id: Optional[UUID] = None) -> List[Role]:
        """List all roles for a tenant."""
        query = select(Role).where(
            Role.tenant_id == tenant_id,
            Role.is_deleted == False
        ).options(selectinload(Role.permissions))
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    # Permission Management
    
    async def create_permission(self, name: str, description: str) -> Permission:
        """Create a new permission."""
        # Check if permission already exists
        existing_permission = await self.get_permission_by_name(name)
        if existing_permission:
            raise ValueError(f"Permission '{name}' already exists")
        
        permission = Permission(
            id=uuid4(),
            name=name,
            description=description,
            created_at=datetime.utcnow()
        )
        
        self.session.add(permission)
        await self.session.commit()
        await self.session.refresh(permission)
        
        logger.info(f"Created permission: {name}")
        return permission
    
    async def get_permission_by_name(self, name: str) -> Optional[Permission]:
        """Get permission by name."""
        query = select(Permission).where(Permission.name == name)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_or_create_permission(self, name: str) -> Permission:
        """Get existing permission or create new one."""
        permission = await self.get_permission_by_name(name)
        if not permission:
            permission = await self.create_permission(name, f"Auto-created permission: {name}")
        return permission
    
    async def list_permissions(self) -> List[Permission]:
        """List all permissions."""
        query = select(Permission)
        result = await self.session.execute(query)
        return result.scalars().all()
    
    # User Role Assignment
    
    async def assign_role_to_user(
        self,
        user_id: UUID,
        role_id: UUID,
        assigned_by: Optional[UUID] = None
    ) -> bool:
        """Assign a role to a user."""
        # Get the user and role
        user = await self.session.get(User, user_id)
        if not user:
            raise ValueError("User not found")
        
        role = await self.session.get(Role, role_id)
        if not role:
            raise ValueError("Role not found")
        
        # Check if assignment already exists
        if role in user.roles:
            raise ValueError("User already has this role assigned")
        
        # Add the role to the user
        user.roles.append(role)
        await self.session.commit()
        
        logger.info(f"Assigned role {role_id} to user {user_id}")
        return True
    
    async def remove_role_from_user(self, user_id: UUID, role_id: UUID) -> bool:
        """Remove a role from a user."""
        # Get the user
        user = await self.session.get(User, user_id, options=[selectinload(User.roles)])
        if not user:
            return False
        
        # Find and remove the role
        role_to_remove = None
        for role in user.roles:
            if role.id == role_id:
                role_to_remove = role
                break
        
        if not role_to_remove:
            return False
        
        user.roles.remove(role_to_remove)
        await self.session.commit()
        
        logger.info(f"Removed role {role_id} from user {user_id}")
        return True
    
    async def get_user_roles(self, user_id: UUID) -> List[Role]:
        """Get all active roles for a user."""
        user = await self.session.get(
            User, 
            user_id, 
            options=[selectinload(User.roles).selectinload(Role.permissions)]
        )
        
        if not user:
            return []
        
        return [role for role in user.roles if not role.is_deleted]
    
    async def get_user_permissions(self, user_id: UUID) -> Set[str]:
        """Get all permissions for a user through their roles."""
        roles = await self.get_user_roles(user_id)
        permissions = set()
        
        for role in roles:
            for permission in role.permissions:
                permissions.add(permission.name)
        
        return permissions
    
    # Permission Checking
    
    async def user_has_permission(self, user_id: UUID, permission_name: str) -> bool:
        """Check if a user has a specific permission."""
        user_permissions = await self.get_user_permissions(user_id)
        return permission_name in user_permissions
    
    async def user_has_role(self, user_id: UUID, role_name: str, tenant_id: Optional[UUID] = None) -> bool:
        """Check if a user has a specific role."""
        user_roles = await self.get_user_roles(user_id)
        
        for role in user_roles:
            if role.name == role_name and role.tenant_id == tenant_id:
                return True
        
        return False
    
    async def user_has_any_role(self, user_id: UUID, role_names: List[str], tenant_id: Optional[UUID] = None) -> bool:
        """Check if a user has any of the specified roles."""
        for role_name in role_names:
            if await self.user_has_role(user_id, role_name, tenant_id):
                return True
        return False
    
    # System Administration
    
    async def is_system_admin(self, user_id: UUID) -> bool:
        """Check if a user is a system administrator."""
        user = await self.session.get(User, user_id)
        return user.is_system_admin if user else False
    
    async def is_tenant_admin(self, user_id: UUID, tenant_id: UUID) -> bool:
        """Check if a user is an admin for a specific tenant."""
        return await self.user_has_role(user_id, "tenant_admin", tenant_id)
    
    # Default Roles Setup
    
    async def setup_default_roles(self, tenant_id: Optional[UUID] = None):
        """Set up default roles for a tenant or system."""
        default_roles = [
            {
                "name": "system_admin",
                "description": "System administrator with full access",
                "permissions": [
                    "system.manage",
                    "tenant.create",
                    "tenant.delete",
                    "user.manage",
                    "role.manage"
                ]
            },
            {
                "name": "tenant_admin",
                "description": "Tenant administrator",
                "permissions": [
                    "tenant.manage",
                    "user.invite",
                    "user.manage",
                    "agent.create",
                    "agent.manage",
                    "workflow.create",
                    "workflow.manage"
                ]
            },
            {
                "name": "developer",
                "description": "Developer with agent and workflow creation rights",
                "permissions": [
                    "agent.create",
                    "agent.manage",
                    "workflow.create",
                    "workflow.manage",
                    "tool.create",
                    "tool.manage"
                ]
            },
            {
                "name": "user",
                "description": "Basic user with read access",
                "permissions": [
                    "agent.view",
                    "workflow.view",
                    "tool.view"
                ]
            }
        ]
        
        for role_data in default_roles:
            try:
                await self.create_role(
                    name=role_data["name"],
                    description=role_data["description"],
                    tenant_id=tenant_id,
                    permissions=role_data["permissions"]
                )
            except ValueError:
                # Role already exists, skip
                logger.info(f"Role {role_data['name']} already exists, skipping")
                continue
        
        logger.info(f"Default roles setup completed for tenant: {tenant_id}")


# Permission constants for easy reference
class Permissions:
    """Standard permission constants."""
    
    # System permissions
    SYSTEM_MANAGE = "system.manage"
    
    # Tenant permissions
    TENANT_CREATE = "tenant.create"
    TENANT_MANAGE = "tenant.manage"
    TENANT_DELETE = "tenant.delete"
    
    # User permissions
    USER_INVITE = "user.invite"
    USER_MANAGE = "user.manage"
    
    # Role permissions
    ROLE_MANAGE = "role.manage"
    
    # Agent permissions
    AGENT_CREATE = "agent.create"
    AGENT_MANAGE = "agent.manage"
    AGENT_VIEW = "agent.view"
    AGENT_EXECUTE = "agent.execute"
    
    # Workflow permissions
    WORKFLOW_CREATE = "workflow.create"
    WORKFLOW_MANAGE = "workflow.manage"
    WORKFLOW_VIEW = "workflow.view"
    WORKFLOW_EXECUTE = "workflow.execute"
    
    # Tool permissions
    TOOL_CREATE = "tool.create"
    TOOL_MANAGE = "tool.manage"
    TOOL_VIEW = "tool.view"
    TOOL_EXECUTE = "tool.execute"
    
    # Audit permissions
    AUDIT_READ = "audit.read"
    AUDIT_EXPORT = "audit.export"
    AUDIT_MANAGE = "audit.manage"


# Alias for backward compatibility
class StandardPermissions(Permissions):
    """Alias for Permissions class for backward compatibility."""
    pass


# Role constants for easy reference
class Roles:
    """Standard role constants."""
    
    SYSTEM_ADMIN = "system_admin"
    TENANT_ADMIN = "tenant_admin"
    DEVELOPER = "developer"
    USER = "user"


# Helper function for FastAPI dependency injection
async def require_permission(
    rbac_service: RBACService,
    user_id: UUID,
    permission_name: str,
    tenant_id: Optional[UUID] = None
) -> None:
    """
    Check if a user has the required permission.
    
    Raises HTTPException with 403 status if permission is not granted.
    """
    from fastapi import HTTPException, status
    
    # System admins have all permissions
    if await rbac_service.is_system_admin(user_id):
        return
    
    # Check specific permission
    has_permission = await rbac_service.user_has_permission(user_id, permission_name)
    
    if not has_permission:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User does not have permission: {permission_name}"
        )
    
    logger.warning(f"User {user_id} attempted unauthorized action: {permission_name}")