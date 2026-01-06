# Third-Party Dependencies

This document tracks all third-party libraries, frameworks, and Docker images used in the AI Agent Framework project.

**Last Updated:** January 6, 2026

## Recent Changes

### January 6, 2026 - Dependency Synchronization
- **Backend**: Verified against `backend/requirements.txt`
- **Frontend**: Verified against `frontend/package.json`
- **Updates**: Added ReactFlow, Recharts, Allotment, Vitest. Removed PyZeebe and React Split Pane.

## Docker Images

| Name | Version | Location | Purpose | EOL Date | License | Notes |
|------|---------|----------|---------|----------|---------|-------|
| node | 18-alpine | frontend/Dockerfile, frontend/Dockerfile.dev | Node.js runtime for frontend build and development | April 2025 (Node 18 LTS) | MIT | Alpine-based for security and smaller size |
| nginx | alpine (latest) | frontend/Dockerfile, docker-compose.security.yml | Web server for frontend static files and reverse proxy | Active (rolling) | BSD-2-Clause | Alpine-based for security |
| python | 3.11-slim | backend/Dockerfile | Python runtime for backend services | October 2027 (Python 3.11) | PSF-2.0 | Slim variant for reduced attack surface |
| postgres | 15-alpine | docker-compose.yml, docker-compose.dev.yml, docker-compose.security.yml | Primary database | November 2027 | PostgreSQL License | LTS version |
| redis | 7-alpine | docker-compose.yml, docker-compose.dev.yml, docker-compose.security.yml | Caching and session storage | February 2026 | BSD-3-Clause | Alpine-based for security |
| quay.io/keycloak/keycloak | 22.0 | docker-compose.yml | Identity and access management | Active | Apache-2.0 | Official Keycloak image |
| kong | 3.4 | docker-compose.yml | API Gateway | Active | Apache-2.0 | Community Edition |
| prom/prometheus | v2.47.0, latest | docker-compose.yml, docker-compose.security.yml | Metrics collection and monitoring | Active | Apache-2.0 | Time-series database |
| grafana/grafana | latest | docker-compose.security.yml | Monitoring dashboards (optional) | Active | AGPL-3.0 | Note: AGPL license |
| ollama/ollama | latest | docker-compose.yml | Local LLM model serving | Active | MIT | For local AI model inference |
| camunda/zeebe | 8.3.0 | docker-compose.yml | BPMN workflow engine | Active | Apache-2.0 | Community Edition |
| camunda/operate | 8.3.0 | docker-compose.yml | Workflow monitoring UI | Active | Apache-2.0 | Community Edition |
| docker.elastic.co/elasticsearch/elasticsearch | 8.9.0 | docker-compose.yml | Search and analytics for Camunda | Active | Elastic License 2.0 | For workflow data storage |
| apache/superset | 3.0.0 | docker-compose.yml | Data visualization and dashboards | Active | Apache-2.0 | Business intelligence platform |

## Python Dependencies (Backend)

