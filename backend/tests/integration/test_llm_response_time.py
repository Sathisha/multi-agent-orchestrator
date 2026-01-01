"Integration tests for LLM response time measurement within agent execution."

import pytest
import asyncio
from unittest.mock import AsyncMock, patch
import time
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from backend.shared.database.connection import AsyncSessionLocal
from backend.shared.models.agent import Agent, AgentStatus
from backend.shared.services.agent_executor import AgentExecutorService
from backend.shared.services.llm_service import LLMService
from backend.shared.services.llm_providers import LLMProviderType, LLMResponse, LLMUsage, LLMMessage, LLMRequest

# Fixture for an async session
@pytest.fixture
async def db_session():
    async with AsyncSessionLocal() as session:
        yield session
        await session.rollback() # Ensure cleanup for tests

# Fixture for a dummy agent
@pytest.fixture
async def dummy_agent(db_session: AsyncSession):
    agent = Agent(
        id="test-agent-id",
        name="Test Agent",
        description="A test agent for LLM response time measurement",
        system_prompt="You are a helpful assistant.",
        status=AgentStatus.ACTIVE,
        config={"llm_provider": LLMProviderType.OLLAMA.value, "model_name": "llama3"}
    )
    db_session.add(agent)
    await db_session.commit()
    return agent

# We need to mock LLMService.generate_response as it's called by AgentExecutorService
@patch('backend.shared.services.llm_service.LLMService.generate_response')
@pytest.mark.asyncio
async def test_llm_response_time_measurement(
    mock_generate_response: AsyncMock,
    db_session: AsyncSession,
    dummy_agent: Agent
):
    # Simulate a delay in the LLM response
    simulated_delay_seconds = 2.0
    
    async def mock_response_with_delay(*args, **kwargs):
        # Ensure we are checking the actual request passed
        llm_request: LLMRequest = args[0] # The first arg to generate_response is LLMRequest
        assert isinstance(llm_request, LLMRequest)
        assert llm_request.model == "llama3"
        assert any(msg.content == "What is the capital of France?" for msg in llm_request.messages)

        await asyncio.sleep(simulated_delay_seconds)
        return LLMResponse(
            content="Mock LLM response", 
            usage=LLMUsage(prompt_tokens=10, completion_tokens=40, total_tokens=50),
            model="llama3",
            provider=LLMProviderType.OLLAMA
        )

    mock_generate_response.side_effect = mock_response_with_delay

    executor_service = AgentExecutorService(session=db_session)

    input_data = {"prompt": "What is the capital of France?"}
    
    # Store time before starting execution
    start_execution_time = time.time()
    
    execution_id = await executor_service.start_agent_execution(
        agent_id=dummy_agent.id,
        input_data=input_data,
        created_by="test_user"
    )

    # Wait for the background task to complete and update the execution record
    max_wait_time = simulated_delay_seconds + 5 # Give it some buffer for async scheduling and DB ops
    current_wait_time = 0
    polling_interval = 0.1 # Check every 100ms
    execution_record = None
    
    while current_wait_time < max_wait_time:
        execution_record = await executor_service.get_by_id(execution_id)
        if execution_record and execution_record.status == 'completed':
            break
        await asyncio.sleep(polling_interval)
        current_wait_time += polling_interval
    
    # Assert that the execution completed successfully
    assert execution_record is not None
    assert execution_record.status == 'completed'
    assert execution_record.output_data['content'] == "Mock LLM response"
    
    # Assert LLM response time (which is effectively the total execution time in this isolated test)
    # The `execution_time_ms` in the record reflects the total time spent in _execute_agent_logic,
    # which in this mocked scenario is dominated by the simulated LLM delay.
    
    # Allowing a margin for overhead from task scheduling, database operations, etc.
    min_expected_ms = int(simulated_delay_seconds * 1000 * 0.95) # At least 95% of simulated delay
    max_expected_ms = int(simulated_delay_seconds * 1000 * 1.50) # Up to 150% of simulated delay
    
    assert min_expected_ms <= execution_record.execution_time_ms <= max_expected_ms, \
        f"Expected execution time between {min_expected_ms}ms and {max_expected_ms}ms, got {execution_record.execution_time_ms}ms"
    
    # Verify that generate_response was called exactly once with correct arguments
    mock_generate_response.assert_called_once()
    call_args, call_kwargs = mock_generate_response.call_args
    
    # The first argument is an LLMRequest object
    llm_request_arg: LLMRequest = call_args[0] 
    assert isinstance(llm_request_arg, LLMRequest)
    assert llm_request_arg.model == "llama3"
    assert any(msg.content == "What is the capital of France?" for msg in llm_request_arg.messages)
    assert llm_request_arg.stream is False
    # The second argument is AgentConfig
    agent_config_arg = call_args[1]
    assert agent_config_arg.model_name == "llama3"
    assert agent_config_arg.llm_provider == LLMProviderType.OLLAMA

    print(f"LLM response time test completed. Measured: {execution_record.execution_time_ms}ms, Simulated: {simulated_delay_seconds*1000}ms")
