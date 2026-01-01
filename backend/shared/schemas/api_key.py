from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel

class APIKeyRequest(BaseModel):
    name: str
    description: Optional[str] = None
    permissions: Optional[List[str]] = None
    expires_at: Optional[datetime] = None

class APIKeyResponse(BaseModel):
    id: UUID
    user_id: UUID
    tenant_id: Optional[UUID] = None
    name: str
    description: Optional[str] = None
    key_prefix: str
    permissions: List[str]
    is_active: bool
    created_at: datetime
    last_used_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class APIKeyCreateResponse(BaseModel):
    api_key: APIKeyResponse
    key: str

class APIKeyUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    permissions: Optional[List[str]] = None

class APIKeyUsageResponse(BaseModel):
    api_key_id: str
    name: str
    created_at: datetime
    last_used_at: Optional[datetime] = None
    total_requests: int
    requests_today: int
    requests_this_month: int
    error_rate: float
    avg_response_time_ms: float

class APIKeyListResponse(BaseModel):
    api_keys: List[APIKeyResponse]
    total_count: int
    skip: int
    limit: int
