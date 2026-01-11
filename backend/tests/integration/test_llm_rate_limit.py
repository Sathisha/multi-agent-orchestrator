
import pytest
import asyncio
import time
from unittest.mock import MagicMock, patch
from shared.services.llm_service import LLMService, GlobalRateLimiter
from shared.models.agent import AgentConfig


from shared.config.settings import settings

@pytest.mark.asyncio
async def test_global_rate_limiter_logic():
    """Verify GlobalRateLimiter logic independent of LLM calls."""
    
    # Configure settings for test
    # 5 calls per 1 second period (mocking period via class attrib if possible or just assuming logic holds)
    # Since we can't easily change _period_seconds without invasive mock, let's keep it 60s but set MAX calls to 2 to fail fast?
    # Or stick with the plan of mocking period.
    
    GlobalRateLimiter._timestamps = []
    GlobalRateLimiter._period_seconds = 1
    
    # IMPORTANT: We need to patch the settings object that the module imports, 
    # OR since 'settings' is imported in llm_service.py, we might need to patch it there.
    # But settings is a singleton instance. We can modify it directly.
    original_limit = settings.llm.rate_limit_per_minute
    settings.llm.rate_limit_per_minute = 5
    
    try:
        # Consuming 5 slots should be instant
        start = time.time()
        for _ in range(5):
            await GlobalRateLimiter.acquire()
        duration = time.time() - start
        assert duration < 0.1, "First 5 calls should be instant"
        
        # 6th slot should wait
        start = time.time()
        await GlobalRateLimiter.acquire()
        duration = time.time() - start
        
        assert duration >= 0.9, f"6th call should wait for the window to clear. Took {duration}s"
    finally:
        settings.llm.rate_limit_per_minute = original_limit

@pytest.mark.asyncio
async def test_llm_service_rate_integration():
    """Verify LLMService uses the limiter."""
    
    # Mock provider to avoid real calls
    service = LLMService()
    service.provider_factory.get_or_create_provider = MagicMock()
    mock_provider = MagicMock()
    mock_provider.generate_response =  asyncio.coroutine(lambda *args: type('obj', (object,), {'usage': type('obj', (object,), {'total_tokens': 10})(), 'content': 'mock', 'model': 'mock'})())
    service.provider_factory.get_or_create_provider.return_value = asyncio.Future()
    service.provider_factory.get_or_create_provider.return_value.set_result(mock_provider)
    
    # Reset limiter
    GlobalRateLimiter._timestamps = []
    GlobalRateLimiter._period_seconds = 1 
    
    original_limit = settings.llm.rate_limit_per_minute
    settings.llm.rate_limit_per_minute = 5
    
    agent_config = AgentConfig(
        name="test",
        model="test-model",
        llm_provider="ollama"
    )
    
    try:
        # 5 fast calls
        for i in range(5):
            await service.generate_response([{"role": "user", "content": "hi"}], agent_config)
        
        # 6th call verify wait
        start = time.time()
        await service.generate_response([{"role": "user", "content": "hi"}], agent_config)
        duration = time.time() - start
        
        assert duration >= 0.9, "LLMService should enforce rate limit delay"
    finally:
        settings.llm.rate_limit_per_minute = original_limit
