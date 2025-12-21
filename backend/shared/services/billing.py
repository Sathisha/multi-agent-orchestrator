# Billing Integration Service
from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from datetime import datetime, timedelta
from enum import Enum
import uuid
import logging
from decimal import Decimal

from ..models.tenant import Tenant
from .base import BaseService
from .quota import ResourceType, ResourceUsageTracker

logger = logging.getLogger(__name__)


class BillingPeriod(str, Enum):
    """Billing period types"""
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUALLY = "annually"


class UsageMetric(str, Enum):
    """Usage metrics for billing"""
    AGENT_EXECUTIONS = "agent_executions"
    WORKFLOW_EXECUTIONS = "workflow_executions"
    API_CALLS = "api_calls"
    STORAGE_GB_HOURS = "storage_gb_hours"
    COMPUTE_MINUTES = "compute_minutes"
    ACTIVE_USERS = "active_users"


class BillingService:
    """Service for managing billing and usage-based pricing"""
    
    def __init__(self, session: AsyncSession, tenant_id: str):
        self.session = session
        self.tenant_id = tenant_id
        
        # Pricing configuration (would typically come from config/database)
        self.pricing_config = {
            UsageMetric.AGENT_EXECUTIONS: Decimal("0.01"),  # $0.01 per execution
            UsageMetric.WORKFLOW_EXECUTIONS: Decimal("0.05"),  # $0.05 per workflow execution
            UsageMetric.API_CALLS: Decimal("0.001"),  # $0.001 per API call
            UsageMetric.STORAGE_GB_HOURS: Decimal("0.10"),  # $0.10 per GB-hour
            UsageMetric.COMPUTE_MINUTES: Decimal("0.50"),  # $0.50 per compute minute
            UsageMetric.ACTIVE_USERS: Decimal("5.00"),  # $5.00 per active user per month
        }
    
    async def get_tenant(self) -> Tenant:
        """Get tenant information"""
        stmt = select(Tenant).where(Tenant.id == self.tenant_id)
        result = await self.session.execute(stmt)
        tenant = result.scalar_one_or_none()
        
        if not tenant:
            raise ValueError(f"Tenant {self.tenant_id} not found")
        
        return tenant
    
    async def calculate_usage_charges(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Calculate usage-based charges for a billing period"""
        tenant = await self.get_tenant()
        
        # This is a simplified calculation - in production, you'd query
        # detailed usage tracking tables
        charges = {
            "tenant_id": self.tenant_id,
            "billing_period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "line_items": [],
            "subtotal": Decimal("0.00"),
            "tax": Decimal("0.00"),
            "total": Decimal("0.00")
        }
        
        # Calculate agent execution charges
        from ..models.agent import AgentExecution
        exec_count = await self.session.execute(
            select(func.count(AgentExecution.id)).where(
                and_(
                    AgentExecution.tenant_id == self.tenant_id,
                    AgentExecution.created_at >= start_date,
                    AgentExecution.created_at < end_date
                )
            )
        )
        
        agent_executions = exec_count.scalar() or 0
        if agent_executions > 0:
            execution_charge = agent_executions * self.pricing_config[UsageMetric.AGENT_EXECUTIONS]
            charges["line_items"].append({
                "description": "Agent Executions",
                "quantity": agent_executions,
                "unit_price": float(self.pricing_config[UsageMetric.AGENT_EXECUTIONS]),
                "total": float(execution_charge)
            })
            charges["subtotal"] += execution_charge
        
        # Calculate workflow execution charges
        from ..models.workflow import WorkflowExecution
        workflow_count = await self.session.execute(
            select(func.count(WorkflowExecution.id)).where(
                and_(
                    WorkflowExecution.tenant_id == self.tenant_id,
                    WorkflowExecution.created_at >= start_date,
                    WorkflowExecution.created_at < end_date
                )
            )
        )
        
        workflow_executions = workflow_count.scalar() or 0
        if workflow_executions > 0:
            workflow_charge = workflow_executions * self.pricing_config[UsageMetric.WORKFLOW_EXECUTIONS]
            charges["line_items"].append({
                "description": "Workflow Executions",
                "quantity": workflow_executions,
                "unit_price": float(self.pricing_config[UsageMetric.WORKFLOW_EXECUTIONS]),
                "total": float(workflow_charge)
            })
            charges["subtotal"] += workflow_charge
        
        # Calculate active user charges (monthly)
        from ..models.tenant import TenantUser
        active_users = await self.session.execute(
            select(func.count(TenantUser.id)).where(
                and_(
                    TenantUser.tenant_id == self.tenant_id,
                    TenantUser.status == "active"
                )
            )
        )
        
        user_count = active_users.scalar() or 0
        if user_count > 0:
            # Calculate pro-rated user charges based on billing period
            days_in_period = (end_date - start_date).days
            monthly_rate = self.pricing_config[UsageMetric.ACTIVE_USERS]
            daily_rate = monthly_rate / 30  # Approximate daily rate
            user_charge = user_count * daily_rate * days_in_period
            
            charges["line_items"].append({
                "description": f"Active Users ({days_in_period} days)",
                "quantity": user_count,
                "unit_price": float(daily_rate * days_in_period),
                "total": float(user_charge)
            })
            charges["subtotal"] += user_charge
        
        # Calculate tax (simplified - would use proper tax calculation service)
        tax_rate = Decimal("0.08")  # 8% tax rate
        charges["tax"] = charges["subtotal"] * tax_rate
        charges["total"] = charges["subtotal"] + charges["tax"]
        
        # Convert Decimal to float for JSON serialization
        charges["subtotal"] = float(charges["subtotal"])
        charges["tax"] = float(charges["tax"])
        charges["total"] = float(charges["total"])
        
        return charges
    
    async def generate_invoice(
        self,
        billing_period_start: datetime,
        billing_period_end: datetime,
        invoice_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Generate an invoice for the billing period"""
        if invoice_date is None:
            invoice_date = datetime.utcnow()
        
        tenant = await self.get_tenant()
        charges = await self.calculate_usage_charges(billing_period_start, billing_period_end)
        
        invoice = {
            "invoice_id": str(uuid.uuid4()),
            "tenant_id": self.tenant_id,
            "tenant_name": tenant.name,
            "invoice_date": invoice_date.isoformat(),
            "due_date": (invoice_date + timedelta(days=30)).isoformat(),
            "billing_period": charges["billing_period"],
            "line_items": charges["line_items"],
            "subtotal": charges["subtotal"],
            "tax": charges["tax"],
            "total": charges["total"],
            "currency": "USD",
            "status": "pending"
        }
        
        # In production, you would save this invoice to a database
        logger.info(f"Generated invoice {invoice['invoice_id']} for tenant {self.tenant_id}")
        
        return invoice
    
    async def get_usage_forecast(
        self,
        forecast_days: int = 30
    ) -> Dict[str, Any]:
        """Generate usage forecast based on historical data"""
        # Get historical usage for the last 30 days
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=30)
        
        historical_charges = await self.calculate_usage_charges(start_date, end_date)
        
        # Simple linear projection (in production, use more sophisticated forecasting)
        daily_average = historical_charges["total"] / 30
        forecasted_total = daily_average * forecast_days
        
        forecast = {
            "tenant_id": self.tenant_id,
            "forecast_period_days": forecast_days,
            "historical_period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "total": historical_charges["total"]
            },
            "daily_average": daily_average,
            "forecasted_total": forecasted_total,
            "confidence": "low"  # Simple linear projection has low confidence
        }
        
        return forecast
    
    async def check_billing_alerts(self) -> List[Dict[str, Any]]:
        """Check for billing-related alerts"""
        alerts = []
        tenant = await self.get_tenant()
        
        # Check if tenant is approaching billing limits
        if hasattr(tenant.resource_limits, 'monthly_spend_limit'):
            monthly_limit = tenant.resource_limits.monthly_spend_limit
            if monthly_limit:
                # Get current month usage
                now = datetime.utcnow()
                month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                
                current_charges = await self.calculate_usage_charges(month_start, now)
                current_spend = current_charges["total"]
                
                # Alert if over 80% of monthly limit
                if current_spend > monthly_limit * 0.8:
                    alerts.append({
                        "type": "billing_limit_warning",
                        "severity": "high" if current_spend > monthly_limit * 0.9 else "medium",
                        "message": f"Monthly spend ({current_spend:.2f}) approaching limit ({monthly_limit:.2f})",
                        "current_spend": current_spend,
                        "monthly_limit": monthly_limit,
                        "percentage": (current_spend / monthly_limit) * 100
                    })
        
        return alerts


