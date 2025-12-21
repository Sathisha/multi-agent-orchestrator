"""Database connection and session management with optimized connection pooling."""

import os
from typing import AsyncGenerator

from sqlalchemy import create_engine, event, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import QueuePool, NullPool

from shared.config.settings import get_settings

# Get settings
settings = get_settings()

# Database configuration from settings
DATABASE_URL = settings.database.url
ASYNC_DATABASE_URL = settings.database.async_url

# Connection pool configuration for production-grade performance
POOL_CONFIG = {
    "poolclass": QueuePool,
    "pool_size": settings.database.pool_size,  # Base connections (default: 10)
    "max_overflow": settings.database.max_overflow,  # Additional connections (default: 20)
    "pool_timeout": 30,  # Wait time for connection (seconds)
    "pool_recycle": 3600,  # Recycle connections every hour
    "pool_pre_ping": True,  # Validate connections before use
    "echo": settings.database.echo,  # SQL query logging
    "echo_pool": settings.debug,  # Connection pool logging (debug only)
    "query_cache_size": 1200,  # Cache prepared statements
}

# Create database engines with optimized connection pooling
engine = create_engine(DATABASE_URL, **POOL_CONFIG)

# Async engine configuration
async_engine = create_async_engine(
    ASYNC_DATABASE_URL,
    poolclass=QueuePool,
    pool_size=settings.database.pool_size,
    max_overflow=settings.database.max_overflow,
    pool_timeout=30,
    pool_recycle=3600,
    pool_pre_ping=True,
    echo=settings.database.echo,
    echo_pool=settings.debug,
)

# Create session makers
SessionLocal = sessionmaker(
    autocommit=False, 
    autoflush=False, 
    bind=engine,
    expire_on_commit=False  # Keep objects accessible after commit
)

AsyncSessionLocal = async_sessionmaker(
    async_engine, 
    class_=AsyncSession, 
    expire_on_commit=False,
    autoflush=False,
    autocommit=False
)

# Base class for SQLAlchemy models
Base = declarative_base()


# Connection pool event listeners for monitoring
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Set database-specific optimizations on connection."""
    if "postgresql" in DATABASE_URL:
        # PostgreSQL-specific optimizations
        with dbapi_connection.cursor() as cursor:
            # Set connection-level optimizations
            cursor.execute("SET statement_timeout = '30s'")
            cursor.execute("SET lock_timeout = '10s'")
            cursor.execute("SET idle_in_transaction_session_timeout = '60s'")


@event.listens_for(engine, "checkout")
def receive_checkout(dbapi_connection, connection_record, connection_proxy):
    """Log connection checkout for monitoring."""
    if settings.debug:
        print(f"Connection checked out: {id(dbapi_connection)}")


@event.listens_for(engine, "checkin")
def receive_checkin(dbapi_connection, connection_record):
    """Log connection checkin for monitoring."""
    if settings.debug:
        print(f"Connection checked in: {id(dbapi_connection)}")


def get_db():
    """Dependency for synchronous database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for asynchronous database sessions."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def create_tables():
    """Create all database tables."""
    # Import all models to ensure they are registered
    import shared.models  # noqa
    
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_tables():
    """Drop all database tables."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


def get_connection_pool_status():
    """Get current connection pool status for monitoring."""
    pool = engine.pool
    return {
        "size": pool.size(),
        "checked_in": pool.checkedin(),
        "checked_out": pool.checkedout(),
        "overflow": pool.overflow(),
    }


async def get_async_connection_pool_status():
    """Get async connection pool status for monitoring."""
    pool = async_engine.pool
    return {
        "size": pool.size(),
        "checked_in": pool.checkedin(),
        "checked_out": pool.checkedout(),
        "overflow": pool.overflow(),
    }


# Health check functions
async def check_database_health():
    """Check database connectivity and performance."""
    import time
    
    try:
        async with AsyncSessionLocal() as session:
            start_time = time.time()
            result = await session.execute(text("SELECT 1"))
            query_time = time.time() - start_time
            
            pool_status = await get_async_connection_pool_status()
            
            return {
                "status": "healthy",
                "query_time_ms": round(query_time * 1000, 2),
                "pool_status": pool_status
            }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }