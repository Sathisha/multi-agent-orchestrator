"""Test script for Agent Executor Service."""

import asyncio
import json
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from shared.services.agent_executor import AgentExecutorService, ExecutionStatus
from shared.services.agent_state_manager import AgentStateManager, AgentState
from shared.services.agent_error_handler import AgentErrorHandler, ErrorSeverity
from shared.models.agent import Agent, AgentStatus, AgentType
from shared.config.settings import get_settings

settings = get_settings()


async def test_agent_executor():
    """Test the agent executor service."""
    print("Testing Agent Executor Service...")
    
    # Create database connection
    engine = create_async_engine(settings.database.async_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        tenant_id = "test-tenant-123"
        
        # Create a test agent
        test_agent = Agent(
            id="test-agent-123",
            tenant_id=tenant_id,
            name="Test Agent",
            description="Test agent for executor testing",
            type=AgentType.CONVERSATIONAL,
            status=AgentStatus.ACTIVE,
            config={
                "llm_provider": "ollama",
                "model_name": "llama2",
                "temperature": 0.7,
                "max_tokens": 100,
                "memory_enabled": True,
                "guardrails_enabled": True
            },
            system_prompt="You are a helpful test assistant.",
            created_by="test-user"
        )
        
        session.add(test_agent)
        await session.commit()
        
        # Test Agent Executor Service
        print("\n1. Testing Agent Executor Service")
        executor = AgentExecutorService(session, tenant_id)
        
        try:
            # Start execution
            execution_id = await executor.start_agent_execution(
                agent_id="test-agent-123",
                input_data={"message": "Hello, this is a test!"},
                session_id="test-session-123",
                timeout_seconds=60
            )
            print(f"✓ Started execution: {execution_id}")
            
            # Check status
            status = await executor.get_execution_status(execution_id)
            print(f"✓ Execution status: {status['status']}")
            
            # List active executions
            active = await executor.list_active_executions()
            print(f"✓ Active executions: {len(active)}")
            
            # Wait a bit for execution to complete or timeout
            await asyncio.sleep(5)
            
            # Check final status
            final_status = await executor.get_execution_status(execution_id)
            print(f"✓ Final status: {final_status['status']}")
            
        except Exception as e:
            print(f"✗ Executor test failed: {str(e)}")
        
        # Test Agent State Manager
        print("\n2. Testing Agent State Manager")
        state_manager = AgentStateManager(session, tenant_id)
        
        try:
            # Initialize agent state
            runtime_info = await state_manager.initialize_agent_state("test-agent-123")
            print(f"✓ Initialized state: {runtime_info.state}")
            
            # Update state
            await state_manager.update_agent_state(
                "test-agent-123",
                AgentState.RUNNING,
                execution_id=execution_id
            )
            print("✓ Updated agent state to RUNNING")
            
            # Get health status
            health = await state_manager.get_agent_health_status("test-agent-123")
            print(f"✓ Health status: {health['status']}")
            
            # Get tenant statistics
            stats = await state_manager.get_tenant_statistics()
            print(f"✓ Tenant stats: {stats['total_agents']} agents")
            
        except Exception as e:
            print(f"✗ State manager test failed: {str(e)}")
        
        # Test Error Handler
        print("\n3. Testing Agent Error Handler")
        error_handler = AgentErrorHandler(session, tenant_id)
        
        try:
            # Simulate an error
            test_error = ValueError("Test error for demonstration")
            
            agent_error = await error_handler.handle_error(
                agent_id="test-agent-123",
                error=test_error,
                execution_id=execution_id,
                context={"test": True}
            )
            print(f"✓ Handled error: {agent_error.error_id}")
            
            # Get error history
            history = await error_handler.get_agent_error_history("test-agent-123")
            print(f"✓ Error history: {len(history)} errors")
            
            # Get error statistics
            error_stats = await error_handler.get_error_statistics("test-agent-123")
            print(f"✓ Error stats: {error_stats['total_errors']} total errors")
            
        except Exception as e:
            print(f"✗ Error handler test failed: {str(e)}")
        
        # Cleanup
        print("\n4. Cleanup")
        try:
            await session.delete(test_agent)
            await session.commit()
            print("✓ Cleaned up test data")
        except Exception as e:
            print(f"✗ Cleanup failed: {str(e)}")
    
    await engine.dispose()
    print("\n✓ Agent Executor Service tests completed!")


async def test_api_endpoints():
    """Test the API endpoints."""
    import httpx
    
    print("\nTesting Agent Executor API endpoints...")
    
    base_url = "http://localhost:8000"
    headers = {"X-Tenant-ID": "test-tenant-123"}
    
    async with httpx.AsyncClient() as client:
        try:
            # Test health endpoint
            response = await client.get(f"{base_url}/api/v1/agent-executor/health")
            if response.status_code == 200:
                print("✓ Health endpoint working")
            else:
                print(f"✗ Health endpoint failed: {response.status_code}")
            
            # Test system status (if available)
            try:
                response = await client.get(f"{base_url}/api/v1/agent-executor/system/status")
                if response.status_code == 200:
                    status = response.json()
                    print(f"✓ System status: {status['total_active_executions']} active executions")
                else:
                    print(f"✗ System status failed: {response.status_code}")
            except Exception as e:
                print(f"✗ System status error: {str(e)}")
                
        except Exception as e:
            print(f"✗ API test failed: {str(e)}")


if __name__ == "__main__":
    print("Agent Executor Service Test Suite")
    print("=" * 50)
    
    # Run the tests
    asyncio.run(test_agent_executor())
    
    # Test API endpoints (requires running server)
    try:
        asyncio.run(test_api_endpoints())
    except Exception as e:
        print(f"API tests skipped (server not running): {str(e)}")
    
    print("\nTest suite completed!")