class NotificationService:
    """Service for sending quota and billing notifications"""
    
    def __init__(self, session: AsyncSession, tenant_id: str):
        self.session = session
        self.tenant_id = tenant_id
    
    async def send_quota_warning(
        self,
        resource_type: ResourceType,
        current_usage: int,
        quota_limit: int,
        threshold_percentage: float
    ):
        """Send quota warning notification"""
        # In production, this would integrate with email/SMS/Slack services
        message = (
            f"Quota Warning: {resource_type.value} usage is at "
            f"{threshold_percentage:.1f}% ({current_usage}/{quota_limit})"
        )
        
        logger.warning(f"Tenant {self.tenant_id}: {message}")
        
        # Here you would integrate with notification services like:
        # - Email service (SendGrid, AWS SES)
        # - Slack webhooks
        # - SMS service (Twilio)
        # - In-app notifications
    
    async def send_quota_exceeded(
        self,
        resource_type: ResourceType,
        current_usage: int,
        quota_limit: int
    ):
        """Send quota exceeded notification"""
        message = (
            f"Quota Exceeded: {resource_type.value} usage ({current_usage}) "
            f"has exceeded the limit ({quota_limit})"
        )
        
        logger.error(f"Tenant {self.tenant_id}: {message}")
    
    async def send_billing_alert(
        self,
        alert_type: str,
        message: str,
        severity: str = "medium"
    ):
        """Send billing-related alert"""
        logger.warning(f"Billing Alert - Tenant {self.tenant_id}: {message}")
    
    async def send_invoice_notification(
        self,
        invoice: Dict[str, Any]
    ):
        """Send invoice notification"""
        message = (
            f"New invoice generated: {invoice['invoice_id']} "
            f"for ${invoice['total']:.2f}, due {invoice['due_date']}"
        )
        
        logger.info(f"Tenant {self.tenant_id}: {message}")


