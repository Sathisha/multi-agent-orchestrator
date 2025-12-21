#!/usr/bin/env python3
"""Simple test script to verify Agent Manager Service functionality."""

import asyncio
import sys
import os

# Add the current directory to Python path
sys.path.insert(0, '/app')

async def test_agent_service():
    """Test the Agent Manager Service functionality."""
    try:
        # Test basic imports
        print("Testing imports...")
        from shared.models.agent import Agent, AgentTemplate, AgentConfig, AgentType, LLMProvider
        print("✓ Agent models imported successfully")
        
        from shared.services.agent_templates import AgentTemplateService
        print("✓ Agent template service imported successfully")
        
        from shared.services.id_generator import IDGeneratorService
        print("✓ ID generator service imported successfully")
        
        # Test template service functionality
        print("\nTesting Agent Template Service...")
        templates = AgentTemplateService.list_templates()
        print(f"✓ Found {len(templates)} templates")
        
        for template in templates:
            print(f"  - {template.name} ({template.type})")
        
        # Test getting a specific template
        chatbot_template = AgentTemplateService.get_template("chatbot-basic")
        if chatbot_template:
            print(f"✓ Retrieved chatbot template: {chatbot_template.name}")
        
        # Test template configuration
        config = AgentTemplateService.get_template_config("chatbot-basic")
        if config:
            print(f"✓ Generated config for chatbot template")
            print(f"  LLM Provider: {config.llm_provider}")
            print(f"  Model: {config.model_name}")
            print(f"  Temperature: {config.temperature}")
        
        # Test ID generation
        print("\nTesting ID Generation...")
        agent_id = IDGeneratorService.generate_agent_id()
        print(f"✓ Generated agent ID: {agent_id}")
        
        execution_id = IDGeneratorService.generate_execution_id()
        print(f"✓ Generated execution ID: {execution_id}")
        
        deployment_id = IDGeneratorService.generate_deployment_id()
        print(f"✓ Generated deployment ID: {deployment_id}")
        
        # Test template validation
        print("\nTesting Template Validation...")
        test_config = {
            "llm_provider": "ollama",
            "model_name": "llama2",
            "system_prompt": "You are a helpful assistant",
            "temperature": 0.7,
            "max_tokens": 1000
        }
        
        is_valid = AgentTemplateService.validate_template_config("chatbot-basic", test_config)
        print(f"✓ Template validation result: {is_valid}")
        
        # Test applying template with overrides
        overrides = {"temperature": 0.9, "max_tokens": 2000}
        applied_config = AgentTemplateService.apply_template("chatbot-basic", overrides)
        if applied_config:
            print(f"✓ Applied template with overrides")
            print(f"  Temperature: {applied_config.temperature}")
            print(f"  Max tokens: {applied_config.max_tokens}")
        
        print("\n🎉 All Agent Manager Service tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_agent_service())
    sys.exit(0 if success else 1)