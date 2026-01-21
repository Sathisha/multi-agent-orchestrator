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
from .v1.endpoints.chat import router as chat_router

from .mcp_gateway import router as mcp_gateway_router
from .mcp_bridge_discovery import router as mcp_bridge_discovery_router
from .users import router as users_router
from .roles import router as roles_router
from .workflow import router as workflow_router

# Create main API router
api_router = APIRouter()

# Include all sub-routers
api_router.include_router(auth_router)
api_router.include_router(users_router, prefix="/auth") 
api_router.include_router(roles_router)
api_router.include_router(workflow_router)
api_router.include_router(api_keys_router)
api_router.include_router(agent_router)
api_router.include_router(agent_executor_router)
api_router.include_router(tool_registry_router)
api_router.include_router(llm_models_router)
api_router.include_router(chains_router)
api_router.include_router(chat_router)
from .agent_templates import router as agent_templates_router
api_router.include_router(agent_templates_router)
api_router.include_router(audit_router)
api_router.include_router(mcp_gateway_router)
api_router.include_router(mcp_bridge_discovery_router)

# Monitoring
from .monitoring import router as monitoring_router
api_router.include_router(monitoring_router)

__all__ = ["api_router"]