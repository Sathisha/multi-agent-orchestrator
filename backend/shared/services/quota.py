# Resource Quota Management Service
from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from datetime import datetime, timedelta
from enum import Enum
import uuid
import logging

from ..models.tenant import Tenant
from ..models.agent import Agent, AgentExecution
from ..models.workflow import Workflow, WorkflowExecution
from .base import BaseService

logger = logging.getLogger(__name__)


class ResourceType(str, Enum):
    """Types of resources that can be quota-managed"""
    AGENTS = "agents"
    WORKFLOWS = "workflows"
    EXECUTIONS = "executions"
    STORAGE = "storage"
    API_CALLS = "api_calls"
    COMPUTE_TIME = "compute_time"
    MEMORY_USAGE = "memory_usage"
    USERS = "users"


class QuotaViolationType(str, Enum):
    """Types of quota violations"""
    HARD_LIMIT = "hard_limit"
    SOFT_LIMIT = "soft_limit"
    RATE_LIMIT = "rate_limit"


class QuotaViolationException(Exception):
    """Exception raised when resource quota is exceeded"""
    
    def __init__(
        self,
        resource_type: ResourceType,
        current_usage: int,
        quota_limit: int,
        requested_amount: int,
        tenant_id: str,
        violation_type: QuotaViolationType = QuotaViolationType.HARD_LIMIT
    ):
        self.resource_type = resource_type
        self.current_usage = current_usage
        self.quota_limit = quota_limit
        self.requested_amount = requested_amount
        self.tenant_id = tenant_id
        self.violation_type = violation_type
        
        message = (
            f"Quota exceeded for {resource_type} in tenant {tenant_id}: "
            f"current={current_usage}, limit={quota_limit}, requested={requested_amount}"
        )
        super().__init__(message)


