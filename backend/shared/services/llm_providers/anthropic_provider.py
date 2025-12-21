"""Anthropic LLM provider implementation."""

import time
from typing import Dict, List, Optional, Any, AsyncGenerator
import anthropic
from anthropic import AsyncAnthropic

from .base import (
    BaseLLMProvider, 
    LLMProviderConfig, 
    LLMRequest, 
    LLMResponse, 
    LLMUsage,
    LLMMessage,
    LLMError,
    LLMAuthenticationError,
    LLMRateLimitError,
    LLMProviderType
)


class AnthropicConfig(LLMProviderConfig):
    """Anthropic-specific configuration."""
    
    max_tokens_per_minute: int = 100000
    requests_per_minute: int = 1000
    
    def __init__(self, **data):
        if "provider_type" not in data:
            data["provider_type"] = LLMProviderType.ANTHROPIC
        super().__init__(**data)


class AnthropicProvider(BaseLLMProvider):
    """Anthropic LLM provider implementation."""
    
    # Token pricing per 1M tokens (as of late 2023)
    TOKEN_PRICING = {
        "claude-3-opus": {"input": 15.0, "output": 75.0},
        "claude-3-sonnet": {"input": 3.0, "output": 15.0},
        "claude-3-haiku": {"input": 0.25, "output": 1.25},
        "claude-2.1": {"input": 8.0, "output": 24.0},
        "claude-2.0": {"input": 8.0, "output": 24.0},
        "claude-instant-1.2": {"input": 0.8, "output": 2.4},
    }
    
    def __init__(self, config: AnthropicConfig, credentials: Dict[str, Any]):
        super().__init__(config, credentials)
        self.config: AnthropicConfig = config
        
        # Extract credentials
        self.api_key = credentials.get("api_key")
        
        if not self.api_key:
            raise LLMError(
                message="Anthropic API key is required",
                provider=self.provider_type.value,
                error_code="MISSING_API_KEY"
            )
    
    async def initialize(self) -> None:
        """Initialize Anthropic provider."""
        try:
            # Initialize Anthropic client
            self._client = AsyncAnthropic(
                api_key=self.api_key,
                timeout=self.config.timeout
            )
            
            self.logger.info("Anthropic provider initialized successfully")
            
        except anthropic.AuthenticationError as e:
            raise LLMAuthenticationError(
                message="Invalid Anthropic API key",
                provider=self.provider_type.value,
                original_error=e
            )
        except Exception as e:
            raise self._handle_error(e, "Failed to initialize Anthropic provider")
    
    async def validate_credentials(self) -> bool:
        """Validate Anthropic credentials."""
        try:
            await self.ensure_initialized()
            # Make a minimal request to test credentials
            test_request = LLMRequest(
                messages=[LLMMessage(role="user", content="Hi")],
                model="claude-3-haiku-20240307",
                max_tokens=10
            )
            await self.generate_response(test_request)
            return True
        except Exception as e:
            self.logger.error(f"Anthropic credential validation failed: {e}")
            return False
    
    async def get_available_models(self) -> List[str]:
        """Get list of available Anthropic models."""
        # Anthropic doesn't have a models endpoint, so return known models
        return [
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307",
            "claude-2.1",
            "claude-2.0",
            "claude-instant-1.2"
        ]
    
    async def generate_response(self, request: LLMRequest) -> LLMResponse:
        """Generate response from Anthropic."""
        start_time = time.time()
        
        try:
            await self.ensure_initialized()
            
            # Convert messages to Anthropic format
            # Anthropic requires system message separate from conversation
            system_message = None
            anthropic_messages = []
            
            for msg in request.messages:
                if msg.role == "system":
                    system_message = msg.content
                else:
                    anthropic_messages.append({
                        "role": msg.role,
                        "content": msg.content
                    })
            
            # Prepare request parameters
            params = {
                "model": request.model,
                "messages": anthropic_messages,
                "max_tokens": request.max_tokens,
                "temperature": request.temperature,
                "stream": False
            }
            
            # Add system message if present
            if system_message:
                params["system"] = system_message
            
            # Make request
            response = await self._client.messages.create(**params)
            response_time_ms = int((time.time() - start_time) * 1000)
            
            # Extract response content
            content = ""
            if response.content and len(response.content) > 0:
                # Anthropic returns content as a list of content blocks
                for block in response.content:
                    if hasattr(block, "text"):
                        content += block.text
            
            # Calculate cost
            cost = self._calculate_cost(request.model, response.usage)
            
            # Create usage object
            usage = LLMUsage(
                prompt_tokens=response.usage.input_tokens if response.usage else 0,
                completion_tokens=response.usage.output_tokens if response.usage else 0,
                total_tokens=(response.usage.input_tokens + response.usage.output_tokens) if response.usage else 0,
                cost=cost
            )
            
            return LLMResponse(
                content=content,
                model=response.model,
                usage=usage,
                finish_reason=response.stop_reason or "stop",
                response_time_ms=response_time_ms,
                provider=self.provider_type.value,
                metadata={
                    "id": response.id,
                    "type": response.type,
                    "role": response.role
                }
            )
            
        except anthropic.AuthenticationError as e:
            raise LLMAuthenticationError(
                message="Anthropic authentication failed",
                provider=self.provider_type.value,
                original_error=e
            )
        except anthropic.RateLimitError as e:
            raise LLMRateLimitError(
                message="Anthropic rate limit exceeded",
                provider=self.provider_type.value,
                original_error=e
            )
        except Exception as e:
            raise self._handle_error(e, "Failed to generate response")
    
    async def stream_response(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        """Stream response from Anthropic."""
        try:
            await self.ensure_initialized()
            
            # Convert messages to Anthropic format
            system_message = None
            anthropic_messages = []
            
            for msg in request.messages:
                if msg.role == "system":
                    system_message = msg.content
                else:
                    anthropic_messages.append({
                        "role": msg.role,
                        "content": msg.content
                    })
            
            # Prepare request parameters
            params = {
                "model": request.model,
                "messages": anthropic_messages,
                "max_tokens": request.max_tokens,
                "temperature": request.temperature,
                "stream": True
            }
            
            # Add system message if present
            if system_message:
                params["system"] = system_message
            
            # Make streaming request
            async with self._client.messages.stream(**params) as stream:
                async for text in stream.text_stream:
                    yield text
                        
        except Exception as e:
            raise self._handle_error(e, "Failed to stream response")
    
    async def health_check(self) -> Dict[str, Any]:
        """Check Anthropic health status."""
        try:
            start_time = time.time()
            
            # Make a minimal request to test the service
            test_request = LLMRequest(
                messages=[LLMMessage(role="user", content="Hi")],
                model="claude-3-haiku-20240307",
                max_tokens=10
            )
            await self.generate_response(test_request)
            
            response_time = time.time() - start_time
            
            return {
                "status": "healthy",
                "response_time_ms": int(response_time * 1000),
                "available_models": len(await self.get_available_models())
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    async def estimate_cost(self, request: LLMRequest) -> Optional[float]:
        """Estimate request cost based on token usage."""
        try:
            # Estimate input tokens
            input_text = " ".join([msg.content for msg in request.messages])
            estimated_input_tokens = len(input_text) // 4  # Rough estimation
            
            # Estimate output tokens (use max_tokens as upper bound)
            estimated_output_tokens = request.max_tokens
            
            # Get pricing for model
            model_key = self._get_model_pricing_key(request.model)
            if model_key not in self.TOKEN_PRICING:
                return None
            
            pricing = self.TOKEN_PRICING[model_key]
            
            # Calculate cost (pricing is per 1M tokens)
            input_cost = (estimated_input_tokens / 1_000_000) * pricing["input"]
            output_cost = (estimated_output_tokens / 1_000_000) * pricing["output"]
            
            return input_cost + output_cost
            
        except Exception:
            return None
    
    def _calculate_cost(self, model: str, usage) -> Optional[float]:
        """Calculate actual cost based on usage."""
        if not usage:
            return None
        
        try:
            model_key = self._get_model_pricing_key(model)
            if model_key not in self.TOKEN_PRICING:
                return None
            
            pricing = self.TOKEN_PRICING[model_key]
            
            # Calculate cost (pricing is per 1M tokens)
            input_cost = (usage.input_tokens / 1_000_000) * pricing["input"]
            output_cost = (usage.output_tokens / 1_000_000) * pricing["output"]
            
            return input_cost + output_cost
            
        except Exception:
            return None
    
    def _get_model_pricing_key(self, model: str) -> str:
        """Get pricing key for model."""
        # Map model names to pricing keys
        if "claude-3-opus" in model:
            return "claude-3-opus"
        elif "claude-3-sonnet" in model:
            return "claude-3-sonnet"
        elif "claude-3-haiku" in model:
            return "claude-3-haiku"
        elif "claude-2.1" in model:
            return "claude-2.1"
        elif "claude-2.0" in model:
            return "claude-2.0"
        elif "claude-instant-1.2" in model:
            return "claude-instant-1.2"
        else:
            return model  # Return as-is if no mapping found