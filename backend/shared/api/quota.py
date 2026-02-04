# Resource Quota Management API
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, Field

from ..database import get_async_db
from ..middleware.tenant import get_tenant_context, TenantContext
from ..services.quota import ResourceQuotaService, ResourceType, QuotaViolationException
from ..services.billing import BillingService, ResourceMonitoringService
from ..models.tenant import ResourceQuotas

router = APIRouter(prefix="/quotas", tags=["quotas"])


class QuotaUpdateRequest(BaseModel):
    """Request model for updating quotas"""
    quotas: Dict[str, int] = Field(..., description="Resource quotas to update")


class UsageSummaryResponse(BaseModel):
    """Response model for usage summary"""
    tenant_id: str
    timestamp: str
    resources: Dict[str, Dict[str, Any]]


class QuotaWarningResponse(BaseModel):
    """Response model for quota warnings"""
    resource_type: str
    current_usage: int
    quota_limit: int
    usage_percentage: float
    threshold: float


class BillingChargesResponse(BaseModel):
    """Response model for billing charges"""
    tenant_id: str
    billing_period: Dict[str, str]
    line_items: List[Dict[str, Any]]
    subtotal: float
    tax: float
    total: float


@router.get("/usage", response_model=UsageSummaryResponse)
async def get_usage_summary(
    tenant_context: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_async_db)
):
    """Get comprehensive usage summary for the tenant"""
    try:
        quota_service = ResourceQuotaService(session, tenant_context.tenant_id)
        usage_summary = await quota_service.get_usage_summary()
        return UsageSummaryResponse(**usage_summary)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/warnings", response_model=List[QuotaWarningResponse])
async def get_quota_warnings(
    threshold: float = Query(0.8, ge=0.0, le=1.0, description="Warning threshold (0.0-1.0)"),
    tenant_context: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_async_db)
):
    """Get resources approaching their quota limits"""
    try:
        quota_service = ResourceQuotaService(session, tenant_context.tenant_id)
        warnings = await quota_service.check_soft_limits(threshold=threshold)
        return [QuotaWarningResponse(**warning) for warning in warnings]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/check/{resource_type}")
async def check_resource_quota(
    resource_type: ResourceType,
    requested_amount: int = Query(1, ge=1, description="Amount of resource to check"),
    tenant_context: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_async_db)
):
    """Check if tenant can use additional resources"""
    try:
        quota_service = ResourceQuotaService(session, tenant_context.tenant_id)
        can_use = await quota_service.check_quota(resource_type, requested_amount)
        current_usage = await quota_service.get_current_usage(resource_type)
        quotas = await quota_service.get_tenant_quotas()
        quota_limit = getattr(quotas, f"max_{resource_type.value}", None)
        
        return {
            "resource_type": resource_type.value,
            "can_use": can_use,
            "requested_amount": requested_amount,
            "current_usage": current_usage,
            "quota_limit": quota_limit,
            "available": (quota_limit - current_usage) if quota_limit else None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/update")
async def update_quotas(
    request: QuotaUpdateRequest,
    tenant_context: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_async_db)
):
    """Update tenant resource quotas (admin only)"""
    try:
        # In production, add admin role check here
        quota_service = ResourceQuotaService(session, tenant_context.tenant_id)
        updated_quotas = await quota_service.update_tenant_quotas(
            quota_updates=request.quotas,
            updated_by=tenant_context.user_id
        )
        
        return {
            "message": "Quotas updated successfully",
            "updated_quotas": request.quotas
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/billing/charges", response_model=BillingChargesResponse)
async def get_billing_charges(
    start_date: Optional[datetime] = Query(None, description="Start date for billing period"),
    end_date: Optional[datetime] = Query(None, description="End date for billing period"),
    tenant_context: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_async_db)
):
    """Get billing charges for a specific period"""
    try:
        # Default to current month if no dates provided
        if not start_date or not end_date:
            now = datetime.utcnow()
            start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end_date = now
        
        billing_service = BillingService(session, tenant_context.tenant_id)
        charges = await billing_service.calculate_usage_charges(start_date, end_date)
        return BillingChargesResponse(**charges)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/billing/invoice")
async def generate_invoice(
    start_date: datetime,
    end_date: datetime,
    tenant_context: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_async_db)
):
    """Generate an invoice for the specified billing period"""
    try:
        billing_service = BillingService(session, tenant_context.tenant_id)
        invoice = await billing_service.generate_invoice(start_date, end_date)
        return invoice
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/billing/forecast")
async def get_usage_forecast(
    forecast_days: int = Query(30, ge=1, le=365, description="Number of days to forecast"),
    tenant_context: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_async_db)
):
    """Get usage forecast based on historical data"""
    try:
        billing_service = BillingService(session, tenant_context.tenant_id)
        forecast = await billing_service.get_usage_forecast(forecast_days)
        return forecast
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/billing/alerts")
async def get_billing_alerts(
    tenant_context: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_async_db)
):
    """Get billing-related alerts for the tenant"""
    try:
        billing_service = BillingService(session, tenant_context.tenant_id)
        alerts = await billing_service.check_billing_alerts()
        return {"alerts": alerts}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/monitoring/run")
async def run_monitoring_cycle(
    tenant_context: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_async_db)
):
    """Run a monitoring cycle to check quotas and billing"""
    try:
        monitoring_service = ResourceMonitoringService(session, tenant_context.tenant_id)
        await monitoring_service.run_monitoring_cycle()
        return {"message": "Monitoring cycle completed successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/current/{resource_type}")
async def get_current_usage(
    resource_type: ResourceType,
    tenant_context: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_async_db)
):
    """Get current usage for a specific resource type"""
    try:
        quota_service = ResourceQuotaService(session, tenant_context.tenant_id)
        current_usage = await quota_service.get_current_usage(resource_type)
        quotas = await quota_service.get_tenant_quotas()
        quota_limit = getattr(quotas, f"max_{resource_type.value}", None)
        
        return {
            "resource_type": resource_type.value,
            "current_usage": current_usage,
            "quota_limit": quota_limit,
            "usage_percentage": (current_usage / quota_limit * 100) if quota_limit else 0,
            "available": (quota_limit - current_usage) if quota_limit else None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
