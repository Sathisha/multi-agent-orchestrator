"""Unit tests for logging configuration."""

import logging
import sys
import os
import pytest
import structlog

# Add the parent directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from shared.logging.config import configure_logging, get_logger, add_service_context


def test_configure_logging_development():
    """Test logging configuration for development environment."""
    configure_logging(
        log_level="DEBUG",
        service_name="test-service",
        environment="development"
    )
    
    logger = get_logger("test")
    assert logger is not None
    
    # Test that we can log without errors
    logger.info("Test message", extra_field="test_value")


def test_configure_logging_production():
    """Test logging configuration for production environment."""
    configure_logging(
        log_level="INFO",
        service_name="test-service",
        environment="production"
    )
    
    logger = get_logger("test")
    assert logger is not None
    
    # Test that we can log without errors
    logger.info("Test message", extra_field="test_value")


def test_add_service_context():
    """Test service context processor."""
    processor = add_service_context("test-service", "test-env")
    
    event_dict = {"message": "test"}
    result = processor(None, None, event_dict)
    
    assert result["service"] == "test-service"
    assert result["environment"] == "test-env"
    assert result["message"] == "test"


def test_get_logger():
    """Test logger creation."""
    logger = get_logger("test.module")
    assert logger is not None
    
    # Test that logger has expected methods
    assert hasattr(logger, "info")
    assert hasattr(logger, "error")
    assert hasattr(logger, "debug")
    assert hasattr(logger, "warning")