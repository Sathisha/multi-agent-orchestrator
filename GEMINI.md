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

This project utilizes a **Docker-first approach** with production-ready images. All services run within Docker containers using the production docker-compose.yml configuration.

### Prerequisites
*   **Docker**: Docker Desktop or Docker Engine installed.
*   **Docker Compose**: Included with Docker Desktop.

### Essential Commands

**CRITICAL:** This project strictly uses `docker-compose` for all build and testing operations. Do **NOT** try to run tests or build the backend directly on the host machine.

You can use the `make` wrappers which execute the underlying `docker-compose` commands:

*   **`make help`**: Show all available commands.
*   **`make build`**: Build images using `docker-compose build`.
*   **`make deploy`**: Deploy using `docker-compose up -d`.
*   **`make pull`**: Pull images using `docker-compose pull`.
*   **`make update`**: Update images and restart services.
*   **`make test`**: Run backend tests via `docker-compose run backend pytest`.
*   **`make logs`**: View logs via `docker-compose logs`.
*   **`make shell`**: Open shell via `docker-compose exec backend bash`.
*   **`make stop`**: Stop services via `docker-compose stop`.
*   **`make clean`**: Remove containers via `docker-compose down -v`.

### Accessing the Application

*   **Frontend Application**: `http://localhost:3000`
*   **Backend API**: `http://localhost:8001`
*   **API Documentation (Swagger UI)**: `http://localhost:8001/docs`
*   **API Health Check**: `http://localhost:8001/health`
*   **Superset Dashboard**: `http://localhost:8088` (admin/admin)
*   **Prometheus Monitoring**: `http://localhost:9090`

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
*   **Configurable Embedding Providers**: The system now supports both OpenAI and local (SentenceTransformers) embedding providers, with OpenAI as the default to improve startup performance and avoid large model downloads.

# Configuration

### Memory & Embeddings
The memory system can be configured using environment variables:
*   `MEMORY_EMBEDDING_PROVIDER`: "openai" (default) or "local".
*   `MEMORY_EMBEDDING_MODEL`: e.g., "text-embedding-3-small" (default) or "all-MiniLM-L6-v2".
*   `OPENAI_API_KEY`: Required if using the OpenAI provider.
*   `MEMORY_VECTOR_DB_PATH`: Path to the vector database (default: `./data/chroma`).

# Remaining Tasks (if any)
*   **General Testing**: Ensure all existing and new functionalities are thoroughly tested across different providers.

Feel free to ask for specific tasks or details about any part of the project!
