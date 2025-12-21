# AI Agent Framework Development Makefile

.PHONY: help setup start stop api test format lint clean migration migrate build logs shell

# Default target
help:
	@echo "AI Agent Framework Development Commands"
	@echo "======================================"
	@echo "setup     - Set up development environment"
	@echo "build     - Build Docker images"
	@echo "start     - Start development services (postgres, redis)"
	@echo "start-all - Start all services including optional ones"
	@echo "stop      - Stop all services"
	@echo "api       - Start API server"
	@echo "test      - Run tests in Docker"
	@echo "format    - Format code with black and isort in Docker"
	@echo "lint      - Lint code with flake8 and mypy in Docker"
	@echo "clean     - Clean up containers and volumes"
	@echo "migration - Create new database migration (requires MESSAGE=)"
	@echo "migrate   - Run database migrations in Docker"
	@echo "logs      - Show backend service logs"
	@echo "shell     - Open shell in backend container"

# Setup development environment
setup: build start migrate
	@echo "✅ Development environment ready!"
	@echo "API available at: http://localhost:8000"
	@echo "API docs at: http://localhost:8000/docs"

# Build Docker images
build:
	@docker-compose build

# Start core development services
start:
	@docker-compose up -d postgres redis
	@echo "⏳ Waiting for services to be ready..."
	@sleep 10

# Start all services
start-all:
	@docker-compose up -d

# Stop all services
stop:
	@docker-compose down

# Start API server
api:
	@docker-compose up backend

# Run tests in Docker
test:
	@docker-compose exec backend pytest tests/ -v

# Run tests with coverage
test-coverage:
	@docker-compose exec backend pytest tests/ --cov=backend --cov-report=html --cov-report=term

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

# Create database migration in Docker
migration:
	@if [ -z "$(MESSAGE)" ]; then \
		echo "Error: MESSAGE is required. Usage: make migration MESSAGE='your message'"; \
		exit 1; \
	fi
	@docker-compose exec backend alembic revision --autogenerate -m "$(MESSAGE)"

# Run database migrations in Docker
migrate:
	@docker-compose exec backend alembic upgrade head

# Show backend logs
logs:
	@docker-compose logs -f backend

# Open shell in backend container
shell:
	@docker-compose exec backend /bin/bash

# Full development cycle
dev: setup api

# CI/CD pipeline simulation
ci: build start migrate test lint