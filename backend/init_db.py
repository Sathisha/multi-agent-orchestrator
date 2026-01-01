#!/usr/bin/env python3
"""
Database initialization script using SQLAlchemy.
Creates all tables defined in the models.
"""
import asyncio
import sys
from pathlib import Path

# Add backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))


async def init_database():
    """Initialize database tables using SQLAlchemy."""
    try:
        print("🔄 Initializing database tables with SQLAlchemy...")
        
        # Import database connection
        from shared.database.connection import create_tables, async_engine
        from sqlalchemy import text
        
        # Test database connection first
        print("📡 Testing database connection...")
        async with async_engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            print("✅ Database connection successful")
        
        # Create all tables
        print("📋 Creating database tables...")
        await create_tables()
        print("✅ Database tables created successfully")
        
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        import traceback
        traceback.print_exc()
        raise


async def main():
    """Main function."""
    print("🚀 Starting database initialization...")
    await init_database()
    print("✅ Database initialization completed successfully")


if __name__ == "__main__":
    asyncio.run(main())