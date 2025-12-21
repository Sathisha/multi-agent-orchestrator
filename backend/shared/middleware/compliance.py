# Compliance Middleware for Data Residency and Retention
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable, Dict, Any, Optional
import logging
import json
from datetime import datetime

from ..services.compliance import (
    DataResidencyService,
    DataRetentionService,
    DataRegion,
    DataClassification,
    DataResidencyViolationException
)

logger = logging.getLogger(__name__)


class ComplianceMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce compliance rules on data operations"""
    
    def __init__(
        self,
        app,
        current_region: DataRegion = DataRegion.US_EAST,
        enforce_residency: bool = True,
        log_violations: bool = True
    ):
        super().__init__(app)
        self.current_region = current_region
        self.enforce_residency = enforce_residency
        self.log_violations = log_violations
        
        # Data operations that should be checked for compliance
        self.monitored_operations = {
            "POST": ["agents", "workflows", "memories", "executions"],
            "PUT": ["agents", "workflows", "memories"],
            "PATCH": ["agents", "workflows", "memories"]
        }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and enforce compliance rules"""
        
        # Skip compliance checks for certain paths
        if self._should_skip_compliance_check(request):
            return await call_next(request)
        
        # Extract tenant context if available
        tenant_id = self._extract_tenant_id(request)
        if not tenant_id:
            return await call_next(request)
        
        # Check if this is a data operation that needs compliance validation
        if self._is_monitored_operation(request):
            try:
                await self._validate_compliance(request, tenant_id)
            except DataResidencyViolationException as e:
                logger.error(f"Data residency violation: {e}")
                if self.enforce_residency:
                    from fastapi import HTTPException
                    raise HTTPException(status_code=403, detail=str(e))
                else:
                    # Log violation but allow operation to continue
                    logger.warning(f"Data residency violation (not enforced): {e}")
        
        # Process the request
        response = await call_next(request)
        
        # Log compliance-related operations
        if self.log_violations and self._is_monitored_operation(request):
            await self._log_compliance_operation(request, response, tenant_id)
        
        return response
    
    def _should_skip_compliance_check(self, request: Request) -> bool:
        """Determine if compliance check should be skipped for this request"""
        skip_paths = [
            "/health",
            "/metrics",
            "/docs",
            "/openapi.json",
            "/api/v1/auth",
            "/api/v1/compliance"  # Skip compliance endpoints themselves
        ]
        
        return any(request.url.path.startswith(path) for path in skip_paths)
    
    def _extract_tenant_id(self, request: Request) -> Optional[str]:
        """Extract tenant ID from request context"""
        # Try to get from request state (set by tenant middleware)
        if hasattr(request.state, 'tenant_context'):
            return request.state.tenant_context.tenant_id
        
        # Try to get from headers
        tenant_header = request.headers.get('X-Tenant-ID')
        if tenant_header:
            return tenant_header
        
        # Try to extract from subdomain
        host = request.headers.get('host', '')
        if '.' in host:
            subdomain = host.split('.')[0]
            if subdomain not in ['www', 'api']:
                return subdomain
        
        return None
    
    def _is_monitored_operation(self, request: Request) -> bool:
        """Check if this request is a monitored data operation"""
        method = request.method
        path = request.url.path
        
        if method not in self.monitored_operations:
            return False
        
        # Check if path contains monitored resource types
        monitored_resources = self.monitored_operations[method]
        return any(resource in path for resource in monitored_resources)
    
    async def _validate_compliance(self, request: Request, tenant_id: str):
        """Validate compliance rules for the request"""
        # This is a simplified validation - in production you'd need database access
        # For now, we'll do basic validation based on request content
        
        try:
            # Get request body to analyze data type
            body = await self._get_request_body(request)
            if not body:
                return
            
            # Determine data type from request path and content
            data_type = self._determine_data_type(request, body)
            classification = self._determine_classification(body)
            
            # For demonstration, we'll create a service instance
            # In production, this would be injected via dependency
            from ..database import get_async_db
            async with get_async_db() as session:
                residency_service = DataResidencyService(session, tenant_id)
                
                # Validate data residency
                is_valid = await residency_service.validate_data_residency(
                    data_type=data_type,
                    target_region=self.current_region,
                    classification=classification
                )
                
                if not is_valid:
                    raise DataResidencyViolationException(
                        tenant_id=tenant_id,
                        data_type=data_type,
                        target_region=self.current_region,
                        classification=classification
                    )
        
        except Exception as e:
            if isinstance(e, DataResidencyViolationException):
                raise e
            else:
                logger.error(f"Error validating compliance: {e}")
                # Don't block request for validation errors
    
    async def _get_request_body(self, request: Request) -> Optional[Dict[str, Any]]:
        """Get request body as dictionary"""
        try:
            if request.method in ["POST", "PUT", "PATCH"]:
                body = await request.body()
                if body:
                    return json.loads(body.decode())
        except Exception as e:
            logger.warning(f"Could not parse request body: {e}")
        
        return None
    
    def _determine_data_type(self, request: Request, body: Dict[str, Any]) -> str:
        """Determine data type from request"""
        path = request.url.path.lower()
        
        if "agent" in path:
            return "agent_data"
        elif "workflow" in path:
            return "workflow_data"
        elif "memory" in path:
            return "memory_data"
        elif "execution" in path:
            return "execution_data"
        elif "user" in path:
            return "user_data"
        else:
            return "general_data"
    
    def _determine_classification(self, body: Dict[str, Any]) -> DataClassification:
        """Determine data classification from request content"""
        # Simple heuristics - in production this would be more sophisticated
        
        # Check for PII indicators
        pii_fields = ["email", "phone", "ssn", "address", "name"]
        if any(field in str(body).lower() for field in pii_fields):
            return DataClassification.PII
        
        # Check for sensitive data indicators
        sensitive_fields = ["password", "token", "key", "secret"]
        if any(field in str(body).lower() for field in sensitive_fields):
            return DataClassification.CONFIDENTIAL
        
        # Default to internal
        return DataClassification.INTERNAL
    
    async def _log_compliance_operation(
        self,
        request: Request,
        response: Response,
        tenant_id: str
    ):
        """Log compliance-related operation"""
        operation_log = {
            "timestamp": datetime.utcnow().isoformat(),
            "tenant_id": tenant_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "region": self.current_region.value,
            "compliance_check": "passed" if response.status_code < 400 else "failed"
        }
        
        logger.info(f"Compliance operation logged: {json.dumps(operation_log)}")


class DataRetentionMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce data retention policies"""
    
    def __init__(
        self,
        app,
        check_retention: bool = True,
        auto_cleanup: bool = False
    ):
        super().__init__(app)
        self.check_retention = check_retention
        self.auto_cleanup = auto_cleanup
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and check retention policies"""
        
        # Skip retention checks for certain paths
        if self._should_skip_retention_check(request):
            return await call_next(request)
        
        # Extract tenant context
        tenant_id = self._extract_tenant_id(request)
        if not tenant_id and self.check_retention:
            # Periodically check for expired data (simplified)
            await self._check_expired_data(tenant_id)
        
        return await call_next(request)
    
    def _should_skip_retention_check(self, request: Request) -> bool:
        """Determine if retention check should be skipped"""
        skip_paths = ["/health", "/metrics", "/docs", "/openapi.json"]
        return any(request.url.path.startswith(path) for path in skip_paths)
    
    def _extract_tenant_id(self, request: Request) -> Optional[str]:
        """Extract tenant ID from request"""
        if hasattr(request.state, 'tenant_context'):
            return request.state.tenant_context.tenant_id
        return request.headers.get('X-Tenant-ID')
    
    async def _check_expired_data(self, tenant_id: str):
        """Check for expired data and optionally clean up"""
        try:
            from ..database import get_async_db
            async with get_async_db() as session:
                retention_service = DataRetentionService(session, tenant_id)
                expired_data = await retention_service.identify_expired_data()
                
                if expired_data:
                    logger.info(f"Found {len(expired_data)} expired data items for tenant {tenant_id}")
                    
                    if self.auto_cleanup:
                        # In production, this would trigger a cleanup job
                        logger.info(f"Auto-cleanup would remove {len(expired_data)} items")
        
        except Exception as e:
            logger.error(f"Error checking expired data: {e}")


# Compliance decorator for individual functions
def enforce_data_residency(
    data_type: str,
    classification: DataClassification = DataClassification.INTERNAL,
    region: Optional[DataRegion] = None
):
    """Decorator to enforce data residency on individual functions"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Extract tenant_id from arguments
            tenant_id = kwargs.get('tenant_id')
            if not tenant_id and args:
                # Try to extract from first argument if it's a service
                if hasattr(args[0], 'tenant_id'):
                    tenant_id = args[0].tenant_id
            
            if tenant_id:
                try:
                    from ..database import get_async_db
                    async with get_async_db() as session:
                        residency_service = DataResidencyService(session, tenant_id)
                        
                        target_region = region or DataRegion.US_EAST
                        await residency_service.enforce_data_residency(
                            data_type=data_type,
                            target_region=target_region,
                            classification=classification
                        )
                except DataResidencyViolationException:
                    raise
                except Exception as e:
                    logger.error(f"Error enforcing data residency: {e}")
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator