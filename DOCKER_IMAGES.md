# Docker Images Reference

This document provides a comprehensive list of all Docker images used in the multi-agent orchestrator platform, along with their purposes and configurations.

## Core Infrastructure Services

### 1. PostgreSQL Database
- **Image**: `postgres:15-alpine`
- **Container Name**: `ai-agent-framework-postgres`
- **Purpose**: Primary relational database for storing application data including agents, workflows, models, tools, executions, and user data
- **Port**: 5432
- **Features**:
  - Alpine-based for smaller footprint
  - PostgreSQL 15 with latest features and performance improvements
  - Includes health checks for service readiness
  - Persistent data storage via volumes
  - Used by Keycloak for identity data storage

### 2. Redis Cache
- **Image**: `redis:7-alpine`
- **Container Name**: `ai-agent-framework-redis`
- **Purpose**: In-memory data store for caching, session management, and job queue management
- **Port**: 6379
- **Features**:
  - Alpine-based for smaller footprint
  - Redis 7 with advanced features
  - AOF (Append Only File) persistence enabled
  - Used for caching LLM responses, agent states, and workflow execution states
  - Improves application performance and reduces database load

## Security & API Management

### 3. Keycloak
- **Image**: `quay.io/keycloak/keycloak:22.0`
- **Container Name**: `ai-agent-framework-keycloak`
- **Purpose**: Identity and Access Management (IAM) solution for authentication and authorization
- **Port**: 8080
- **Features**:
  - Single Sign-On (SSO) capabilities
  - User federation and identity brokering
  - OAuth 2.0 and OpenID Connect support
  - Role-Based Access Control (RBAC)
  - Stores identity data in PostgreSQL
  - Provides admin console for user and realm management

### 4. Kong API Gateway
- **Image**: `kong:3.4`
- **Container Name**: `ai-agent-framework-kong`
- **Purpose**: API Gateway for routing, rate limiting, authentication, and request transformation
- **Ports**: 
  - 8000 (Proxy)
  - 8002 (Admin API)
- **Features**:
  - DB-less mode using declarative configuration
  - Request/Response transformation
  - Rate limiting and authentication plugins
  - Load balancing capabilities
  - Centralized API management and monitoring

## Application Services

### 5. Backend API
- **Image**: Custom build from `./backend/Dockerfile`
- **Base**: Python-based (FastAPI framework)
- **Container Name**: `ai-agent-framework-backend`
- **Purpose**: Core application backend providing RESTful APIs for all platform functionality
- **Port**: 8001 (mapped from internal 8000)
- **Features**:
  - FastAPI framework for high-performance async APIs
  - SQLAlchemy ORM for database operations
  - Integration with all LLM providers (OpenAI, Anthropic, Azure OpenAI, Ollama)
  - Agent execution engine
  - Workflow orchestration logic
  - Memory and embedding management
  - Tool registry and MCP server integration
  - Health check endpoints
  - GPU support for local model processing (NVIDIA)

### 6. Frontend Application
- **Image**: Custom build from `./frontend/Dockerfile`
- **Base**: Node.js + React 18 + TypeScript
- **Container Name**: `ai-agent-framework-frontend`
- **Purpose**: Web-based user interface for managing agents, workflows, models, and monitoring
- **Port**: 3000 (mapped to internal 80)
- **Features**:
  - React 18 with TypeScript
  - Material-UI component library
  - VS Code-style interface
  - Real-time execution monitoring
  - Agent and workflow builders
  - Model management and testing interface
  - Served via Nginx in production

## AI/ML Services

### 7. Ollama
- **Image**: `ollama/ollama:latest` (custom build with entrypoint)
- **Build Context**: `./infrastructure/docker/ollama/Dockerfile.ollama`
- **Container Name**: `ai-agent-framework-ollama`
- **Purpose**: Local Large Language Model (LLM) hosting and inference
- **Port**: 11434
- **Features**:
  - Hosts and runs local LLM models (Llama, Mistral, etc.)
  - Provides OpenAI-compatible API
  - GPU acceleration support (NVIDIA)
  - Model caching to avoid re-downloads
  - Configurable for parallel requests and model loading
  - Custom entrypoint for auto-pulling models
  - Memory limits: 8G max, 4G reserved
  - Supports image/vision models (e.g., llama3.2-vision)

