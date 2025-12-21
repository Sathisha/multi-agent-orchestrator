# Guardrails Middleware
from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Callable, Dict, Any, Optional
import logging
import json
import time
import asyncio

from ..database.connection import get_database_session
from ..services.guardrails import GuardrailsService, ValidationContext, ContentCategory
from .tenant import get_tenant_context

logger = logging.getLogger(__name__)


class GuardrailsMiddleware(BaseHTTPMiddleware):
    """
    Middleware to automatically apply guardrails to API requests and responses
    
    This middleware:
    1. Validates input content in request bodies
    2. Validates output content in response bodies
    3. Enforces tenant-specific policies
    4. Logs violations and blocks harmful content
    """
    
    def __init__(self, app, enabled: bool = True, strict_mode: bool = False):
        super().__init__(app)
        self.enabled = enabled
        self.strict_mode = strict_mode  # If True, blocks all violations; if False, allows with warnings
        
        # Endpoints that should be checked for input validation
        self.input_validation_paths = {
            '/api/v1/agents/execute',
            '/api/v1/agents/chat',
            '/api/v1/workflows/execute',
            '/api/v1/memory/store',
        }
        
        # Endpoints that should be checked for output validation
        self.output_validation_paths = {
            '/api/v1/agents/execute',
            '/api/v1/agents/chat',
            '/api/v1/workflows/execute',
        }
        
        # Endpoints to skip entirely
        self.skip_paths = {
            '/api/v1/auth/',
            '/api/v1/health',
            '/api/v1/guardrails/',
            '/docs',
            '/openapi.json',
            '/favicon.ico'
        }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request through guardrails"""
        if not self.enabled:
            return await call_next(request)
        
        # Skip certain paths
        if any(request.url.path.startswith(skip_path) for skip_path in self.skip_paths):
            return await call_next(request)
        
        start_time = time.time()
        
        try:
            # Get tenant context
            tenant_context = get_tenant_context(request)
            tenant_id = tenant_context.get('tenant_id')
            
            if not tenant_id:
                # No tenant context, skip guardrails
                return await call_next(request)
            
            # Get database session
            async with get_database_session() as session:
                guardrails_service = GuardrailsService(session)
                
                # Validate input if applicable
                if request.url.path in self.input_validation_paths:
                    input_validation_result = await self._validate_input(
                        request, guardrails_service, tenant_id
                    )
                    
                    if not input_validation_result.is_valid and self.strict_mode:
                        return self._create_violation_response(input_validation_result, "input")
                
                # Process the request
                response = await call_next(request)
                
                # Validate output if applicable
                if request.url.path in self.output_validation_paths:
                    response = await self._validate_output(
                        request, response, guardrails_service, tenant_id
                    )
                
                # Add guardrails headers
                processing_time = (time.time() - start_time) * 1000
                response.headers["X-Guardrails-Processed"] = "true"
                response.headers["X-Guardrails-Time-Ms"] = str(round(processing_time, 2))
                
                return response
                
        except Exception as e:
            logger.error(f"Error in guardrails middleware: {e}")
            # Continue processing even if guardrails fail
            response = await call_next(request)
            response.headers["X-Guardrails-Error"] = "true"
            return response
    
    async def _validate_input(
        self,
        request: Request,
        guardrails_service: GuardrailsService,
        tenant_id: str
    ) -> Optional[Any]:
        """Validate request input content"""
        try:
            # Read request body
            body = await request.body()
            if not body:
                return None
            
            # Parse JSON content
            try:
                content_data = json.loads(body.decode())
            except (json.JSONDecodeError, UnicodeDecodeError):
                # Not JSON or not decodable, skip validation
                return None
            
            # Extract text content to validate
            text_content = self._extract_text_content(content_data)
            if not text_content:
                return None
            
            # Get user context
            user_id = getattr(request.state, 'user_id', None)
            agent_id = content_data.get('agent_id')
            session_id = content_data.get('session_id')
            
            # Validate content
            result = await guardrails_service.validate_agent_input(
                tenant_id=tenant_id,
                agent_id=agent_id,
                user_id=user_id,
                content=text_content,
                session_id=session_id
            )
            
            if not result.is_valid:
                logger.warning(
                    f"Input validation failed for tenant {tenant_id}: "
                    f"{len(result.violations)} violations detected"
                )
            
            return result
            
        except Exception as e:
            logger.error(f"Error validating input: {e}")
            return None
    
    async def _validate_output(
        self,
        request: Request,
        response: Response,
        guardrails_service: GuardrailsService,
        tenant_id: str
    ) -> Response:
        """Validate response output content"""
        try:
            # Only validate JSON responses
            if not response.headers.get("content-type", "").startswith("application/json"):
                return response
            
            # Read response body
            response_body = b""
            async for chunk in response.body_iterator:
                response_body += chunk
            
            if not response_body:
                return response
            
            # Parse JSON content
            try:
                content_data = json.loads(response_body.decode())
            except (json.JSONDecodeError, UnicodeDecodeError):
                # Not JSON or not decodable, return original response
                return Response(
                    content=response_body,
                    status_code=response.status_code,
                    headers=dict(response.headers)
                )
            
            # Extract text content to validate
            text_content = self._extract_text_content(content_data)
            if not text_content:
                return Response(
                    content=response_body,
                    status_code=response.status_code,
                    headers=dict(response.headers)
                )
            
            # Get user context
            user_id = getattr(request.state, 'user_id', None)
            agent_id = content_data.get('agent_id')
            session_id = content_data.get('session_id')
            
            # Validate content
            result = await guardrails_service.validate_agent_output(
                tenant_id=tenant_id,
                agent_id=agent_id,
                user_id=user_id,
                content=text_content,
                session_id=session_id
            )
            
            if not result.is_valid:
                logger.warning(
                    f"Output validation failed for tenant {tenant_id}: "
                    f"{len(result.violations)} violations detected"
                )
                
                if self.strict_mode:
                    return self._create_violation_response(result, "output")
                else:
                    # Sanitize content if available
                    if result.sanitized_content:
                        content_data = self._replace_text_content(content_data, result.sanitized_content)
                        response_body = json.dumps(content_data).encode()
            
            # Create new response with validated content
            headers = dict(response.headers)
            headers["X-Guardrails-Output-Validated"] = "true"
            headers["X-Guardrails-Risk-Score"] = str(result.risk_score)
            
            return Response(
                content=response_body,
                status_code=response.status_code,
                headers=headers
            )
            
        except Exception as e:
            logger.error(f"Error validating output: {e}")
            # Return original response on error
            return response
    
    def _extract_text_content(self, data: Any) -> Optional[str]:
        """Extract text content from request/response data"""
        if isinstance(data, str):
            return data
        elif isinstance(data, dict):
            # Look for common text fields
            text_fields = ['content', 'message', 'text', 'prompt', 'response', 'output']
            for field in text_fields:
                if field in data and isinstance(data[field], str):
                    return data[field]
            
            # Recursively search nested objects
            for value in data.values():
                text_content = self._extract_text_content(value)
                if text_content:
                    return text_content
        elif isinstance(data, list):
            # Search list items
            for item in data:
                text_content = self._extract_text_content(item)
                if text_content:
                    return text_content
        
        return None
    
    def _replace_text_content(self, data: Any, sanitized_content: str) -> Any:
        """Replace text content with sanitized version"""
        if isinstance(data, str):
            return sanitized_content
        elif isinstance(data, dict):
            result = data.copy()
            # Look for common text fields
            text_fields = ['content', 'message', 'text', 'prompt', 'response', 'output']
            for field in text_fields:
                if field in result and isinstance(result[field], str):
                    result[field] = sanitized_content
                    return result
            
            # Recursively replace in nested objects
            for key, value in result.items():
                result[key] = self._replace_text_content(value, sanitized_content)
            return result
        elif isinstance(data, list):
            # Replace in list items
            return [self._replace_text_content(item, sanitized_content) for item in data]
        
        return data
    
    def _create_violation_response(self, result: Any, source: str) -> JSONResponse:
        """Create response for guardrail violations"""
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": "Content validation failed",
                "detail": f"The {source} content violates content policies",
                "violations": result.violations,
                "risk_score": result.risk_score,
                "risk_level": result.risk_level.value,
                "blocked_phrases": result.blocked_phrases
            },
            headers={
                "X-Guardrails-Blocked": "true",
                "X-Guardrails-Risk-Level": result.risk_level.value
            }
        )


class GuardrailsConfig:
    """Configuration for guardrails middleware"""
    
    def __init__(
        self,
        enabled: bool = True,
        strict_mode: bool = False,
        input_validation_paths: Optional[set] = None,
        output_validation_paths: Optional[set] = None,
        skip_paths: Optional[set] = None
    ):
        self.enabled = enabled
        self.strict_mode = strict_mode
        self.input_validation_paths = input_validation_paths or set()
        self.output_validation_paths = output_validation_paths or set()
        self.skip_paths = skip_paths or set()


def create_guardrails_middleware(config: Optional[GuardrailsConfig] = None):
    """Factory function to create guardrails middleware with configuration"""
    if config is None:
        config = GuardrailsConfig()
    
    class ConfiguredGuardrailsMiddleware(GuardrailsMiddleware):
        def __init__(self, app):
            super().__init__(
                app,
                enabled=config.enabled,
                strict_mode=config.strict_mode
            )
            
            if config.input_validation_paths:
                self.input_validation_paths.update(config.input_validation_paths)
            if config.output_validation_paths:
                self.output_validation_paths.update(config.output_validation_paths)
            if config.skip_paths:
                self.skip_paths.update(config.skip_paths)
    
    return ConfiguredGuardrailsMiddleware