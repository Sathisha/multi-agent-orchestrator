"""
API Key Management Service

This module provides API key generation, validation, and management functionality.
"""

import logging
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.shared.models.api_key import APIKey

logger = logging.getLogger(__name__)


class APIKeyService:
    """Service for managing API keys."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    @staticmethod
    def generate_api_key() -> str:
        """Generate a secure API key."""
        # Generate 32 bytes of random data and encode as hex
        return secrets.token_hex(32)
    
    @staticmethod
    def hash_api_key(api_key: str) -> str:
        """Hash an API key for secure storage."""
        return hashlib.sha256(api_key.encode()).hexdigest()
    
    @staticmethod
    def get_key_prefix(api_key: str) -> str:
        """Get the first 8 characters of an API key for display."""
        return api_key[:8] if len(api_key) >= 8 else api_key
    
    async def create_api_key(
        self,
        user_id: UUID,
        name: str,
        description: Optional[str] = None,
        expires_at: Optional[datetime] = None,
        permissions: Optional[List[str]] = None,
        tenant_id: Optional[UUID] = None
    ) -> tuple[APIKey, str]:
        """
        Create a new API key.
        
        Returns:
            Tuple of (APIKey object, plain text API key)
        """
        # Generate API key
        plain_key = self.generate_api_key()
        key_hash = self.hash_api_key(plain_key)
        key_prefix = self.get_key_prefix(plain_key)
        
        # Create API key record
        api_key = APIKey(
            id=uuid4(),
            user_id=user_id,
            tenant_id=tenant_id,
            name=name,
            description=description,
            key_hash=key_hash,
            key_prefix=key_prefix,
            permissions=permissions or [],
            expires_at=expires_at,
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        self.session.add(api_key)
        await self.session.commit()
        await self.session.refresh(api_key)
        
        logger.info(f"Created API key: {name} for user {user_id}")
        return api_key, plain_key
    
    async def validate_api_key(self, api_key: str) -> Optional[APIKey]:
        """
        Validate an API key and return the associated record.
        
        Args:
            api_key: Plain text API key to validate
            
        Returns:
            APIKey object if valid, None otherwise
        """
        key_hash = self.hash_api_key(api_key)
        
        query = select(APIKey).where(
            and_(
                APIKey.key_hash == key_hash,
                APIKey.is_active == True
            )
        )
        
        result = await self.session.execute(query)
        api_key_record = result.scalar_one_or_none()
        
        if not api_key_record:
            return None
        
        # Check if key has expired
        if api_key_record.expires_at and datetime.utcnow() > api_key_record.expires_at:
            logger.warning(f"Expired API key used: {api_key_record.key_prefix}...")
            return None
        
        # Update last used timestamp
        api_key_record.last_used_at = datetime.utcnow()
        await self.session.commit()
        
        return api_key_record
    
    async def get_user_api_keys(self, user_id: UUID) -> List[APIKey]:
        """Get all API keys for a user."""
        query = select(APIKey).where(
            and_(
                APIKey.user_id == user_id,
                APIKey.is_active == True
            )
        ).order_by(APIKey.created_at.desc())
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def get_api_key_by_id(self, api_key_id: UUID) -> Optional[APIKey]:
        """Get an API key by ID."""
        query = select(APIKey).where(APIKey.id == api_key_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def revoke_api_key(self, api_key_id: UUID, user_id: Optional[UUID] = None) -> bool:
        """
        Revoke an API key.
        
        Args:
            api_key_id: ID of the API key to revoke
            user_id: Optional user ID for ownership verification
            
        Returns:
            True if revoked successfully, False otherwise
        """
        query = select(APIKey).where(APIKey.id == api_key_id)
        
        if user_id:
            query = query.where(APIKey.user_id == user_id)
        
        result = await self.session.execute(query)
        api_key = result.scalar_one_or_none()
        
        if not api_key:
            return False
        
        api_key.is_active = False
        api_key.revoked_at = datetime.utcnow()
        api_key.updated_at = datetime.utcnow()
        
        await self.session.commit()
        
        logger.info(f"Revoked API key: {api_key.name} ({api_key.key_prefix}...)")
        return True
    
    async def update_api_key(
        self,
        api_key_id: UUID,
        name: Optional[str] = None,
        description: Optional[str] = None,
        permissions: Optional[List[str]] = None,
        user_id: Optional[UUID] = None
    ) -> Optional[APIKey]:
        """
        Update an API key.
        
        Args:
            api_key_id: ID of the API key to update
            name: New name for the API key
            description: New description
            permissions: New permissions list
            user_id: Optional user ID for ownership verification
            
        Returns:
            Updated APIKey object or None if not found
        """
        query = select(APIKey).where(APIKey.id == api_key_id)
        
        if user_id:
            query = query.where(APIKey.user_id == user_id)
        
        result = await self.session.execute(query)
        api_key = result.scalar_one_or_none()
        
        if not api_key:
            return None
        
        # Update fields
        if name is not None:
            api_key.name = name
        
        if description is not None:
            api_key.description = description
        
        if permissions is not None:
            api_key.permissions = permissions
        
        api_key.updated_at = datetime.utcnow()
        
        await self.session.commit()
        await self.session.refresh(api_key)
        
        logger.info(f"Updated API key: {api_key.name} ({api_key.key_prefix}...)")
        return api_key
    
    async def cleanup_expired_keys(self) -> int:
        """
        Clean up expired API keys.
        
        Returns:
            Number of keys cleaned up
        """
        current_time = datetime.utcnow()
        
        query = select(APIKey).where(
            and_(
                APIKey.expires_at < current_time,
                APIKey.is_active == True
            )
        )
        
        result = await self.session.execute(query)
        expired_keys = result.scalars().all()
        
        count = 0
        for api_key in expired_keys:
            api_key.is_active = False
            api_key.revoked_at = current_time
            api_key.updated_at = current_time
            count += 1
        
        if count > 0:
            await self.session.commit()
            logger.info(f"Cleaned up {count} expired API keys")
        
        return count
    
    async def get_api_key_usage_stats(self, api_key_id: UUID) -> Dict[str, Any]:
        """
        Get usage statistics for an API key.
        
        This is a placeholder implementation. In production, you would
        query actual usage metrics from logs or a metrics database.
        """
        api_key = await self.get_api_key_by_id(api_key_id)
        
        if not api_key:
            return {}
        
        return {
            "api_key_id": str(api_key_id),
            "name": api_key.name,
            "created_at": api_key.created_at,
            "last_used_at": api_key.last_used_at,
            "total_requests": 0,  # TODO: Implement from metrics
            "requests_today": 0,  # TODO: Implement from metrics
            "requests_this_month": 0,  # TODO: Implement from metrics
            "error_rate": 0.0,  # TODO: Implement from metrics
            "avg_response_time_ms": 0.0,  # TODO: Implement from metrics
        }
    
    async def has_permission(self, api_key: APIKey, permission: str) -> bool:
        """
        Check if an API key has a specific permission.
        
        Args:
            api_key: APIKey object
            permission: Permission string to check
            
        Returns:
            True if the API key has the permission, False otherwise
        """
        if not api_key.permissions:
            return False
        
        # Check for exact permission match
        if permission in api_key.permissions:
            return True
        
        # Check for wildcard permissions
        for perm in api_key.permissions:
            if perm.endswith("*"):
                prefix = perm[:-1]
                if permission.startswith(prefix):
                    return True
        
        return False