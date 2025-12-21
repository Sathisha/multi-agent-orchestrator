# Data Residency and Compliance Service
from typing import Dict, Any, Optional, List, Set
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from datetime import datetime, timedelta
from enum import Enum
import logging
import json
from dataclasses import dataclass

from ..models.tenant import Tenant
from ..models.audit import AuditLog
from .base import BaseService

logger = logging.getLogger(__name__)


class DataRegion(str, Enum):
    """Supported data regions for residency compliance"""
    US_EAST = "us-east-1"
    US_WEST = "us-west-2"
    EU_WEST = "eu-west-1"
    EU_CENTRAL = "eu-central-1"
    ASIA_PACIFIC = "ap-southeast-1"
    CANADA = "ca-central-1"
    UK = "eu-west-2"
    AUSTRALIA = "ap-southeast-2"


class ComplianceFramework(str, Enum):
    """Compliance frameworks supported"""
    GDPR = "gdpr"
    CCPA = "ccpa"
    HIPAA = "hipaa"
    SOC2 = "soc2"
    ISO27001 = "iso27001"
    PCI_DSS = "pci_dss"
    PIPEDA = "pipeda"  # Canada
    LGPD = "lgpd"      # Brazil


class DataClassification(str, Enum):
    """Data classification levels"""
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"
    PII = "pii"  # Personally Identifiable Information
    PHI = "phi"  # Protected Health Information


class RetentionPeriod(str, Enum):
    """Standard data retention periods"""
    DAYS_30 = "30_days"
    DAYS_90 = "90_days"
    MONTHS_6 = "6_months"
    YEAR_1 = "1_year"
    YEARS_3 = "3_years"
    YEARS_7 = "7_years"
    INDEFINITE = "indefinite"


@dataclass
class DataResidencyRule:
    """Data residency rule configuration"""
    tenant_id: str
    allowed_regions: List[DataRegion]
    prohibited_regions: List[DataRegion]
    data_types: List[str]
    compliance_frameworks: List[ComplianceFramework]
    created_at: datetime
    updated_at: datetime


@dataclass
class RetentionPolicy:
    """Data retention policy configuration"""
    tenant_id: str
    data_type: str
    classification: DataClassification
    retention_period: RetentionPeriod
    auto_delete: bool
    legal_hold_exempt: bool
    compliance_frameworks: List[ComplianceFramework]
    created_at: datetime
    updated_at: datetime


