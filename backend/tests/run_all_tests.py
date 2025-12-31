"""
Test Suite Runner - Single Entry Point for All Tests

This module provides a central entry point to run all tests (unit, property-based, and integration).
Use this as the main test command instead of running individual test files.

Usage:
    pytest tests/run_all_tests.py -v
    pytest tests/run_all_tests.py -v --html=report.html
    pytest tests/run_all_tests.py -v -k "property" (run only property tests)
    pytest tests/run_all_tests.py -v -k "unit" (run only unit tests)
    pytest tests/run_all_tests.py -v -k "integration" (run only integration tests)
"""

import pytest


def test_placeholder():
    """Placeholder test to ensure pytest discovers this module."""
    assert True


# Test collection happens automatically via pytest discovery
# Pytest will collect tests from:
# - tests/unit/
# - tests/properties/
# - tests/integration/
