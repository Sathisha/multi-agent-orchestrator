"""Main FastAPI application entry point for AI Agent Framework."""

import logging
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app

from shared.config.settings import get_settings
from shared.logging.structured_logging import setup_structured_logging, get_logger
from shared.api import api_router
from shared.middleware.compliance import ComplianceMiddleware
from shared.middleware.audit import AuditMiddleware
from shared.middleware.security import SecurityConfig, create_security_middleware_stack
from shared.services.monitoring import monitoring_service

# Initialize structured logging
setup_structured_logging()
# logging.basicConfig(level=logging.INFO)
logger = get_logger(__name__)

# Get settings
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan event handler."""
    # Startup
    logger.info(
        f"Starting AI Agent Framework API version={settings.version} environment={settings.environment} service={settings.service_name}"
    )
    
    # Initialize database tables
    from shared.database.connection import init_database_on_startup
    await init_database_on_startup()
    logger.info("Database initialized")
    
    # Start monitoring service
    await monitoring_service.start()
    logger.info("Monitoring service started")
    
    # Start agent lifecycle monitoring
    from shared.services.agent_executor import lifecycle_manager
    from shared.services.agent_state_manager import global_state_manager
    
    await lifecycle_manager.start_monitoring()
    await global_state_manager.start_global_monitoring()
    logger.info("Agent lifecycle monitoring started")
    
    yield
    
    # Shutdown
    logger.info("Shutting down AI Agent Framework API")
    
    # Stop monitoring service
    await monitoring_service.stop()
    logger.info("Monitoring service stopped")
    
    # Stop agent lifecycle monitoring
    await lifecycle_manager.stop_monitoring()
    await global_state_manager.stop_global_monitoring()
    logger.info("Agent lifecycle monitoring stopped")


# Create FastAPI application
app = FastAPI(
    title="AI Agent Framework API",
    description="A comprehensive platform for creating, orchestrating, and deploying AI agents",
    version=settings.version,
    debug=settings.debug,
    lifespan=lifespan,
)

# Configure security middleware
security_config = SecurityConfig()
security_config.enable_rate_limiting = True
security_config.enable_input_validation = False
security_config.enable_security_headers = False  # Disabled to allow Swagger UI assets
security_config.enable_request_logging = True

# Apply security middleware stack
app = create_security_middleware_stack(app, security_config)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.api.cors_origins,
    allow_credentials=settings.api.cors_credentials,
    allow_methods=settings.api.cors_methods,
    allow_headers=settings.api.cors_headers,
)

# Add audit middleware
app.add_middleware(AuditMiddleware)

# Add compliance middleware
# app.add_middleware(ComplianceMiddleware)

# Include API routers
app.include_router(api_router)

# Add monitoring endpoints
from shared.api.monitoring import router as monitoring_router
app.include_router(monitoring_router)

# Add Prometheus metrics endpoint (use monitoring service metrics)
@app.get("/metrics")
async def get_prometheus_metrics():
    """Get Prometheus metrics"""
    from fastapi import Response
    metrics_data = monitoring_service.get_metrics_data()
    return Response(content=metrics_data, media_type="text/plain")


@app.get("/")
async def root():
    """Root endpoint for health check."""
    return {
        "message": "AI Agent Framework API",
        "version": settings.version,
        "environment": settings.environment,
        "status": "healthy"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": settings.service_name,
        "version": settings.version,
        "environment": settings.environment
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.api.host,
        port=settings.api.port,
        reload=settings.api.reload,
        workers=settings.api.workers if not settings.api.reload else 1,
        log_config=None,  # Use our custom logging configuration
    )