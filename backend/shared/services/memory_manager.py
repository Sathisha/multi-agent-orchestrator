"""
Memory Management System for AI Agent Framework

This module implements a comprehensive memory management system with:
- Chroma vector database for semantic memory storage
- Sentence Transformers for embeddings
- Semantic search and retrieval mechanisms
- Intelligent memory management with importance scoring
- Conversation history and user preference tracking
- Memory persistence across agent restarts
"""

import asyncio
import logging
import os
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum


import chromadb
from chromadb.config import Settings

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.orm import selectinload

from ..models.agent import AgentMemory, Agent
from .base import BaseService
from .id_generator import IDGeneratorService


class MemoryType(str, Enum):
    """Types of memory that can be stored."""
    
    CONVERSATION = "conversation"
    FACT = "fact"
    PREFERENCE = "preference"
    SKILL = "skill"
    CONTEXT = "context"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"


class ImportanceLevel(str, Enum):
    """Importance levels for memory scoring."""
    
    CRITICAL = "critical"      # 0.9-1.0
    HIGH = "high"             # 0.7-0.89
    MEDIUM = "medium"         # 0.4-0.69
    LOW = "low"               # 0.1-0.39
    MINIMAL = "minimal"       # 0.0-0.09


@dataclass
class MemorySearchResult:
    """Result from semantic memory search."""
    
    memory_id: str
    agent_id: str
    content: str
    similarity_score: float
    importance_score: float
    memory_type: str
    metadata: Dict[str, Any]
    created_at: datetime
    last_accessed: datetime
    access_count: int


@dataclass
class MemoryConfig:
    """Configuration for memory management."""
    
    max_memories_per_agent: int = 10000
    max_conversation_length: int = 50
    importance_decay_rate: float = 0.95
    similarity_threshold: float = 0.7
    cleanup_interval_hours: int = 24
    embedding_provider: str = "openai"  # "openai", "ollama", or "local"
    embedding_model: str = "text-embedding-3-small"  # For OpenAI, Ollama or local model name
    openai_api_key: Optional[str] = None  # Optional, uses OPENAI_API_KEY env var if not set
    ollama_base_url: str = "http://ollama:11434"
    vector_db_path: str = "./data/chroma"


