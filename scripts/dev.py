#!/usr/bin/env python3
"""Development helper script for AI Agent Framework."""

import argparse
import subprocess
import sys
from pathlib import Path


def run_command(command: str, cwd: str = None) -> int:
    """Run a shell command and return exit code."""
    try:
        return subprocess.run(command.split(), cwd=cwd).returncode
    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user")
        return 1


def start_services(args):
    """Start development services."""
    project_root = Path(__file__).parent.parent
    
    services = ["postgres", "redis"]
    if args.all:
        services.extend(["keycloak", "kong", "prometheus"])
    
    print(f"🚀 Starting services: {', '.join(services)}")
    return run_command(f"docker-compose up -d {' '.join(services)}", str(project_root))


def stop_services(args):
    """Stop development services."""
    project_root = Path(__file__).parent.parent
    
    print("🛑 Stopping all services")
    return run_command("docker-compose down", str(project_root))


def start_api(args):
    """Start the API server."""
    backend_dir = Path(__file__).parent.parent / "backend"
    
    print("🚀 Starting API server...")
    return run_command("python main.py", str(backend_dir))


def run_tests(args):
    """Run tests."""
    backend_dir = Path(__file__).parent.parent / "backend"
    
    test_command = "pytest"
    if args.verbose:
        test_command += " -v"
    if args.coverage:
        test_command += " --cov=backend --cov-report=html"
    if args.pattern:
        test_command += f" -k {args.pattern}"
    
    print(f"🧪 Running tests: {test_command}")
    return run_command(test_command, str(backend_dir))


def format_code(args):
    """Format code with black and isort."""
    backend_dir = Path(__file__).parent.parent / "backend"
    
    print("🎨 Formatting code with black...")
    black_result = run_command("black .", str(backend_dir))
    
    print("📦 Sorting imports with isort...")
    isort_result = run_command("isort .", str(backend_dir))
    
    return max(black_result, isort_result)


def lint_code(args):
    """Lint code with flake8 and mypy."""
    backend_dir = Path(__file__).parent.parent / "backend"
    
    print("🔍 Linting with flake8...")
    flake8_result = run_command("flake8 .", str(backend_dir))
    
    print("🔍 Type checking with mypy...")
    mypy_result = run_command("mypy .", str(backend_dir))
    
    return max(flake8_result, mypy_result)


def create_migration(args):
    """Create a new database migration."""
    backend_dir = Path(__file__).parent.parent / "backend"
    
    if not args.message:
        print("❌ Migration message is required")
        return 1
    
    print(f"📝 Creating migration: {args.message}")
    return run_command(f"alembic revision --autogenerate -m '{args.message}'", str(backend_dir))


def migrate_db(args):
    """Run database migrations."""
    backend_dir = Path(__file__).parent.parent / "backend"
    
    print("🗄️ Running database migrations...")
    return run_command("alembic upgrade head", str(backend_dir))


def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(description="AI Agent Framework development helper")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Start services
    start_parser = subparsers.add_parser("start", help="Start development services")
    start_parser.add_argument("--all", action="store_true", help="Start all services including optional ones")
    start_parser.set_defaults(func=start_services)
    
    # Stop services
    stop_parser = subparsers.add_parser("stop", help="Stop development services")
    stop_parser.set_defaults(func=stop_services)
    
    # Start API
    api_parser = subparsers.add_parser("api", help="Start API server")
    api_parser.set_defaults(func=start_api)
    
    # Run tests
    test_parser = subparsers.add_parser("test", help="Run tests")
    test_parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    test_parser.add_argument("-c", "--coverage", action="store_true", help="Generate coverage report")
    test_parser.add_argument("-k", "--pattern", help="Test pattern to match")
    test_parser.set_defaults(func=run_tests)
    
    # Format code
    format_parser = subparsers.add_parser("format", help="Format code")
    format_parser.set_defaults(func=format_code)
    
    # Lint code
    lint_parser = subparsers.add_parser("lint", help="Lint code")
    lint_parser.set_defaults(func=lint_code)
    
    # Create migration
    migration_parser = subparsers.add_parser("migration", help="Create database migration")
    migration_parser.add_argument("-m", "--message", required=True, help="Migration message")
    migration_parser.set_defaults(func=create_migration)
    
    # Migrate database
    migrate_parser = subparsers.add_parser("migrate", help="Run database migrations")
    migrate_parser.set_defaults(func=migrate_db)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())