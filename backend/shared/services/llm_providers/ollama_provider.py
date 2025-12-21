"""Ollama LLM provider implementation."""

import asyncio
import time
from typing import Dict, List, Optional, Any, AsyncGenerator
import httpx
import json

from .base import (
    BaseLLMProvider, 
    LLMProviderConfig, 
    LLMRequest, 
    LLMResponse, 
    LLMUsage,
    LLMMessage,
    LLMError,
    LLMConnectionError,
    LLMProviderType
)


class OllamaConfig(LLMProviderConfig):
    """Ollama-specific configuration."""
    
    base_url: str = "http://localhost:11434"
    keep_alive: str = "5m"
    num_predict: Optional[int] = None
    num_ctx: Optional[int] = None
    
    def __init__(self, **data):
        if "provider_type" not in data:
            data["provider_type"] = LLMProviderType.OLLAMA
        super().__init__(**data)


class OllamaProvider(BaseLLMProvider):
    """Ollama LLM provider implementation."""
    
    def __init__(self, config: OllamaConfig, credentials: Dict[str, Any]):
        super().__init__(config, credentials)
        self.config: OllamaConfig = config
        self.base_url = credentials.get("base_url", config.base_url)
        
        # Initialize HTTP client
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(config.timeout),
            headers={"Content-Type": "application/json"}
        )
    
    async def initialize(self) -> None:
        """Initialize Ollama provider."""
        try:
            # Test connection
            response = await self._client.get("/api/tags")
            if response.status_code != 200:
                raise LLMConnectionError(
                    message=f"Failed to connect to Ollama server: {response.status_code}",
                    provider=self.provider_type.value
                )
            
            self.logger.info(f"Ollama provider initialized successfully at {self.base_url}")
            
        except httpx.RequestError as e:
            raise LLMConnectionError(
                message=f"Failed to connect to Ollama server: {str(e)}",
                provider=self.provider_type.value,
                original_error=e
            )
    
    async def validate_credentials(self) -> bool:
        """Validate Ollama connection."""
        try:
            await self.ensure_initialized()
            response = await self._client.get("/api/tags")
            return response.status_code == 200
        except Exception as e:
            self.logger.error(f"Ollama credential validation failed: {e}")
            return False
    
    async def get_available_models(self) -> List[str]:
        """Get list of available Ollama models."""
        try:
            await self.ensure_initialized()
            response = await self._client.get("/api/tags")
            response.raise_for_status()
            
            data = response.json()
            models = []
            
            for model in data.get("models", []):
                models.append(model.get("name", ""))
            
            return [m for m in models if m]  # Filter out empty names
            
        except Exception as e:
            raise self._handle_error(e, "Failed to get available models")
    
    async def generate_response(self, request: LLMRequest) -> LLMResponse:
        """Generate response from Ollama."""
        start_time = time.time()
        
        try:
            await self.ensure_initialized()
            
            # Convert messages to Ollama format
            ollama_messages = []
            for msg in request.messages:
                ollama_messages.append({
                    "role": msg.role,
                    "content": msg.content
                })
            
            # Prepare request payload
            payload = {
                "model": request.model,
                "messages": ollama_messages,
                "stream": False,
                "options": {
                    "temperature": request.temperature,
                    "num_predict": request.max_tokens,
                }
            }
            
            # Add optional parameters
            if self.config.num_ctx:
                payload["options"]["num_ctx"] = self.config.num_ctx
            
            if self.config.keep_alive:
                payload["keep_alive"] = self.config.keep_alive
            
            # Make request
            response = await self._client.post("/api/chat", json=payload)
            response.raise_for_status()
            
            response_data = response.json()
            response_time_ms = int((time.time() - start_time) * 1000)
            
            # Extract response content
            content = ""
            if "message" in response_data and "content" in response_data["message"]:
                content = response_data["message"]["content"]
            
            # Calculate usage (Ollama doesn't provide token counts, so we estimate)
            prompt_tokens = self._estimate_tokens(" ".join([msg.content for msg in request.messages]))
            completion_tokens = self._estimate_tokens(content)
            
            usage = LLMUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
                cost=0.0  # Ollama is free
            )
            
            return LLMResponse(
                content=content,
                model=request.model,
                usage=usage,
                finish_reason=response_data.get("done_reason", "stop"),
                response_time_ms=response_time_ms,
                provider=self.provider_type.value,
                metadata={
                    "eval_count": response_data.get("eval_count", 0),
                    "eval_duration": response_data.get("eval_duration", 0),
                    "load_duration": response_data.get("load_duration", 0),
                    "prompt_eval_count": response_data.get("prompt_eval_count", 0),
                    "prompt_eval_duration": response_data.get("prompt_eval_duration", 0),
                }
            )
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise LLMError(
                    message=f"Model '{request.model}' not found. Available models: {await self.get_available_models()}",
                    provider=self.provider_type.value,
                    error_code="MODEL_NOT_FOUND"
                )
            else:
                raise self._handle_error(e, f"HTTP error {e.response.status_code}")
        except Exception as e:
            raise self._handle_error(e, "Failed to generate response")
    
    async def stream_response(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        """Stream response from Ollama."""
        try:
            await self.ensure_initialized()
            
            # Convert messages to Ollama format
            ollama_messages = []
            for msg in request.messages:
                ollama_messages.append({
                    "role": msg.role,
                    "content": msg.content
                })
            
            # Prepare request payload
            payload = {
                "model": request.model,
                "messages": ollama_messages,
                "stream": True,
                "options": {
                    "temperature": request.temperature,
                    "num_predict": request.max_tokens,
                }
            }
            
            # Add optional parameters
            if self.config.num_ctx:
                payload["options"]["num_ctx"] = self.config.num_ctx
            
            if self.config.keep_alive:
                payload["keep_alive"] = self.config.keep_alive
            
            # Make streaming request
            async with self._client.stream("POST", "/api/chat", json=payload) as response:
                response.raise_for_status()
                
                async for line in response.aiter_lines():
                    if line.strip():
                        try:
                            data = json.loads(line)
                            if "message" in data and "content" in data["message"]:
                                content = data["message"]["content"]
                                if content:
                                    yield content
                        except json.JSONDecodeError:
                            continue
                        
        except Exception as e:
            raise self._handle_error(e, "Failed to stream response")
    
    async def health_check(self) -> Dict[str, Any]:
        """Check Ollama health status."""
        try:
            start_time = time.time()
            response = await self._client.get("/api/tags")
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                models = data.get("models", [])
                
                return {
                    "status": "healthy",
                    "response_time_ms": int(response_time * 1000),
                    "available_models": len(models),
                    "base_url": self.base_url,
                    "models": [model.get("name", "") for model in models[:5]]  # First 5 models
                }
            else:
                return {
                    "status": "unhealthy",
                    "error": f"HTTP {response.status_code}",
                    "base_url": self.base_url
                }
                
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "base_url": self.base_url
            }
    
    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count for text (rough approximation)."""
        # Simple estimation: ~4 characters per token
        return max(1, len(text) // 4)
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.ensure_initialized()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()