"""Audit middleware for automatic logging of all system operations."""

import asyncio
import json
import time
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from ..models.audit import AuditEventType, AuditSeverity, AuditOutcome
from ..services.audit import AuditService
from ..database import get_database_session


class AuditMiddleware(BaseHTTPMiddleware):
    """
    Middleware for comprehensive audit logging of all HTTP requests and responses.
    
    This middleware automatically captures and logs all API interactions,
    providing complete audit trails for compliance and security monitoring.
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.sensitive_headers = {
            'authorization', 'cookie', 'x-api-key', 'x-auth-token',
            'x-access-token', 'x-refresh-token'
        }
        self.sensitive_fields = {
            'password', 'token', 'secret', 'key', 'credential',
            'auth', 'authorization', 'api_key', 'access_token',
            'refresh_token', 'private_key', 'certificate'
        }
        self.excluded_paths = {
            '/health', '/metrics', '/favicon.ico', '/docs', '/openapi.json',
            '/redoc', '/static'
        }
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request and response with comprehensive audit logging."""
        
        # Skip audit logging for excluded paths
        if any(request.url.path.startswith(path) for path in self.excluded_paths):
            return await call_next(request)
        
        # Generate correlation ID for request tracing
        correlation_id = str(uuid.uuid4())
        request.state.correlation_id = correlation_id
        
        # Capture request start time
        start_time = time.time()
        
        # Extract request information
        request_info = await self._extract_request_info(request)
        
        # Process the request
        response = None
        error_info = None
        
        try:
            response = await call_next(request)
            outcome = AuditOutcome.SUCCESS if response.status_code < 400 else AuditOutcome.FAILURE
            
        except Exception as e:
            outcome = AuditOutcome.FAILURE
            error_info = {
                'error_type': type(e).__name__,
                'error_message': str(e)
            }
            # Re-raise the exception after logging
            raise
        
        finally:
            # Calculate request duration
            duration = time.time() - start_time
            
            # Extract response information
            response_info = self._extract_response_info(response) if response else {}
            
            # Log the audit event asynchronously
            asyncio.create_task(
                self._log_audit_event(
                    request=request,
                    response=response,
                    correlation_id=correlation_id,
                    duration=duration,
                    request_info=request_info,
                    response_info=response_info,
                    outcome=outcome,
                    error_info=error_info
                )
            )
        
        return response
    
    async def _extract_request_info(self, request: Request) -> Dict[str, Any]:
        """Extract comprehensive request information for audit logging."""
        
        # Basic request information
        request_info = {
            'method': request.method,
            'url': str(request.url),
            'path': request.url.path,
            'query_params': dict(request.query_params),
            'headers': self._sanitize_headers(dict(request.headers)),
            'client_ip': self._get_client_ip(request),
            'user_agent': request.headers.get('user-agent'),
            'content_type': request.headers.get('content-type'),
            'content_length': request.headers.get('content-length')
        }
        
        # Extract request body for POST/PUT/PATCH requests
        if request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
            try:
                # Read body (this consumes the stream, so we need to be careful)
                body = await request.body()
                if body:
                    content_type = request.headers.get('content-type', '')
                    if 'application/json' in content_type:
                        try:
                            request_data = json.loads(body.decode('utf-8'))
                            request_info['body'] = self._sanitize_data(request_data)
                        except (json.JSONDecodeError, UnicodeDecodeError):
                            request_info['body'] = '<binary_or_invalid_json>'
                    elif 'application/x-www-form-urlencoded' in content_type:
                        request_info['body'] = '<form_data>'
                    elif 'multipart/form-data' in content_type:
                        request_info['body'] = '<multipart_data>'
                    else:
                        request_info['body'] = f'<{content_type}>'
            except Exception:
                request_info['body'] = '<error_reading_body>'
        
        return request_info
    
    def _extract_response_info(self, response: Optional[Response]) -> Dict[str, Any]:
        """Extract response information for audit logging."""
        
        if not response:
            return {}
        
        response_info = {
            'status_code': response.status_code,
            'headers': self._sanitize_headers(dict(response.headers)),
            'content_type': response.headers.get('content-type'),
            'content_length': response.headers.get('content-length')
        }
        
        # Note: We don't capture response body to avoid performance issues
        # and potential memory problems with large responses
        
        return response_info
    
    def _sanitize_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """Sanitize headers by masking sensitive information."""
        
        sanitized = {}
        for key, value in headers.items():
            key_lower = key.lower()
            if key_lower in self.sensitive_headers:
                sanitized[key] = self._mask_sensitive_value(value)
            else:
                sanitized[key] = value
        
        return sanitized
    
    def _sanitize_data(self, data: Any) -> Any:
        """Recursively sanitize data by masking sensitive fields."""
        
        if isinstance(data, dict):
            sanitized = {}
            for key, value in data.items():
                key_lower = key.lower()
                if any(sensitive in key_lower for sensitive in self.sensitive_fields):
                    sanitized[key] = self._mask_sensitive_value(str(value))
                else:
                    sanitized[key] = self._sanitize_data(value)
            return sanitized
        
        elif isinstance(data, list):
            return [self._sanitize_data(item) for item in data]
        
        else:
            return data
    
    def _mask_sensitive_value(self, value: str) -> str:
        """Mask sensitive values while preserving some information for debugging."""
        
        if not value:
            return value
        
        if len(value) <= 4:
            return '*' * len(value)
        
        # Show first 2 and last 2 characters
        return value[:2] + '*' * (len(value) - 4) + value[-2:]
    
    def _get_client_ip(self, request: Request) -> Optional[str]:
        """Extract client IP address from request headers."""
        
        # Check for forwarded headers (common in load balancer setups)
        forwarded_for = request.headers.get('x-forwarded-for')
        if forwarded_for:
            # Take the first IP in the chain
            return forwarded_for.split(',')[0].strip()
        
        real_ip = request.headers.get('x-real-ip')
        if real_ip:
            return real_ip
        
        # Fall back to direct client IP
        if hasattr(request, 'client') and request.client:
            return request.client.host
        
        return None
    
    def _determine_event_type(self, request: Request, response: Optional[Response]) -> AuditEventType:
        """Determine the appropriate audit event type based on the request."""
        
        path = request.url.path.lower()
        method = request.method.upper()
        
        # Authentication endpoints
        if '/auth/' in path:
            if 'login' in path:
                if response and response.status_code >= 400:
                    return AuditEventType.USER_LOGIN_FAILED
                return AuditEventType.USER_LOGIN
            elif 'logout' in path:
                return AuditEventType.USER_LOGOUT
            elif 'register' in path:
                return AuditEventType.USER_CREATED
        
        # Agent operations
        elif '/agents/' in path:
            if method == 'POST':
                return AuditEventType.AGENT_CREATED
            elif method in ['PUT', 'PATCH']:
                return AuditEventType.AGENT_UPDATED
            elif method == 'DELETE':
                return AuditEventType.AGENT_DELETED
            elif 'execute' in path:
                if response and response.status_code >= 400:
                    return AuditEventType.AGENT_EXECUTION_FAILED
                return AuditEventType.AGENT_EXECUTED
        
        # Workflow operations
        elif '/workflows/' in path:
            if method == 'POST':
                return AuditEventType.WORKFLOW_CREATED
            elif method in ['PUT', 'PATCH']:
                return AuditEventType.WORKFLOW_UPDATED
            elif method == 'DELETE':
                return AuditEventType.WORKFLOW_DELETED
            elif 'execute' in path:
                if response and response.status_code >= 400:
                    return AuditEventType.WORKFLOW_EXECUTION_FAILED
                return AuditEventType.WORKFLOW_EXECUTED
        
        # Tool operations
        elif '/tools/' in path:
            if method == 'POST':
                return AuditEventType.TOOL_CREATED
            elif method in ['PUT', 'PATCH']:
                return AuditEventType.TOOL_UPDATED
            elif method == 'DELETE':
                return AuditEventType.TOOL_DELETED
            elif 'execute' in path:
                return AuditEventType.TOOL_EXECUTED
        
        # MCP operations
        elif '/mcp/' in path:
            if 'connect' in path:
                return AuditEventType.MCP_SERVER_CONNECTED
            elif 'disconnect' in path:
                return AuditEventType.MCP_SERVER_DISCONNECTED
            else:
                return AuditEventType.MCP_CALL_MADE
        
        # Data operations
        elif method == 'GET' and any(endpoint in path for endpoint in ['/data/', '/export/', '/download/']):
            return AuditEventType.DATA_ACCESSED
        elif 'export' in path:
            return AuditEventType.DATA_EXPORTED
        elif 'import' in path:
            return AuditEventType.DATA_IMPORTED
        
        # Role and permission operations
        elif '/roles/' in path or '/permissions/' in path:
            if method == 'POST':
                return AuditEventType.ROLE_CREATED
            elif method in ['PUT', 'PATCH']:
                return AuditEventType.ROLE_UPDATED
            elif method == 'DELETE':
                return AuditEventType.ROLE_DELETED
        
        # Access denied (4xx responses)
        elif response and response.status_code in [401, 403]:
            return AuditEventType.ACCESS_DENIED
        
        # Security violations (other 4xx responses)
        elif response and 400 <= response.status_code < 500:
            return AuditEventType.SECURITY_VIOLATION
        
        # Default to data access for GET requests
        elif method == 'GET':
            return AuditEventType.DATA_ACCESSED
        
        # Default to configuration change for other operations
        else:
            return AuditEventType.CONFIGURATION_CHANGED
    
    def _determine_severity(self, request: Request, response: Optional[Response], error_info: Optional[Dict]) -> AuditSeverity:
        """Determine the severity level of the audit event."""
        
        # Critical severity for security violations and system errors
        if error_info or (response and response.status_code >= 500):
            return AuditSeverity.CRITICAL
        
        # High severity for authentication failures and access denials
        if response and response.status_code in [401, 403]:
            return AuditSeverity.HIGH
        
        # Medium severity for client errors and data modifications
        if response and 400 <= response.status_code < 500:
            return AuditSeverity.MEDIUM
        
        # Medium severity for data modifications
        if request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
            return AuditSeverity.MEDIUM
        
        # Low severity for read operations
        return AuditSeverity.LOW
    
    def _extract_resource_info(self, request: Request) -> tuple[Optional[str], Optional[str], Optional[str]]:
        """Extract resource information from the request path."""
        
        path_parts = request.url.path.strip('/').split('/')
        
        if len(path_parts) >= 2:
            resource_type = path_parts[1]  # e.g., 'agents', 'workflows', 'tools'
            
            # Try to extract resource ID (usually the next path segment)
            resource_id = None
            resource_name = None
            
            if len(path_parts) >= 3 and path_parts[2] not in ['execute', 'export', 'import']:
                resource_id = path_parts[2]
            
            return resource_type, resource_id, resource_name
        
        return None, None, None
    
    async def _log_audit_event(
        self,
        request: Request,
        response: Optional[Response],
        correlation_id: str,
        duration: float,
        request_info: Dict[str, Any],
        response_info: Dict[str, Any],
        outcome: AuditOutcome,
        error_info: Optional[Dict[str, Any]]
    ):
        """Log the audit event asynchronously."""
        
        try:
            # Get database session
            async with get_database_session() as session:
                # Extract user information from request state
                user_id = getattr(request.state, 'user_id', None)
                
                # Create audit service
                audit_service = AuditService(session, user_id=user_id)
                
                # Determine event details
                event_type = self._determine_event_type(request, response)
                severity = self._determine_severity(request, response, error_info)
                resource_type, resource_id, resource_name = self._extract_resource_info(request)
                
                # Create audit message
                status_code = response.status_code if response else 'ERROR'
                message = f"{request.method} {request.url.path} - {status_code} ({duration:.3f}s)"
                
                # Prepare audit details
                details = {
                    'request': request_info,
                    'response': response_info,
                    'duration_seconds': round(duration, 3),
                    'correlation_id': correlation_id
                }
                
                if error_info:
                    details['error'] = error_info
                
                # Log the audit event
                await audit_service.log_event(
                    event_type=event_type,
                    action=f"{request.method.lower()}_{request.url.path.replace('/', '_').strip('_')}",
                    message=message,
                    outcome=outcome,
                    severity=severity,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    resource_name=resource_name,
                    details=details,
                    request_data=request_info.get('body'),
                    response_data=response_info,
                    error_code=str(response.status_code) if response and response.status_code >= 400 else None,
                    error_message=error_info.get('error_message') if error_info else None,
                    source_ip=request_info.get('client_ip'),
                    user_agent=request_info.get('user_agent'),
                    source_service='api_gateway',
                    session_id=getattr(request.state, 'session_id', None),
                    correlation_id=correlation_id,
                    compliance_tags=['api_access', 'http_request']
                )
                
        except Exception as e:
            # Log audit logging failures to system logs
            print(f"Failed to log audit event: {e}")
            # Don't raise the exception to avoid breaking the main request flow