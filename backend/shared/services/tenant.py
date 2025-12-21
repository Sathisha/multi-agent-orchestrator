"""Multi-tenant service for managing tenant context and operations."""

import logging
from typing import Optional, List, Dict, Any, Tuple
from uuid import UUID
from datetime import datetime, timedelta

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models.tenant import Tenant, TenantInvitation, TenantStatus, TenantPlan, TenantContext
from ..models.user import User
from ..database.connection import get_async_db


logger = logging.getLogger(__name__)


class TenantService:
    """Service for managing multi-tenant operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_tenant_by_id(self, tenant_id: UUID) -> Optional[Tenant]:
        """Get tenant by ID."""
        query = select(Tenant).where(
            Tenant.id == tenant_id,
            Tenant.is_deleted == False
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_tenant_by_slug(self, slug: str) -> Optional[Tenant]:
        """Get tenant by slug."""
        query = select(Tenant).where(
            Tenant.slug == slug,
            Tenant.is_deleted == False
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def create_tenant(
        self,
        name: str,
        slug: str,
        display_name: str,
        primary_email: str,
        plan: TenantPlan = TenantPlan.FREE,
        **kwargs
    ) -> Tenant:
        """Create a new tenant."""
        # Check if slug is already taken
        existing = await self.get_tenant_by_slug(slug)
        if existing:
            raise ValueError(f"Tenant slug '{slug}' is already taken")
        
        # Set trial period for new tenants
        trial_ends_at = datetime.utcnow() + timedelta(days=14)  # 14-day trial
        
        tenant = Tenant(
            name=name,
            slug=slug,
            display_name=display_name,
            primary_email=primary_email,
            plan=plan,
            status=TenantStatus.TRIAL,
            trial_ends_at=trial_ends_at,
            **kwargs
        )
        
        self.session.add(tenant)
        await self.session.commit()
        await self.session.refresh(tenant)
        
        logger.info(f"Created tenant: {tenant.name} (slug: {tenant.slug})")
        return tenant
    
    async def update_tenant(self, tenant_id: UUID, **updates) -> Optional[Tenant]:
        """Update tenant information."""
        tenant = await self.get_tenant_by_id(tenant_id)
        if not tenant:
            return None
        
        for key, value in updates.items():
            if hasattr(tenant, key):
                setattr(tenant, key, value)
        
        await self.session.commit()
        await self.session.refresh(tenant)
        
        logger.info(f"Updated tenant: {tenant.name}")
        return tenant
    
    async def suspend_tenant(self, tenant_id: UUID, reason: str = None) -> bool:
        """Suspend a tenant."""
        tenant = await self.get_tenant_by_id(tenant_id)
        if not tenant:
            return False
        
        tenant.status = TenantStatus.SUSPENDED
        if reason:
            tenant.settings = tenant.settings or {}
            tenant.settings['suspension_reason'] = reason
            tenant.settings['suspended_at'] = datetime.utcnow().isoformat()
        
        await self.session.commit()
        
        logger.warning(f"Suspended tenant: {tenant.name} (reason: {reason})")
        return True
    
    async def activate_tenant(self, tenant_id: UUID) -> bool:
        """Activate a suspended tenant."""
        tenant = await self.get_tenant_by_id(tenant_id)
        if not tenant:
            return False
        
        tenant.status = TenantStatus.ACTIVE
        if tenant.settings:
            tenant.settings.pop('suspension_reason', None)
            tenant.settings.pop('suspended_at', None)
        
        await self.session.commit()
        
        logger.info(f"Activated tenant: {tenant.name}")
        return True
    
    async def get_tenant_users(self, tenant_id: UUID) -> List[User]:
        """Get all users for a tenant."""
        query = select(User).where(
            User.tenant_id == tenant_id,
            User.is_deleted == False
        ).options(selectinload(User.roles))
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def check_resource_limits(self, tenant_id: UUID) -> Dict[str, Any]:
        """Check current resource usage against limits."""
        tenant = await self.get_tenant_by_id(tenant_id)
        if not tenant:
            return {}
        
        # Get current usage
        user_count = await self.session.scalar(
            select(func.count(User.id)).where(
                User.tenant_id == tenant_id,
                User.is_deleted == False
            )
        )
        
        # Add more resource counts as needed
        # agent_count = await self.session.scalar(...)
        # workflow_count = await self.session.scalar(...)
        
        return {
            'limits': {
                'users': tenant.max_users,
                'agents': tenant.max_agents,
                'workflows': tenant.max_workflows,
                'storage_gb': tenant.max_storage_gb,
                'api_calls_per_month': tenant.max_api_calls_per_month,
            },
            'usage': {
                'users': user_count,
                'agents': 0,  # TODO: Implement when Agent model is updated
                'workflows': 0,  # TODO: Implement when Workflow model is updated
                'storage_gb': 0,  # TODO: Implement storage tracking
                'api_calls_this_month': 0,  # TODO: Implement API call tracking
            },
            'percentage': {
                'users': (user_count / tenant.max_users * 100) if tenant.max_users > 0 else 0,
                # Add more percentages as needed
            }
        }
    
    async def create_invitation(
        self,
        tenant_id: UUID,
        email: str,
        invited_by_user_id: UUID,
        role_ids: List[str] = None,
        expires_in_days: int = 7
    ) -> TenantInvitation:
        """Create a tenant invitation."""
        expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
        
        invitation = TenantInvitation(
            tenant_id=tenant_id,
            email=email,
            invited_by_user_id=invited_by_user_id,
            expires_at=expires_at,
            role_ids=role_ids or []
        )
        
        self.session.add(invitation)
        await self.session.commit()
        await self.session.refresh(invitation)
        
        logger.info(f"Created invitation for {email} to tenant {tenant_id}")
        return invitation
    
    async def accept_invitation(self, invitation_id: UUID, user_id: UUID) -> bool:
        """Accept a tenant invitation."""
        query = select(TenantInvitation).where(TenantInvitation.id == invitation_id)
        result = await self.session.execute(query)
        invitation = result.scalar_one_or_none()
        
        if not invitation or not invitation.is_valid():
            return False
        
        # Update user's tenant
        user = await self.session.get(User, user_id)
        if not user:
            return False
        
        user.tenant_id = invitation.tenant_id
        
        # Assign roles if specified
        if invitation.role_ids:
            # TODO: Implement role assignment
            pass
        
        # Mark invitation as accepted
        invitation.status = 'accepted'
        invitation.accepted_at = datetime.utcnow()
        
        await self.session.commit()
        
        logger.info(f"User {user_id} accepted invitation to tenant {invitation.tenant_id}")
        return True
    
    async def get_tenant_context(self, tenant_id: UUID, user_id: UUID = None) -> Optional[TenantContext]:
        """Get tenant context for request processing."""
        tenant = await self.get_tenant_by_id(tenant_id)
        if not tenant:
            return None
        
        user = None
        if user_id:
            user = await self.session.get(User, user_id)
        
        return TenantContext(tenant=tenant, user=user)


class TenantMiddleware:
    """Middleware for extracting tenant context from requests."""
    
    @staticmethod
    def extract_tenant_from_subdomain(host: str) -> Optional[str]:
        """Extract tenant slug from subdomain."""
        if not host:
            return None
        
        # Remove port if present
        host = host.split(':')[0]
        
        # Split by dots and check if it's a subdomain
        parts = host.split('.')
        if len(parts) >= 3:  # subdomain.domain.tld
            return parts[0]
        
        return None
    
    @staticmethod
    def extract_tenant_from_header(headers: Dict[str, str]) -> Optional[str]:
        """Extract tenant slug from X-Tenant-Slug header."""
        return headers.get('x-tenant-slug') or headers.get('X-Tenant-Slug')
    
    @staticmethod
    def extract_tenant_from_path(path: str) -> Optional[str]:
        """Extract tenant slug from URL path like /tenant/{slug}/..."""
        if not path.startswith('/tenant/'):
            return None
        
        parts = path.split('/')
        if len(parts) >= 3:
            return parts[2]
        
        return None
    
    @classmethod
    async def get_tenant_context(
        self,
        host: str = None,
        headers: Dict[str, str] = None,
        path: str = None,
        user_id: UUID = None
    ) -> Optional[TenantContext]:
        """Get tenant context from request information."""
        tenant_slug = None
        
        # Try different methods to extract tenant
        if host:
            tenant_slug = self.extract_tenant_from_subdomain(host)
        
        if not tenant_slug and headers:
            tenant_slug = self.extract_tenant_from_header(headers)
        
        if not tenant_slug and path:
            tenant_slug = self.extract_tenant_from_path(path)
        
        if not tenant_slug:
            return None
        
        # Get tenant context
        async with get_async_db() as session:
            service = TenantService(session)
            tenant = await service.get_tenant_by_slug(tenant_slug)
            
            if not tenant:
                return None
            
            return await service.get_tenant_context(tenant.id, user_id)


# Row-Level Security (RLS) helper functions
class TenantRLS:
    """Helper functions for implementing Row-Level Security."""
    
    @staticmethod
    def add_tenant_filter(query, tenant_id: UUID, model_class):
        """Add tenant filter to a query."""
        if hasattr(model_class, 'tenant_id'):
            return query.where(model_class.tenant_id == tenant_id)
        return query
    
    @staticmethod
    def ensure_tenant_access(obj, tenant_id: UUID):
        """Ensure an object belongs to the specified tenant."""
        if hasattr(obj, 'tenant_id') and obj.tenant_id != tenant_id:
            raise PermissionError(f"Access denied: Object does not belong to tenant {tenant_id}")
    
    @staticmethod
    def set_tenant_on_create(obj, tenant_id: UUID):
        """Set tenant_id on object creation."""
        if hasattr(obj, 'tenant_id'):
            obj.tenant_id = tenant_id


# Additional methods for tenant administration
class TenantAdminService(TenantService):
    """Extended tenant service for administration operations."""
    
    async def list_tenants(
        self,
        skip: int = 0,
        limit: int = 100,
        status_filter: Optional[str] = None,
        subscription_plan: Optional[str] = None,
        search: Optional[str] = None
    ) -> tuple[List[Tenant], int]:
        """List tenants with filtering and pagination."""
        query = select(Tenant).where(Tenant.is_deleted == False)
        
        # Apply filters
        if status_filter:
            query = query.where(Tenant.status == status_filter)
        
        if subscription_plan:
            query = query.where(Tenant.plan == subscription_plan)
        
        if search:
            search_term = f"%{search}%"
            query = query.where(
                (Tenant.name.ilike(search_term)) |
                (Tenant.display_name.ilike(search_term)) |
                (Tenant.primary_email.ilike(search_term))
            )
        
        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_count = await self.session.scalar(count_query)
        
        # Apply pagination and ordering
        query = query.order_by(Tenant.created_at.desc()).offset(skip).limit(limit)
        
        result = await self.session.execute(query)
        tenants = result.scalars().all()
        
        return tenants, total_count
    
    async def get_tenant(self, tenant_id: UUID) -> Optional[Tenant]:
        """Get tenant with detailed information."""
        query = select(Tenant).where(
            Tenant.id == tenant_id,
            Tenant.is_deleted == False
        ).options(
            selectinload(Tenant.users),
            selectinload(Tenant.invitations)
        )
        
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def delete_tenant(self, tenant_id: UUID, force: bool = False) -> bool:
        """Delete a tenant and all associated data."""
        tenant = await self.get_tenant_by_id(tenant_id)
        if not tenant:
            return False
        
        # Check for active resources if not forcing
        if not force:
            user_count = await self.session.scalar(
                select(func.count(User.id)).where(
                    User.tenant_id == tenant_id,
                    User.is_deleted == False
                )
            )
            
            if user_count > 0:
                raise ValueError(f"Cannot delete tenant with {user_count} active users. Use force=True to override.")
        
        # Soft delete the tenant
        tenant.is_deleted = True
        tenant.deleted_at = datetime.utcnow()
        
        # Also soft delete all associated users
        users_query = select(User).where(
            User.tenant_id == tenant_id,
            User.is_deleted == False
        )
        result = await self.session.execute(users_query)
        users = result.scalars().all()
        
        for user in users:
            user.is_deleted = True
            user.deleted_at = datetime.utcnow()
        
        await self.session.commit()
        
        logger.warning(f"Deleted tenant: {tenant.name} (force: {force})")
        return True
    
    async def suspend_tenant(
        self,
        tenant_id: UUID,
        reason: str,
        suspended_by: UUID,
        suspension_expires_at: Optional[datetime] = None
    ) -> Optional[Tenant]:
        """Suspend a tenant with detailed tracking."""
        tenant = await self.get_tenant_by_id(tenant_id)
        if not tenant:
            return None
        
        tenant.status = TenantStatus.SUSPENDED
        tenant.settings = tenant.settings or {}
        tenant.settings.update({
            'suspension_reason': reason,
            'suspended_at': datetime.utcnow().isoformat(),
            'suspended_by': str(suspended_by),
            'suspension_expires_at': suspension_expires_at.isoformat() if suspension_expires_at else None
        })
        
        await self.session.commit()
        await self.session.refresh(tenant)
        
        logger.warning(f"Suspended tenant: {tenant.name} by user {suspended_by} (reason: {reason})")
        return tenant
    
    async def reactivate_tenant(
        self,
        tenant_id: UUID,
        reactivated_by: UUID,
        notes: Optional[str] = None
    ) -> Optional[Tenant]:
        """Reactivate a suspended tenant."""
        tenant = await self.get_tenant_by_id(tenant_id)
        if not tenant:
            return None
        
        tenant.status = TenantStatus.ACTIVE
        tenant.settings = tenant.settings or {}
        
        # Clear suspension info and add reactivation info
        suspension_info = {
            'previous_suspension_reason': tenant.settings.pop('suspension_reason', None),
            'previous_suspended_at': tenant.settings.pop('suspended_at', None),
            'previous_suspended_by': tenant.settings.pop('suspended_by', None),
            'suspension_expires_at': tenant.settings.pop('suspension_expires_at', None)
        }
        
        tenant.settings.update({
            'reactivated_at': datetime.utcnow().isoformat(),
            'reactivated_by': str(reactivated_by),
            'reactivation_notes': notes,
            'suspension_history': tenant.settings.get('suspension_history', []) + [suspension_info]
        })
        
        await self.session.commit()
        await self.session.refresh(tenant)
        
        logger.info(f"Reactivated tenant: {tenant.name} by user {reactivated_by}")
        return tenant
    
    async def get_user_tenant_membership(
        self,
        user_id: UUID,
        tenant_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """Get user's membership details for a specific tenant."""
        query = select(User).where(
            User.id == user_id,
            User.tenant_id == tenant_id,
            User.is_deleted == False
        ).options(selectinload(User.roles))
        
        result = await self.session.execute(query)
        user = result.scalar_one_or_none()
        
        if not user:
            return None
        
        # Determine user role (simplified - in real implementation, use proper RBAC)
        role = "member"  # default
        if user.roles:
            for user_role in user.roles:
                if user_role.name == "tenant_admin":
                    role = "admin"
                    break
                elif user_role.name == "tenant_manager":
                    role = "manager"
                    break
        
        return {
            "user_id": user.id,
            "tenant_id": tenant_id,
            "role": role,
            "status": "active" if not user.is_deleted else "inactive",
            "joined_at": user.created_at
        }
    
    async def list_tenant_users(self, tenant_id: UUID) -> List[User]:
        """List all users in a tenant with their roles."""
        query = select(User).where(
            User.tenant_id == tenant_id,
            User.is_deleted == False
        ).options(selectinload(User.roles))
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def invite_user_to_tenant(
        self,
        tenant_id: UUID,
        email: str,
        role: str,
        invited_by: UUID,
        message: Optional[str] = None
    ) -> TenantInvitation:
        """Invite a user to join a tenant."""
        # Check if user is already in tenant
        existing_user = await self.session.scalar(
            select(User).where(
                User.email == email,
                User.tenant_id == tenant_id,
                User.is_deleted == False
            )
        )
        
        if existing_user:
            raise ValueError(f"User {email} is already a member of this tenant")
        
        # Check for existing pending invitation
        existing_invitation = await self.session.scalar(
            select(TenantInvitation).where(
                TenantInvitation.tenant_id == tenant_id,
                TenantInvitation.email == email,
                TenantInvitation.status == 'pending'
            )
        )
        
        if existing_invitation:
            raise ValueError(f"Pending invitation already exists for {email}")
        
        # Create invitation
        invitation = TenantInvitation(
            tenant_id=tenant_id,
            email=email,
            invited_by_user_id=invited_by,
            role_ids=[role],  # Store role in role_ids for now
            expires_at=datetime.utcnow() + timedelta(days=7),
            message=message
        )
        
        self.session.add(invitation)
        await self.session.commit()
        await self.session.refresh(invitation)
        
        logger.info(f"Invited {email} to tenant {tenant_id} with role {role}")
        return invitation
    
    async def update_tenant_user(
        self,
        tenant_id: UUID,
        user_id: UUID,
        role: Optional[str] = None,
        status: Optional[str] = None
    ) -> Optional[User]:
        """Update a tenant user's role or status."""
        user = await self.session.scalar(
            select(User).where(
                User.id == user_id,
                User.tenant_id == tenant_id
            ).options(selectinload(User.roles))
        )
        
        if not user:
            return None
        
        # Update status
        if status:
            if status == "inactive":
                user.is_deleted = True
                user.deleted_at = datetime.utcnow()
            elif status == "active":
                user.is_deleted = False
                user.deleted_at = None
        
        # Update role (simplified - in real implementation, use proper RBAC)
        if role:
            # This is a simplified role update - in practice, you'd manage roles properly
            logger.info(f"Updated user {user_id} role to {role} in tenant {tenant_id}")
        
        await self.session.commit()
        await self.session.refresh(user)
        
        return user
    
    async def remove_user_from_tenant(self, tenant_id: UUID, user_id: UUID) -> bool:
        """Remove a user from a tenant."""
        user = await self.session.scalar(
            select(User).where(
                User.id == user_id,
                User.tenant_id == tenant_id,
                User.is_deleted == False
            )
        )
        
        if not user:
            return False
        
        # Soft delete the user
        user.is_deleted = True
        user.deleted_at = datetime.utcnow()
        
        await self.session.commit()
        
        logger.info(f"Removed user {user_id} from tenant {tenant_id}")
        return True
    
    async def get_tenant_configuration(self, tenant_id: UUID) -> Dict[str, Any]:
        """Get tenant configuration and branding settings."""
        tenant = await self.get_tenant_by_id(tenant_id)
        if not tenant:
            return {}
        
        return {
            "id": str(tenant.id),
            "tenant_id": str(tenant.id),
            "branding": tenant.settings.get("branding", {}),
            "features": tenant.settings.get("features", {}),
            "integrations": tenant.settings.get("integrations", {}),
            "security": tenant.settings.get("security", {}),
            "notifications": tenant.settings.get("notifications", {}),
            "updated_at": tenant.updated_at
        }
    
    async def update_tenant_configuration(
        self,
        tenant_id: UUID,
        config_updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update tenant configuration."""
        tenant = await self.get_tenant_by_id(tenant_id)
        if not tenant:
            raise ValueError("Tenant not found")
        
        tenant.settings = tenant.settings or {}
        
        # Update configuration sections
        for section, values in config_updates.items():
            if section in ["branding", "features", "integrations", "security", "notifications"]:
                tenant.settings[section] = tenant.settings.get(section, {})
                tenant.settings[section].update(values)
        
        await self.session.commit()
        await self.session.refresh(tenant)
        
        return await self.get_tenant_configuration(tenant_id)
    
    async def get_tenant_usage(
        self,
        tenant_id: UUID,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Get tenant resource usage statistics."""
        # This is a simplified implementation
        # In practice, you'd query actual usage metrics from various sources
        
        tenant = await self.get_tenant_by_id(tenant_id)
        if not tenant:
            return {}
        
        # Get basic counts
        user_count = await self.session.scalar(
            select(func.count(User.id)).where(
                User.tenant_id == tenant_id,
                User.is_deleted == False
            )
        )
        
        return {
            "tenant_id": str(tenant_id),
            "period_start": start_date,
            "period_end": end_date,
            "api_requests": 0,  # TODO: Implement from metrics
            "agent_executions": 0,  # TODO: Implement from metrics
            "workflow_runs": 0,  # TODO: Implement from metrics
            "storage_used_mb": 0.0,  # TODO: Implement from storage metrics
            "bandwidth_used_mb": 0.0,  # TODO: Implement from metrics
            "cpu_hours": 0.0,  # TODO: Implement from metrics
            "memory_gb_hours": 0.0,  # TODO: Implement from metrics
            "llm_tokens_input": 0,  # TODO: Implement from LLM metrics
            "llm_tokens_output": 0,  # TODO: Implement from LLM metrics
            "llm_requests": 0,  # TODO: Implement from LLM metrics
            "quota_utilization": {
                "users": (user_count / tenant.max_users * 100) if tenant.max_users > 0 else 0
            }
        }
    
    async def get_tenant_analytics(
        self,
        tenant_id: UUID,
        period: str
    ) -> Dict[str, Any]:
        """Get comprehensive tenant analytics and insights."""
        # This is a simplified implementation
        # In practice, you'd aggregate data from various metrics sources
        
        tenant = await self.get_tenant_by_id(tenant_id)
        if not tenant:
            return {}
        
        # Calculate period dates
        now = datetime.utcnow()
        if period == "7d":
            start_date = now - timedelta(days=7)
        elif period == "30d":
            start_date = now - timedelta(days=30)
        elif period == "90d":
            start_date = now - timedelta(days=90)
        elif period == "1y":
            start_date = now - timedelta(days=365)
        else:
            start_date = now - timedelta(days=30)
        
        # Get basic metrics
        user_count = await self.session.scalar(
            select(func.count(User.id)).where(
                User.tenant_id == tenant_id,
                User.is_deleted == False
            )
        )
        
        new_users = await self.session.scalar(
            select(func.count(User.id)).where(
                User.tenant_id == tenant_id,
                User.created_at >= start_date,
                User.is_deleted == False
            )
        )
        
        return {
            "tenant_id": str(tenant_id),
            "period": period,
            "generated_at": now,
            "active_users": user_count,
            "new_users": new_users,
            "user_sessions": 0,  # TODO: Implement from session tracking
            "agents_created": 0,  # TODO: Implement from agent metrics
            "agents_executed": 0,  # TODO: Implement from execution metrics
            "avg_execution_time_ms": 0.0,  # TODO: Implement from performance metrics
            "workflows_created": 0,  # TODO: Implement from workflow metrics
            "workflows_executed": 0,  # TODO: Implement from execution metrics
            "workflow_success_rate": 0.0,  # TODO: Implement from execution metrics
            "avg_response_time_ms": 0.0,  # TODO: Implement from performance metrics
            "error_rate": 0.0,  # TODO: Implement from error metrics
            "uptime_percentage": 100.0,  # TODO: Implement from uptime metrics
            "growth_rate": {},  # TODO: Implement growth calculations
            "trends": {}  # TODO: Implement trend analysis
        }