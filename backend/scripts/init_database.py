#!/usr/bin/env python3
"""Database initialization script for AI Agent Framework.

This script creates the initial database schema and seeds it with
system roles, permissions, and default data.
"""

import asyncio
import logging
import sys
import os
from typing import List

# Add the backend directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.database.connection import AsyncSessionLocal, create_tables as db_create_tables
from shared.models.base import Base
from shared.models.rbac import Role, Permission, ResourceType, ActionType, PermissionEffect
from shared.models.user import User, UserStatus, AuthProvider
from shared.models.tenant import Tenant, TenantStatus, TenantPlan
# Import all models to ensure they are registered with SQLAlchemy
import shared.models.agent  # noqa
import shared.models.workflow  # noqa
import shared.models.audit  # noqa

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def create_tables():
    """Create all database tables."""
    logger.info("Creating database tables...")
    await db_create_tables()
    logger.info("Database tables created successfully")


async def create_system_permissions() -> List[Permission]:
    """Create system permissions."""
    logger.info("Creating system permissions...")
    
    permissions_data = [
        # User management permissions
        ("user:create", "Create users", ResourceType.USER, ActionType.CREATE),
        ("user:read", "Read user information", ResourceType.USER, ActionType.READ),
        ("user:update", "Update user information", ResourceType.USER, ActionType.UPDATE),
        ("user:delete", "Delete users", ResourceType.USER, ActionType.DELETE),
        ("user:manage", "Manage users", ResourceType.USER, ActionType.MANAGE),
        
        # Agent management permissions
        ("agent:create", "Create agents", ResourceType.AGENT, ActionType.CREATE),
        ("agent:read", "Read agent information", ResourceType.AGENT, ActionType.READ),
        ("agent:update", "Update agent configuration", ResourceType.AGENT, ActionType.UPDATE),
        ("agent:delete", "Delete agents", ResourceType.AGENT, ActionType.DELETE),
        ("agent:execute", "Execute agents", ResourceType.AGENT, ActionType.EXECUTE),
        ("agent:deploy", "Deploy agents", ResourceType.AGENT, ActionType.DEPLOY),
        ("agent:manage", "Manage agents", ResourceType.AGENT, ActionType.MANAGE),
        
        # Workflow management permissions
        ("workflow:create", "Create workflows", ResourceType.WORKFLOW, ActionType.CREATE),
        ("workflow:read", "Read workflow information", ResourceType.WORKFLOW, ActionType.READ),
        ("workflow:update", "Update workflow configuration", ResourceType.WORKFLOW, ActionType.UPDATE),
        ("workflow:delete", "Delete workflows", ResourceType.WORKFLOW, ActionType.DELETE),
        ("workflow:execute", "Execute workflows", ResourceType.WORKFLOW, ActionType.EXECUTE),
        ("workflow:deploy", "Deploy workflows", ResourceType.WORKFLOW, ActionType.DEPLOY),
        ("workflow:manage", "Manage workflows", ResourceType.WORKFLOW, ActionType.MANAGE),
        
        # Tool management permissions
        ("tool:create", "Create tools", ResourceType.TOOL, ActionType.CREATE),
        ("tool:read", "Read tool information", ResourceType.TOOL, ActionType.READ),
        ("tool:update", "Update tool configuration", ResourceType.TOOL, ActionType.UPDATE),
        ("tool:delete", "Delete tools", ResourceType.TOOL, ActionType.DELETE),
        ("tool:execute", "Execute tools", ResourceType.TOOL, ActionType.EXECUTE),
        ("tool:manage", "Manage tools", ResourceType.TOOL, ActionType.MANAGE),
        
        # System administration permissions
        ("system:admin", "System administration", ResourceType.SYSTEM, ActionType.ADMIN),
        ("system:read", "System monitoring", ResourceType.SYSTEM, ActionType.READ),
        ("system:manage", "System management", ResourceType.SYSTEM, ActionType.MANAGE),
        
        # Audit and compliance permissions
        ("audit:read", "Read audit logs", ResourceType.AUDIT_LOG, ActionType.READ),
        ("audit:manage", "Manage audit logs", ResourceType.AUDIT_LOG, ActionType.MANAGE),
        
        # Role and permission management
        ("role:create", "Create roles", ResourceType.ROLE, ActionType.CREATE),
        ("role:read", "Read role information", ResourceType.ROLE, ActionType.READ),
        ("role:update", "Update role configuration", ResourceType.ROLE, ActionType.UPDATE),
        ("role:delete", "Delete roles", ResourceType.ROLE, ActionType.DELETE),
        ("role:manage", "Manage roles", ResourceType.ROLE, ActionType.MANAGE),
    ]
    
    permissions = []
    async with AsyncSessionLocal() as session:
        for name, description, resource_type, action in permissions_data:
            # Check if permission already exists
            from sqlalchemy import select
            query = select(Permission).where(Permission.name == name)
            result = await session.execute(query)
            existing = result.scalar_one_or_none()
            
            if existing:
                logger.info(f"Permission {name} already exists, skipping")
                permissions.append(existing)
                continue
                
            permission = Permission(
                name=name,
                description=description,
                resource_type=resource_type,
                action=action,
                effect=PermissionEffect.ALLOW
            )
            session.add(permission)
            permissions.append(permission)
            logger.info(f"Created permission: {name}")
        
        await session.commit()
    
    logger.info(f"Created {len(permissions)} system permissions")
    return permissions


