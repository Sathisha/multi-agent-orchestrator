"""
Unit tests for AI Agent Framework components.

Unit tests verify individual components in isolation without external dependencies.
Tests in this folder should:
- Test one component/function per test
- Mock external dependencies
- Run quickly (< 1 second each)
- Be deterministic and repeatable
- Not require database or network access

Test files:
- test_config.py: Configuration system tests
- test_database_models.py: ORM model tests
- test_guardrails.py: Guardrails engine unit tests
- test_logging.py: Logging system unit tests

Run unit tests with:
    pytest tests/unit/ -v
    pytest tests/unit/ -v -k "test_name"
"""