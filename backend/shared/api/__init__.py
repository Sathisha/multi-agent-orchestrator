"""
API module initialization.

This module provides centralized API router registration and configuration.
"""

from fastapi import APIRouter
from .auth import router as auth_router
from .api_keys import router as api_keys_router
from .agent import router as agent_router
from .agent_executor import router as agent_executor_router
from .tool_registry import router as tool_registry_router
from .audit import router as audit_router
from .llm_models import router as llm_models_router
from .v1.endpoints.chains import router as chains_router

from .mcp_gateway import router as mcp_gateway_router

# Create main API router
api_router = APIRouter()

# Include all sub-routers
api_router.include_router(auth_router)
api_router.include_router(api_keys_router)
api_router.include_router(agent_router)
api_router.include_router(agent_executor_router)
api_router.include_router(tool_registry_router)
api_router.include_router(llm_models_router)
api_router.include_router(chains_router)
api_router.include_router(audit_router)
api_router.include_router(mcp_gateway_router)

# Monitoring
from .monitoring import router as monitoring_router
api_router.include_router(monitoring_router)

__all__ = ["api_router"]
