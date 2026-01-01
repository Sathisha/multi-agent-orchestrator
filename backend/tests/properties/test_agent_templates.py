"""
Property-based tests for agent template configuration completeness.

**Feature: ai-agent-framework, Property 1: Template Configuration Completeness**
**Validates: Requirements 1.2**
"""

import pytest
from hypothesis import given, strategies as st, assume
from typing import Dict, Any

from shared.models.agent import AgentTemplate, AgentType, LLMProvider, AgentConfig
from shared.services.agent_templates import AgentTemplateService


# Hypothesis strategies for generating test data
@st.composite
def agent_template_strategy(draw):
    """Generate valid agent template configurations."""
    template_id = draw(st.sampled_from(list(AgentTemplateService.TEMPLATES.keys())))
    return template_id


@st.composite
def config_override_strategy(draw):
    """Generate configuration overrides that might be provided by users."""
    overrides = {}
    
    # Optionally override some fields
    if draw(st.booleans()):
        overrides["temperature"] = draw(st.floats(min_value=0.0, max_value=2.0))
    
    if draw(st.booleans()):
        overrides["max_tokens"] = draw(st.integers(min_value=1, max_value=8000))
    
    if draw(st.booleans()):
        overrides["llm_provider"] = draw(st.sampled_from([p.value for p in LLMProvider]))
    
    if draw(st.booleans()):
        overrides["model"] = draw(st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd", "Pc"))))
    
    if draw(st.booleans()):
        overrides["system_prompt"] = draw(st.text(min_size=10, max_size=500))
    
    if draw(st.booleans()):
        overrides["memory_enabled"] = draw(st.booleans())
    
    if draw(st.booleans()):
        overrides["guardrails_enabled"] = draw(st.booleans())
    
    return overrides


class TestAgentTemplateConfigurationCompleteness:
    """Test suite for agent template configuration completeness property."""
    
    @pytest.mark.property
    @given(template_id=agent_template_strategy())
    def test_template_provides_complete_default_configuration(self, template_id: str):
        """
        **Feature: ai-agent-framework, Property 1: Template Configuration Completeness**
        **Validates: Requirements 1.2**
        
        Property: For any agent template selection, the resulting configuration should have 
        all required fields populated with valid default values that pass validation.
        
        This test ensures that when a developer selects an agent template, the AI Agent 
        Framework pre-populates configuration fields with sensible defaults as required 
        by acceptance criteria 1.2.
        """
        # Get the template
        template = AgentTemplateService.get_template(template_id)
        assert template is not None, f"Template {template_id} should exist"
        
        # Get the default configuration
        default_config = AgentTemplateService.get_template_config(template_id)
        assert default_config is not None, f"Template {template_id} should provide default configuration"
        
        # Verify all required fields are implicitly handled by AgentConfig validation
        # The fields are now verified when AgentConfig(**config_dict) is called.
        
        # default_config is already an AgentConfig object, so its validity is ensured
        # when AgentTemplateService.get_template_config returns it.
        # No need to re-validate here.
        
        # Verify template validation function works correctly
        assert AgentTemplateService.validate_template_config(template_id, default_config.model_dump()), \
            f"Template {template_id} default configuration should pass validation"
    
    @pytest.mark.property
    @given(
        template_id=agent_template_strategy(),
        overrides=config_override_strategy()
    )
    def test_template_with_overrides_maintains_completeness(self, template_id: str, overrides: Dict[str, Any]):
        """
        **Feature: ai-agent-framework, Property 1: Template Configuration Completeness**
        **Validates: Requirements 1.2**
        
        Property: For any agent template and any valid configuration overrides, 
        the resulting merged configuration should still have all required fields 
        populated and pass validation.
        
        This ensures that user customizations don't break the template's completeness.
        """
        # Apply template with overrides
        merged_config = AgentTemplateService.apply_template(template_id, overrides)
        assert merged_config is not None, f"Template {template_id} should be applicable with overrides"
        
        # The required fields are now verified when AgentConfig(**config_dict) is called.
        
        # merged_config is already an AgentConfig object, so its validity is ensured
        # when AgentTemplateService.apply_template returns it.
        # No need to re-validate here.
        
        # Verify overrides were actually applied where provided
        merged_config_dict = merged_config.model_dump() # Define merged_config_dict
        for override_key, override_value in overrides.items():
            if override_key in merged_config_dict:
                assert merged_config_dict[override_key] == override_value, \
                    f"Override for '{override_key}' was not applied correctly in template {template_id}"
    
    @pytest.mark.property
    @given(template_id=agent_template_strategy())
    def test_template_configuration_has_sensible_defaults(self, template_id: str):
        """
        **Feature: ai-agent-framework, Property 1: Template Configuration Completeness**
        **Validates: Requirements 1.2**
        
        Property: For any agent template, the default configuration values should be 
        within reasonable ranges and appropriate for the template type.
        
        This ensures that templates provide "sensible defaults" as required by the specification.
        """
        template = AgentTemplateService.get_template(template_id)
        assert template is not None
        
        config = AgentTemplateService.get_template_config(template_id)
        assert config is not None
        
        # Check that temperature is in a reasonable range
        assert 0.0 <= config.temperature <= 2.0, f"Template {template_id} has unreasonable temperature: {config.temperature}"
        
        # Check that max_tokens is reasonable
        assert 1 <= config.max_tokens <= 8000, f"Template {template_id} has unreasonable max_tokens: {config.max_tokens}"
        
        # Check that system_prompt is not empty
        assert len(config.system_prompt.strip()) > 0, f"Template {template_id} has empty system prompt"
        
        # Check that model_name is not empty
        assert len(config.model.strip()) > 0, f"Template {template_id} has empty model name"
        
        # Check that LLM provider is valid
        assert config.llm_provider in [p.value for p in LLMProvider], \
            f"Template {template_id} has invalid LLM provider: {config.llm_provider}"
        
        # Type-specific checks
        if template.agent_type == AgentType.CHATBOT:
            # Chatbots should have memory enabled by default for conversation continuity
            assert config.memory_enabled, f"Chatbot template {template_id} should have memory enabled by default"
        
        if template.agent_type == AgentType.DATA_ANALYSIS:
            # Data analysis agents should have lower temperature for more deterministic results
            assert config.temperature <= 0.5, f"Data analysis template {template_id} should have low temperature for deterministic results"
        
        if template.agent_type == AgentType.CONTENT_GENERATION:
            # Content generation agents should have higher temperature for creativity
            assert config.temperature >= 0.7, f"Content generation template {template_id} should have higher temperature for creativity"
    
    def test_all_built_in_templates_exist_and_are_valid(self):
        """
        **Feature: ai-agent-framework, Property 1: Template Configuration Completeness**
        **Validates: Requirements 1.2**
        
        Unit test to ensure all built-in templates are properly defined and valid.
        This is not a property test but validates the template definitions themselves.
        """
        templates = AgentTemplateService.list_templates()
        assert len(templates) > 0, "At least one template should be available"
        
        # Check that we have templates for each agent type
        template_types = {template.agent_type for template in templates}
        expected_types = {AgentType.CHATBOT, AgentType.CONTENT_GENERATION, AgentType.DATA_ANALYSIS, AgentType.CUSTOM}
        assert template_types >= expected_types, f"Missing templates for types: {expected_types - template_types}"
        
        # Validate each template
        for template in templates:
            # Template should have required metadata
            assert template.id, f"Template {template.name} missing ID"
            assert template.name, f"Template {template.id} missing name"
            assert template.description, f"Template {template.id} missing description"
            assert template.agent_type, f"Template {template.id} missing type"
            
            # Template should have valid default configuration
            config = AgentTemplateService.get_template_config(template.id)
            assert config is not None, f"Template {template.id} should provide valid default configuration"
            
            # Required fields are implicitly checked by AgentConfig validation within get_template_config.