class DataResidencyService:
    """Service for managing data residency and geographic restrictions"""
    
    def __init__(self, session: AsyncSession, tenant_id: str):
        self.session = session
        self.tenant_id = tenant_id
        self.current_region = DataRegion.US_EAST  # Would be configured per deployment
    
    async def get_tenant_residency_rules(self) -> List[DataResidencyRule]:
        """Get data residency rules for tenant"""
        tenant = await self._get_tenant()
        compliance_settings = tenant.compliance_settings or {}
        residency_rules = compliance_settings.get("data_residency", [])
        
        return [
            DataResidencyRule(
                tenant_id=self.tenant_id,
                allowed_regions=[DataRegion(r) for r in rule.get("allowed_regions", [])],
                prohibited_regions=[DataRegion(r) for r in rule.get("prohibited_regions", [])],
                data_types=rule.get("data_types", []),
                compliance_frameworks=[ComplianceFramework(f) for f in rule.get("compliance_frameworks", [])],
                created_at=datetime.fromisoformat(rule.get("created_at", datetime.utcnow().isoformat())),
                updated_at=datetime.fromisoformat(rule.get("updated_at", datetime.utcnow().isoformat()))
            )
            for rule in residency_rules
        ]
    
    async def validate_data_residency(
        self,
        data_type: str,
        target_region: DataRegion,
        classification: DataClassification = DataClassification.INTERNAL
    ) -> bool:
        """Validate if data can be stored/processed in target region"""
        rules = await self.get_tenant_residency_rules()
        
        # If no rules defined, allow all regions
        if not rules:
            return True
        
        # Check rules that apply to this data type
        applicable_rules = [
            rule for rule in rules
            if not rule.data_types or data_type in rule.data_types
        ]
        
        if not applicable_rules:
            return True
        
        # Check if target region is allowed
        for rule in applicable_rules:
            # If prohibited regions are specified and target is in them, deny
            if rule.prohibited_regions and target_region in rule.prohibited_regions:
                logger.warning(
                    f"Data residency violation: {data_type} cannot be stored in {target_region} "
                    f"for tenant {self.tenant_id} (prohibited region)"
                )
                return False
            
            # If allowed regions are specified and target is not in them, deny
            if rule.allowed_regions and target_region not in rule.allowed_regions:
                logger.warning(
                    f"Data residency violation: {data_type} cannot be stored in {target_region} "
                    f"for tenant {self.tenant_id} (not in allowed regions)"
                )
                return False
        
        return True
    
    async def enforce_data_residency(
        self,
        data_type: str,
        target_region: Optional[DataRegion] = None,
        classification: DataClassification = DataClassification.INTERNAL
    ):
        """Enforce data residency rules with exceptions"""
        if target_region is None:
            target_region = self.current_region
        
        if not await self.validate_data_residency(data_type, target_region, classification):
            raise DataResidencyViolationException(
                tenant_id=self.tenant_id,
                data_type=data_type,
                target_region=target_region,
                classification=classification
            )
    
    async def add_residency_rule(
        self,
        allowed_regions: List[DataRegion],
        data_types: List[str],
        compliance_frameworks: List[ComplianceFramework],
        prohibited_regions: Optional[List[DataRegion]] = None
    ) -> DataResidencyRule:
        """Add new data residency rule"""
        tenant = await self._get_tenant()
        compliance_settings = tenant.compliance_settings or {}
        residency_rules = compliance_settings.get("data_residency", [])
        
        new_rule = {
            "allowed_regions": [r.value for r in allowed_regions],
            "prohibited_regions": [r.value for r in (prohibited_regions or [])],
            "data_types": data_types,
            "compliance_frameworks": [f.value for f in compliance_frameworks],
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        residency_rules.append(new_rule)
        compliance_settings["data_residency"] = residency_rules
        tenant.compliance_settings = compliance_settings
        
        await self.session.commit()
        await self.session.refresh(tenant)
        
        return DataResidencyRule(
            tenant_id=self.tenant_id,
            allowed_regions=allowed_regions,
            prohibited_regions=prohibited_regions or [],
            data_types=data_types,
            compliance_frameworks=compliance_frameworks,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
    
    async def get_compliance_report(self) -> Dict[str, Any]:
        """Generate data residency compliance report"""
        rules = await self.get_tenant_residency_rules()
        tenant = await self._get_tenant()
        
        return {
            "tenant_id": self.tenant_id,
            "current_region": self.current_region.value,
            "total_rules": len(rules),
            "compliance_frameworks": list(set([
                framework.value
                for rule in rules
                for framework in rule.compliance_frameworks
            ])),
            "protected_data_types": list(set([
                data_type
                for rule in rules
                for data_type in rule.data_types
            ])),
            "allowed_regions": list(set([
                region.value
                for rule in rules
                for region in rule.allowed_regions
            ])),
            "prohibited_regions": list(set([
                region.value
                for rule in rules
                for region in rule.prohibited_regions
            ])),
            "last_updated": max([rule.updated_at for rule in rules]) if rules else None
        }
    
    async def _get_tenant(self) -> Tenant:
        """Get tenant record"""
        stmt = select(Tenant).where(Tenant.id == self.tenant_id)
        result = await self.session.execute(stmt)
        tenant = result.scalar_one_or_none()
        
        if not tenant:
            raise ValueError(f"Tenant {self.tenant_id} not found")
        
        return tenant


class DataRetentionService:
    """Service for managing data retention policies"""
    
    def __init__(self, session: AsyncSession, tenant_id: str):
        self.session = session
        self.tenant_id = tenant_id
    
    async def get_retention_policies(self) -> List[RetentionPolicy]:
        """Get data retention policies for tenant"""
        tenant = await self._get_tenant()
        compliance_settings = tenant.compliance_settings or {}
        retention_policies = compliance_settings.get("data_retention", [])
        
        return [
            RetentionPolicy(
                tenant_id=self.tenant_id,
                data_type=policy.get("data_type"),
                classification=DataClassification(policy.get("classification", "internal")),
                retention_period=RetentionPeriod(policy.get("retention_period", "1_year")),
                auto_delete=policy.get("auto_delete", False),
                legal_hold_exempt=policy.get("legal_hold_exempt", False),
                compliance_frameworks=[ComplianceFramework(f) for f in policy.get("compliance_frameworks", [])],
                created_at=datetime.fromisoformat(policy.get("created_at", datetime.utcnow().isoformat())),
                updated_at=datetime.fromisoformat(policy.get("updated_at", datetime.utcnow().isoformat()))
            )
            for policy in retention_policies
        ]
    
    async def add_retention_policy(
        self,
        data_type: str,
        classification: DataClassification,
        retention_period: RetentionPeriod,
        compliance_frameworks: List[ComplianceFramework],
        auto_delete: bool = False,
        legal_hold_exempt: bool = False
    ) -> RetentionPolicy:
        """Add new data retention policy"""
        tenant = await self._get_tenant()
        compliance_settings = tenant.compliance_settings or {}
        retention_policies = compliance_settings.get("data_retention", [])
        
        new_policy = {
            "data_type": data_type,
            "classification": classification.value,
            "retention_period": retention_period.value,
            "auto_delete": auto_delete,
            "legal_hold_exempt": legal_hold_exempt,
            "compliance_frameworks": [f.value for f in compliance_frameworks],
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        retention_policies.append(new_policy)
        compliance_settings["data_retention"] = retention_policies
        tenant.compliance_settings = compliance_settings
        
        await self.session.commit()
        await self.session.refresh(tenant)
        
        return RetentionPolicy(
            tenant_id=self.tenant_id,
            data_type=data_type,
            classification=classification,
            retention_period=retention_period,
            auto_delete=auto_delete,
            legal_hold_exempt=legal_hold_exempt,
            compliance_frameworks=compliance_frameworks,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
    
    async def get_retention_period_for_data(
        self,
        data_type: str,
        classification: DataClassification
    ) -> Optional[RetentionPeriod]:
        """Get retention period for specific data type and classification"""
        policies = await self.get_retention_policies()
        
        # Find most specific policy
        exact_match = next(
            (p for p in policies if p.data_type == data_type and p.classification == classification),
            None
        )
        if exact_match:
            return exact_match.retention_period
        
        # Find policy for data type with any classification
        type_match = next(
            (p for p in policies if p.data_type == data_type),
            None
        )
        if type_match:
            return type_match.retention_period
        
        # Find policy for classification with any data type
        classification_match = next(
            (p for p in policies if p.classification == classification),
            None
        )
        if classification_match:
            return classification_match.retention_period
        
        return None
    
    async def identify_expired_data(self) -> List[Dict[str, Any]]:
        """Identify data that has exceeded retention periods"""
        policies = await self.get_retention_policies()
        expired_data = []
        
        for policy in policies:
            if policy.retention_period == RetentionPeriod.INDEFINITE:
                continue
            
            # Calculate cutoff date based on retention period
            cutoff_date = self._calculate_cutoff_date(policy.retention_period)
            
            # Query audit logs to find old data
            stmt = select(AuditLog).where(
                and_(
                    AuditLog.tenant_id == self.tenant_id,
                    AuditLog.timestamp < cutoff_date,
                    AuditLog.resource_type == policy.data_type
                )
            )
            
            result = await self.session.execute(stmt)
            old_records = result.scalars().all()
            
            for record in old_records:
                expired_data.append({
                    "record_id": record.id,
                    "data_type": policy.data_type,
                    "classification": policy.classification.value,
                    "retention_period": policy.retention_period.value,
                    "created_date": record.timestamp,
                    "cutoff_date": cutoff_date,
                    "auto_delete": policy.auto_delete,
                    "legal_hold_exempt": policy.legal_hold_exempt
                })
        
        return expired_data
    
    def _calculate_cutoff_date(self, retention_period: RetentionPeriod) -> datetime:
        """Calculate cutoff date for retention period"""
        now = datetime.utcnow()
        
        if retention_period == RetentionPeriod.DAYS_30:
            return now - timedelta(days=30)
        elif retention_period == RetentionPeriod.DAYS_90:
            return now - timedelta(days=90)
        elif retention_period == RetentionPeriod.MONTHS_6:
            return now - timedelta(days=180)
        elif retention_period == RetentionPeriod.YEAR_1:
            return now - timedelta(days=365)
        elif retention_period == RetentionPeriod.YEARS_3:
            return now - timedelta(days=1095)
        elif retention_period == RetentionPeriod.YEARS_7:
            return now - timedelta(days=2555)
        else:
            return now - timedelta(days=365)  # Default to 1 year
    
    async def _get_tenant(self) -> Tenant:
        """Get tenant record"""
        stmt = select(Tenant).where(Tenant.id == self.tenant_id)
        result = await self.session.execute(stmt)
        tenant = result.scalar_one_or_none()
        
        if not tenant:
            raise ValueError(f"Tenant {self.tenant_id} not found")
        
        return tenant


class ComplianceReportingService:
    """Service for generating compliance reports"""
    
    def __init__(self, session: AsyncSession, tenant_id: str):
        self.session = session
        self.tenant_id = tenant_id
        self.residency_service = DataResidencyService(session, tenant_id)
        self.retention_service = DataRetentionService(session, tenant_id)
    
    async def generate_compliance_report(
        self,
        frameworks: Optional[List[ComplianceFramework]] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Generate comprehensive compliance report"""
        if start_date is None:
            start_date = datetime.utcnow() - timedelta(days=30)
        if end_date is None:
            end_date = datetime.utcnow()
        
        # Get residency compliance
        residency_report = await self.residency_service.get_compliance_report()
        
        # Get retention policies
        retention_policies = await self.retention_service.get_retention_policies()
        
        # Get expired data
        expired_data = await self.retention_service.identify_expired_data()
        
        # Get audit activity
        audit_activity = await self._get_audit_activity(start_date, end_date)
        
        report = {
            "tenant_id": self.tenant_id,
            "report_period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            },
            "compliance_frameworks": [f.value for f in (frameworks or [])],
            "data_residency": residency_report,
            "data_retention": {
                "total_policies": len(retention_policies),
                "policies": [
                    {
                        "data_type": p.data_type,
                        "classification": p.classification.value,
                        "retention_period": p.retention_period.value,
                        "auto_delete": p.auto_delete,
                        "compliance_frameworks": [f.value for f in p.compliance_frameworks]
                    }
                    for p in retention_policies
                ],
                "expired_data_count": len(expired_data),
                "expired_data": expired_data[:10]  # Limit to first 10 for report size
            },
            "audit_activity": audit_activity,
            "generated_at": datetime.utcnow().isoformat()
        }
        
        return report
    
    async def _get_audit_activity(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Get audit activity summary"""
        stmt = select(
            func.count(AuditLog.id).label('total_events'),
            func.count(AuditLog.id).filter(AuditLog.success == True).label('successful_events'),
            func.count(AuditLog.id).filter(AuditLog.success == False).label('failed_events')
        ).where(
            and_(
                AuditLog.tenant_id == self.tenant_id,
                AuditLog.timestamp >= start_date,
                AuditLog.timestamp <= end_date
            )
        )
        
        result = await self.session.execute(stmt)
        stats = result.first()
        
        return {
            "total_events": stats.total_events or 0,
            "successful_events": stats.successful_events or 0,
            "failed_events": stats.failed_events or 0,
            "success_rate": (
                (stats.successful_events or 0) / max(stats.total_events or 1, 1)
            ) * 100
        }


class DataResidencyViolationException(Exception):
    """Exception raised when data residency rules are violated"""
    
    def __init__(
        self,
        tenant_id: str,
        data_type: str,
        target_region: DataRegion,
        classification: DataClassification
    ):
        self.tenant_id = tenant_id
        self.data_type = data_type
        self.target_region = target_region
        self.classification = classification
        
        message = (
            f"Data residency violation for tenant {tenant_id}: "
            f"{data_type} ({classification.value}) cannot be stored in {target_region.value}"
        )
        super().__init__(message)