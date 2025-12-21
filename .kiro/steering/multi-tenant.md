# Multi-Tenant Architecture Guidelines

## Core Multi-Tenant Principles

### Data Isolation Strategy

**Row-Level Security Implementation:**
```python
# All tenant-scoped models must inherit from TenantEntity
class TenantEntity(BaseEntity):
    tenant_id: Mapped[str] = mapped_column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    
    @declared_attr
    def tenant(cls) -> Mapped["Tenant"]:
        return relationship("Tenant", back_populates="entities")

# Automatic tenant filtering in queries
class TenantAwareQuery:
    def __init__(self, session: AsyncSession, tenant_context: TenantContext):
        self.session = session
        self.tenant_context = tenant_context
    
    def filter_by_tenant(self, query: Select) -> Select:
        """Automatically add tenant_id filter to all queries"""
        if hasattr(query.column_descriptions[0]['type'], 'tenant_id'):
            return query.where(query.column_descriptions[0]['type'].tenant_id == self.tenant_context.tenant_id)
        return query
```

**Database Schema Patterns:**
- **System Tables**: No tenant_id (users, system_roles, global_configs)
- **Tenant Tables**: Always include tenant_id with NOT NULL constraint
- **Shared Tables**: Optional tenant_id for tenant-specific overrides
- **Audit Tables**: Always include tenant_id for proper audit scoping

### Tenant Context Management

**Middleware Implementation:**
```python
class TenantContextMiddleware:
    async def __call__(self, request: Request, call_next):
        # Extract tenant context from multiple sources
        tenant_context = await self.extract_tenant_context(request)
        
        # Validate tenant access
        if not await self.validate_tenant_access(request.user, tenant_context):
            raise HTTPException(status_code=403, detail="Tenant access denied")
        
        # Inject tenant context into request state
        request.state.tenant_context = tenant_context
        
        # Process request with tenant context
        response = await call_next(request)
        
        # Add tenant headers to response
        response.headers["X-Tenant-ID"] = tenant_context.tenant_id
        return response
    
    async def extract_tenant_context(self, request: Request) -> TenantContext:
        """Extract tenant context from subdomain, headers, or JWT"""
        # Priority order: JWT claims > X-Tenant-ID header > subdomain
        
        # 1. Check JWT claims
        if hasattr(request.state, 'user') and request.state.user:
            jwt_tenant = request.state.user.get('tenant_id')
            if jwt_tenant:
                return await self.get_tenant_context(jwt_tenant)
        
        # 2. Check X-Tenant-ID header
        tenant_header = request.headers.get('X-Tenant-ID')
        if tenant_header:
            return await self.get_tenant_context(tenant_header)
        
        # 3. Check subdomain
        host = request.headers.get('host', '')
        if '.' in host:
            subdomain = host.split('.')[0]
            return await self.get_tenant_by_subdomain(subdomain)
        
        raise HTTPException(status_code=400, detail="Tenant context not found")
```

### Resource Quota Management

**Quota Enforcement:**
```python
class ResourceQuotaService:
    def __init__(self, tenant_service: TenantService):
        self.tenant_service = tenant_service
        self.usage_cache = TTLCache(maxsize=1000, ttl=300)  # 5-minute cache
    
    async def check_quota(self, tenant_id: str, resource_type: str, requested_amount: int = 1) -> bool:
        """Check if tenant can use additional resources"""
        tenant = await self.tenant_service.get_tenant(tenant_id)
        current_usage = await self.get_current_usage(tenant_id, resource_type)
        
        quota_limit = getattr(tenant.resource_limits, f"max_{resource_type}")
        return current_usage + requested_amount <= quota_limit
    
    async def enforce_quota(self, tenant_id: str, resource_type: str, requested_amount: int = 1):
        """Enforce quota limits with detailed error messages"""
        if not await self.check_quota(tenant_id, resource_type, requested_amount):
            current_usage = await self.get_current_usage(tenant_id, resource_type)
            tenant = await self.tenant_service.get_tenant(tenant_id)
            quota_limit = getattr(tenant.resource_limits, f"max_{resource_type}")
            
            raise QuotaExceededException(
                resource_type=resource_type,
                current_usage=current_usage,
                quota_limit=quota_limit,
                requested_amount=requested_amount,
                tenant_id=tenant_id
            )
    
    async def track_usage(self, tenant_id: str, resource_type: str, amount: int = 1):
        """Track resource usage for billing and analytics"""
        usage_record = ResourceUsage(
            tenant_id=tenant_id,
            resource_type=resource_type,
            amount=amount,
            timestamp=datetime.utcnow()
        )
        await self.usage_repository.create(usage_record)
        
        # Invalidate cache
        cache_key = f"{tenant_id}:{resource_type}"
        if cache_key in self.usage_cache:
            del self.usage_cache[cache_key]
```

