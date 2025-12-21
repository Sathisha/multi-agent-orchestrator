"""
Tenant Pydantic Schemas - Basic Framework

This module defines basic Pydantic models for tenant-related API requests and responses.
These can be extended later when implementing full multi-tenant functionality.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field


# Basic Tenant Schemas

class TenantBase(BaseModel):
    """Base tenant schema with essential fields."""
    name: str = Field(..., min_length=1, max_length=255, description="Tenant display name")
    slug: str = Field(..., min_length=3, max_length=63, description="Unique tenant identifier")


class TenantCreate(TenantBase):
    """Schema for creating a new tenant."""
    admin_email: str = Field(..., description="Email of the tenant administrator")
    plan: str = Field("free", description="Initial subscription plan")


class TenantUpdate(BaseModel):
    """Schema for updating tenant information."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    status: Optional[str] = Field(None, regex="^(active|suspended|inactive)$")
    settings: Optional[Dict[str, Any]] = None


class TenantResponse(TenantBase):
    """Schema for tenant API responses."""
    id: UUID
    status: str
    plan: str
    settings: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Basic User Management Schemas

class TenantUserBase(BaseModel):
    """Base schema for tenant user relationships."""
    role: str = Field(..., regex="^(admin|manager|member|viewer)$", description="User role in tenant")


class TenantUserResponse(TenantUserBase):
    """Schema for tenant user API responses."""
    id: UUID
    tenant_id: UUID
    user_id: UUID
    status: str
    joined_at: datetime
    
    class Config:
        from_attributes = True


# Basic Configuration Schemas

class TenantConfigurationUpdate(BaseModel):
    """Schema for updating tenant configuration."""
    branding: Optional[Dict[str, Any]] = Field(None, description="Branding configuration")
    features: Optional[Dict[str, bool]] = Field(None, description="Feature toggles")
    settings: Optional[Dict[str, Any]] = Field(None, description="General settings")


class TenantConfigurationResponse(BaseModel):
    """Schema for tenant configuration responses."""
    id: UUID
    tenant_id: UUID
    branding: Dict[str, Any] = Field(default_factory=dict)
    features: Dict[str, bool] = Field(default_factory=dict)
    settings: Dict[str, Any] = Field(default_factory=dict)
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Basic Usage and Analytics Schemas

class TenantUsageResponse(BaseModel):
    """Schema for tenant usage statistics."""
    tenant_id: UUID
    period_start: datetime
    period_end: datetime
    
    # Basic usage metrics
    api_requests: int = 0
    storage_used_mb: float = 0.0
    active_users: int = 0
    
    class Config:
        from_attributes = True


class TenantAnalyticsResponse(BaseModel):
    """Schema for tenant analytics data."""
    tenant_id: UUID
    period: str
    generated_at: datetime
    
    # Basic analytics
    user_activity: Dict[str, Any] = Field(default_factory=dict)
    resource_usage: Dict[str, Any] = Field(default_factory=dict)
    performance_metrics: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        from_attributes = True