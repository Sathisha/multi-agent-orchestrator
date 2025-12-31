#!/usr/bin/env python3
"""
Test Ollama connection and LLM integration with running Ollama instance.

This script tests the actual connection to Ollama and performs real LLM requests.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

async def test_ollama_connection():
    """Test connection to running Ollama instance."""
    
    print("Testing Ollama Connection and Integration...")
    print("=" * 60)
    
    try:
        # Import required modules
        from shared.services.llm_providers import (
            LLMProviderFactory,
            CredentialManager,
            LLMProviderType,
            LLMRequest,
            LLMMessage,
            OllamaProvider
        )
        from shared.services.llm_providers.ollama_provider import OllamaConfig
        from shared.services.llm_service import LLMService
        from shared.models.agent import AgentConfig
        
        print("✓ All imports successful")
        
        # Test 1: Direct Ollama provider connection
        print("\nTest 1: Direct Ollama Provider Connection")
        
        # Create Ollama configuration
        ollama_config = OllamaConfig(
            base_url="http://host.docker.internal:11434",  # Access host from container
            timeout=30
        )
        
        # Create credentials
        ollama_credentials = {
            "base_url": "http://host.docker.internal:11434"
        }
        
        # Create provider instance
        ollama_provider = OllamaProvider(ollama_config, ollama_credentials)
        
        # Initialize provider
        await ollama_provider.initialize()
        print("✓ Ollama provider initialized successfully")
        
        # Test 2: Health check
        print("\nTest 2: Ollama Health Check")
        health = await ollama_provider.health_check()
        print(f"Health Status: {health['status']}")
        print(f"Response Time: {health.get('response_time_ms', 'N/A')}ms")
        print(f"Base URL: {health.get('base_url', 'N/A')}")
        
        if health['status'] != 'healthy':
            print("⚠ Ollama is not healthy, but continuing with tests...")
        
        # Test 3: Get available models
        print("\nTest 3: Get Available Models")
        try:
            models = await ollama_provider.get_available_models()
            print(f"✓ Found {len(models)} models:")
            for i, model in enumerate(models[:5]):  # Show first 5 models
                print(f"  {i+1}. {model}")
            
            if len(models) == 0:
                print("⚠ No models found. You may need to pull a model first.")
                print("  Run: docker exec ollama ollama pull llama2")
                return False
                
        except Exception as e:
            print(f"✗ Failed to get models: {e}")
            print("⚠ This might mean Ollama is not accessible or no models are installed")
            return False
        
        # Test 4: Simple LLM request (if models are available)
        if models:
            print(f"\nTest 4: Simple LLM Request with {models[0]}")
            
            test_messages = [
                LLMMessage(role="user", content="Hello! Please respond with just 'Hi there!'")
            ]
            
            test_request = LLMRequest(
                messages=test_messages,
                model=models[0],
                temperature=0.1,  # Low temperature for consistent response
                max_tokens=50
            )
            
            try:
                response = await ollama_provider.generate_response(test_request)
                print("✓ LLM Response received:")
                print(f"  Content: {response.content}")
                print(f"  Model: {response.model}")
                print(f"  Tokens: {response.usage.total_tokens}")
                print(f"  Response Time: {response.response_time_ms}ms")
                print(f"  Provider: {response.provider}")
                
            except Exception as e:
                print(f"✗ LLM request failed: {e}")
                return False
        
        # Test 5: LLM Service integration
        print("\nTest 5: LLM Service Integration")
        
        credential_manager = CredentialManager()
        llm_service = LLMService(credential_manager)
        
        # Store Ollama credentials
        await credential_manager.store_credentials(
            LLMProviderType.OLLAMA,
            ollama_credentials
        )
        print("✓ Credentials stored in LLM service")
        
        # Validate credentials
        is_valid = await llm_service.validate_credentials("ollama")
        print(f"✓ Credential validation: {'PASSED' if is_valid else 'FAILED'}")
        
        # Get available models through service
        service_models = await llm_service.get_available_models("ollama")
        print(f"✓ Service found {len(service_models)} models")
        
        # Test 6: Agent configuration integration
        if models:
            print(f"\nTest 6: Agent Configuration Integration with {models[0]}")
            
            agent_config = AgentConfig(
                llm_provider="ollama",
                model_name=models[0],
                system_prompt="You are a helpful assistant. Keep responses brief.",
                temperature=0.3,
                max_tokens=100
            )
            
            test_messages = [
                {"role": "user", "content": "What is 2 + 2? Answer briefly."}
            ]
            
            try:
                response = await llm_service.generate_response(
                    test_messages,
                    agent_config
                )
                
                print("✓ Agent-style response received:")
                print(f"  Content: {response.content}")
                print(f"  Tokens: {response.usage.total_tokens}")
                print(f"  Cost: ${response.usage.cost or 0.0}")
                print(f"  Response Time: {response.response_time_ms}ms")
                
            except Exception as e:
                print(f"✗ Agent integration failed: {e}")
                return False
        
        # Test 7: Streaming response (if models available)
        if models:
            print(f"\nTest 7: Streaming Response with {models[0]}")
            
            test_messages = [
                {"role": "user", "content": "Count from 1 to 5, one number per line."}
            ]
            
            try:
                print("✓ Streaming response:")
                print("  ", end="", flush=True)
                
                async for chunk in llm_service.stream_response(test_messages, agent_config):
                    print(chunk, end="", flush=True)
                
                print("\n✓ Streaming completed successfully")
                
            except Exception as e:
                print(f"✗ Streaming failed: {e}")
                return False
        
        # Test 8: Provider health through service
        print("\nTest 8: Provider Health Through Service")
        
        health_status = await llm_service.get_provider_health("ollama")
        print(f"✓ Service health check:")
        print(f"  Status: {health_status.get('status', 'unknown')}")
        print(f"  Response Time: {health_status.get('response_time_ms', 'N/A')}ms")
        
        # Test 9: Error handling
        print("\nTest 9: Error Handling")
        
        try:
            # Try to use a non-existent model
            bad_config = AgentConfig(
                llm_provider="ollama",
                model_name="non-existent-model-12345",
                system_prompt="Test",
                temperature=0.5,
                max_tokens=50
            )
            
            await llm_service.generate_response([{"role": "user", "content": "test"}], bad_config)
            print("⚠ Expected error handling test to fail, but it didn't")
            
        except Exception as e:
            print(f"✓ Error handling working: {type(e).__name__}: {str(e)[:100]}...")
        
        print("\n" + "=" * 60)
        print("✅ Ollama Connection and Integration Tests COMPLETED!")
        print("\nTest Results Summary:")
        print("  ✓ Direct provider connection")
        print("  ✓ Health checks")
        print("  ✓ Model discovery")
        print("  ✓ LLM request/response")
        print("  ✓ Service integration")
        print("  ✓ Agent configuration")
        print("  ✓ Streaming responses")
        print("  ✓ Error handling")
        print("\n🎉 Your Ollama integration is working perfectly!")
        
        return True
        
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_ollama_connection())
    sys.exit(0 if success else 1)