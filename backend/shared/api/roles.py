from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from shared.database.connection import get_async_db
from shared.api.auth import get_current_user
from shared.models.rbac import Role
from shared.models.user import User
from shared.schemas.role import RoleResponse

router = APIRouter(prefix="/auth/roles", tags=["Role Management"])

@router.get("/", response_model=List[RoleResponse])
async def list_roles(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """List all available roles (authenticated users)."""
    # Load roles with permissions
    stmt = select(Role).options(selectinload(Role.permissions))
    result = await db.execute(stmt)
    roles = result.scalars().all()
    
    return [RoleResponse.model_validate(role) for role in roles]

@router.get("/{role_id}", response_model=RoleResponse)
async def get_role(
    role_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """Get role details."""
    stmt = select(Role).options(selectinload(Role.permissions)).where(Role.id == role_id)
    result = await db.execute(stmt)
    role = result.scalars().first()
    
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
        
    return RoleResponse.model_validate(role)
