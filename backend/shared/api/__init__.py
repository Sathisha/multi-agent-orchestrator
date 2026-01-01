"""
API module initialization.

This module provides centralized API router registration and configuration.
"""

from fastapi import APIRouter
# Temporarily commented out - complex multi-tenant features (low priority per user)
# from .tenant_admin import router as tenant_admin_router
# from .compliance import router as compliance_router
from .auth import router as auth_router
from .api_keys import router as api_keys_router
from .agent import router as agent_router
# from .agent_templates import router as agent_templates_router
# from .agent_versioning import router as agent_versioning_router
from .agent_executor import router as agent_executor_router
from .workflow_orchestrator import router as workflow_orchestrator_router
from .tool_registry import router as tool_registry_router
# from .mcp_gateway import router as mcp_gateway_router
# Temporarily commented out to fix import issues
# from .llm_providers import router as llm_providers_router
# Temporarily commented out to fix import issues
# from .memory import router as memory_router
# from .guardrails import router as guardrails_router
from .audit import router as audit_router

# Create main API router
api_router = APIRouter()

# Include all sub-routers
api_router.include_router(auth_router)
api_router.include_router(api_keys_router)
# Temporarily commented out - complex multi-tenant features (low priority per user)
# api_router.include_router(tenant_admin_router)
# api_router.include_router(compliance_router)
api_router.include_router(agent_router)
# api_router.include_router(agent_templates_router)
# api_router.include_router(agent_versioning_router)
api_router.include_router(agent_executor_router)
api_router.include_router(workflow_orchestrator_router)
api_router.include_router(tool_registry_router)
# api_router.include_router(mcp_gateway_router)
# Temporarily commented out to fix import issues
# api_router.include_router(llm_providers_router)
# Temporarily commented out to fix import issues
# api_router.include_router(memory_router)
# api_router.include_router(guardrails_router)
api_router.include_router(audit_router)

__all__ = ["api_router"]