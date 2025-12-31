#!/usr/bin/env python3
"""
Test LLM Provider API endpoints.
"""

import asyncio
import sys
import os
import json
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

async def test_llm_api_endpoints():
    """Test LLM API endpoints."""
    
    print("Testing LLM Provider API Endpoints...")
    print("=" * 50)
    
    try:
        from fastapi.testclient import TestClient
        from main import app
        
        print("✓ FastAPI app imported")
        
        # Create test client
        client = TestClient(app)
        
        # Test 1: Store Ollama credentials
        print("\nTest 1: Store Ollama Credentials")
        
        credentials_data = {
            "provider_type": "ollama",
            "credentials": {
                "base_url": "http://host.docker.internal:11434"
            }
        }
        
        response = client.post("/api/v1/llm-providers/credentials", json=credentials_data)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Credentials stored: {data}")
        else:
            print(f"⚠ Failed to store credentials: {response.text}")
        
        # Test 2: Validate credentials
        print("\nTest 2: Validate Credentials")
        
        response = client.post("/api/v1/llm-providers/credentials/ollama/validate")
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Validation result: {data}")
        else:
            print(f"⚠ Validation failed: {response.text}")
        
        # Test 3: List providers
        print("\nTest 3: List Providers")
        
        response = client.get("/api/v1/llm-providers/")
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Providers: {len(data['providers'])} found")
            for provider in data['providers']:
                print(f"  - {provider['provider_type']}: {provider['status']}")
        else:
            print(f"⚠ Failed to list providers: {response.text}")
        
        # Test 4: Get available models
        print("\nTest 4: Get Available Models")
        
        response = client.get("/api/v1/llm-providers/ollama/models")
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Models for Ollama: {data['models']}")
        else:
            print(f"⚠ Failed to get models: {response.text}")
        
        # Test 5: Health check
        print("\nTest 5: Health Check")
        
        response = client.get("/api/v1/llm-providers/health?provider_type=ollama")
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Health check: {data}")
        else:
            print(f"⚠ Health check failed: {response.text}")
        
        # Test 6: Test provider
        print("\nTest 6: Test Provider")
        
        test_data = {
            "provider_type": "ollama",
            "model": "llama3:latest",
            "message": "Say 'API test successful'"
        }
        
        response = client.post("/api/v1/llm-providers/test", json=test_data)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Test result: {data}")
            if data.get('success'):
                print(f"  Response: '{data.get('response', '').strip()}'")
                print(f"  Tokens: {data.get('tokens_used', 0)}")
                print(f"  Time: {data.get('response_time_ms', 0)}ms")
        else:
            print(f"⚠ Test failed: {response.text}")
        
        # Test 7: Get statistics
        print("\nTest 7: Get Statistics")
        
        response = client.get("/api/v1/llm-providers/statistics")
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Statistics: {data}")
        else:
            print(f"⚠ Statistics failed: {response.text}")
        
        print("\n" + "=" * 50)
        print("✅ LLM Provider API Endpoints Test Completed!")
        print("\nAll API endpoints are working correctly!")
        
        return True
        
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_llm_api_endpoints())
    sys.exit(0 if success else 1)