"""Base LLM Provider interface and common models."""

from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field
import logging

logger = logging.getLogger(__name__)


class LLMProviderType(str, Enum):
    """Supported LLM provider types."""
    
    OLLAMA = "ollama"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    AZURE_OPENAI = "azure-openai"
    GOOGLE = "google"
    MOCK = "mock"


class LLMMessage(BaseModel):
    """LLM message model."""
    
    role: str = Field(..., description="Message role (system, user, assistant)")
    content: str = Field(..., description="Message content")
    images: Optional[List[str]] = Field(None, description="List of base64 encoded images")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")


class LLMRequest(BaseModel):
    """LLM request model."""
    
    messages: List[LLMMessage] = Field(..., description="Conversation messages")
    model: str = Field(..., description="Model name")
    temperature: float = Field(0.7, ge=0.0, le=2.0, description="Temperature setting")
    max_tokens: int = Field(1000, ge=1, le=8000, description="Maximum tokens")
    top_p: Optional[float] = Field(None, ge=0.0, le=1.0, description="Nucleus sampling parameter")
    top_k: Optional[int] = Field(None, ge=1, description="Top-k sampling parameter")
    stop_sequences: Optional[List[str]] = Field(None, description="Stop sequences for generation")
    stream: bool = Field(False, description="Enable streaming response")
    tools: Optional[List[Dict[str, Any]]] = Field(None, description="Available tools")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Request metadata")


class LLMUsage(BaseModel):
    """LLM usage statistics."""
    
    prompt_tokens: int = Field(0, description="Input tokens used")
    completion_tokens: int = Field(0, description="Output tokens used")
    total_tokens: int = Field(0, description="Total tokens used")
    cost: Optional[float] = Field(None, description="Estimated cost")


class LLMResponse(BaseModel):
    """LLM response model."""
    
    content: str = Field(..., description="Response content")
    model: str = Field(..., description="Model used")
    usage: LLMUsage = Field(..., description="Token usage")
    finish_reason: str = Field(..., description="Completion reason")
    response_time_ms: int = Field(..., description="Response time in milliseconds")
    provider: str = Field(..., description="Provider name")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Response metadata")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")


class LLMError(Exception):
    """Base LLM provider error."""
    
    def __init__(
        self, 
        message: str, 
        provider: str, 
        error_code: Optional[str] = None,
        retry_after: Optional[int] = None,
        original_error: Optional[Exception] = None
    ):
        self.message = message
        self.provider = provider
        self.error_code = error_code
        self.retry_after = retry_after
        self.original_error = original_error
        super().__init__(f"[{provider}] {message}")


class LLMConnectionError(LLMError):
    """LLM provider connection error."""
    pass


class LLMAuthenticationError(LLMError):
    """LLM provider authentication error."""
    pass


class LLMRateLimitError(LLMError):
    """LLM provider rate limit error."""
    pass


class LLMValidationError(LLMError):
    """LLM provider validation error."""
    pass


class LLMProviderConfig(BaseModel):
    """Base LLM provider configuration."""
    
    provider_type: LLMProviderType = Field(..., description="Provider type")
    enabled: bool = Field(True, description="Provider enabled")
    timeout: int = Field(30, description="Request timeout in seconds")
    max_retries: int = Field(3, description="Maximum retry attempts")
    retry_delay: float = Field(1.0, description="Retry delay in seconds")
    fallback_providers: List[str] = Field(default_factory=list, description="Fallback provider names")
    
    # Rate limiting
    requests_per_minute: Optional[int] = Field(None, description="Rate limit per minute")
    tokens_per_minute: Optional[int] = Field(None, description="Token limit per minute")
    
    # Cost management
    max_cost_per_request: Optional[float] = Field(None, description="Maximum cost per request")
    daily_cost_limit: Optional[float] = Field(None, description="Daily cost limit")


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    def __init__(self, config: LLMProviderConfig, credentials: Dict[str, Any]):
        self.config = config
        self.credentials = credentials
        self.provider_type = config.provider_type
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Initialize provider-specific client
        self._client = None
        self._is_initialized = False
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the provider client."""
        pass
    
    @abstractmethod
    async def validate_credentials(self) -> bool:
        """Validate provider credentials."""
        pass
    
    @abstractmethod
    async def get_available_models(self) -> List[str]:
        """Get list of available models."""
        pass
    
    @abstractmethod
    async def generate_response(self, request: LLMRequest) -> LLMResponse:
        """Generate response from LLM."""
        pass
    
    @abstractmethod
    async def stream_response(self, request: LLMRequest):
        """Stream response from LLM (async generator)."""
        pass
    
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Check provider health status."""
        pass
    
    async def ensure_initialized(self) -> None:
        """Ensure provider is initialized."""
        if not self._is_initialized:
            await self.initialize()
            self._is_initialized = True
    
    def get_provider_info(self) -> Dict[str, Any]:
        """Get provider information."""
        return {
            "provider_type": self.provider_type.value,
            "enabled": self.config.enabled,
            "timeout": self.config.timeout,
            "max_retries": self.config.max_retries,
            "fallback_providers": self.config.fallback_providers
        }
    
    async def estimate_cost(self, request: LLMRequest) -> Optional[float]:
        """Estimate request cost (override in provider implementations)."""
        return None
    
    def _handle_error(self, error: Exception, context: str = "") -> LLMError:
        """Convert provider-specific errors to LLMError."""
        # Use repr(error) if str(error) is empty to avoid trailing colons
        err_str = str(error) if str(error) else repr(error)
        error_message = f"{context}: {err_str}" if context else err_str
        
        # Map common error types
        if "authentication" in str(error).lower() or "unauthorized" in str(error).lower():
            return LLMAuthenticationError(
                message=error_message,
                provider=self.provider_type.value,
                original_error=error
            )
        elif "rate limit" in str(error).lower() or "quota" in str(error).lower():
            return LLMRateLimitError(
                message=error_message,
                provider=self.provider_type.value,
                original_error=error
            )
        elif "connection" in str(error).lower() or "timeout" in str(error).lower():
            return LLMConnectionError(
                message=error_message,
                provider=self.provider_type.value,
                original_error=error
            )
        else:
            return LLMError(
                message=error_message,
                provider=self.provider_type.value,
                original_error=error
            )