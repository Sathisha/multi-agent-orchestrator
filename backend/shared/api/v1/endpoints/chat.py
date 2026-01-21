import logging
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status, BackgroundTasks
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from shared.database.connection import get_async_db
from shared.models.chat import ChatSession, ChatMessage, MessageRole
from shared.models.chain import Chain
from shared.schemas.chat import (
    ChatSessionCreate, ChatSessionResponse, 
    ChatMessageCreate, ChatMessageResponse
)
from shared.api.auth import get_current_user
from shared.models.user import User
from shared.services.chain_orchestrator import ChainOrchestratorService, ChainExecutionError
from shared.api.v1.endpoints.chains import get_chain_orchestrator_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/chat", tags=["Chat"])

@router.post("/sessions", response_model=ChatSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    request: ChatSessionCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_db)
):
    """Create a new chat session linked to a specific chain."""
    # Verify chain exists
    chain_result = await session.execute(select(Chain).where(Chain.id == request.chain_id))
    chain = chain_result.scalar_one_or_none()
    if not chain:
        raise HTTPException(status_code=404, detail="Chain not found")

    new_session = ChatSession(
        user_id=current_user.id,
        chain_id=request.chain_id,
        title=request.title or f"Chat with {chain.name}",
        session_metadata=request.session_metadata
    )
    session.add(new_session)
    await session.commit()
    await session.refresh(new_session)
    
    return ChatSessionResponse(
        id=new_session.id,
        user_id=new_session.user_id,
        chain_id=new_session.chain_id,
        title=new_session.title,
        created_at=new_session.created_at,
        updated_at=new_session.updated_at,
        messages=[]
    )
    return new_session

@router.get("/sessions", response_model=List[ChatSessionResponse])
async def list_sessions(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_db)
):
    """List chat sessions for the current user."""
    query = select(ChatSession).where(
        ChatSession.user_id == current_user.id,
        ChatSession.is_archived == False
    ).options(selectinload(ChatSession.messages)).order_by(desc(ChatSession.updated_at)).offset(skip).limit(limit)
    
    result = await session.execute(query)
    sessions = result.scalars().all()
    return sessions

@router.get("/sessions/{session_id}", response_model=ChatSessionResponse)
async def get_session(
    session_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_db)
):
    """Get a specific chat session with its messages."""
    result = await session.execute(
        select(ChatSession)
        .options(selectinload(ChatSession.messages))
        .where(ChatSession.id == session_id, ChatSession.user_id == current_user.id)
    )
    chat_session = result.scalar_one_or_none()
    if not chat_session:
        raise HTTPException(status_code=404, detail="Session not found")
    return chat_session