async def create_system_roles(permissions: List[Permission]):
    """Create system roles with appropriate permissions."""
    logger.info("Creating system roles...")
    
    # Define role configurations
    role_configs = {
        "super_admin": {
            "display_name": "Super Administrator",
            "description": "Full system access with all permissions",
            "permissions": [p.name for p in permissions]  # All permissions
        },
        "admin": {
            "display_name": "Administrator", 
            "description": "System administrator with most permissions",
            "permissions": [
                "user:create", "user:read", "user:update", "user:manage",
                "agent:create", "agent:read", "agent:update", "agent:delete", "agent:execute", "agent:deploy", "agent:manage",
                "workflow:create", "workflow:read", "workflow:update", "workflow:delete", "workflow:execute", "workflow:deploy", "workflow:manage",
                "tool:create", "tool:read", "tool:update", "tool:delete", "tool:execute", "tool:manage",
                "system:read", "system:manage",
                "audit:read", "audit:manage",
                "role:read", "role:manage"
            ]
        },
        "developer": {
            "display_name": "Developer",
            "description": "Developer role with agent and workflow management permissions",
            "permissions": [
                "agent:create", "agent:read", "agent:update", "agent:execute", "agent:deploy",
                "workflow:create", "workflow:read", "workflow:update", "workflow:execute", "workflow:deploy",
                "tool:read", "tool:execute",
                "system:read"
            ]
        },
        "operator": {
            "display_name": "Operator",
            "description": "Operator role with execution and monitoring permissions",
            "permissions": [
                "agent:read", "agent:execute",
                "workflow:read", "workflow:execute",
                "tool:read", "tool:execute",
                "system:read"
            ]
        },
        "viewer": {
            "display_name": "Viewer",
            "description": "Read-only access to system resources",
            "permissions": [
                "agent:read",
                "workflow:read",
                "tool:read",
                "system:read"
            ]
        }
    }
    
    # Create permission lookup
    permission_lookup = {p.name: p for p in permissions}
    
    async with AsyncSessionLocal() as session:
        for role_name, config in role_configs.items():
            # Check if role already exists
            from sqlalchemy import select
            query = select(Role).where(Role.name == role_name)
            result = await session.execute(query)
            existing_role = result.scalar_one_or_none()
            
            if existing_role:
                logger.info(f"Role {role_name} already exists, skipping")
                continue
            
            # Create role
            role = Role(
                name=role_name,
                display_name=config["display_name"],
                description=config["description"]
            )
            
            # Add permissions to role
            for perm_name in config["permissions"]:
                if perm_name in permission_lookup:
                    role.permissions.append(permission_lookup[perm_name])
                else:
                    logger.warning(f"Permission {perm_name} not found for role {role_name}")
            
            session.add(role)
            logger.info(f"Created role: {role_name} with {len(role.permissions)} permissions")
        
        await session.commit()
    
    logger.info("System roles created successfully")