## Monitoring & Analytics

### 8. Prometheus
- **Image**: `prom/prometheus:v2.47.0`
- **Container Name**: `ai-agent-framework-prometheus`
- **Purpose**: Metrics collection and monitoring for system health and performance
- **Port**: 9090
- **Features**:
  - Time-series database for metrics
  - Scrapes metrics from backend and other services
  - Alert manager integration capabilities
  - Query language (PromQL) for metric analysis
  - Persistent storage for historical data
  - Web-based query interface

### 9. Apache Superset
- **Image**: `apache/superset:3.0.0`
- **Container Name**: `ai-agent-framework-superset`
- **Purpose**: Business intelligence and data visualization platform
- **Port**: 8088
- **Features**:
  - Interactive dashboards and visualizations
  - SQL Lab for ad-hoc queries
  - Connects to PostgreSQL for data analysis
  - Pre-configured with admin user
  - Visualization of agent performance, execution metrics, and workflow analytics
  - Custom superset configuration support

## Volume Mounts

The platform uses the following persistent volumes for data storage:

- **postgres_data**: PostgreSQL database files
- **redis_data**: Redis persistence files
- **prometheus_data**: Prometheus metrics storage
- **superset_data**: Superset configuration and metadata
- **chroma_data**: ChromaDB vector database for embeddings
- **ollama_data**: Ollama model storage (prevents re-downloading)

## Network Configuration

All services run on a custom bridge network called `ai-agent-network`, enabling:
- Service discovery by container name
- Isolated network communication
- Secure inter-service communication
- Easy service-to-service connectivity

## GPU Support

The following services have NVIDIA GPU support configured:
- **Backend**: For local embedding model processing
- **Ollama**: For LLM inference acceleration

GPU support requires:
- NVIDIA GPU on host machine
- NVIDIA Container Toolkit installed
- Docker with GPU support enabled

## Health Checks

Services with configured health checks:
- **PostgreSQL**: `pg_isready` check every 10s
- **Redis**: `redis-cli ping` every 10s
- **Ollama**: `ollama list` every 10s (30s start period)
- **Backend**: HTTP check on `/health` endpoint every 30s (40s start period)

## Additional Docker Compose Files

The project includes several specialized compose files for different scenarios:
- `docker-compose.dev.yml`: Development environment with hot-reloading
- `docker-compose.prod.yml`: Production deployment configuration
- `docker-compose.test.yml`: Testing environment setup
- `docker-compose.security.yml`: Enhanced security configurations
- `docker-compose.agent-executor.yml`: Specialized agent execution environment
- `docker-compose.override.yml`: Local overrides (not version controlled)

## Resource Requirements

### Minimum System Requirements
- **CPU**: 4 cores recommended
- **RAM**: 16GB minimum (32GB recommended with Ollama)
- **Disk**: 50GB free space (for models and data)
- **GPU**: Optional but recommended for Ollama (NVIDIA with CUDA support)

### Service Memory Allocation
- **Ollama**: 4-8GB reserved
- **PostgreSQL**: ~256MB
- **Redis**: ~128MB
- **Backend**: Varies based on workload
- **Other services**: ~512MB each

## Startup Order

Services start in the following dependency order:
1. PostgreSQL (required by most services)
2. Redis (required by backend and Superset)
3. Keycloak (depends on PostgreSQL)
4. Kong (independent, but gateway to backend)
5. Ollama (independent LLM service)
6. Backend (depends on PostgreSQL, Redis)
7. Frontend (independent, connects to backend)
8. Prometheus (monitors all services)
9. Superset (depends on PostgreSQL and Redis)

## Environment Variables

Key environment variables used across services:
- **DATABASE_URL**: PostgreSQL connection string
- **REDIS_URL**: Redis connection string
- **OLLAMA_BASE_URL**: Ollama service endpoint
- **MEMORY_EMBEDDING_PROVIDER**: Embedding provider (ollama/openai/local)
- **OPENAI_API_KEY**: OpenAI API key (if using OpenAI)
- **ENVIRONMENT**: Development/production mode

---

**Last Updated**: 2026-01-06
**Docker Compose Version**: 3.8+
**Platform**: Multi-Agent Orchestrator
