# AI Agent Framework

A comprehensive platform that enables developers to create, orchestrate, and deploy AI agents with minimal complexity while maintaining enterprise-grade capabilities.

## 🚀 Key Features

- **VS Code-Style Interface**: Familiar developer experience with workspaces for agents, workflows, tools, and monitoring.
- **Enterprise Security**: Built-in RBAC (Casbin), guardrails, audit trails, and compliance features.
- **LLM Management**: Centralized management for OpenAI, Anthropic, Azure OpenAI, Gemini, and local Ollama models.
- **Ollama Integration**: Auto-discovery and easy import of local Ollama models.
- **Model Testing**: Built-in playground to test and validate different LLM models and configurations.
- **Agent Capabilities**: Configurable agents with specific LLM selection and tool integration.
- **Extensible Architecture**: Plugin system for custom tools and MCP server integrations.
- **Self-Hosting**: Complete data sovereignty with Docker-first deployment.


## 🛡️ Enterprise-Grade Capabilities

Designed for mission-critical applications, the platform includes a robust suite of enterprise features:

### 🔐 Advanced Security & RBAC
- **Fine-Grained Access Control**: Implements Casbin for attribute-based and role-based access control (RBAC).
  - **System Admin**: Full access to all system configurations and user management.
  - **Developer**: Create and manage agents, workflows, and tools.
  - **User/Viewer**: Execute agents and view results without modification rights.
- **Identity Management**: Integrated Keycloak for centralized authentication, SSO, and user management.
- **Secure Communication**: End-to-end encryption for all data in transit.

### 🛡️ AI Guardrails & Safety
- **Input/Output Validation**: Real-time validation of LLM inputs and outputs to prevent injection attacks and ensure content safety.
- **Policy Enforcement**: Define and enforce organization-wide policies for AI agent behaviors.
- **Hallucination Detection**: Mechanisms to cross-reference and validate LLM-generated content (planned).

### ⚖️ Scalability & Reliability
- **Load Balancing**: Kong Gateway acts as an API gateway to manage traffic, enforce rate limits, and provide load balancing across services.
- **High Availability**: Stateless microservices architecture designed to run on Kubernetes or Docker Swarm.
- **Resource Management**: Optimized container orchestration to handle varying loads efficiently.

### 📊 Audit & Compliance
- **Comprehensive Audit Logs**: Detailed tracking of who did what and when for security auditing.
- **Execution History**: Complete storage of agent execution runs, prompts, and completion data for review.
- **Data Sovereignty**: Flexible deployment options allow you to keep all data within your own infrastructure.

## 🏗️ Architecture

- **Backend**: Python microservices with FastAPI, PostgreSQL, Redis
- **Frontend**: React 18+ with TypeScript and VS Code-style interface
- **Security**: Keycloak authentication, Casbin RBAC, comprehensive guardrails
- **Monitoring**: Prometheus metrics with Apache Superset dashboards

## 📋 Project Status

This project is in **Active Development**. Core architecture is in place, including multi-tenancy removal, comprehensive model management, and workflow orchestration. See `MEMORY[GEMINI.md]` for the latest implementation details.

## 🛠️ Technology Stack

- **Backend**: Python 3.11+, FastAPI, SQLAlchemy, PostgreSQL, Redis
- **Frontend**: React 18+, TypeScript, Material-UI, Monaco Editor, React Flow
- **Infrastructure**: Docker, Docker Compose, Kong Gateway
- **Security**: Keycloak, Casbin, Custom Guardrails Engine
- **Monitoring**: Prometheus, Apache Superset, Structured Logging

## ⚙️ Configuration

### Memory & Embeddings
The memory system can be configured using environment variables:
- `MEMORY_EMBEDDING_PROVIDER`: "openai" (default) or "local" (SentenceTransformers).
- `MEMORY_EMBEDDING_MODEL`: e.g., "text-embedding-3-small" (default) or "all-MiniLM-L6-v2".
- `OPENAI_API_KEY`: Required if using the OpenAI provider.
- `MEMORY_VECTOR_DB_PATH`: Path to the vector database (default: `./data/chroma`).

## 📁 Project Structure

```
ai-agent-framework/
├── .kiro/                          # Kiro configuration and specs
│   ├── specs/                      # Feature specifications
│   └── steering/                   # AI assistant guidance rules
├── backend/                        # Python microservices
├── frontend/                       # React TypeScript application
├── infrastructure/                 # Deployment and infrastructure
├── docs/                           # Documentation
└── config/                         # Configuration files
```

