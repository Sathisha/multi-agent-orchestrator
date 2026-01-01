"""
Default Tenant Context - Simplified Multi-Tenant Implementation

This module provides stub functions for tenant context with default values.
Multi-tenant features are low priority and have been simplified to use default values.
"""
import uuid
from dataclasses import dataclass
from typing import Optional
from enum import Enum


# Stub enums for test compatibility
class TenantStatus(Enum):
    """Simplified tenant status enumeration"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


class TenantPlan(Enum):
    """Simplified tenant plan enumeration"""
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


# Default tenant ID used throughout the system
DEFAULT_TENANT_ID = "00000000-0000-0000-0000-000000000001"
DEFAULT_TENANT_UUID = uuid.UUID(DEFAULT_TENANT_ID)
DEFAULT_TENANT_NAME = "default"


@dataclass
class TenantContext:
    """Simplified tenant context with default values"""
    tenant_id: str = DEFAULT_TENANT_ID
    tenant_uuid: uuid.UUID = DEFAULT_TENANT_UUID
    tenant_name: str = DEFAULT_TENANT_NAME
    user_id: Optional[str] = None
    
    def __post_init__(self):
        """Ensure UUID is properly set"""
        if isinstance(self.tenant_uuid, str):
            self.tenant_uuid = uuid.UUID(self.tenant_uuid)


def get_default_tenant_context() -> TenantContext:
    """
    Returns a default tenant context.
    
    This replaces the complex multi-tenant dependency injection.
    All requests use the default tenant for simplicity.
    """
    return TenantContext(
        tenant_id=DEFAULT_TENANT_ID,
        tenant_uuid=DEFAULT_TENANT_UUID,
        tenant_name=DEFAULT_TENANT_NAME
    )


async def get_tenant_context() -> TenantContext:
    """
    Async version of get_default_tenant_context for FastAPI Depends.
    
    Usage in endpoints:
        tenant_context: TenantContext = Depends(get_tenant_context)
    """
    return get_default_tenant_context()


def get_current_tenant_id() -> str:
    """Get the current tenant ID (always returns default)"""
    return DEFAULT_TENANT_ID


def get_current_tenant_uuid() -> uuid.UUID:
    """Get the current tenant UUID (always returns default)"""
    return DEFAULT_TENANT_UUID
