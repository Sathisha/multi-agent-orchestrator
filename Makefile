# AI Agent Framework - Simplified Makefile
# Essential commands for development, testing, and deployment

.PHONY: help dev-build dev-deploy prod-deploy docker-publish test clean logs shell

# ============================================================================
# HELP
# ============================================================================
help:
	@echo "AI Agent Framework - Essential Commands"
	@echo "========================================="
	@echo ""
	@echo "🏗️  Local Development:"
	@echo "  dev-build        - Build all Docker images locally"
	@echo "  dev-deploy       - Deploy locally (build + start all services)"
	@echo "  logs             - View backend logs"
	@echo "  shell            - Open shell in backend container"
	@echo "  clean            - Stop and remove all containers/volumes"
	@echo ""
	@echo "🧪 Testing:"
	@echo "  test             - Run all tests with coverage"
	@echo "  test-quick       - Run quick tests (no slow tests)"
	@echo ""
	@echo "🚀 Production:"
	@echo "  prod-deploy      - Deploy using production images from GHCR"
	@echo "  prod-stop        - Stop production deployment"
	@echo ""
	@echo "📦 CI/CD:"
	@echo "  docker-publish   - Build and push images to GHCR (manual trigger)"
	@echo ""

# ============================================================================
# LOCAL DEVELOPMENT - Full Build & Deploy
# ============================================================================

# Build all Docker images
dev-build:
	@echo "🔨 Building all Docker images..."
	@docker-compose build
	@echo "✅ Build complete!"

# Full local development deployment
dev-deploy: dev-build
	@echo "🚀 Starting all services..."
	@docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
	@echo "✅ Development environment ready!"
	@echo ""
	@echo "📍 Access points:"
	@echo "  - Frontend:  http://localhost:3000"
	@echo "  - Backend:   http://localhost:8000"
	@echo "  - API Docs:  http://localhost:8000/docs"
	@echo "  - Superset:  http://localhost:8088 (admin/admin)"
	@echo "  - Prometheus: http://localhost:9090"
	@echo ""

# ============================================================================
# PRODUCTION DEPLOYMENT - Pull & Deploy
# ============================================================================

# Deploy using pre-built images from GitHub Container Registry
prod-deploy:
	@echo "🚀 Pulling latest images from GHCR..."
	@docker-compose -f docker-compose.prod.yml pull
	@echo "🚀 Starting production services..."
	@docker-compose -f docker-compose.prod.yml up -d
	@echo "✅ Production deployment complete!"
	@echo ""
	@echo "📍 Access points:"
	@echo "  - Frontend:  http://localhost:3000"
	@echo "  - Backend:   http://localhost:8001"
	@echo "  - API Docs:  http://localhost:8001/docs"
	@echo ""

# Stop production deployment
prod-stop:
	@echo "🛑 Stopping production services..."
	@docker-compose -f docker-compose.prod.yml down

# Update production to latest images
prod-update:
	@echo "🔄 Updating to latest images..."
	@docker-compose -f docker-compose.prod.yml pull
	@docker-compose -f docker-compose.prod.yml up -d
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

# ============================================================================
# CI/CD - Docker Publishing
# ============================================================================

# Manually trigger Docker image build and push to GHCR
# Note: Normally triggered by GitHub Actions on push to main
docker-publish:
	@echo "📦 Building Docker images for publishing..."
	@docker build -t ghcr.io/$(GITHUB_REPOSITORY_OWNER)/multi-agent-orchestrator-backend:latest ./backend
	@docker build -t ghcr.io/$(GITHUB_REPOSITORY_OWNER)/multi-agent-orchestrator-frontend:latest ./frontend
	@docker build -t ghcr.io/$(GITHUB_REPOSITORY_OWNER)/multi-agent-orchestrator-ollama:latest ./infrastructure/docker/ollama
	@echo "📤 Pushing images to GitHub Container Registry..."
	@docker push ghcr.io/$(GITHUB_REPOSITORY_OWNER)/multi-agent-orchestrator-backend:latest
	@docker push ghcr.io/$(GITHUB_REPOSITORY_OWNER)/multi-agent-orchestrator-frontend:latest
	@docker push ghcr.io/$(GITHUB_REPOSITORY_OWNER)/multi-agent-orchestrator-ollama:latest
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

# Clean up everything
clean:
	@echo "🧹 Cleaning up..."
	@docker-compose down -v
	@docker-compose -f docker-compose.prod.yml down -v
	@docker system prune -f
	@echo "✅ Cleanup complete!"

# Stop development services
stop:
	@docker-compose down