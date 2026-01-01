"""LLM Provider Factory for creating and managing provider instances."""

from typing import Dict, Any, Optional, List
import logging

from .base import BaseLLMProvider, LLMProviderType, LLMProviderConfig, LLMError
from .ollama_provider import OllamaProvider, OllamaConfig
from .openai_provider import OpenAIProvider, OpenAIConfig
from .anthropic_provider import AnthropicProvider, AnthropicConfig
from .azure_openai_provider import AzureOpenAIProvider, AzureOpenAIConfig
from .credential_manager import CredentialManager

logger = logging.getLogger(__name__)


class LLMProviderFactory:
    """Factory for creating and managing LLM provider instances."""
    
    def __init__(self, credential_manager: Optional[CredentialManager] = None):
        """Initialize provider factory.
        
        Args:
            credential_manager: Optional credential manager instance
        """
        self.credential_manager = credential_manager or CredentialManager()
        self._provider_cache: Dict[str, BaseLLMProvider] = {}
        self.logger = logging.getLogger(__name__)
        
        # Provider class mapping
        self._provider_classes = {
            LLMProviderType.OLLAMA: (OllamaProvider, OllamaConfig),
            LLMProviderType.OPENAI: (OpenAIProvider, OpenAIConfig),
            LLMProviderType.ANTHROPIC: (AnthropicProvider, AnthropicConfig),
            LLMProviderType.AZURE_OPENAI: (AzureOpenAIProvider, AzureOpenAIConfig)
        }
    
    async def create_provider(
        self, 
        provider_type: LLMProviderType,
        config: Optional[Dict[str, Any]] = None,
        credentials: Optional[Dict[str, Any]] = None,
        cache_key: Optional[str] = None
    ) -> BaseLLMProvider:
        """Create a new LLM provider instance.
        
        Args:
            provider_type: Type of LLM provider to create
            config: Provider configuration dictionary
            credentials: Provider credentials dictionary
            cache_key: Optional cache key for provider instance
            
        Returns:
            Initialized LLM provider instance
            
        Raises:
            LLMError: If provider creation fails
        """
        try:
            # Generate cache key if not provided
            if not cache_key:
                cache_key = self._generate_cache_key(provider_type)
            
            # Check cache first
            if cache_key in self._provider_cache:
                provider = self._provider_cache[cache_key]
                # Validate cached provider is still healthy
                if await self._validate_cached_provider(provider):
                    return provider
                else:
                    # Remove invalid provider from cache
                    del self._provider_cache[cache_key]
            
            # Get provider class and config class
            if provider_type not in self._provider_classes:
                raise LLMError(
                    message=f"Unsupported provider type: {provider_type.value}",
                    provider=provider_type.value,
                    error_code="UNSUPPORTED_PROVIDER"
                )
            
            provider_class, config_class = self._provider_classes[provider_type]
            
            # Create provider configuration
            provider_config = self._create_provider_config(config_class, config or {})
            
            # Get credentials
            if not credentials:
                credentials = await self.credential_manager.get_credentials(
                    provider_type
                )
            
            if not credentials:
                raise LLMError(
                    message=f"No credentials found for provider {provider_type.value}",
                    provider=provider_type.value,
                    error_code="MISSING_CREDENTIALS"
                )
            
            # Create provider instance
            provider = provider_class(provider_config, credentials)
            
            # Initialize provider
            await provider.initialize()
            
            # Validate credentials
            is_valid = await provider.validate_credentials()
            if not is_valid:
                raise LLMError(
                    message=f"Invalid credentials for provider {provider_type.value}",
                    provider=provider_type.value,
                    error_code="INVALID_CREDENTIALS"
                )
            
            # Update credential validation status
            await self.credential_manager.validate_and_update_credentials(
                provider_type, is_valid
            )
            
            # Cache provider instance
            self._provider_cache[cache_key] = provider
            
            self.logger.info(f"Created and cached provider {provider_type.value}")
            return provider
            
        except Exception as e:
            if isinstance(e, LLMError):
                raise e
            else:
                raise LLMError(
                    message=f"Failed to create provider {provider_type.value}: {str(e)}",
                    provider=provider_type.value,
                    error_code="PROVIDER_CREATION_ERROR",
                    original_error=e
                )
    
    async def get_provider(
        self, 
        provider_type: LLMProviderType
    ) -> Optional[BaseLLMProvider]:
        """Get cached provider instance.
        
        Args:
            provider_type: Type of LLM provider
            
        Returns:
            Cached provider instance or None if not found
        """
        cache_key = self._generate_cache_key(provider_type)
        
        if cache_key in self._provider_cache:
            provider = self._provider_cache[cache_key]
            # Validate cached provider is still healthy
            if await self._validate_cached_provider(provider):
                return provider
            else:
                # Remove invalid provider from cache
                del self._provider_cache[cache_key]
        
        return None
    
    async def get_or_create_provider(
        self, 
        provider_type: LLMProviderType,
        config: Optional[Dict[str, Any]] = None,
        credentials: Optional[Dict[str, Any]] = None
    ) -> BaseLLMProvider:
        """Get cached provider or create new one if not exists.
        
        Args:
            provider_type: Type of LLM provider
            config: Provider configuration dictionary
            credentials: Provider credentials dictionary
            
        Returns:
            LLM provider instance
        """
        # Try to get cached provider first
        provider = await self.get_provider(provider_type)
        
        if provider:
            return provider
        
        # Create new provider if not cached
        return await self.create_provider(
            provider_type, config, credentials
        )
    
    async def list_available_providers(
        self
    ) -> List[Dict[str, Any]]:
        """List all available providers with their status.
        
        Returns:
            List of provider information dictionaries
        """
        providers = []
        
        for provider_type in LLMProviderType:
            try:
                # Check if credentials exist
                credentials = await self.credential_manager.get_credentials(
                    provider_type
                )
                
                provider_info = {
                    "provider_type": provider_type.value,
                    "has_credentials": credentials is not None,
                    "status": "unknown"
                }
                
                # Try to get or create provider to check status
                if credentials:
                    try:
                        provider = await self.get_or_create_provider(
                            provider_type
                        )
                        health = await provider.health_check()
                        provider_info["status"] = health.get("status", "unknown")
                        provider_info["models"] = await provider.get_available_models()
                    except Exception as e:
                        provider_info["status"] = "error"
                        provider_info["error"] = str(e)
                
                providers.append(provider_info)
                
            except Exception as e:
                providers.append({
                    "provider_type": provider_type.value,
                    "has_credentials": False,
                    "status": "error",
                    "error": str(e)
                })
        
        return providers
    
    async def validate_all_providers(
        self
    ) -> Dict[str, bool]:
        """Validate all configured providers.
        
        Returns:
            Dictionary mapping provider types to validation status
        """
        validation_results = {}
        
        for provider_type in LLMProviderType:
            try:
                provider = await self.get_or_create_provider(
                    provider_type
                )
                is_valid = await provider.validate_credentials()
                validation_results[provider_type.value] = is_valid
                
                # Update credential validation status
                await self.credential_manager.validate_and_update_credentials(
                    provider_type, is_valid
                )
                
            except Exception as e:
                self.logger.error(f"Validation failed for {provider_type.value}: {e}")
                validation_results[provider_type.value] = False
        
        return validation_results
    
    def clear_cache(self, provider_type: Optional[LLMProviderType] = None):
        """Clear provider cache.
        
        Args:
            provider_type: Optional specific provider type to clear
        """
        if provider_type:
            # Clear specific provider type
            keys_to_remove = [
                key for key in self._provider_cache.keys() 
                if key.endswith(f":{provider_type.value}")
            ]
            for key in keys_to_remove:
                del self._provider_cache[key]
        else:
            # Clear all cached providers
            self._provider_cache.clear()
        
        self.logger.info(f"Cleared provider cache for {provider_type.value if provider_type else 'all providers'}")
    
    def _generate_cache_key(
        self, 
        provider_type: LLMProviderType
    ) -> str:
        """Generate cache key for provider instance.
        
        Args:
            provider_type: LLM provider type
            
        Returns:
            Cache key string
        """
        return provider_type.value
    
    def _create_provider_config(
        self, 
        config_class: type, 
        config_dict: Dict[str, Any]
    ) -> LLMProviderConfig:
        """Create provider configuration instance.
        
        Args:
            config_class: Configuration class
            config_dict: Configuration dictionary
            
        Returns:
            Provider configuration instance
        """
        try:
            return config_class(**config_dict)
        except Exception as e:
            raise LLMError(
                message=f"Invalid provider configuration: {str(e)}",
                provider="factory",
                error_code="INVALID_CONFIG",
                original_error=e
            )
    
    async def _validate_cached_provider(self, provider: BaseLLMProvider) -> bool:
        """Validate that cached provider is still healthy.
        
        Args:
            provider: Provider instance to validate
            
        Returns:
            True if provider is healthy, False otherwise
        """
        try:
            health = await provider.health_check()
            return health.get("status") == "healthy"
        except Exception:
            return False