# Data Residency and Compliance API
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field

from ..database.connection import get_async_db
from ..middleware.tenant import get_tenant_context
from ..models.tenant import TenantContext
from ..services.compliance import (
    DataResidencyService,
    DataRetentionService,
    ComplianceReportingService,
    DataRegion,
    ComplianceFramework,
    DataClassification,
    RetentionPeriod,
    DataResidencyViolationException
)

router = APIRouter(prefix="/api/v1/compliance", tags=["compliance"])


# Request/Response models
class DataResidencyRuleRequest(BaseModel):
    """Request model for creating data residency rules"""
    allowed_regions: List[DataRegion] = Field(..., description="Allowed data regions")
    data_types: List[str] = Field(..., description="Data types this rule applies to")
    compliance_frameworks: List[ComplianceFramework] = Field(..., description="Applicable compliance frameworks")
    prohibited_regions: Optional[List[DataRegion]] = Field(None, description="Prohibited data regions")


class DataRetentionPolicyRequest(BaseModel):
    """Request model for creating data retention policies"""
    data_type: str = Field(..., description="Type of data this policy applies to")
    classification: DataClassification = Field(..., description="Data classification level")
    retention_period: RetentionPeriod = Field(..., description="How long to retain the data")
    compliance_frameworks: List[ComplianceFramework] = Field(..., description="Applicable compliance frameworks")
    auto_delete: bool = Field(False, description="Automatically delete expired data")
    legal_hold_exempt: bool = Field(False, description="Exempt from legal holds")


class DataResidencyValidationRequest(BaseModel):
    """Request model for validating data residency"""
    data_type: str = Field(..., description="Type of data to validate")
    target_region: DataRegion = Field(..., description="Target region for data storage")
    classification: DataClassification = Field(DataClassification.INTERNAL, description="Data classification")


class ComplianceReportRequest(BaseModel):
    """Request model for generating compliance reports"""
    frameworks: Optional[List[ComplianceFramework]] = Field(None, description="Specific frameworks to report on")
    start_date: Optional[datetime] = Field(None, description="Report start date")
    end_date: Optional[datetime] = Field(None, description="Report end date")


