"""Agent Versioning API endpoints."""

from typing import List, Optional, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from ..services.agent_versioning import AgentVersioningService
from ..schemas.agent import AgentResponse
from ..models.user import User
from ..services.auth import get_current_user
from ..database.connection import get_async_db

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
    session: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new version of an agent."""
    service = AgentVersioningService(session)
    
    try:
        new_version = await service.create_version(
            agent_id=str(agent_id),
            version=request.version,
            changes=request.changes,
            created_by=str(current_user.id)
        )
        return AgentResponse.from_orm(new_version)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{agent_id}/versions", response_model=List[AgentResponse])
async def list_agent_versions(
    agent_id: UUID,
    session: AsyncSession = Depends(get_async_db)
):
    """List all versions of an agent."""
    service = AgentVersioningService(session)
    
    versions = await service.get_agent_versions(str(agent_id))
    return [AgentResponse.from_orm(version) for version in versions]


@router.get("/{agent_id}/versions/{version}", response_model=AgentResponse)
async def get_agent_version(
    agent_id: UUID,
    version: str,
    session: AsyncSession = Depends(get_async_db)
):
    """Get a specific version of an agent."""
    service = AgentVersioningService(session)
    
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
    session: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """Rollback an agent to a specific version."""
    service = AgentVersioningService(session)
    
    try:
        rolled_back_agent = await service.rollback_to_version(
            agent_id=str(agent_id),
            target_version=request.target_version,
            updated_by=str(current_user.id)
        )
        return AgentResponse.from_orm(rolled_back_agent)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{agent_id}/versions/compare/{version1}/{version2}", response_model=VersionComparisonResponse)
async def compare_agent_versions(
    agent_id: UUID,
    version1: str,
    version2: str,
    session: AsyncSession = Depends(get_async_db)
):
    """Compare two versions of an agent."""
    service = AgentVersioningService(session)
    
    try:
        comparison = await service.compare_versions(str(agent_id), version1, version2)
        return VersionComparisonResponse(**comparison)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{agent_id}/history", response_model=List[VersionHistoryEntry])
async def get_agent_version_history(
    agent_id: UUID,
    session: AsyncSession = Depends(get_async_db)
):
    """Get version history for an agent."""
    service = AgentVersioningService(session)
    
    history = await service.get_version_history(str(agent_id))
    return [VersionHistoryEntry(**entry) for entry in history]


@router.post("/{agent_id}/versions/{version}/activate", response_model=AgentResponse)
async def activate_agent_version(
    agent_id: UUID,
    version: str,
    session: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """Activate a specific version of an agent."""
    service = AgentVersioningService(session)
    
    try:
        activated_agent = await service.activate_version(
            agent_id=str(agent_id),
            version=version,
            updated_by=str(current_user.id)
        )
        return AgentResponse.from_orm(activated_agent)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
