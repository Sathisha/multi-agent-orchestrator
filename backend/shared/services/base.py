"""Base service class for CRUD operations."""

from typing import Optional, Type, TypeVar, List, Dict, Any
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from shared.models.base import BaseEntity, SystemEntity

T = TypeVar('T', bound=BaseEntity)


class BaseService:
    """Simple base service class."""
    
    def __init__(self, session: AsyncSession, model_class: Type[T]):
        self.session = session
        self.model_class = model_class
    
    async def get_by_id(self, entity_id: str) -> Optional[T]:
        """Get entity by ID."""
        query = select(self.model_class).where(self.model_class.id == entity_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def create(self, **kwargs) -> T:
        """Create entity."""
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