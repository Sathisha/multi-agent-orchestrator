"""
Permission Middleware for RBAC

This module provides FastAPI dependencies for permission checking.
"""

from typing import Callable
from uuid import UUID
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.connection import get_async_db
from ..services.rbac import RBACService
from ..api.auth import get_current_user


def require_permission(permission_name: str):
    """
    FastAPI dependency factory that checks if the current user has a specific permission.
    
    Args:
        permission_name: The permission to check (e.g., "agent.view", "agent.manage")
    
    Returns:
        A FastAPI dependency function that validates permission
    
    Raises:
        HTTPException: 403 Forbidden if user lacks permission
    
    Example:
        @router.get("/agents", dependencies=[Depends(require_permission("agent.view"))])
        async def list_agents(...):
            ...
    """
    async def permission_checker(
        current_user = Depends(get_current_user),
        db: AsyncSession = Depends(get_async_db)
    ):
        # System admins have all permissions
        if getattr(current_user, 'is_system_admin', False):
            return current_user
        
        # Check if user has the required permission
        rbac_service = RBACService(db)
        has_permission = await rbac_service.user_has_permission(
            current_user.id,
            permission_name
        )
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: requires '{permission_name}' permission"
            )
        
        return current_user
    
    return permission_checker


def require_any_permission(*permission_names: str):
    """
    FastAPI dependency factory that checks if user has ANY of the specified permissions.
    
    Args:
        *permission_names: Variable number of permissions to check
    
    Returns:
        A FastAPI dependency function that validates permissions
    """
    async def permission_checker(
        current_user = Depends(get_current_user),
        db: AsyncSession = Depends(get_async_db)
    ):
        # System admins have all permissions
        if getattr(current_user, 'is_system_admin', False):
            return current_user
        
        # Check if user has any of the required permissions
        rbac_service = RBACService(db)
        
        for perm_name in permission_names:
            has_permission = await rbac_service.user_has_permission(
                current_user.id,
                perm_name
            )
            if has_permission:
                return current_user
        
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission denied: requires one of {permission_names}"
        )
    
    return permission_checker
