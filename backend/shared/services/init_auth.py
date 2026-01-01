"""
Authentication and RBAC Initialization Service

This module provides functions to initialize the authentication system
with default roles, permissions, and system users.
"""

import logging
from typing import List, Dict, Any
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from .auth import AuthService
from .rbac import RBACService, StandardPermissions, StandardRoles
from ..models.rbac import Permission, Role

logger = logging.getLogger(__name__)


class AuthInitService:
    """Service for initializing authentication and RBAC system."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.auth_service = AuthService(session)
        self.rbac_service = RBACService(session)
    
    async def initialize_permissions(self) -> List[Permission]:
        """Initialize standard permissions."""
        permissions_data = [
            # System permissions
            {"name": StandardPermissions.SYSTEM_ADMIN, "resource": "system", "action": "admin", "description": "Full system administration"},
            {"name": StandardPermissions.SYSTEM_MANAGE, "resource": "system", "action": "manage", "description": "System management"},
            
            # User permissions
            {"name": StandardPermissions.USER_CREATE, "resource": "user", "action": "create", "description": "Create users"},
            {"name": StandardPermissions.USER_READ, "resource": "user", "action": "read", "description": "View user information"},
            {"name": StandardPermissions.USER_UPDATE, "resource": "user", "action": "update", "description": "Update user profiles"},
            {"name": StandardPermissions.USER_DELETE, "resource": "user", "action": "delete", "description": "Delete users"},
            {"name": StandardPermissions.USER_MANAGE, "resource": "user", "action": "manage", "description": "Full user management"},
            {"name": StandardPermissions.USER_INVITE, "resource": "user", "action": "invite", "description": "Invite users"},
            
            # Role permissions
            {"name": StandardPermissions.ROLE_CREATE, "resource": "role", "action": "create", "description": "Create roles"},
            {"name": StandardPermissions.ROLE_READ, "resource": "role", "action": "read", "description": "View role information"},
            {"name": StandardPermissions.ROLE_UPDATE, "resource": "role", "action": "update", "description": "Update roles"},
            {"name": StandardPermissions.ROLE_DELETE, "resource": "role", "action": "delete", "description": "Delete roles"},
            {"name": StandardPermissions.ROLE_MANAGE, "resource": "role", "action": "manage", "description": "Full role management"},
            {"name": StandardPermissions.ROLE_ASSIGN, "resource": "role", "action": "assign", "description": "Assign roles to users"},
            
            # Agent permissions
            {"name": StandardPermissions.AGENT_CREATE, "resource": "agent", "action": "create", "description": "Create AI agents"},
            {"name": StandardPermissions.AGENT_READ, "resource": "agent", "action": "read", "description": "View agent information"},
            {"name": StandardPermissions.AGENT_UPDATE, "resource": "agent", "action": "update", "description": "Update agent configurations"},
            {"name": StandardPermissions.AGENT_DELETE, "resource": "agent", "action": "delete", "description": "Delete agents"},
            {"name": StandardPermissions.AGENT_EXECUTE, "resource": "agent", "action": "execute", "description": "Execute agents"},
            {"name": StandardPermissions.AGENT_MANAGE, "resource": "agent", "action": "manage", "description": "Full agent management"},
            
            # Workflow permissions
            {"name": StandardPermissions.WORKFLOW_CREATE, "resource": "workflow", "action": "create", "description": "Create workflows"},
            {"name": StandardPermissions.WORKFLOW_READ, "resource": "workflow", "action": "read", "description": "View workflow information"},
            {"name": StandardPermissions.WORKFLOW_UPDATE, "resource": "workflow", "action": "update", "description": "Update workflows"},
            {"name": StandardPermissions.WORKFLOW_DELETE, "resource": "workflow", "action": "delete", "description": "Delete workflows"},
            {"name": StandardPermissions.WORKFLOW_EXECUTE, "resource": "workflow", "action": "execute", "description": "Execute workflows"},
            {"name": StandardPermissions.WORKFLOW_MANAGE, "resource": "workflow", "action": "manage", "description": "Full workflow management"},
            
            # Tool permissions
            {"name": StandardPermissions.TOOL_CREATE, "resource": "tool", "action": "create", "description": "Create custom tools"},
            {"name": StandardPermissions.TOOL_READ, "resource": "tool", "action": "read", "description": "View tool information"},
            {"name": StandardPermissions.TOOL_UPDATE, "resource": "tool", "action": "update", "description": "Update tools"},
            {"name": StandardPermissions.TOOL_DELETE, "resource": "tool", "action": "delete", "description": "Delete tools"},
            {"name": StandardPermissions.TOOL_EXECUTE, "resource": "tool", "action": "execute", "description": "Execute tools"},
            {"name": StandardPermissions.TOOL_MANAGE, "resource": "tool", "action": "manage", "description": "Full tool management"},
            
            # Audit permissions
            {"name": StandardPermissions.AUDIT_READ, "resource": "audit", "action": "read", "description": "View audit logs"},
            {"name": StandardPermissions.AUDIT_EXPORT, "resource": "audit", "action": "export", "description": "Export audit data"},
            {"name": StandardPermissions.AUDIT_MANAGE, "resource": "audit", "action": "manage", "description": "Full audit management"},
        ]
        
        created_permissions = []
        
        for perm_data in permissions_data:
            try:
                permission = await self.rbac_service.create_permission(
                    name=perm_data["name"],
                    description=perm_data["description"]
                )
                # Update resource and action fields
                permission.resource = perm_data["resource"]
                permission.action = perm_data["action"]
                permission.is_system_permission = True
                
                created_permissions.append(permission)
                logger.info(f"Created permission: {perm_data['name']}")
                
            except ValueError:
                # Permission already exists
                logger.info(f"Permission already exists: {perm_data['name']}")
                existing_permission = await self.rbac_service.get_permission_by_name(perm_data["name"])
                if existing_permission:
                    created_permissions.append(existing_permission)
        
        await self.session.commit()
        return created_permissions
    
    async def initialize_roles(self) -> List[Role]:
        """Initialize standard roles."""
        roles_data = [
            {
                "name": StandardRoles.SYSTEM_ADMIN,
                "description": "System administrator with full access to all features",
                "permissions": [
                    StandardPermissions.SYSTEM_ADMIN,
                    StandardPermissions.SYSTEM_MANAGE,
                    StandardPermissions.USER_CREATE,
                    StandardPermissions.USER_READ,
                    StandardPermissions.USER_UPDATE,
                    StandardPermissions.USER_DELETE,
                    StandardPermissions.USER_MANAGE,
                    StandardPermissions.USER_INVITE,
                    StandardPermissions.ROLE_CREATE,
                    StandardPermissions.ROLE_READ,
                    StandardPermissions.ROLE_UPDATE,
                    StandardPermissions.ROLE_DELETE,
                    StandardPermissions.ROLE_MANAGE,
                    StandardPermissions.ROLE_ASSIGN,
                    StandardPermissions.AUDIT_READ,
                    StandardPermissions.AUDIT_EXPORT,
                    StandardPermissions.AUDIT_MANAGE,
                ]
            },
            {
                "name": StandardRoles.DEVELOPER,
                "description": "Developer with agent and workflow creation capabilities",
                "permissions": [
                    StandardPermissions.USER_READ,
                    StandardPermissions.AGENT_CREATE,
                    StandardPermissions.AGENT_READ,
                    StandardPermissions.AGENT_UPDATE,
                    StandardPermissions.AGENT_DELETE,
                    StandardPermissions.AGENT_EXECUTE,
                    StandardPermissions.WORKFLOW_CREATE,
                    StandardPermissions.WORKFLOW_READ,
                    StandardPermissions.WORKFLOW_UPDATE,
                    StandardPermissions.WORKFLOW_DELETE,
                    StandardPermissions.WORKFLOW_EXECUTE,
                    StandardPermissions.TOOL_CREATE,
                    StandardPermissions.TOOL_READ,
                    StandardPermissions.TOOL_UPDATE,
                    StandardPermissions.TOOL_DELETE,
                    StandardPermissions.TOOL_EXECUTE,
                ]
            },
            {
                "name": StandardRoles.USER,
                "description": "Regular user with execution capabilities",
                "permissions": [
                    StandardPermissions.AGENT_READ,
                    StandardPermissions.AGENT_EXECUTE,
                    StandardPermissions.WORKFLOW_READ,
                    StandardPermissions.WORKFLOW_EXECUTE,
                    StandardPermissions.TOOL_READ,
                    StandardPermissions.TOOL_EXECUTE,
                ]
            },
            {
                "name": StandardRoles.VIEWER,
                "description": "Read-only access to agents and workflows",
                "permissions": [
                    StandardPermissions.AGENT_READ,
                    StandardPermissions.WORKFLOW_READ,
                    StandardPermissions.TOOL_READ,
                ]
            }
        ]
        
        created_roles = []
        
        for role_data in roles_data:
            try:
                role = await self.rbac_service.create_role(
                    name=role_data["name"],
                    description=role_data["description"],
                    permissions=role_data["permissions"]
                )
                
                # Mark system roles
                role.is_system_role = True
                
                created_roles.append(role)
                logger.info(f"Created role: {role_data['name']}")
                
            except ValueError:
                # Role already exists
                logger.info(f"Role already exists: {role_data['name']}")
                existing_role = await self.rbac_service.get_role_by_name(role_data["name"])
                if existing_role:
                    created_roles.append(existing_role)
        
        await self.session.commit()
        return created_roles
    
    async def create_system_admin(
        self,
        email: str = "admin@example.com",
        password: str = "admin123",
        full_name: str = "System Administrator"
    ):
        """Create the initial system administrator user."""
        try:
            # Create admin user
            admin_user = await self.auth_service.register_user(
                email=email,
                password=password,
                full_name=full_name
            )
            
            # Mark as system admin
            admin_user.is_system_admin = True
            
            # Assign system admin role
            system_admin_role = await self.rbac_service.get_role_by_name(StandardRoles.SYSTEM_ADMIN)
            if system_admin_role:
                await self.rbac_service.assign_role_to_user(
                    user_id=admin_user.id,
                    role_id=system_admin_role.id
                )
            
            await self.session.commit()
            
            logger.info(f"Created system administrator: {email}")
            return admin_user
            
        except ValueError as e:
            logger.info(f"System administrator already exists: {e}")
            return await self.auth_service.get_user_by_email(email)
    
    async def initialize_auth_system(
        self,
        admin_email: str = "admin@example.com",
        admin_password: str = "admin123"
    ):
        """Initialize the complete authentication system."""
        logger.info("Initializing authentication system...")
        
        # 1. Initialize permissions
        logger.info("Creating standard permissions...")
        await self.initialize_permissions()
        
        # 2. Initialize system roles
        logger.info("Creating system roles...")
        await self.initialize_roles()
        
        # 3. Create system administrator
        logger.info("Creating system administrator...")
        await self.create_system_admin(
            email=admin_email,
            password=admin_password
        )
        
        logger.info("Authentication system initialization completed!")


async def initialize_auth_system(session: AsyncSession):
    """Convenience function to initialize the auth system."""
    init_service = AuthInitService(session)
    await init_service.initialize_auth_system()