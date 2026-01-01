"""
Memory Management API endpoints for AI Agent Framework.

Provides REST API endpoints for:
- Storing and retrieving agent memories
- Semantic search across memories
- Conversation history management
- User preference tracking
- Memory statistics and management
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_async_db
from ..middleware.tenant import get_tenant_context, TenantContext
# Temporarily commented out to fix import issues
# from ..services.memory_manager import (
#     MemoryManagerService, MemoryType, ImportanceLevel, MemorySearchResult,
#     create_memory_manager_service
# )
from ..models.base import BaseRequest, BaseResponse


# Request/Response Models
class StoreMemoryRequest(BaseRequest):
    """Request to store a new memory."""
    
    agent_id: str = Field(..., description="Agent ID")
    content: str = Field(..., min_length=1, description="Memory content")
    memory_type: MemoryType = Field(MemoryType.CONVERSATION, description="Type of memory")
    session_id: Optional[str] = Field(None, description="Session ID for conversation memories")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    importance_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Importance score (0-1)")
    expires_at: Optional[datetime] = Field(None, description="Expiration timestamp")


class MemorySearchRequest(BaseRequest):
    """Request to search memories."""
    
    agent_id: str = Field(..., description="Agent ID")
    query: str = Field(..., min_length=1, description="Search query")
    limit: int = Field(10, ge=1, le=100, description="Maximum results")
    similarity_threshold: Optional[float] = Field(None, ge=0.0, le=1.0, description="Similarity threshold")
    memory_types: Optional[List[MemoryType]] = Field(None, description="Filter by memory types")
    session_id: Optional[str] = Field(None, description="Filter by session ID")


class MemoryResponse(BaseResponse):
    """Response containing memory information."""
    
    memory_id: str = Field(..., description="Memory ID")
    agent_id: str = Field(..., description="Agent ID")
    content: str = Field(..., description="Memory content")
    memory_type: str = Field(..., description="Memory type")
    importance_score: float = Field(..., description="Importance score")
    metadata: Dict[str, Any] = Field(..., description="Memory metadata")
    session_id: Optional[str] = Field(None, description="Session ID")
    access_count: int = Field(..., description="Number of times accessed")
    created_at: datetime = Field(..., description="Creation timestamp")
    last_accessed: Optional[datetime] = Field(None, description="Last access timestamp")


class SearchResultResponse(BaseResponse):
    """Response containing search result."""
    
    memory_id: str = Field(..., description="Memory ID")
    agent_id: str = Field(..., description="Agent ID")
    content: str = Field(..., description="Memory content")
    similarity_score: float = Field(..., description="Similarity score")
    importance_score: float = Field(..., description="Importance score")
    memory_type: str = Field(..., description="Memory type")
    metadata: Dict[str, Any] = Field(..., description="Memory metadata")
    created_at: datetime = Field(..., description="Creation timestamp")
    last_accessed: datetime = Field(..., description="Last access timestamp")
    access_count: int = Field(..., description="Access count")


class MemoryStatisticsResponse(BaseResponse):
    """Response containing memory statistics."""
    
    total_memories: int = Field(..., description="Total number of memories")
    memories_by_type: Dict[str, int] = Field(..., description="Memories grouped by type")
    average_importance_score: float = Field(..., description="Average importance score")
    system_stats: Dict[str, Any] = Field(..., description="System-level statistics")
    max_memories_per_agent: int = Field(..., description="Maximum memories per agent")
    similarity_threshold: float = Field(..., description="Current similarity threshold")


# Create router
router = APIRouter(prefix="/api/v1/memory", tags=["Memory Management"])


@router.post("/store", response_model=MemoryResponse)
async def store_memory(
    request: StoreMemoryRequest,
    session: AsyncSession = Depends(get_async_db),
    tenant_context: TenantContext = Depends(get_tenant_context)
):
    """
    Store a new memory for an agent.
    
    This endpoint allows storing various types of memories including:
    - Conversation history
    - Facts and preferences
    - Skills and context
    - Episodic and semantic memories
    """
    try:
        memory_service = await create_memory_manager_service(session, tenant_context.tenant_id)
        
        memory_id = await memory_service.store_memory(
            agent_id=request.agent_id,
            content=request.content,
            memory_type=request.memory_type,
            session_id=request.session_id,
            metadata=request.metadata,
            importance_score=request.importance_score,
            expires_at=request.expires_at,
            created_by=tenant_context.user_id
        )
        
        # Retrieve the stored memory to return complete information
        memory = await memory_service.memory_manager.access_memory(
            session, tenant_context.tenant_id, memory_id
        )
        
        if not memory:
            raise HTTPException(status_code=500, detail="Failed to retrieve stored memory")
        
        return MemoryResponse(
            memory_id=memory.id,
            agent_id=memory.agent_id,
            content=memory.content,
            memory_type=memory.memory_type,
            importance_score=memory.importance_score or 0.0,
            metadata=memory.memory_metadata or {},
            session_id=memory.session_id,
            access_count=memory.access_count,
            created_at=memory.created_at,
            last_accessed=memory.last_accessed
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to store memory: {str(e)}")


@router.post("/search", response_model=List[SearchResultResponse])
async def search_memories(
    request: MemorySearchRequest,
    session: AsyncSession = Depends(get_async_db),
    tenant_context: TenantContext = Depends(get_tenant_context)
):
    """
    Perform semantic search on agent memories.
    
    Uses vector embeddings to find semantically similar memories
    ranked by both similarity and importance scores.
    """
    try:
        memory_service = await create_memory_manager_service(session, tenant_context.tenant_id)
        
        results = await memory_service.semantic_search(
            agent_id=request.agent_id,
            query=request.query,
            limit=request.limit,
            similarity_threshold=request.similarity_threshold,
            memory_types=request.memory_types,
            session_id=request.session_id
        )
        
        return [
            SearchResultResponse(
                memory_id=result.memory_id,
                agent_id=result.agent_id,
                content=result.content,
                similarity_score=result.similarity_score,
                importance_score=result.importance_score,
                memory_type=result.memory_type,
                metadata=result.metadata,
                created_at=result.created_at,
                last_accessed=result.last_accessed,
                access_count=result.access_count
            )
            for result in results
        ]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to search memories: {str(e)}")


@router.get("/conversation/{agent_id}/{session_id}", response_model=List[SearchResultResponse])
async def get_conversation_history(
    agent_id: str,
    session_id: str,
    limit: Optional[int] = Query(50, ge=1, le=200, description="Maximum messages to return"),
    session: AsyncSession = Depends(get_async_db),
    tenant_context: TenantContext = Depends(get_tenant_context)
):
    """
    Get conversation history for a specific agent and session.
    
    Returns messages in chronological order for maintaining
    conversation continuity.
    """
    try:
        memory_service = await create_memory_manager_service(session, tenant_context.tenant_id)
        
        history = await memory_service.get_conversation_history(
            agent_id=agent_id,
            session_id=session_id,
            limit=limit
        )
        
        return [
            SearchResultResponse(
                memory_id=result.memory_id,
                agent_id=result.agent_id,
                content=result.content,
                similarity_score=result.similarity_score,
                importance_score=result.importance_score,
                memory_type=result.memory_type,
                metadata=result.metadata,
                created_at=result.created_at,
                last_accessed=result.last_accessed,
                access_count=result.access_count
            )
            for result in history
        ]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get conversation history: {str(e)}")


@router.get("/preferences/{agent_id}", response_model=List[SearchResultResponse])
async def get_user_preferences(
    agent_id: str,
    user_id: Optional[str] = Query(None, description="Filter by specific user"),
    session: AsyncSession = Depends(get_async_db),
    tenant_context: TenantContext = Depends(get_tenant_context)
):
    """
    Get user preferences and important facts for an agent.
    
    Returns preferences and facts ordered by importance score
    to help personalize agent responses.
    """
    try:
        memory_service = await create_memory_manager_service(session, tenant_context.tenant_id)
        
        preferences = await memory_service.get_user_preferences(
            agent_id=agent_id,
            user_id=user_id
        )
        
        return [
            SearchResultResponse(
                memory_id=result.memory_id,
                agent_id=result.agent_id,
                content=result.content,
                similarity_score=result.similarity_score,
                importance_score=result.importance_score,
                memory_type=result.memory_type,
                metadata=result.metadata,
                created_at=result.created_at,
                last_accessed=result.last_accessed,
                access_count=result.access_count
            )
            for result in preferences
        ]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get user preferences: {str(e)}")


@router.post("/manage-capacity/{agent_id}")
async def manage_memory_capacity(
    agent_id: str,
    session: AsyncSession = Depends(get_async_db),
    tenant_context: TenantContext = Depends(get_tenant_context)
):
    """
    Manage memory capacity for an agent.
    
    Removes less important memories when capacity limits are reached,
    using intelligent scoring to preserve the most valuable memories.
    """
    try:
        memory_service = await create_memory_manager_service(session, tenant_context.tenant_id)
        
        removed_count = await memory_service.manage_memory_capacity(agent_id)
        
        return {
            "message": f"Memory capacity managed successfully",
            "memories_removed": removed_count,
            "agent_id": agent_id
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to manage memory capacity: {str(e)}")


@router.post("/cleanup-expired")
async def cleanup_expired_memories(
    session: AsyncSession = Depends(get_async_db),
    tenant_context: TenantContext = Depends(get_tenant_context)
):
    """
    Clean up expired memories for the tenant.
    
    Removes memories that have passed their expiration date
    to free up storage space and maintain performance.
    """
    try:
        memory_service = await create_memory_manager_service(session, tenant_context.tenant_id)
        
        cleaned_count = await memory_service.cleanup_expired_memories()
        
        return {
            "message": "Expired memories cleaned up successfully",
            "memories_cleaned": cleaned_count,
            "tenant_id": tenant_context.tenant_id
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cleanup expired memories: {str(e)}")


@router.get("/statistics", response_model=MemoryStatisticsResponse)
async def get_memory_statistics(
    agent_id: Optional[str] = Query(None, description="Filter by specific agent"),
    session: AsyncSession = Depends(get_async_db),
    tenant_context: TenantContext = Depends(get_tenant_context)
):
    """
    Get memory usage statistics for the tenant or specific agent.
    
    Provides insights into memory usage patterns, types of memories stored,
    and system performance metrics.
    """
    try:
        memory_service = await create_memory_manager_service(session, tenant_context.tenant_id)
        
        stats = await memory_service.get_statistics(agent_id)
        
        return MemoryStatisticsResponse(**stats)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get memory statistics: {str(e)}")


@router.get("/health")
async def memory_system_health():
    """
    Check the health of the memory management system.
    
    Returns status information about the vector database,
    embedding model, and system components.
    """
    try:
        # Temporarily commented out to fix import issues
        # from ..services.memory_manager import get_memory_manager
        # 
        # memory_manager = await get_memory_manager()
        
        # Basic health checks
        health_status = {
            "status": "healthy",
            "embedding_model": memory_manager.config.embedding_model,
            "vector_db_path": memory_manager.config.vector_db_path,
            "max_memories_per_agent": memory_manager.config.max_memories_per_agent,
            "similarity_threshold": memory_manager.config.similarity_threshold,
            "system_stats": memory_manager._stats.copy()
        }
        
        return health_status
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }