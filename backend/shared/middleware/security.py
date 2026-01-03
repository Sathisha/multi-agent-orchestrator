"""
Security Middleware - API Gateway Security Layer

This module provides essential security middleware including:
- Rate limiting
- Input validation and sanitization
- CORS policies and security headers
- IP filtering and basic DDoS protection
- Request/response logging for security monitoring
- Authentication and authorization dependencies

This is a simplified implementation that can be extended with Kong Gateway later.
"""

import logging
import time
import re
from typing import Dict, List, Optional, Set, Callable
from collections import defaultdict, deque
from datetime import datetime, timedelta
from ipaddress import ip_address, ip_network

from fastapi import Request, Response, HTTPException, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

# Import auth functions from services
from ..services.auth import get_current_user as _get_current_user, get_current_user_with_tenant as _get_current_user_with_tenant
from ..models.user import User

logger = logging.getLogger(__name__)

# Re-export auth functions for backward compatibility
get_current_user = _get_current_user
get_current_user_with_tenant = _get_current_user_with_tenant


def require_permissions(permissions: List[str]) -> Callable:
    """
    FastAPI dependency to require specific permissions.
    
    Args:
        permissions: List of required permissions
        
    Returns:
        FastAPI dependency function
        
    Usage:
        @app.get("/admin")
        async def admin_endpoint(
            current_user: User = Depends(get_current_user),
            _: None = Depends(require_permissions(["admin:read"]))
        ):
            return {"message": "Admin access granted"}
    """
    def permission_dependency(current_user: User = Depends(get_current_user)) -> None:
        """Check if current user has required permissions."""
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        # For now, system admins have all permissions
        if current_user.is_system_admin:
            return None
        
        # TODO: Implement proper RBAC permission checking
        # This is a placeholder implementation
        user_permissions = getattr(current_user, 'permissions', [])
        
        missing_permissions = [p for p in permissions if p not in user_permissions]
        if missing_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required permissions: {', '.join(missing_permissions)}"
            )
        
        return None
    
    return permission_dependency


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware with sliding window algorithm."""
    
    def __init__(
        self,
        app,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
        burst_limit: int = 10
    ):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.burst_limit = burst_limit
        
        # In-memory storage (in production, use Redis)
        self.request_counts: Dict[str, deque] = defaultdict(deque)
        self.burst_counts: Dict[str, int] = defaultdict(int)
        self.burst_reset_times: Dict[str, float] = defaultdict(float)
    
    async def dispatch(self, request: Request, call_next):
        """Apply rate limiting to requests."""
        client_ip = self._get_client_ip(request)
        current_time = time.time()
        
        # Check burst limit (10 requests per 10 seconds)
        if self._check_burst_limit(client_ip, current_time):
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Rate limit exceeded - too many requests in short time",
                    "retry_after": 10
                }
            )
        
        # Check minute and hour limits
        if self._check_rate_limits(client_ip, current_time):
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Rate limit exceeded",
                    "retry_after": 60
                }
            )
        
        # Record the request
        self._record_request(client_ip, current_time)
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(
            max(0, self.requests_per_minute - len(self.request_counts[client_ip]))
        )
        
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request."""
        # Check for forwarded headers (from load balancers/proxies)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fallback to direct client IP
        return request.client.host if request.client else "unknown"
    
    def _check_burst_limit(self, client_ip: str, current_time: float) -> bool:
        """Check if client has exceeded burst limit."""
        # Reset burst count every 10 seconds
        if current_time - self.burst_reset_times[client_ip] > 10:
            self.burst_counts[client_ip] = 0
            self.burst_reset_times[client_ip] = current_time
        
        self.burst_counts[client_ip] += 1
        return self.burst_counts[client_ip] > self.burst_limit
    
    def _check_rate_limits(self, client_ip: str, current_time: float) -> bool:
        """Check if client has exceeded rate limits."""
        requests = self.request_counts[client_ip]
        
        # Remove old requests (older than 1 hour)
        while requests and current_time - requests[0] > 3600:
            requests.popleft()
        
        # Check hour limit
        if len(requests) >= self.requests_per_hour:
            return True
        
        # Check minute limit
        minute_requests = sum(1 for req_time in requests if current_time - req_time <= 60)
        return minute_requests >= self.requests_per_minute
    
    def _record_request(self, client_ip: str, current_time: float):
        """Record a request for rate limiting."""
        self.request_counts[client_ip].append(current_time)


