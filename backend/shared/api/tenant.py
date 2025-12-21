# Tenant Administration API Endpoints
from typing import List, Optional, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from ..database.connection import get_async_db
from ..services.tenant import TenantService, TenantInvitationService, TenantUserService
from ..services.quota import ResourceQuotaService
from ..services.analytics import TenantAnalyticsService, AnalyticsTimeframe
from ..middleware.tenant import (
    get_tenant_context_dependency,
    require_tenant_context_dependency,
    get_tenant_aware_session
)
from ..models.tenant import Tenant, TenantContext, TenantInvitation, TenantUser, ResourceQuotas
from ..models.rbac import Role

router = APIRouter(prefix="/api/v1/tenants", tags=["tenants"])


# Pydantic models for API requests/responses
class TenantCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=100)
    display_name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    primary_email: str = Field(..., regex=r'^[^@]+@[^@]+\.[^@]+$')
    plan_name: str = Field(default="free")


class TenantUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    display_name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    primary_email: Optional[str] = Field(None, regex=r'^[^@]+@[^@]+\.[^@]+$')


class TenantResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    display_name: Optional[str]
    description: Optional[str]
    primary_email: str
    status: str
    created_at: str
    updated_at: str
    
    class Config:
        from_attributes = True


class TenantInvitationRequest(BaseModel):
    email: str = Field(..., regex=r'^[^@]+@[^@]+\.[^@]+$')
    role: str = Field(default="member")


class TenantInvitationResponse(BaseModel):
    id: UUID
    email: str
    role: str
    status: str
    expires_at: str
    created_at: str
    
    class Config:
        from_attributes = True


class TenantUserResponse(BaseModel):
    id: UUID
    user_id: UUID
    role: str
    status: str
    joined_at: Optional[str]
    
    class Config:
        from_attributes = True


class ResourceQuotaResponse(BaseModel):
    max_agents: int
    max_workflows: int
    max_executions: int
    max_storage: int
    max_api_calls: int
    max_users: int
    
    class Config:
        from_attributes = True


class ResourceUsageResponse(BaseModel):
    tenant_id: UUID
    timestamp: str
    resources: Dict[str, Any]


class QuotaUpdateRequest(BaseModel):
    max_agents: Optional[int] = None
    max_workflows: Optional[int] = None
    max_executions: Optional[int] = None
    max_storage: Optional[int] = None
    max_api_calls: Optional[int] = None
    max_users: Optional[int] = None


# Tenant CRUD endpoints
@router.post("/", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    request: TenantCreateRequest,
    session: AsyncSession = Depends(get_async_db),
    current_user: Dict[str, Any] = Depends(lambda: {"user_id": "system"})  # TODO: Replace with actual auth
):
    """Create a new tenant (system admin only)"""
    service = TenantService(session)
    
    try:
        tenant = await service.create_tenant(
            name=request.name,
            slug=request.slug,
            display_name=request.display_name,
            description=request.description,
            primary_email=request.primary_email,
            plan_name=request.plan_name,
            created_by=current_user["user_id"]
        )
        return TenantResponse.from_orm(tenant)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=List[TenantResponse])
async def list_tenants(
    status_filter: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    session: AsyncSession = Depends(get_async_db),
    current_user: Dict[str, Any] = Depends(lambda: {"user_id": "system"})  # TODO: Replace with actual auth
):
    """List all tenants (system admin only)"""
    service = TenantService(session)
    
    tenants = await service.list_tenants(
        status=status_filter,
        limit=limit,
        offset=offset
    )
    
    return [TenantResponse.from_orm(tenant) for tenant in tenants]


