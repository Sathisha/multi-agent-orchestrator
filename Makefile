# AI Agent Framework - Simplified Makefile
# Essential commands for building, deploying, and testing

# ============================================================================
# VARIABLES
# ============================================================================
GITHUB_REPOSITORY_OWNER ?= sathisha

.PHONY: help build deploy stop clean test logs shell docker-publish

# ============================================================================
# HELP
# ============================================================================
help:
	@echo "AI Agent Framework - Essential Commands"
	@echo "========================================="
	@echo ""
	@echo "🏗️  Build & Deploy:"
	@echo "  build            - Build all Docker images locally"
	@echo "  deploy           - Deploy application (pull images from GHCR or build locally)"
	@echo "  stop             - Stop all running services"
	@echo "  clean            - Stop and remove all containers/volumes"
	@echo ""
	@echo "🧪 Testing:"
	@echo "  test             - Run all tests with coverage"
	@echo "  test-quick       - Run quick tests (no slow tests)"
	@echo "  test-tools       - Run tool integration tests"
	@echo "  test-e2e         - Run end-to-end tests"
	@echo ""
	@echo "📚 Documentation:"
	@echo "  api-docs         - Export OpenAPI specification"
	@echo "  api-docs-serve   - Serve API docs locally"
	@echo ""
	@echo "🔧 Utilities:"
	@echo "  logs             - View backend logs"
	@echo "  shell            - Open shell in backend container"
	@echo ""
	@echo "📦 CI/CD:"
	@echo "  docker-publish   - Build and push images to GHCR (manual trigger)"
	@echo ""

# ============================================================================
# BUILD & DEPLOY
# ============================================================================

# Build all Docker images locally
build:
	@echo "🔨 Building all Docker images..."
	@docker-compose build
	@echo "✅ Build complete!"

# Deploy application
deploy:
	@echo "🚀 Starting all services..."
	@docker-compose up -d
	@echo "✅ Deployment complete!"
	@echo ""
	@echo "📍 Access points:"
	@echo "  - Frontend:   http://localhost:3000"
	@echo "  - Backend:    http://localhost:8001"
	@echo "  - API Docs:   http://localhost:8001/docs"
	@echo "  - Superset:   http://localhost:8088 (admin/admin)"
	@echo "  - Prometheus: http://localhost:9090"
	@echo ""

# Stop all services
stop:
	@echo "🛑 Stopping all services..."
	@docker-compose down

# Clean up everything
clean:
	@echo "🧹 Cleaning up..."
	@docker-compose down -v
	@docker system prune -f
	@if exist logs powershell -Command "Remove-Item -Path logs\* -Include *.log -Recurse -Force -ErrorAction SilentlyContinue"
	@echo "✅ Cleanup complete!"

# Pull latest images from GHCR
pull:
	@echo "🚀 Pulling latest images from GHCR..."
	@docker-compose pull
	@echo "✅ Images pulled!"

# Update to latest images and restart
update: pull
	@echo "🔄 Updating to latest images..."
	@docker-compose up -d
	@echo "✅ Update complete!"

# ============================================================================
# TESTING - Full Test Suite
# ============================================================================

# Run all tests with coverage
test:
	@echo "🧪 Running full test suite..."
	@docker-compose exec -T backend bash -c "export PYTHONPATH=/app:/app/backend && mkdir -p reports htmlcov && pytest tests/ -v --cov=shared --cov-report=html --cov-report=term-missing --junit-xml=reports/junit.xml"
	@echo ""
	@echo "✅ Tests completed!"
	@echo "📊 Coverage: htmlcov/index.html"
	@echo "📋 JUnit: reports/junit.xml"

# Quick tests (skip slow tests)
test-quick:
	@echo "🧪 Running quick tests..."
	@docker-compose exec -T backend pytest tests/ -v -m 'not slow' --cov=shared --cov-report=term-missing
	@echo "✅ Quick tests completed!"

# Run tool-specific tests
test-tools:
	@echo "🧪 Running tool integration tests..."
	@docker-compose exec -T backend bash -c "export PYTHONPATH=/app:/app/backend && pytest tests/integration/test_tool_execution.py tests/integration/test_agent_with_tools.py -v"
	@echo "✅ Tool tests completed!"

# Run end-to-end tests
test-e2e:
	@echo "🧪 Running end-to-end tests..."
	@docker-compose exec -T backend bash -c "export PYTHONPATH=/app:/app/backend && pytest tests/e2e/ -v"
	@echo "✅ E2E tests completed!"

# ============================================================================
# API DOCUMENTATION
# ============================================================================

# Export OpenAPI specification
api-docs:
	@echo "📚 Exporting OpenAPI specification..."
	@if not exist "docs\\api" mkdir docs\\api
	@powershell -Command "Invoke-WebRequest -Uri 'http://localhost:8001/openapi.json' -OutFile 'docs\\api\\openapi.json'"
	@echo "✅ OpenAPI spec exported to docs/api/openapi.json"

# Serve API docs locally
api-docs-serve:
	@echo "📚 Starting local documentation server..."
	@echo "📍 Open http://localhost:8080 in your browser"
	@echo "📍 Swagger UI: http://localhost:8080/api/swagger-ui.html"
	@cd docs && python -m http.server 8080

# ============================================================================
# CI/CD - Docker Publishing
# ============================================================================

# Manually trigger Docker image build and push to GHCR
# Note: Normally triggered by GitHub Actions on push to main
docker-publish:
	@echo "📦 Building Docker images for publishing..."
	@docker build -t ghcr.io/$(GITHUB_REPOSITORY_OWNER)/multi-agent-orchestrator-backend:latest ./backend
	@docker build -t ghcr.io/$(GITHUB_REPOSITORY_OWNER)/multi-agent-orchestrator-frontend:latest ./frontend
	@echo "📤 Pushing images to GitHub Container Registry..."
	@docker push ghcr.io/$(GITHUB_REPOSITORY_OWNER)/multi-agent-orchestrator-backend:latest
	@docker push ghcr.io/$(GITHUB_REPOSITORY_OWNER)/multi-agent-orchestrator-frontend:latest
	@echo "✅ Images published!"

# ============================================================================
# UTILITIES
# ============================================================================

# View backend logs
logs:
	@docker-compose logs -f backend

# Open shell in backend container
shell:
	@docker-compose exec backend /bin/bash
# Register built-in tools (web search, Wikipedia, etc.)
setup-tools:
	@echo "🔧 Registering built-in tools..."
	@docker-compose exec -T backend bash -c "export PYTHONPATH=/app && python scripts/register_builtin_tools.py"
	@echo "✅ Tools registered! Use 'curl http://localhost:8001/api/v1/tools' to see them"