## 🚀 Getting Started

### Prerequisites

- **Docker**: Install Docker Desktop or Docker Engine
- **Docker Compose**: Included with Docker Desktop, or install separately

### Quick Start

1. **Clone and Setup**:
   ```bash
   git clone <repository-url>
   cd ai-agent-framework
   ```

2. **Run Setup Script** (Linux/Mac):
   ```bash
   ./scripts/docker-setup.sh
   ```

3. **Manual Setup** (Windows or alternative):
   ```bash
   # Copy environment file
   copy .env.example .env
   
   # Build and start services
   make setup
   ```

4. **Start Development**:
   ```bash
   # Start API server
   make api
   
   # In another terminal, run tests
   make test
   ```

5. **Access the Application**:
   - Frontend: http://localhost:3000 (or http://localhost:3001 for dev)
   - API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs
   - Health Check: http://localhost:8000/health

### Development Commands

```bash
# Essential commands
make help          # Show all available commands
make setup         # Complete setup (build, start, migrate)
make start         # Start core services (postgres, redis)
make api           # Start API server with hot reload
make test          # Run all tests in Docker
make logs          # View backend service logs
make shell         # Open shell in backend container

# Code quality
make format        # Format code with black and isort
make lint          # Lint code with flake8 and mypy
make test-coverage # Run tests with coverage report

# Database operations
make migrate                           # Run migrations
make migration MESSAGE="description"   # Create new migration

# Service management
make start-all     # Start all services (including optional)
make stop          # Stop all services
make clean         # Clean up containers and volumes
```

### Docker-First Development

This project uses a **Docker-first development approach**:

- ✅ All development and testing happens in Docker containers
- ✅ No need to install Python, dependencies, or databases on your host
- ✅ Consistent environment across all developers and deployment targets
- ✅ Easy setup and teardown of development environment

### Project Structure

```
ai-agent-framework/
├── backend/                        # Python FastAPI services
│   ├── main.py                     # Main application entry point
│   ├── requirements.txt            # Python dependencies
│   ├── alembic/                    # Database migrations
│   ├── shared/                     # Shared utilities and models
│   └── tests/                      # Test suite
├── infrastructure/                 # Docker and deployment configs
│   └── docker/                     # Docker service configurations
├── scripts/                        # Development helper scripts
├── docker-compose.yml              # Main service definitions
├── docker-compose.override.yml     # Development overrides
├── Makefile                        # Development commands
└── .env.example                    # Environment configuration template
```

## 📄 License & Attribution

### Project License

This project uses only permissive licenses (MIT, Apache 2.0, BSD) that are safe for commercial use and monetization.

### Third-Party Software

This project incorporates and extends the following open-source software:

**Core Infrastructure:**
- **Ollama** - MIT License - Copyright (c) Ollama
  - Source: https://github.com/ollama/ollama
  - We extend the official Ollama Docker image with custom model management
  - See `deployment/LICENSES/OLLAMA-LICENSE` for full license text

**Docker Base Images:**
- PostgreSQL (PostgreSQL License)
- Redis (BSD 3-Clause)
- Keycloak (Apache 2.0)
- Kong Gateway (Apache 2.0)
- Prometheus (Apache 2.0)
- Apache Superset (Apache 2.0)
- nginx (2-Clause BSD)

### LLM Model Licensing

> **⚠️ Important**: LLM models have separate licenses from the Ollama software and this project.

**Pre-configured Models** (auto-downloaded on first startup):
- `nomic-embed-text` - Apache License 2.0
- `tinyllama` - Apache License 2.0
- `phi` - MIT License

**User Responsibility**: When you pull additional models using `ollama pull <model>`, you are responsible for:
1. Reviewing the model's license (available at https://ollama.com/library/<model>)
2. Ensuring it permits your intended use (commercial, research, etc.)
3. Complying with any attribution or usage requirements

Some models (e.g., Meta Llama) have proprietary licenses with specific terms for commercial use and attribution requirements.

**For Complete Details**: See `deployment/LICENSES/THIRD-PARTY-NOTICES.md`

## 🤝 Contributing

This project is currently in active development. Please refer to the implementation tasks for current development priorities.