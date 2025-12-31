"""
Pytest configuration and fixtures for AI Agent Framework tests.

This module provides centralized configuration and fixtures for all tests:
- Unit tests (tests/unit/)
- Property-based tests (tests/properties/)
- Integration tests (tests/integration/)

Usage:
    pytest tests/ -v              # Run all tests
    pytest tests/unit/ -v         # Run only unit tests
    pytest tests/properties/ -v   # Run only property tests
    pytest tests/integration/ -v  # Run only integration tests

Available Fixtures:
    - event_loop: Event loop for async tests
    - async_engine: Async SQLAlchemy engine
    - async_session: Async database session (transaction with rollback)
    - async_db_session: Alias for async_session
    - test_client: FastAPI TestClient
    - test_settings: Test Settings object

See TEST_GUIDE.md for detailed information.
"""

import asyncio
import os
import sys
from typing import AsyncGenerator, Generator

# Set testing environment variable
os.environ['TESTING'] = 'true'

# Add the parent directory to Python path to allow imports of 'shared' and 'main'
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app
from shared.database.connection import Base, get_async_db
from shared.config.settings import Settings

# Test database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
TEST_SYNC_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def async_engine():
    """Create async test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest.fixture
async def async_session(async_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create async test database session."""
    async_session_maker = sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session_maker() as session:
        yield session


@pytest.fixture
def test_client(async_session):
    """Create test client with database dependency override."""
    
    async def override_get_async_db():
        yield async_session
    
    app.dependency_overrides[get_async_db] = override_get_async_db
    
    with TestClient(app) as client:
        yield client
    
    app.dependency_overrides.clear()


@pytest.fixture
async def async_db_session(async_engine) -> AsyncGenerator[AsyncSession, None]:
    """
    Alias for async_session with transaction rollback.
    
    Use this fixture for tests that need database transactions rolled back
    automatically after the test completes.
    
    Example:
        async def test_user_creation(async_db_session):
            user = await create_user(async_db_session, name="test")
            assert user.id is not None
    """
    async_session_maker = sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session_maker() as session:
        yield session


@pytest.fixture
def client(test_client):
    """Alias for test_client for backward compatibility."""
    return test_client


@pytest.fixture
def test_settings() -> Settings:
    """
    Create test settings with sensible defaults.
    
    Use this fixture to override settings in tests:
    
    Example:
        def test_with_settings(test_settings):
            test_settings.debug = False
            # Use test_settings in your test
    """
    return Settings(
        environment="test",
        debug=True,
        database={
            "url": TEST_SYNC_DATABASE_URL, 
            "async_url": TEST_DATABASE_URL,
            "echo": False,
            "pool_size": 5,
            "max_overflow": 10
        },
        redis={"url": "redis://localhost:6379/1", "max_connections": 5},
        security={
            "secret_key": "test-secret-key",
            "algorithm": "HS256",
            "access_token_expire_minutes": 30
        },
        logging={"level": "DEBUG", "format": "console"},
        api={
            "host": "0.0.0.0",
            "port": 8000,
            "reload": False,
            "workers": 1,
            "cors_origins": ["http://localhost:3000"],
            "cors_credentials": True,
            "cors_methods": ["GET", "POST", "PUT", "DELETE"],
            "cors_headers": ["*"]
        }
    )


# Pytest configuration and hooks
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "property: mark test as a property-based test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow"
    )
    config.addinivalue_line(
        "markers", "db: mark test as requiring database"
    )
    config.addinivalue_line(
        "markers", "llm: mark test as requiring LLM services"
    )
    config.addinivalue_line(
        "markers", "requires_docker: mark test as requiring Docker"
    )