| Name | Version | Location | Purpose | EOL Date | License | Notes |
|------|---------|----------|---------|----------|---------|-------|
| fastapi | 0.109.1 | backend/requirements.txt | Web framework for APIs | Active | MIT | High-performance async framework |
| uvicorn | 0.27.0 | backend/requirements.txt | ASGI server | Active | BSD-3-Clause | With standard extras |
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
| argon2-cffi | 23.1.0 | backend/requirements.txt | Password hashing | Active | MIT | Secure password hashing |
| python-keycloak | 3.7.0 | backend/requirements.txt | Keycloak integration | Active | MIT | Official Python client |
| casbin | 1.36.2 | backend/requirements.txt | Authorization library | Active | Apache-2.0 | RBAC/ABAC enforcement |
| casbin-sqlalchemy-adapter | 1.4.0 | backend/requirements.txt | Casbin SQLAlchemy adapter | Active | Apache-2.0 | Database adapter for Casbin |
| redis | 5.0.1 | backend/requirements.txt | Redis client | Active | MIT | Synchronous Redis client |
| aioredis | 2.0.1 | backend/requirements.txt | Async Redis client | Active | MIT | Async Redis operations |
| httpx | 0.26.0 | backend/requirements.txt | HTTP client | Active | BSD-3-Clause | Async HTTP requests |
| aiohttp | 3.9.1 | backend/requirements.txt | HTTP client/server | Active | Apache-2.0 | Alternative HTTP client |
| lxml | 4.9.3 | backend/requirements.txt | XML/HTML processing | Active | BSD-3-Clause | XML parsing and processing |
| structlog | 23.2.0 | backend/requirements.txt | Structured logging | Active | MIT | Enhanced logging |
| prometheus-client | 0.19.0 | backend/requirements.txt | Prometheus metrics | Active | Apache-2.0 | Metrics collection |
| python-dotenv | 1.0.0 | backend/requirements.txt | Environment variables | Active | BSD-3-Clause | .env file support |
| python-json-logger | 2.0.7 | backend/requirements.txt | JSON logging formatter | Active | BSD-2-Clause | Structured JSON logging |
| psutil | 5.9.6 | backend/requirements.txt | System and process utilities | Active | BSD-3-Clause | System monitoring and resource usage |

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
| openai | 1.40.0 | backend/requirements.txt | OpenAI API client | Active | MIT | Official OpenAI Python client for GPT models |
| anthropic | 0.28.0 | backend/requirements.txt | Anthropic API client | Active | MIT | Official Anthropic Python client for Claude models |
| tiktoken | 0.5.2 | backend/requirements.txt | Token counting for OpenAI models | Active | MIT | OpenAI tokenizer library for accurate cost estimation |
| tenacity | 8.2.3 | backend/requirements.txt | Retry library with backoff | Active | Apache-2.0 | Resilient API calls and error handling for LLM providers |
| chromadb | 0.4.18 | backend/requirements.txt | Vector database for embeddings | Active | Apache-2.0 | Local vector database for semantic memory and RAG |
| sentence-transformers | 2.2.2 | backend/requirements.txt | Text embeddings generation | Active | Apache-2.0 | Pre-trained models for semantic similarity and search |
| numpy | 1.24.4 | backend/requirements.txt | Numerical computing for ML | Active | BSD-3-Clause | Core dependency for embeddings and vector operations |
| huggingface-hub | 0.19.4 | backend/requirements.txt | HuggingFace model hub client | Active | Apache-2.0 | Download and manage pre-trained models |

## Frontend Dependencies (Node.js/React)

| Name | Version | Location | Purpose | EOL Date | License | Notes |
|------|---------|----------|---------|----------|---------|-------|
| react | ^18.2.0 | frontend/package.json | Core React library | Active (LTS) | MIT | Main UI framework, LTS version |
| react-dom | ^18.2.0 | frontend/package.json | React DOM renderer | Active (LTS) | MIT | DOM rendering for React |
| typescript | ^5.3.3 | frontend/package.json | TypeScript compiler | Active | Apache-2.0 | Static type checking |
| @types/react | ^18.2.45 | frontend/package.json | React TypeScript definitions | Active | MIT | Type definitions for React |
| @types/react-dom | ^18.2.18 | frontend/package.json | React DOM TypeScript definitions | Active | MIT | Type definitions for React DOM |
| @types/node | ^20.10.0 | frontend/package.json | Node.js TypeScript definitions | Active | MIT | Type definitions for Node.js |
| @monaco-editor/react | ^4.6.0 | frontend/package.json | Monaco Editor React wrapper | Active | MIT | VS Code-style code editor component |
| react-router-dom | ^6.20.1 | frontend/package.json | React routing library | Active | MIT | Client-side routing for SPA |
| allotment | ^1.20.2 | frontend/package.json | Resizable split pane component | Active | MIT | VS Code-style resizable panels |
| @emotion/react | ^11.11.1 | frontend/package.json | CSS-in-JS library | Active | MIT | Emotion CSS-in-JS for styling |
| @emotion/styled | ^11.11.0 | frontend/package.json | Styled components for Emotion | Active | MIT | Styled components API for Emotion |
| @mui/material | ^5.15.0 | frontend/package.json | Material-UI component library | Active | MIT | Google Material Design components |
| @mui/icons-material | ^5.15.0 | frontend/package.json | Material-UI icons | Active | MIT | Material Design icon set |
| axios | ^1.6.2 | frontend/package.json | HTTP client library | Active | MIT | Promise-based HTTP client |
| react-query | ^3.39.3 | frontend/package.json | Data fetching and caching | Active | MIT | Server state management (now TanStack Query) |
| web-vitals | ^3.5.0 | frontend/package.json | Web performance metrics | Active | Apache-2.0 | Core Web Vitals measurement |
| reactflow | ^11.10.4 | frontend/package.json | Visual workflow builder | Active | MIT | For workflow node graph editing |
| recharts | ^2.10.3 | frontend/package.json | Charting library | Active | MIT | For data visualization |

