"""
Structured Logging Configuration

This module provides structured logging capabilities with:
- JSON formatting for machine-readable logs
- Correlation ID tracking for distributed tracing
- Multiple output formats (JSON, text, syslog)
- Log aggregation and filtering
- Performance monitoring integration
"""

import logging
import logging.config
import json
import sys
import os
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from contextvars import ContextVar
import traceback

from pythonjsonlogger import jsonlogger


# Context variables for request correlation
correlation_id_var: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)
tenant_id_var: ContextVar[Optional[str]] = ContextVar('tenant_id', default=None)
user_id_var: ContextVar[Optional[str]] = ContextVar('user_id', default=None)


class CorrelationFilter(logging.Filter):
    """Add correlation ID and context to log records"""
    
    def filter(self, record):
        # Add correlation ID
        correlation_id = correlation_id_var.get()
        if correlation_id:
            record.correlation_id = correlation_id
        else:
            record.correlation_id = str(uuid.uuid4())
        
        # Add tenant context
        tenant_id = tenant_id_var.get()
        if tenant_id:
            record.tenant_id = tenant_id
        
        # Add user context
        user_id = user_id_var.get()
        if user_id:
            record.user_id = user_id
        
        # Add timestamp
        record.timestamp = datetime.utcnow().isoformat()
        
        # Add service name
        record.service = 'ai-agent-framework'
        
        return True


class CustomJSONFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter with additional fields"""
    
    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        
        # Add standard fields
        log_record['timestamp'] = getattr(record, 'timestamp', datetime.utcnow().isoformat())
        log_record['level'] = record.levelname
        log_record['logger'] = record.name
        log_record['service'] = getattr(record, 'service', 'ai-agent-framework')
        
        # Add correlation fields
        if hasattr(record, 'correlation_id'):
            log_record['correlation_id'] = record.correlation_id
        if hasattr(record, 'tenant_id'):
            log_record['tenant_id'] = record.tenant_id
        if hasattr(record, 'user_id'):
            log_record['user_id'] = record.user_id
        
        # Add exception info if present
        if record.exc_info:
            log_record['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': traceback.format_exception(*record.exc_info)
            }
        
        # Add extra fields from the log call
        for key, value in message_dict.items():
            if key not in log_record:
                log_record[key] = value


class PerformanceFilter(logging.Filter):
    """Filter for performance-related logs"""
    
    def filter(self, record):
        # Only pass through performance-related logs
        performance_keywords = [
            'duration', 'response_time', 'query_time', 'execution_time',
            'performance', 'slow', 'timeout', 'latency'
        ]
        
        message = record.getMessage().lower()
        return any(keyword in message for keyword in performance_keywords)


class SecurityFilter(logging.Filter):
    """Filter for security-related logs"""
    
    def filter(self, record):
        # Only pass through security-related logs
        security_keywords = [
            'auth', 'login', 'logout', 'permission', 'access', 'denied',
            'security', 'violation', 'breach', 'attack', 'suspicious'
        ]
        
        message = record.getMessage().lower()
        return any(keyword in message for keyword in security_keywords)


class AuditFilter(logging.Filter):
    """Filter for audit-related logs"""
    
    def filter(self, record):
        # Only pass through audit-related logs
        audit_keywords = [
            'audit', 'create', 'update', 'delete', 'modify', 'change',
            'compliance', 'policy', 'violation', 'forensic'
        ]
        
        message = record.getMessage().lower()
        return any(keyword in message for keyword in audit_keywords)


def setup_structured_logging(
    log_level: str = "INFO",
    log_format: str = "json",
    enable_file_logging: bool = True,
    log_file_path: str = "/app/logs/app.log"
):
    """
    Setup structured logging configuration
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Log format (json, text)
        enable_file_logging: Whether to enable file logging
        log_file_path: Path to log file
    """
    
    # Create logs directory if it doesn't exist
    if enable_file_logging:
        os.makedirs(os.path.dirname(log_file_path), exist_ok=True)
    
    # Define formatters
    formatters = {
        'json': {
            '()': CustomJSONFormatter,
            'format': '%(timestamp)s %(level)s %(logger)s %(message)s'
        },
        'text': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - [%(correlation_id)s] - %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        }
    }
    
    # Define handlers
    handlers = {
        'console': {
            'class': 'logging.StreamHandler',
            'level': log_level,
            'formatter': log_format,  # This should reference a formatter name
            'stream': sys.stdout,
            'filters': ['correlation']
        }
    }
    
    # Add file handlers if enabled
    if enable_file_logging:
        handlers.update({
            'file_all': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': log_level,
                'formatter': log_format,
                'filename': log_file_path,
                'maxBytes': 10485760,  # 10MB
                'backupCount': 5,
                'filters': ['correlation']
            },
            'file_performance': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': 'INFO',
                'formatter': log_format,
                'filename': log_file_path.replace('.log', '_performance.log'),
                'maxBytes': 10485760,  # 10MB
                'backupCount': 5,
                'filters': ['correlation', 'performance']
            },
            'file_security': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': 'WARNING',
                'formatter': log_format,
                'filename': log_file_path.replace('.log', '_security.log'),
                'maxBytes': 10485760,  # 10MB
                'backupCount': 10,  # Keep more security logs
                'filters': ['correlation', 'security']
            },
            'file_audit': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': 'INFO',
                'formatter': log_format,
                'filename': log_file_path.replace('.log', '_audit.log'),
                'maxBytes': 10485760,  # 10MB
                'backupCount': 20,  # Keep many audit logs
                'filters': ['correlation', 'audit']
            }
        })
    
    # Define filters
    filters = {
        'correlation': {
            '()': CorrelationFilter
        },
        'performance': {
            '()': PerformanceFilter
        },
        'security': {
            '()': SecurityFilter
        },
        'audit': {
            '()': AuditFilter
        }
    }
    
    # Define loggers
    loggers = {
        '': {  # Root logger
            'level': log_level,
            'handlers': ['console'] + (['file_all'] if enable_file_logging else [])
        },
        'performance': {
            'level': 'INFO',
            'handlers': ['console'] + (['file_performance'] if enable_file_logging else []),
            'propagate': False
        },
        'security': {
            'level': 'WARNING',
            'handlers': ['console'] + (['file_security'] if enable_file_logging else []),
            'propagate': False
        },
        'audit': {
            'level': 'INFO',
            'handlers': ['console'] + (['file_audit'] if enable_file_logging else []),
            'propagate': False
        },
        'uvicorn': {
            'level': 'INFO',
            'handlers': ['console'],
            'propagate': False
        },
        'sqlalchemy.engine': {
            'level': 'WARNING',  # Reduce SQL query noise
            'handlers': ['console'],
            'propagate': False
        }
    }
    
    # Configure logging
    logging_config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': formatters,
        'filters': filters,
        'handlers': handlers,
        'loggers': loggers
    }
    
    logging.config.dictConfig(logging_config)


class StructuredLogger:
    """Structured logger with context management"""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.performance_logger = logging.getLogger('performance')
        self.security_logger = logging.getLogger('security')
        self.audit_logger = logging.getLogger('audit')
    
    def set_correlation_id(self, correlation_id: str):
        """Set correlation ID for current context"""
        correlation_id_var.set(correlation_id)
    
    def set_tenant_context(self, tenant_id: str):
        """Set tenant context for current request"""
        tenant_id_var.set(tenant_id)
    
    def set_user_context(self, user_id: str):
        """Set user context for current request"""
        user_id_var.set(user_id)
    
    def clear_context(self):
        """Clear all context variables"""
        correlation_id_var.set(None)
        tenant_id_var.set(None)
        user_id_var.set(None)
    
    def info(self, message: str, **kwargs):
        """Log info message with context"""
        self.logger.info(message, extra=kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message with context"""
        self.logger.warning(message, extra=kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message with context"""
        self.logger.error(message, extra=kwargs)
    
    def debug(self, message: str, **kwargs):
        """Log debug message with context"""
        self.logger.debug(message, extra=kwargs)
    
    def critical(self, message: str, **kwargs):
        """Log critical message with context"""
        self.logger.critical(message, extra=kwargs)
    
    def performance(self, message: str, duration: float = None, **kwargs):
        """Log performance-related message"""
        extra = kwargs.copy()
        if duration is not None:
            extra['duration_ms'] = duration * 1000
        self.performance_logger.info(message, extra=extra)
    
    def security(self, message: str, **kwargs):
        """Log security-related message"""
        self.security_logger.warning(message, extra=kwargs)
    
    def audit(self, action: str, resource_type: str, resource_id: str = None, **kwargs):
        """Log audit trail message"""
        extra = {
            'action': action,
            'resource_type': resource_type,
            'resource_id': resource_id,
            **kwargs
        }
        self.audit_logger.info(f"Audit: {action} {resource_type}", extra=extra)


def get_logger(name: str) -> StructuredLogger:
    """Get a structured logger instance"""
    return StructuredLogger(name)


# Context managers for request correlation
class RequestContext:
    """Context manager for request-scoped logging context"""
    
    def __init__(self, correlation_id: str = None, tenant_id: str = None, user_id: str = None):
        self.correlation_id = correlation_id or str(uuid.uuid4())
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.previous_correlation_id = None
        self.previous_tenant_id = None
        self.previous_user_id = None
    
    def __enter__(self):
        # Save previous context
        self.previous_correlation_id = correlation_id_var.get()
        self.previous_tenant_id = tenant_id_var.get()
        self.previous_user_id = user_id_var.get()
        
        # Set new context
        correlation_id_var.set(self.correlation_id)
        if self.tenant_id:
            tenant_id_var.set(self.tenant_id)
        if self.user_id:
            user_id_var.set(self.user_id)
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Restore previous context
        correlation_id_var.set(self.previous_correlation_id)
        tenant_id_var.set(self.previous_tenant_id)
        user_id_var.set(self.previous_user_id)


# Initialize logging on module import (only if not in test mode)
if not os.getenv('TESTING', '').lower() == 'true':
    setup_structured_logging(
        log_level=os.getenv('LOG_LEVEL', 'INFO'),
        log_format=os.getenv('LOG_FORMAT', 'json'),
        enable_file_logging=os.getenv('ENABLE_FILE_LOGGING', 'true').lower() == 'true',
        log_file_path=os.getenv('LOG_FILE_PATH', '/app/logs/app.log')
    )