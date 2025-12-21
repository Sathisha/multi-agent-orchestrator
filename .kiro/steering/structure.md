# Project Organization & Structure

## Repository Structure

```
ai-agent-framework/
├── .kiro/                          # Kiro configuration and specs
│   ├── specs/                      # Feature specifications
│   └── steering/                   # AI assistant guidance rules
├── backend/                        # Python microservices
│   ├── services/                   # Individual microservices
│   │   ├── agent_manager/          # Agent CRUD and lifecycle
│   │   ├── workflow_orchestrator/  # BPMN workflow execution
│   │   ├── memory_manager/         # Semantic memory system
│   │   ├── guardrails_engine/      # Security and content filtering
│   │   ├── auth_service/           # Authentication and RBAC
│   │   ├── tool_registry/          # Custom tools and MCP gateway
│   │   └── audit_service/          # Compliance and logging
│   ├── shared/                     # Shared libraries and utilities
│   │   ├── models/                 # SQLAlchemy and Pydantic models
│   │   ├── auth/                   # Authentication utilities
│   │   ├── database/               # Database connection and utilities
│   │   └── logging/                # Structured logging setup
│   └── tests/                      # Backend test suite
│       ├── unit/                   # Unit tests per service
│       ├── integration/            # Cross-service integration tests
│       └── properties/             # Property-based tests
├── frontend/                       # React TypeScript application
│   ├── src/
│   │   ├── components/             # Reusable UI components
│   │   ├── workspaces/             # VS Code-style workspace views
│   │   │   ├── AgentWorkspace/     # Agent creation and management
│   │   │   ├── WorkflowWorkspace/  # BPMN workflow designer
│   │   │   ├── ToolsWorkspace/     # Tool development interface
│   │   │   └── MonitoringWorkspace/ # System monitoring and logs
│   │   ├── services/               # API client services
│   │   ├── hooks/                  # React hooks for state management
│   │   └── utils/                  # Frontend utilities
│   └── tests/                      # Frontend test suite
├── infrastructure/                 # Deployment and infrastructure
│   ├── docker/                     # Docker configurations
│   │   ├── docker-compose.yml      # Development environment
│   │   ├── docker-compose.prod.yml # Production environment
│   │   └── Dockerfile.*            # Service-specific Dockerfiles
│   ├── kubernetes/                 # Kubernetes manifests and Helm charts
│   ├── terraform/                  # Infrastructure as Code
│   └── scripts/                    # Deployment and utility scripts
├── docs/                           # Documentation
│   ├── api/                        # API documentation
│   ├── deployment/                 # Deployment guides
│   └── user/                       # User guides and tutorials
└── config/                         # Configuration files
    ├── development/                # Development environment configs
    ├── production/                 # Production environment configs
    └── templates/                  # Configuration templates
```

## Architecture Patterns

### Microservices Organization
- Each service in `backend/services/` is independently deployable
- Services communicate via REST APIs (FastAPI)
- Shared code lives in `backend/shared/`
- Each service has its own database schema but shares the PostgreSQL instance

### Frontend Architecture
- VS Code-inspired layout with workspaces for different functions
- Component-based architecture with reusable UI elements
- State management through React Query for server state
- Monaco Editor integration for code editing experiences

### Configuration Management
- Environment-specific configs in `config/` directory
- Docker Compose for local development orchestration
- Kubernetes manifests for production deployments
- Infrastructure as Code with Terraform for cloud deployments

## Naming Conventions

### Python Code
- **Services**: `snake_case` for modules and functions
- **Classes**: `PascalCase` for models and services
- **Constants**: `UPPER_SNAKE_CASE`
- **Files**: `snake_case.py`

### Frontend Code
- **Components**: `PascalCase` for React components
- **Files**: `PascalCase.tsx` for components, `camelCase.ts` for utilities
- **Hooks**: `use` prefix (e.g., `useAgentManager`)
- **Services**: `camelCase` with descriptive names

### Database
- **Tables**: `snake_case` (e.g., `agent_configurations`)
- **Columns**: `snake_case`
- **Indexes**: `idx_table_column`
- **Foreign Keys**: `fk_table_referenced_table`

### API Endpoints
- **REST**: `/api/v1/resource-name` (kebab-case)
- **Versioning**: Include version in URL path
- **Actions**: Use HTTP verbs appropriately (GET, POST, PUT, DELETE)

## Development Workflow

### Feature Development
1. Create feature spec in `.kiro/specs/`
2. Implement backend services with property tests
3. Create frontend components and integration
4. Write integration tests
5. Update documentation

### Testing Strategy
- **Unit Tests**: Test individual functions and classes
- **Property Tests**: Validate system-wide correctness properties
- **Integration Tests**: Test service interactions
- **End-to-End Tests**: Test complete user workflows

### Code Organization Principles
- **Single Responsibility**: Each service has one clear purpose
- **Dependency Injection**: Use FastAPI's dependency system
- **Configuration**: Environment-based configuration management
- **Error Handling**: Consistent error responses across services
- **Logging**: Structured logging with correlation IDs