"""Google Gemini LLM provider implementation."""

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
    LLMAuthenticationError,
    LLMRateLimitError,
    LLMProviderType
)


class GoogleConfig(LLMProviderConfig):
    """Google Gemini-specific configuration."""
    
    base_url: str = "https://generativelanguage.googleapis.com/v1beta"
    max_tokens_per_minute: int = 60000
    requests_per_minute: int = 60
    
    def __init__(self, **data):
        if "provider_type" not in data:
            data["provider_type"] = LLMProviderType.GOOGLE
        super().__init__(**data)


class GoogleProvider(BaseLLMProvider):
    """Google Gemini LLM provider implementation."""
    
    # Token pricing per 1M tokens (approximate)
    TOKEN_PRICING = {
        "gemini-1.5-pro": {"input": 1.25, "output": 5.00},
        "gemini-1.5-flash": {"input": 0.075, "output": 0.30},
        "gemini-pro": {"input": 0.50, "output": 1.50},
    }
    
    def __init__(self, config: GoogleConfig, credentials: Dict[str, Any]):
        super().__init__(config, credentials)
        self.config: GoogleConfig = config
        
        # Extract credentials
        self.api_key = credentials.get("api_key")
        
        if not self.api_key:
            raise LLMError(
                message="Google API key is required",
                provider=self.provider_type.value,
                error_code="MISSING_API_KEY"
            )
        
        # Initialize HTTP client
        self._client = httpx.AsyncClient(
            base_url=self.config.base_url,
            timeout=self.config.timeout
        )
    
    async def initialize(self) -> None:
        """Initialize Google provider."""
        try:
            # Test connection by listing models
            models = await self.get_available_models()
            self.logger.info(f"Google provider initialized successfully with {len(models)} models")
            
        except Exception as e:
            raise self._handle_error(e, "Failed to initialize Google provider")
    
    async def validate_credentials(self) -> bool:
        """Validate Google credentials."""
        try:
            await self.ensure_initialized()
            # Try to list models as a credential test
            await self.get_available_models()
            return True
        except Exception as e:
            self.logger.error(f"Google credential validation failed: {e}")
            return False
    
    async def get_available_models(self) -> List[str]:
        """Get list of available Google models."""
        try:
            # Make API request to list models
            response = await self._client.get(
                "/models",
                params={"key": self.api_key}
            )
            
            if response.status_code == 401:
                raise LLMAuthenticationError(
                    message="Invalid Google API key",
                    provider=self.provider_type.value
                )
            
            response.raise_for_status()
            data = response.json()
            
            # Extract model names that support generateContent
            models = []
            for model in data.get("models", []):
                if "generateContent" in model.get("supportedGenerationMethods", []):
                    # Extract model name (remove "models/" prefix)
                    model_name = model.get("name", "").replace("models/", "")
                    models.append(model_name)
            
            return sorted(models)
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise LLMAuthenticationError(
                    message="Invalid Google API key",
                    provider=self.provider_type.value,
                    original_error=e
                )
            elif e.response.status_code == 429:
                raise LLMRateLimitError(
                    message="Google rate limit exceeded",
                    provider=self.provider_type.value,
                    original_error=e
                )
            raise self._handle_error(e, "Failed to get available models")
        except Exception as e:
            raise self._handle_error(e, "Failed to get available models")
    
    async def generate_response(self, request: LLMRequest) -> LLMResponse:
        """Generate response from Google Gemini."""
        start_time = time.time()
        
        try:
            await self.ensure_initialized()
            
            # Convert messages to Google format
            contents = []
            system_instruction = None
            
            for msg in request.messages:
                if msg.role == "system":
                    # Google uses systemInstruction separately
                    system_instruction = {"parts": [{"text": msg.content}]}
                else:
                    # Map role (assistant -> model)
                    role = "model" if msg.role == "assistant" else "user"
                    contents.append({
                        "role": role,
                        "parts": [{"text": msg.content}]
                    })
            
            # Prepare request body
            body = {
                "contents": contents,
                "generationConfig": {
                    "temperature": request.temperature,
                    "maxOutputTokens": request.max_tokens,
                }
            }
            
            if system_instruction:
                body["systemInstruction"] = system_instruction
            
            # Make request
            model_name = request.model
            if not model_name.startswith("models/"):
                model_name = f"models/{model_name}"
            
            response = await self._client.post(
                f"/{model_name}:generateContent",
                params={"key": self.api_key},
                json=body,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 401:
                raise LLMAuthenticationError(
                    message="Invalid Google API key",
                    provider=self.provider_type.value
                )
            
            response.raise_for_status()
            response_time_ms = int((time.time() - start_time) * 1000)
            
            data = response.json()
            
            # Extract response content
            content = ""
            if "candidates" in data and len(data["candidates"]) > 0:
                candidate = data["candidates"][0]
                if "content" in candidate and "parts" in candidate["content"]:
                    parts = candidate["content"]["parts"]
                    content = "".join([part.get("text", "") for part in parts])
            
            # Extract usage metadata
            usage_metadata = data.get("usageMetadata", {})
            prompt_tokens = usage_metadata.get("promptTokenCount", 0)
            completion_tokens = usage_metadata.get("candidatesTokenCount", 0)
            total_tokens = usage_metadata.get("totalTokenCount", 0)
            
            # Calculate cost
            cost = self._calculate_cost(request.model, prompt_tokens, completion_tokens)
            
            # Create usage object
            usage = LLMUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                cost=cost
            )
            
            # Get finish reason
            finish_reason = "unknown"
            if "candidates" in data and len(data["candidates"]) > 0:
                finish_reason = data["candidates"][0].get("finishReason", "unknown").lower()
            
            return LLMResponse(
                content=content,
                model=request.model,
                usage=usage,
                finish_reason=finish_reason,
                response_time_ms=response_time_ms,
                provider=self.provider_type.value,
                metadata={
                    "model_version": data.get("modelVersion"),
                    "safety_ratings": data.get("candidates", [{}])[0].get("safetyRatings", [])
                }
            )
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise LLMAuthenticationError(
                    message="Google authentication failed",
                    provider=self.provider_type.value,
                    original_error=e
                )
            elif e.response.status_code == 429:
                raise LLMRateLimitError(
                    message="Google rate limit exceeded",
                    provider=self.provider_type.value,
                    original_error=e
                )
            raise self._handle_error(e, "Failed to generate response")
        except Exception as e:
            raise self._handle_error(e, "Failed to generate response")
    
    async def stream_response(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        """Stream response from Google Gemini."""
        try:
            await self.ensure_initialized()
            
            # Convert messages to Google format
            contents = []
            system_instruction = None
            
            for msg in request.messages:
                if msg.role == "system":
                    system_instruction = {"parts": [{"text": msg.content}]}
                else:
                    role = "model" if msg.role == "assistant" else "user"
                    contents.append({
                        "role": role,
                        "parts": [{"text": msg.content}]
                    })
            
            # Prepare request body
            body = {
                "contents": contents,
                "generationConfig": {
                    "temperature": request.temperature,
                    "maxOutputTokens": request.max_tokens,
                }
            }
            
            if system_instruction:
                body["systemInstruction"] = system_instruction
            
            # Make streaming request
            model_name = request.model
            if not model_name.startswith("models/"):
                model_name = f"models/{model_name}"
            
            async with self._client.stream(
                "POST",
                f"/{model_name}:streamGenerateContent",
                params={"key": self.api_key, "alt": "sse"},
                json=body,
                headers={"Content-Type": "application/json"}
            ) as response:
                response.raise_for_status()
                
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        try:
                            chunk_data = json.loads(line[6:])
                            if "candidates" in chunk_data and len(chunk_data["candidates"]) > 0:
                                candidate = chunk_data["candidates"][0]
                                if "content" in candidate and "parts" in candidate["content"]:
                                    for part in candidate["content"]["parts"]:
                                        if "text" in part:
                                            yield part["text"]
                        except json.JSONDecodeError:
                            continue
                        
        except Exception as e:
            raise self._handle_error(e, "Failed to stream response")
    
    async def health_check(self) -> Dict[str, Any]:
        """Check Google health status."""
        try:
            start_time = time.time()
            models = await self.get_available_models()
            response_time = time.time() - start_time
            
            return {
                "status": "healthy",
                "response_time_ms": int(response_time * 1000),
                "available_models": len(models),
                "models": models[:5]  # First 5 models
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
            
            # Calculate cost
            return self._calculate_cost(request.model, estimated_input_tokens, estimated_output_tokens)
            
        except Exception:
            return None
    
    def _calculate_cost(self, model: str, prompt_tokens: int, completion_tokens: int) -> Optional[float]:
        """Calculate actual cost based on usage."""
        try:
            model_key = self._get_model_pricing_key(model)
            if model_key not in self.TOKEN_PRICING:
                return None
            
            pricing = self.TOKEN_PRICING[model_key]
            
            # Calculate cost (pricing is per 1M tokens)
            input_cost = (prompt_tokens / 1_000_000) * pricing["input"]
            output_cost = (completion_tokens / 1_000_000) * pricing["output"]
            
            return input_cost + output_cost
            
        except Exception:
            return None
    
    def _get_model_pricing_key(self, model: str) -> str:
        """Get pricing key for model."""
        # Remove "models/" prefix if present
        model = model.replace("models/", "")
        
        # Map model names to pricing keys
        if "gemini-1.5-pro" in model:
            return "gemini-1.5-pro"
        elif "gemini-1.5-flash" in model:
            return "gemini-1.5-flash"
        elif "gemini-pro" in model:
            return "gemini-pro"
        else:
            return model  # Return as-is if no mapping found
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()
