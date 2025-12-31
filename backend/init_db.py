#!/usr/bin/env python3
"""Database initialization script for development.

This script creates all database tables directly without using Alembic migrations.
Use this during development phase to avoid versioning complexity.
"""

import asyncio
import sys
from pathlib import Path

# Add backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from shared.database.connection import create_tables, drop_tables, async_engine


async def init_database(recreate: bool = False):
    """Initialize database tables.
    
    Args:
        recreate: If True, drop existing tables before creating new ones
    """
    try:
        if recreate:
            print("Dropping existing database tables...")
            await drop_tables()
            print("Existing tables dropped successfully")
        
        print("Creating database tables...")
        await create_tables()
        print("Database tables created successfully")
        
        # Verify tables were created
        async with async_engine.begin() as conn:
            from sqlalchemy import text
            result = await conn.execute(
                text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
            )
            tables = [row[0] for row in result.fetchall()]
            print(f"Created {len(tables)} tables: {', '.join(sorted(tables))}")
        
    except Exception as e:
        print(f"Database initialization failed: {e}")
        raise
    finally:
        await async_engine.dispose()


async def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Initialize database for AI Agent Framework")
    parser.add_argument(
        "--recreate", 
        action="store_true", 
        help="Drop existing tables before creating new ones"
    )
    
    args = parser.parse_args()
    
    print("Starting database initialization...")
    await init_database(recreate=args.recreate)
    print("Database initialization completed successfully")


if __name__ == "__main__":
    asyncio.run(main())