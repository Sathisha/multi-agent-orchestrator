"""
Authentication API - Basic Framework

This module provides authentication endpoints including:
- User registration and login
- Token refresh
- Password management
- User profile management
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.connection import get_async_db
from ..services.auth import AuthService
from ..services.rbac import RBACService
from ..schemas.auth import (
    UserRegister, UserLogin, UserResponse, TokenResponse,
    PasswordChange, PasswordReset, UserUpdate
)

router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])
security = HTTPBearer()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: UserRegister,
    db: AsyncSession = Depends(get_database_session)
):
    """
    Register a new user.
    
    Creates a new user account with basic user role.
    """
    auth_service = AuthService(db)
    rbac_service = RBACService(db)
    
    try:
        # Create user
        user = await auth_service.register_user(
            email=user_data.email,
            password=user_data.password,
            full_name=user_data.full_name,
            tenant_id=user_data.tenant_id
        )
        
        # Assign default user role
        try:
            # Get or create default user role
            user_role = await rbac_service.get_role_by_name("user", user_data.tenant_id)
            if user_role:
                await rbac_service.assign_role_to_user(user.id, user_role.id)
        except Exception as e:
            # Log but don't fail registration if role assignment fails
            import logging
            logging.warning(f"Failed to assign default role to user {user.email}: {e}")
        
        return UserResponse.from_orm(user)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )


@router.post("/login", response_model=TokenResponse)
async def login_user(
    user_data: UserLogin,
    db: AsyncSession = Depends(get_database_session)
):
    """
    Authenticate user and return access tokens.
    
    Returns JWT access and refresh tokens for authenticated user.
    """
    auth_service = AuthService(db)
    
    # Authenticate user
    user = await auth_service.authenticate_user(user_data.email, user_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Create tokens
    tokens = await auth_service.create_user_tokens(user)
    
    return TokenResponse(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        token_type=tokens["token_type"],
        expires_in=1800  # 30 minutes
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    refresh_token: str,
    db: AsyncSession = Depends(get_database_session)
):
    """
    Refresh access token using refresh token.
    
    Returns new access and refresh tokens.
    """
    auth_service = AuthService(db)
    
    tokens = await auth_service.refresh_access_token(refresh_token)
    
    if not tokens:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    return TokenResponse(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        token_type=tokens["token_type"],
        expires_in=1800  # 30 minutes
    )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_database_session)
):
    """
    FastAPI dependency to get current authenticated user.
    
    Validates JWT token and returns user object.
    """
    auth_service = AuthService(db)
    
    # Decode token
    payload = auth_service.decode_token(credentials.credentials)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Get user
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    user = await auth_service.get_user_by_id(UUID(user_id))
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    return user


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user = Depends(get_current_user)
):
    """
    Get current user profile information.
    
    Returns the authenticated user's profile data.
    """
    return UserResponse.from_orm(current_user)


@router.put("/me", response_model=UserResponse)
async def update_user_profile(
    user_update: UserUpdate,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_database_session)
):
    """
    Update current user profile information.
    
    Allows users to update their own profile data.
    """
    # Update user fields
    if user_update.full_name is not None:
        current_user.full_name = user_update.full_name
    
    if user_update.avatar_url is not None:
        current_user.avatar_url = user_update.avatar_url
    
    current_user.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(current_user)
    
    return UserResponse.from_orm(current_user)


@router.post("/change-password")
async def change_password(
    password_data: PasswordChange,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_database_session)
):
    """
    Change user password.
    
    Requires current password for verification.
    """
    auth_service = AuthService(db)
    
    success = await auth_service.change_password(
        user_id=current_user.id,
        old_password=password_data.old_password,
        new_password=password_data.new_password
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid current password"
        )
    
    return {"message": "Password changed successfully"}


@router.post("/reset-password")
async def reset_password(
    password_data: PasswordReset,
    db: AsyncSession = Depends(get_database_session)
):
    """
    Reset user password (admin function).
    
    This is a simplified implementation. In production, this would
    require proper authorization and possibly email verification.
    """
    auth_service = AuthService(db)
    
    success = await auth_service.reset_password(
        email=password_data.email,
        new_password=password_data.new_password
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return {"message": "Password reset successfully"}


@router.post("/logout")
async def logout_user(
    current_user = Depends(get_current_user)
):
    """
    Logout user.
    
    In a basic implementation, this just returns success.
    In production, you might want to blacklist the token.
    """
    return {"message": "Logged out successfully"}


# Admin endpoints for user management

@router.get("/users", response_model=list[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_database_session)
):
    """
    List all users (admin only).
    
    TODO: Add proper admin authorization check.
    """
    # Basic admin check
    if not current_user.is_system_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    from sqlalchemy import select
    from ..models.user import User
    
    query = select(User).where(User.is_deleted == False).offset(skip).limit(limit)
    result = await db.execute(query)
    users = result.scalars().all()
    
    return [UserResponse.from_orm(user) for user in users]


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_database_session)
):
    """
    Get user by ID (admin only).
    
    TODO: Add proper admin authorization check.
    """
    # Basic admin check
    if not current_user.is_system_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    auth_service = AuthService(db)
    user = await auth_service.get_user_by_id(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserResponse.from_orm(user)