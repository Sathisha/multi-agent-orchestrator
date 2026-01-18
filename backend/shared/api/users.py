from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.orm import selectinload

from shared.database.connection import get_async_db
from shared.api.auth import get_current_user
from shared.models.user import User
from shared.models.rbac import Role, UserRole
from shared.schemas.user import UserResponse, UserCreateRequest, UserUpdateRequest, UserRoleAssignRequest, RoleResponse
from shared.decorators.permissions import require_super_admin
from shared.services.auth import AuthService

router = APIRouter(prefix="/users", tags=["User Management"])

@router.get("/", response_model=List[UserResponse])
@require_super_admin
async def list_users(
    skip: int = 0, 
    limit: int = 100,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """List all users (super admin only)."""
    stmt = select(User).options(
        selectinload(User.roles).selectinload(UserRole.role)
    ).offset(skip).limit(limit)
    
    result = await db.execute(stmt)
    users = result.scalars().all()
    
    # Transform to response model
    response = []
    for user in users:
        user_roles = []
        for ur in user.roles:
            if ur.role:
                user_roles.append(RoleResponse(
                    id=ur.role.id,
                    name=ur.role.name,
                    display_name=ur.role.display_name,
                    permission_level=ur.role.permission_level,
                    is_system_role=ur.role.is_system_role,
                    description=ur.role.description
                ))
                
        response.append(UserResponse(
            id=user.id,
            email=user.email,
            username=user.username,
            full_name=user.full_name,
            is_superuser=user.is_superuser,
            is_active=user.is_active,
            status=user.status,
            roles=user_roles,
            created_at=user.created_at,
            updated_at=user.updated_at,
            last_login_at=user.last_login_at
        ))
        
    return response

@router.post("/", response_model=UserResponse)
@require_super_admin
async def create_user(
    user_data: UserCreateRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new user (super admin only)."""
    # Check if user exists
    stmt = select(User).where(User.email == user_data.email)
    result = await db.execute(stmt)
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Email already registered")
        
    # Create user
    auth_service = AuthService()
    hashed_password = auth_service.get_password_hash(user_data.password)
    
    new_user = User(
        email=user_data.email,
        username=user_data.username or user_data.email.split('@')[0],
        hashed_password=hashed_password,
        full_name=user_data.full_name,
        status=user_data.status,
        is_active=True
    )
    
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    # Assign roles if provided
    if user_data.role_ids:
        for role_id in user_data.role_ids:
            user_role = UserRole(user_id=new_user.id, role_id=role_id, assigned_by=current_user.id)
            db.add(user_role)
        await db.commit()
    
    # Reload with roles
    stmt = select(User).options(
        selectinload(User.roles).selectinload(UserRole.role)
    ).where(User.id == new_user.id)
    result = await db.execute(stmt)
    user = result.scalars().first()
    
    # Transform response (simplified logic)
    user_roles = []
    for ur in user.roles:
        if ur.role:
            user_roles.append(RoleResponse.model_validate(ur.role))
            
    return UserResponse(
        id=user.id,
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        is_superuser=user.is_superuser,
        is_active=user.is_active,
        status=user.status,
        roles=user_roles,
        created_at=user.created_at,
        updated_at=user.updated_at,
        last_login_at=user.last_login_at
    )

@router.get("/{user_id}", response_model=UserResponse)
@require_super_admin
async def get_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """Get user details (super admin only)."""
    stmt = select(User).options(
        selectinload(User.roles).selectinload(UserRole.role)
    ).where(User.id == user_id)
    
    result = await db.execute(stmt)
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    user_roles = []
    for ur in user.roles:
        if ur.role:
            user_roles.append(RoleResponse.model_validate(ur.role))
            
    return UserResponse(
        id=user.id,
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        is_superuser=user.is_superuser,
        is_active=user.is_active,
        status=user.status,
        roles=user_roles,
        created_at=user.created_at,
        updated_at=user.updated_at,
        last_login_at=user.last_login_at
    )

@router.put("/{user_id}", response_model=UserResponse)
@require_super_admin
async def update_user(
    user_id: UUID,
    user_data: UserUpdateRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """Update user (super admin only)."""
    stmt = select(User).options(
        selectinload(User.roles).selectinload(UserRole.role)
    ).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    if user_data.email:
        user.email = user_data.email
    if user_data.full_name:
        user.full_name = user_data.full_name
    if user_data.status:
        user.status = user_data.status
    if user_data.is_active is not None:
        user.is_active = user_data.is_active
        
    # Handle role updates if provided (Full replacement)
    if user_data.role_ids is not None:
        # Remove existing roles
        delete_stmt = delete(UserRole).where(UserRole.user_id == user_id)
        await db.execute(delete_stmt)
        
        # Add new roles
        for role_id in user_data.role_ids:
            user_role = UserRole(user_id=user.id, role_id=role_id, assigned_by=current_user.id)
            db.add(user_role)
            
    await db.commit()
    await db.refresh(user)
    
    # Creating response manually to ensure roles are loaded
    stmt = select(User).options(
        selectinload(User.roles).selectinload(UserRole.role)
    ).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalars().first()

    user_roles = []
    for ur in user.roles:
        if ur.role:
            user_roles.append(RoleResponse.model_validate(ur.role))
            
    return UserResponse(
        id=user.id,
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        is_superuser=user.is_superuser,
        is_active=user.is_active,
        status=user.status,
        roles=user_roles,
        created_at=user.created_at,
        updated_at=user.updated_at,
        last_login_at=user.last_login_at
    )

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
@require_super_admin
async def delete_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """Delete user (super admin only)."""
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    if user.is_superuser:
        raise HTTPException(status_code=400, detail="Cannot delete superuser")
        
    await db.delete(user)
    await db.commit()

@router.post("/{user_id}/roles/{role_id}")
@require_super_admin
async def assign_user_role(
    user_id: UUID,
    role_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """Assign a role to a user."""
    # Check if role is already assigned
    stmt = select(UserRole).where(UserRole.user_id == user_id, UserRole.role_id == role_id)
    result = await db.execute(stmt)
    if result.scalars().first():
        return {"message": "Role already assigned"}
        
    user_role = UserRole(user_id=user_id, role_id=role_id, assigned_by=current_user.id)
    db.add(user_role)
    await db.commit()
    
    return {"message": "Role assigned successfully"}

@router.delete("/{user_id}/roles/{role_id}")
@require_super_admin
async def revoke_user_role(
    user_id: UUID,
    role_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """Revoke a role from a user."""
    stmt = delete(UserRole).where(UserRole.user_id == user_id, UserRole.role_id == role_id)
    result = await db.execute(stmt)
    
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Role assignment not found")
        
    await db.commit()
    return {"message": "Role revoked successfully"}

@router.get("/{user_id}/roles", response_model=List[RoleResponse])
@require_super_admin
async def get_user_roles(
    user_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """Get roles assigned to a user."""
    stmt = select(UserRole).options(selectinload(UserRole.role)).where(UserRole.user_id == user_id)
    result = await db.execute(stmt)
    user_roles = result.scalars().all()
    
    return [RoleResponse.model_validate(ur.role) for ur in user_roles if ur.role]
