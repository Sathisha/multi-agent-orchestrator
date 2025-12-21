"""LLM Service for managing LLM provider integrations."""

import asyncio
import time
from typing import Dict, List, Optional, Any, AsyncGenerator
from datetime import datetime
import logging

from .llm_providers import (
    LLMProviderFactory,
    CredentialManager,
    BaseLLMProvider,
    LLMRequest,
    LLMResponse,
    LLMMessage,
    LLMError,
    LLMProviderType,
    LLMConnectionError,
    LLMRateLimitError
)
from ..models.agent import LLMProvider, AgentConfig

logger = logging.getLogger(__name__)


class LLMService:
    """Service for managing LLM provider integrations and requests."""
    
    def __init__(self, credential_manager: Optional[CredentialManager] = None):
        """Initialize LLM service.
        
        Args:
            credential_manager: Optional credential manager instance
        """
        self.credential_manager = credential_manager or CredentialManager()
        self.provider_factory = LLMProviderFactory(self.credential_manager)
        self.logger = logging.getLogger(__name__)
        
        # Request tracking for rate limiting and monitoring
        self._request_stats: Dict[str, Dict[str, Any]] = {}
        
        # Fallback configuration
        self._fallback_enabled = True
        self._fallback_order = [
            LLMProviderType.OLLAMA,
            LLMProviderType.OPENAI,
            LLMProviderType.ANTHROPIC
        ]
    
    async def store_credentials(
        self,
        provider_type: str,
        credentials: Dict[str, Any],
        tenant_id: Optional[str] = None
    ) -> bool:
        """Store LLM provider credentials.
        
        Args:
            provider_type: LLM provider type string
            credentials: Credentials dictionary
            tenant_id: Optional tenant ID for multi-tenant deployments
            
        Returns:
            True if credentials stored successfully
            
        Raises:
            LLMError: If credential storage fails
        """
        try:
            # Convert string to enum
            provider_enum = LLMProviderType(provider_type)
            
            # Store encrypted credentials
            storage_key = await self.credential_manager.store_credentials(
                provider_enum, credentials, tenant_id
            )
            
            # Validate credentials by creating provider
            provider = await self.provider_factory.create_provider(
                provider_enum, tenant_id=tenant_id
            )
            
            is_valid = await provider.validate_credentials()
            
            # Update validation status
            await self.credential_manager.validate_and_update_credentials(
                provider_enum, is_valid, tenant_id
            )
            
            self.logger.info(f"Stored and validated credentials for {provider_type}")
            return is_valid
            
        except ValueError as e:
            raise LLMError(
                message=f"Invalid provider type: {provider_type}",
                provider=provider_type,
                error_code="INVALID_PROVIDER_TYPE"
            )
        except Exception as e:
            raise LLMError(
                message=f"Failed to store credentials: {str(e)}",
                provider=provider_type,
                error_code="CREDENTIAL_STORAGE_ERROR",
                original_error=e
            )
    
    async def validate_credentials(
        self,
        provider_type: str,
        tenant_id: Optional[str] = None
    ) -> bool:
        """Validate stored LLM provider credentials.
        
        Args:
            provider_type: LLM provider type string
            tenant_id: Optional tenant ID for multi-tenant deployments
            
        Returns:
            True if credentials are valid
        """
        try:
            provider_enum = LLMProviderType(provider_type)
            provider = await self.provider_factory.get_or_create_provider(
                provider_enum, tenant_id=tenant_id
            )
            
            is_valid = await provider.validate_credentials()
            
            # Update validation status
            await self.credential_manager.validate_and_update_credentials(
                provider_enum, is_valid, tenant_id
            )
            
            return is_valid
            
        except Exception as e:
            self.logger.error(f"Credential validation failed for {provider_type}: {e}")
            return False
    
    async def get_available_models(
        self,
        provider_type: str,
        tenant_id: Optional[str] = None
    ) -> List[str]:
        """Get available models for a provider.
        
        Args:
            provider_type: LLM provider type string
            tenant_id: Optional tenant ID for multi-tenant deployments
            
        Returns:
            List of available model names
            
        Raises:
            LLMError: If provider access fails
        """
        try:
            provider_enum = LLMProviderType(provider_type)
            provider = await self.provider_factory.get_or_create_provider(
                provider_enum, tenant_id=tenant_id
            )
            
            return await provider.get_available_models()
            
        except Exception as e:
            raise LLMError(
                message=f"Failed to get models for {provider_type}: {str(e)}",
                provider=provider_type,
                error_code="MODEL_LIST_ERROR",
                original_error=e
            )
    
    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        agent_config: AgentConfig,
        tenant_id: Optional[str] = None,
        stream: bool = False
    ) -> LLMResponse:
        """Generate response using configured LLM provider.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            agent_config: Agent configuration containing LLM settings
            tenant_id: Optional tenant ID for multi-tenant deployments
            stream: Whether to stream the response
            
        Returns:
            LLM response object
            
        Raises:
            LLMError: If response generation fails
        """
        start_time = time.time()
        
        try:
            # Convert messages to LLMMessage objects
            llm_messages = [
                LLMMessage(role=msg["role"], content=msg["content"])
                for msg in messages
            ]
            
            # Create LLM request
            request = LLMRequest(
                messages=llm_messages,
                model=agent_config.model_name,
                temperature=agent_config.temperature,
                max_tokens=agent_config.max_tokens,
                stream=stream
            )
            
            # Get provider - handle both enum and string values
            if hasattr(agent_config.llm_provider, 'value'):
                # It's an enum
                provider_enum = LLMProviderType(agent_config.llm_provider.value)
            else:
                # It's a string
                provider_enum = LLMProviderType(agent_config.llm_provider)
            
            provider = await self.provider_factory.get_or_create_provider(
                provider_enum, tenant_id=tenant_id
            )
            
            # Generate response with fallback
            response = await self._generate_with_fallback(
                request, provider, agent_config, tenant_id
            )
            
            # Track request statistics
            self._track_request_stats(
                provider_enum.value, 
                response.usage.total_tokens,
                time.time() - start_time,
                True
            )
            
            return response
            
        except Exception as e:
            # Track failed request - handle both enum and string values
            provider_value = agent_config.llm_provider
            if hasattr(provider_value, 'value'):
                provider_value = provider_value.value
            
            self._track_request_stats(
                provider_value,
                0,
                time.time() - start_time,
                False
            )
            
            if isinstance(e, LLMError):
                raise e
            else:
                provider_value = agent_config.llm_provider
                if hasattr(provider_value, 'value'):
                    provider_value = provider_value.value
                
                raise LLMError(
                    message=f"Failed to generate response: {str(e)}",
                    provider=provider_value,
                    error_code="RESPONSE_GENERATION_ERROR",
                    original_error=e
                )
    
    async def stream_response(
        self,
        messages: List[Dict[str, str]],
        agent_config: AgentConfig,
        tenant_id: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """Stream response using configured LLM provider.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            agent_config: Agent configuration containing LLM settings
            tenant_id: Optional tenant ID for multi-tenant deployments
            
        Yields:
            Response content chunks
            
        Raises:
            LLMError: If streaming fails
        """
        try:
            # Convert messages to LLMMessage objects
            llm_messages = [
                LLMMessage(role=msg["role"], content=msg["content"])
                for msg in messages
            ]
            
            # Create LLM request
            request = LLMRequest(
                messages=llm_messages,
                model=agent_config.model_name,
                temperature=agent_config.temperature,
                max_tokens=agent_config.max_tokens,
                stream=True
            )
            
            # Get provider - handle both enum and string values
            if hasattr(agent_config.llm_provider, 'value'):
                # It's an enum
                provider_enum = LLMProviderType(agent_config.llm_provider.value)
            else:
                # It's a string
                provider_enum = LLMProviderType(agent_config.llm_provider)
            
            provider = await self.provider_factory.get_or_create_provider(
                provider_enum, tenant_id=tenant_id
            )
            
            # Stream response
            async for chunk in provider.stream_response(request):
                yield chunk
                
        except Exception as e:
            if isinstance(e, LLMError):
                raise e
            else:
                raise LLMError(
                    message=f"Failed to stream response: {str(e)}",
                    provider=agent_config.llm_provider.value,
                    error_code="RESPONSE_STREAMING_ERROR",
                    original_error=e
                )
    
    async def get_provider_health(
        self,
        provider_type: Optional[str] = None,
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get health status for providers.
        
        Args:
            provider_type: Optional specific provider type to check
            tenant_id: Optional tenant ID for multi-tenant deployments
            
        Returns:
            Health status dictionary
        """
        if provider_type:
            # Check specific provider
            try:
                provider_enum = LLMProviderType(provider_type)
                provider = await self.provider_factory.get_or_create_provider(
                    provider_enum, tenant_id=tenant_id
                )
                return await provider.health_check()
            except Exception as e:
                return {
                    "status": "unhealthy",
                    "error": str(e),
                    "provider": provider_type
                }
        else:
            # Check all providers
            health_status = {}
            for provider_enum in LLMProviderType:
                try:
                    provider = await self.provider_factory.get_provider(
                        provider_enum, tenant_id
                    )
                    if provider:
                        health_status[provider_enum.value] = await provider.health_check()
                    else:
                        health_status[provider_enum.value] = {
                            "status": "not_configured",
                            "message": "Provider not configured"
                        }
                except Exception as e:
                    health_status[provider_enum.value] = {
                        "status": "unhealthy",
                        "error": str(e)
                    }
            
            return health_status
    
    async def list_providers(
        self, tenant_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List all available providers with their status.
        
        Args:
            tenant_id: Optional tenant ID for multi-tenant deployments
            
        Returns:
            List of provider information
        """
        return await self.provider_factory.list_available_providers(tenant_id)
    
    def get_request_statistics(self) -> Dict[str, Any]:
        """Get request statistics for monitoring.
        
        Returns:
            Request statistics dictionary
        """
        return dict(self._request_stats)
    
    async def _generate_with_fallback(
        self,
        request: LLMRequest,
        primary_provider: BaseLLMProvider,
        agent_config: AgentConfig,
        tenant_id: Optional[str] = None
    ) -> LLMResponse:
        """Generate response with fallback to other providers.
        
        Args:
            request: LLM request object
            primary_provider: Primary provider to try first
            agent_config: Agent configuration
            tenant_id: Optional tenant ID
            
        Returns:
            LLM response object
            
        Raises:
            LLMError: If all providers fail
        """
        errors = []
        
        # Try primary provider first
        try:
            return await primary_provider.generate_response(request)
        except (LLMConnectionError, LLMRateLimitError) as e:
            errors.append(f"{primary_provider.provider_type.value}: {str(e)}")
            self.logger.warning(f"Primary provider failed: {e}")
        except Exception as e:
            # For other errors, don't try fallback
            raise e
        
        # Try fallback providers if enabled
        if not self._fallback_enabled:
            raise LLMError(
                message=f"Primary provider failed and fallback disabled: {errors[0]}",
                provider=primary_provider.provider_type.value,
                error_code="PRIMARY_PROVIDER_FAILED"
            )
        
        # Try fallback providers
        for fallback_type in self._fallback_order:
            if fallback_type == primary_provider.provider_type:
                continue  # Skip primary provider
            
            try:
                fallback_provider = await self.provider_factory.get_provider(
                    fallback_type, tenant_id
                )
                
                if not fallback_provider:
                    continue  # Skip if not configured
                
                # Adjust request for fallback provider
                fallback_request = self._adjust_request_for_provider(
                    request, fallback_type
                )
                
                response = await fallback_provider.generate_response(fallback_request)
                
                # Add fallback metadata
                response.metadata["fallback_used"] = True
                response.metadata["primary_provider"] = primary_provider.provider_type.value
                response.metadata["fallback_provider"] = fallback_type.value
                
                self.logger.info(f"Fallback successful: {fallback_type.value}")
                return response
                
            except Exception as e:
                errors.append(f"{fallback_type.value}: {str(e)}")
                self.logger.warning(f"Fallback provider {fallback_type.value} failed: {e}")
                continue
        
        # All providers failed
        raise LLMError(
            message=f"All providers failed: {'; '.join(errors)}",
            provider="fallback_system",
            error_code="ALL_PROVIDERS_FAILED"
        )
    
    def _adjust_request_for_provider(
        self, 
        request: LLMRequest, 
        provider_type: LLMProviderType
    ) -> LLMRequest:
        """Adjust request parameters for specific provider.
        
        Args:
            request: Original request
            provider_type: Target provider type
            
        Returns:
            Adjusted request
        """
        # Create a copy of the request
        adjusted_request = LLMRequest(
            messages=request.messages,
            model=request.model,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            stream=request.stream,
            tools=request.tools,
            metadata=request.metadata
        )
        
        # Adjust model name for different providers
        if provider_type == LLMProviderType.OLLAMA:
            # Use a default Ollama model
            adjusted_request.model = "llama2"
        elif provider_type == LLMProviderType.OPENAI:
            # Use a default OpenAI model
            adjusted_request.model = "gpt-3.5-turbo"
        elif provider_type == LLMProviderType.ANTHROPIC:
            # Use a default Anthropic model
            adjusted_request.model = "claude-3-haiku-20240307"
        
        return adjusted_request
    
    def _track_request_stats(
        self,
        provider: str,
        tokens: int,
        duration: float,
        success: bool
    ) -> None:
        """Track request statistics.
        
        Args:
            provider: Provider name
            tokens: Number of tokens used
            duration: Request duration in seconds
            success: Whether request was successful
        """
        if provider not in self._request_stats:
            self._request_stats[provider] = {
                "total_requests": 0,
                "successful_requests": 0,
                "failed_requests": 0,
                "total_tokens": 0,
                "total_duration": 0.0,
                "average_duration": 0.0,
                "last_request": None
            }
        
        stats = self._request_stats[provider]
        stats["total_requests"] += 1
        stats["total_tokens"] += tokens
        stats["total_duration"] += duration
        stats["average_duration"] = stats["total_duration"] / stats["total_requests"]
        stats["last_request"] = datetime.utcnow().isoformat()
        
        if success:
            stats["successful_requests"] += 1
        else:
            stats["failed_requests"] += 1