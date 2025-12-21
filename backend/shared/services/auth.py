"""
Authentication Service - Basic Framework

This module provides basic authentication functionality including:
- User registration and login
- JWT token generation and validation
- Password hashing and verification
- Basic session management

This can be extended later with Keycloak integration and advanced RBAC.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from uuid import UUID, uuid4

from passlib.context import CryptContext
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.user import User
from ..config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT settings
SECRET_KEY = settings.security.secret_key if hasattr(settings, 'security') else "your-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7


class AuthService:
    """Basic authentication service."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt."""
        return pwd_context.hash(password)
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return pwd_context.verify(plain_password, hashed_password)
    
    @staticmethod
    def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Create a JWT access token."""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire, "type": "access"})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def create_refresh_token(data: Dict[str, Any]) -> str:
        """Create a JWT refresh token."""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode.update({"exp": expire, "type": "refresh"})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def decode_token(token: str) -> Optional[Dict[str, Any]]:
        """Decode and validate a JWT token."""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return payload
        except JWTError as e:
            logger.error(f"Token decode error: {e}")
            return None
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email address."""
        query = select(User).where(
            User.email == email,
            User.is_deleted == False
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_user_by_id(self, user_id: UUID) -> Optional[User]:
        """Get user by ID."""
        query = select(User).where(
            User.id == user_id,
            User.is_deleted == False
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def register_user(
        self,
        email: str,
        password: str,
        full_name: str,
        tenant_id: Optional[UUID] = None
    ) -> User:
        """Register a new user."""
        # Check if user already exists
        existing_user = await self.get_user_by_email(email)
        if existing_user:
            raise ValueError(f"User with email {email} already exists")
        
        # Create new user
        user = User(
            id=uuid4(),
            email=email,
            hashed_password=self.hash_password(password),
            full_name=full_name,
            tenant_id=tenant_id,
            is_active=True,
            is_system_admin=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        
        logger.info(f"Registered new user: {email}")
        return user
    
    async def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """Authenticate a user with email and password."""
        user = await self.get_user_by_email(email)
        
        if not user:
            logger.warning(f"Authentication failed: User not found - {email}")
            return None
        
        if not user.is_active:
            logger.warning(f"Authentication failed: User inactive - {email}")
            return None
        
        if not self.verify_password(password, user.hashed_password):
            logger.warning(f"Authentication failed: Invalid password - {email}")
            return None
        
        # Update last login
        user.last_login_at = datetime.utcnow()
        await self.session.commit()
        
        logger.info(f"User authenticated successfully: {email}")
        return user
    
    async def create_user_tokens(self, user: User) -> Dict[str, str]:
        """Create access and refresh tokens for a user."""
        token_data = {
            "sub": str(user.id),
            "email": user.email,
            "tenant_id": str(user.tenant_id) if user.tenant_id else None,
            "is_system_admin": user.is_system_admin
        }
        
        access_token = self.create_access_token(token_data)
        refresh_token = self.create_refresh_token({"sub": str(user.id)})
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }
    
    async def refresh_access_token(self, refresh_token: str) -> Optional[Dict[str, str]]:
        """Refresh an access token using a refresh token."""
        payload = self.decode_token(refresh_token)
        
        if not payload or payload.get("type") != "refresh":
            return None
        
        user_id = payload.get("sub")
        if not user_id:
            return None
        
        user = await self.get_user_by_id(UUID(user_id))
        if not user or not user.is_active:
            return None
        
        return await self.create_user_tokens(user)
    
    async def change_password(
        self,
        user_id: UUID,
        old_password: str,
        new_password: str
    ) -> bool:
        """Change a user's password."""
        user = await self.get_user_by_id(user_id)
        
        if not user:
            return False
        
        if not self.verify_password(old_password, user.hashed_password):
            logger.warning(f"Password change failed: Invalid old password - {user.email}")
            return False
        
        user.hashed_password = self.hash_password(new_password)
        user.updated_at = datetime.utcnow()
        await self.session.commit()
        
        logger.info(f"Password changed successfully: {user.email}")
        return True
    
    async def reset_password(self, email: str, new_password: str) -> bool:
        """Reset a user's password (admin function)."""
        user = await self.get_user_by_email(email)
        
        if not user:
            return False
        
        user.hashed_password = self.hash_password(new_password)
        user.updated_at = datetime.utcnow()
        await self.session.commit()
        
        logger.info(f"Password reset for user: {email}")
        return True


# Dependency for FastAPI endpoints
async def get_current_user(token: str, session: AsyncSession) -> Optional[User]:
    """
    FastAPI dependency to get the current authenticated user from a JWT token.
    
    Usage:
        @app.get("/protected")
        async def protected_route(
            current_user: User = Depends(get_current_user)
        ):
            return {"user": current_user.email}
    """
    auth_service = AuthService(session)
    payload = auth_service.decode_token(token)
    
    if not payload:
        return None
    
    user_id = payload.get("sub")
    if not user_id:
        return None
    
    user = await auth_service.get_user_by_id(UUID(user_id))
    return user