## Security Considerations

### Tenant Isolation Validation

**Security Testing Requirements:**
```python
# Property-based test for tenant isolation
@given(tenant_data=tenant_strategy(), other_tenant_data=tenant_strategy())
def test_tenant_data_isolation(tenant_data, other_tenant_data):
    """Property: Tenant data must be completely isolated"""
    assume(tenant_data.tenant_id != other_tenant_data.tenant_id)
    
    # Create data for both tenants
    with tenant_context(tenant_data.tenant_id):
        agent1 = create_agent(tenant_data.agent_config)
    
    with tenant_context(other_tenant_data.tenant_id):
        agent2 = create_agent(other_tenant_data.agent_config)
        
        # Verify tenant 2 cannot see tenant 1's data
        agents = list_agents()
        assert agent1.id not in [a.id for a in agents]
        assert all(a.tenant_id == other_tenant_data.tenant_id for a in agents)
```

**Audit Trail Requirements:**
- All tenant operations must be logged with tenant_id
- Cross-tenant operations must be explicitly authorized and logged
- Tenant data access must be traceable to specific users and operations

### Authentication Integration

**Multi-Tenant SSO Support:**
```python
class TenantAwareAuthService:
    async def authenticate_user(self, credentials: UserCredentials, tenant_context: TenantContext) -> AuthResult:
        """Authenticate user with tenant-specific identity providers"""
        
        # Get tenant-specific auth configuration
        auth_config = await self.get_tenant_auth_config(tenant_context.tenant_id)
        
        if auth_config.sso_enabled:
            # Use tenant-specific SSO provider
            return await self.authenticate_via_sso(credentials, auth_config)
        else:
            # Use standard authentication
            return await self.authenticate_standard(credentials)
    
    async def validate_tenant_membership(self, user: User, tenant_id: str) -> bool:
        """Validate that user is a member of the specified tenant"""
        tenant_membership = await self.get_tenant_membership(user.id, tenant_id)
        return tenant_membership is not None and tenant_membership.status == 'active'
```

## Performance Optimization

### Tenant-Aware Caching

**Cache Key Strategy:**
```python
class TenantAwareCache:
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
    
    def get_cache_key(self, tenant_id: str, resource_type: str, resource_id: str) -> str:
        """Generate tenant-scoped cache keys"""
        return f"tenant:{tenant_id}:{resource_type}:{resource_id}"
    
    async def get_tenant_scoped(self, tenant_id: str, key: str) -> Optional[Any]:
        """Get cached value with automatic tenant scoping"""
        cache_key = self.get_cache_key(tenant_id, "generic", key)
        return await self.redis.get(cache_key)
    
    async def invalidate_tenant_cache(self, tenant_id: str):
        """Invalidate all cache entries for a specific tenant"""
        pattern = f"tenant:{tenant_id}:*"
        keys = await self.redis.keys(pattern)
        if keys:
            await self.redis.delete(*keys)
```

### Database Query Optimization

**Index Strategy:**
```sql
-- Composite indexes for tenant-scoped queries
CREATE INDEX idx_agents_tenant_created ON agents(tenant_id, created_at DESC);
CREATE INDEX idx_workflows_tenant_status ON workflows(tenant_id, status);
CREATE INDEX idx_executions_tenant_workflow ON executions(tenant_id, workflow_id);

-- Partial indexes for active tenants only
CREATE INDEX idx_active_tenant_agents ON agents(tenant_id, id) 
WHERE tenant_id IN (SELECT id FROM tenants WHERE status = 'active');
```

## Deployment Considerations

### Environment Configuration

