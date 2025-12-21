# Tenant Analytics and Reporting Service
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc, text
from datetime import datetime, timedelta
from enum import Enum
import logging

from ..models.tenant import Tenant, TenantUser
from ..models.agent import Agent, AgentExecution
from ..models.workflow import Workflow, WorkflowExecution
from ..models.audit import AuditLog
from .base import BaseService

logger = logging.getLogger(__name__)


class AnalyticsTimeframe(str, Enum):
    """Analytics timeframe options"""
    LAST_24_HOURS = "24h"
    LAST_7_DAYS = "7d"
    LAST_30_DAYS = "30d"
    LAST_90_DAYS = "90d"
    LAST_YEAR = "1y"


class TenantAnalyticsService:
    """Service for tenant analytics and reporting"""
    
    def __init__(self, session: AsyncSession, tenant_id: str):
        self.session = session
        self.tenant_id = tenant_id
    
    def _get_timeframe_start(self, timeframe: AnalyticsTimeframe) -> datetime:
        """Get start datetime for timeframe"""
        now = datetime.utcnow()
        
        if timeframe == AnalyticsTimeframe.LAST_24_HOURS:
            return now - timedelta(hours=24)
        elif timeframe == AnalyticsTimeframe.LAST_7_DAYS:
            return now - timedelta(days=7)
        elif timeframe == AnalyticsTimeframe.LAST_30_DAYS:
            return now - timedelta(days=30)
        elif timeframe == AnalyticsTimeframe.LAST_90_DAYS:
            return now - timedelta(days=90)
        elif timeframe == AnalyticsTimeframe.LAST_YEAR:
            return now - timedelta(days=365)
        else:
            return now - timedelta(days=30)  # Default to 30 days
    
    async def get_tenant_overview(self) -> Dict[str, Any]:
        """Get high-level tenant overview statistics"""
        # Get tenant info
        tenant_stmt = select(Tenant).where(Tenant.id == self.tenant_id)
        tenant_result = await self.session.execute(tenant_stmt)
        tenant = tenant_result.scalar_one_or_none()
        
        if not tenant:
            raise ValueError(f"Tenant {self.tenant_id} not found")
        
        # Get counts
        agents_count = await self.session.execute(
            select(func.count(Agent.id)).where(Agent.tenant_id == self.tenant_id)
        )
        
        workflows_count = await self.session.execute(
            select(func.count(Workflow.id)).where(Workflow.tenant_id == self.tenant_id)
        )
        
        users_count = await self.session.execute(
            select(func.count(TenantUser.id)).where(
                and_(
                    TenantUser.tenant_id == self.tenant_id,
                    TenantUser.status == "active"
                )
            )
        )
        
        # Get recent activity (last 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        
        recent_executions = await self.session.execute(
            select(func.count(AgentExecution.id)).where(
                and_(
                    AgentExecution.tenant_id == self.tenant_id,
                    AgentExecution.created_at >= thirty_days_ago
                )
            )
        )
        
        recent_workflow_executions = await self.session.execute(
            select(func.count(WorkflowExecution.id)).where(
                and_(
                    WorkflowExecution.tenant_id == self.tenant_id,
                    WorkflowExecution.created_at >= thirty_days_ago
                )
            )
        )
        
        return {
            "tenant_id": self.tenant_id,
            "tenant_name": tenant.name,
            "tenant_status": tenant.status,
            "created_at": tenant.created_at.isoformat(),
            "totals": {
                "agents": agents_count.scalar() or 0,
                "workflows": workflows_count.scalar() or 0,
                "active_users": users_count.scalar() or 0
            },
            "recent_activity": {
                "agent_executions_30d": recent_executions.scalar() or 0,
                "workflow_executions_30d": recent_workflow_executions.scalar() or 0
            }
        }
    
    async def get_usage_analytics(
        self,
        timeframe: AnalyticsTimeframe = AnalyticsTimeframe.LAST_30_DAYS
    ) -> Dict[str, Any]:
        """Get detailed usage analytics"""
        start_date = self._get_timeframe_start(timeframe)
        end_date = datetime.utcnow()
        
        # Agent execution analytics
        agent_exec_stats = await self.session.execute(
            select(
                func.count(AgentExecution.id).label('total_executions'),
                func.count(AgentExecution.id).filter(AgentExecution.status == 'completed').label('successful'),
                func.count(AgentExecution.id).filter(AgentExecution.status == 'failed').label('failed'),
                func.avg(AgentExecution.execution_time_ms).label('avg_execution_time'),
                func.sum(AgentExecution.tokens_used).label('total_tokens'),
                func.sum(AgentExecution.cost).label('total_cost')
            ).where(
                and_(
                    AgentExecution.tenant_id == self.tenant_id,
                    AgentExecution.created_at >= start_date,
                    AgentExecution.created_at <= end_date
                )
            )
        )
        
        exec_stats = agent_exec_stats.first()
        
        # Workflow execution analytics
        workflow_exec_stats = await self.session.execute(
            select(
                func.count(WorkflowExecution.id).label('total_workflows'),
                func.count(WorkflowExecution.id).filter(WorkflowExecution.status == 'completed').label('successful_workflows'),
                func.count(WorkflowExecution.id).filter(WorkflowExecution.status == 'failed').label('failed_workflows'),
                func.avg(
                    func.extract('epoch', WorkflowExecution.completed_at - WorkflowExecution.started_at)
                ).label('avg_workflow_duration')
            ).where(
                and_(
                    WorkflowExecution.tenant_id == self.tenant_id,
                    WorkflowExecution.created_at >= start_date,
                    WorkflowExecution.created_at <= end_date
                )
            )
        )
        
        workflow_stats = workflow_exec_stats.first()
        
        # Most active agents
        top_agents = await self.session.execute(
            select(
                Agent.id,
                Agent.name,
                func.count(AgentExecution.id).label('execution_count')
            ).join(
                AgentExecution, Agent.id == AgentExecution.agent_id
            ).where(
                and_(
                    Agent.tenant_id == self.tenant_id,
                    AgentExecution.created_at >= start_date,
                    AgentExecution.created_at <= end_date
                )
            ).group_by(Agent.id, Agent.name).order_by(desc('execution_count')).limit(10)
        )
        
        return {
            "timeframe": timeframe.value,
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "agent_executions": {
                "total": exec_stats.total_executions or 0,
                "successful": exec_stats.successful or 0,
                "failed": exec_stats.failed or 0,
                "success_rate": (
                    (exec_stats.successful or 0) / max(exec_stats.total_executions or 1, 1)
                ),
                "avg_execution_time_ms": float(exec_stats.avg_execution_time or 0),
                "total_tokens_used": exec_stats.total_tokens or 0,
                "total_cost": float(exec_stats.total_cost or 0)
            },
            "workflow_executions": {
                "total": workflow_stats.total_workflows or 0,
                "successful": workflow_stats.successful_workflows or 0,
                "failed": workflow_stats.failed_workflows or 0,
                "success_rate": (
                    (workflow_stats.successful_workflows or 0) / 
                    max(workflow_stats.total_workflows or 1, 1)
                ),
                "avg_duration_seconds": float(workflow_stats.avg_workflow_duration or 0)
            },
            "top_agents": [
                {
                    "agent_id": row.id,
                    "agent_name": row.name,
                    "execution_count": row.execution_count
                }
                for row in top_agents.fetchall()
            ]
        }
    
    async def get_daily_activity(
        self,
        timeframe: AnalyticsTimeframe = AnalyticsTimeframe.LAST_30_DAYS
    ) -> Dict[str, Any]:
        """Get daily activity breakdown"""
        start_date = self._get_timeframe_start(timeframe)
        end_date = datetime.utcnow()
        
        # Daily agent executions
        daily_executions = await self.session.execute(
            text("""
                SELECT 
                    DATE(created_at) as date,
                    COUNT(*) as executions,
                    COUNT(CASE WHEN status = 'completed' THEN 1 END) as successful,
                    COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed
                FROM agent_executions 
                WHERE tenant_id = :tenant_id 
                    AND created_at >= :start_date 
                    AND created_at <= :end_date
                GROUP BY DATE(created_at)
                ORDER BY date
            """),
            {
                "tenant_id": self.tenant_id,
                "start_date": start_date,
                "end_date": end_date
            }
        )
        
        # Daily workflow executions
        daily_workflows = await self.session.execute(
            text("""
                SELECT 
                    DATE(created_at) as date,
                    COUNT(*) as workflows,
                    COUNT(CASE WHEN status = 'completed' THEN 1 END) as successful,
                    COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed
                FROM workflow_executions 
                WHERE tenant_id = :tenant_id 
                    AND created_at >= :start_date 
                    AND created_at <= :end_date
                GROUP BY DATE(created_at)
                ORDER BY date
            """),
            {
                "tenant_id": self.tenant_id,
                "start_date": start_date,
                "end_date": end_date
            }
        )
        
        return {
            "timeframe": timeframe.value,
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "daily_agent_executions": [
                {
                    "date": row.date.isoformat(),
                    "total": row.executions,
                    "successful": row.successful,
                    "failed": row.failed
                }
                for row in daily_executions.fetchall()
            ],
            "daily_workflow_executions": [
                {
                    "date": row.date.isoformat(),
                    "total": row.workflows,
                    "successful": row.successful,
                    "failed": row.failed
                }
                for row in daily_workflows.fetchall()
            ]
        }
    
    async def get_error_analytics(
        self,
        timeframe: AnalyticsTimeframe = AnalyticsTimeframe.LAST_30_DAYS
    ) -> Dict[str, Any]:
        """Get error analytics and patterns"""
        start_date = self._get_timeframe_start(timeframe)
        end_date = datetime.utcnow()
        
        # Most common agent execution errors
        agent_errors = await self.session.execute(
            select(
                AgentExecution.error_message,
                func.count(AgentExecution.id).label('error_count')
            ).where(
                and_(
                    AgentExecution.tenant_id == self.tenant_id,
                    AgentExecution.status == 'failed',
                    AgentExecution.error_message.isnot(None),
                    AgentExecution.created_at >= start_date,
                    AgentExecution.created_at <= end_date
                )
            ).group_by(AgentExecution.error_message).order_by(desc('error_count')).limit(10)
        )
        
        # Most common workflow execution errors
        workflow_errors = await self.session.execute(
            select(
                WorkflowExecution.error_message,
                func.count(WorkflowExecution.id).label('error_count')
            ).where(
                and_(
                    WorkflowExecution.tenant_id == self.tenant_id,
                    WorkflowExecution.status == 'failed',
                    WorkflowExecution.error_message.isnot(None),
                    WorkflowExecution.created_at >= start_date,
                    WorkflowExecution.created_at <= end_date
                )
            ).group_by(WorkflowExecution.error_message).order_by(desc('error_count')).limit(10)
        )
        
        return {
            "timeframe": timeframe.value,
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "top_agent_errors": [
                {
                    "error_message": row.error_message,
                    "count": row.error_count
                }
                for row in agent_errors.fetchall()
            ],
            "top_workflow_errors": [
                {
                    "error_message": row.error_message,
                    "count": row.error_count
                }
                for row in workflow_errors.fetchall()
            ]
        }
    
    async def get_user_activity(
        self,
        timeframe: AnalyticsTimeframe = AnalyticsTimeframe.LAST_30_DAYS
    ) -> Dict[str, Any]:
        """Get user activity analytics"""
        start_date = self._get_timeframe_start(timeframe)
        end_date = datetime.utcnow()
        
        # Most active users (based on audit logs)
        active_users = await self.session.execute(
            select(
                AuditLog.user_id,
                func.count(AuditLog.id).label('activity_count'),
                func.max(AuditLog.timestamp).label('last_activity')
            ).where(
                and_(
                    AuditLog.tenant_id == self.tenant_id,
                    AuditLog.user_id.isnot(None),
                    AuditLog.timestamp >= start_date,
                    AuditLog.timestamp <= end_date
                )
            ).group_by(AuditLog.user_id).order_by(desc('activity_count')).limit(10)
        )
        
        # Activity by event type
        activity_by_type = await self.session.execute(
            select(
                AuditLog.event_type,
                func.count(AuditLog.id).label('event_count')
            ).where(
                and_(
                    AuditLog.tenant_id == self.tenant_id,
                    AuditLog.timestamp >= start_date,
                    AuditLog.timestamp <= end_date
                )
            ).group_by(AuditLog.event_type).order_by(desc('event_count'))
        )
        
        return {
            "timeframe": timeframe.value,
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "most_active_users": [
                {
                    "user_id": row.user_id,
                    "activity_count": row.activity_count,
                    "last_activity": row.last_activity.isoformat() if row.last_activity else None
                }
                for row in active_users.fetchall()
            ],
            "activity_by_type": [
                {
                    "event_type": row.event_type,
                    "count": row.event_count
                }
                for row in activity_by_type.fetchall()
            ]
        }
    
    async def generate_tenant_report(
        self,
        timeframe: AnalyticsTimeframe = AnalyticsTimeframe.LAST_30_DAYS
    ) -> Dict[str, Any]:
        """Generate comprehensive tenant report"""
        overview = await self.get_tenant_overview()
        usage = await self.get_usage_analytics(timeframe)
        daily_activity = await self.get_daily_activity(timeframe)
        errors = await self.get_error_analytics(timeframe)
        user_activity = await self.get_user_activity(timeframe)
        
        return {
            "report_id": f"tenant-report-{self.tenant_id}-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}",
            "generated_at": datetime.utcnow().isoformat(),
            "tenant_overview": overview,
            "usage_analytics": usage,
            "daily_activity": daily_activity,
            "error_analytics": errors,
            "user_activity": user_activity
        }