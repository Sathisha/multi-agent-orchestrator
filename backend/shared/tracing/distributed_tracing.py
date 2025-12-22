"""
Distributed Tracing Configuration

This module provides distributed tracing capabilities using OpenTelemetry:
- Request correlation across services
- Performance monitoring and profiling
- Error tracking and debugging
- Service dependency mapping
"""

import os
import logging
from typing import Dict, Any, Optional, Callable
from functools import wraps
import time
import asyncio

from opentelemetry import trace, baggage
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.propagate import set_global_textmap
from opentelemetry.propagators.b3 import B3MultiFormat
from opentelemetry.propagators.jaeger import JaegerPropagator
from opentelemetry.propagators.composite import CompositeHTTPPropagator


logger = logging.getLogger(__name__)


class TracingConfig:
    """Configuration for distributed tracing"""
    
    def __init__(self):
        self.service_name = os.getenv('SERVICE_NAME', 'ai-agent-framework')
        self.service_version = os.getenv('SERVICE_VERSION', '1.0.0')
        self.environment = os.getenv('ENVIRONMENT', 'development')
        
        # Tracing backend configuration
        self.tracing_enabled = os.getenv('TRACING_ENABLED', 'true').lower() == 'true'
        self.jaeger_endpoint = os.getenv('JAEGER_ENDPOINT', 'http://jaeger:14268/api/traces')
        self.otlp_endpoint = os.getenv('OTLP_ENDPOINT', 'http://otel-collector:4317')
        self.console_exporter = os.getenv('CONSOLE_EXPORTER', 'false').lower() == 'true'
        
        # Sampling configuration
        self.sample_rate = float(os.getenv('TRACE_SAMPLE_RATE', '1.0'))  # 100% sampling in dev
        
        # Custom attributes
        self.resource_attributes = {
            'service.name': self.service_name,
            'service.version': self.service_version,
            'deployment.environment': self.environment,
            'service.instance.id': os.getenv('HOSTNAME', 'unknown')
        }


def setup_tracing(config: TracingConfig = None) -> trace.Tracer:
    """
    Setup distributed tracing with OpenTelemetry
    
    Args:
        config: Tracing configuration
        
    Returns:
        Configured tracer instance
    """
    if config is None:
        config = TracingConfig()
    
    if not config.tracing_enabled:
        logger.info("Distributed tracing is disabled")
        return trace.NoOpTracer()
    
    # Create resource with service information
    resource = Resource.create(config.resource_attributes)
    
    # Create tracer provider
    tracer_provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(tracer_provider)
    
    # Configure exporters
    exporters = []
    
    # Jaeger exporter
    if config.jaeger_endpoint:
        try:
            jaeger_exporter = JaegerExporter(
                endpoint=config.jaeger_endpoint,
                collector_endpoint=config.jaeger_endpoint.replace('/api/traces', '/api/traces')
            )
            exporters.append(jaeger_exporter)
            logger.info(f"Jaeger exporter configured: {config.jaeger_endpoint}")
        except Exception as e:
            logger.warning(f"Failed to configure Jaeger exporter: {e}")
    
    # OTLP exporter
    if config.otlp_endpoint:
        try:
            otlp_exporter = OTLPSpanExporter(endpoint=config.otlp_endpoint)
            exporters.append(otlp_exporter)
            logger.info(f"OTLP exporter configured: {config.otlp_endpoint}")
        except Exception as e:
            logger.warning(f"Failed to configure OTLP exporter: {e}")
    
    # Console exporter for development
    if config.console_exporter:
        console_exporter = ConsoleSpanExporter()
        exporters.append(console_exporter)
        logger.info("Console exporter configured")
    
    # Add span processors
    for exporter in exporters:
        span_processor = BatchSpanProcessor(exporter)
        tracer_provider.add_span_processor(span_processor)
    
    # Configure propagators
    set_global_textmap(
        CompositeHTTPPropagator([
            JaegerPropagator(),
            B3MultiFormat(),
        ])
    )
    
    # Get tracer
    tracer = trace.get_tracer(__name__)
    
    logger.info(f"Distributed tracing initialized for service: {config.service_name}")
    return tracer


def instrument_app(app):
    """
    Instrument FastAPI application with automatic tracing
    
    Args:
        app: FastAPI application instance
    """
    try:
        # Instrument FastAPI
        FastAPIInstrumentor.instrument_app(app)
        logger.info("FastAPI instrumentation enabled")
        
        # Instrument SQLAlchemy
        SQLAlchemyInstrumentor().instrument()
        logger.info("SQLAlchemy instrumentation enabled")
        
        # Instrument Redis
        RedisInstrumentor().instrument()
        logger.info("Redis instrumentation enabled")
        
        # Instrument HTTP client
        HTTPXClientInstrumentor().instrument()
        logger.info("HTTPX instrumentation enabled")
        
    except Exception as e:
        logger.error(f"Failed to instrument application: {e}")