class IPFilterMiddleware(BaseHTTPMiddleware):
    """IP filtering middleware for basic access control."""
    
    def __init__(
        self,
        app,
        allowed_ips: Optional[List[str]] = None,
        blocked_ips: Optional[List[str]] = None,
        allowed_networks: Optional[List[str]] = None
    ):
        super().__init__(app)
        self.allowed_ips = set(allowed_ips or [])
        self.blocked_ips = set(blocked_ips or [])
        self.allowed_networks = [ip_network(net) for net in (allowed_networks or [])]
    
    async def dispatch(self, request: Request, call_next):
        """Filter requests based on IP address."""
        client_ip = self._get_client_ip(request)
        
        try:
            ip_addr = ip_address(client_ip)
        except ValueError:
            # Invalid IP address
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"detail": "Invalid client IP address"}
            )
        
        # Check if IP is blocked
        if client_ip in self.blocked_ips:
            logger.warning(f"Blocked IP attempted access: {client_ip}")
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "Access denied"}
            )
        
        # Check if IP is in allowed list (if configured)
        if self.allowed_ips and client_ip not in self.allowed_ips:
            # Check allowed networks
            if not any(ip_addr in network for network in self.allowed_networks):
                logger.warning(f"Unauthorized IP attempted access: {client_ip}")
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={"detail": "Access denied"}
                )
        
        return await call_next(request)
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request."""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else "unknown"


class InputValidationMiddleware(BaseHTTPMiddleware):
    """Input validation and sanitization middleware."""
    
    def __init__(self, app):
        super().__init__(app)
        
        # Patterns for detecting malicious input
        self.sql_injection_patterns = [
            r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)\b)",
            r"(--|#|/\*|\*/)",
            r"(\b(OR|AND)\s+\d+\s*=\s*\d+)",
            r"(\'\s*(OR|AND)\s*\'\w*\'\s*=\s*\'\w*)",
        ]
        
        self.xss_patterns = [
            r"<script[^>]*>.*?</script>",
            r"javascript:",
            r"on\w+\s*=",
            r"<iframe[^>]*>.*?</iframe>",
            r"<object[^>]*>.*?</object>",
        ]
        
        self.command_injection_patterns = [
            r"[;&|`$(){}[\]\\]",
            r"\b(cat|ls|pwd|whoami|id|uname|ps|netstat|ifconfig)\b",
        ]
        
        self.path_traversal_patterns = [
            r"\.\./",
            r"\.\.\\",
            r"%2e%2e%2f",
            r"%2e%2e\\",
            r"\.\.%2f",
            r"\.\.%5c",
        ]
        
        self.header_injection_patterns = [
            r"[\r\n]",  # Carriage return and newline characters
            r"%0d%0a",  # URL encoded CRLF
            r"%0a",     # URL encoded LF
            r"%0d",     # URL encoded CR
        ]
    
    async def dispatch(self, request: Request, call_next):
        """Validate and sanitize request input."""
        # Check URL path
        if self._contains_malicious_patterns(request.url.path):
            logger.warning(f"Malicious URL detected: {request.url.path}")
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"detail": "Invalid request"}
            )
        
        # Check query parameters
        for key, value in request.query_params.items():
            if self._contains_malicious_patterns(f"{key}={value}"):
                logger.warning(f"Malicious query parameter detected: {key}={value}")
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"detail": "Invalid query parameters"}
                )
        
        # Check headers for suspicious content
        for header_name, header_value in request.headers.items():
            if self._contains_malicious_patterns(header_value):
                logger.warning(f"Malicious header detected: {header_name}={header_value}")
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"detail": "Invalid request headers"}
                )
        
        return await call_next(request)
    
    def _contains_malicious_patterns(self, text: str) -> bool:
        """Check if text contains malicious patterns."""
        text_lower = text.lower()
        
        # Check SQL injection patterns
        for pattern in self.sql_injection_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return True
        
        # Check XSS patterns
        for pattern in self.xss_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return True
        
        # Check command injection patterns
        for pattern in self.command_injection_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return True
        
        # Check path traversal patterns
        for pattern in self.path_traversal_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return True
        
        # Check header injection patterns
        for pattern in self.header_injection_patterns:
            if re.search(pattern, text, re.IGNORECASE):  # Don't convert to lowercase for these
                return True
        
        return False


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Security headers middleware for enhanced protection."""
    
    def __init__(self, app):
        super().__init__(app)
        
        self.security_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self' https:; "
                "connect-src 'self' https:; "
                "frame-ancestors 'none';"
            ),
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": (
                "geolocation=(), microphone=(), camera=(), "
                "payment=(), usb=(), magnetometer=(), gyroscope=()"
            )
        }
    
    async def dispatch(self, request: Request, call_next):
        """Add security headers to response."""
        response = await call_next(request)
        
        # Add security headers
        for header_name, header_value in self.security_headers.items():
            response.headers[header_name] = header_value
        
        # Add server identification header
        response.headers["Server"] = "AI-Agent-Framework"
        
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Request logging middleware for security monitoring."""
    
    def __init__(self, app):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next):
        """Log requests for security monitoring."""
        start_time = time.time()
        client_ip = self._get_client_ip(request)
        
        # Log request
        logger.info(
            f"Request: {request.method} {request.url.path}",
            extra={
                "client_ip": client_ip,
                "method": request.method,
                "path": request.url.path,
                "query_params": dict(request.query_params),
                "user_agent": request.headers.get("User-Agent"),
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
        # Process request
        try:
            response = await call_next(request)
            
            # Log response
            duration = time.time() - start_time
            logger.info(
                f"Response: {response.status_code} in {duration:.3f}s",
                extra={
                    "client_ip": client_ip,
                    "status_code": response.status_code,
                    "duration_ms": round(duration * 1000, 2),
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            
            return response
            
        except Exception as e:
            # Log error
            duration = time.time() - start_time
            logger.error(
                f"Request failed: {str(e)} in {duration:.3f}s",
                extra={
                    "client_ip": client_ip,
                    "error": str(e),
                    "duration_ms": round(duration * 1000, 2),
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            raise
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request."""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else "unknown"


