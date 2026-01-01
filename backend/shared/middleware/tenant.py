"""
Simplified Tenant Middleware - Returns Default Tenant Context

Multi-tenant features simplified per user requirements (low priority).
All requests use the default tenant context.
"""
from typing import Optional, Tuple
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from shared.context.default_tenant import TenantContext, get_default_tenant_context, DEFAULT_TENANT_ID
from shared.database.connection import get_async_db


class TenantContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware to handle tenant context. 
    Simplified for single-tenant mode: just passes through.
    """
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # In multi-tenant, we would extract tenant ID here.
        # Single-tenant: assumes default tenant context is used globally/by default.
        return await call_next(request)



async def get_tenant_context() -> TenantContext:
    """
    Returns default tenant context for all requests.
    
    Simplified implementation - multi-tenant features are low priority.
    """
    return get_default_tenant_context()


async def get_tenant_aware_session(
    session: AsyncSession = Depends(get_async_db)
) -> Tuple[AsyncSession, TenantContext]:
    """
    Returns database session and tenant context.
    
    Always returns default tenant for simplified implementation.
    """
    tenant_context = get_default_tenant_context()
    return (session, tenant_context)


def get_tenant_context_dependency():
    """
    Dependency that provides tenant context.
    Returns default tenant context.
    """
    return Depends(get_tenant_context)


def require_tenant_context_dependency():
    """
    Dependency that requires tenant context.
    Returns default tenant context.
    """
    return Depends(get_tenant_context)


def get_current_tenant_id_from_request(request: Request) -> str:
    """
    Extract tenant ID from request.
    Always returns default tenant ID.
    """
    return DEFAULT_TENANT_ID