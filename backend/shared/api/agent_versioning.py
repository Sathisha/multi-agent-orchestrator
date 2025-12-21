"""Agent Versioning API endpoints."""

from typing import List, Optional, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from ..services.agent_versioning import AgentVersioningService
from ..middleware.tenant import get_tenant_aware_session
from ..models.agent import AgentResponse

router = APIRouter(prefix="/api/v1/agents", tags=["agent-versioning"])


class CreateVersionRequest(BaseModel):
    """Request model for creating a new agent version."""
    
    version: str = Field(..., description="Version string (e.g., '1.1.0')")
    changes: Optional[Dict[str, Any]] = Field(None, description="Changes to apply to the new version")


class RollbackRequest(BaseModel):
    """Request model for rolling back to a version."""
    
    target_version: str = Field(..., description="Version to rollback to")


class VersionComparisonResponse(BaseModel):
    """Response model for version comparison."""
    
    version1: str = Field(..., description="First version")
    version2: str = Field(..., description="Second version")
    differences: Dict[str, Any] = Field(..., description="Differences between versions")
    has_changes: bool = Field(..., description="Whether there are any changes")


class VersionHistoryEntry(BaseModel):
    """Model for version history entry."""
    
    id: UUID = Field(..., description="Version ID")
    version: str = Field(..., description="Version string")
    created_at: str = Field(..., description="Creation timestamp")
    created_by: Optional[str] = Field(None, description="Creator")
    status: str = Field(..., description="Version status")
    is_current: bool = Field(..., description="Whether this is the current version")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Version metadata")


@router.post("/{agent_id}/versions", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_agent_version(
    agent_id: UUID,
    request: CreateVersionRequest,
    session_and_context = Depends(get_tenant_aware_session),
    current_user: Dict[str, Any] = Depends(lambda: {"user_id": "system"})  # TODO: Replace with actual auth
):
    """Create a new version of an agent."""
    session, tenant_context = session_and_context
    
    if not tenant_context:
        raise HTTPException(status_code=400, detail="Tenant context required")
    
    service = AgentVersioningService(session, tenant_context.tenant_id)
    
    try:
        new_version = await service.create_version(
            agent_id=str(agent_id),
            version=request.version,
            changes=request.changes,
            created_by=current_user["user_id"]
        )
        return AgentResponse.from_orm(new_version)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{agent_id}/versions", response_model=List[AgentResponse])
async def list_agent_versions(
    agent_id: UUID,
    session_and_context = Depends(get_tenant_aware_session)
):
    """List all versions of an agent."""
    session, tenant_context = session_and_context
    
    if not tenant_context:
        raise HTTPException(status_code=400, detail="Tenant context required")
    
    service = AgentVersioningService(session, tenant_context.tenant_id)
    
    versions = await service.get_agent_versions(str(agent_id))
    return [AgentResponse.from_orm(version) for version in versions]


@router.get("/{agent_id}/versions/{version}", response_model=AgentResponse)
async def get_agent_version(
    agent_id: UUID,
    version: str,
    session_and_context = Depends(get_tenant_aware_session)
):
    """Get a specific version of an agent."""
    session, tenant_context = session_and_context
    
    if not tenant_context:
        raise HTTPException(status_code=400, detail="Tenant context required")
    
    service = AgentVersioningService(session, tenant_context.tenant_id)
    
    agent_version = await service.get_version_by_number(str(agent_id), version)
    if not agent_version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Version {version} not found for agent {agent_id}"
        )
    
    return AgentResponse.from_orm(agent_version)


@router.post("/{agent_id}/rollback", response_model=AgentResponse)
async def rollback_agent(
    agent_id: UUID,
    request: RollbackRequest,
    session_and_context = Depends(get_tenant_aware_session),
    current_user: Dict[str, Any] = Depends(lambda: {"user_id": "system"})  # TODO: Replace with actual auth
):
    """Rollback an agent to a specific version."""
    session, tenant_context = session_and_context
    
    if not tenant_context:
        raise HTTPException(status_code=400, detail="Tenant context required")
    
    service = AgentVersioningService(session, tenant_context.tenant_id)
    
    try:
        rolled_back_agent = await service.rollback_to_version(
            agent_id=str(agent_id),
            target_version=request.target_version,
            updated_by=current_user["user_id"]
        )
        return AgentResponse.from_orm(rolled_back_agent)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{agent_id}/versions/compare/{version1}/{version2}", response_model=VersionComparisonResponse)
async def compare_agent_versions(
    agent_id: UUID,
    version1: str,
    version2: str,
    session_and_context = Depends(get_tenant_aware_session)
):
    """Compare two versions of an agent."""
    session, tenant_context = session_and_context
    
    if not tenant_context:
        raise HTTPException(status_code=400, detail="Tenant context required")
    
    service = AgentVersioningService(session, tenant_context.tenant_id)
    
    try:
        comparison = await service.compare_versions(str(agent_id), version1, version2)
        return VersionComparisonResponse(**comparison)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{agent_id}/history", response_model=List[VersionHistoryEntry])
async def get_agent_version_history(
    agent_id: UUID,
    session_and_context = Depends(get_tenant_aware_session)
):
    """Get version history for an agent."""
    session, tenant_context = session_and_context
    
    if not tenant_context:
        raise HTTPException(status_code=400, detail="Tenant context required")
    
    service = AgentVersioningService(session, tenant_context.tenant_id)
    
    history = await service.get_version_history(str(agent_id))
    return [VersionHistoryEntry(**entry) for entry in history]


@router.post("/{agent_id}/versions/{version}/activate", response_model=AgentResponse)
async def activate_agent_version(
    agent_id: UUID,
    version: str,
    session_and_context = Depends(get_tenant_aware_session),
    current_user: Dict[str, Any] = Depends(lambda: {"user_id": "system"})  # TODO: Replace with actual auth
):
    """Activate a specific version of an agent."""
    session, tenant_context = session_and_context
    
    if not tenant_context:
        raise HTTPException(status_code=400, detail="Tenant context required")
    
    service = AgentVersioningService(session, tenant_context.tenant_id)
    
    try:
        activated_agent = await service.activate_version(
            agent_id=str(agent_id),
            version=version,
            updated_by=current_user["user_id"]
        )
        return AgentResponse.from_orm(activated_agent)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))