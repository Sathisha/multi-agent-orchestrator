"""
Authentication Pydantic Schemas

This module defines Pydantic models for authentication-related API requests and responses.
"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, Field, EmailStr, validator


# User Registration and Login Schemas

class UserRegister(BaseModel):
    """Schema for user registration."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="User password (minimum 8 characters)")
    full_name: str = Field(..., min_length=1, max_length=255, description="User full name")
    
    @validator('password')
    def validate_password(cls, v):
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        
        # Basic password requirements
        has_upper = any(c.isupper() for c in v)
        has_lower = any(c.islower() for c in v)
        has_digit = any(c.isdigit() for c in v)
        
        if not (has_upper and has_lower and has_digit):
            raise ValueError('Password must contain at least one uppercase letter, one lowercase letter, and one digit')
        
        return v


class UserLogin(BaseModel):
    """Schema for user login."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")


class UserUpdate(BaseModel):
    """Schema for updating user profile."""
    full_name: Optional[str] = Field(None, min_length=1, max_length=255, description="User full name")
    avatar_url: Optional[str] = Field(None, description="User avatar URL")


# Token Schemas

class TokenResponse(BaseModel):
    """Schema for authentication token response."""
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field("bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")


class TokenRefresh(BaseModel):
    """Schema for token refresh request."""
    refresh_token: str = Field(..., description="Refresh token")


# Password Management Schemas

class PasswordChange(BaseModel):
    """Schema for password change request."""
    old_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, description="New password")
    
    @validator('new_password')
    def validate_new_password(cls, v):
        """Validate new password strength."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        
        # Basic password requirements
        has_upper = any(c.isupper() for c in v)
        has_lower = any(c.islower() for c in v)
        has_digit = any(c.isdigit() for c in v)
        
        if not (has_upper and has_lower and has_digit):
            raise ValueError('Password must contain at least one uppercase letter, one lowercase letter, and one digit')
        
        return v


class PasswordReset(BaseModel):
    """Schema for password reset request."""
    email: EmailStr = Field(..., description="User email address")
    new_password: str = Field(..., min_length=8, description="New password")
    
    @validator('new_password')
    def validate_new_password(cls, v):
        """Validate new password strength."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        
        # Basic password requirements
        has_upper = any(c.isupper() for c in v)
        has_lower = any(c.islower() for c in v)
        has_digit = any(c.isdigit() for c in v)
        
        if not (has_upper and has_lower and has_digit):
            raise ValueError('Password must contain at least one uppercase letter, one lowercase letter, and one digit')
        
        return v


# User Response Schemas

class UserResponse(BaseModel):
    """Schema for user API responses."""
    id: UUID
    email: str
    full_name: str
    avatar_url: Optional[str] = None
    # is_active: bool # Check step 733. Yes.
    is_active: bool
    is_system_admin: bool
    created_at: datetime
    updated_at: datetime
    last_login_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    """Schema for paginated user list responses."""
    users: List[UserResponse]
    total_count: int
    skip: int
    limit: int


# Role and Permission Schemas

class PermissionResponse(BaseModel):
    """Schema for permission API responses."""
    id: UUID
    name: str
    description: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class RoleResponse(BaseModel):
    """Schema for role API responses."""
    id: UUID
    name: str
    description: str
    permissions: List[PermissionResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class RoleCreate(BaseModel):
    """Schema for creating a new role."""
    name: str = Field(..., min_length=1, max_length=100, description="Role name")
    description: str = Field(..., min_length=1, max_length=500, description="Role description")
    permissions: Optional[List[str]] = Field(default_factory=list, description="List of permission names")


class RoleUpdate(BaseModel):
    """Schema for updating a role."""
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Role name")
    description: Optional[str] = Field(None, min_length=1, max_length=500, description="Role description")
    permissions: Optional[List[str]] = Field(None, description="List of permission names")


class UserRoleAssignment(BaseModel):
    """Schema for assigning roles to users."""
    user_id: UUID = Field(..., description="User ID")
    role_id: UUID = Field(..., description="Role ID")


class UserRoleResponse(BaseModel):
    """Schema for user role assignment responses."""
    id: UUID
    user_id: UUID
    role_id: UUID
    assigned_by: Optional[UUID] = None
    assigned_at: datetime
    is_active: bool
    
    class Config:
        from_attributes = True


# Permission Check Schemas

class PermissionCheck(BaseModel):
    """Schema for permission check requests."""
    user_id: UUID = Field(..., description="User ID to check")
    permission: str = Field(..., description="Permission name to check")


class PermissionCheckResponse(BaseModel):
    """Schema for permission check responses."""
    user_id: UUID
    permission: str
    has_permission: bool
    roles: List[str] = Field(default_factory=list, description="Roles that grant this permission")


# Session Management Schemas

class SessionInfo(BaseModel):
    """Schema for session information."""
    user_id: UUID
    email: str
    roles: List[str] = Field(default_factory=list)
    permissions: List[str] = Field(default_factory=list)
    is_system_admin: bool
    session_start: datetime
    last_activity: datetime


# Error Response Schemas

class AuthErrorResponse(BaseModel):
    """Schema for authentication error responses."""
    detail: str
    error_code: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# API Key Schemas (for future use)

class APIKeyCreate(BaseModel):
    """Schema for creating API keys."""
    name: str = Field(..., min_length=1, max_length=100, description="API key name")
    description: Optional[str] = Field(None, max_length=500, description="API key description")
    expires_at: Optional[datetime] = Field(None, description="API key expiration date")
    permissions: Optional[List[str]] = Field(default_factory=list, description="API key permissions")


class APIKeyResponse(BaseModel):
    """Schema for API key responses."""
    id: UUID
    name: str
    description: Optional[str] = None
    key_prefix: str = Field(..., description="First 8 characters of the API key")
    created_at: datetime
    expires_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    is_active: bool
    
    class Config:
        from_attributes = True