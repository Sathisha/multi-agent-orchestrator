"""
Property-based tests for Memory Management System

Tests the correctness properties related to memory storage, retrieval,
and management as specified in the design document.
"""

import asyncio
import os
import pytest
from datetime import datetime, timedelta
from typing import List, Dict, Any
from hypothesis import given, strategies as st, assume, settings
from hypothesis.strategies import composite

from shared.services.memory_manager import (
    MemoryManager, MemoryManagerService, MemoryType, MemoryConfig,
    create_memory_manager_service
)
from shared.database.connection import get_database_session
from shared.services.id_generator import IDGeneratorService


# Test data generators
@composite
def memory_content_strategy(draw):
    """Generate realistic memory content."""
    content_types = [
        st.text(min_size=10, max_size=500),  # General text
        st.from_regex(r"User: .{10,100} Assistant: .{10,100}"),  # Conversation
        st.from_regex(r"User prefers .{5,50}"),  # Preferences
        st.from_regex(r"User's name is \w+ and .{10,100}"),  # Facts
        st.from_regex(r"User learned .{10,100}"),  # Skills
    ]
    return draw(st.one_of(content_types))


@composite
def memory_metadata_strategy(draw):
    """Generate memory metadata."""
    return draw(st.dictionaries(
        st.text(min_size=1, max_size=20),
        st.one_of(
            st.text(min_size=1, max_size=50),
            st.integers(min_value=0, max_value=1000),
            st.booleans(),
            st.floats(min_value=0.0, max_value=1.0)
        ),
        min_size=0,
        max_size=5
    ))


@composite
def agent_memory_strategy(draw):
    """Generate complete agent memory data."""
    return {
        "content": draw(memory_content_strategy()),
        "memory_type": draw(st.sampled_from(list(MemoryType))),
        "metadata": draw(memory_metadata_strategy()),
        "importance_score": draw(st.floats(min_value=0.0, max_value=1.0)),
        "session_id": draw(st.one_of(st.none(), st.text(min_size=5, max_size=50)))
    }


