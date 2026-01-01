# AI Agent Framework Development Makefile

.PHONY: help setup start stop api test test-v test-unit test-property test-integration test-quick test-file test-coverage test-mark test-keyword test-llm test-memory test-audit test-guardrails test-tools test-debug test-help format lint clean migration migrate build logs shell dev ci

# Default target
help:
	@echo "AI Agent Framework Development Commands"
	@echo "======================================"
	@echo ""
	@echo "Setup & Infrastructure:"
	@echo "  setup            - Set up development environment with auto DB recreation"
	@echo "  build            - Build Docker images"
	@echo "  build-backend    - Build backend Docker image"
	@echo "  build-frontend   - Build frontend Docker image"
	@echo "  start            - Start all services (equivalent to 'docker-compose up -d')"
	@echo "  start-dev        - Start development environment with auto DB recreation (frontend and backend)"
	@echo "  start-prod       - Start production-like environment (no DB recreation)"
	@echo "  start-all-dev    - Start all services in development mode"
	@echo "  restart-backend  - Restart backend service"
	@echo "  restart-frontend - Restart frontend service"
	@echo "  api              - Start API server in development mode"
	@echo "  api-prod         - Start API server in production mode"
	@echo "  stop             - Stop all services"
	@echo "  clean            - Clean up containers and volumes"
	@echo ""
	@echo "Testing (run in existing development containers):"
	@echo "  NOTE: Ensure development containers are running with 'make start' or 'make start-dev'"
	@echo "  test            - Run all tests"
	@echo "  test-v          - Run all tests with verbose output"
	@echo "  test-unit       - Run unit tests only"
	@echo "  test-property   - Run property-based tests only"
	@echo "  test-integration- Run integration tests only"
	@echo "  test-quick      - Run quick tests (no slow tests)"
	@echo "  test-coverage   - Run tests with coverage report"
	@echo "  test-llm        - Run LLM-related tests"
	@echo "  test-memory     - Run memory-related tests"
	@echo "  test-audit      - Run audit-related tests"
	@echo "  test-guardrails - Run guardrails tests"
	@echo "  test-tools      - Run tool registry tests"
	@echo "  test-file FILE=... - Run specific test file"
	@echo "  test-mark MARKER=... - Run tests with marker"
	@echo "  test-keyword KEYWORD=... - Run tests with keyword filter"
	@echo "  test-debug      - Run tests with debugging (pdb on failure)"
	@echo "  test-help       - Show detailed test help"
	@echo ""
	@echo "Code Quality:"
	@echo "  format    - Format code with black and isort"
	@echo "  lint      - Lint code with flake8 and mypy"
	@echo ""
	@echo "Database (manual operations - usually automated):"
	@echo "  force-recreate-db - Force database recreation"
	@echo ""
	@echo "Utilities:"
	@echo "  logs      - Show backend service logs"
	@echo "  shell     - Open shell in backend container"
	@echo "  dev       - Full development cycle (setup + api)"
	@echo "  ci        - CI/CD pipeline simulation (build + test + lint)"
	@echo ""

# Setup development environment
setup: build start-dev
	@echo "✅ Development environment ready!"
	@echo "API available at: http://localhost:8000"
	@echo "API docs at: http://localhost:8000/docs"

# Build Docker images
build:
	@echo "🔨 Building Docker images..."
	@docker-compose build

# Build backend image
build-backend:
	@echo "🔨 Building backend Docker image..."
	@docker-compose build backend

# Build frontend image
build-frontend:
	@echo "🔨 Building frontend Docker image..."
	@docker-compose build frontend

# Restart backend service
restart-backend:
	@echo "🔄 Restarting backend service..."
	@docker-compose restart backend

# Restart frontend service
restart-frontend:
	@echo "🔄 Restarting frontend service..."
	@docker-compose restart frontend

# Start all services
start:
	@echo "🚀 Starting all services..."
	@docker-compose up -d

# Start development environment with auto database recreation
start-dev:
	@echo "🚀 Starting development environment with database auto-initialization..."
	@docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d postgres redis
	@echo "⏳ Waiting for database to be ready..."
	@timeout 10
	@echo "🔄 Starting backend with automatic database recreation..."
	@docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d backend

# Start production-like environment (no database recreation)
start-prod:
	@echo "🚀 Starting production-like environment..."
	@docker-compose up -d postgres redis backend

# Start all services
start-all:
	@docker-compose up -d

