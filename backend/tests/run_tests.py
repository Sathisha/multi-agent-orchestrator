#!/usr/bin/env python
"""
Test Suite Command-Line Interface

A convenient way to run tests with different options.

Usage:
    python tests_cli.py all              # Run all tests
    python tests_cli.py unit             # Run unit tests only
    python tests_cli.py property         # Run property tests only
    python tests_cli.py integration      # Run integration tests only
    python tests_cli.py quick            # Run quick tests (exclude slow)
    python tests_cli.py coverage         # Run with coverage report
    python tests_cli.py watch            # Watch mode (requires pytest-watch)
    python tests_cli.py --help           # Show help
"""

import subprocess
import sys
import os


def run_command(cmd, description=None):
    """Run a command and display output."""
    if description:
        print(f"\n{'='*70}")
        print(f"  {description}")
        print(f"{'='*70}\n")
    
    print(f"$ {' '.join(cmd)}\n")
    result = subprocess.run(cmd)
    return result.returncode == 0


def main():
    """Main CLI handler."""
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    # Change to backend directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    success = True
    
    if command == "all":
        success = run_command(
            ["pytest", "tests/", "-v"],
            "Running ALL tests (unit + property + integration)"
        )
    
    elif command == "unit":
        success = run_command(
            ["pytest", "tests/unit/", "-v"],
            "Running UNIT tests only"
        )
    
    elif command == "property":
        success = run_command(
            ["pytest", "tests/properties/", "-v"],
            "Running PROPERTY-BASED tests only"
        )
    
    elif command == "integration":
        success = run_command(
            ["pytest", "tests/integration/", "-v"],
            "Running INTEGRATION tests only"
        )
    
    elif command == "quick":
        success = run_command(
            ["pytest", "tests/", "-v", "-m", "not slow"],
            "Running QUICK tests (excluding slow tests)"
        )
    
    elif command == "coverage":
        success = run_command(
            ["pytest", "tests/", "-v", "--cov=shared", "--cov-report=html"],
            "Running tests with COVERAGE report"
        )
        if success:
            print("\n✅ Coverage report generated in htmlcov/index.html")
    
    elif command == "watch":
        success = run_command(
            ["ptw", "tests/", "-v"],
            "Running tests in WATCH mode (auto-rerun on changes)"
        )
    
    elif command == "parallel":
        success = run_command(
            ["pytest", "tests/", "-v", "-n", "auto"],
            "Running tests in PARALLEL"
        )
    
    elif command == "failed":
        success = run_command(
            ["pytest", "tests/", "-v", "--lf"],
            "Running FAILED tests from last run"
        )
    
    elif command == "--help" or command == "-h":
        print(__doc__)
        sys.exit(0)
    
    else:
        print(f"❌ Unknown command: {command}\n")
        print(__doc__)
        sys.exit(1)
    
    if success:
        print(f"\n✅ Tests completed successfully!")
        sys.exit(0)
    else:
        print(f"\n❌ Tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
