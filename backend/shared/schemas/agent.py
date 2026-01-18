from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field
from enum import Enum

class AgentType(str, Enum):
    CONVERSATIONAL = "conversational"
    TASK = "task"
    ROUTER = "router"
    COORDINATOR = "coordinator"
    CHATBOT = "chatbot"
    CONTENT_GENERATION = "content_generation"
    DATA_ANALYSIS = "data_analysis"
    CUSTOM = "custom"

class AgentStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"
    ERROR = "error"

class LLMProvider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    VERTEX_AI = "vertex_ai"
    OLLAMA = "ollama"
    HUGGINGFACE = "huggingface"

class AgentConfig(BaseModel):
    """Configuration for an agent."""
    llm_model_id: Optional[UUID] = None # Link to the LLMModel
    name: str
    description: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 1000
    top_p: Optional[float] = None  # Nucleus sampling parameter (0.0-1.0)
    top_k: Optional[int] = None  # Top-k sampling parameter
    stop_sequences: Optional[List[str]] = None  # Stop sequences for generation
    system_prompt: Optional[str] = None
    tools: List[str] = []
    mcp_servers: Optional[List[str]] = []
    memory_enabled: bool = False
    guardrails_enabled: bool = False
    use_standard_response_format: bool = False
    use_standard_protocol: bool = False
    
    model_config = {
        "protected_namespaces": ()
    }

class AgentBase(BaseModel):
    """Base Agent schema."""
    name: str
    description: Optional[str] = None
    type: AgentType
    status: AgentStatus
    version: str
    config: Dict[str, Any]
    system_prompt: Optional[str] = None

class AgentCreate(AgentBase):
    """Schema for creating an Agent."""
    llm_model_id: Optional[UUID] = None
    
    model_config = {
        "protected_namespaces": ()
    }

class AgentUpdate(AgentBase):
    """Schema for updating an Agent."""
    name: Optional[str] = None
    description: Optional[str] = None
    type: Optional[AgentType] = None
    status: Optional[AgentStatus] = None
    version: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    system_prompt: Optional[str] = None

class AgentResponse(AgentBase):
    """Response schema for Agent."""
    id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: Optional[UUID] = None
    updated_by: Optional[UUID] = None

    class Config:
        from_attributes = True
