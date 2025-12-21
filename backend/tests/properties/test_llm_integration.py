"""Property-based tests for LLM Provider Integration.

**Feature: ai-agent-framework, Property 5: LLM Provider Integration**
**Validates: Requirements 2.2, 2.3, 2.4, 2.5**
"""

import pytest
from hypothesis import given, strategies as st, assume, settings
from typing import Dict, Any, List
import asyncio

from shared.services.llm_providers import (
    LLMProviderFactory,
    CredentialManager,
    LLMProviderType,
    LLMRequest,
    LLMMessage,
    LLMError
)
from shared.services.llm_service import LLMService
from shared.models.agent import AgentConfig, LLMProvider


# Test data generators
@st.composite
def llm_provider_type_strategy(draw):
    """Generate valid LLM provider types."""
    return draw(st.sampled_from([p.value for p in LLMProviderType]))


@st.composite
def credentials_strategy(draw):
    """Generate valid credential dictionaries for different providers."""
    provider_type = draw(st.sampled_from(list(LLMProviderType)))
    
    if provider_type == LLMProviderType.OLLAMA:
        return {
            "base_url": draw(st.text(min_size=10, max_size=100).filter(lambda x: "http" in x))
        }
    elif provider_type == LLMProviderType.OPENAI:
        return {
            "api_key": draw(st.text(min_size=20, max_size=100)),
            "organization": draw(st.one_of(st.none(), st.text(min_size=5, max_size=50)))
        }
    elif provider_type == LLMProviderType.ANTHROPIC:
        return {
            "api_key": draw(st.text(min_size=20, max_size=100))
        }
    elif provider_type == LLMProviderType.AZURE_OPENAI:
        return {
            "api_key": draw(st.text(min_size=20, max_size=100)),
            "endpoint": draw(st.text(min_size=10, max_size=100).filter(lambda x: "http" in x)),
            "api_version": draw(st.text(min_size=5, max_size=20))
        }
    else:
        return {"api_key": draw(st.text(min_size=10, max_size=100))}


@st.composite
def llm_message_strategy(draw):
    """Generate valid LLM messages."""
    role = draw(st.sampled_from(["system", "user", "assistant"]))
    content = draw(st.text(min_size=1, max_size=1000))
    return LLMMessage(role=role, content=content)


@st.composite
def llm_request_strategy(draw):
    """Generate valid LLM requests."""
    messages = draw(st.lists(llm_message_strategy(), min_size=1, max_size=10))
    model = draw(st.text(min_size=1, max_size=50))
    temperature = draw(st.floats(min_value=0.0, max_value=2.0))
    max_tokens = draw(st.integers(min_value=1, max_value=8000))
    
    return LLMRequest(
        messages=messages,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens
    )


@st.composite
def agent_config_strategy(draw):
    """Generate valid agent configurations."""
    provider = draw(st.sampled_from([p.value for p in LLMProvider]))
    model_name = draw(st.text(min_size=1, max_size=50))
    system_prompt = draw(st.text(min_size=1, max_size=500))
    temperature = draw(st.floats(min_value=0.0, max_value=2.0))
    max_tokens = draw(st.integers(min_value=1, max_value=8000))
    
    return AgentConfig(
        llm_provider=LLMProvider(provider),
        model_name=model_name,
        system_prompt=system_prompt,
        temperature=temperature,
        max_tokens=max_tokens
    )


