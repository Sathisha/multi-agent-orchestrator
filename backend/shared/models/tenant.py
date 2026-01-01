import uuid
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field

# Stubs for tenant models to satisfy imports but not create DB tables
# We are converting this to single-tenant architecture

class TenantStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"

class TenantPlan(Enum):
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"

@dataclass
class TenantContext:
    tenant_id: str
    tenant_uuid: uuid.UUID
    tenant_name: str = "default"
    user_id: Optional[str] = None

# These are no longer SQLAlchemy models
class Tenant:
    id: uuid.UUID
    name: str
    status: str

class TenantUser:
    id: uuid.UUID
    tenant_id: uuid.UUID
    user_id: uuid.UUID

class TenantInvitation:
    pass

class ResourceQuotas:
    pass
