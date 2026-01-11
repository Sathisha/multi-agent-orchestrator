"""Google Gemini LLM provider implementation using official google-genai SDK."""

import time
from typing import Dict, List, Optional, Any, AsyncGenerator

try:
    from google import genai
    from google.genai import types
except ImportError:
    raise ImportError("google-genai package is required. Install with: pip install google-genai")

from .base import (
    BaseLLMProvider,
    LLMProviderConfig,
    LLMRequest,
    LLMResponse,
    LLMUsage,
    LLMError,
    LLMAuthenticationError,
    LLMRateLimitError,
    LLMProviderType
)


class GoogleConfig(LLMProviderConfig):
    """Google Gemini-specific configuration."""
    
    max_tokens_per_minute: int = 60000
    requests_per_minute: int = 60
    
    def __init__(self, **data):
        if "provider_type" not in data:
            data["provider_type"] = LLMProviderType.GOOGLE
        super().__init__(**data)


class GoogleProvider(BaseLLMProvider):
    """Google Gemini LLM provider implementation via official SDK."""
    
    # Token pricing per 1M tokens (approximate)
    TOKEN_PRICING = {
        "gemini-1.5-pro": {"input": 1.25, "output": 5.00},
        "gemini-1.5-flash": {"input": 0.075, "output": 0.30},
        "gemini-2.0-flash": {"input": 0.075, "output": 0.30},
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
        
        # Create client - API key can be passed or set via GEMINI_API_KEY env var
        self._client = genai.Client(api_key=self.api_key)
    
    async def initialize(self) -> None:
        """Initialize Google provider."""
        try:
            # Test connectivity by listing models
            await self.get_available_models()
            self.logger.info("Google GenAI SDK provider initialized successfully")
        except Exception as e:
            self.logger.warning(f"Google initialization check failed (non-blocking): {e}")
    
    async def validate_credentials(self) -> bool:
        """Validate Google credentials."""
        try:
            await self.get_available_models()
            return True
        except Exception as e:
            self.logger.error(f"Google credential validation failed: {e}")
            return False
    
    async def health_check(self) -> Dict[str, Any]:
        """Check Google Gemini provider health status."""
        try:
            models = await self.get_available_models()
            return {
                "status": "healthy",
                "provider": self.provider_type.value,
                "available_models": len(models),
                "message": "Google Gemini API is accessible"
            }
        except LLMAuthenticationError as e:
            return {
                "status": "unhealthy",
                "provider": self.provider_type.value,
                "error": "Authentication failed",
                "message": str(e)
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "provider": self.provider_type.value,
                "error": "Connection or API error",
                "message": str(e)
            }
    
    async def get_available_models(self) -> List[str]:
        """Get list of available Google models."""
        try:
            # List models using new SDK - this returns an iterator
            models_response = self._client.models.list()
            
            available_models = []
            for model in models_response:
                # Model has .name attribute like "models/gemini-1.5-pro"
                model_name = model.name.replace("models/", "")
                available_models.append(model_name)
            
            return sorted(available_models)
            
        except Exception as e:
            error_str = str(e)
            if "401" in error_str or "403" in error_str or "Unauthorized" in error_str:
                raise LLMAuthenticationError(
                    message=f"Authentication failed: {e}",
                    provider=self.provider_type.value
                )
            raise self._handle_error(e, "Failed to get available models")
    
    async def generate_response(self, request: LLMRequest) -> LLMResponse:
        """Generate response from Google Gemini using SDK."""
        start_time = time.time()
        
        try:
            model_name = self._resolve_model_name(request.model)
            
            # Build content from messages
            contents = []
            system_instruction = None
            
            for msg in request.messages:
                if msg.role == "system":
                    system_instruction = msg.content
                elif msg.role == "user":
                    contents.append(types.Content(role="user", parts=[types.Part(text=msg.content)]))
                elif msg.role == "assistant":
                    contents.append(types.Content(role="model", parts=[types.Part(text=msg.content)]))
            
            # Build config
            config = types.GenerateContentConfig(
                temperature=request.temperature,
                max_output_tokens=request.max_tokens,
                system_instruction=system_instruction if system_instruction else None
            )
            
            self.logger.info(f"[Google SDK] Generating with model {model_name}")
            
            # Generate content using new SDK
            response = self._client.models.generate_content(
                model=model_name,
                contents=contents,
                config=config
            )
            
            # Extract content - response.text is the easiest way
            if not response.text:
                # Check for safety blocks or other issues
                if hasattr(response, 'candidates') and response.candidates:
                    candidate = response.candidates[0]
                    if hasattr(candidate, 'finish_reason'):
                        finish_reason = str(candidate.finish_reason)
                        if 'SAFETY' in finish_reason:
                            raise LLMError(
                                message=f"Content blocked due to safety: {finish_reason}",
                                provider=self.provider_type.value,
                                error_code="SAFETY_BLOCK"
                            )
                
                raise LLMError(
                    message="No text content in response",
                    provider=self.provider_type.value,
                    error_code="NO_CONTENT"
                )
            
            content = response.text
            
            # Extract usage metadata
            prompt_tokens = 0
            completion_tokens = 0
            total_tokens = 0
            
            if hasattr(response, 'usage_metadata'):
                usage = response.usage_metadata
                prompt_tokens = getattr(usage, 'prompt_token_count', 0)
                completion_tokens = getattr(usage, 'candidates_token_count', 0)
                total_tokens = getattr(usage, 'total_token_count', 0)
            
            # Calculate cost
            cost = self._calculate_cost(request.model, prompt_tokens, completion_tokens)
            
            llm_usage = LLMUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                cost=cost
            )
            
            response_time_ms = int((time.time() - start_time) * 1000)
            
            # Get finish reason
            finish_reason = "stop"
            if hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, 'finish_reason'):
                    finish_reason = str(candidate.finish_reason).lower()
            
            return LLMResponse(
                content=content,
                model=request.model,
                usage=llm_usage,
                finish_reason=finish_reason,
                response_time_ms=response_time_ms,
                provider=self.provider_type.value
            )
            
        except Exception as e:
            if isinstance(e, LLMError):
                raise
            
            error_msg = str(e)
            
            # Map SDK exceptions to our error types
            if "API key" in error_msg or "401" in error_msg or "403" in error_msg:
                raise LLMAuthenticationError(
                    message=f"Authentication failed: {error_msg}",
                    provider=self.provider_type.value
                )
            elif "429" in error_msg or "quota" in error_msg.lower():
                raise LLMRateLimitError(
                    message=f"Rate limit exceeded: {error_msg}",
                    provider=self.provider_type.value
                )
            elif "not found" in error_msg.lower() or "invalid" in error_msg.lower():
                from .base import LLMValidationError
                raise LLMValidationError(
                    message=f"Invalid model or request: {error_msg}",
                    provider=self.provider_type.value
                )
            else:
                raise self._handle_error(e, "Failed to generate response")
    
    async def stream_response(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        """Stream response from Google Gemini using SDK."""
        try:
            model_name = self._resolve_model_name(request.model)
            
            # Build content from messages
            contents = []
            system_instruction = None
            
            for msg in request.messages:
                if msg.role == "system":
                    system_instruction = msg.content
                elif msg.role == "user":
                    contents.append(types.Content(role="user", parts=[types.Part(text=msg.content)]))
                elif msg.role == "assistant":
                    contents.append(types.Content(role="model", parts=[types.Part(text=msg.content)]))
            
            # Build config
            config = types.GenerateContentConfig(
                temperature=request.temperature,
                max_output_tokens=request.max_tokens,
                system_instruction=system_instruction if system_instruction else None
            )
            
            self.logger.info(f"[Google SDK] Streaming from model {model_name}")
            
            # Stream content
            for chunk in self._client.models.generate_content_stream(
                model=model_name,
                contents=contents,
                config=config
            ):
                if chunk.text:
                    yield chunk.text
                    
        except Exception as e:
            if isinstance(e, LLMError):
                raise
            raise self._handle_error(e, "Failed to stream response")
    
    def _resolve_model_name(self, model: str) -> str:
        """Resolve generic model names to specific IDs."""
        model_lower = model.lower()
        
        if model_lower == "gemini":
            return "gemini-2.0-flash-exp"
        
        if model.startswith("models/"):
            return model.replace("models/", "")
            
        return model
    
    async def estimate_cost(self, request: LLMRequest) -> Optional[float]:
        """Estimate request cost."""
        try:
            input_text = " ".join([msg.content for msg in request.messages])
            estimated_input_tokens = len(input_text) // 4
            estimated_output_tokens = request.max_tokens
            return self._calculate_cost(request.model, estimated_input_tokens, estimated_output_tokens)
        except Exception:
            return None
            
    def _calculate_cost(self, model: str, prompt_tokens: int, completion_tokens: int) -> Optional[float]:
        try:
            simple_name = self._resolve_model_name(model) 
            pricing = None
            for key in self.TOKEN_PRICING:
                if key in simple_name:
                    pricing = self.TOKEN_PRICING[key]
                    break
            
            if not pricing:
                return None
            
            input_cost = (prompt_tokens / 1_000_000) * pricing["input"]
            output_cost = (completion_tokens / 1_000_000) * pricing["output"]
            return input_cost + output_cost
        except Exception:
            return None
