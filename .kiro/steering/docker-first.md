---
inclusion: always
---

# Docker-First Development

## Development Philosophy

**Always use Docker Compose for testing and development. Do not install Python directly on the host system.**

## Key Principles

- All development and testing must be done within Docker containers
- Use `docker-compose` for orchestrating development services
- Python, dependencies, and runtime should be containerized
- Host system should only have Docker and Docker Compose installed

## Testing Commands

```bash
# Run tests in container
docker-compose exec backend pytest tests/ -v

# Run specific test files
docker-compose exec backend pytest tests/test_main.py -v

# Run with coverage
docker-compose exec backend pytest tests/ --cov=backend --cov-report=html

# Format code in container
docker-compose exec backend black .
docker-compose exec backend isort .

# Lint code in container
docker-compose exec backend flake8 .
docker-compose exec backend mypy .
```

## Development Workflow

1. Start services: `docker-compose up -d`
2. Run tests: `docker-compose exec backend pytest`
3. Make changes to code
4. Re-run tests in container
5. No Python installation required on host

This ensures consistent development environment across all team members and deployment targets.