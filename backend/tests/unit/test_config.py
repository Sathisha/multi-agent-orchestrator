"""Unit tests for configuration management."""

import os
import sys
import pytest

# Add the parent directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from shared.config.settings import Settings, DatabaseSettings, RedisSettings


def test_database_settings_defaults():
    """Test database settings with default values."""
    settings = DatabaseSettings()
    
    assert "postgresql://" in settings.url
    assert "postgresql+asyncpg://" in settings.async_url
    assert settings.echo is False
    assert settings.pool_size == 10
    assert settings.max_overflow == 20


def test_redis_settings_defaults():
    """Test Redis settings with default values."""
    settings = RedisSettings()
    
    assert "redis://" in settings.url
    assert settings.max_connections == 10


def test_settings_from_environment(monkeypatch):
    """Test that settings can be loaded from environment variables."""
    # Set environment variables
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/test")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/1")
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("DEBUG", "true")
    
    settings = Settings()
    
    assert settings.database.url == "postgresql://test:test@localhost/test"
    assert settings.redis.url == "redis://localhost:6379/1"
    assert settings.environment == "test"
    assert settings.debug is True


def test_settings_validation():
    """Test settings validation."""
    settings = Settings()
    
    # Test that required fields have values
    assert settings.service_name
    assert settings.version
    assert settings.database.url
    assert settings.redis.url