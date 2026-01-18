# Antigravity IDE & Gemini CLI Operational Guidelines

These guidelines are derived from the project's steering documents and are intended to ensure consistent, reliable, and secure development practices.

## Core Principles

### 1. Docker-First Development
- **Mandate**: All development, testing, and building MUST be performed within Docker containers.
- **Rationale**: Ensures environment consistency, isolates dependencies, and simplifies setup.
- **Action**: Use `docker-compose` commands (or their `make` wrappers) exclusively for building and testing. NEVER run `pytest` or build scripts directly on the host.

### 2. Security First
- **Mandate**: Adhere to a "Defense in Depth" security strategy.
- **Rationale**: Protects against various threats including prompt injection, credential theft, and data breaches.
- **Action**:
    - Validate and sanitize all user inputs rigorously.
    - Use secure secret management (e.g., Vault, environment variables only for dev).
    - Implement RBAC and tenant isolation for all operations.
    - Ensure audit trails are comprehensive and tamper-evident.
    - Prioritize encryption for data at rest and in transit.

### 3. Reliability & Resilience
- **Mandate**: Build fault-tolerant systems using established patterns.
- **Rationale**: Ensures high availability and graceful handling of failures.
- **Action**:
    - Implement circuit breakers for external service calls.
    - Use retry mechanisms with exponential backoff for transient errors.
    - Design for graceful degradation when dependencies are unavailable.
    - Ensure comprehensive health checks are in place for all services.

### 4. Performance & Scalability
- **Mandate**: Optimize for performance and scalability from the outset.
- **Rationale**: Ensures the platform can handle increased load and provides a responsive user experience.
- **Action**:
    - Utilize asynchronous programming for I/O operations.
    - Implement multi-layer caching (in-memory, Redis).
    - Optimize database queries and use connection pooling.
    - Configure resource limits and auto-scaling for containerized services.

### 5. Multi-Tenancy
- **Mandate**: Adhere to strict tenant data isolation and context management.
- **Rationale**: Ensures data privacy, security, and compliance for all tenants.
- **Action**:
    - All data models and queries MUST include tenant_id filters.
    - Tenant context must be consistently propagated through service calls.
    - RBAC and resource quotas must be tenant-scoped.

### 6. Code Quality & Consistency
- **Mandate**: Follow project conventions for code style, structure, and testing.
- **Rationale**: Enhances maintainability, readability, and collaboration.
- **Action**:
    - Adhere to specified naming conventions (snake_case for Python, PascalCase for React).
    - Write unit tests for individual components and property tests for system-wide correctness.
    - Use structured logging with correlation IDs.
    - Ensure all code changes are reviewed and tested.

## Specific Instructions for Gemini CLI & Antigravity IDE

- **File Access**: Always use provided tools (`read_file`, `list_directory`, etc.) to access project files. Do not assume file contents.
- **Tool Usage**: Prefer specialized tools (`search_file_content`, `glob`) over generic shell commands where applicable.
- **Code Conventions**: Mimic existing project style (formatting, naming, architectural patterns).
- **Safety**: Explain critical commands before execution. Do not introduce code that exposes secrets.
- **Iterative Development**: Plan changes, implement, test, and verify. Add tests for new features.
- **No Silent Tool Calls**: Provide a brief explanation before executing tools.
- **User Confirmation**: Respect user confirmations for tool calls.
