"""
API module initialization.

This module provides centralized API router registration and configuration.
"""

from fastapi import APIRouter
from .tenant_admin import router as tenant_admin_router
from .compliance import router as compliance_router
from .auth import router as auth_router
from .api_keys import router as api_keys_router
from .agent import router as agent_router
from .agent_templates import router as agent_templates_router
from .agent_versioning import router as agent_versioning_router
from .llm_providers import router as llm_providers_router

# Create main API router
api_router = APIRouter()

# Include all sub-routers
api_router.include_router(auth_router)
api_router.include_router(api_keys_router)
api_router.include_router(tenant_admin_router)
api_router.include_router(compliance_router)
api_router.include_router(agent_router)
api_router.include_router(agent_templates_router)
api_router.include_router(agent_versioning_router)
api_router.include_router(llm_providers_router)

__all__ = ["api_router"]