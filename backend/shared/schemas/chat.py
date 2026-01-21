from uuid import UUID
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from shared.models.chat import MessageRole

class ChatMessageBase(BaseModel):
    role: MessageRole
    content: str
    message_metadata: Optional[Dict[str, Any]] = None

class ChatMessageCreate(ChatMessageBase):
    pass

class ChatMessageResponse(ChatMessageBase):
    id: UUID
    session_id: UUID
    created_at: datetime
    execution_id: Optional[UUID] = None
    
    class Config:
        from_attributes = True

class ChatSessionBase(BaseModel):
    title: Optional[str] = None
    chain_id: UUID
    session_metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, serialization_alias="metadata")

class ChatSessionCreate(ChatSessionBase):
    pass

class ChatSessionResponse(ChatSessionBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None
    messages: List[ChatMessageResponse] = []
    
    class Config:
        from_attributes = True
