from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel

class PermissionResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    resource: str
    action: str

    class Config:
        from_attributes = True

class RoleCreateRequest(BaseModel):
    name: str
    display_name: str
    description: Optional[str] = None
    permission_level: int = 1
    is_system_role: bool = False
    permissions: Optional[List[str]] = None  # List of permission names like "agent.view"

class RoleUpdateRequest(BaseModel):
    display_name: Optional[str] = None
    description: Optional[str] = None
    permission_level: Optional[int] = None
    permissions: Optional[List[str]] = None

class RoleResponse(BaseModel):
    id: UUID
    name: str
    display_name: str
    description: Optional[str] = None
    permission_level: int
    is_system_role: bool
    permissions: List[PermissionResponse] = []
    
    class Config:
        from_attributes = True
