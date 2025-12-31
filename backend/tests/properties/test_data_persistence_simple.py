"""
Simple property-based tests for data persistence round-trip validation.

**Feature: ai-agent-framework, Property 3: Data Persistence Round-Trip**
**Validates: Requirements 1.4, 8.5**

This is a simplified version to test the basic approach before implementing the full test suite.
"""

import sys
import os
# Add the app directory to Python path so we can import shared modules
sys.path.insert(0, '/app')

import pytest
import asyncio
import uuid
from uuid import UUID
from datetime import datetime
from typing import Dict, Any

# Test if basic imports work
def test_basic_imports():
    """Test that all required imports work correctly."""
    try:
        from shared.database import get_database_session
        print("✅ Database import OK")
    except ImportError as e:
        pytest.fail(f"Database import failed: {e}")
    
    try:
        from shared.models.agent import Agent, AgentConfig, AgentType, LLMProvider
        print("✅ Agent models import OK")
    except ImportError as e:
        pytest.fail(f"Agent models import failed: {e}")
    
    try:
        from shared.services.agent import AgentService
        print("✅ Agent service import OK")
    except ImportError as e:
        pytest.fail(f"Agent service import failed: {e}")


@pytest.mark.asyncio
async def test_simple_agent_persistence():
    """
    Simple test to verify agent data can be stored and retrieved.
    This tests the basic persistence functionality without property-based testing.
    """
    try:
        from shared.database import get_database_session
        from shared.models.agent import AgentConfig, AgentType, LLMProvider
        from shared.models.tenant import Tenant, TenantStatus, TenantPlan
        from shared.services.agent import AgentService
        from shared.services.tenant import TenantService
    except ImportError as e:
        pytest.skip(f"Required imports not available: {e}")
    
    test_tenant_id = UUID("550e8400-e29b-41d4-a716-446655440000")  # Valid UUID format
    test_user_id = UUID("550e8400-e29b-41d4-a716-446655440001")    # Valid UUID format
    
    # Simple test data with unique name
    unique_suffix = str(uuid.uuid4())[:8]
    agent_data = {
        "name": f"Test Agent Simple {unique_suffix}",
        "description": "A simple test agent for persistence testing",
        "type": AgentType.CHATBOT,
        "config": {
            "temperature": 0.7,
            "max_tokens": 2000,
            "model": "llama2"
        },
        "tags": ["test", "simple"]
    }
    
    async with get_database_session() as session:
        # First, create a test tenant
        tenant_service = TenantService(session)
        
        # Check if tenant already exists, if not create it
        existing_tenant = await tenant_service.get_tenant_by_id(test_tenant_id)
        if not existing_tenant:
            test_tenant = await tenant_service.create_tenant(
                name="Test Tenant",
                slug="test-tenant-simple",
                display_name="Test Tenant for Simple Tests",
                primary_email="test@example.com",
                plan=TenantPlan.FREE
            )
            # Update the tenant ID to match our test ID
            test_tenant.id = test_tenant_id
            await session.commit()
        
        # Now test agent persistence
        agent_service = AgentService(session, test_tenant_id)
        
        created_agent = None
        try:
            # Store the agent data
            created_agent = await agent_service.create_agent(
                name=agent_data["name"],
                description=agent_data["description"],
                agent_type=agent_data["type"],
                config=agent_data["config"],
                system_prompt="You are a helpful assistant.",
                tags=agent_data["tags"],
                created_by=test_user_id
            )
            
            assert created_agent is not None, "Agent should be created successfully"
            assert created_agent.id is not None, "Created agent should have an ID"
            
            # Retrieve the agent data
            retrieved_agent = await agent_service.get_by_id(created_agent.id)
            
            assert retrieved_agent is not None, "Agent should be retrievable after creation"
            
            # Verify basic data integrity
            assert retrieved_agent.name == agent_data["name"], "Agent name should be preserved"
            assert retrieved_agent.description == agent_data["description"], "Agent description should be preserved"
            assert retrieved_agent.type == agent_data["type"], "Agent type should be preserved"
            assert retrieved_agent.tenant_id == test_tenant_id, "Tenant ID should be preserved"
            assert retrieved_agent.created_by == test_user_id, "Creator ID should be preserved"
            
            # Verify configuration data integrity
            config = retrieved_agent.config
            original_config = agent_data["config"]
            
            assert config["temperature"] == original_config["temperature"], "Temperature should be preserved"
            assert config["max_tokens"] == original_config["max_tokens"], "Max tokens should be preserved"
            assert config["model"] == original_config["model"], "Model should be preserved"
            
            print("✅ Simple agent persistence test passed")
            
        finally:
            # Cleanup: Delete the test agent
            if created_agent:
                try:
                    await agent_service.delete(created_agent.id)
                    print("✅ Test cleanup completed")
                except Exception as cleanup_error:
                    print(f"⚠️ Cleanup failed: {cleanup_error}")


if __name__ == "__main__":
    # Run the test directly
    asyncio.run(test_simple_agent_persistence())