class ResourceUsageTracker:
    """Tracks resource usage for billing and analytics"""
    
    def __init__(self, session: AsyncSession, tenant_id: str):
        self.session = session
        self.tenant_id = tenant_id
    
    async def track_usage(
        self,
        resource_type: ResourceType,
        amount: int = 1,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Track resource usage for billing and analytics"""
        # This would typically write to a usage tracking table
        # For now, we'll log the usage
        logger.info(
            f"Resource usage tracked: tenant={self.tenant_id}, "
            f"resource={resource_type}, amount={amount}, metadata={metadata}"
        )


class ResourceQuotaService:
    """Service for managing resource quotas and enforcement"""
    
    def __init__(self, session: AsyncSession, tenant_id: str):
        self.session = session
        self.tenant_id = tenant_id
        self.usage_tracker = ResourceUsageTracker(session, tenant_id)
        
        # Cache for quota limits (5-minute TTL)
        self._quota_cache = {}
        self._cache_timestamp = None
        self._cache_ttl = 300  # 5 minutes
    
    async def get_tenant_quotas(self) -> Dict[str, Any]:
        """Get resource quotas for the tenant"""
        # Check cache first
        if (self._cache_timestamp and 
            datetime.utcnow().timestamp() - self._cache_timestamp < self._cache_ttl and
            self.tenant_id in self._quota_cache):
            return self._quota_cache[self.tenant_id]
        
        # Fetch from database
        stmt = select(Tenant).where(Tenant.id == self.tenant_id)
        result = await self.session.execute(stmt)
        tenant = result.scalar_one_or_none()
        
        if not tenant:
            raise ValueError(f"Tenant {self.tenant_id} not found")
        
        # Cache the result
        self._quota_cache[self.tenant_id] = tenant.resource_limits
        self._cache_timestamp = datetime.utcnow().timestamp()
        
        return tenant.resource_limits
    
    async def get_current_usage(self, resource_type: ResourceType) -> int:
        """Get current usage for a specific resource type"""
        if resource_type == ResourceType.AGENTS:
            stmt = select(func.count(Agent.id)).where(Agent.tenant_id == self.tenant_id)
            result = await self.session.execute(stmt)
            return result.scalar() or 0
        
        elif resource_type == ResourceType.WORKFLOWS:
            stmt = select(func.count(Workflow.id)).where(Workflow.tenant_id == self.tenant_id)
            result = await self.session.execute(stmt)
            return result.scalar() or 0
        
        elif resource_type == ResourceType.EXECUTIONS:
            # Count executions in the last 24 hours
            since = datetime.utcnow() - timedelta(hours=24)
            stmt = select(func.count(AgentExecution.id)).where(
                and_(
                    AgentExecution.tenant_id == self.tenant_id,
                    AgentExecution.created_at >= since
                )
            )
            result = await self.session.execute(stmt)
            return result.scalar() or 0
        
        elif resource_type == ResourceType.API_CALLS:
            # This would typically come from API gateway metrics
            # For now, return 0
            return 0
        
        elif resource_type == ResourceType.STORAGE:
            # Calculate storage usage across all tenant data
            # This is a simplified calculation
            agent_storage = await self.session.execute(
                select(func.sum(func.length(Agent.config.cast(str)))).where(
                    Agent.tenant_id == self.tenant_id
                )
            )
            workflow_storage = await self.session.execute(
                select(func.sum(func.length(Workflow.bpmn_xml))).where(
                    Workflow.tenant_id == self.tenant_id
                )
            )
            
            total_storage = (agent_storage.scalar() or 0) + (workflow_storage.scalar() or 0)
            return total_storage
        
        elif resource_type == ResourceType.USERS:
            from ..models.tenant import TenantUser
            stmt = select(func.count(TenantUser.id)).where(
                and_(
                    TenantUser.tenant_id == self.tenant_id,
                    TenantUser.status == "active"
                )
            )
            result = await self.session.execute(stmt)
            return result.scalar() or 0
        
        else:
            logger.warning(f"Unknown resource type: {resource_type}")
            return 0
    
    async def check_quota(
        self,
        resource_type: ResourceType,
        requested_amount: int = 1
    ) -> bool:
        """Check if tenant can use additional resources"""
        quotas = await self.get_tenant_quotas()
        current_usage = await self.get_current_usage(resource_type)
        
        # Get quota limit for resource type
        quota_limit = getattr(quotas, f"max_{resource_type.value}", None)
        if quota_limit is None:
            # No limit set, allow usage
            return True
        
        return current_usage + requested_amount <= quota_limit
    
    async def enforce_quota(
        self,
        resource_type: ResourceType,
        requested_amount: int = 1,
        violation_type: QuotaViolationType = QuotaViolationType.HARD_LIMIT
    ):
        """Enforce quota limits with detailed error messages"""
        if not await self.check_quota(resource_type, requested_amount):
            quotas = await self.get_tenant_quotas()
            current_usage = await self.get_current_usage(resource_type)
            quota_limit = getattr(quotas, f"max_{resource_type.value}", 0)
            
            raise QuotaViolationException(
                resource_type=resource_type,
                current_usage=current_usage,
                quota_limit=quota_limit,
                requested_amount=requested_amount,
                tenant_id=self.tenant_id,
                violation_type=violation_type
            )
    
    async def track_usage(
        self,
        resource_type: ResourceType,
        amount: int = 1,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Track resource usage for billing and analytics"""
        await self.usage_tracker.track_usage(resource_type, amount, metadata)
    
    async def get_usage_summary(self) -> Dict[str, Any]:
        """Get comprehensive usage summary for the tenant"""
        quotas = await self.get_tenant_quotas()
        
        usage_summary = {
            "tenant_id": self.tenant_id,
            "timestamp": datetime.utcnow().isoformat(),
            "resources": {}
        }
        
        for resource_type in ResourceType:
            current_usage = await self.get_current_usage(resource_type)
            quota_limit = getattr(quotas, f"max_{resource_type.value}", None)
            
            usage_summary["resources"][resource_type.value] = {
                "current_usage": current_usage,
                "quota_limit": quota_limit,
                "usage_percentage": (
                    (current_usage / quota_limit * 100) if quota_limit else 0
                ),
                "available": (quota_limit - current_usage) if quota_limit else None
            }
        
        return usage_summary
    
    async def check_soft_limits(self, threshold: float = 0.8) -> List[Dict[str, Any]]:
        """Check for resources approaching their limits"""
        warnings = []
        quotas = await self.get_tenant_quotas()
        
        for resource_type in ResourceType:
            quota_limit = getattr(quotas, f"max_{resource_type.value}", None)
            if not quota_limit:
                continue
            
            current_usage = await self.get_current_usage(resource_type)
            usage_percentage = current_usage / quota_limit
            
            if usage_percentage >= threshold:
                warnings.append({
                    "resource_type": resource_type.value,
                    "current_usage": current_usage,
                    "quota_limit": quota_limit,
                    "usage_percentage": usage_percentage * 100,
                    "threshold": threshold * 100
                })
        
        return warnings
    
    async def update_tenant_quotas(
        self,
        quota_updates: Dict[str, int],
        updated_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update tenant resource quotas"""
        stmt = select(Tenant).where(Tenant.id == self.tenant_id)
        result = await self.session.execute(stmt)
        tenant = result.scalar_one_or_none()
        
        if not tenant:
            raise ValueError(f"Tenant {self.tenant_id} not found")
        
        # Update quota values
        for resource_type, new_limit in quota_updates.items():
            if hasattr(tenant.resource_limits, f"max_{resource_type}"):
                setattr(tenant.resource_limits, f"max_{resource_type}", new_limit)
        
        tenant.updated_by = updated_by
        tenant.updated_at = datetime.utcnow()
        
        await self.session.commit()
        await self.session.refresh(tenant)
        
        # Clear cache
        if self.tenant_id in self._quota_cache:
            del self._quota_cache[self.tenant_id]
        
        return tenant.resource_limits


class QuotaEnforcementDecorator:
    """Decorator for automatic quota enforcement"""
    
    def __init__(
        self,
        resource_type: ResourceType,
        amount: int = 1,
        track_usage: bool = True
    ):
        self.resource_type = resource_type
        self.amount = amount
        self.track_usage = track_usage
    
    def __call__(self, func):
        async def wrapper(*args, **kwargs):
            # Extract tenant_id from arguments or kwargs
            tenant_id = None
            session = None
            
            # Look for tenant_id in kwargs
            if 'tenant_id' in kwargs:
                tenant_id = kwargs['tenant_id']
            
            # Look for session in args or kwargs
            if 'session' in kwargs:
                session = kwargs['session']
            elif args and hasattr(args[0], 'session'):
                session = args[0].session
                if hasattr(args[0], 'tenant_id'):
                    tenant_id = args[0].tenant_id
            
            if not tenant_id or not session:
                # If we can't find tenant_id or session, proceed without quota check
                return await func(*args, **kwargs)
            
            # Check and enforce quota
            quota_service = ResourceQuotaService(session, tenant_id)
            await quota_service.enforce_quota(self.resource_type, self.amount)
            
            # Execute the function
            result = await func(*args, **kwargs)
            
            # Track usage if requested
            if self.track_usage:
                await quota_service.track_usage(self.resource_type, self.amount)
            
            return result
        
        return wrapper


# Convenience decorators for common resource types
def enforce_agent_quota(amount: int = 1):
    """Decorator to enforce agent creation quota"""
    return QuotaEnforcementDecorator(ResourceType.AGENTS, amount)


def enforce_workflow_quota(amount: int = 1):
    """Decorator to enforce workflow creation quota"""
    return QuotaEnforcementDecorator(ResourceType.WORKFLOWS, amount)


def enforce_execution_quota(amount: int = 1):
    """Decorator to enforce execution quota"""
    return QuotaEnforcementDecorator(ResourceType.EXECUTIONS, amount)