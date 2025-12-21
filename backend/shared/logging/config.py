"""Structured logging configuration for the AI Agent Framework."""

import logging
import os
import sys
from typing import Any, Dict

import structlog
from structlog.types import Processor


def configure_logging(
    log_level: str = "INFO",
    service_name: str = "ai-agent-framework",
    environment: str = "development"
) -> None:
    """Configure structured logging for the application.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        service_name: Name of the service for log identification
        environment: Environment name (development, staging, production)
    """
    # Convert log level string to logging constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=numeric_level,
    )
    
    # Shared processors for all log entries
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        add_service_context(service_name, environment),
    ]
    
    # Environment-specific configuration
    if environment == "production":
        # Production: JSON output for log aggregation
        processors = shared_processors + [
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer()
        ]
    else:
        # Development: Human-readable output
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(colors=True)
        ]
    
    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(numeric_level),
        logger_factory=structlog.WriteLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def add_service_context(service_name: str, environment: str) -> Processor:
    """Add service context to all log entries."""
    def processor(logger: Any, method_name: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
        event_dict["service"] = service_name
        event_dict["environment"] = environment
        return event_dict
    return processor


def get_logger(name: str = None) -> structlog.BoundLogger:
    """Get a configured logger instance.
    
    Args:
        name: Logger name, typically __name__ of the calling module
        
    Returns:
        Configured structlog logger
    """
    return structlog.get_logger(name)


# Initialize logging configuration from environment
def init_logging() -> None:
    """Initialize logging from environment variables."""
    log_level = os.getenv("LOG_LEVEL", "INFO")
    service_name = os.getenv("SERVICE_NAME", "ai-agent-framework")
    environment = os.getenv("ENVIRONMENT", "development")
    
    configure_logging(
        log_level=log_level,
        service_name=service_name,
        environment=environment
    )