@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    tenant_id: UUID,
    session: AsyncSession = Depends(get_async_db),
    current_user: Dict[str, Any] = Depends(lambda: {"user_id": "system"})  # TODO: Replace with actual auth
):
    """Get tenant by ID"""
    service = TenantService(session)
    
    tenant = await service.get_tenant_by_id(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    return TenantResponse.from_orm(tenant)


@router.put("/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant_id: UUID,
    request: TenantUpdateRequest,
    session: AsyncSession = Depends(get_async_db),
    current_user: Dict[str, Any] = Depends(lambda: {"user_id": "system"})  # TODO: Replace with actual auth
):
    """Update tenant"""
    service = TenantService(session)
    
    tenant = await service.update_tenant(
        tenant_id=tenant_id,
        name=request.name,
        display_name=request.display_name,
        description=request.description,
        primary_email=request.primary_email,
        updated_by=current_user["user_id"]
    )
    
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    return TenantResponse.from_orm(tenant)


@router.post("/{tenant_id}/activate")
async def activate_tenant(
    tenant_id: UUID,
    session: AsyncSession = Depends(get_async_db),
    current_user: Dict[str, Any] = Depends(lambda: {"user_id": "system"})  # TODO: Replace with actual auth
):
    """Activate tenant"""
    service = TenantService(session)
    
    tenant = await service.activate_tenant(tenant_id, current_user["user_id"])
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    return {"message": "Tenant activated successfully"}


@router.post("/{tenant_id}/suspend")
async def suspend_tenant(
    tenant_id: UUID,
    session: AsyncSession = Depends(get_async_db),
    current_user: Dict[str, Any] = Depends(lambda: {"user_id": "system"})  # TODO: Replace with actual auth
):
    """Suspend tenant"""
    service = TenantService(session)
    
    tenant = await service.suspend_tenant(tenant_id, current_user["user_id"])
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    return {"message": "Tenant suspended successfully"}


# Tenant user management endpoints
@router.post("/{tenant_id}/invitations", response_model=TenantInvitationResponse)
async def create_invitation(
    tenant_id: UUID,
    request: TenantInvitationRequest,
    session: AsyncSession = Depends(get_async_db),
    current_user: Dict[str, Any] = Depends(lambda: {"user_id": "system"})  # TODO: Replace with actual auth
):
    """Create tenant invitation"""
    service = TenantInvitationService(session, str(tenant_id))
    
    try:
        invitation = await service.create_invitation(
            email=request.email,
            role=request.role,
            invited_by=current_user["user_id"]
        )
        return TenantInvitationResponse.from_orm(invitation)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{tenant_id}/invitations", response_model=List[TenantInvitationResponse])
async def list_invitations(
    tenant_id: UUID,
    status_filter: Optional[str] = None,
    session: AsyncSession = Depends(get_async_db),
    current_user: Dict[str, Any] = Depends(lambda: {"user_id": "system"})  # TODO: Replace with actual auth
):
    """List tenant invitations"""
    service = TenantInvitationService(session, str(tenant_id))
    
    invitations = await service.list_invitations(status=status_filter)
    return [TenantInvitationResponse.from_orm(inv) for inv in invitations]


@router.post("/invitations/{invitation_id}/accept")
async def accept_invitation(
    invitation_id: UUID,
    session: AsyncSession = Depends(get_async_db),
    current_user: Dict[str, Any] = Depends(lambda: {"user_id": "system"})  # TODO: Replace with actual auth
):
    """Accept tenant invitation"""
    # This would typically be called by the invited user
    # For now, we'll use a placeholder implementation
    
    # Find invitation
    from sqlalchemy import select
    stmt = select(TenantInvitation).where(TenantInvitation.id == invitation_id)
    result = await session.execute(stmt)
    invitation = result.scalar_one_or_none()
    
    if not invitation:
        raise HTTPException(status_code=404, detail="Invitation not found")
    
    if invitation.status != "pending":
        raise HTTPException(status_code=400, detail="Invitation is not pending")
    
    # Accept invitation
    service = TenantInvitationService(session, invitation.tenant_id)
    await service.accept_invitation(invitation_id, current_user["user_id"])
    
    return {"message": "Invitation accepted successfully"}


@router.get("/{tenant_id}/users", response_model=List[TenantUserResponse])
async def list_tenant_users(
    tenant_id: UUID,
    status_filter: Optional[str] = None,
    session: AsyncSession = Depends(get_async_db),
    current_user: Dict[str, Any] = Depends(lambda: {"user_id": "system"})  # TODO: Replace with actual auth
):
    """List tenant users"""
    service = TenantUserService(session, str(tenant_id))
    
    users = await service.list_tenant_users(status=status_filter)
    return [TenantUserResponse.from_orm(user) for user in users]


@router.delete("/{tenant_id}/users/{user_id}")
async def remove_tenant_user(
    tenant_id: UUID,
    user_id: UUID,
    session: AsyncSession = Depends(get_async_db),
    current_user: Dict[str, Any] = Depends(lambda: {"user_id": "system"})  # TODO: Replace with actual auth
):
    """Remove user from tenant"""
    service = TenantUserService(session, str(tenant_id))
    
    success = await service.remove_user_from_tenant(str(user_id))
    if not success:
        raise HTTPException(status_code=404, detail="User not found in tenant")
    
    return {"message": "User removed from tenant successfully"}


# Resource quota management endpoints
@router.get("/{tenant_id}/quotas", response_model=ResourceQuotaResponse)
async def get_tenant_quotas(
    tenant_id: UUID,
    session: AsyncSession = Depends(get_async_db),
    current_user: Dict[str, Any] = Depends(lambda: {"user_id": "system"})  # TODO: Replace with actual auth
):
    """Get tenant resource quotas"""
    service = ResourceQuotaService(session, str(tenant_id))
    
    quotas = await service.get_tenant_quotas()
    return ResourceQuotaResponse.from_orm(quotas)


@router.put("/{tenant_id}/quotas", response_model=ResourceQuotaResponse)
async def update_tenant_quotas(
    tenant_id: UUID,
    request: QuotaUpdateRequest,
    session: AsyncSession = Depends(get_async_db),
    current_user: Dict[str, Any] = Depends(lambda: {"user_id": "system"})  # TODO: Replace with actual auth
):
    """Update tenant resource quotas"""
    service = ResourceQuotaService(session, str(tenant_id))
    
    # Build update dictionary from non-None values
    quota_updates = {}
    for field, value in request.dict(exclude_unset=True).items():
        if value is not None:
            quota_updates[field.replace('max_', '')] = value
    
    quotas = await service.update_tenant_quotas(
        quota_updates=quota_updates,
        updated_by=current_user["user_id"]
    )
    
    return ResourceQuotaResponse.from_orm(quotas)


@router.get("/{tenant_id}/usage", response_model=ResourceUsageResponse)
async def get_tenant_usage(
    tenant_id: UUID,
    session: AsyncSession = Depends(get_async_db),
    current_user: Dict[str, Any] = Depends(lambda: {"user_id": "system"})  # TODO: Replace with actual auth
):
    """Get tenant resource usage"""
    service = ResourceQuotaService(session, str(tenant_id))
    
    usage = await service.get_usage_summary()
    return ResourceUsageResponse(**usage)


@router.get("/{tenant_id}/usage/warnings")
async def get_usage_warnings(
    tenant_id: UUID,
    threshold: float = 0.8,
    session: AsyncSession = Depends(get_async_db),
    current_user: Dict[str, Any] = Depends(lambda: {"user_id": "system"})  # TODO: Replace with actual auth
):
    """Get usage warnings for resources approaching limits"""
    service = ResourceQuotaService(session, str(tenant_id))
    
    warnings = await service.check_soft_limits(threshold)
    return {"warnings": warnings}


# Current tenant context endpoints (for tenant users)
@router.get("/current", response_model=TenantResponse)
async def get_current_tenant(
    tenant_context: TenantContext = Depends(require_tenant_context_dependency)
):
    """Get current tenant information"""
    return TenantResponse.from_orm(tenant_context.tenant)


@router.get("/current/usage", response_model=ResourceUsageResponse)
async def get_current_tenant_usage(
    session_and_context = Depends(get_tenant_aware_session)
):
    """Get current tenant resource usage"""
    session, tenant_context = session_and_context
    
    if not tenant_context:
        raise HTTPException(status_code=400, detail="Tenant context required")
    
    service = ResourceQuotaService(session, tenant_context.tenant_id)
    usage = await service.get_usage_summary()
    
    return ResourceUsageResponse(**usage)


@router.get("/current/quotas", response_model=ResourceQuotaResponse)
async def get_current_tenant_quotas(
    session_and_context = Depends(get_tenant_aware_session)
):
    """Get current tenant resource quotas"""
    session, tenant_context = session_and_context
    
    if not tenant_context:
        raise HTTPException(status_code=400, detail="Tenant context required")
    
    service = ResourceQuotaService(session, tenant_context.tenant_id)
    quotas = await service.get_tenant_quotas()
    
    return ResourceQuotaResponse.from_orm(quotas)


# Analytics endpoints
@router.get("/{tenant_id}/analytics/overview")
async def get_tenant_analytics_overview(
    tenant_id: UUID,
    session: AsyncSession = Depends(get_async_db),
    current_user: Dict[str, Any] = Depends(lambda: {"user_id": "system"})  # TODO: Replace with actual auth
):
    """Get tenant analytics overview"""
    service = TenantAnalyticsService(session, str(tenant_id))
    overview = await service.get_tenant_overview()
    return overview


@router.get("/{tenant_id}/analytics/usage")
async def get_tenant_usage_analytics(
    tenant_id: UUID,
    timeframe: AnalyticsTimeframe = AnalyticsTimeframe.LAST_30_DAYS,
    session: AsyncSession = Depends(get_async_db),
    current_user: Dict[str, Any] = Depends(lambda: {"user_id": "system"})  # TODO: Replace with actual auth
):
    """Get detailed tenant usage analytics"""
    service = TenantAnalyticsService(session, str(tenant_id))
    analytics = await service.get_usage_analytics(timeframe)
    return analytics


@router.get("/{tenant_id}/analytics/daily")
async def get_tenant_daily_activity(
    tenant_id: UUID,
    timeframe: AnalyticsTimeframe = AnalyticsTimeframe.LAST_30_DAYS,
    session: AsyncSession = Depends(get_async_db),
    current_user: Dict[str, Any] = Depends(lambda: {"user_id": "system"})  # TODO: Replace with actual auth
):
    """Get tenant daily activity breakdown"""
    service = TenantAnalyticsService(session, str(tenant_id))
    daily_activity = await service.get_daily_activity(timeframe)
    return daily_activity


@router.get("/{tenant_id}/analytics/errors")
async def get_tenant_error_analytics(
    tenant_id: UUID,
    timeframe: AnalyticsTimeframe = AnalyticsTimeframe.LAST_30_DAYS,
    session: AsyncSession = Depends(get_async_db),
    current_user: Dict[str, Any] = Depends(lambda: {"user_id": "system"})  # TODO: Replace with actual auth
):
    """Get tenant error analytics and patterns"""
    service = TenantAnalyticsService(session, str(tenant_id))
    error_analytics = await service.get_error_analytics(timeframe)
    return error_analytics


@router.get("/{tenant_id}/analytics/users")
async def get_tenant_user_activity(
    tenant_id: UUID,
    timeframe: AnalyticsTimeframe = AnalyticsTimeframe.LAST_30_DAYS,
    session: AsyncSession = Depends(get_async_db),
    current_user: Dict[str, Any] = Depends(lambda: {"user_id": "system"})  # TODO: Replace with actual auth
):
    """Get tenant user activity analytics"""
    service = TenantAnalyticsService(session, str(tenant_id))
    user_activity = await service.get_user_activity(timeframe)
    return user_activity


@router.get("/{tenant_id}/analytics/report")
async def generate_tenant_report(
    tenant_id: UUID,
    timeframe: AnalyticsTimeframe = AnalyticsTimeframe.LAST_30_DAYS,
    session: AsyncSession = Depends(get_async_db),
    current_user: Dict[str, Any] = Depends(lambda: {"user_id": "system"})  # TODO: Replace with actual auth
):
    """Generate comprehensive tenant report"""
    service = TenantAnalyticsService(session, str(tenant_id))
    report = await service.generate_tenant_report(timeframe)
    return report


# Current tenant analytics endpoints
@router.get("/current/analytics/overview")
async def get_current_tenant_analytics_overview(
    session_and_context = Depends(get_tenant_aware_session)
):
    """Get current tenant analytics overview"""
    session, tenant_context = session_and_context
    
    if not tenant_context:
        raise HTTPException(status_code=400, detail="Tenant context required")
    
    service = TenantAnalyticsService(session, tenant_context.tenant_id)
    overview = await service.get_tenant_overview()
    return overview


@router.get("/current/analytics/usage")
async def get_current_tenant_usage_analytics(
    timeframe: AnalyticsTimeframe = AnalyticsTimeframe.LAST_30_DAYS,
    session_and_context = Depends(get_tenant_aware_session)
):
    """Get current tenant usage analytics"""
    session, tenant_context = session_and_context
    
    if not tenant_context:
        raise HTTPException(status_code=400, detail="Tenant context required")
    
    service = TenantAnalyticsService(session, tenant_context.tenant_id)
    analytics = await service.get_usage_analytics(timeframe)
    return analytics


@router.get("/current/analytics/report")
async def generate_current_tenant_report(
    timeframe: AnalyticsTimeframe = AnalyticsTimeframe.LAST_30_DAYS,
    session_and_context = Depends(get_tenant_aware_session)
):
    """Generate comprehensive report for current tenant"""
    session, tenant_context = session_and_context
    
    if not tenant_context:
        raise HTTPException(status_code=400, detail="Tenant context required")
    
    service = TenantAnalyticsService(session, tenant_context.tenant_id)
    report = await service.generate_tenant_report(timeframe)
    return report