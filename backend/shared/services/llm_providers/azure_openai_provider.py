"""Azure OpenAI LLM provider implementation."""

import time
from typing import Dict, List, Optional, Any, AsyncGenerator
import openai
from openai import AsyncAzureOpenAI

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


class AzureOpenAIConfig(LLMProviderConfig):
    """Azure OpenAI-specific configuration."""
    
    api_version: str = "2023-12-01-preview"
    max_tokens_per_minute: int = 90000
    requests_per_minute: int = 3500
    
    def __init__(self, **data):
        if "provider_type" not in data:
            data["provider_type"] = LLMProviderType.AZURE_OPENAI
        super().__init__(**data)


class AzureOpenAIProvider(BaseLLMProvider):
    """Azure OpenAI LLM provider implementation."""
    
    def __init__(self, config: AzureOpenAIConfig, credentials: Dict[str, Any]):
        super().__init__(config, credentials)
        self.config: AzureOpenAIConfig = config
        
        # Extract credentials
        self.api_key = credentials.get("api_key")
        self.endpoint = credentials.get("endpoint")
        self.api_version = credentials.get("api_version", config.api_version)
        
        if not self.api_key:
            raise LLMError(
                message="Azure OpenAI API key is required",
                provider=self.provider_type.value,
                error_code="MISSING_API_KEY"
            )
        
        if not self.endpoint:
            raise LLMError(
                message="Azure OpenAI endpoint is required",
                provider=self.provider_type.value,
                error_code="MISSING_ENDPOINT"
            )
    
    async def initialize(self) -> None:
        """Initialize Azure OpenAI provider."""
        try:
            # Initialize Azure OpenAI client
            self._client = AsyncAzureOpenAI(
                api_key=self.api_key,
                azure_endpoint=self.endpoint,
                api_version=self.api_version,
                timeout=self.config.timeout
            )
            
            self.logger.info(f"Azure OpenAI provider initialized successfully at {self.endpoint}")
            
        except openai.AuthenticationError as e:
            raise LLMAuthenticationError(
                message="Invalid Azure OpenAI credentials",
                provider=self.provider_type.value,
                original_error=e
            )
        except Exception as e:
            raise self._handle_error(e, "Failed to initialize Azure OpenAI provider")
    
    async def validate_credentials(self) -> bool:
        """Validate Azure OpenAI credentials."""
        try:
            await self.ensure_initialized()
            # Try to list deployments as a credential test
            deployments = await self._client.models.list()
            return True
        except Exception as e:
            self.logger.error(f"Azure OpenAI credential validation failed: {e}")
            return False
    
    async def get_available_models(self) -> List[str]:
        """Get list of available Azure OpenAI deployments."""
        try:
            await self.ensure_initialized()
            models = await self._client.models.list()
            
            # Return deployment names (which are used as model names in Azure)
            deployment_names = []
            for model in models.data:
                deployment_names.append(model.id)
            
            return sorted(deployment_names)
            
        except Exception as e:
            raise self._handle_error(e, "Failed to get available models")
    
    async def generate_response(self, request: LLMRequest) -> LLMResponse:
        """Generate response from Azure OpenAI."""
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
                "model": request.model,  # This is the deployment name in Azure
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
            
            # Create usage object (Azure OpenAI uses same format as OpenAI)
            usage = LLMUsage(
                prompt_tokens=response.usage.prompt_tokens if response.usage else 0,
                completion_tokens=response.usage.completion_tokens if response.usage else 0,
                total_tokens=response.usage.total_tokens if response.usage else 0,
                cost=None  # Azure pricing varies by deployment
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
                    "object": response.object,
                    "endpoint": self.endpoint,
                    "api_version": self.api_version
                }
            )
            
        except openai.AuthenticationError as e:
            raise LLMAuthenticationError(
                message="Azure OpenAI authentication failed",
                provider=self.provider_type.value,
                original_error=e
            )
        except openai.RateLimitError as e:
            raise LLMRateLimitError(
                message="Azure OpenAI rate limit exceeded",
                provider=self.provider_type.value,
                retry_after=getattr(e, "retry_after", None),
                original_error=e
            )
        except Exception as e:
            raise self._handle_error(e, "Failed to generate response")
    
    async def stream_response(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        """Stream response from Azure OpenAI."""
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
                "model": request.model,  # This is the deployment name in Azure
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
        """Check Azure OpenAI health status."""
        try:
            start_time = time.time()
            models = await self._client.models.list()
            response_time = time.time() - start_time
            
            return {
                "status": "healthy",
                "response_time_ms": int(response_time * 1000),
                "available_models": len(models.data),
                "endpoint": self.endpoint,
                "api_version": self.api_version,
                "models": [model.id for model in models.data[:5]]  # First 5 models
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "endpoint": self.endpoint,
                "api_version": self.api_version
            }
    
    async def estimate_cost(self, request: LLMRequest) -> Optional[float]:
        """Estimate request cost (Azure pricing varies by deployment)."""
        # Azure OpenAI pricing varies by deployment and region
        # Return None as we can't estimate without deployment-specific pricing
        return None