class MemoryManager:
    """
    Comprehensive memory management system for AI agents.
    
    Provides semantic memory storage, retrieval, and intelligent management
    with importance scoring and conversation continuity.
    """
    
    def __init__(self, config: Optional[MemoryConfig] = None):
        self.config = config or MemoryConfig()
        self.logger = logging.getLogger(__name__)
        
        # Initialize embedding provider
        self._embedding_provider = None
        self._chroma_client = None
        self._collections: Dict[str, Any] = {}
        
        # Memory statistics
        self._stats = {
            "total_memories": 0,
            "searches_performed": 0,
            "cache_hits": 0,
            "cache_misses": 0
        }
    
    async def initialize(self):
        """Initialize the memory management system."""
        try:
            # Initialize embedding provider
            from .embeddings import OpenAIEmbeddingProvider, LocalEmbeddingProvider, OllamaEmbeddingProvider
            
            if self.config.embedding_provider == "openai":
                self.logger.info(f"Initializing OpenAI embedding provider: {self.config.embedding_model}")
                self._embedding_provider = OpenAIEmbeddingProvider(
                    api_key=self.config.openai_api_key,
                    model=self.config.embedding_model
                )
            elif self.config.embedding_provider == "ollama":
                self.logger.info(f"Initializing Ollama embedding provider: {self.config.embedding_model} at {self.config.ollama_base_url}")
                self._embedding_provider = OllamaEmbeddingProvider(
                    base_url=self.config.ollama_base_url,
                    model=self.config.embedding_model
                )
            else:  # local
                self.logger.info(f"Initializing local embedding model: {self.config.embedding_model}")
                self._embedding_provider = LocalEmbeddingProvider(
                    model_name=self.config.embedding_model
                )
            
            await self._embedding_provider.initialize()
            
            # Initialize Chroma vector database
            self.logger.info(f"Initializing Chroma database at: {self.config.vector_db_path}")
            os.makedirs(self.config.vector_db_path, exist_ok=True)
            
            self._chroma_client = chromadb.PersistentClient(
                path=self.config.vector_db_path,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            
            self.logger.info("Memory management system initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize memory management system: {e}")
            raise
    
    def _get_collection_name(self, tenant_id: str, agent_id: str) -> str:
        """Generate collection name for tenant and agent."""
        return f"tenant_{tenant_id}_agent_{agent_id}"
    
    async def _get_or_create_collection(self, tenant_id: str, agent_id: str):
        """Get or create a Chroma collection for the agent."""
        collection_name = self._get_collection_name(tenant_id, agent_id)
        
        if collection_name not in self._collections:
            try:
                # Try to get existing collection
                collection = self._chroma_client.get_collection(collection_name)
            except Exception:
                # Create new collection if it doesn't exist
                collection = self._chroma_client.create_collection(
                    name=collection_name,
                    metadata={"tenant_id": tenant_id, "agent_id": agent_id}
                )
            
            self._collections[collection_name] = collection
        
        return self._collections[collection_name]
    
    async def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text using configured provider."""
        if not self._embedding_provider:
            raise RuntimeError("Embedding provider not initialized")
        
        return await self._embedding_provider.generate_embedding(text)
    
    def _calculate_importance_score(
        self,
        content: str,
        memory_type: MemoryType,
        metadata: Dict[str, Any]
    ) -> float:
        """
        Calculate importance score for memory based on content and context.
        
        Scoring factors:
        - Memory type (conversation < fact < preference < skill)
        - Content length and complexity
        - Recency
        - User interaction indicators
        - Emotional content indicators
        """
        base_scores = {
            MemoryType.CONVERSATION: 0.3,
            MemoryType.FACT: 0.6,
            MemoryType.PREFERENCE: 0.8,
            MemoryType.SKILL: 0.9,
            MemoryType.CONTEXT: 0.4,
            MemoryType.EPISODIC: 0.5,
            MemoryType.SEMANTIC: 0.7
        }
        
        score = base_scores.get(memory_type, 0.5)
        
        # Adjust based on content length (longer content often more important)
        content_length = len(content)
        if content_length > 500:
            score += 0.1
        elif content_length > 200:
            score += 0.05
        
        # Adjust based on metadata indicators
        if metadata.get("user_explicit", False):
            score += 0.2  # User explicitly mentioned this
        
        if metadata.get("emotional_content", False):
            score += 0.1  # Emotional content is often important
        
        if metadata.get("decision_related", False):
            score += 0.15  # Decision-related content is important
        
        # Ensure score is within bounds
        return min(max(score, 0.0), 1.0)
    
    async def store_memory(
        self,
        session: AsyncSession,
        tenant_id: str,
        agent_id: str,
        content: str,
        memory_type: MemoryType = MemoryType.CONVERSATION,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        importance_score: Optional[float] = None,
        expires_at: Optional[datetime] = None,
        created_by: Optional[str] = None
    ) -> str:
        """
        Store a memory with semantic embedding.
        
        Returns the memory ID.
        """
        if not content or not content.strip():
            raise ValueError("Memory content cannot be empty")
        
        metadata = metadata or {}
        
        # Calculate importance score if not provided
        if importance_score is None:
            importance_score = self._calculate_importance_score(content, memory_type, metadata)
        
        # Generate embedding
        embedding = await self._generate_embedding(content)
        
        # Create memory record in database
        memory_id = IDGeneratorService.generate_memory_id()
        
        memory = AgentMemory(
            id=memory_id,
            # tenant_id removed
            agent_id=agent_id,
            session_id=session_id,
            memory_type=memory_type.value,
            content=content,
            memory_metadata=metadata,
            importance_score=importance_score,
            access_count=0,
            # expires_at removed
            # created_by=created_by # handled by BaseEntity if properly passed, but careful with types
        )
        if created_by:
             try:
                 memory.created_by = uuid.UUID(created_by)
             except:
                 pass
        
        session.add(memory)
        await session.commit()
        
        # Store in vector database
        collection = await self._get_or_create_collection(tenant_id, agent_id)
        
        collection.add(
            embeddings=[embedding],
            documents=[content],
            metadatas=[{
                "memory_id": memory_id,
                "memory_type": memory_type.value,
                "importance_score": importance_score,
                "session_id": session_id or "",
                "created_at": datetime.utcnow().isoformat(),
                **metadata
            }],
            ids=[memory_id]
        )
        
        self._stats["total_memories"] += 1
        self.logger.info(f"Stored memory {memory_id} for agent {agent_id}")
        
        return memory_id
    
    async def semantic_search(
        self,
        session: AsyncSession,
        tenant_id: str,
        agent_id: str,
        query: str,
        limit: int = 10,
        similarity_threshold: Optional[float] = None,
        memory_types: Optional[List[MemoryType]] = None,
        session_id: Optional[str] = None
    ) -> List[MemorySearchResult]:
        """
        Perform semantic search on agent memories.
        
        Returns memories ranked by similarity and importance.
        """
        if not query or not query.strip():
            return []
        
        similarity_threshold = similarity_threshold or self.config.similarity_threshold
        
        # Generate query embedding
        query_embedding = await self._generate_embedding(query)
        
        # Search in vector database
        collection = await self._get_or_create_collection(tenant_id, agent_id)
        
        # Build where clause for filtering
        where_clause = {}
        if memory_types:
            where_clause["memory_type"] = {"$in": [mt.value for mt in memory_types]}
        if session_id:
            where_clause["session_id"] = session_id
        
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=limit * 2,  # Get more results to filter
            where=where_clause if where_clause else None,
            include=["documents", "metadatas", "distances"]
        )
        
        # Process results
        search_results = []
        
        if results["ids"] and results["ids"][0]:
            # Get memory details from database
            memory_ids = results["ids"][0]
            
            stmt = select(AgentMemory).where(
                and_(
                    # AgentMemory.tenant_id == tenant_id, # Removed
                    AgentMemory.id.in_(memory_ids),
                    # or_(
                    #     AgentMemory.expires_at.is_(None),
                    #     AgentMemory.expires_at > datetime.utcnow()
                    # ) # Removed expires_at
                )
            )
            
            db_result = await session.execute(stmt)
            memories_by_id = {m.id: m for m in db_result.scalars().all()}
            
            # Combine vector search results with database records
            for i, memory_id in enumerate(memory_ids):
                if memory_id not in memories_by_id:
                    continue
                
                memory = memories_by_id[memory_id]
                distance = results["distances"][0][i]
                similarity_score = 1.0 - distance  # Convert distance to similarity
                
                if similarity_score < similarity_threshold:
                    continue
                
                metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                
                search_results.append(MemorySearchResult(
                    memory_id=memory_id,
                    agent_id=agent_id,
                    content=memory.content,
                    similarity_score=similarity_score,
                    importance_score=memory.importance_score or 0.0,
                    memory_type=memory.memory_type,
                    metadata=memory.memory_metadata or {},
                    created_at=memory.created_at,
                    last_accessed=memory.last_accessed_at or memory.created_at,
                    access_count=memory.access_count
                ))
        
        # Sort by combined score (similarity * importance)
        search_results.sort(
            key=lambda x: x.similarity_score * (x.importance_score + 0.1),
            reverse=True
        )
        
        self._stats["searches_performed"] += 1
        
        return search_results[:limit]
    
    async def get_conversation_history(
        self,
        session: AsyncSession,
        tenant_id: str,
        agent_id: str,
        session_id: str,
        limit: Optional[int] = None
    ) -> List[MemorySearchResult]:
        """
        Get conversation history for a specific session.
        """
        limit = limit or self.config.max_conversation_length
        
        stmt = select(AgentMemory).where(
            and_(
                # AgentMemory.tenant_id == tenant_id,
                AgentMemory.agent_id == agent_id,
                AgentMemory.session_id == session_id,
                AgentMemory.memory_type == MemoryType.CONVERSATION.value,
                # or_(
                #     AgentMemory.expires_at.is_(None),
                #     AgentMemory.expires_at > datetime.utcnow()
                # )
            )
        ).order_by(AgentMemory.created_at.desc()).limit(limit)
        
        result = await session.execute(stmt)
        memories = list(result.scalars().all())
        
        # Convert to search results format
        conversation_history = []
        for memory in reversed(memories):  # Reverse to get chronological order
            conversation_history.append(MemorySearchResult(
                memory_id=memory.id,
                agent_id=agent_id,
                content=memory.content,
                similarity_score=1.0,  # Perfect match for conversation history
                importance_score=memory.importance_score or 0.0,
                memory_type=memory.memory_type,
                metadata=memory.memory_metadata or {},
                created_at=memory.created_at,
                last_accessed=memory.last_accessed_at or memory.created_at,
                access_count=memory.access_count
            ))
        
        return conversation_history
    
    async def get_user_preferences(
        self,
        session: AsyncSession,
        tenant_id: str,
        agent_id: str,
        user_id: Optional[str] = None
    ) -> List[MemorySearchResult]:
        """
        Get user preferences and important facts.
        """
        stmt = select(AgentMemory).where(
            and_(
                # AgentMemory.tenant_id == tenant_id,
                AgentMemory.agent_id == agent_id,
                AgentMemory.memory_type.in_([
                    MemoryType.PREFERENCE.value,
                    MemoryType.FACT.value
                ]),
                # or_(
                #     AgentMemory.expires_at.is_(None),
                #     AgentMemory.expires_at > datetime.utcnow()
                # )
            )
        ).order_by(desc(AgentMemory.importance_score))
        
        if user_id:
            stmt = stmt.where(AgentMemory.created_by == user_id)
        
        result = await session.execute(stmt)
        memories = list(result.scalars().all())
        
        preferences = []
        for memory in memories:
            preferences.append(MemorySearchResult(
                memory_id=memory.id,
                agent_id=agent_id,
                content=memory.content,
                similarity_score=1.0,
                importance_score=memory.importance_score or 0.0,
                memory_type=memory.memory_type,
                metadata=memory.memory_metadata or {},
                created_at=memory.created_at,
                last_accessed=memory.last_accessed_at or memory.created_at,
                access_count=memory.access_count
            ))
        
        return preferences
    
    async def access_memory(
        self,
        session: AsyncSession,
        tenant_id: str,
        memory_id: str
    ) -> Optional[AgentMemory]:
        """
        Access a memory and update access statistics.
        """
        stmt = select(AgentMemory).where(
            and_(
                # AgentMemory.tenant_id == tenant_id,
                AgentMemory.id == memory_id
            )
        )
        
        result = await session.execute(stmt)
        memory = result.scalar_one_or_none()
        
        if memory:
            memory.access_count += 1
            memory.last_accessed_at = datetime.utcnow()
            await session.commit()
        
        return memory
    
    async def manage_memory_capacity(
        self,
        session: AsyncSession,
        tenant_id: str,
        agent_id: str
    ) -> int:
        """
        Manage memory capacity by removing less important memories.
        
        Returns the number of memories removed.
        """
        # Count current memories
        count_stmt = select(func.count(AgentMemory.id)).where(
            and_(
                # AgentMemory.tenant_id == tenant_id,
                AgentMemory.agent_id == agent_id,
                # or_(
                #     AgentMemory.expires_at.is_(None),
                #     AgentMemory.expires_at > datetime.utcnow()
                # )
            )
        )
        
        result = await session.execute(count_stmt)
        current_count = result.scalar()
        
        if current_count <= self.config.max_memories_per_agent:
            return 0
        
        # Calculate how many to remove
        memories_to_remove = current_count - int(self.config.max_memories_per_agent * 0.8)
        
        # Get least important memories
        stmt = select(AgentMemory).where(
            and_(
                # AgentMemory.tenant_id == tenant_id,
                AgentMemory.agent_id == agent_id,
                # or_(
                #     AgentMemory.expires_at.is_(None),
                #     AgentMemory.expires_at > datetime.utcnow()
                # )
            )
        ).order_by(
            AgentMemory.importance_score.asc(),
            AgentMemory.access_count.asc(),
            AgentMemory.created_at.asc()
        ).limit(memories_to_remove)
        
        result = await session.execute(stmt)
        memories_to_delete = list(result.scalars().all())
        
        # Remove from vector database
        collection = await self._get_or_create_collection(tenant_id, agent_id)
        memory_ids_to_delete = [m.id for m in memories_to_delete]
        
        try:
            collection.delete(ids=memory_ids_to_delete)
        except Exception as e:
            self.logger.warning(f"Failed to delete from vector database: {e}")
        
        # Remove from SQL database
        for memory in memories_to_delete:
            await session.delete(memory)
        
        await session.commit()
        
        self.logger.info(f"Removed {len(memories_to_delete)} memories for agent {agent_id}")
        return len(memories_to_delete)
    
    async def cleanup_expired_memories(
        self,
        session: AsyncSession,
        tenant_id: str
    ) -> int:
        """
        Clean up expired memories for a tenant.
        
        Returns the number of memories cleaned up.
        """
        # Get expired memories
        # Get expired memories - NO OP since no expires_at
        return 0
        # stmt = select(AgentMemory).where(...)
        
        result = await session.execute(stmt)
        expired_memories = list(result.scalars().all())
        
        if not expired_memories:
            return 0
        
        # Group by agent for vector database cleanup
        memories_by_agent = {}
        for memory in expired_memories:
            if memory.agent_id not in memories_by_agent:
                memories_by_agent[memory.agent_id] = []
            memories_by_agent[memory.agent_id].append(memory.id)
        
        # Remove from vector databases
        for agent_id, memory_ids in memories_by_agent.items():
            try:
                collection = await self._get_or_create_collection(tenant_id, agent_id)
                collection.delete(ids=memory_ids)
            except Exception as e:
                self.logger.warning(f"Failed to delete expired memories from vector database: {e}")
        
        # Remove from SQL database
        for memory in expired_memories:
            await session.delete(memory)
        
        await session.commit()
        
        self.logger.info(f"Cleaned up {len(expired_memories)} expired memories for tenant {tenant_id}")
        return len(expired_memories)
    
    async def get_memory_statistics(
        self,
        session: AsyncSession,
        tenant_id: str,
        agent_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get memory usage statistics.
        """
        base_query = select(AgentMemory) # .where(AgentMemory.tenant_id == tenant_id)
        
        if agent_id:
            base_query = base_query.where(AgentMemory.agent_id == agent_id)
        
        # Total memories
        total_stmt = select(func.count(AgentMemory.id)).select_from(base_query.subquery())
        total_result = await session.execute(total_stmt)
        total_memories = total_result.scalar()
        
        # Memories by type
        type_stmt = select(
            AgentMemory.memory_type,
            func.count(AgentMemory.id)
        ) # .where(AgentMemory.tenant_id == tenant_id)
        
        if agent_id:
            type_stmt = type_stmt.where(AgentMemory.agent_id == agent_id)
        
        type_stmt = type_stmt.group_by(AgentMemory.memory_type)
        type_result = await session.execute(type_stmt)
        memories_by_type = dict(type_result.all())
        
        # Average importance score
        avg_stmt = select(func.avg(AgentMemory.importance_score)).select_from(base_query.subquery())
        avg_result = await session.execute(avg_stmt)
        avg_importance = avg_result.scalar() or 0.0
        
        return {
            "total_memories": total_memories,
            "memories_by_type": memories_by_type,
            "average_importance_score": float(avg_importance),
            "system_stats": self._stats.copy(),
            "max_memories_per_agent": self.config.max_memories_per_agent,
            "similarity_threshold": self.config.similarity_threshold
        }


class MemoryManagerService(BaseService):
    """
    Service wrapper for MemoryManager with tenant support.
    """
    
    def __init__(self, session: AsyncSession, tenant_id: str, memory_manager: MemoryManager):
        super().__init__(session, AgentMemory)
        self.tenant_id = tenant_id
        self.memory_manager = memory_manager
    
    async def store_memory(
        self,
        agent_id: str,
        content: str,
        memory_type: MemoryType = MemoryType.CONVERSATION,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        importance_score: Optional[float] = None,
        expires_at: Optional[datetime] = None,
        created_by: Optional[str] = None
    ) -> str:
        """Store a memory for an agent."""
        return await self.memory_manager.store_memory(
            session=self.session,
            tenant_id=self.tenant_id,
            agent_id=agent_id,
            content=content,
            memory_type=memory_type,
            session_id=session_id,
            metadata=metadata,
            importance_score=importance_score,
            expires_at=expires_at,
            created_by=created_by
        )
    
    async def semantic_search(
        self,
        agent_id: str,
        query: str,
        limit: int = 10,
        similarity_threshold: Optional[float] = None,
        memory_types: Optional[List[MemoryType]] = None,
        session_id: Optional[str] = None
    ) -> List[MemorySearchResult]:
        """Perform semantic search on agent memories."""
        return await self.memory_manager.semantic_search(
            session=self.session,
            tenant_id=self.tenant_id,
            agent_id=agent_id,
            query=query,
            limit=limit,
            similarity_threshold=similarity_threshold,
            memory_types=memory_types,
            session_id=session_id
        )
    
    async def get_conversation_history(
        self,
        agent_id: str,
        session_id: str,
        limit: Optional[int] = None
    ) -> List[MemorySearchResult]:
        """Get conversation history for a session."""
        return await self.memory_manager.get_conversation_history(
            session=self.session,
            tenant_id=self.tenant_id,
            agent_id=agent_id,
            session_id=session_id,
            limit=limit
        )
    
    async def get_user_preferences(
        self,
        agent_id: str,
        user_id: Optional[str] = None
    ) -> List[MemorySearchResult]:
        """Get user preferences and important facts."""
        return await self.memory_manager.get_user_preferences(
            session=self.session,
            tenant_id=self.tenant_id,
            agent_id=agent_id,
            user_id=user_id
        )
    
    async def manage_memory_capacity(self, agent_id: str) -> int:
        """Manage memory capacity for an agent."""
        return await self.memory_manager.manage_memory_capacity(
            session=self.session,
            tenant_id=self.tenant_id,
            agent_id=agent_id
        )
    
    async def cleanup_expired_memories(self) -> int:
        """Clean up expired memories for the tenant."""
        return await self.memory_manager.cleanup_expired_memories(
            session=self.session,
            tenant_id=self.tenant_id
        )
    
    async def get_statistics(self, agent_id: Optional[str] = None) -> Dict[str, Any]:
        """Get memory usage statistics."""
        return await self.memory_manager.get_memory_statistics(
            session=self.session,
            tenant_id=self.tenant_id,
            agent_id=agent_id
        )


# Global memory manager instance
_memory_manager: Optional[MemoryManager] = None


async def get_memory_manager() -> MemoryManager:
    """Get the global memory manager instance."""
    global _memory_manager
    
    if _memory_manager is None:
        # Load settings and create config
        from ..config.settings import get_settings
        settings = get_settings()
        
        config = MemoryConfig(
            embedding_provider=settings.memory.embedding_provider,
            embedding_model=settings.memory.embedding_model,
            openai_api_key=settings.memory.openai_api_key,
            ollama_base_url=settings.memory.ollama_base_url,
            vector_db_path=settings.memory.vector_db_path
        )

        _memory_manager = MemoryManager(config)
        await _memory_manager.initialize()

    return _memory_manager


async def create_memory_manager_service(
    session: AsyncSession,
    tenant_id: str
) -> MemoryManagerService:
    """Create a memory manager service for a tenant."""
    memory_manager = await get_memory_manager()
    return MemoryManagerService(session, tenant_id, memory_manager)
