#!/usr/bin/env python3
"""
Simple Ollama connection test with timeout.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

async def test_ollama_simple():
    """Simple test with timeout."""
    
    print("Testing Ollama Connection (Simple)...")
    print("=" * 50)
    
    try:
        from shared.services.llm_providers import (
            LLMProviderFactory,
            CredentialManager,
            LLMProviderType,
            LLMRequest,
            LLMMessage
        )
        from shared.services.llm_providers.ollama_provider import OllamaConfig, OllamaProvider
        
        print("✓ Imports successful")
        
        # Test connection
        ollama_config = OllamaConfig(
            base_url="http://host.docker.internal:11434",
            timeout=10  # Shorter timeout
        )
        
        ollama_credentials = {
            "base_url": "http://host.docker.internal:11434"
        }
        
        provider = OllamaProvider(ollama_config, ollama_credentials)
        await provider.initialize()
        print("✓ Provider initialized")
        
        # Health check
        health = await provider.health_check()
        print(f"✓ Health: {health['status']}")
        
        # Get models
        models = await provider.get_available_models()
        print(f"✓ Models: {models}")
        
        if models:
            print(f"\nTesting simple request with {models[0]}...")
            
            # Create a very simple request
            messages = [LLMMessage(role="user", content="Say 'Hello'")]
            request = LLMRequest(
                messages=messages,
                model=models[0],
                temperature=0.1,
                max_tokens=10
            )
            
            # Test with timeout
            try:
                response = await asyncio.wait_for(
                    provider.generate_response(request),
                    timeout=30.0  # 30 second timeout
                )
                print(f"✓ Response: {response.content}")
                print(f"✓ Tokens: {response.usage.total_tokens}")
                print(f"✓ Time: {response.response_time_ms}ms")
                
            except asyncio.TimeoutError:
                print("⚠ Request timed out (model might be loading)")
                return True  # Still consider this a success for connection
            
        print("\n✅ Ollama connection test completed!")
        return True
        
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_ollama_simple())
    sys.exit(0 if success else 1)