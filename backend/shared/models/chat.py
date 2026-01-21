import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum

from sqlalchemy import String, Text, ForeignKey, Integer, DateTime, text, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.models.base import SystemEntity

class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

class ChatSession(SystemEntity):
    __tablename__ = "chat_sessions"
    
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True, nullable=False)
    chain_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("chains.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_archived: Mapped[bool] = mapped_column(default=False)
    session_metadata: Mapped[Dict[str, Any]] = mapped_column("metadata", JSONB, nullable=True, server_default=text("'{}'::jsonb"))
    
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan", order_by="ChatMessage.created_at")

class ChatMessage(SystemEntity):
    __tablename__ = "chat_messages"
    
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(50), nullable=False) # user, assistant
    content: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Link to execution that produced this message (for assistant messages)
    execution_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("chain_executions.id"), nullable=True)
    
    # Metadata
    message_metadata: Mapped[Dict[str, Any]] = mapped_column("metadata", JSONB, nullable=True, server_default=text("'{}'::jsonb"))
    
    session = relationship("ChatSession", back_populates="messages")
