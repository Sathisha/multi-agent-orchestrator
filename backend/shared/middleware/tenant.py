"""
Tenant Context Middleware - Basic Framework

This middleware provides a basic framework for tenant context extraction.
It can be extended later when implementing full multi-tenant functionality.
"""

import logging
from typing import Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class TenantContextMiddleware(BaseHTTPMiddleware):
    """Basic tenant context middleware framework."""
    
    def __init__(self, app):
        super().__init__(app)
        self.excluded_paths = {
            "/",
            "/health",
            "/metrics",
            "/docs",
            "/redoc",
            "/openapi.json"
        }
    
    async def dispatch(self, request: Request, call_next):
        """Process request with basic tenant context handling."""
        
        # Skip tenant context for excluded paths
        if request.url.path in self.excluded_paths:
            return await call_next(request)
        
        # Basic tenant context extraction (framework only)
        tenant_id = self._extract_basic_tenant_context(request)
        
        if tenant_id:
            # Store basic tenant context in request state
            request.state.tenant_id = tenant_id
            logger.debug(f"Extracted tenant context: {tenant_id}")
        
        # Process request
        response = await call_next(request)
        
        # Add basic tenant headers if context exists
        if tenant_id:
            response.headers["X-Tenant-ID"] = tenant_id
        
        return response
    
    def _extract_basic_tenant_context(self, request: Request) -> Optional[str]:
        """Extract basic tenant context from request."""
        
        # Method 1: Check X-Tenant-ID header
        tenant_header = request.headers.get("x-tenant-id")
        if tenant_header:
            return tenant_header
        
        # Method 2: Extract from subdomain (basic implementation)
        host = request.headers.get("host", "")
        if host:
            tenant_from_subdomain = self._extract_from_subdomain(host)
            if tenant_from_subdomain:
                return tenant_from_subdomain
        
        # Method 3: Extract from path (basic implementation)
        tenant_from_path = self._extract_from_path(request.url.path)
        if tenant_from_path:
            return tenant_from_path
        
        return None
    
    def _extract_from_subdomain(self, host: str) -> Optional[str]:
        """Extract tenant from subdomain - basic implementation."""
        # Remove port if present
        host = host.split(':')[0]
        
        # Split by dots
        parts = host.split('.')
        
        # Check if it's a subdomain (at least 3 parts: subdomain.domain.tld)
        if len(parts) >= 3:
            subdomain = parts[0]
            
            # Skip common subdomains
            if subdomain not in ['www', 'api', 'admin', 'app']:
                return subdomain
        
        return None
    
    def _extract_from_path(self, path: str) -> Optional[str]:
        """Extract tenant from URL path - basic implementation."""
        # Pattern: /tenant/{tenant_id}/...
        if path.startswith('/tenant/'):
            parts = path.split('/')
            if len(parts) >= 3:
                return parts[2]
        
        return None


def get_tenant_context(request: Request) -> Optional[str]:
    """Get basic tenant context from request state."""
    return getattr(request.state, 'tenant_id', None)