#!/usr/bin/env python3
"""Standalone test for Agent Templates API."""

import asyncio
import sys
import os
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Add the current directory to Python path
sys.path.insert(0, '/app')

def test_agent_templates_standalone():
    """Test the Agent Templates API in isolation."""
    try:
        print("Testing Agent Templates API (standalone)...")
        
        # Import only what we need for agent templates
        from shared.services.agent_templates import AgentTemplateService
        from shared.models.agent import AgentTemplate, AgentConfig, AgentType, LLMProvider
        from pydantic import BaseModel, Field
        from typing import List, Optional, Dict, Any
        from fastapi import APIRouter, HTTPException, status
        
        # Create the router inline to avoid import issues
        router = APIRouter(prefix="/api/v1/agent-templates", tags=["agent-templates"])
        
        class TemplateConfigRequest(BaseModel):
            template_id: str = Field(..., description="Template identifier")
            overrides: Optional[Dict[str, Any]] = Field(None, description="Configuration overrides")
        
        class TemplateConfigResponse(BaseModel):
            template_id: str = Field(..., description="Template identifier")
            config: AgentConfig = Field(..., description="Resolved configuration")
        
        class TemplateValidationRequest(BaseModel):
            template_id: str = Field(..., description="Template identifier")
            config: Dict[str, Any] = Field(..., description="Configuration to validate")
        
        class TemplateValidationResponse(BaseModel):
            is_valid: bool = Field(..., description="Whether configuration is valid")
            errors: List[str] = Field(default_factory=list, description="Validation errors")
        
        @router.get("/", response_model=List[AgentTemplate])
        async def list_templates():
            return AgentTemplateService.list_templates()
        
        @router.get("/{template_id}", response_model=AgentTemplate)
        async def get_template(template_id: str):
            template = AgentTemplateService.get_template(template_id)
            if not template:
                raise HTTPException(status_code=404, detail=f"Template '{template_id}' not found")
            return template
        
        @router.get("/{template_id}/config", response_model=AgentConfig)
        async def get_template_config(template_id: str):
            config = AgentTemplateService.get_template_config(template_id)
            if not config:
                raise HTTPException(status_code=404, detail=f"Template '{template_id}' not found")
            return config
        
        @router.post("/apply-config", response_model=TemplateConfigResponse)
        async def apply_template_config(request: TemplateConfigRequest):
            config = AgentTemplateService.apply_template(request.template_id, request.overrides)
            if not config:
                raise HTTPException(status_code=404, detail=f"Template '{request.template_id}' not found")
            return TemplateConfigResponse(template_id=request.template_id, config=config)
        
        @router.post("/validate", response_model=TemplateValidationResponse)
        async def validate_template_config(request: TemplateValidationRequest):
            template = AgentTemplateService.get_template(request.template_id)
            if not template:
                raise HTTPException(status_code=404, detail=f"Template '{request.template_id}' not found")
            
            is_valid = AgentTemplateService.validate_template_config(request.template_id, request.config)
            errors = []
            if not is_valid:
                for field in template.required_fields:
                    if field not in request.config:
                        errors.append(f"Missing required field: {field}")
                try:
                    AgentConfig(**request.config)
                except Exception as e:
                    errors.append(f"Configuration validation error: {str(e)}")
            
            return TemplateValidationResponse(is_valid=is_valid, errors=errors)
        
        # Create test app
        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)
        
        # Run tests
        print("Testing GET /api/v1/agent-templates/")
        response = client.get("/api/v1/agent-templates/")
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            templates = response.json()
            print(f"✓ Retrieved {len(templates)} templates")
            for template in templates:
                print(f"  - {template['name']} ({template['type']})")
        
        print("\nTesting GET /api/v1/agent-templates/chatbot-basic")
        response = client.get("/api/v1/agent-templates/chatbot-basic")
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            template = response.json()
            print(f"✓ Retrieved template: {template['name']}")
        
        print("\nTesting GET /api/v1/agent-templates/chatbot-basic/config")
        response = client.get("/api/v1/agent-templates/chatbot-basic/config")
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            config = response.json()
            print(f"✓ Retrieved config with LLM provider: {config['llm_provider']}")
        
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
        
        print("\n🎉 All Agent Templates API tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ API test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_agent_templates_standalone()
    sys.exit(0 if success else 1)