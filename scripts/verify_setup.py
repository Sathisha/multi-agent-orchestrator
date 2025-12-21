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
            response = await client.get("http://localhost:8000/health", timeout=10.0)
            
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


async def verify_metrics_endpoint():
    """Verify that the metrics endpoint is accessible."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8000/metrics", timeout=10.0)
            
            if response.status_code == 200:
                print("✅ Metrics Endpoint: PASSED")
                return True
            else:
                print(f"❌ Metrics Endpoint: FAILED (Status: {response.status_code})")
                return False
                
    except Exception as e:
        print(f"❌ Metrics Endpoint: FAILED ({str(e)})")
        return False


def verify_project_structure():
    """Verify that the project structure is correct."""
    required_paths = [
        "backend/main.py",
        "backend/requirements.txt",
        "backend/shared/config/settings.py",
        "backend/shared/database/connection.py",
        "backend/shared/logging/config.py",
        "backend/shared/models/base.py",
        "backend/tests/conftest.py",
        "backend/tests/test_main.py",
        "docker-compose.yml",
        "docker-compose.dev.yml",
        "Makefile",
        ".env.example",
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


async def main():
    """Main verification function."""
    print("🚀 AI Agent Framework Setup Verification")
    print("=" * 50)
    
    # Check project structure
    structure_ok = verify_project_structure()
    
    # Check API endpoints
    print("\n📡 Testing API Endpoints...")
    health_ok = await verify_api_health()
    metrics_ok = await verify_metrics_endpoint()
    
    # Summary
    print("\n📋 Verification Summary")
    print("-" * 30)
    
    all_checks = [structure_ok, health_ok, metrics_ok]
    passed_checks = sum(all_checks)
    total_checks = len(all_checks)
    
    if all(all_checks):
        print(f"🎉 All checks passed! ({passed_checks}/{total_checks})")
        print("\n✅ Your AI Agent Framework setup is complete and ready for development!")
        print("\nNext steps:")
        print("1. Start developing with: make api")
        print("2. Run tests with: make test")
        print("3. View API docs at: http://localhost:8000/docs")
        return 0
    else:
        print(f"⚠️  Some checks failed ({passed_checks}/{total_checks})")
        print("\n❌ Please fix the issues above before proceeding.")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))