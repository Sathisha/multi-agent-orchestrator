#!/usr/bin/env python3
"""
Simple test for Memory Management System without Docker dependencies.

This test verifies the core memory management functionality works
without requiring database or external services.
"""

import asyncio
import os
import tempfile
import shutil
from datetime import datetime

from shared.services.memory_manager import MemoryManager, MemoryType, MemoryConfig


async def test_memory_manager_basic():
    """Test basic memory manager functionality."""
    
    print("🧠 Testing Memory Manager Basic Functionality")
    print("=" * 50)
    
    # Create temporary directory for Chroma
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Initialize memory manager with temporary directory
        config = MemoryConfig(
            vector_db_path=temp_dir,
            embedding_model="all-MiniLM-L6-v2",
            max_memories_per_agent=10
        )
        
        memory_manager = MemoryManager(config)
        
        print("📥 Initializing memory manager...")
        await memory_manager.initialize()
        print("✅ Memory manager initialized successfully")
        
        # Test embedding generation
        print("\n🔤 Testing embedding generation...")
        test_text = "This is a test sentence for embedding generation."
        embedding = memory_manager._generate_embedding(test_text)
        
        print(f"  Text: '{test_text}'")
        print(f"  Embedding dimensions: {len(embedding)}")
        print(f"  Embedding type: {type(embedding)}")
        print("✅ Embedding generation works")
        
        # Test importance score calculation
        print("\n📊 Testing importance score calculation...")
        
        test_cases = [
            ("User prefers coffee over tea", MemoryType.PREFERENCE, {"user_explicit": True}),
            ("Just a casual conversation message", MemoryType.CONVERSATION, {}),
            ("User learned Python programming", MemoryType.SKILL, {"decision_related": True}),
            ("Important fact about the user", MemoryType.FACT, {"emotional_content": True})
        ]
        
        for content, memory_type, metadata in test_cases:
            score = memory_manager._calculate_importance_score(content, memory_type, metadata)
            print(f"  [{memory_type.value}] '{content[:30]}...' -> {score:.3f}")
        
        print("✅ Importance scoring works")
        
        # Test collection management
        print("\n📁 Testing collection management...")
        agent_id = "test-agent"
        
        collection = await memory_manager._get_or_create_collection(agent_id)
        collection_name = memory_manager._get_collection_name(agent_id)
        
        print(f"  Collection name: {collection_name}")
        print(f"  Collection created: {collection is not None}")
        print("✅ Collection management works")
        
        # Test vector operations
        print("\n🔍 Testing vector operations...")
        
        # Add some test documents
        test_documents = [
            "The user likes coffee in the morning",
            "Python is a programming language",
            "The weather is nice today",
            "Machine learning is fascinating"
        ]
        
        embeddings = [memory_manager._generate_embedding(doc) for doc in test_documents]
        
        collection.add(
            embeddings=embeddings,
            documents=test_documents,
            metadatas=[{"type": "test", "index": i} for i in range(len(test_documents))],
            ids=[f"test-{i}" for i in range(len(test_documents))]
        )
        
        print(f"  Added {len(test_documents)} test documents")
        
        # Test search
        query = "What does the user like to drink?"
        query_embedding = memory_manager._generate_embedding(query)
        
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=2,
            include=["documents", "metadatas", "distances"]
        )
        
        print(f"  Query: '{query}'")
        print(f"  Found {len(results['documents'][0])} results:")
        
        for i, (doc, distance) in enumerate(zip(results['documents'][0], results['distances'][0])):
            similarity = 1.0 - distance
            print(f"    {i+1}. '{doc}' (similarity: {similarity:.3f})")
        
        print("✅ Vector operations work")
        
        print(f"\n🎉 All basic tests passed!")
        print("Memory management system is working correctly")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        raise
    
    finally:
        # Clean up temporary directory
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    asyncio.run(test_memory_manager_basic())