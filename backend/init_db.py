#!/usr/bin/env python3
import asyncio
import sys
from pathlib import Path
import subprocess

# Add backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))


async def init_database():
    """Initialize database tables using Alembic migrations."""
    try:
        print("Running Alembic migrations...")
        # Use subprocess to run Alembic commands
        process = await asyncio.create_subprocess_exec(
            "alembic", "upgrade", "head",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(backend_dir)
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            raise RuntimeError(f"Alembic migration failed: {stderr.decode()}")

        print(stdout.decode())
        print("Alembic migrations completed successfully")
        
    except Exception as e:
        print(f"Database initialization failed: {e}")
        raise


async def main():
    """Main function."""
    print("Starting database initialization (via Alembic)...")
    await init_database()
    print("Database initialization completed successfully")


if __name__ == "__main__":
    asyncio.run(main())