"""
API Key Management API

This module provides endpoints for managing API keys including:
- Creating and revoking API keys
- Listing user API keys
- Updating API key permissions
- API key usage statistics
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.connection import get_async_db
from ..services.api_key import APIKeyService
from .auth import get_current_user
from ..schemas.auth import UserResponse
from ..schemas.api_key import (
    APIKeyRequest, APIKeyResponse, APIKeyCreateResponse,
    APIKeyUpdateRequest, APIKeyUsageResponse, APIKeyListResponse
)

router = APIRouter(prefix="/api/v1/api-keys", tags=["api-keys"])


@router.post("/", response_model=APIKeyCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    api_key_data: APIKeyRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Create a new API key for the current user.
    
    The API key will be returned only once. Make sure to save it securely.
    """
    api_key_service = APIKeyService(db)
    
    try:
        api_key_record, plain_key = await api_key_service.create_api_key(
            user_id=current_user.id,
            name=api_key_data.name,
            description=api_key_data.description,
            expires_at=api_key_data.expires_at,
            permissions=api_key_data.permissions,
            tenant_id=current_user.tenant_id
        )
        
        return APIKeyCreateResponse(
            api_key=APIKeyResponse.from_orm(api_key_record),
            key=plain_key
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create API key: {str(e)}"
        )


@router.get("/", response_model=APIKeyListResponse)
async def list_api_keys(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    List all API keys for the current user.
    """
    api_key_service = APIKeyService(db)
    
    api_keys = await api_key_service.get_user_api_keys(current_user.id)
    
    # Apply pagination
    total_count = len(api_keys)
    paginated_keys = api_keys[skip:skip + limit]
    
    return APIKeyListResponse(
        api_keys=[APIKeyResponse.from_orm(key) for key in paginated_keys],
        total_count=total_count,
        skip=skip,
        limit=limit
    )


@router.get("/{api_key_id}", response_model=APIKeyResponse)
async def get_api_key(
    api_key_id: UUID,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Get details of a specific API key.
    """
    api_key_service = APIKeyService(db)
    
    api_key = await api_key_service.get_api_key_by_id(api_key_id)
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    
    # Check ownership (unless system admin)
    if not current_user.is_system_admin and api_key.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to API key"
        )
    
    return APIKeyResponse.from_orm(api_key)


@router.put("/{api_key_id}", response_model=APIKeyResponse)
async def update_api_key(
    api_key_id: UUID,
    api_key_update: APIKeyUpdateRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Update an API key's name, description, or permissions.
    """
    api_key_service = APIKeyService(db)
    
    # For non-admin users, verify ownership
    user_id = None if current_user.is_system_admin else current_user.id
    
    api_key = await api_key_service.update_api_key(
        api_key_id=api_key_id,
        name=api_key_update.name,
        description=api_key_update.description,
        permissions=api_key_update.permissions,
        user_id=user_id
    )
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found or access denied"
        )
    
    return APIKeyResponse.from_orm(api_key)


@router.delete("/{api_key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(
    api_key_id: UUID,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Revoke an API key. This action cannot be undone.
    """
    api_key_service = APIKeyService(db)
    
    # For non-admin users, verify ownership
    user_id = None if current_user.is_system_admin else current_user.id
    
    success = await api_key_service.revoke_api_key(
        api_key_id=api_key_id,
        user_id=user_id
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found or access denied"
        )


@router.get("/{api_key_id}/usage", response_model=APIKeyUsageResponse)
async def get_api_key_usage(
    api_key_id: UUID,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Get usage statistics for an API key.
    """
    api_key_service = APIKeyService(db)
    
    # Check if API key exists and user has access
    api_key = await api_key_service.get_api_key_by_id(api_key_id)
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    
    # Check ownership (unless system admin)
    if not current_user.is_system_admin and api_key.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to API key usage data"
        )
    
    usage_stats = await api_key_service.get_api_key_usage_stats(api_key_id)
    
    return APIKeyUsageResponse(**usage_stats)


# Admin endpoints

@router.get("/admin/all", response_model=APIKeyListResponse)
async def list_all_api_keys(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    user_id: Optional[UUID] = Query(None, description="Filter by user ID"),
    tenant_id: Optional[UUID] = Query(None, description="Filter by tenant ID"),
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    List all API keys in the system (admin only).
    """
    if not current_user.is_system_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="System administrator privileges required"
        )
    
    # This is a simplified implementation
    # In production, you'd implement proper filtering and pagination
    return APIKeyListResponse(
        api_keys=[],
        total_count=0,
        skip=skip,
        limit=limit
    )


@router.post("/admin/cleanup", status_code=status.HTTP_200_OK)
async def cleanup_expired_api_keys(
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Clean up expired API keys (admin only).
    """
    if not current_user.is_system_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="System administrator privileges required"
        )
    
    api_key_service = APIKeyService(db)
    
    cleaned_count = await api_key_service.cleanup_expired_keys()
    
    return {
        "message": f"Cleaned up {cleaned_count} expired API keys",
        "cleaned_count": cleaned_count
    }