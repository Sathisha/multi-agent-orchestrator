
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from uuid import UUID

from sqlalchemy import String, Text, ForeignKey, Integer, Float, DateTime
from sqlalchemy.dialects.postgresql import JSONB, UUID as UUIDType
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.models.base import SystemEntity

class RAGSourceType(str, Enum):
    WEBSITE = "website"
    PDF = "pdf"
    TEXT = "text"

class RAGStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class RAGSource(SystemEntity):
    __tablename__ = "rag_sources"
    
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False, default=RAGSourceType.WEBSITE)
    content_source: Mapped[str] = mapped_column(Text, nullable=False) # URL or File Path
    status: Mapped[str] = mapped_column(String(50), nullable=False, default=RAGStatus.PENDING)
    
    owner_id: Mapped[UUID] = mapped_column(UUIDType(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    
    # Access control
    is_public: Mapped[bool] = mapped_column(default=False, nullable=False, index=True)
    
    # Metadata for processing stats (chunks count, vector ids, etc)
    processing_metadata: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=True)
    
    # For now, let's keep it simple. If we need N-N with agents, we'll add a link table.
    
class AgentRAGSource(SystemEntity):
    __tablename__ = "agent_rag_sources"
    
    agent_id: Mapped[UUID] = mapped_column(UUIDType(as_uuid=True), ForeignKey("agents.id"), nullable=False, index=True)
    rag_source_id: Mapped[UUID] = mapped_column(UUIDType(as_uuid=True), ForeignKey("rag_sources.id"), nullable=False, index=True)

class RAGSourceRole(SystemEntity):
    """Role-based access control for RAG sources."""
    __tablename__ = "rag_source_roles"
    
    rag_source_id: Mapped[UUID] = mapped_column(UUIDType(as_uuid=True), ForeignKey("rag_sources.id", ondelete="CASCADE"), nullable=False, index=True)
    role_id: Mapped[UUID] = mapped_column(UUIDType(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), nullable=False, index=True)
    access_type: Mapped[str] = mapped_column(String(50), nullable=False)  # 'view', 'query', 'modify'

