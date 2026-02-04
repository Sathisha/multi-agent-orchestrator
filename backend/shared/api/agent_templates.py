"""Agent Templates API endpoints."""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field

from ..services.agent_templates import AgentTemplateService
from shared.schemas.agent_template import AgentTemplate
from shared.models.agent import AgentConfig, AgentType, LLMProvider

router = APIRouter(prefix="/agent-templates", tags=["agent-templates"])


class TemplateConfigRequest(BaseModel):
    """Request model for applying template configuration."""
    
    template_id: str = Field(..., description="Template identifier")
    overrides: Optional[Dict[str, Any]] = Field(None, description="Configuration overrides")


class TemplateConfigResponse(BaseModel):
    """Response model for template configuration."""
    
    template_id: str = Field(..., description="Template identifier")
    config: AgentConfig = Field(..., description="Resolved configuration")


class TemplateValidationRequest(BaseModel):
    """Request model for template validation."""
    
    template_id: str = Field(..., description="Template identifier")
    config: Dict[str, Any] = Field(..., description="Configuration to validate")


class TemplateValidationResponse(BaseModel):
    """Response model for template validation."""
    
    is_valid: bool = Field(..., description="Whether configuration is valid")
    errors: List[str] = Field(default_factory=list, description="Validation errors")


@router.get("/", response_model=List[AgentTemplate])
async def list_templates():
    """List all available agent templates."""
    return AgentTemplateService.list_templates()


@router.get("/{template_id}", response_model=AgentTemplate)
async def get_template(template_id: str):
    """Get a specific template by ID."""
    template = AgentTemplateService.get_template(template_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template '{template_id}' not found"
        )
    return template


@router.get("/{template_id}/config", response_model=AgentConfig)
async def get_template_config(template_id: str):
    """Get the default configuration for a template."""
    config = AgentTemplateService.get_template_config(template_id)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template '{template_id}' not found"
        )
    return config


@router.post("/apply-config", response_model=TemplateConfigResponse)
async def apply_template_config(request: TemplateConfigRequest):
    """Apply a template with optional overrides."""
    config = AgentTemplateService.apply_template(request.template_id, request.overrides)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template '{request.template_id}' not found"
        )
    
    return TemplateConfigResponse(
        template_id=request.template_id,
        config=config
    )


@router.post("/validate", response_model=TemplateValidationResponse)
async def validate_template_config(request: TemplateValidationRequest):
    """Validate a configuration against a template."""
    template = AgentTemplateService.get_template(request.template_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template '{request.template_id}' not found"
        )
    
    is_valid = AgentTemplateService.validate_template_config(
        request.template_id, 
        request.config
    )
    
    errors = []
    if not is_valid:
        # Check for missing required fields
        for field in template.required_fields:
            if field not in request.config:
                errors.append(f"Missing required field: {field}")
        
        # Try to validate with AgentConfig to get specific errors
        try:
            AgentConfig(**request.config)
        except Exception as e:
            errors.append(f"Configuration validation error: {str(e)}")
    
    return TemplateValidationResponse(
        is_valid=is_valid,
        errors=errors
    )


@router.get("/types/{agent_type}", response_model=List[AgentTemplate])
async def list_templates_by_type(agent_type: AgentType):
    """List templates filtered by agent type."""
    all_templates = AgentTemplateService.list_templates()
    filtered_templates = [t for t in all_templates if t.type == agent_type]
    return filtered_templates
