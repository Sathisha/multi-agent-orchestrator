"""Agent template service for managing pre-built agent configurations."""

from typing import Dict, List, Optional

from shared.models.agent import AgentTemplate, AgentType, LLMProvider, AgentConfig


class AgentTemplateService:
    """Service for managing agent templates and their default configurations."""
    
    # Define built-in templates with complete default configurations
    TEMPLATES: Dict[str, AgentTemplate] = {
        "chatbot-basic": AgentTemplate(
            id="chatbot-basic",
            name="Basic Chatbot",
            description="A simple conversational chatbot for general Q&A",
            agent_type=AgentType.CHATBOT,
            default_config=AgentConfig(
                name="Basic Chatbot",
                model="llama2",
                system_prompt="You are a helpful assistant. Answer questions clearly and concisely.",
                temperature=0.7,
                max_tokens=1000,
                tools=[],
                llm_provider=LLMProvider.OLLAMA,
                mcp_servers=[],
                memory_enabled=True,
                guardrails_enabled=True
            ),
        ),
        "chatbot-advanced": AgentTemplate(
            id="chatbot-advanced",
            name="Advanced Chatbot",
            description="Advanced chatbot with query analysis, knowledge expert, and response preparation",
            agent_type=AgentType.CHATBOT,
            default_config=AgentConfig(
                name="Advanced Chatbot",
                model="gpt-4",
                system_prompt="You are an advanced AI assistant with specialized capabilities for query analysis and knowledge synthesis.",
                temperature=0.8,
                max_tokens=2000,
                tools=["query_analyzer", "knowledge_expert", "response_preparer"],
                llm_provider=LLMProvider.OPENAI,
                mcp_servers=["knowledge_base", "guardrails"],
                memory_enabled=True,
                guardrails_enabled=True
            ),
        ),
        "content-generator": AgentTemplate(
            id="content-generator",
            name="Content Generator",
            description="Agent specialized in generating various types of content",
            agent_type=AgentType.CONTENT_GENERATION,
            default_config=AgentConfig(
                name="Content Generator",
                model="claude-3-opus",
                system_prompt="You are a creative content generator. Create engaging, well-structured content based on user requirements.",
                temperature=0.9,
                max_tokens=4000,
                tools=["content_formatter", "style_analyzer"],
                llm_provider=LLMProvider.ANTHROPIC,
                mcp_servers=["content_library"],
                memory_enabled=True,
                guardrails_enabled=True
            ),
        ),
        "data-analyst": AgentTemplate(
            id="data-analyst",
            name="Data Analyst",
            description="Agent for analyzing data and generating insights",
            agent_type=AgentType.DATA_ANALYSIS,
            default_config=AgentConfig(
                name="Data Analyst",
                model="codellama",
                system_prompt="You are a data analyst. Analyze data, identify patterns, and provide actionable insights.",
                temperature=0.3,
                max_tokens=3000,
                tools=["data_processor", "chart_generator", "statistics_calculator"],
                llm_provider=LLMProvider.OLLAMA,
                mcp_servers=["data_warehouse"],
                memory_enabled=True,
                guardrails_enabled=True
            ),
        ),
        "custom-agent": AgentTemplate(
            id="custom-agent",
            name="Custom Agent",
            description="Blank template for creating custom agents from scratch",
            agent_type=AgentType.CUSTOM,
            default_config=AgentConfig(
                name="Custom Agent",
                model="llama2",
                system_prompt="You are an AI assistant.",
                temperature=0.7,
                max_tokens=1000,
                tools=[],
                llm_provider=LLMProvider.OLLAMA,
                mcp_servers=[],
                memory_enabled=False,
                guardrails_enabled=True
            ),
        )
    }
    
    @classmethod
    def get_template(cls, template_id: str) -> Optional[AgentTemplate]:
        """Get a template by ID."""
        return cls.TEMPLATES.get(template_id)
    
    @classmethod
    def list_templates(cls) -> List[AgentTemplate]:
        """List all available templates."""
        return list(cls.TEMPLATES.values())
    
    @classmethod
    def get_template_config(cls, template_id: str) -> Optional[AgentConfig]:
        """Get the default configuration for a template as an AgentConfig object."""
        template = cls.get_template(template_id)
        if not template:
            return None
        
        # Create AgentConfig from template defaults
        return template.default_config
    
    @classmethod
    def apply_template(cls, template_id: str, overrides: Optional[Dict] = None) -> Optional[AgentConfig]:
        """
        Apply a template and merge with user-provided overrides.
        
        Args:
            template_id: The template identifier
            overrides: Optional dictionary of configuration overrides
            
        Returns:
            AgentConfig with template defaults and applied overrides, or None if template not found
        """
        template = cls.get_template(template_id)
        if not template:
            return None
        
        # Start with template defaults
        config_dict = template.default_config.model_dump()
        
        # Apply overrides if provided
        if overrides:
            config_dict.update(overrides)
        
        # Create and validate AgentConfig
        return AgentConfig(**config_dict)
    
    @classmethod
    def validate_template_config(cls, template_id: str, config: Dict) -> bool:
        """
        Validate that a configuration has all required fields for a template.
        
        Args:
            template_id: The template identifier
            config: Configuration dictionary to validate
            
        Returns:
            True if all required fields are present and valid, False otherwise
        """
        template = cls.get_template(template_id)
        if not template:
            return False
        
        # The Pydantic model AgentConfig will handle validation of required fields.
        
        # Try to create AgentConfig to validate types and constraints
        try:
            AgentConfig(**config)
            return True
        except Exception:
            return False