# Start all services in development mode
start-all-dev:
	@docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# Stop all services
stop:
	@docker-compose down

# Start API server in development mode (with auto database recreation)
api:
	@docker-compose -f docker-compose.yml -f docker-compose.dev.yml up backend

# Start API server in production mode (no database recreation)
api-prod:
	@docker-compose up backend

# ============================================================================
# TEST TARGETS - Run tests in existing development containers
# ============================================================================

# Run all tests with coverage and JUnit reports using existing containers
test:
	@mkdir -p reports htmlcov
	@echo "🧪 Running all tests in development containers..."
	@./scripts/ensure-dev-containers.sh
	@docker-compose exec -T backend pytest tests/ -v --cov=shared --cov-report=html --cov-report=term-missing --junit-xml=reports/junit.xml
	@echo ""
	@echo "✅ Test execution completed!"
	@echo "📊 Coverage Report: htmlcov/index.html"
	@echo "📋 JUnit XML Report: reports/junit.xml"
	@echo ""

# Run all tests with verbose output
test-v:
	@echo "🧪 Running all tests with verbose output..."
	@docker-compose exec -T backend pytest tests/ -vv

# Run unit tests only
test-unit:
	@mkdir -p reports htmlcov
	@echo "🧪 Running unit tests..."
	@docker-compose exec -T backend pytest tests/unit/ -v --cov=shared --cov-report=html --cov-report=term-missing --junit-xml=reports/junit.xml

# Run property-based tests only
test-property:
	@mkdir -p reports htmlcov
	@echo "🧪 Running property-based tests..."
	@docker-compose exec -T backend pytest tests/properties/ -v --cov=shared --cov-report=html --cov-report=term-missing --junit-xml=reports/junit.xml

# Run integration tests only
test-integration:
	@mkdir -p reports htmlcov
	@echo "🧪 Running integration tests..."
	@docker-compose exec -T backend pytest tests/integration/ -v --cov=shared --cov-report=html --cov-report=term-missing --junit-xml=reports/junit.xml

# Run quick tests (unit + essential integration, no slow tests)
test-quick:
	@mkdir -p reports htmlcov
	@echo "🧪 Running quick tests..."
	@docker-compose exec -T backend pytest tests/ -v -m 'not slow and not requires_docker' --cov=shared --cov-report=html --cov-report=term-missing --junit-xml=reports/junit.xml

# Run specific test file
test-file:
	@if [ -z "$(FILE)" ]; then \
		echo "Error: FILE is required. Usage: make test-file FILE=tests/unit/test_config.py"; \
		exit 1; \
	fi
	@mkdir -p reports htmlcov
	@echo "🧪 Running test file: $(FILE)"
	@docker-compose exec -T backend pytest $(FILE) -v --cov=shared --cov-report=html --cov-report=term-missing --junit-xml=reports/junit.xml

# Run tests with coverage report
test-coverage:
	@echo "🧪 Running tests with coverage report..."
	@docker-compose exec -T backend pytest tests/ -v --cov=shared --cov-report=html --cov-report=term-missing
	@echo "📊 Coverage report generated in htmlcov/index.html"

# Run tests with specific marker
test-mark:
	@if [ -z "$(MARKER)" ]; then \
		echo "Error: MARKER is required. Usage: make test-mark MARKER=slow"; \
		exit 1; \
	fi
	@mkdir -p reports htmlcov
	@echo "🧪 Running tests with marker: $(MARKER)"
	@docker-compose exec -T backend pytest tests/ -v -m '$(MARKER)' --cov=shared --cov-report=html --cov-report=term-missing --junit-xml=reports/junit.xml

# Run tests with keyword filter
test-keyword:
	@if [ -z "$(KEYWORD)" ]; then \
		echo "Error: KEYWORD is required. Usage: make test-keyword KEYWORD=audit"; \
		exit 1; \
	fi
	@mkdir -p reports htmlcov
	@echo "🧪 Running tests with keyword: $(KEYWORD)"
	@docker-compose exec -T backend pytest tests/ -v -k '$(KEYWORD)' --cov=shared --cov-report=html --cov-report=term-missing --junit-xml=reports/junit.xml

# Run LLM tests
test-llm:
	@mkdir -p reports htmlcov
	@echo "🧪 Running LLM tests..."
	@docker-compose exec -T backend pytest tests/integration/ -v -k 'llm or ollama' --cov=shared --cov-report=html --cov-report=term-missing --junit-xml=reports/junit.xml