**Multi-Tenant vs Single-Tenant Mode:**
```python
# Environment-based tenant mode configuration
TENANT_MODE = os.getenv('TENANT_MODE', 'single')  # 'single' or 'multi'

class TenantModeConfig:
    @staticmethod
    def is_multi_tenant() -> bool:
        return TENANT_MODE == 'multi'
    
    @staticmethod
    def get_default_tenant_id() -> Optional[str]:
        """Get default tenant ID for single-tenant deployments"""
        if TENANT_MODE == 'single':
            return os.getenv('DEFAULT_TENANT_ID', 'default')
        return None
```

**Migration Strategy:**
```python
# Database migration for enabling multi-tenant mode
async def migrate_to_multi_tenant():
    """Migrate existing single-tenant deployment to multi-tenant"""
    
    # 1. Create system tenant
    system_tenant = await create_system_tenant()
    
    # 2. Create default tenant for existing data
    default_tenant = await create_default_tenant()
    
    # 3. Migrate existing data to default tenant
    await migrate_existing_agents(default_tenant.id)
    await migrate_existing_workflows(default_tenant.id)
    await migrate_existing_users(default_tenant.id)
    
    # 4. Update configuration
    await update_tenant_mode_config('multi')
```

## Monitoring and Observability

### Tenant-Specific Metrics

**Metrics Collection:**
```python
# Tenant-aware metrics collection
class TenantMetrics:
    def __init__(self, prometheus_registry):
        self.agent_executions = Counter(
            'agent_executions_total',
            'Total agent executions',
            ['tenant_id', 'agent_type', 'status']
        )
        
        self.resource_usage = Gauge(
            'tenant_resource_usage',
            'Current resource usage by tenant',
            ['tenant_id', 'resource_type']
        )
    
    def record_agent_execution(self, tenant_id: str, agent_type: str, status: str):
        self.agent_executions.labels(
            tenant_id=tenant_id,
            agent_type=agent_type,
            status=status
        ).inc()
    
    def update_resource_usage(self, tenant_id: str, resource_type: str, usage: float):
        self.resource_usage.labels(
            tenant_id=tenant_id,
            resource_type=resource_type
        ).set(usage)
```

### Tenant Health Monitoring

**Health Check Implementation:**
```python
class TenantHealthChecker:
    async def check_tenant_health(self, tenant_id: str) -> TenantHealthStatus:
        """Comprehensive tenant health check"""
        health_status = TenantHealthStatus(tenant_id=tenant_id)
        
        # Check database connectivity for tenant
        health_status.database = await self.check_tenant_database_access(tenant_id)
        
        # Check resource usage vs quotas
        health_status.resources = await self.check_tenant_resource_health(tenant_id)
        
        # Check active agents and workflows
        health_status.services = await self.check_tenant_service_health(tenant_id)
        
        # Check external integrations
        health_status.integrations = await self.check_tenant_integrations(tenant_id)
        
        return health_status
```

## Best Practices

### Code Organization

1. **Tenant Context Injection**: Always inject tenant context at the service layer
2. **Automatic Filtering**: Use middleware to automatically filter queries by tenant
3. **Resource Validation**: Validate tenant resource access before any operations
4. **Audit Everything**: Log all tenant operations with proper context
5. **Cache Isolation**: Ensure cache keys include tenant identifiers

### Error Handling

```python
class TenantAwareException(Exception):
    def __init__(self, message: str, tenant_id: str, error_code: str = None):
        self.tenant_id = tenant_id
        self.error_code = error_code
        super().__init__(f"[Tenant: {tenant_id}] {message}")

class QuotaExceededException(TenantAwareException):
    def __init__(self, resource_type: str, current_usage: int, quota_limit: int, 
                 requested_amount: int, tenant_id: str):
        message = (f"Quota exceeded for {resource_type}: "
                  f"current={current_usage}, limit={quota_limit}, "
                  f"requested={requested_amount}")
        super().__init__(message, tenant_id, "QUOTA_EXCEEDED")
```

### Testing Strategy

1. **Isolation Testing**: Verify complete data isolation between tenants
2. **Context Testing**: Ensure tenant context is maintained across all operations
3. **Quota Testing**: Validate resource quota enforcement
4. **Performance Testing**: Test with multiple tenants under load
5. **Migration Testing**: Verify single-tenant to multi-tenant migration