## Frontend Development Dependencies

| Name | Version | Location | Purpose | EOL Date | License | Notes |
|------|---------|----------|---------|----------|---------|-------|
| vite | ^5.0.8 | frontend/package.json | Build tool and dev server | Active | MIT | Fast build tool and development server |
| vitest | ^1.0.0 | frontend/package.json | Test framework | Active | MIT | Unit testing powered by Vite |
| @vitest/ui | ^1.0.0 | frontend/package.json | Test UI | Active | MIT | UI for Vitest |
| @vitejs/plugin-react | ^4.2.0 | frontend/package.json | Vite React plugin | Active | MIT | React support for Vite |
| eslint | ^8.55.0 | frontend/package.json | JavaScript/TypeScript linter | Active | MIT | Code quality and style enforcement |
| @typescript-eslint/eslint-plugin | ^6.14.0 | frontend/package.json | TypeScript ESLint plugin | Active | MIT | TypeScript-specific linting rules |
| @typescript-eslint/parser | ^6.14.0 | frontend/package.json | TypeScript ESLint parser | Active | MIT | TypeScript parser for ESLint |
| eslint-plugin-react | ^7.33.2 | frontend/package.json | React ESLint plugin | Active | MIT | React-specific linting rules |
| eslint-plugin-react-hooks | ^4.6.0 | frontend/package.json | React Hooks ESLint plugin | Active | MIT | React Hooks linting rules |
| @testing-library/react | ^14.1.2 | frontend/package.json | React testing utilities | Active | MIT | Testing helpers for React |
| @testing-library/jest-dom | ^6.1.5 | frontend/package.json | DOM matchers | Active | MIT | Custom matchers for Jest/Vitest |
| jsdom | ^23.0.1 | frontend/package.json | DOM implementation | Active | MIT | JSDOM for testing in Node |
| vite-tsconfig-paths | ^4.3.1 | frontend/package.json | TypeScript path resolver | Active | MIT | Resolve TS paths in Vite |

## Infrastructure Configuration

| Name | Version | Location | Purpose | EOL Date | License | Notes |
|------|---------|----------|---------|----------|---------|-------|
| Docker Compose | 3.8 | docker-compose.yml, docker-compose.dev.yml, docker-compose.security.yml | Container orchestration | Active | Apache-2.0 | Compose file format version |
| Docker Compose | (no version) | docker-compose.frontend.yml | Frontend container orchestration | Active | Apache-2.0 | Uses latest compose format without version |

## Security Considerations

### High-Risk Dependencies
- **Grafana**: Uses AGPL-3.0 license which may have commercial restrictions
- **psycopg2-binary**: LGPL-3.0 license requires compliance considerations
- **React 18.2.0**: Monitor for React2Shell vulnerability (CVE-2025-55182) - ensure React Server Components are not used or properly secured
- **Elasticsearch**: Uses Elastic License 2.0 which has restrictions on cloud service providers