class APIKeyMiddleware(BaseHTTPMiddleware):
    """API key authentication middleware."""
    
    def __init__(self, app, api_keys: Optional[Set[str]] = None):
        super().__init__(app)
        self.api_keys = api_keys or set()
        self.protected_paths = {"/api/v1/admin/", "/api/v1/agents/", "/api/v1/workflows/"}
    
    async def dispatch(self, request: Request, call_next):
        """Validate API keys for protected endpoints."""
        # Check if path requires API key
        if not any(request.url.path.startswith(path) for path in self.protected_paths):
            return await call_next(request)
        
        # Skip API key check for auth endpoints
        if request.url.path.startswith("/api/v1/auth/"):
            return await call_next(request)
        
        # Check for API key in header
        api_key = request.headers.get("X-API-Key")
        if not api_key:
            # Check for Bearer token (JWT auth takes precedence)
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                return await call_next(request)
            
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "API key required"}
            )
        
        # Validate API key
        if self.api_keys and api_key not in self.api_keys:
            logger.warning(f"Invalid API key used: {api_key[:8]}...")
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Invalid API key"}
            )
        
        return await call_next(request)


# Configuration class for security settings
class SecurityConfig:
    """Security configuration settings."""
    
    def __init__(self):
        # Rate limiting settings
        self.rate_limit_per_minute = 600
        self.rate_limit_per_hour = 10000
        self.burst_limit = 100
        
        # IP filtering settings
        self.allowed_ips: List[str] = []
        self.blocked_ips: List[str] = []
        self.allowed_networks: List[str] = ["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"]
        
        # API key settings
        self.api_keys: Set[str] = set()
        
        # Security features
        self.enable_rate_limiting = True
        self.enable_ip_filtering = False
        self.enable_input_validation = True
        self.enable_security_headers = True
        self.enable_request_logging = True
        self.enable_api_key_auth = False


def create_security_middleware_stack(app, config: SecurityConfig):
    """Create and configure the security middleware stack."""
    
    # Add security headers (outermost layer)
    if config.enable_security_headers:
        app.add_middleware(SecurityHeadersMiddleware)
    
    # Add request logging
    if config.enable_request_logging:
        app.add_middleware(RequestLoggingMiddleware)
    
    # Add rate limiting
    if config.enable_rate_limiting:
        app.add_middleware(
            RateLimitMiddleware,
            requests_per_minute=config.rate_limit_per_minute,
            requests_per_hour=config.rate_limit_per_hour,
            burst_limit=config.burst_limit
        )
    
    # Add IP filtering
    if config.enable_ip_filtering:
        app.add_middleware(
            IPFilterMiddleware,
            allowed_ips=config.allowed_ips,
            blocked_ips=config.blocked_ips,
            allowed_networks=config.allowed_networks
        )
    
    # Add input validation
    if config.enable_input_validation:
        app.add_middleware(InputValidationMiddleware)
    
    # Add API key authentication
    if config.enable_api_key_auth:
        app.add_middleware(APIKeyMiddleware, api_keys=config.api_keys)
    
    return app