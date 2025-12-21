# Performance & Scalability Guidelines

## Performance Requirements & SLAs

### Production Response Time Targets
- **API Endpoints**: < 200ms for 95th percentile
- **Agent Creation**: < 2 seconds end-to-end
- **Workflow Execution Start**: < 500ms
- **Memory Retrieval**: < 100ms for semantic search
- **UI Loading**: < 2 seconds for critical path

### Development Response Time Targets (Relaxed)
- **API Endpoints**: < 2 seconds for 95th percentile
- **Agent Creation**: < 10 seconds end-to-end
- **Workflow Execution Start**: < 5 seconds
- **Memory Retrieval**: < 1 second for semantic search
- **UI Loading**: < 10 seconds for critical path

### Production Throughput Requirements
- **Concurrent Agent Executions**: 1000+ simultaneous agents
- **API Requests**: 10,000 requests/second sustained
- **Memory Operations**: 50,000 reads/second, 10,000 writes/second
- **Workflow Executions**: 500 concurrent workflows

### Development Throughput Requirements (Relaxed)
- **Concurrent Agent Executions**: 10+ simultaneous agents
- **API Requests**: 100 requests/second sustained
- **Memory Operations**: 1,000 reads/second, 100 writes/second
- **Workflow Executions**: 5 concurrent workflows

### Production Resource Utilization Targets
- **CPU**: < 70% average utilization per service
- **Memory**: < 80% of allocated memory
- **Database Connections**: < 80% of pool capacity
- **Network**: < 60% of available bandwidth

### Development Resource Utilization Targets (Relaxed)
- **CPU**: < 90% average utilization per service
- **Memory**: < 90% of allocated memory
- **Database Connections**: < 90% of pool capacity
- **Network**: < 80% of available bandwidth

## Performance Architecture Patterns

### Caching Strategy Implementation
```python
from functools import wraps
import asyncio
from typing import Any, Callable, Optional
import redis.asyncio as redis

class MultiLayerCache:
    def __init__(self):
        self.l1_cache = {}  # In-memory cache
        self.l2_cache = redis.Redis(host='redis', decode_responses=True)
        self.cache_stats = {'hits': 0, 'misses': 0}
    
    async def get(self, key: str) -> Optional[Any]:
        # L1 Cache check
        if key in self.l1_cache:
            self.cache_stats['hits'] += 1
            return self.l1_cache[key]
        
        # L2 Cache check
        value = await self.l2_cache.get(key)
        if value:
            self.l1_cache[key] = value  # Promote to L1
            self.cache_stats['hits'] += 1
            return value
        
        self.cache_stats['misses'] += 1
        return None
    
    async def set(self, key: str, value: Any, ttl: int = 300):
        # Set in both layers
        self.l1_cache[key] = value
        await self.l2_cache.setex(key, ttl, value)

def cached(ttl: int = 300, cache_key_func: Optional[Callable] = None):
    """Decorator for caching function results"""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache = MultiLayerCache()
            
            if cache_key_func:
                cache_key = cache_key_func(*args, **kwargs)
            else:
                cache_key = f"{func.__name__}:{hash(str(args) + str(kwargs))}"
            
            # Try cache first
            cached_result = await cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            await cache.set(cache_key, result, ttl)
            return result
        
        return wrapper
    return decorator
```

### Database Performance Optimization
```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool

class DatabaseManager:
    def __init__(self):
        # Optimized connection pool configuration
        self.engine = create_async_engine(
            DATABASE_URL,
            poolclass=QueuePool,
            pool_size=20,           # Base connections
            max_overflow=30,        # Additional connections under load
            pool_timeout=30,        # Wait time for connection
            pool_recycle=3600,      # Recycle connections hourly
            pool_pre_ping=True,     # Validate connections
            echo=False,             # Disable SQL logging in production
            query_cache_size=1200,  # Cache prepared statements
        )
        
        self.session_factory = sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
    
    async def execute_with_retry(self, query, max_retries=3):
        """Execute database query with exponential backoff retry"""
        for attempt in range(max_retries):
            try:
                async with self.session_factory() as session:
                    result = await session.execute(query)
                    await session.commit()
                    return result
            except Exception as e:
                if attempt == max_retries - 1:
                    raise e
                
                wait_time = (2 ** attempt) + random.uniform(0, 1)
                await asyncio.sleep(wait_time)

# Query optimization patterns
class OptimizedQueries:
    @staticmethod
    async def get_agent_with_dependencies(agent_id: str) -> Agent:
        """Optimized query with eager loading"""
        query = select(Agent).options(
            selectinload(Agent.configurations),
            selectinload(Agent.deployments),
            selectinload(Agent.memory_entries)
        ).where(Agent.id == agent_id)
        
        return await db.execute_with_retry(query)
    
    @staticmethod
    async def get_agents_paginated(offset: int, limit: int) -> List[Agent]:
        """Paginated query with index optimization"""
        query = select(Agent).offset(offset).limit(limit).order_by(Agent.created_at.desc())
        return await db.execute_with_retry(query)
```

