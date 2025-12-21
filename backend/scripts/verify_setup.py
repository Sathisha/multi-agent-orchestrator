#!/usr/bin/env python3
"""Verification script to ensure the AI Agent Framework setup is complete."""

import asyncio
import httpx
import sys
import time
from pathlib import Path


async def verify_api_health():
    """Verify that the API is healthy and responding."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://backend:8000/health", timeout=10.0)
            
            if response.status_code == 200:
                data = response.json()
                print("✅ API Health Check: PASSED")
                print(f"   Service: {data.get('service')}")
                print(f"   Version: {data.get('version')}")
                print(f"   Environment: {data.get('environment')}")
                return True
            else:
                print(f"❌ API Health Check: FAILED (Status: {response.status_code})")
                return False
                
    except Exception as e:
        print(f"❌ API Health Check: FAILED ({str(e)})")
        return False


async def verify_database_connection():
    """Verify database connection."""
    try:
        import sys
        import os
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        from sqlalchemy.ext.asyncio import create_async_engine
        from sqlalchemy import text
        
        # Use container network hostname
        database_url = "postgresql+asyncpg://postgres:postgres@postgres:5432/ai_agent_framework"
        engine = create_async_engine(database_url)
        
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            row = result.fetchone()
            
            if row and row[0] == 1:
                print("✅ Database Connection: PASSED")
                return True
            else:
                print("❌ Database Connection: FAILED (Invalid response)")
                return False
                
    except Exception as e:
        print(f"❌ Database Connection: FAILED ({str(e)})")
        return False


async def verify_redis_connection():
    """Verify Redis connection."""
    try:
        import redis.asyncio as redis
        
        client = redis.Redis(host='redis', port=6379, decode_responses=True)
        pong = await client.ping()
        
        if pong:
            print("✅ Redis Connection: PASSED")
            return True
        else:
            print("❌ Redis Connection: FAILED")
            return False
                
    except Exception as e:
        print(f"❌ Redis Connection: FAILED ({str(e)})")
        return False


def verify_project_structure():
    """Verify that the project structure is correct within the container."""
    required_paths = [
        "main.py",
        "requirements.txt",
        "shared/config/settings.py",
        "shared/database/connection.py",
        "shared/logging/config.py",
        "shared/models/base.py",
        "tests/conftest.py",
        "tests/test_main.py",
        "alembic.ini",
        "alembic/env.py",
    ]
    
    missing_paths = []
    for path in required_paths:
        if not Path(path).exists():
            missing_paths.append(path)
    
    if not missing_paths:
        print("✅ Project Structure: PASSED")
        return True
    else:
        print("❌ Project Structure: FAILED")
        print("   Missing files:")
        for path in missing_paths:
            print(f"   - {path}")
        return False


def verify_dependencies():
    """Verify that key dependencies are installed."""
    try:
        import fastapi
        import sqlalchemy
        import redis
        import structlog
        import prometheus_client
        import pytest
        
        print("✅ Dependencies: PASSED")
        return True
        
    except ImportError as e:
        print(f"❌ Dependencies: FAILED ({str(e)})")
        return False


async def main():
    """Main verification function."""
    print("🚀 AI Agent Framework Setup Verification")
    print("=" * 50)
    
    # Check project structure
    structure_ok = verify_project_structure()
    
    # Check dependencies
    deps_ok = verify_dependencies()
    
    # Check database and Redis connections
    print("\n🔗 Testing Service Connections...")
    db_ok = await verify_database_connection()
    redis_ok = await verify_redis_connection()
    
    # Summary
    print("\n📋 Verification Summary")
    print("-" * 30)
    
    all_checks = [structure_ok, deps_ok, db_ok, redis_ok]
    passed_checks = sum(all_checks)
    total_checks = len(all_checks)
    
    if all(all_checks):
        print(f"🎉 All checks passed! ({passed_checks}/{total_checks})")
        print("\n✅ Your AI Agent Framework backend setup is complete!")
        print("\nNext steps:")
        print("1. Run tests: docker-compose -f docker-compose.dev.yml run --rm backend pytest")
        print("2. Start API: docker-compose -f docker-compose.dev.yml up backend")
        print("3. View API docs at: http://localhost:8000/docs")
        return 0
    else:
        print(f"⚠️  Some checks failed ({passed_checks}/{total_checks})")
        print("\n❌ Please fix the issues above before proceeding.")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))