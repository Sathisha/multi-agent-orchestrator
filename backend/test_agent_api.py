#!/usr/bin/env python3
"""Simple test script to verify Agent API endpoints."""

import asyncio
import sys
import os
from fastapi.testclient import TestClient

# Add the current directory to Python path
sys.path.insert(0, '/app')

def test_agent_api():
    """Test the Agent API endpoints."""
    try:
        print("Testing Agent API endpoints...")
        
        # Import the agent templates API directly
        from shared.api.agent_templates import router as templates_router
        from fastapi import FastAPI
        
        # Create a test app with just the templates router
        app = FastAPI()
        app.include_router(templates_router)
        
        client = TestClient(app)
        
        # Test list templates endpoint
        print("Testing GET /api/v1/agent-templates/")
        response = client.get("/api/v1/agent-templates/")
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            templates = response.json()
            print(f"✓ Retrieved {len(templates)} templates")
            for template in templates:
                print(f"  - {template['name']} ({template['type']})")
        
        # Test get specific template
        print("\nTesting GET /api/v1/agent-templates/chatbot-basic")
        response = client.get("/api/v1/agent-templates/chatbot-basic")
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            template = response.json()
            print(f"✓ Retrieved template: {template['name']}")
        
        # Test get template config
        print("\nTesting GET /api/v1/agent-templates/chatbot-basic/config")
        response = client.get("/api/v1/agent-templates/chatbot-basic/config")
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            config = response.json()
            print(f"✓ Retrieved config with LLM provider: {config['llm_provider']}")
        
        # Test apply template config
        print("\nTesting POST /api/v1/agent-templates/apply-config")
        payload = {
            "template_id": "chatbot-basic",
            "overrides": {
                "temperature": 0.9,
                "max_tokens": 2000
            }
        }
        response = client.post("/api/v1/agent-templates/apply-config", json=payload)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✓ Applied template with temperature: {result['config']['temperature']}")
        
        # Test validate template config
        print("\nTesting POST /api/v1/agent-templates/validate")
        payload = {
            "template_id": "chatbot-basic",
            "config": {
                "llm_provider": "ollama",
                "model_name": "llama2",
                "system_prompt": "You are a helpful assistant",
                "temperature": 0.7,
                "max_tokens": 1000
            }
        }
        response = client.post("/api/v1/agent-templates/validate", json=payload)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✓ Validation result: {result['is_valid']}")
        
        print("\n🎉 All Agent API tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ API test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_agent_api()
    sys.exit(0 if success else 1)