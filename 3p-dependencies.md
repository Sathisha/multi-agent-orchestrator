# Third-Party Dependencies

This document tracks all third-party libraries, frameworks, and Docker images used in the AI Agent Framework project.

**Last Updated:** December 21, 2025 (Updated with vector database and embeddings dependencies)

## Docker Images

| Name | Version | Location | Purpose | EOL Date | License | Notes |
|------|---------|----------|---------|----------|---------|-------|
| nginx | alpine (latest) | docker-compose.security.yml | Reverse proxy with SSL termination | Active (rolling) | BSD-2-Clause | Alpine-based for security |
| postgres | 15-alpine | docker-compose.yml, docker-compose.dev.yml, docker-compose.security.yml | Primary database | November 2027 | PostgreSQL License | LTS version |
| redis | 7-alpine | docker-compose.yml, docker-compose.dev.yml, docker-compose.security.yml | Caching and session storage | February 2026 | BSD-3-Clause | Alpine-based for security |
| quay.io/keycloak/keycloak | 22.0 | docker-compose.yml | Identity and access management | Active | Apache-2.0 | Official Keycloak image |
| kong | 3.4 | docker-compose.yml | API Gateway | Active | Apache-2.0 | Community Edition |
| prom/prometheus | v2.47.0, latest | docker-compose.yml, docker-compose.security.yml | Metrics collection and monitoring | Active | Apache-2.0 | Time-series database |
| grafana/grafana | latest | docker-compose.security.yml | Monitoring dashboards (optional) | Active | AGPL-3.0 | Note: AGPL license |

## Python Dependencies (Backend)

| Name | Version | Location | Purpose | EOL Date | License | Notes |
|------|---------|----------|---------|----------|---------|-------|
| fastapi | 0.104.1 | backend/requirements.txt | Web framework for APIs | Active | MIT | High-performance async framework |
| uvicorn | 0.24.0 | backend/requirements.txt | ASGI server | Active | BSD-3-Clause | With standard extras |
| python-multipart | 0.0.6 | backend/requirements.txt | Form data parsing | Active | Apache-2.0 | For file uploads |
| sqlalchemy | 2.0.23 | backend/requirements.txt | ORM and database toolkit | Active | MIT | Latest 2.x series |
| alembic | 1.12.1 | backend/requirements.txt | Database migrations | Active | MIT | SQLAlchemy companion |
| psycopg2-binary | 2.9.9 | backend/requirements.txt | PostgreSQL adapter | Active | LGPL-3.0 | Binary distribution |
| asyncpg | 0.29.0 | backend/requirements.txt | Async PostgreSQL driver | Active | Apache-2.0 | High-performance async |
| aiosqlite | 0.19.0 | backend/requirements.txt | Async SQLite driver | Active | MIT | For testing/development |
| pydantic | 2.5.0 | backend/requirements.txt | Data validation | Active | MIT | Latest 2.x series |
| pydantic-settings | 2.1.0 | backend/requirements.txt | Settings management | Active | MIT | Pydantic companion |
| email-validator | 2.1.0 | backend/requirements.txt | Email validation | Active | CC0-1.0 | For Pydantic email fields |
| python-jose | 3.3.0 | backend/requirements.txt | JWT handling | Active | MIT | With cryptography extras |
| passlib | 1.7.4 | backend/requirements.txt | Password hashing | Active | BSD-2-Clause | With bcrypt extras |
| python-keycloak | 3.7.0 | backend/requirements.txt | Keycloak integration | Active | MIT | Official Python client |
| casbin | 1.36.2 | backend/requirements.txt | Authorization library | Active | Apache-2.0 | RBAC/ABAC enforcement |
| casbin-sqlalchemy-adapter | 1.4.0 | backend/requirements.txt | Casbin SQLAlchemy adapter | Active | Apache-2.0 | Database adapter for Casbin |
| redis | 5.0.1 | backend/requirements.txt | Redis client | Active | MIT | Synchronous Redis client |
| aioredis | 2.0.1 | backend/requirements.txt | Async Redis client | Active | MIT | Async Redis operations |
| httpx | 0.25.2 | backend/requirements.txt | HTTP client | Active | BSD-3-Clause | Async HTTP requests |
| aiohttp | 3.9.1 | backend/requirements.txt | HTTP client/server | Active | Apache-2.0 | Alternative HTTP client |
| structlog | 23.2.0 | backend/requirements.txt | Structured logging | Active | MIT | Enhanced logging |
| prometheus-client | 0.19.0 | backend/requirements.txt | Prometheus metrics | Active | Apache-2.0 | Metrics collection |
| python-dotenv | 1.0.0 | backend/requirements.txt | Environment variables | Active | BSD-3-Clause | .env file support |

## Development Dependencies (Backend)

