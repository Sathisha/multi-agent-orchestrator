# Resource Quota Management Service
from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from datetime import datetime, timedelta
from enum import Enum
import uuid
import logging

from ..models.agent import Agent, AgentExecution
from ..models.workflow import Workflow, WorkflowExecution
from ..models.user import User
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
        violation_type: QuotaViolationType = QuotaViolationType.HARD_LIMIT
    ):
        self.resource_type = resource_type
        self.current_usage = current_usage
        self.quota_limit = quota_limit
        self.requested_amount = requested_amount
        self.violation_type = violation_type
        
        message = (
            f"Quota exceeded for {resource_type}: "
            f"current={current_usage}, limit={quota_limit}, requested={requested_amount}"
        )
        super().__init__(message)


class ResourceUsageTracker:
    """Tracks resource usage for billing and analytics"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
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
            f"Resource usage tracked: resource={resource_type}, amount={amount}, metadata={metadata}"
        )


class ResourceQuotaService:
    """Service for managing resource quotas and enforcement"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.usage_tracker = ResourceUsageTracker(session)
    
    async def get_quotas(self) -> Dict[str, Any]:
        """Get resource quotas"""
        # For now, return default hardcoded quotas
        # In a multi-tenant system, this would fetch tenant-specific quotas
        return {
            "max_agents": 100,
            "max_workflows": 50,
            "max_executions": 1000,
            "max_storage": 1024, # MB
            "max_api_calls": 10000,
            "max_users": 10
        }
    
    async def get_current_usage(self, resource_type: ResourceType) -> int:
        """Get current usage for a specific resource type"""
        if resource_type == ResourceType.AGENTS:
            stmt = select(func.count(Agent.id))
            result = await self.session.execute(stmt)
            return result.scalar() or 0
        
        elif resource_type == ResourceType.WORKFLOWS:
            stmt = select(func.count(Workflow.id))
            result = await self.session.execute(stmt)
            return result.scalar() or 0
        
        elif resource_type == ResourceType.EXECUTIONS:
            # Count executions in the last 24 hours
            since = datetime.utcnow() - timedelta(hours=24)
            stmt = select(func.count(AgentExecution.id)).where(
                AgentExecution.created_at >= since
            )
            result = await self.session.execute(stmt)
            return result.scalar() or 0
        
        elif resource_type == ResourceType.API_CALLS:
            # This would typically come from API gateway metrics
            # For now, return 0
            return 0
        
        elif resource_type == ResourceType.STORAGE:
            # Calculate storage usage across all data
            # This is a simplified calculation
            agent_storage = await self.session.execute(
                select(func.sum(func.length(Agent.config.cast(str))))
            )
            workflow_storage = await self.session.execute(
                select(func.sum(func.length(Workflow.bpmn_xml)))
            )
            
            total_storage = (agent_storage.scalar() or 0) + (workflow_storage.scalar() or 0)
            return total_storage
        
        elif resource_type == ResourceType.USERS:
            from ..models.user import User
            stmt = select(func.count(User.id)).where(
                User.is_active == True
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
        """Check if can use additional resources"""
        quotas = await self.get_quotas()
        current_usage = await self.get_current_usage(resource_type)
        
        # Get quota limit for resource type
        quota_limit = quotas.get(f"max_{resource_type.value}", None)
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
            quotas = await self.get_quotas()
            current_usage = await self.get_current_usage(resource_type)
            quota_limit = quotas.get(f"max_{resource_type.value}", 0)
            
            raise QuotaViolationException(
                resource_type=resource_type,
                current_usage=current_usage,
                quota_limit=quota_limit,
                requested_amount=requested_amount,
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
        """Get comprehensive usage summary"""
        quotas = await self.get_quotas()
        
        usage_summary = {
            "timestamp": datetime.utcnow().isoformat(),
            "resources": {}
        }
        
        for resource_type in ResourceType:
            current_usage = await self.get_current_usage(resource_type)
            quota_limit = quotas.get(f"max_{resource_type.value}", None)
            
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
        quotas = await self.get_quotas()
        
        for resource_type in ResourceType:
            quota_limit = quotas.get(f"max_{resource_type.value}", None)
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
    
    async def update_quotas(
        self,
        quota_updates: Dict[str, int],
        updated_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update resource quotas (admin only)"""
        # For now, update in-memory defaults or a config file
        # In a multi-tenant system, this would update tenant-specific quotas
        logger.info(f"Updating global quotas: {quota_updates}")
        
        # This is a placeholder for actual quota update logic
        # In a real system, you'd persist these changes
        updated_quotas = await self.get_quotas()
        updated_quotas.update(quota_updates) # Update in-memory dict for demonstration
        
        return updated_quotas


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
            # Extract session
            session = None
            if 'session' in kwargs:
                session = kwargs['session']
            elif args and hasattr(args[0], 'session'):
                session = args[0].session
            
            if not session:
                # If we can't find session, proceed without quota check
                return await func(*args, **kwargs)
            
            # Check and enforce quota
            quota_service = ResourceQuotaService(session)
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