class TestMemoryManagementProperties:
    """Property-based tests for memory management system."""
    
    @pytest.fixture(scope="class")
    async def memory_manager(self):
        """Create a memory manager for testing."""
        config = MemoryConfig(
            max_memories_per_agent=1000,
            similarity_threshold=0.5,
            embedding_model="all-MiniLM-L6-v2"
        )
        manager = MemoryManager(config)
        await manager.initialize()
        return manager
    
    @pytest.fixture
    async def memory_service(self, memory_manager):
        """Create a memory service for testing."""
        tenant_id = f"test-tenant-{IDGeneratorService.generate_short_id()}"
        async with get_database_session() as session:
            yield MemoryManagerService(session, tenant_id, memory_manager)
    
    @given(memory_data=agent_memory_strategy())
    @settings(max_examples=50, deadline=30000)  # 30 second deadline for embedding operations
    async def test_memory_storage_and_retrieval_round_trip(self, memory_service, memory_data):
        """
        **Feature: ai-agent-framework, Property 11: Memory Storage and Retrieval**
        **Validates: Requirements 8.1, 8.2**
        
        Property: For any information processing by agents, relevant data should be 
        stored in memory and retrievable through semantic search with proper efficiency.
        """
        assume(len(memory_data["content"].strip()) > 5)  # Ensure meaningful content
        
        agent_id = f"test-agent-{IDGeneratorService.generate_short_id()}"
        
        # Store the memory
        memory_id = await memory_service.store_memory(
            agent_id=agent_id,
            content=memory_data["content"],
            memory_type=memory_data["memory_type"],
            session_id=memory_data["session_id"],
            metadata=memory_data["metadata"],
            importance_score=memory_data["importance_score"]
        )
        
        # Verify memory was stored
        assert memory_id is not None
        assert memory_id.startswith("mem-")
        
        # Retrieve through semantic search using the exact content
        search_results = await memory_service.semantic_search(
            agent_id=agent_id,
            query=memory_data["content"],
            limit=10
        )
        
        # The stored memory should be found with high similarity
        assert len(search_results) > 0
        
        # Find our stored memory in the results
        stored_memory = None
        for result in search_results:
            if result.memory_id == memory_id:
                stored_memory = result
                break
        
        assert stored_memory is not None, "Stored memory should be retrievable"
        assert stored_memory.content == memory_data["content"]
        assert stored_memory.memory_type == memory_data["memory_type"].value
        assert stored_memory.similarity_score > 0.9  # Should be very similar to itself
    
    @given(
        memories=st.lists(agent_memory_strategy(), min_size=2, max_size=10),
        query=st.text(min_size=5, max_size=100)
    )
    @settings(max_examples=20, deadline=60000)  # Longer deadline for multiple embeddings
    async def test_semantic_search_ranking(self, memory_service, memories, query):
        """
        **Feature: ai-agent-framework, Property 11: Memory Storage and Retrieval**
        **Validates: Requirements 8.1, 8.2**
        
        Property: Semantic search should return results ranked by relevance,
        with more similar content appearing first.
        """
        agent_id = f"test-agent-{IDGeneratorService.generate_short_id()}"
        
        # Store all memories
        memory_ids = []
        for memory_data in memories:
            assume(len(memory_data["content"].strip()) > 5)
            
            memory_id = await memory_service.store_memory(
                agent_id=agent_id,
                content=memory_data["content"],
                memory_type=memory_data["memory_type"],
                metadata=memory_data["metadata"],
                importance_score=memory_data["importance_score"]
            )
            memory_ids.append(memory_id)
        
        # Perform semantic search
        results = await memory_service.semantic_search(
            agent_id=agent_id,
            query=query,
            limit=len(memories)
        )
        
        # Verify results are ranked by similarity (descending)
        if len(results) > 1:
            for i in range(len(results) - 1):
                combined_score_current = results[i].similarity_score * (results[i].importance_score + 0.1)
                combined_score_next = results[i + 1].similarity_score * (results[i + 1].importance_score + 0.1)
                assert combined_score_current >= combined_score_next, \
                    "Results should be ranked by combined similarity and importance score"
    
    @given(
        conversation_messages=st.lists(
            st.text(min_size=10, max_size=200), 
            min_size=3, 
            max_size=20
        )
    )
    @settings(max_examples=20, deadline=60000)
    async def test_conversation_continuity(self, memory_service, conversation_messages):
        """
        **Feature: ai-agent-framework, Property 13: Conversation Continuity**
        **Validates: Requirements 8.4**
        
        Property: For any user interaction with agents, conversation history and 
        preferences should be maintained and accessible across sessions.
        """
        agent_id = f"test-agent-{IDGeneratorService.generate_short_id()}"
        session_id = f"session-{IDGeneratorService.generate_short_id()}"
        
        # Store conversation messages
        stored_ids = []
        for i, message in enumerate(conversation_messages):
            memory_id = await memory_service.store_memory(
                agent_id=agent_id,
                content=message,
                memory_type=MemoryType.CONVERSATION,
                session_id=session_id,
                metadata={"turn": i + 1}
            )
            stored_ids.append(memory_id)
        
        # Retrieve conversation history
        history = await memory_service.get_conversation_history(
            agent_id=agent_id,
            session_id=session_id
        )
        
        # Verify all messages are present and in correct order
        assert len(history) == len(conversation_messages)
        
        # Messages should be in chronological order
        for i, result in enumerate(history):
            assert result.content == conversation_messages[i]
            assert result.memory_type == MemoryType.CONVERSATION.value
            assert result.metadata.get("turn") == i + 1
    
    @given(
        memories=st.lists(agent_memory_strategy(), min_size=5, max_size=15),
        capacity_limit=st.integers(min_value=3, max_value=8)
    )
    @settings(max_examples=15, deadline=60000)
    async def test_memory_management_intelligence(self, memory_service, memories, capacity_limit):
        """
        **Feature: ai-agent-framework, Property 12: Memory Management Intelligence**
        **Validates: Requirements 8.3**
        
        Property: For any agent reaching memory capacity, the system should retain 
        important memories and remove less important ones based on defined criteria.
        """
        agent_id = f"test-agent-{IDGeneratorService.generate_short_id()}"
        
        # Override capacity limit for this test
        memory_service.memory_manager.config.max_memories_per_agent = capacity_limit
        
        # Store memories with varying importance scores
        memory_ids = []
        importance_scores = []
        
        for memory_data in memories:
            assume(len(memory_data["content"].strip()) > 5)
            
            memory_id = await memory_service.store_memory(
                agent_id=agent_id,
                content=memory_data["content"],
                memory_type=memory_data["memory_type"],
                importance_score=memory_data["importance_score"]
            )
            memory_ids.append(memory_id)
            importance_scores.append(memory_data["importance_score"])
        
        # If we stored more than the limit, trigger capacity management
        if len(memories) > capacity_limit:
            removed_count = await memory_service.manage_memory_capacity(agent_id)
            
            # Verify some memories were removed
            assert removed_count > 0
            
            # Get remaining memories
            remaining_memories = await memory_service.semantic_search(
                agent_id=agent_id,
                query="test",  # Generic query to get all memories
                limit=100
            )
            
            # Should have fewer memories now
            assert len(remaining_memories) <= capacity_limit
            
            # Remaining memories should generally have higher importance scores
            if len(remaining_memories) > 1:
                avg_remaining_importance = sum(m.importance_score for m in remaining_memories) / len(remaining_memories)
                avg_original_importance = sum(importance_scores) / len(importance_scores)
                
                # The average importance of remaining memories should be higher than or equal to original average
                # (allowing for some tolerance due to other factors like access count)
                assert avg_remaining_importance >= avg_original_importance - 0.2
    
    @given(
        preferences=st.lists(
            st.text(min_size=10, max_size=100),
            min_size=2,
            max_size=8
        )
    )
    @settings(max_examples=15, deadline=45000)
    async def test_user_preference_tracking(self, memory_service, preferences):
        """
        **Feature: ai-agent-framework, Property 13: Conversation Continuity**
        **Validates: Requirements 8.4**
        
        Property: User preferences should be stored with high importance and 
        be easily retrievable for personalization.
        """
        agent_id = f"test-agent-{IDGeneratorService.generate_short_id()}"
        user_id = f"user-{IDGeneratorService.generate_short_id()}"
        
        # Store preferences with high importance
        preference_ids = []
        for pref in preferences:
            memory_id = await memory_service.store_memory(
                agent_id=agent_id,
                content=f"User prefers {pref}",
                memory_type=MemoryType.PREFERENCE,
                importance_score=0.8,  # High importance for preferences
                created_by=user_id
            )
            preference_ids.append(memory_id)
        
        # Retrieve user preferences
        retrieved_prefs = await memory_service.get_user_preferences(
            agent_id=agent_id,
            user_id=user_id
        )
        
        # All preferences should be retrieved
        assert len(retrieved_prefs) == len(preferences)
        
        # All should be preference type with high importance
        for pref_result in retrieved_prefs:
            assert pref_result.memory_type == MemoryType.PREFERENCE.value
            assert pref_result.importance_score >= 0.7  # Should maintain high importance
    
    @given(
        memory_data=agent_memory_strategy(),
        expiry_minutes=st.integers(min_value=-10, max_value=10)
    )
    @settings(max_examples=20, deadline=30000)
    async def test_memory_persistence_across_restarts(self, memory_service, memory_data, expiry_minutes):
        """
        **Feature: ai-agent-framework, Property 3: Data Persistence Round-Trip**
        **Validates: Requirements 1.4, 8.5**
        
        Property: For any valid data (memory data), storing and then retrieving 
        should produce equivalent data that survives system restarts.
        """
        assume(len(memory_data["content"].strip()) > 5)
        
        agent_id = f"test-agent-{IDGeneratorService.generate_short_id()}"
        
        # Set expiration time
        expires_at = None
        if expiry_minutes != 0:
            expires_at = datetime.utcnow() + timedelta(minutes=expiry_minutes)
        
        # Store memory
        memory_id = await memory_service.store_memory(
            agent_id=agent_id,
            content=memory_data["content"],
            memory_type=memory_data["memory_type"],
            metadata=memory_data["metadata"],
            importance_score=memory_data["importance_score"],
            expires_at=expires_at
        )
        
        # Simulate system restart by creating new memory service instance
        new_memory_service = MemoryManagerService(
            memory_service.session,
            memory_service.tenant_id,
            memory_service.memory_manager
        )
        
        # Try to retrieve the memory
        if expiry_minutes <= 0:
            # Memory should be expired or expiring soon, might not be retrievable
            results = await new_memory_service.semantic_search(
                agent_id=agent_id,
                query=memory_data["content"],
                limit=10
            )
            # Don't assert anything for expired memories
        else:
            # Memory should still be accessible
            results = await new_memory_service.semantic_search(
                agent_id=agent_id,
                query=memory_data["content"],
                limit=10
            )
            
            # Should find the memory
            found_memory = None
            for result in results:
                if result.memory_id == memory_id:
                    found_memory = result
                    break
            
            assert found_memory is not None, "Memory should persist across system restarts"
            assert found_memory.content == memory_data["content"]
            assert found_memory.memory_type == memory_data["memory_type"].value


# Run the tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])