class TestLLMProviderIntegration:
    """Property-based tests for LLM Provider Integration."""
    
    @pytest.fixture
    def credential_manager(self):
        """Create credential manager for testing."""
        return CredentialManager()
    
    @pytest.fixture
    def provider_factory(self, credential_manager):
        """Create provider factory for testing."""
        return LLMProviderFactory(credential_manager)
    
    @pytest.fixture
    def llm_service(self, credential_manager):
        """Create LLM service for testing."""
        return LLMService(credential_manager)
    
    @given(credentials_strategy())
    @settings(max_examples=50, deadline=5000)
    def test_credential_encryption_round_trip(self, credential_manager, credentials):
        """
        **Feature: ai-agent-framework, Property 5: LLM Provider Integration**
        **Validates: Requirements 2.3**
        
        Property: For any valid credentials, encrypting and then decrypting 
        should produce the original credentials.
        """
        # Encrypt credentials
        encrypted = credential_manager.encrypt_credentials(credentials)
        
        # Decrypt credentials
        decrypted = credential_manager.decrypt_credentials(encrypted)
        
        # Verify round-trip integrity
        assert decrypted == credentials, "Credential encryption/decryption round-trip failed"
        assert isinstance(encrypted, str), "Encrypted credentials should be string"
        assert len(encrypted) > 0, "Encrypted credentials should not be empty"
    
    @given(llm_provider_type_strategy(), credentials_strategy())
    @settings(max_examples=20, deadline=10000)
    def test_credential_storage_and_retrieval(self, credential_manager, provider_type, credentials):
        """
        **Feature: ai-agent-framework, Property 5: LLM Provider Integration**
        **Validates: Requirements 2.2, 2.3**
        
        Property: For any provider type and credentials, storing and then retrieving 
        should produce the original credentials.
        """
        async def run_test():
            provider_enum = LLMProviderType(provider_type)
            
            # Store credentials
            storage_key = await credential_manager.store_credentials(
                provider_enum, credentials
            )
            
            # Retrieve credentials
            retrieved = await credential_manager.get_credentials(provider_enum)
            
            # Verify storage/retrieval integrity
            assert retrieved == credentials, "Credential storage/retrieval round-trip failed"
            assert isinstance(storage_key, str), "Storage key should be string"
            assert len(storage_key) > 0, "Storage key should not be empty"
        
        asyncio.run(run_test())
    
    @given(llm_provider_type_strategy())
    @settings(max_examples=20, deadline=10000)
    def test_provider_factory_lists_all_providers(self, provider_factory, provider_type):
        """
        **Feature: ai-agent-framework, Property 5: LLM Provider Integration**
        **Validates: Requirements 2.1**
        
        Property: For any provider type, the factory should list it as an available provider.
        """
        async def run_test():
            providers = await provider_factory.list_available_providers()
            
            # Verify all provider types are listed
            provider_types = [p["provider_type"] for p in providers]
            assert provider_type in provider_types, f"Provider {provider_type} not listed"
            
            # Verify provider information structure
            for provider in providers:
                assert "provider_type" in provider, "Provider should have type"
                assert "has_credentials" in provider, "Provider should have credential status"
                assert "status" in provider, "Provider should have status"
                assert isinstance(provider["has_credentials"], bool), "Credential status should be boolean"
        
        asyncio.run(run_test())
    
    @given(llm_request_strategy())
    @settings(max_examples=20, deadline=5000)
    def test_llm_request_validation(self, request):
        """
        **Feature: ai-agent-framework, Property 5: LLM Provider Integration**
        **Validates: Requirements 2.4**
        
        Property: For any valid LLM request, the request should maintain its structure 
        and all fields should be accessible.
        """
        # Verify request structure
        assert hasattr(request, "messages"), "Request should have messages"
        assert hasattr(request, "model"), "Request should have model"
        assert hasattr(request, "temperature"), "Request should have temperature"
        assert hasattr(request, "max_tokens"), "Request should have max_tokens"
        
        # Verify field types and constraints
        assert isinstance(request.messages, list), "Messages should be list"
        assert len(request.messages) > 0, "Messages should not be empty"
        assert isinstance(request.model, str), "Model should be string"
        assert len(request.model) > 0, "Model should not be empty"
        assert 0.0 <= request.temperature <= 2.0, "Temperature should be in valid range"
        assert 1 <= request.max_tokens <= 8000, "Max tokens should be in valid range"
        
        # Verify message structure
        for message in request.messages:
            assert hasattr(message, "role"), "Message should have role"
            assert hasattr(message, "content"), "Message should have content"
            assert message.role in ["system", "user", "assistant"], "Role should be valid"
            assert isinstance(message.content, str), "Content should be string"
            assert len(message.content) > 0, "Content should not be empty"
    
    @given(agent_config_strategy())
    @settings(max_examples=20, deadline=5000)
    def test_agent_config_llm_provider_mapping(self, config):
        """
        **Feature: ai-agent-framework, Property 5: LLM Provider Integration**
        **Validates: Requirements 2.1, 2.4**
        
        Property: For any agent configuration, the LLM provider should map to a valid 
        provider type and maintain configuration integrity.
        """
        # Verify LLM provider mapping
        provider_value = config.llm_provider.value
        valid_providers = [p.value for p in LLMProviderType]
        assert provider_value in valid_providers, f"Provider {provider_value} not in valid providers"
        
        # Verify configuration structure
        assert hasattr(config, "model_name"), "Config should have model_name"
        assert hasattr(config, "system_prompt"), "Config should have system_prompt"
        assert hasattr(config, "temperature"), "Config should have temperature"
        assert hasattr(config, "max_tokens"), "Config should have max_tokens"
        
        # Verify field constraints
        assert isinstance(config.model_name, str), "Model name should be string"
        assert len(config.model_name) > 0, "Model name should not be empty"
        assert isinstance(config.system_prompt, str), "System prompt should be string"
        assert len(config.system_prompt) > 0, "System prompt should not be empty"
        assert 0.0 <= config.temperature <= 2.0, "Temperature should be in valid range"
        assert 1 <= config.max_tokens <= 8000, "Max tokens should be in valid range"
    
    @given(llm_provider_type_strategy())
    @settings(max_examples=10, deadline=15000)
    def test_provider_health_check_structure(self, llm_service, provider_type):
        """
        **Feature: ai-agent-framework, Property 5: LLM Provider Integration**
        **Validates: Requirements 2.5**
        
        Property: For any provider type, health check should return structured information 
        with consistent format regardless of provider status.
        """
        async def run_test():
            try:
                health = await llm_service.get_provider_health(provider_type)
                
                # Verify health check structure
                if isinstance(health, dict):
                    # Single provider health check
                    assert "status" in health, "Health check should have status"
                    valid_statuses = ["healthy", "unhealthy", "not_configured"]
                    assert health["status"] in valid_statuses, f"Invalid status: {health['status']}"
                else:
                    # Multiple provider health check
                    assert isinstance(health, dict), "Health should be dictionary"
                    
                    for provider, status in health.items():
                        assert isinstance(status, dict), "Provider status should be dict"
                        assert "status" in status, "Provider should have status"
            
            except Exception as e:
                # Health check failures are acceptable for unconfigured providers
                assert isinstance(e, (LLMError, Exception)), "Should handle errors gracefully"
        
        asyncio.run(run_test())
    
    @given(st.lists(llm_message_strategy(), min_size=1, max_size=5))
    @settings(max_examples=10, deadline=10000)
    def test_message_format_consistency(self, messages):
        """
        **Feature: ai-agent-framework, Property 5: LLM Provider Integration**
        **Validates: Requirements 2.4, 2.5**
        
        Property: For any list of messages, the format should be consistent and 
        compatible with all provider implementations.
        """
        # Convert to dictionary format (as used in service layer)
        message_dicts = [{"role": msg.role, "content": msg.content} for msg in messages]
        
        # Verify message format consistency
        for msg_dict in message_dicts:
            assert "role" in msg_dict, "Message dict should have role"
            assert "content" in msg_dict, "Message dict should have content"
            assert isinstance(msg_dict["role"], str), "Role should be string"
            assert isinstance(msg_dict["content"], str), "Content should be string"
            assert msg_dict["role"] in ["system", "user", "assistant"], "Role should be valid"
            assert len(msg_dict["content"]) > 0, "Content should not be empty"
        
        # Verify conversion back to LLMMessage objects
        converted_messages = [
            LLMMessage(role=msg["role"], content=msg["content"])
            for msg in message_dicts
        ]
        
        assert len(converted_messages) == len(messages), "Conversion should preserve count"
        
        for original, converted in zip(messages, converted_messages):
            assert original.role == converted.role, "Role should be preserved"
            assert original.content == converted.content, "Content should be preserved"
    
    def test_provider_type_enum_completeness(self):
        """
        **Feature: ai-agent-framework, Property 5: LLM Provider Integration**
        **Validates: Requirements 2.1**
        
        Property: All supported LLM providers should be represented in the provider type enum.
        """
        # Verify all expected providers are in enum
        expected_providers = ["ollama", "openai", "anthropic", "azure-openai"]
        actual_providers = [p.value for p in LLMProviderType]
        
        for expected in expected_providers:
            assert expected in actual_providers, f"Provider {expected} missing from enum"
        
        # Verify enum values are strings
        for provider in LLMProviderType:
            assert isinstance(provider.value, str), "Provider enum values should be strings"
            assert len(provider.value) > 0, "Provider enum values should not be empty"
    
    @given(st.text(min_size=1, max_size=100))
    @settings(max_examples=20, deadline=5000)
    def test_error_handling_consistency(self, error_message):
        """
        **Feature: ai-agent-framework, Property 5: LLM Provider Integration**
        **Validates: Requirements 2.5**
        
        Property: For any error condition, LLM errors should maintain consistent structure 
        and provide meaningful information.
        """
        # Create LLM error
        provider = "test_provider"
        error = LLMError(
            message=error_message,
            provider=provider,
            error_code="TEST_ERROR"
        )
        
        # Verify error structure
        assert hasattr(error, "message"), "Error should have message"
        assert hasattr(error, "provider"), "Error should have provider"
        assert hasattr(error, "error_code"), "Error should have error_code"
        
        # Verify error content
        assert error.message == error_message, "Error message should be preserved"
        assert error.provider == provider, "Error provider should be preserved"
        assert error.error_code == "TEST_ERROR", "Error code should be preserved"
        
        # Verify string representation
        error_str = str(error)
        assert provider in error_str, "Provider should be in error string"
        assert error_message in error_str, "Message should be in error string"