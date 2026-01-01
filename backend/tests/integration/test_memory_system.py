#!/usr/bin/env python3
"""
Test script for Memory Management System

This script tests the core functionality of the memory management system:
- Memory storage and retrieval
- Semantic search capabilities
- Conversation history management
- User preference tracking
- Memory capacity management
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta
from typing import List

# Add the backend directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from shared.services.memory_manager import (
    MemoryManager, MemoryManagerService, MemoryType, MemoryConfig,
    create_memory_manager_service
)
from shared.database.connection import get_database_session
from shared.services.id_generator import IDGeneratorService


async def test_memory_system():
    """Test the memory management system functionality."""
    
    print("🧠 Testing AI Agent Framework Memory Management System")
    print("=" * 60)
    
    # Initialize memory manager
    config = MemoryConfig(
        max_memories_per_agent=100,
        similarity_threshold=0.6,
        embedding_model="all-MiniLM-L6-v2"
    )
    
    memory_manager = MemoryManager(config)
    await memory_manager.initialize()
    
    print("✅ Memory manager initialized successfully")
    
    # Test data
    agent_id = "test-agent-001"
    session_id = "test-session-001"
    user_id = "test-user-001"
    
    # Create a mock database session (in real usage, this comes from FastAPI dependency)
    async with get_database_session() as session:
        memory_service = MemoryManagerService(session, memory_manager)
        
        print("\n📝 Testing memory storage...")
        
        # Test 1: Store different types of memories
        test_memories = [
            {
                "content": "User prefers coffee over tea in the morning",
                "memory_type": MemoryType.PREFERENCE,
                "metadata": {"category": "beverage", "time": "morning"}
            },
            {
                "content": "The user's name is Alice and she works as a software engineer",
                "memory_type": MemoryType.FACT,
                "metadata": {"category": "personal_info"}
            },
            {
                "content": "User: Hello, how are you today? Assistant: I'm doing well, thank you for asking!",
                "memory_type": MemoryType.CONVERSATION,
                "session_id": session_id,
                "metadata": {"turn": 1}
            },
            {
                "content": "User asked about Python programming best practices",
                "memory_type": MemoryType.CONVERSATION,
                "session_id": session_id,
                "metadata": {"turn": 2, "topic": "programming"}
            },
            {
                "content": "User learned how to use async/await in Python",
                "memory_type": MemoryType.SKILL,
                "metadata": {"skill_level": "beginner", "topic": "python"}
            }
        ]
        
        stored_memory_ids = []
        
        for i, memory_data in enumerate(test_memories):
            try:
                memory_id = await memory_service.store_memory(
                    agent_id=agent_id,
                    content=memory_data["content"],
                    memory_type=memory_data["memory_type"],
                    session_id=memory_data.get("session_id"),
                    metadata=memory_data["metadata"],
                    created_by=user_id
                )
                stored_memory_ids.append(memory_id)
                print(f"  ✅ Stored memory {i+1}: {memory_id}")
                
            except Exception as e:
                print(f"  ❌ Failed to store memory {i+1}: {e}")
        
        print(f"\n📊 Stored {len(stored_memory_ids)} memories successfully")
        
        # Test 2: Semantic search
        print("\n🔍 Testing semantic search...")
        
        search_queries = [
            "What does the user like to drink?",
            "Tell me about Alice",
            "Python programming questions",
            "What skills has the user learned?"
        ]
        
        for query in search_queries:
            try:
                results = await memory_service.semantic_search(
                    agent_id=agent_id,
                    query=query,
                    limit=3
                )
                
                print(f"\n  Query: '{query}'")
                print(f"  Found {len(results)} results:")
                
                for j, result in enumerate(results):
                    print(f"    {j+1}. [{result.memory_type}] {result.content[:50]}...")
                    print(f"       Similarity: {result.similarity_score:.3f}, Importance: {result.importance_score:.3f}")
                
            except Exception as e:
                print(f"  ❌ Search failed for '{query}': {e}")
        
        # Test 3: Conversation history
        print("\n💬 Testing conversation history...")
        
        try:
            conversation = await memory_service.get_conversation_history(
                agent_id=agent_id,
                session_id=session_id
            )
            
            print(f"  Found {len(conversation)} conversation messages:")
            for i, msg in enumerate(conversation):
                print(f"    {i+1}. {msg.content[:60]}...")
                
        except Exception as e:
            print(f"  ❌ Failed to get conversation history: {e}")
        
        # Test 4: User preferences
        print("\n👤 Testing user preferences...")
        
        try:
            preferences = await memory_service.get_user_preferences(
                agent_id=agent_id,
                user_id=user_id
            )
            
            print(f"  Found {len(preferences)} preferences/facts:")
            for i, pref in enumerate(preferences):
                print(f"    {i+1}. [{pref.memory_type}] {pref.content[:50]}...")
                print(f"       Importance: {pref.importance_score:.3f}")
                
        except Exception as e:
            print(f"  ❌ Failed to get user preferences: {e}")
        
        # Test 5: Memory statistics
        print("\n📈 Testing memory statistics...")
        
        try:
            stats = await memory_service.get_statistics(agent_id=agent_id)
            
            print(f"  Total memories: {stats['total_memories']}")
            print(f"  Average importance: {stats['average_importance_score']:.3f}")
            print(f"  Memories by type: {stats['memories_by_type']}")
            print(f"  System stats: {stats['system_stats']}")
            
        except Exception as e:
            print(f"  ❌ Failed to get statistics: {e}")
        
        # Test 6: Memory capacity management
        print("\n🗂️ Testing memory capacity management...")
        
        try:
            # Add many low-importance memories to test capacity management
            for i in range(10):
                await memory_service.store_memory(
                    agent_id=agent_id,
                    content=f"Low importance test memory number {i}",
                    memory_type=MemoryType.CONVERSATION,
                    importance_score=0.1,
                    created_by=user_id
                )
            
            # Trigger capacity management
            removed_count = await memory_service.manage_memory_capacity(agent_id)
            print(f"  Removed {removed_count} low-importance memories")
            
        except Exception as e:
            print(f"  ❌ Failed to manage memory capacity: {e}")
        
        # Test 7: Cleanup expired memories
        print("\n🧹 Testing expired memory cleanup...")
        
        try:
            # Add an expired memory
            await memory_service.store_memory(
                agent_id=agent_id,
                content="This memory should expire immediately",
                memory_type=MemoryType.CONVERSATION,
                expires_at=datetime.utcnow() - timedelta(minutes=1),
                created_by=user_id
            )
            
            # Clean up expired memories
            cleaned_count = await memory_service.cleanup_expired_memories()
            print(f"  Cleaned up {cleaned_count} expired memories")
            
        except Exception as e:
            print(f"  ❌ Failed to cleanup expired memories: {e}")
        
        print("\n🎉 Memory management system tests completed!")
        print("=" * 60)


async def test_embedding_performance():
    """Test embedding generation performance."""
    
    print("\n⚡ Testing embedding performance...")
    
    config = MemoryConfig(embedding_model="all-MiniLM-L6-v2")
    memory_manager = MemoryManager(config)
    await memory_manager.initialize()
    
    test_texts = [
        "This is a short text for testing.",
        "This is a much longer text that contains more information and should take longer to process but we want to see how the embedding model handles it.",
        "Technical content about machine learning, artificial intelligence, neural networks, and deep learning algorithms.",
        "User preferences and personal information including names, locations, and behavioral patterns.",
        "Conversation history with multiple turns between user and assistant discussing various topics."
    ]
    
    import time
    
    for i, text in enumerate(test_texts):
        start_time = time.time()
        embedding = memory_manager._generate_embedding(text)
        end_time = time.time()
        
        print(f"  Text {i+1} ({len(text)} chars): {(end_time - start_time)*1000:.2f}ms, {len(embedding)} dimensions")
    
    print("✅ Embedding performance test completed")


if __name__ == "__main__":
    # Set up environment
    os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/ai_agent_framework")
    os.environ.setdefault("CHROMA_DB_PATH", "./data/chroma")
    
    # Run tests
    asyncio.run(test_memory_system())
    asyncio.run(test_embedding_performance())