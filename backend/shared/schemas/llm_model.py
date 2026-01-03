"""
LLM Model Pydantic Schemas
"""

from typing import Optional, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field
from shared.models.llm_model import LLMProvider


class LLMModelBase(BaseModel):
    """Base LLM model schema with essential fields."""
    name: str = Field(..., min_length=1, max_length=255, description="LLM model name")
    provider: LLMProvider = Field(..., description="LLM provider")
    api_base: Optional[str] = Field(None, max_length=255, description="API base URL for the model")
    description: Optional[str] = Field(None, description="Model description")
    is_default: bool = Field(False, description="Whether this is the default model")
    config: Dict[str, Any] = Field(default_factory=dict, description="Model configuration")


class LLMModelCreate(LLMModelBase):
    """Schema for creating a new LLM model."""
    api_key: Optional[str] = Field(None, description="API key for the model")


class LLMModelUpdate(BaseModel):
    """Schema for updating LLM model information."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    provider: Optional[LLMProvider] = None
    api_base: Optional[str] = Field(None, max_length=255)
    api_key: Optional[str] = Field(None, description="API key for the model")
    description: Optional[str] = None
    is_default: Optional[bool] = None
    config: Optional[Dict[str, Any]] = None


class LLMModelResponse(LLMModelBase):
    """Schema for LLM model API responses."""
    id: UUID

    class Config:
        from_attributes = True

class LLMModelTestRequest(BaseModel):
    """Schema for testing an LLM model."""
    model_id: UUID = Field(..., description="ID of the LLM model to test")
    prompt: str = Field(..., min_length=1, description="Sample prompt to send to the model")
    system_prompt: Optional[str] = Field(None, description="Optional system prompt for the model")

    model_config = {
        "protected_namespaces": ()
    }