### Async Processing & Concurrency
```python
import asyncio
from asyncio import Semaphore
from typing import List, Coroutine, Any

class ConcurrencyManager:
    def __init__(self, max_concurrent_operations: int = 100):
        self.semaphore = Semaphore(max_concurrent_operations)
        self.active_operations = 0
        self.operation_stats = {
            'completed': 0,
            'failed': 0,
            'average_duration': 0
        }
    
    async def execute_with_concurrency_limit(self, coro: Coroutine) -> Any:
        """Execute coroutine with concurrency limiting"""
        async with self.semaphore:
            self.active_operations += 1
            start_time = time.time()
            
            try:
                result = await coro
                self.operation_stats['completed'] += 1
                return result
            except Exception as e:
                self.operation_stats['failed'] += 1
                raise e
            finally:
                self.active_operations -= 1
                duration = time.time() - start_time
                self._update_average_duration(duration)
    
    async def execute_batch(self, coroutines: List[Coroutine]) -> List[Any]:
        """Execute multiple coroutines with optimal batching"""
        batch_size = min(len(coroutines), 50)  # Optimal batch size
        results = []
        
        for i in range(0, len(coroutines), batch_size):
            batch = coroutines[i:i + batch_size]
            batch_results = await asyncio.gather(
                *[self.execute_with_concurrency_limit(coro) for coro in batch],
                return_exceptions=True
            )
            results.extend(batch_results)
        
        return results

# Agent execution optimization
class OptimizedAgentExecutor:
    def __init__(self):
        self.concurrency_manager = ConcurrencyManager(max_concurrent_operations=200)
        self.execution_cache = {}
    
    async def execute_agent_pipeline(self, agent_id: str, input_data: dict) -> dict:
        """Optimized agent execution with parallel processing"""
        
        # Parallel data loading
        async with asyncio.TaskGroup() as tg:
            agent_task = tg.create_task(self.load_agent_config(agent_id))
            memory_task = tg.create_task(self.load_agent_memory(agent_id))
            tools_task = tg.create_task(self.load_available_tools(agent_id))
        
        agent_config = agent_task.result()
        agent_memory = memory_task.result()
        available_tools = tools_task.result()
        
        # Parallel LLM processing
        llm_tasks = []
        if agent_config.requires_multiple_llm_calls:
            for prompt_chunk in self.chunk_prompt(input_data):
                llm_task = self.call_llm_provider(agent_config, prompt_chunk)
                llm_tasks.append(llm_task)
        else:
            llm_tasks = [self.call_llm_provider(agent_config, input_data)]
        
        llm_results = await self.concurrency_manager.execute_batch(llm_tasks)
        
        # Combine results and update memory
        final_result = await self.combine_llm_results(llm_results)
        
        # Async memory update (don't wait for completion)
        asyncio.create_task(self.update_agent_memory(agent_id, final_result))
        
        return final_result
```

### Memory Management & Optimization
```python
import gc
import psutil
from typing import Dict, Any
import weakref

class MemoryManager:
    def __init__(self):
        self.memory_threshold = 0.8  # 80% memory usage threshold
        self.cleanup_callbacks = []
        self.object_pools = {}
        
    def monitor_memory_usage(self):
        """Monitor system memory and trigger cleanup if needed"""
        memory_percent = psutil.virtual_memory().percent / 100
        
        if memory_percent > self.memory_threshold:
            self.trigger_memory_cleanup()
            
        return memory_percent
    
    def trigger_memory_cleanup(self):
        """Aggressive memory cleanup when threshold exceeded"""
        # Clear caches
        for callback in self.cleanup_callbacks:
            callback()
        
        # Force garbage collection
        gc.collect()
        
        # Clear object pools
        for pool in self.object_pools.values():
            pool.clear()
    
    def register_cleanup_callback(self, callback):
        """Register callback for memory cleanup"""
        self.cleanup_callbacks.append(callback)

# Memory-efficient data structures
class MemoryEfficientAgentContext:
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self._memory_entries = weakref.WeakValueDictionary()
        self._execution_cache = {}
        self._max_cache_size = 1000
    
    def add_memory_entry(self, key: str, value: Any):
        """Add memory entry with automatic cleanup"""
        if len(self._execution_cache) > self._max_cache_size:
            # Remove oldest entries (LRU)
            oldest_keys = list(self._execution_cache.keys())[:100]
            for key in oldest_keys:
                del self._execution_cache[key]
        
        self._execution_cache[key] = value
    
    def __del__(self):
        """Cleanup when context is destroyed"""
        self._memory_entries.clear()
        self._execution_cache.clear()
```

## Performance Monitoring & Alerting

