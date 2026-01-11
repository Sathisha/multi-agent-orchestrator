# AI Agent Framework

A comprehensive platform that enables developers to create, orchestrate, and deploy AI agents with minimal complexity while maintaining enterprise-grade capabilities.

## 🚀 Key Features

- **VS Code-Style Interface**: Familiar developer experience with workspaces for agents, workflows, tools, and monitoring.
- **Advanced Workflow Orchestration**: Create complex, multi-agent workflows with branching, parallel execution, and conditional logic.
- **API-First Design**: Execute workflows programmatically via securely authenticated REST APIs.
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
- **Orchestration**: Custom graph-based workflow engine with parallel execution support
- **Security**: Keycloak authentication, Casbin RBAC, comprehensive guardrails
- **Monitoring**: Prometheus metrics with Apache Superset dashboards

## 📋 Project Status

This project is in **Active Development**. Core architecture is in place, featuring:
- **Docker-First Development**: Consistent environments for all developers.
- **Multi-Tenancy Removal**: Simplified architecture for single-tenant enterprise deployments.
- **Workflow Engine**: New internal orchestration engine replacing external BPMN dependencies.
- **Ollama Integration**: Seamless local LLM support.

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
multi-agent-orchestrator/
├── .kiro/                          # Kiro configuration and specs
├── backend/                        # Python FastAPI services
├── frontend/                       # React TypeScript application
├── infrastructure/                 # Deployment and infrastructure
├── docs/                           # Documentation
└── config/                         # Configuration files
```

## 🚀 Getting Started

### Prerequisites

- **Docker**: Install Docker Desktop or Docker Engine
- **Docker Compose**: Included with Docker Desktop, or install separately
- **Make**: (Optional) For running simplified commands. Windows users can use WSL2 or Git Bash.

### Quick Start

1. **Clone and Setup**:
   ```bash
   git clone <repository-url>
   cd multi-agent-orchestrator
   ```

2. **Start Development Environment**:
   ```bash
   make dev-deploy
   ```
   This command builds all images and starts the services in development mode.

3. **Access the Application**:
   - **Frontend**: http://localhost:3000
   - **Backend API**: http://localhost:8000
   - **API Documentation**: http://localhost:8000/docs
   - **Superset (Monitoring)**: http://localhost:8088 (User: `admin`, Pass: `admin`)
   - **Prometheus**: http://localhost:9090
   - **Keycloak**: http://localhost:8080 (User: `admin`, Pass: `admin`)

### Development Commands

We provide a `Makefile` to simplify common development tasks:

```bash
# 🏗️  Local Development
make dev-build        # Build all Docker images locally
make dev-deploy       # Deploy locally (build + start all services)
make logs             # View backend logs
make shell            # Open shell in backend container
make clean            # Stop and remove all containers/volumes

# 🧪 Testing
make test             # Run all tests with coverage
make test-quick       # Run quick tests (no slow tests)

# 🚀 Production
make prod-deploy      # Deploy using production images from GHCR
make prod-stop        # Stop production deployment

# 📦 CI/CD
make docker-publish   # Build and push images to GHCR (requires permissions)
```

### Docker-First Development

This project uses a **Docker-first development approach**:

- ✅ All development and testing happens in Docker containers
- ✅ No need to install Python, dependencies, or databases on your host
- ✅ Consistent environment across all developers and deployment targets
- ✅ Easy setup and teardown of development environment

### Production Deployment

For production environments, we recommend using the pre-built images stored in GitHub Container Registry (GHCR) rather than building from source.

1. **Pull and Deploy**:
   ```bash
   make prod-deploy
   ```
   This uses `docker-compose.prod.yml` to pull optimized images and run them.

2. **Update**:
   ```bash
   make prod-update
   ```

## 📡 API Documentation

Comprehensive API documentation is available in multiple formats:

### Interactive Documentation
- **[Swagger UI (Live)](https://sathisha.github.io/multi-agent-orchestrator/api/swagger-ui.html)** - Interactive API explorer hosted on GitHub Pages
- **[Local Swagger UI](http://localhost:8000/docs)** - When running the application locally
- **[ReDoc](http://localhost:8000/redoc)** - Alternative documentation format

### Documentation Resources
- **[API Guide](API.md)** - Comprehensive guide covering:
  - Authentication methods (API Keys, JWT, Sessions)
  - All endpoint categories and usage
  - Common use cases and examples
  - Best practices and rate limiting
- **[OpenAPI Specification](https://sathisha.github.io/multi-agent-orchestrator/api/openapi.json)** - Machine-readable OpenAPI 3.1 spec for importing into tools like Postman or Insomnia

### Generating API Docs

```bash
# Export OpenAPI specification
make api-docs

# Serve docs locally for testing
make api-docs-serve
```

The OpenAPI specification is automatically updated via GitHub Actions when backend code changes are pushed to the main branch.

## 📚 Documentation

- [Workflow Usage Guide](docs/workflow_usage.md): Comprehensive guide on creating and using workflows, including API usage.
- [Deployment Guide](DEPLOYMENT.md): Detailed deployment instructions.
- [Docker Images](DOCKER_IMAGES.md): Information about the Docker images and containers used.

## 📄 License & Attribution

### Project License

This project is licensed under the **Apache License, Version 2.0**. See the [LICENSE](LICENSE) file for the full license text.

Dependencies for this project are predominantly under permissive licenses (MIT, Apache 2.0, BSD) that are safe for commercial use and monetization.

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