# Data Residency endpoints
@router.post("/data-residency/rules")
async def create_residency_rule(
    request: DataResidencyRuleRequest,
    tenant_context: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_async_db)
):
    """Create a new data residency rule"""
    try:
        service = DataResidencyService(session, tenant_context.tenant_id)
        
        rule = await service.add_residency_rule(
            allowed_regions=request.allowed_regions,
            data_types=request.data_types,
            compliance_frameworks=request.compliance_frameworks,
            prohibited_regions=request.prohibited_regions
        )
        
        return {
            "message": "Data residency rule created successfully",
            "rule": {
                "allowed_regions": [r.value for r in rule.allowed_regions],
                "prohibited_regions": [r.value for r in rule.prohibited_regions],
                "data_types": rule.data_types,
                "compliance_frameworks": [f.value for f in rule.compliance_frameworks],
                "created_at": rule.created_at.isoformat()
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/data-residency/rules")
async def get_residency_rules(
    tenant_context: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_async_db)
):
    """Get all data residency rules for the tenant"""
    try:
        service = DataResidencyService(session, tenant_context.tenant_id)
        rules = await service.get_tenant_residency_rules()
        
        return {
            "rules": [
                {
                    "allowed_regions": [r.value for r in rule.allowed_regions],
                    "prohibited_regions": [r.value for r in rule.prohibited_regions],
                    "data_types": rule.data_types,
                    "compliance_frameworks": [f.value for f in rule.compliance_frameworks],
                    "created_at": rule.created_at.isoformat(),
                    "updated_at": rule.updated_at.isoformat()
                }
                for rule in rules
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/data-residency/validate")
async def validate_data_residency(
    request: DataResidencyValidationRequest,
    tenant_context: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_async_db)
):
    """Validate if data can be stored in a specific region"""
    try:
        service = DataResidencyService(session, tenant_context.tenant_id)
        
        is_valid = await service.validate_data_residency(
            data_type=request.data_type,
            target_region=request.target_region,
            classification=request.classification
        )
        
        return {
            "valid": is_valid,
            "data_type": request.data_type,
            "target_region": request.target_region.value,
            "classification": request.classification.value
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/data-residency/report")
async def get_residency_report(
    tenant_context: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_async_db)
):
    """Get data residency compliance report"""
    try:
        service = DataResidencyService(session, tenant_context.tenant_id)
        report = await service.get_compliance_report()
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Data Retention endpoints
@router.post("/data-retention/policies")
async def create_retention_policy(
    request: DataRetentionPolicyRequest,
    tenant_context: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_async_db)
):
    """Create a new data retention policy"""
    try:
        service = DataRetentionService(session, tenant_context.tenant_id)
        
        policy = await service.add_retention_policy(
            data_type=request.data_type,
            classification=request.classification,
            retention_period=request.retention_period,
            compliance_frameworks=request.compliance_frameworks,
            auto_delete=request.auto_delete,
            legal_hold_exempt=request.legal_hold_exempt
        )
        
        return {
            "message": "Data retention policy created successfully",
            "policy": {
                "data_type": policy.data_type,
                "classification": policy.classification.value,
                "retention_period": policy.retention_period.value,
                "auto_delete": policy.auto_delete,
                "legal_hold_exempt": policy.legal_hold_exempt,
                "compliance_frameworks": [f.value for f in policy.compliance_frameworks],
                "created_at": policy.created_at.isoformat()
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/data-retention/policies")
async def get_retention_policies(
    tenant_context: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_async_db)
):
    """Get all data retention policies for the tenant"""
    try:
        service = DataRetentionService(session, tenant_context.tenant_id)
        policies = await service.get_retention_policies()
        
        return {
            "policies": [
                {
                    "data_type": policy.data_type,
                    "classification": policy.classification.value,
                    "retention_period": policy.retention_period.value,
                    "auto_delete": policy.auto_delete,
                    "legal_hold_exempt": policy.legal_hold_exempt,
                    "compliance_frameworks": [f.value for f in policy.compliance_frameworks],
                    "created_at": policy.created_at.isoformat(),
                    "updated_at": policy.updated_at.isoformat()
                }
                for policy in policies
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/data-retention/expired")
async def get_expired_data(
    tenant_context: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_async_db)
):
    """Get data that has exceeded retention periods"""
    try:
        service = DataRetentionService(session, tenant_context.tenant_id)
        expired_data = await service.identify_expired_data()
        
        return {
            "expired_data_count": len(expired_data),
            "expired_data": expired_data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/data-retention/period/{data_type}")
async def get_retention_period(
    data_type: str,
    classification: DataClassification = Query(DataClassification.INTERNAL),
    tenant_context: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_async_db)
):
    """Get retention period for specific data type and classification"""
    try:
        service = DataRetentionService(session, tenant_context.tenant_id)
        
        retention_period = await service.get_retention_period_for_data(
            data_type=data_type,
            classification=classification
        )
        
        return {
            "data_type": data_type,
            "classification": classification.value,
            "retention_period": retention_period.value if retention_period else None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Compliance Reporting endpoints
@router.post("/reports/generate")
async def generate_compliance_report(
    request: ComplianceReportRequest,
    tenant_context: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_async_db)
):
    """Generate comprehensive compliance report"""
    try:
        service = ComplianceReportingService(session, tenant_context.tenant_id)
        
        report = await service.generate_compliance_report(
            frameworks=request.frameworks,
            start_date=request.start_date,
            end_date=request.end_date
        )
        
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/frameworks")
async def get_supported_frameworks():
    """Get list of supported compliance frameworks"""
    return {
        "frameworks": [
            {
                "code": framework.value,
                "name": framework.name,
                "description": _get_framework_description(framework)
            }
            for framework in ComplianceFramework
        ]
    }


@router.get("/regions")
async def get_supported_regions():
    """Get list of supported data regions"""
    return {
        "regions": [
            {
                "code": region.value,
                "name": region.name,
                "description": _get_region_description(region)
            }
            for region in DataRegion
        ]
    }


@router.get("/classifications")
async def get_data_classifications():
    """Get list of data classification levels"""
    return {
        "classifications": [
            {
                "code": classification.value,
                "name": classification.name,
                "description": _get_classification_description(classification)
            }
            for classification in DataClassification
        ]
    }


@router.get("/retention-periods")
async def get_retention_periods():
    """Get list of standard retention periods"""
    return {
        "retention_periods": [
            {
                "code": period.value,
                "name": period.name,
                "description": _get_retention_description(period)
            }
            for period in RetentionPeriod
        ]
    }


# Helper functions for descriptions
def _get_framework_description(framework: ComplianceFramework) -> str:
    """Get description for compliance framework"""
    descriptions = {
        ComplianceFramework.GDPR: "General Data Protection Regulation (EU)",
        ComplianceFramework.CCPA: "California Consumer Privacy Act (US)",
        ComplianceFramework.HIPAA: "Health Insurance Portability and Accountability Act (US)",
        ComplianceFramework.SOC2: "Service Organization Control 2",
        ComplianceFramework.ISO27001: "ISO/IEC 27001 Information Security Management",
        ComplianceFramework.PCI_DSS: "Payment Card Industry Data Security Standard",
        ComplianceFramework.PIPEDA: "Personal Information Protection and Electronic Documents Act (Canada)",
        ComplianceFramework.LGPD: "Lei Geral de Proteção de Dados (Brazil)"
    }
    return descriptions.get(framework, "")


def _get_region_description(region: DataRegion) -> str:
    """Get description for data region"""
    descriptions = {
        DataRegion.US_EAST: "US East (N. Virginia)",
        DataRegion.US_WEST: "US West (Oregon)",
        DataRegion.EU_WEST: "Europe (Ireland)",
        DataRegion.EU_CENTRAL: "Europe (Frankfurt)",
        DataRegion.ASIA_PACIFIC: "Asia Pacific (Singapore)",
        DataRegion.CANADA: "Canada (Central)",
        DataRegion.UK: "Europe (London)",
        DataRegion.AUSTRALIA: "Asia Pacific (Sydney)"
    }
    return descriptions.get(region, "")


def _get_classification_description(classification: DataClassification) -> str:
    """Get description for data classification"""
    descriptions = {
        DataClassification.PUBLIC: "Publicly available information",
        DataClassification.INTERNAL: "Internal use only",
        DataClassification.CONFIDENTIAL: "Confidential business information",
        DataClassification.RESTRICTED: "Highly restricted access",
        DataClassification.PII: "Personally Identifiable Information",
        DataClassification.PHI: "Protected Health Information"
    }
    return descriptions.get(classification, "")


def _get_retention_description(period: RetentionPeriod) -> str:
    """Get description for retention period"""
    descriptions = {
        RetentionPeriod.DAYS_30: "30 days",
        RetentionPeriod.DAYS_90: "90 days",
        RetentionPeriod.MONTHS_6: "6 months",
        RetentionPeriod.YEAR_1: "1 year",
        RetentionPeriod.YEARS_3: "3 years",
        RetentionPeriod.YEARS_7: "7 years",
        RetentionPeriod.INDEFINITE: "Indefinite retention"
    }
    return descriptions.get(period, "")