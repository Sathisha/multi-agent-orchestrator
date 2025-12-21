#!/usr/bin/env python3
"""Setup script for AI Agent Framework development environment."""

import os
import subprocess
import sys
from pathlib import Path


def run_command(command: str, cwd: str = None) -> bool:
    """Run a shell command and return success status."""
    try:
        result = subprocess.run(
            command.split(),
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True
        )
        print(f"✓ {command}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ {command}")
        print(f"Error: {e.stderr}")
        return False


def main():
    """Main setup function."""
    print("🚀 Setting up AI Agent Framework development environment...")
    
    # Get project root
    project_root = Path(__file__).parent.parent
    backend_dir = project_root / "backend"
    
    # Check if Python 3.11+ is available
    python_version = sys.version_info
    if python_version.major < 3 or python_version.minor < 11:
        print("❌ Python 3.11+ is required")
        sys.exit(1)
    
    print(f"✓ Python {python_version.major}.{python_version.minor} detected")
    
    # Create .env file if it doesn't exist
    env_file = project_root / ".env"
    env_example = project_root / ".env.example"
    
    if not env_file.exists() and env_example.exists():
        env_file.write_text(env_example.read_text())
        print("✓ Created .env file from .env.example")
    
    # Install Python dependencies
    print("\n📦 Installing Python dependencies...")
    if not run_command("pip install -r requirements.txt", str(backend_dir)):
        print("❌ Failed to install Python dependencies")
        sys.exit(1)
    
    # Start Docker services
    print("\n🐳 Starting Docker services...")
    if not run_command("docker-compose up -d postgres redis", str(project_root)):
        print("❌ Failed to start Docker services")
        sys.exit(1)
    
    # Wait for services to be ready
    print("\n⏳ Waiting for services to be ready...")
    import time
    time.sleep(10)
    
    # Initialize database
    print("\n🗄️ Initializing database...")
    if not run_command("alembic upgrade head", str(backend_dir)):
        print("❌ Failed to initialize database")
        sys.exit(1)
    
    print("\n✅ Setup complete!")
    print("\nNext steps:")
    print("1. Start the API server: cd backend && python main.py")
    print("2. Visit http://localhost:8000 to verify the API is running")
    print("3. Check http://localhost:8000/docs for API documentation")


if __name__ == "__main__":
    main()