from typing import Dict, Any, List, Optional, AsyncGenerator
from .base import BaseLLMProvider, LLMRequest, LLMResponse, LLMUsage, LLMProviderConfig, LLMProviderType

class MockConfig(LLMProviderConfig):
    """Configuration for Mock provider."""
    provider_type: LLMProviderType = LLMProviderType.MOCK

class MockProvider(BaseLLMProvider):
    """Mock LLM provider for testing."""
    
    async def initialize(self) -> None:
        pass
        
    async def validate_credentials(self) -> bool:
        return True
        
    async def get_available_models(self) -> List[str]:
        return ["mock-model-v1"]
        
    async def generate_response(self, request: LLMRequest) -> LLMResponse:
        content = "Mock response"
        
        # Simple logic to help with testing
        last_msg = request.messages[-1].content if request.messages else ""
        
        # Check for JSON instruction injection
        if "valid JSON format matching this schema" in last_msg or "IMPORTANT" in last_msg:
             content = '{"status": "mock_json", "data": "test"}'
             
        return LLMResponse(
            content=content,
            model="mock-model",
            usage=LLMUsage(total_tokens=10),
            finish_reason="stop",
            response_time_ms=10,
            provider="mock"
        )
        
    async def stream_response(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        yield "Mock "
        yield "response"

    async def health_check(self) -> Dict[str, Any]:
        return {"status": "healthy"}