@router.post("/sessions/{session_id}/messages", response_model=ChatMessageResponse)
async def send_message(
    session_id: UUID,
    message: ChatMessageCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_db),
    orchestrator: ChainOrchestratorService = Depends(get_chain_orchestrator_service)
):
    """Send a message to the chat session and execute the chain to get a response."""
    # Get session
    result = await session.execute(
        select(ChatSession).where(ChatSession.id == session_id, ChatSession.user_id == current_user.id)
    )
    chat_session = result.scalar_one_or_none()
    if not chat_session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Save User Message
    user_msg = ChatMessage(
        session_id=session_id,
        role=MessageRole.USER,
        content=message.content,
        message_metadata=message.message_metadata
    )
    session.add(user_msg)
    await session.commit()
    await session.refresh(user_msg)
    
    # Update session updated_at
    chat_session.updated_at = datetime.now()
    session.add(chat_session)
    await session.commit()
    
    # Prepare Input for Chain
    # Fetch recent history (exclude the message we just added to avoid duplication if we append manually, 
    # but usually we want to include it in history or as current input. 
    # Here we treat current message as 'input' variable and past messages as 'chat_history'.)
    
    history_result = await session.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id, ChatMessage.id != user_msg.id)
        .order_by(ChatMessage.created_at)
    )
    history = history_result.scalars().all()
    
    formatted_history = [
        {"role": msg.role, "content": msg.content} for msg in history
    ]
    
    # We also include the current message in the history for the LLM if the chain handles it that way.
    # But typically: input = current prompt, history = past context.
    
    chain_input = {
        "input": message.content,
        "chat_history": formatted_history
    }
    
    # Extract model override from session metadata
    model_override = None
    if chat_session.session_metadata:
        model_override = chat_session.session_metadata.get("model_override")

    try:
        # Execute Chain Synchronously (wait for response)
        # Using a timeout of 60 seconds for chat interactions (adjust as needed)
        execution = await orchestrator.execute_chain(
            session=session,
            chain_id=chat_session.chain_id,
            input_data=chain_input,
            execution_name=f"Chat Execution {user_msg.id}",
            timeout_seconds=300,
            model_override=model_override
        )
        
        # Check execution status
        await session.refresh(execution)
        
        output_data = execution.output_data or {}
        logger.info(f"DEBUG: output_data type: {type(output_data)}")
        logger.info(f"DEBUG: output_data full: {output_data}")

        # Heuristic to find the response text
        response_text = None
        if isinstance(output_data, dict):
            # 0. SACP Top-level 'message' check (Standard Agent Communication Protocol)
            if "message" in output_data and isinstance(output_data["message"], str):
                 response_text = output_data["message"]

            # 1. Try nested data fields if top-level SACP message not found
            if not response_text:
                data_dict = output_data.get("data")
                if isinstance(data_dict, dict):
                    # Prioritize 'message' (final human readable answer)
                    if "message" in data_dict and isinstance(data_dict["message"], str):
                        response_text = data_dict["message"]
                    # Then 'result' (structured outcome)
                    elif "result" in data_dict and isinstance(data_dict["result"], str):
                        response_text = data_dict["result"]
                    # Fallback to 'raw_output' (if parsing failed or no structured answer)
                    elif "raw_output" in data_dict and isinstance(data_dict["raw_output"], str):
                        response_text = data_dict["raw_output"]

            # 2. Try top-level common fields if nested lookup failed
            if not response_text:
                # Prefer 'output', 'response', 'text', 'answer', 'content'
                for key in ['output', 'response', 'text', 'answer', 'content']:
                    if key in output_data and isinstance(output_data[key], str):
                        val = output_data[key]
                        # Check if the string itself resembles a dict/json
                        # Fix precedence: check startswith AND (contains keywords)
                        if isinstance(val, str) and val.strip().startswith("{") and ("result" in val or "message" in val or "thought" in val):
                            try:
                                # Try to clean potential python dict string (single quotes) or json (double quotes)
                                import ast
                                # Use literal_eval for python-style dicts (common in logs/repr)
                                parsed = ast.literal_eval(val) if "'" in val else json.loads(val)
                                
                                if isinstance(parsed, dict):
                                    # Extract message > result > raw content
                                    if "message" in parsed and isinstance(parsed["message"], str) and parsed["message"].strip():
                                        response_text = parsed["message"]
                                        break
                                    if "result" in parsed and isinstance(parsed["result"], str) and parsed["result"].strip():
                                        response_text = parsed["result"]
                                        break
                                    # If only thought is present, maybe show it? Or look for other fields.
                                    # For now, if we found a dict but no message/result, we might want to keep looking or use the raw string.
                            except Exception:
                                pass # Not parseable, treat as plain text
                        
                        response_text = val
                        break
            
            # 3. Fallback strategies
            if not response_text:
                # If only one key, take it
                if len(output_data) == 1:
                    response_text = str(list(output_data.values())[0])
                else:
                    response_text = str(output_data) # Fallback to JSON string
        else:
            response_text = str(output_data)

        assistant_msg = ChatMessage(
            session_id=session_id,
            role=MessageRole.ASSISTANT,
            content=response_text,
            execution_id=execution.id
        )
        session.add(assistant_msg)
        await session.commit()
        await session.refresh(assistant_msg)
        
        return assistant_msg

    except Exception as e:
        logger.error(f"Error in chat execution: {e}", exc_info=True)
        # Create error message
        err_msg = ChatMessage(
            session_id=session_id,
            role=MessageRole.ASSISTANT,
            content=f"Error executing request: {str(e)}",
            message_metadata={"error": True}
        )
        session.add(err_msg)
        await session.commit()
        await session.refresh(err_msg)
        return err_msg
