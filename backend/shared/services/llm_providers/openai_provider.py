"""OpenAI LLM provider implementation."""

import time
from typing import Dict, List, Optional, Any, AsyncGenerator
import openai
from openai import AsyncOpenAI

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


class OpenAIConfig(LLMProviderConfig):
    """OpenAI-specific configuration."""
    
    organization: Optional[str] = None
    max_tokens_per_minute: int = 90000
    requests_per_minute: int = 3500
    
    def __init__(self, **data):
        if "provider_type" not in data:
            data["provider_type"] = LLMProviderType.OPENAI
        super().__init__(**data)


class OpenAIProvider(BaseLLMProvider):
    """OpenAI LLM provider implementation."""
    
    # Token pricing per 1K tokens (as of late 2023)
    TOKEN_PRICING = {
        "gpt-4": {"input": 0.03, "output": 0.06},
        "gpt-4-32k": {"input": 0.06, "output": 0.12},
        "gpt-4-turbo-preview": {"input": 0.01, "output": 0.03},
        "gpt-3.5-turbo": {"input": 0.0015, "output": 0.002},
        "gpt-3.5-turbo-16k": {"input": 0.003, "output": 0.004},
    }
    
    def __init__(self, config: OpenAIConfig, credentials: Dict[str, Any]):
        super().__init__(config, credentials)
        self.config: OpenAIConfig = config
        
        # Extract credentials
        self.api_key = credentials.get("api_key")
        self.organization = credentials.get("organization", config.organization)
        
        if not self.api_key:
            raise LLMError(
                message="OpenAI API key is required",
                provider=self.provider_type.value,
                error_code="MISSING_API_KEY"
            )
    
    async def initialize(self) -> None:
        """Initialize OpenAI provider."""
        try:
            # Initialize OpenAI client
            self._client = AsyncOpenAI(
                api_key=self.api_key,
                organization=self.organization,
                timeout=self.config.timeout
            )
            
            # Test connection by listing models
            models = await self._client.models.list()
            self.logger.info(f"OpenAI provider initialized successfully with {len(models.data)} models")
            
        except openai.AuthenticationError as e:
            raise LLMAuthenticationError(
                message="Invalid OpenAI API key",
                provider=self.provider_type.value,
                original_error=e
            )
        except Exception as e:
            raise self._handle_error(e, "Failed to initialize OpenAI provider")
    
    async def validate_credentials(self) -> bool:
        """Validate OpenAI credentials."""
        try:
            await self.ensure_initialized()
            # Try to list models as a credential test
            await self._client.models.list()
            return True
        except Exception as e:
            self.logger.error(f"OpenAI credential validation failed: {e}")
            return False
    
    async def get_available_models(self) -> List[str]:
        """Get list of available OpenAI models."""
        try:
            await self.ensure_initialized()
            models = await self._client.models.list()
            
            # Filter for chat models
            chat_models = []
            for model in models.data:
                if any(prefix in model.id for prefix in ["gpt-", "text-davinci"]):
                    chat_models.append(model.id)
            
            return sorted(chat_models)
            
        except Exception as e:
            raise self._handle_error(e, "Failed to get available models")
    
    async def generate_response(self, request: LLMRequest) -> LLMResponse:
        """Generate response from OpenAI."""
        start_time = time.time()
        
        try:
            await self.ensure_initialized()
            
            # Convert messages to OpenAI format
            openai_messages = []
            for msg in request.messages:
                openai_messages.append({
                    "role": msg.role,
                    "content": msg.content
                })
            
            # Prepare request parameters
            params = {
                "model": request.model,
                "messages": openai_messages,
                "temperature": request.temperature,
                "max_tokens": request.max_tokens,
                "stream": False
            }
            
            # Add tools if provided
            if request.tools:
                params["tools"] = request.tools
            
            # Make request
            response = await self._client.chat.completions.create(**params)
            response_time_ms = int((time.time() - start_time) * 1000)
            
            # Extract response content
            content = ""
            if response.choices and len(response.choices) > 0:
                choice = response.choices[0]
                if choice.message and choice.message.content:
                    content = choice.message.content
            
            # Calculate cost
            cost = self._calculate_cost(request.model, response.usage)
            
            # Create usage object
            usage = LLMUsage(
                prompt_tokens=response.usage.prompt_tokens if response.usage else 0,
                completion_tokens=response.usage.completion_tokens if response.usage else 0,
                total_tokens=response.usage.total_tokens if response.usage else 0,
                cost=cost
            )
            
            return LLMResponse(
                content=content,
                model=response.model,
                usage=usage,
                finish_reason=response.choices[0].finish_reason if response.choices else "unknown",
                response_time_ms=response_time_ms,
                provider=self.provider_type.value,
                metadata={
                    "system_fingerprint": getattr(response, "system_fingerprint", None),
                    "created": response.created,
                    "object": response.object
                }
            )
            
        except openai.AuthenticationError as e:
            raise LLMAuthenticationError(
                message="OpenAI authentication failed",
                provider=self.provider_type.value,
                original_error=e
            )
        except openai.RateLimitError as e:
            raise LLMRateLimitError(
                message="OpenAI rate limit exceeded",
                provider=self.provider_type.value,
                retry_after=getattr(e, "retry_after", None),
                original_error=e
            )
        except Exception as e:
            raise self._handle_error(e, "Failed to generate response")
    
    async def stream_response(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        """Stream response from OpenAI."""
        try:
            await self.ensure_initialized()
            
            # Convert messages to OpenAI format
            openai_messages = []
            for msg in request.messages:
                openai_messages.append({
                    "role": msg.role,
                    "content": msg.content
                })
            
            # Prepare request parameters
            params = {
                "model": request.model,
                "messages": openai_messages,
                "temperature": request.temperature,
                "max_tokens": request.max_tokens,
                "stream": True
            }
            
            # Add tools if provided
            if request.tools:
                params["tools"] = request.tools
            
            # Make streaming request
            stream = await self._client.chat.completions.create(**params)
            
            async for chunk in stream:
                if chunk.choices and len(chunk.choices) > 0:
                    choice = chunk.choices[0]
                    if choice.delta and choice.delta.content:
                        yield choice.delta.content
                        
        except Exception as e:
            raise self._handle_error(e, "Failed to stream response")
    
    async def health_check(self) -> Dict[str, Any]:
        """Check OpenAI health status."""
        try:
            start_time = time.time()
            models = await self._client.models.list()
            response_time = time.time() - start_time
            
            return {
                "status": "healthy",
                "response_time_ms": int(response_time * 1000),
                "available_models": len(models.data),
                "organization": self.organization,
                "models": [model.id for model in models.data[:5]]  # First 5 models
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "organization": self.organization
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
            
            # Calculate cost (pricing is per 1K tokens)
            input_cost = (estimated_input_tokens / 1000) * pricing["input"]
            output_cost = (estimated_output_tokens / 1000) * pricing["output"]
            
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
            
            # Calculate cost (pricing is per 1K tokens)
            input_cost = (usage.prompt_tokens / 1000) * pricing["input"]
            output_cost = (usage.completion_tokens / 1000) * pricing["output"]
            
            return input_cost + output_cost
            
        except Exception:
            return None
    
    def _get_model_pricing_key(self, model: str) -> str:
        """Get pricing key for model."""
        # Map model names to pricing keys
        if "gpt-4-turbo" in model:
            return "gpt-4-turbo-preview"
        elif "gpt-4-32k" in model:
            return "gpt-4-32k"
        elif "gpt-4" in model:
            return "gpt-4"
        elif "gpt-3.5-turbo-16k" in model:
            return "gpt-3.5-turbo-16k"
        elif "gpt-3.5-turbo" in model:
            return "gpt-3.5-turbo"
        else:
            return model  # Return as-is if no mapping found