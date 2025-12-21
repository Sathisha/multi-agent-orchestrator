# Technology Stack & Build System

## Core Technology Stack

### Backend Services
- **Language**: Python 3.11+ with FastAPI for all microservices
- **Database**: PostgreSQL 15+ with SQLAlchemy ORM and Alembic migrations
- **Cache**: Redis 7+ for session management and caching
- **Vector DB**: Chroma (development) → Pinecone/Weaviate (production)
- **Authentication**: Keycloak for identity management, JWT with python-jose
- **Security**: Casbin for RBAC, custom guardrails engine

### Frontend
- **Framework**: React 18+ with TypeScript
- **UI Library**: Material-UI or Ant Design
- **Editor**: Monaco Editor (VS Code experience)
- **Workflow Design**: React Flow for BPMN visual editor
- **State Management**: React Query for API state

### Infrastructure
- **Containerization**: Docker with Docker Compose
- **API Gateway**: Kong Gateway (Community Edition)
- **Process Engine**: Camunda Platform 8 (Community Edition)
- **Monitoring**: Prometheus + Apache Superset (not Grafana due to AGPL)
- **Logging**: Structured logging with Python logging framework

### External Integrations
- **LLM Providers**: Ollama (local), OpenAI, Anthropic, Azure OpenAI
- **Embeddings**: Sentence Transformers for local embeddings
- **MCP Protocol**: Custom Python implementation for tool integration

## Common Commands

### Development Setup
```bash
# Initial setup
docker-compose up -d postgres redis keycloak
pip install -r requirements.txt
alembic upgrade head

# Start development services
docker-compose up -d
python -m uvicorn main:app --reload --port 8000

# Frontend development
cd frontend
npm install
npm run dev
```

### Testing
```bash
# Run all tests
pytest tests/ -v

# Property-based tests
pytest tests/properties/ -v

# Integration tests
pytest tests/integration/ -v

# Frontend tests
cd frontend && npm test
```

### Database Operations
```bash
# Create migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

### Deployment
```bash
# Build production images
docker-compose -f docker-compose.prod.yml build

# Deploy with Docker Compose
docker-compose -f docker-compose.prod.yml up -d

# Generate self-hosting package
python scripts/generate_deployment_package.py
```

## License Compliance

All technologies use permissive licenses (MIT, Apache 2.0, BSD) safe for commercial use. Avoid AGPL-licensed software like Grafana in customer-facing deployments.