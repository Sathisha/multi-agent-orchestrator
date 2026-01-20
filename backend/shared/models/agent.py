from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel

from sqlalchemy import String, Text, ForeignKey, text, Integer, Float, DateTime
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
import uuid

from shared.models.base import SystemEntity, BaseEntity

# Enums
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
    GOOGLE = "google"
    OLLAMA = "ollama"
    HUGGINGFACE = "huggingface"
    MOCK = "mock"

class AgentConfig(BaseModel):
    """Configuration for an agent."""
    name: str
    description: Optional[str] = None
    model: str
    temperature: float = 0.7
    max_tokens: int = 1000
    top_p: Optional[float] = None  # Nucleus sampling parameter (0.0-1.0)
    top_k: Optional[int] = None  # Top-k sampling parameter
    stop_sequences: Optional[List[str]] = None  # Stop sequences for generation
    system_prompt: Optional[str] = None
    tools: List[str] = []
    llm_provider: Optional[LLMProvider] = None
    mcp_servers: Optional[List[str]] = []
    memory_enabled: bool = False
    guardrails_enabled: bool = False
    use_standard_response_format: bool = False
    success_criteria: Optional[str] = None
    failure_criteria: Optional[str] = None

class Agent(SystemEntity):
    __tablename__ = "agents"
    
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    type: Mapped[str] = mapped_column(String(50), nullable=False, default=AgentType.CONVERSATIONAL, index=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default=AgentStatus.DRAFT, index=True)
    version: Mapped[str] = mapped_column(String(50), nullable=False, default="1.0")
    config: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    system_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    model_config_dict: Mapped[Dict[str, Any]] = mapped_column("model_config", JSONB, nullable=True, server_default=text("'{}'::jsonb"))
    available_tools: Mapped[List[str]] = mapped_column(JSONB, nullable=True, server_default=text("'[]'::jsonb"))
    capabilities: Mapped[List[str]] = mapped_column(JSONB, nullable=True, server_default=text("'[]'::jsonb"))
    tags: Mapped[List[str]] = mapped_column(JSONB, nullable=True, server_default=text("'[]'::jsonb"))
    agent_metadata: Mapped[Dict[str, Any]] = mapped_column("agent_metadata", JSONB, nullable=True, server_default=text("'{}'::jsonb"))

class AgentDeployment(SystemEntity):
    __tablename__ = "agent_deployments"
    
    agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    environment: Mapped[str] = mapped_column(String(50), nullable=False, default="development")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active")
    config: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=True)
    resource_limits: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=True)
    deployed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
class AgentExecution(SystemEntity):
    __tablename__ = "agent_executions"
    
    agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False, index=True)
    deployment_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_deployments.id"), nullable=True, index=True)
    session_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    input_data: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=True)
    output_data: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tokens_used: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    execution_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    cost: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

class AgentMemory(SystemEntity):
    __tablename__ = "agent_memories"
    
    agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False, index=True)
    session_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    memory_type: Mapped[str] = mapped_column(String(50), nullable=False, default="conversation")
    content: Mapped[str] = mapped_column(Text, nullable=False)
    memory_metadata: Mapped[Dict[str, Any]] = mapped_column("memory_metadata", JSONB, nullable=True)
    importance_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    access_count: Mapped[int] = mapped_column(Integer, default=0)
    last_accessed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


