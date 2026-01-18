from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.connection import get_async_db
from shared.api.auth import get_current_user
from shared.models.user import User
from shared.services.permission_service import PermissionService
from shared.decorators.permissions import require_permission
from shared.schemas.user import RoleResponse
from pydantic import BaseModel

class WorkflowRoleAssignRequest(BaseModel):
    role_id: UUID
    access_type: str  # 'view', 'execute', 'modify'

class WorkflowRoleResponse(BaseModel):
    role_id: UUID
    role_name: str
    access_type: str
    
    class Config:
        from_attributes = True

router = APIRouter(prefix="/workflows", tags=["Workflow RBAC"])

@router.post("/{workflow_id}/roles")
@require_permission(resource_type="workflow", action="modify", resource_id_param="workflow_id")
async def assign_workflow_role(
    workflow_id: UUID,
    role_assignment: WorkflowRoleAssignRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """Assign a role to a workflow."""
    perm_service = PermissionService(db)
    
    assignment = await perm_service.assign_resource_role(
        resource_type="workflow",
        resource_id=workflow_id,
        role_id=role_assignment.role_id,
        access_type=role_assignment.access_type,
        created_by=current_user.id
    )
    
    return WorkflowRoleResponse(
        role_id=assignment.role_id,
        role_name=assignment.role.name if assignment.role else "Unknown",
        access_type=assignment.access_type
    )

@router.get("/{workflow_id}/roles")
@require_permission(resource_type="workflow", action="view", resource_id_param="workflow_id")
async def list_workflow_roles(
    workflow_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """List roles assigned to a workflow."""
    perm_service = PermissionService(db)
    roles_data = await perm_service.get_resource_roles("workflow", workflow_id)
    return [WorkflowRoleResponse(**r) for r in roles_data]

@router.delete("/{workflow_id}/roles/{role_id}")
@require_permission(resource_type="workflow", action="modify", resource_id_param="workflow_id")
async def revoke_workflow_role(
    workflow_id: UUID,
    role_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """Remove a role from a workflow."""
    perm_service = PermissionService(db)
    success = await perm_service.revoke_resource_role("workflow", workflow_id, role_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Role assignment not found")
    
    return {"message": "Role revoked successfully"}