class TracingMiddleware:
    """Custom tracing middleware for additional context"""
    
    def __init__(self, app):
        self.app = app
        self.tracer = trace.get_tracer(__name__)
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        # Extract request information
        request_method = scope.get("method", "UNKNOWN")
        request_path = scope.get("path", "/")
        
        # Start span
        with self.tracer.start_as_current_span(
            f"{request_method} {request_path}",
            kind=trace.SpanKind.SERVER
        ) as span:
            # Add request attributes
            span.set_attribute("http.method", request_method)
            span.set_attribute("http.url", request_path)
            span.set_attribute("http.scheme", scope.get("scheme", "http"))
            
            # Add custom attributes from headers
            headers = dict(scope.get("headers", []))
            
            # Extract tenant and user context from headers
            tenant_id = headers.get(b"x-tenant-id")
            if tenant_id:
                span.set_attribute("tenant.id", tenant_id.decode())
                baggage.set_baggage("tenant.id", tenant_id.decode())
            
            user_id = headers.get(b"x-user-id")
            if user_id:
                span.set_attribute("user.id", user_id.decode())
                baggage.set_baggage("user.id", user_id.decode())
            
            # Track request start time
            start_time = time.time()
            
            try:
                await self.app(scope, receive, send)
                span.set_status(trace.Status(trace.StatusCode.OK))
                
            except Exception as e:
                span.set_status(trace.Status(
                    trace.StatusCode.ERROR,
                    description=str(e)
                ))
                span.record_exception(e)
                raise
            
            finally:
                # Record request duration
                duration = time.time() - start_time
                span.set_attribute("http.duration_ms", duration * 1000)


def trace_function(
    operation_name: str = None,
    span_kind: trace.SpanKind = trace.SpanKind.INTERNAL,
    record_exception: bool = True
):
    """
    Decorator to trace function execution
    
    Args:
        operation_name: Name for the span (defaults to function name)
        span_kind: Type of span (INTERNAL, CLIENT, SERVER, etc.)
        record_exception: Whether to record exceptions in the span
    """
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            tracer = trace.get_tracer(__name__)
            span_name = operation_name or f"{func.__module__}.{func.__name__}"
            
            with tracer.start_as_current_span(span_name, kind=span_kind) as span:
                # Add function attributes
                span.set_attribute("function.name", func.__name__)
                span.set_attribute("function.module", func.__module__)
                
                # Add baggage context
                tenant_id = baggage.get_baggage("tenant.id")
                if tenant_id:
                    span.set_attribute("tenant.id", tenant_id)
                
                user_id = baggage.get_baggage("user.id")
                if user_id:
                    span.set_attribute("user.id", user_id)
                
                start_time = time.time()
                
                try:
                    if asyncio.iscoroutinefunction(func):
                        result = await func(*args, **kwargs)
                    else:
                        result = func(*args, **kwargs)
                    
                    span.set_status(trace.Status(trace.StatusCode.OK))
                    return result
                    
                except Exception as e:
                    if record_exception:
                        span.record_exception(e)
                        span.set_status(trace.Status(
                            trace.StatusCode.ERROR,
                            description=str(e)
                        ))
                    raise
                
                finally:
                    duration = time.time() - start_time
                    span.set_attribute("duration_ms", duration * 1000)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            tracer = trace.get_tracer(__name__)
            span_name = operation_name or f"{func.__module__}.{func.__name__}"
            
            with tracer.start_as_current_span(span_name, kind=span_kind) as span:
                # Add function attributes
                span.set_attribute("function.name", func.__name__)
                span.set_attribute("function.module", func.__module__)
                
                # Add baggage context
                tenant_id = baggage.get_baggage("tenant.id")
                if tenant_id:
                    span.set_attribute("tenant.id", tenant_id)
                
                user_id = baggage.get_baggage("user.id")
                if user_id:
                    span.set_attribute("user.id", user_id)
                
                start_time = time.time()
                
                try:
                    result = func(*args, **kwargs)
                    span.set_status(trace.Status(trace.StatusCode.OK))
                    return result
                    
                except Exception as e:
                    if record_exception:
                        span.record_exception(e)
                        span.set_status(trace.Status(
                            trace.StatusCode.ERROR,
                            description=str(e)
                        ))
                    raise
                
                finally:
                    duration = time.time() - start_time
                    span.set_attribute("duration_ms", duration * 1000)
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator


class TracingHelper:
    """Helper class for manual tracing operations"""
    
    def __init__(self):
        self.tracer = trace.get_tracer(__name__)
    
    def start_span(self, name: str, **attributes) -> trace.Span:
        """Start a new span with optional attributes"""
        span = self.tracer.start_span(name)
        
        for key, value in attributes.items():
            span.set_attribute(key, value)
        
        return span
    
    def add_event(self, span: trace.Span, name: str, **attributes):
        """Add an event to a span"""
        span.add_event(name, attributes)
    
    def set_baggage(self, key: str, value: str):
        """Set baggage for cross-service context propagation"""
        baggage.set_baggage(key, value)
    
    def get_baggage(self, key: str) -> Optional[str]:
        """Get baggage value"""
        return baggage.get_baggage(key)
    
    def get_current_span(self) -> trace.Span:
        """Get the current active span"""
        return trace.get_current_span()
    
    def get_trace_id(self) -> str:
        """Get the current trace ID"""
        span = trace.get_current_span()
        if span and span.get_span_context().is_valid:
            return format(span.get_span_context().trace_id, '032x')
        return ""
    
    def get_span_id(self) -> str:
        """Get the current span ID"""
        span = trace.get_current_span()
        if span and span.get_span_context().is_valid:
            return format(span.get_span_context().span_id, '016x')
        return ""


# Global tracing helper instance
tracing_helper = TracingHelper()


# Context manager for manual span management
class SpanContext:
    """Context manager for manual span creation"""
    
    def __init__(self, name: str, **attributes):
        self.name = name
        self.attributes = attributes
        self.span = None
        self.tracer = trace.get_tracer(__name__)
    
    def __enter__(self):
        self.span = self.tracer.start_span(self.name)
        
        for key, value in self.attributes.items():
            self.span.set_attribute(key, value)
        
        return self.span
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.span.record_exception(exc_val)
            self.span.set_status(trace.Status(
                trace.StatusCode.ERROR,
                description=str(exc_val)
            ))
        else:
            self.span.set_status(trace.Status(trace.StatusCode.OK))
        
        self.span.end()


# Initialize tracing
tracer = setup_tracing()