### Performance Metrics Collection
```python
import time
from prometheus_client import Counter, Histogram, Gauge
from functools import wraps

# Prometheus metrics
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
REQUEST_DURATION = Histogram('http_request_duration_seconds', 'HTTP request duration')
ACTIVE_CONNECTIONS = Gauge('active_database_connections', 'Active database connections')
MEMORY_USAGE = Gauge('memory_usage_bytes', 'Memory usage in bytes')
AGENT_EXECUTION_TIME = Histogram('agent_execution_duration_seconds', 'Agent execution time')

def monitor_performance(metric_name: str = None):
    """Decorator to monitor function performance"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                status = 'success'
                return result
            except Exception as e:
                status = 'error'
                raise e
            finally:
                duration = time.time() - start_time
                
                if metric_name:
                    REQUEST_DURATION.observe(duration)
                    REQUEST_COUNT.labels(
                        method=getattr(func, '__name__', 'unknown'),
                        endpoint=metric_name,
                        status=status
                    ).inc()
        
        return wrapper
    return decorator

class PerformanceMonitor:
    def __init__(self):
        self.performance_thresholds = {
            'api_response_time': 0.2,  # 200ms
            'database_query_time': 0.1,  # 100ms
            'memory_usage_percent': 0.8,  # 80%
            'cpu_usage_percent': 0.7,  # 70%
        }
    
    async def check_performance_thresholds(self):
        """Check if performance metrics exceed thresholds"""
        alerts = []
        
        # Check API response times
        avg_response_time = REQUEST_DURATION._sum.get() / REQUEST_DURATION._count.get()
        if avg_response_time > self.performance_thresholds['api_response_time']:
            alerts.append({
                'type': 'performance',
                'metric': 'api_response_time',
                'value': avg_response_time,
                'threshold': self.performance_thresholds['api_response_time']
            })
        
        # Check memory usage
        memory_percent = psutil.virtual_memory().percent / 100
        if memory_percent > self.performance_thresholds['memory_usage_percent']:
            alerts.append({
                'type': 'performance',
                'metric': 'memory_usage',
                'value': memory_percent,
                'threshold': self.performance_thresholds['memory_usage_percent']
            })
        
        return alerts
```

## Load Testing & Capacity Planning

### Load Testing Strategy
```python
# Load testing with locust
from locust import HttpUser, task, between

class AgentFrameworkUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        """Login and setup"""
        response = self.client.post("/api/v1/auth/login", json={
            "username": "test_user",
            "password": "test_password"
        })
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    @task(3)
    def list_agents(self):
        """Most common operation - list agents"""
        self.client.get("/api/v1/agents", headers=self.headers)
    
    @task(2)
    def get_agent_details(self):
        """Get specific agent details"""
        self.client.get("/api/v1/agents/test-agent-id", headers=self.headers)
    
    @task(1)
    def create_agent(self):
        """Less frequent but resource-intensive operation"""
        agent_data = {
            "name": "Load Test Agent",
            "template": "chatbot",
            "config": {
                "llm_provider": "ollama",
                "model": "llama2"
            }
        }
        self.client.post("/api/v1/agents", json=agent_data, headers=self.headers)

# Capacity planning calculations
class CapacityPlanner:
    def __init__(self):
        self.baseline_metrics = {
            'requests_per_second': 1000,
            'avg_response_time': 0.15,
            'memory_per_request': 50 * 1024,  # 50KB
            'cpu_per_request': 0.01,  # 1% CPU
        }
    
    def calculate_required_resources(self, target_rps: int) -> Dict[str, Any]:
        """Calculate required resources for target RPS"""
        scaling_factor = target_rps / self.baseline_metrics['requests_per_second']
        
        return {
            'cpu_cores': max(4, int(scaling_factor * 8)),  # Minimum 4 cores
            'memory_gb': max(8, int(scaling_factor * 16)),  # Minimum 8GB
            'database_connections': max(20, int(scaling_factor * 40)),
            'redis_memory_gb': max(2, int(scaling_factor * 4)),
            'estimated_response_time': self.baseline_metrics['avg_response_time'] * (1 + scaling_factor * 0.1)
        }
```

## Performance Optimization Checklist

### Database Optimization
- [ ] All queries use appropriate indexes
- [ ] Connection pooling configured optimally
- [ ] Query execution plans reviewed and optimized
- [ ] Database statistics updated regularly
- [ ] Slow query logging enabled and monitored

### Application Optimization
- [ ] All I/O operations are asynchronous
- [ ] Caching implemented at multiple layers
- [ ] Memory usage monitored and optimized
- [ ] CPU-intensive operations moved to background tasks
- [ ] Connection reuse implemented for external services

### Infrastructure Optimization
- [ ] Load balancing configured for even distribution
- [ ] Auto-scaling policies defined and tested
- [ ] CDN configured for static assets
- [ ] Network latency minimized
- [ ] Resource limits and requests properly configured