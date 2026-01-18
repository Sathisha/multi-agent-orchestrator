"""Permission decorators for FastAPI endpoints."""

import logging
from typing import Optional
from functools import wraps
from uuid import UUID

from fastapi import HTTPException,status, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ..services.permission_service import PermissionService
from ..models.user import User

logger = logging.getLogger(__name__)


def require_permission(resource_type: str, action: str, resource_id_param: Optional[str] = None):
    """
    Decorator to enforce permission checks on endpoints.
    
    Args:
        resource_type: Type of resource ('agent', 'workflow', 'user', etc.)
        action: Action being performed ('view', 'execute', 'modify', 'delete')
        resource_id_param: Name of the path/query parameter containing the resource ID
                          If None, only checks global permissions
    
    Example:
        @router.post("/agents/{agent_id}/execute")
        @require_permission("agent", "execute", "agent_id")
        async def execute_agent(agent_id: UUID, current_user: User = Depends(...)):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request and current_user from arguments
            request: Optional[Request] = None
            current_user: Optional[User] = None
            db: Optional[AsyncSession] = None
            
            # Find request, user, and db session in kwargs
            for key, value in kwargs.items():
                if isinstance(value, Request):
                    request = value
                elif isinstance(value, User):
                    current_user = value
                elif isinstance(value, AsyncSession):
                    db = value
            
            # Also check args (for positional parameters)
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                elif isinstance(arg, User):
                    current_user = arg
                elif isinstance(arg, AsyncSession):
                    db = arg
            
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            if not db:
                # Try to get from request state
                if request and hasattr(request.state, 'db'):
                    db = request.state.db
                else:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Database session not available"
                    )
            
            # Extract resource_id from path parameters if specified
            resource_id: Optional[UUID] = None
            if resource_id_param:
                resource_id = kwargs.get(resource_id_param)
                if not resource_id:
                    # Try to get from request path params
                    if request:
                        resource_id = request.path_params.get(resource_id_param)
            
            # Check permission
            permission_service = PermissionService(db)
            has_perm = await permission_service.has_permission(
                user=current_user,
                resource_type=resource_type,
                action=action,
                resource_id=resource_id
            )
            
            if not has_perm:
                logger.warning(
                    f"Permission denied for user {current_user.id} - "
                    f"Resource: {resource_type}, Action: {action}, ID: {resource_id}"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient permissions to {action} {resource_type}"
                )
            
            # Permission granted, execute the endpoint
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def require_super_admin(func):
    """
    Decorator to require super admin access.
    
    Example:
        @router.post("/users")
        @require_super_admin
        async def create_user(current_user: User = Depends(...)):
            ...
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Extract current_user from arguments
        current_user: Optional[User] = None
        
        for key, value in kwargs.items():
            if isinstance(value, User):
                current_user = value
                break
        
        if not current_user:
            for arg in args:
                if isinstance(arg, User):
                    current_user = arg
                    break
        
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        if not (current_user.is_superuser or current_user.is_system_admin):
            logger.warning(
                f"Super admin access denied for user {current_user.id}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Super admin access required"
            )
        
        return await func(*args, **kwargs)
    
    return wrapper
