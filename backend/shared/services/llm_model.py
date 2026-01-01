from typing import List, Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from shared.models.llm_model import LLMModel
from shared.schemas.llm_model import LLMModelCreate, LLMModelUpdate

class LLMModelService:
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session

    async def create_llm_model(self, model_data: LLMModelCreate) -> LLMModel:
        """Create a new LLM model."""
        # TODO: Add encryption for api_key
        new_model = LLMModel(**model_data.dict())
        self.db_session.add(new_model)
        await self.db_session.commit()
        await self.db_session.refresh(new_model)
        return new_model

    async def list_llm_models(self) -> List[LLMModel]:
        """List all LLM models."""
        query = select(LLMModel).where(LLMModel.is_deleted == False)
        result = await self.db_session.execute(query)
        return result.scalars().all()

    async def get_llm_model(self, model_id: UUID) -> Optional[LLMModel]:
        """Get a specific LLM model by ID."""
        query = select(LLMModel).where(LLMModel.id == model_id, LLMModel.is_deleted == False)
        result = await self.db_session.execute(query)
        return result.scalar_one_or_none()

    async def update_llm_model(self, model_id: UUID, model_data: LLMModelUpdate) -> Optional[LLMModel]:
        """Update an LLM model."""
        model = await self.get_llm_model(model_id)
        if not model:
            return None

        update_data = model_data.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(model, key, value)
        
        # TODO: Add encryption for api_key if it is updated

        await self.db_session.commit()
        await self.db_session.refresh(model)
        return model

    async def delete_llm_model(self, model_id: UUID) -> bool:
        """Delete an LLM model."""
        model = await self.get_llm_model(model_id)
        if not model:
            return False
        
        model.is_deleted = True
        await self.db_session.commit()
        return True