# Run memory tests
test-memory:
	@mkdir -p reports htmlcov
	@echo "🧪 Running memory tests..."
	@docker-compose exec -T backend pytest tests/integration/ -v -k 'memory' --cov=shared --cov-report=html --cov-report=term-missing --junit-xml=reports/junit.xml

# Run audit tests
test-audit:
	@mkdir -p reports htmlcov
	@echo "🧪 Running audit tests..."
	@docker-compose exec -T backend pytest tests/ -v -k 'audit' --cov=shared --cov-report=html --cov-report=term-missing --junit-xml=reports/junit.xml

# Run guardrails tests
test-guardrails:
	@mkdir -p reports htmlcov
	@echo "🧪 Running guardrails tests..."
	@docker-compose exec -T backend pytest tests/integration/ -v -k 'guardrails' --cov=shared --cov-report=html --cov-report=term-missing --junit-xml=reports/junit.xml

# Run tool registry tests
test-tools:
	@mkdir -p reports htmlcov
	@echo "🧪 Running tool registry tests..."
	@docker-compose exec -T backend pytest tests/integration/ -v -k 'tool or mcp' --cov=shared --cov-report=html --cov-report=term-missing --junit-xml=reports/junit.xml

# Interactive debugging - drops into pdb on failure
test-debug:
	@mkdir -p reports htmlcov
	@echo "🧪 Running tests with debugging..."
	@docker-compose exec backend pytest tests/ -v --pdb --cov=shared --cov-report=html --cov-report=term-missing --junit-xml=reports/junit.xml

# Show test help
test-help:
	@echo "Test Commands"
	@echo "============="
	@echo "make test              - Run all tests"
	@echo "make test-v            - Run all tests with verbose output"
	@echo "make test-unit         - Run unit tests only"
	@echo "make test-property     - Run property-based tests only"
	@echo "make test-integration  - Run integration tests only"
	@echo "make test-quick        - Run quick tests (no slow tests)"
	@echo "make test-file FILE=...  - Run specific test file"
	@echo "make test-coverage     - Run tests with coverage report"
	@echo "make test-mark MARKER=... - Run tests with specific marker"
	@echo "make test-keyword KEYWORD=... - Run tests with keyword filter"
	@echo "make test-llm          - Run LLM-related tests"
	@echo "make test-memory       - Run memory-related tests"
	@echo "make test-audit        - Run audit-related tests"
	@echo "make test-guardrails   - Run guardrails tests"
	@echo "make test-tools        - Run tool registry tests"
	@echo "make test-debug        - Run tests with debugging (pdb on failure)"

# Format code in Docker
format:
	@docker-compose exec backend black .
	@docker-compose exec backend isort .

# Lint code in Docker
lint:
	@docker-compose exec backend flake8 .
	@docker-compose exec backend mypy .

# Clean up Docker containers and volumes
clean:
	@docker-compose down -v
	@docker system prune -f

# Database operations (now automated in Docker startup)
init-db:
	@echo "ℹ️  Database initialization is now automated during container startup"
	@echo "   Use 'make start-dev' for development with auto DB recreation"
	@echo "   Use 'make start-prod' for production-like mode without recreation"
	@echo "   Manual initialization (if needed):"
	@docker-compose exec backend python3 init_db.py

recreate-db:
	@echo "ℹ️  Database recreation is now automated in development mode"
	@echo "   Use 'make start-dev' or 'make api' for auto recreation"
	@echo "   Manual recreation (if needed):"
	@docker-compose exec backend python3 init_db.py --recreate

# Force database recreation (manual override)
force-recreate-db:
	@echo "🔄 Forcing database recreation..."
	@docker-compose exec backend python3 init_db.py --recreate

# Legacy migration targets (disabled during development)
migration:
	@echo "❌ Migrations disabled during development phase"
	@echo "   Use 'make init-db' or 'make recreate-db' instead"
	@exit 1

migrate:
	@echo "❌ Migrations disabled during development phase"
	@echo "   Use 'make init-db' or 'make recreate-db' instead"
	@exit 1

# Show backend logs
logs:
	@docker-compose logs -f backend

# Open shell in backend container
shell:
	@docker-compose exec backend /bin/bash

# Full development cycle (now with auto DB setup)
dev: setup api

# CI/CD pipeline simulation (now with auto DB setup)
ci: build start-prod test lint