| Name | Version | Location | Purpose | EOL Date | License | Notes |
|------|---------|----------|---------|----------|---------|-------|
| pytest | 7.4.3 | backend/requirements.txt | Testing framework | Active | MIT | Primary test runner |
| pytest-asyncio | 0.21.1 | backend/requirements.txt | Async testing support | Active | Apache-2.0 | For async tests |
| pytest-cov | 4.1.0 | backend/requirements.txt | Coverage reporting | Active | MIT | Test coverage |
| black | 23.11.0 | backend/requirements.txt | Code formatter | Active | MIT | Python code formatting |
| isort | 5.12.0 | backend/requirements.txt | Import sorting | Active | MIT | Import organization |
| flake8 | 6.1.0 | backend/requirements.txt | Linting | Active | MIT | Code quality checks |
| mypy | 1.7.1 | backend/requirements.txt | Type checking | Active | MIT | Static type analysis |
| hypothesis | 6.92.1 | backend/requirements.txt | Property-based testing | Active | MPL-2.0 | Advanced testing framework |

## LLM and AI Dependencies (Backend)

| Name | Version | Location | Purpose | EOL Date | License | Notes |
|------|---------|----------|---------|----------|---------|-------|
| openai | 1.3.7 | backend/requirements.txt | OpenAI API client | Active | MIT | Official OpenAI Python client for GPT models |
| anthropic | 0.7.8 | backend/requirements.txt | Anthropic API client | Active | MIT | Official Anthropic Python client for Claude models |
| ollama | 0.1.7 | backend/requirements.txt | Ollama API client | Active | MIT | Local LLM server integration for self-hosted models |
| tiktoken | 0.5.2 | backend/requirements.txt | Token counting for OpenAI models | Active | MIT | OpenAI tokenizer library for accurate cost estimation |
| tenacity | 8.2.3 | backend/requirements.txt | Retry library with backoff | Active | Apache-2.0 | Resilient API calls and error handling for LLM providers |
| chromadb | 0.4.18 | backend/requirements.txt | Vector database for embeddings | Active | Apache-2.0 | Local vector database for semantic memory and RAG |
| sentence-transformers | 2.2.2 | backend/requirements.txt | Text embeddings generation | Active | Apache-2.0 | Pre-trained models for semantic similarity and search |
| numpy | 1.24.4 | backend/requirements.txt | Numerical computing for ML | Active | BSD-3-Clause | Core dependency for embeddings and vector operations |

## Infrastructure Configuration

| Name | Version | Location | Purpose | EOL Date | License | Notes |
|------|---------|----------|---------|----------|---------|-------|
| Docker Compose | 3.8 | All docker-compose files | Container orchestration | Active | Apache-2.0 | Compose file format version |

## Security Considerations

### High-Risk Dependencies
- **Grafana**: Uses AGPL-3.0 license which may have commercial restrictions
- **psycopg2-binary**: LGPL-3.0 license requires compliance considerations

### LLM Provider Security
- **OpenAI, Anthropic, Ollama**: API keys and credentials must be securely managed
- **tiktoken**: Used for token counting - ensure input sanitization
- **tenacity**: Retry mechanisms should include rate limiting to prevent abuse
- **chromadb**: Vector database should be secured with proper access controls
- **sentence-transformers**: Model files should be verified for integrity
- **numpy**: Core numerical library - keep updated for security patches

### EOL Monitoring
- **PostgreSQL 15**: EOL November 2027 - Plan migration to newer version
- **Redis 7**: EOL February 2026 - Monitor for updates
- **Python 3.11**: Monitor Python release cycle for updates
- **OpenAI SDK**: Monitor for security updates and API changes
- **Anthropic SDK**: Monitor for security updates and API changes

### License Compliance
- Most dependencies use permissive licenses (MIT, Apache-2.0, BSD)
- AGPL-3.0 (Grafana) requires source code availability if distributed
- LGPL-3.0 (psycopg2-binary) allows dynamic linking without source requirements

## Maintenance Schedule

### Quarterly Reviews
- Check for security updates
- Review EOL dates
- Update to latest stable versions

### Annual Reviews
- Major version upgrades
- License compliance audit
- Dependency cleanup and optimization

## Notes

1. All Docker images use Alpine Linux variants where available for reduced attack surface
2. Python dependencies are pinned to specific versions for reproducible builds
3. Development dependencies are separated from production requirements
4. Property-based testing with Hypothesis provides enhanced test coverage
5. Multi-layer caching strategy uses both Redis and in-memory caching
6. Authentication stack includes both JWT and Keycloak for flexibility
7. LLM provider integrations support multiple providers (OpenAI, Anthropic, Ollama) for flexibility
8. Token counting with tiktoken ensures accurate cost estimation for OpenAI models
9. Tenacity library provides resilient retry mechanisms with exponential backoff for API calls
10. All LLM provider credentials should be stored in HashiCorp Vault or similar secret management system
11. ChromaDB provides local vector database capabilities for semantic memory and RAG applications
12. Sentence Transformers enables local embeddings generation without external API dependencies
13. NumPy provides essential numerical computing foundation for ML and vector operations