class ResourceMonitoringService:
    """Service for monitoring resource usage and triggering alerts"""
    
    def __init__(self, session: AsyncSession, tenant_id: str):
        self.session = session
        self.tenant_id = tenant_id
        self.notification_service = NotificationService(session, tenant_id)
    
    async def check_and_alert_quotas(self):
        """Check all quotas and send alerts if necessary"""
        from .quota import ResourceQuotaService
        
        quota_service = ResourceQuotaService(self.session, self.tenant_id)
        
        # Check for soft limit warnings (80% threshold)
        warnings = await quota_service.check_soft_limits(threshold=0.8)
        
        for warning in warnings:
            await self.notification_service.send_quota_warning(
                resource_type=ResourceType(warning["resource_type"]),
                current_usage=warning["current_usage"],
                quota_limit=warning["quota_limit"],
                threshold_percentage=warning["usage_percentage"]
            )
    
    async def check_and_alert_billing(self):
        """Check billing status and send alerts if necessary"""
        billing_service = BillingService(self.session, self.tenant_id)
        alerts = await billing_service.check_billing_alerts()
        
        for alert in alerts:
            await self.notification_service.send_billing_alert(
                alert_type=alert["type"],
                message=alert["message"],
                severity=alert["severity"]
            )
    
    async def run_monitoring_cycle(self):
        """Run a complete monitoring cycle"""
        try:
            await self.check_and_alert_quotas()
            await self.check_and_alert_billing()
            logger.info(f"Monitoring cycle completed for tenant {self.tenant_id}")
        except Exception as e:
            logger.error(f"Error in monitoring cycle for tenant {self.tenant_id}: {e}")