async def create_system_tenant() -> Tenant:
    """Create the system tenant for system-wide operations."""
    logger.info("Creating system tenant...")
    
    async with AsyncSessionLocal() as session:
        # Check if system tenant already exists
        from sqlalchemy import select
        query = select(Tenant).where(Tenant.slug == "system")
        result = await session.execute(query)
        existing_tenant = result.scalar_one_or_none()
        
        if existing_tenant:
            logger.info("System tenant already exists, skipping")
            return existing_tenant
        
        # Create system tenant
        system_tenant = Tenant(
            name="System Tenant",
            slug="system",
            display_name="System Tenant",
            description="System-wide tenant for administrative operations",
            primary_email="admin@localhost",
            status=TenantStatus.ACTIVE,
            plan=TenantPlan.ENTERPRISE,
            max_users=1000,
            max_agents=1000,
            max_workflows=1000,
            max_storage_gb=100,
            max_api_calls_per_month=1000000
        )
        
        session.add(system_tenant)
        await session.commit()
        await session.refresh(system_tenant)
        
        logger.info("System tenant created successfully")
        return system_tenant
async def create_default_admin_user(system_tenant: Tenant):
    """Create default admin user if none exists."""
    logger.info("Checking for admin users...")
    
    async with AsyncSessionLocal() as session:
        # Check if any super_admin users exist
        from sqlalchemy import select
        from shared.models.user import user_roles
        
        query = select(User).join(user_roles).join(Role).where(Role.name == "super_admin")
        result = await session.execute(query)
        existing_admin = result.scalar_one_or_none()
        
        if existing_admin:
            logger.info("Admin user already exists, skipping default admin creation")
            return
        
        # Create default admin user
        admin_user = User(
            username="admin",
            email="admin@localhost",
            first_name="System",
            last_name="Administrator",
            status=UserStatus.ACTIVE,
            auth_provider=AuthProvider.LOCAL,
            tenant_id=system_tenant.id
        )
        
        # Get super_admin role
        query = select(Role).where(Role.name == "super_admin")
        result = await session.execute(query)
        super_admin_role = result.scalar_one_or_none()
        
        if super_admin_role:
            admin_user.roles.append(super_admin_role)
        
        session.add(admin_user)
        await session.commit()
        
        logger.info("Created default admin user (username: admin)")
        logger.warning("IMPORTANT: Set a password for the admin user before production use!")


async def verify_database_setup():
    """Verify database setup is correct."""
    logger.info("Verifying database setup...")
    
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select, func
        
        # Count permissions
        perm_count = await session.scalar(select(func.count(Permission.name)))
        logger.info(f"Total permissions: {perm_count}")
        
        # Count roles
        role_count = await session.scalar(select(func.count(Role.name)))
        logger.info(f"Total roles: {role_count}")
        
        # Count users
        user_count = await session.scalar(select(func.count(User.id)))
        logger.info(f"Total users: {user_count}")
        
        # Verify admin user has super_admin role
        from shared.models.user import user_roles
        query = select(User).join(user_roles).join(Role).where(
            User.username == "admin",
            Role.name == "super_admin"
        )
        admin_user = await session.scalar(query)
        if admin_user:
            logger.info("✓ Admin user has super_admin role")
        else:
            logger.warning("✗ Admin user does not have super_admin role")
    
    logger.info("Database verification complete")


async def main():
    """Main initialization function."""
    logger.info("Starting database initialization...")
    
    try:
        # Create tables
        await create_tables()
        
        # Create system tenant
        system_tenant = await create_system_tenant()
        
        # Create permissions
        permissions = await create_system_permissions()
        
        # Create roles
        await create_system_roles(permissions)
        
        # Create default admin user
        await create_default_admin_user(system_tenant)
        
        # Verify setup
        await verify_database_setup()
        
        logger.info("Database initialization completed successfully!")
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())