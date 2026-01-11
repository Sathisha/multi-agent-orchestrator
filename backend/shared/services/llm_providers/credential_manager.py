"""Credential management for LLM providers."""

import os
import json
from datetime import datetime
from typing import Dict, Any, Optional
from cryptography.fernet import Fernet
from pydantic import BaseModel, Field
import logging

from .base import LLMProviderType, LLMError

logger = logging.getLogger(__name__)


class ProviderCredentials(BaseModel):
    """Provider credentials model."""
    
    provider_type: LLMProviderType = Field(..., description="Provider type")
    credentials: Dict[str, Any] = Field(..., description="Encrypted credentials")
    is_valid: bool = Field(False, description="Credentials validation status")
    last_validated: Optional[str] = Field(None, description="Last validation timestamp")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class CredentialManager:
    """Manages LLM provider credentials with encryption."""
    
    def __init__(self, encryption_key: Optional[str] = None):
        """Initialize credential manager.
        
        Args:
            encryption_key: Base64 encoded encryption key. If None, generates new key.
        """
        if encryption_key:
            self.encryption_key = encryption_key.encode()
        else:
            # Generate new key if not provided
            self.encryption_key = Fernet.generate_key()
        
        self.cipher = Fernet(self.encryption_key)
        self.logger = logging.getLogger(__name__)
        
        # In-memory credential cache
        self._credential_cache: Dict[str, ProviderCredentials] = {}
    
    def encrypt_credentials(self, credentials: Dict[str, Any]) -> str:
        """Encrypt credentials dictionary.
        
        Args:
            credentials: Raw credentials dictionary
            
        Returns:
            Encrypted credentials as base64 string
        """
        try:
            credentials_json = json.dumps(credentials)
            encrypted_data = self.cipher.encrypt(credentials_json.encode())
            return encrypted_data.decode()
        except Exception as e:
            raise LLMError(
                message=f"Failed to encrypt credentials: {str(e)}",
                provider="credential_manager",
                error_code="ENCRYPTION_ERROR"
            )
    
    def decrypt_credentials(self, encrypted_credentials: str) -> Dict[str, Any]:
        """Decrypt credentials string.
        
        Args:
            encrypted_credentials: Base64 encoded encrypted credentials
            
        Returns:
            Decrypted credentials dictionary
        """
        try:
            decrypted_data = self.cipher.decrypt(encrypted_credentials.encode())
            return json.loads(decrypted_data.decode())
        except Exception as e:
            raise LLMError(
                message=f"Failed to decrypt credentials: {str(e)}",
                provider="credential_manager",
                error_code="DECRYPTION_ERROR"
            )
    
    async def store_credentials(
        self, 
        provider_type: LLMProviderType, 
        credentials: Dict[str, Any]
    ) -> str:
        """Store encrypted credentials.
        
        Args:
            provider_type: LLM provider type
            credentials: Raw credentials dictionary
            
        Returns:
            Credential storage key
        """
        try:
            # Encrypt credentials
            encrypted_creds = self.encrypt_credentials(credentials)
            
            # Create credential record
            cred_record = ProviderCredentials(
                provider_type=provider_type,
                credentials={"encrypted": encrypted_creds},
                is_valid=False  # Will be validated separately
            )
            
            # Generate storage key
            storage_key = self._generate_storage_key(provider_type)
            
            # Store in cache (in production, this would be stored in database)
            self._credential_cache[storage_key] = cred_record
            
            self.logger.info(f"Stored credentials for provider {provider_type.value}")
            return storage_key
            
        except Exception as e:
            raise LLMError(
                message=f"Failed to store credentials: {str(e)}",
                provider=provider_type.value,
                error_code="STORAGE_ERROR"
            )
    
    async def get_credentials(
        self, 
        provider_type: LLMProviderType
    ) -> Optional[Dict[str, Any]]:
        """Retrieve and decrypt credentials.
        
        Args:
            provider_type: LLM provider type
            
        Returns:
            Decrypted credentials dictionary or None if not found
        """
        try:
            storage_key = self._generate_storage_key(provider_type)
            
            # Check cache first
            if storage_key in self._credential_cache:
                cred_record = self._credential_cache[storage_key]
                encrypted_creds = cred_record.credentials.get("encrypted")
                if encrypted_creds:
                    return self.decrypt_credentials(encrypted_creds)
            
            # Check environment variables as fallback
            env_creds = self._get_env_credentials(provider_type)
            if env_creds:
                self.logger.info(f"Using environment credentials for {provider_type.value}")
                return env_creds
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve credentials for {provider_type.value}: {e}")
            return None
    
    async def validate_and_update_credentials(
        self, 
        provider_type: LLMProviderType, 
        is_valid: bool
    ) -> None:
        """Update credential validation status.
        
        Args:
            provider_type: LLM provider type
            is_valid: Whether credentials are valid
        """
        storage_key = self._generate_storage_key(provider_type)
        
        if storage_key in self._credential_cache:
            cred_record = self._credential_cache[storage_key]
            cred_record.is_valid = is_valid
            cred_record.last_validated = str(datetime.utcnow())
            
            self.logger.info(
                f"Updated credential validation for {provider_type.value}: {is_valid}"
            )
    
    async def delete_credentials(
        self, 
        provider_type: LLMProviderType
    ) -> bool:
        """Delete stored credentials.
        
        Args:
            provider_type: LLM provider type
            
        Returns:
            True if credentials were deleted, False if not found
        """
        storage_key = self._generate_storage_key(provider_type)
        
        if storage_key in self._credential_cache:
            del self._credential_cache[storage_key]
            self.logger.info(f"Deleted credentials for {provider_type.value}")
            return True
        
        return False
    
    def _generate_storage_key(
        self, 
        provider_type: LLMProviderType
    ) -> str:
        """Generate storage key for credentials.
        
        Args:
            provider_type: LLM provider type
            
        Returns:
            Storage key string
        """
        return provider_type.value
    
    def _get_env_credentials(self, provider_type: LLMProviderType) -> Optional[Dict[str, Any]]:
        """Get credentials from environment variables.
        
        Args:
            provider_type: LLM provider type
            
        Returns:
            Credentials dictionary or None if not found
        """
        env_mapping = {
            LLMProviderType.OPENAI: {
                "api_key": "OPENAI_API_KEY",
                "organization": "OPENAI_ORGANIZATION"
            },
            LLMProviderType.ANTHROPIC: {
                "api_key": "ANTHROPIC_API_KEY"
            },
            LLMProviderType.AZURE_OPENAI: {
                "api_key": "AZURE_OPENAI_API_KEY",
                "endpoint": "AZURE_OPENAI_ENDPOINT",
                "api_version": "AZURE_OPENAI_API_VERSION"
            },
            LLMProviderType.OLLAMA: {
                "base_url": "OLLAMA_BASE_URL"
            },
            LLMProviderType.GOOGLE: {
                "api_key": ["GEMINI_API_KEY", "GOOGLE_API_KEY"]  # Support both env vars
            }
        }
        
        if provider_type not in env_mapping:
            return None
        
        credentials = {}
        for cred_key, env_var_config in env_mapping[provider_type].items():
            # Support both single env var and list of fallback env vars
            env_vars = env_var_config if isinstance(env_var_config, list) else [env_var_config]
            
            for env_var in env_vars:
                value = os.getenv(env_var)
                if value:
                    credentials[cred_key] = value
                    break  # Use first found value
        
        # Fallback for Ollama if not provided
        if provider_type == LLMProviderType.OLLAMA and "base_url" not in credentials:
            credentials["base_url"] = "http://ollama:11434"
            self.logger.info("Using default Ollama base URL: http://ollama:11434")
        
        # Return credentials only if we have at least one value
        return credentials if credentials else None
    
    def get_encryption_key(self) -> str:
        """Get the encryption key for backup/restore purposes.
        
        Returns:
            Base64 encoded encryption key
        """
        return self.encryption_key.decode()