### Frontend Security
- **Monaco Editor**: Code editor component - ensure proper input sanitization for user-provided code
- **React Query**: Data fetching library - ensure proper authentication and authorization for API calls
- **Axios**: HTTP client - configure proper timeout, CSRF protection, and request/response interceptors
- **Material-UI**: UI component library - keep updated for security patches, validate user inputs in forms
- **Node.js 18**: Monitor for security updates, EOL April 2025 - plan migration to Node.js 20 LTS

### LLM Provider Security
- **OpenAI, Anthropic**: API keys and credentials must be securely managed
- **tiktoken**: Used for token counting - ensure input sanitization
- **tenacity**: Retry mechanisms should include rate limiting to prevent abuse
- **chromadb**: Vector database should be secured with proper access controls
- **sentence-transformers**: Model files should be verified for integrity
- **numpy**: Core numerical library - keep updated for security patches
- **huggingface-hub**: Model downloads should be verified and scanned

### Container Security
- **Node.js Alpine**: Minimal attack surface but monitor for Alpine Linux security updates
- **Python Slim**: Reduced attack surface compared to full Python image
- **Nginx Alpine**: Secure web server configuration required
- **All Alpine Images**: Monitor Alpine Linux security advisories

### EOL Monitoring
- **Node.js 18**: EOL April 2025 - Plan migration to Node.js 20 LTS
- **PostgreSQL 15**: EOL November 2027 - Plan migration to newer version
- **Redis 7**: EOL February 2026 - Monitor for updates
- **Python 3.11**: EOL October 2027 - Monitor Python release cycle for updates
- **React 18**: LTS version, monitor for security updates and React 19 migration path
- **TypeScript 5.3**: Monitor for security updates and new releases
- **OpenAI SDK**: Monitor for security updates and API changes
- **Anthropic SDK**: Monitor for security updates and API changes

### License Compliance
- Most dependencies use permissive licenses (MIT, Apache-2.0, BSD)
- AGPL-3.0 (Grafana) requires source code availability if distributed
- LGPL-3.0 (psycopg2-binary) allows dynamic linking without source requirements
- Elastic License 2.0 (Elasticsearch) has restrictions on cloud service providers
- All frontend dependencies use MIT or Apache-2.0 licenses (permissive)
- All Docker base images use permissive licenses

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
7. LLM provider integrations support multiple providers (OpenAI, Anthropic) for flexibility
8. Token counting with tiktoken ensures accurate cost estimation for OpenAI models
9. Tenacity library provides resilient retry mechanisms with exponential backoff for API calls
10. All LLM provider credentials should be stored in HashiCorp Vault or similar secret management system
11. ChromaDB provides local vector database capabilities for semantic memory and RAG applications
12. Sentence Transformers enables local embeddings generation without external API dependencies
13. NumPy provides essential numerical computing foundation for ML and vector operations
14. HuggingFace Hub enables downloading and managing pre-trained models
15. Frontend uses React 18 LTS for stability and long-term support
16. Monaco Editor provides VS Code-style editing experience in the browser
17. Material-UI (MUI) provides Google Material Design components for consistent UI
18. Vite provides fast development server and optimized production builds
19. TypeScript ensures type safety across the entire frontend codebase
20. React Query (TanStack Query) provides robust server state management and caching
21. Axios provides reliable HTTP client with interceptors for authentication and error handling
22. ESLint with TypeScript plugins ensures code quality and consistency
23. React Router DOM enables client-side routing for single-page application experience
24. Emotion provides CSS-in-JS styling solution with excellent performance
25. Allotment enables VS Code-style resizable panel layouts (superseding react-split-pane)
26. Node.js 18 Alpine provides secure, minimal runtime environment for frontend builds
27. Nginx Alpine serves static frontend assets with minimal security footprint
28. Python 3.11 Slim provides secure, minimal runtime for backend services
29. Docker Compose orchestrates multi-container development and production environments
30. Ollama enables local LLM inference without external API dependencies
31. Camunda Platform 8 provides enterprise-grade BPMN workflow orchestration
32. Elasticsearch powers Camunda's workflow data storage and search capabilities
33. Apache Superset provides self-hosted business intelligence and data visualization
34. Vitest provides a fast, modern testing framework for the frontend, replacing Jest