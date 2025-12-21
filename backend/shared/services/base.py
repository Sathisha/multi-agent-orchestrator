"""Base service classes for tenant-aware operations."""

from typing import Optional, Type, TypeVar, List, Dict, Any
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from shared.models.base import TenantEntity, SystemEntity

T = TypeVar('T', bound=TenantEntity)
S = TypeVar('S', bound=SystemEntity)


class BaseService:
    """Simple base service class."""
    
    def __init__(self, session: AsyncSession, model_class: Type[T], tenant_id: Optional[str] = None):
        self.session = session
        self.model_class = model_class
        self.tenant_id = tenant_id
    
    async def get_by_id(self, entity_id: str) -> Optional[T]:
        """Get entity by ID."""
        if self.tenant_id:
            query = select(self.model_class).where(
                and_(
                    self.model_class.id == entity_id,
                    self.model_class.tenant_id == self.tenant_id
                )
            )
        else:
            query = select(self.model_class).where(self.model_class.id == entity_id)
        
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def create(self, **kwargs) -> T:
        """Create entity."""
        if self.tenant_id and hasattr(self.model_class, 'tenant_id'):
            kwargs['tenant_id'] = self.tenant_id
        
        entity = self.model_class(**kwargs)
        self.session.add(entity)
        await self.session.commit()
        await self.session.refresh(entity)
        return entity
    
    async def delete(self, entity_id: str) -> bool:
        """Delete entity."""
        entity = await self.get_by_id(entity_id)
        if entity:
            await self.session.delete(entity)
            await self.session.commit()
            return True
        return False