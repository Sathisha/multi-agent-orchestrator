"""
Integration tests for AI Agent Framework.

Integration tests verify interactions between multiple components:
- API endpoint responses with database
- Service-to-service communication
- End-to-end workflow execution
- External service integration

These tests:
- Use real FastAPI TestClient
- Access test database
- May be slower than unit tests (2-30 seconds)
- Test realistic usage scenarios
- Verify component interactions

Test files:
- test_agent_api.py: Agent API endpoints
- test_agent_executor.py: Agent execution service
- test_agent_service.py: Agent service integration
- test_api_endpoints.py: General API endpoint tests
- test_audit_system.py: Complete audit system
- test_guardrails_integration.py: Guardrails system
- test_llm_providers.py: LLM provider integration
- test_memory_system.py: Memory system integration
- test_tool_registry.py: Tool registry integration
- test_workflow_orchestrator.py: Workflow orchestration
- [Additional integration tests...]

Run integration tests with:
    pytest tests/integration/ -v
    pytest tests/integration/ -v -m "not requires_docker" (skip Docker-dependent)
    pytest tests/integration/ -v -k "agent" (specific integration)
"""
