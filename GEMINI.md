# Project Overview

This is a comprehensive platform designed to create, orchestrate, and deploy AI agents with enterprise-grade capabilities. It features a VS Code-style interface, BPMN workflow orchestration, robust enterprise security (RBAC, guardrails, audit trails), self-hosting options, and flexibility in LLM choices (OpenAI, Anthropic, Azure OpenAI, local models like Ollama). The architecture is extensible with a plugin system for custom tools and MCP server integrations.

**Key Technologies:**
*   **Backend:** Python (FastAPI, SQLAlchemy, PostgreSQL, Redis)
*   **Frontend:** React 18+ (TypeScript, Material-UI)
*   **Infrastructure:** Docker, Docker Compose, Kong Gateway, Camunda Platform 8, Ollama
*   **Security:** Keycloak, Casbin, Custom Guardrails Engine
*   **Monitoring:** Prometheus, Apache Superset

**Architecture:** Microservices-based with a Python backend and React/TypeScript frontend. Adheres to a Docker-first development approach.

# Building and Running

This project utilizes a **Docker-first development approach**, meaning all development and testing occur within Docker containers. You do not need Python, npm, or databases installed directly on your host machine.

### Prerequisites
*   **Docker**: Docker Desktop or Docker Engine installed.
*   **Docker Compose**: Included with Docker Desktop.

### Essential Commands

All commands are typically run using `make` from the project root.

*   **`make help`**: Show all available commands.
*   **`make setup`**: Complete initial setup (builds, starts, and migrates).
*   **`make start`**: Start core services (PostgreSQL, Redis, Keycloak, Kong, Ollama, Backend, Frontend).
*   **`make api`**: Start the backend API server with hot-reloading for development.
*   **`make test`**: Run all backend tests within Docker.
*   **`make logs`**: View logs for all running services.
*   **`make shell`**: Open a shell within the backend container.
*   **`make stop`**: Stop all running Docker services.
*   **`make clean`**: Stop all services and remove containers, networks, and volumes.

### Accessing the Application

*   **Frontend Application**: `http://localhost:3000` (for production build) or `http://localhost:3001` (for development with hot reload).
*   **Backend API**: `http://localhost:8000`
*   **API Documentation (Swagger UI)**: `http://localhost:8000/docs`
*   **API Health Check**: `http://localhost:8000/health`

# Development Conventions

*   **Docker-First Development**: Development environment consistency is maintained by performing all development and testing inside Docker containers.
*   **Code Quality**:
    *   `make format`: Format code using Black and iSort.
    *   `make lint`: Lint code using Flake8 and MyPy.
    *   `make test-coverage`: Run tests and generate a coverage report.
*   **Database Migrations (Alembic)**:
    *   `make migrate`: Apply pending database migrations.
    *   `make migration MESSAGE="<description>"`: Create a new Alembic migration script.

# Key Features Implemented

*   **Multi-tenancy removal**: The application has been refactored to remove all multi-tenancy related logic.
*   **LLM Model Management Page**: A new page has been implemented under `/models` in the frontend to manage LLM models.
*   **Ollama Integration**: The LLM model management now includes auto-discovery of Ollama models running in Docker. These models are cached to avoid repeated downloads on restarts.
*   **Model Tester**: A simple model tester has been integrated into the LLM model management page, allowing users to send sample requests to selected LLM models and view their responses. Now supports testing with OpenAI, Anthropic, and Azure OpenAI in addition to Ollama.
*   **Agent LLM Selection**: The "Create Agent" dialog on the `/agents` page now includes a dropdown for selecting LLM models (both configured and discovered Ollama models).
*   **Ollama Model Import**: Discovered Ollama models can now be easily imported into the configuration database with a single click.

# Remaining Tasks (if any)
*   **General Testing**: Ensure all existing and new functionalities are thoroughly tested across different providers.

Feel free to ask for specific tasks or details about any part of the project!
