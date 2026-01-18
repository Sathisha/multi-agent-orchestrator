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
from unittest.mock import MagicMock, AsyncMock, patch

# Set testing environment variable
os.environ['TESTING'] = 'true'

# Mock pyzeebe if not installed, to allow imports of modules that depend on it
try:
    import pyzeebe
except ImportError:
    mock_pyzeebe = MagicMock()
    sys.modules["pyzeebe"] = mock_pyzeebe
    sys.modules["pyzeebe.aio"] = MagicMock()
    sys.modules["pyzeebe.aio.client"] = MagicMock()

# Add the parent directory to Python path to allow imports of 'shared' and 'main'
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.ext.compiler import compiles
import sqlalchemy.types
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.types import Text, VARCHAR
from sqlalchemy.sql.expression import TextClause

# Monkeypatch PostgreSQL UUID to work with SQLite (store as String)
class StringyUUID(sqlalchemy.types.TypeDecorator):
    impl = sqlalchemy.types.String
    cache_ok = True
    
    def __init__(self, as_uuid=True, **kwargs):
        # Swallow as_uuid, pass other kwargs to impl
        super().__init__(**kwargs)

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return str(value)
    def process_result_value(self, value, dialect):
        return value

postgresql.UUID = StringyUUID

from main import app
from shared.database.connection import Base, get_async_db
import shared.models  # Ensure all models are registered
from shared.config.settings import Settings
from shared.database.connection import Base, get_async_db
from shared.config.settings import Settings
from shared.services.auth import get_current_user as get_current_user_service
from shared.api.auth import get_current_user_or_api_key, get_current_user
from shared.models.user import User
from shared.models.user import User
from uuid import uuid4
from contextlib import asynccontextmanager

# Handle JSONB in SQLite for testing
@compiles(JSONB, "sqlite")
def compile_jsonb(type_, compiler, **kw):
    return "TEXT"

# Strip ::jsonb cast in SQLite for testing
@compiles(TextClause, "sqlite")
def compile_text_clause(element, compiler, **kw):
    text_content = element.text.replace("::jsonb", "")
    if "gen_random_uuid()" in text_content:
        return text_content.replace("gen_random_uuid()", "NULL")
    return text_content

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
        echo=True
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
def test_client(async_engine, async_session):
    """Create test client with database dependency override."""
    
    async def override_get_async_db():
        async with AsyncSession(async_engine, expire_on_commit=False) as session:
            yield session
    
    async def override_get_current_user():
        return User(
            id=uuid4(),
            email="admin@example.com",
            username="testuser",
            is_active=True
        )

    @asynccontextmanager
    async def mock_get_db_session():
        async with AsyncSession(async_engine, expire_on_commit=False) as session:
            yield session

    app.dependency_overrides[get_async_db] = override_get_async_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_current_user_service] = override_get_current_user
    app.dependency_overrides[get_current_user_or_api_key] = override_get_current_user
    
    with patch("shared.middleware.audit.get_database_session", side_effect=mock_get_db_session):
        with TestClient(app) as client:
            yield client
    
    app.dependency_overrides.clear()


@pytest.fixture
async def async_client(async_engine, async_session):
    """Create async client for async tests."""
    
    async def override_get_async_db():
        async with AsyncSession(async_engine, expire_on_commit=False) as session:
            yield session
    
    async def override_get_current_user():
        return User(
            id=uuid4(),
            email="admin@example.com",
            username="testuser",
            is_active=True
        )

    @asynccontextmanager
    async def mock_get_db_session():
        async with AsyncSession(async_engine, expire_on_commit=False) as session:
            yield session

    app.dependency_overrides[get_async_db] = override_get_async_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_current_user_service] = override_get_current_user
    app.dependency_overrides[get_current_user_or_api_key] = override_get_current_user
    
    with patch("shared.middleware.audit.get_database_session", side_effect=mock_get_db_session):
        async with AsyncClient(app=app, base_url="http://testserver") as client:
            yield client
    
    app.dependency_overrides.clear()


@pytest.fixture(scope="function", autouse=True)
async def mock_db_init(async_engine):
    """Mock database initialization, background services, and session factory."""
    # Create a factory that returns a NEW session each time
    def session_factory():
        return AsyncSession(async_engine, expire_on_commit=False)

    with patch("shared.database.connection.init_database_on_startup", new_callable=AsyncMock) as mock_db, \
         patch("shared.services.monitoring.monitoring_service.start", new_callable=AsyncMock), \
         patch("shared.services.monitoring.monitoring_service.stop", new_callable=AsyncMock), \
         patch("shared.services.agent_executor.lifecycle_manager.start_monitoring", new_callable=AsyncMock), \
         patch("shared.services.agent_executor.lifecycle_manager.stop_monitoring", new_callable=AsyncMock), \
         patch("shared.services.agent_state_manager.global_state_manager.start_global_monitoring", new_callable=AsyncMock), \
         patch("shared.services.agent_state_manager.global_state_manager.stop_global_monitoring", new_callable=AsyncMock), \
         patch("shared.database.connection.AsyncSessionLocal", side_effect=session_factory), \
         patch("shared.services.agent_executor.AsyncSessionLocal", side_effect=session_factory), \
         patch("shared.services.audit.AuditService.log_event", new_callable=AsyncMock):
        yield mock_db


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

@pytest.fixture
def mock_zeebe_client():
    """Mock Zeebe client to prevent actual network calls."""
    mock_client = MagicMock()
    mock_client.create_process_instance = AsyncMock(return_value={"processInstanceKey": 12345})
    mock_client.deploy_resource = AsyncMock(return_value={"key": 1})
    mock_client.publish_message = AsyncMock(return_value={})
    mock_client.cancel_process_instance = AsyncMock(return_value={})
    mock_client.topology = AsyncMock(return_value={"brokers": []})

    # Also patch the global service instance if it exists
    # We patch shared.core.workflow.zeebe_service which the API uses.
    # Note: shared.core.workflow.zeebe_service is an INSTANCE of ZeebeService.
    # We need to mock its methods (run_workflow, deploy_workflow) AND its client attribute.
    with patch("shared.core.workflow.zeebe_service", new_callable=MagicMock) as mock_service:
        mock_service.run_workflow = AsyncMock(return_value=12345)
        mock_service.deploy_workflow = AsyncMock(return_value="deployed")
        mock_service.zeebe_client = mock_client # Assume service has this attribute exposed or used internally
        
        # If the code accesses zeebe_service.client (not zeebe_client)
        mock_service.client = mock_client
        
        # Patch where it is imported in the service we are testing
        with patch("shared.services.workflow_orchestrator.zeebe_service", mock_service):
            yield mock_client

@pytest.fixture(autouse=True)
async def reset_workflow_service():
    """Reset the workflow orchestrator service singleton before each test."""
    try:
        import shared.api.workflow_orchestrator
        shared.api.workflow_orchestrator._workflow_orchestrator_instance = None
    except (ImportError, AttributeError):
        pass

    try:
        import shared.api.v1.endpoints.chains
        shared.api.v1.endpoints.chains._chain_orchestrator_instance = None
    except (ImportError, AttributeError):
        pass
    yield