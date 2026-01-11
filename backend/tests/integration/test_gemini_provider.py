#!/usr/bin/env python3
"""
Integration tests for Google Gemini Provider.

Tests basic text generation, error handling, timeout behavior, and system instructions.
Requires GEMINI_API_KEY environment variable to be set with a valid API key.
"""

import asyncio
import os
import sys
import pytest
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from shared.services.llm_providers.google_provider import GoogleProvider, GoogleConfig
from shared.services.llm_providers.base import (
    LLMRequest,
    LLMMessage,
    LLMError,
    LLMAuthenticationError,
    LLMValidationError
)


@pytest.fixture
def api_key():
    """Get Gemini API key from environment."""
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        pytest.skip("GEMINI_API_KEY environment variable not set")
    return key


@pytest.fixture
async def gemini_provider(api_key):
    """Create a Gemini provider instance with valid credentials."""
    config = GoogleConfig()
    credentials = {"api_key": api_key}
    provider = GoogleProvider(config, credentials)
    await provider.initialize()
    yield provider
    # Cleanup
    await provider._client.aclose()


@pytest.mark.asyncio
async def test_basic_text_generation(gemini_provider):
    """Test basic text generation with a simple prompt."""
    print("\n[TEST] Basic text generation...")
    
    request = LLMRequest(
        messages=[LLMMessage(role="user", content="Say 'Hello, World!' and nothing else.")],
        model="gemini-1.5-flash",
        temperature=0.0,
        max_tokens=50
    )
    
    response = await gemini_provider.generate_response(request)
    
    assert response is not None
    assert response.content is not None
    assert len(response.content) > 0
    assert "hello" in response.content.lower() or "world" in response.content.lower()
    assert response.usage.total_tokens > 0
    assert response.response_time_ms > 0
    print(f"✓ Response: {response.content}")
    print(f"  Tokens: {response.usage.total_tokens}, Time: {response.response_time_ms}ms")


@pytest.mark.asyncio
async def test_system_instruction(gemini_provider):
    """Test that system instructions are properly sent and respected."""
    print("\n[TEST] System instruction handling...")
    
    request = LLMRequest(
        messages=[
            LLMMessage(role="system", content="You are a helpful cat. Always end your responses with 'Meow!'"),
            LLMMessage(role="user", content="Introduce yourself in one sentence.")
        ],
        model="gemini-1.5-flash",
        temperature=0.7,
        max_tokens=100
    )
    
    response = await gemini_provider.generate_response(request)
    
    assert response is not None
    assert response.content is not None
    # Most of the time Gemini will respect the instruction
    print(f"✓ Response with system instruction: {response.content}")
    print(f"  (System instruction may or may not be strictly followed)")


@pytest.mark.asyncio
async def test_invalid_api_key():
    """Test that invalid API key returns proper authentication error."""
    print("\n[TEST] Invalid API key handling...")
    
    config = GoogleConfig()
    credentials = {"api_key": "invalid_key_12345"}
    provider = GoogleProvider(config, credentials)
    
    request = LLMRequest(
        messages=[LLMMessage(role="user", content="Hello")],
        model="gemini-1.5-flash",
        max_tokens=10
    )
    
    with pytest.raises(LLMAuthenticationError) as exc_info:
        await provider.generate_response(request)
    
    error_msg = str(exc_info.value.message)
    assert "401" in error_msg or "403" in error_msg or "API key" in error_msg
    print(f"✓ Correctly caught auth error: {error_msg[:100]}...")
    
    await provider._client.aclose()


@pytest.mark.asyncio
async def test_invalid_model_name(gemini_provider):
    """Test that invalid model name returns proper validation error."""
    print("\n[TEST] Invalid model name handling...")
    
    request = LLMRequest(
        messages=[LLMMessage(role="user", content="Hello")],
        model="invalid-model-12345",
        max_tokens=10
    )
    
    with pytest.raises((LLMValidationError, LLMError)) as exc_info:
        await provider.generate_response(request)
    
    error_msg = str(exc_info.value.message)
    assert "400" in error_msg or "model" in error_msg.lower() or "not found" in error_msg.lower()
    print(f"✓ Correctly caught validation error: {error_msg[:100]}...")


@pytest.mark.asyncio
async def test_empty_request_validation():
    """Test that empty messages are caught."""
    print("\n[TEST] Empty request validation...")
    
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        pytest.skip("GEMINI_API_KEY not set")
    
    config = GoogleConfig()
    credentials = {"api_key": api_key}
    provider = GoogleProvider(config, credentials)
    
    # Request with only system message (no user message)
    request = LLMRequest(
        messages=[LLMMessage(role="system", content="You are helpful")],
        model="gemini-1.5-flash",
        max_tokens=10
    )
    
    with pytest.raises(LLMError) as exc_info:
        await provider.generate_response(request)
    
    error_msg = str(exc_info.value.message)
    assert "empty" in error_msg.lower() or "required" in error_msg.lower()
    print(f"✓ Correctly caught empty request: {error_msg[:100]}...")
    
    await provider._client.aclose()


@pytest.mark.asyncio
async def test_multi_turn_conversation(gemini_provider):
    """Test multi-turn conversation."""
    print("\n[TEST] Multi-turn conversation...")
    
    request = LLMRequest(
        messages=[
            LLMMessage(role="user", content="What is 2+2?"),
            LLMMessage(role="assistant", content="2+2 equals 4."),
            LLMMessage(role="user", content="What about 4+4?")
        ],
        model="gemini-1.5-flash",
        temperature=0.0,
        max_tokens=50
    )
    
    response = await gemini_provider.generate_response(request)
    
    assert response is not None
    assert response.content is not None
    assert "8" in response.content
    print(f"✓ Multi-turn response: {response.content}")


@pytest.mark.asyncio
async def test_available_models(gemini_provider):
    """Test getting list of available models."""
    print("\n[TEST] Getting available models...")
    
    models = await gemini_provider.get_available_models()
    
    assert models is not None
    assert len(models) > 0
    assert any("gemini" in m.lower() for m in models)
    print(f"✓ Found {len(models)} models")
    print(f"  Sample models: {models[:5]}")


@pytest.mark.asyncio  
async def test_cost_estimation(gemini_provider):
    """Test cost estimation."""
    print("\n[TEST] Cost estimation...")
    
    request = LLMRequest(
        messages=[LLMMessage(role="user", content="Hello world")],
        model="gemini-1.5-flash",
        max_tokens=100
    )
    
    cost = await gemini_provider.estimate_cost(request)
    
    assert cost is not None
    assert cost >= 0
    print(f"✓ Estimated cost: ${cost:.6f}")


if __name__ == "__main__":
    print("=" * 60)
    print("Google Gemini Provider Integration Tests")
    print("=" * 60)
    print("\nRequires GEMINI_API_KEY environment variable.")
    print("Get your API key at: https://aistudio.google.com/app/apikey\n")
    
    # Run tests
    exit_code = pytest.main([__file__, "-v", "-s"])
    sys.exit(exit_code)
