from typing import Optional, List
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field

class RoleResponse(BaseModel):
    id: UUID
    name: str
    display_name: str
    permission_level: int
    is_system_role: bool
    description: Optional[str] = None
    
    class Config:
        from_attributes = True

class UserCreateRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str
    username: Optional[str] = None
    status: str = "active"
    role_ids: Optional[List[UUID]] = None

class UserUpdateRequest(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    status: Optional[str] = None
    is_active: Optional[bool] = None
    role_ids: Optional[List[UUID]] = None

class UserRoleAssignRequest(BaseModel):
    role_id: UUID
    expires_at: Optional[datetime] = None

class UserResponse(BaseModel):
    id: UUID
    email: str
    username: str
    full_name: Optional[str] = None
    is_superuser: bool
    is_active: bool
    status: str
    roles: List[RoleResponse] = []
    created_at: datetime
    updated_at: datetime
    last_login_at: Optional[datetime] = None

    class Config:
        from_attributes = True
