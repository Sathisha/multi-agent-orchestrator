# Reliability & Operational Excellence

## Reliability Requirements & SLAs

### Service Level Objectives (SLOs)
- **Availability**: 99.9% uptime (8.77 hours downtime/year)
- **Error Rate**: < 0.1% of all requests
- **Recovery Time**: < 5 minutes for service restoration
- **Data Durability**: 99.999999999% (11 9's) for critical data
- **Backup Recovery**: < 4 hours RTO, < 1 hour RPO

### Failure Budget Management
- **Monthly Error Budget**: 0.1% of total requests
- **Downtime Budget**: 43.8 minutes per month
- **Alert Thresholds**: 50% budget consumed = warning, 80% = critical
- **Feature Freeze**: When 90% of error budget is consumed

## Resilience Patterns Implementation

### Circuit Breaker Pattern
```python
import asyncio
import time
from enum import Enum
from typing import Callable, Any, Optional
import logging

class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

class CircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception,
        success_threshold: int = 3
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.success_threshold = success_threshold
        
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = CircuitState.CLOSED
        self.logger = logging.getLogger(__name__)
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection"""
        
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                self.logger.info(f"Circuit breaker transitioning to HALF_OPEN")
            else:
                raise CircuitBreakerOpenException(
                    f"Circuit breaker is OPEN. Last failure: {self.last_failure_time}"
                )
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
            
        except self.expected_exception as e:
            self._on_failure()
            raise e
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset"""
        return (
            self.last_failure_time is not None and
            time.time() - self.last_failure_time >= self.recovery_timeout
        )
    
    def _on_success(self):
        """Handle successful execution"""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                self._reset()
        elif self.state == CircuitState.CLOSED:
            self.failure_count = 0
    
    def _on_failure(self):
        """Handle failed execution"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            self.logger.error(f"Circuit breaker opened after {self.failure_count} failures")
        
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            self.logger.warning("Circuit breaker reopened during half-open state")
    
    def _reset(self):
        """Reset circuit breaker to closed state"""
        self.failure_count = 0
        self.success_count = 0
        self.state = CircuitState.CLOSED
        self.logger.info("Circuit breaker reset to CLOSED state")

class CircuitBreakerOpenException(Exception):
    """Exception raised when circuit breaker is open"""
    pass
```

### Retry Pattern with Exponential Backoff
```python
import asyncio
import random
from typing import Callable, Any, Type, Tuple
from functools import wraps

class RetryConfig:
    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,)
    ):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.retryable_exceptions = retryable_exceptions

def retry_with_backoff(config: RetryConfig):
    """Decorator for retry with exponential backoff"""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(config.max_attempts):
                try:
                    return await func(*args, **kwargs)
                    
                except config.retryable_exceptions as e:
                    last_exception = e
                    
                    if attempt == config.max_attempts - 1:
                        # Last attempt failed, raise the exception
                        raise e
                    
                    # Calculate delay with exponential backoff
                    delay = min(
                        config.base_delay * (config.exponential_base ** attempt),
                        config.max_delay
                    )
                    
                    # Add jitter to prevent thundering herd
                    if config.jitter:
                        delay *= (0.5 + random.random() * 0.5)
                    
                    logging.warning(
                        f"Attempt {attempt + 1} failed for {func.__name__}: {e}. "
                        f"Retrying in {delay:.2f} seconds..."
                    )
                    
                    await asyncio.sleep(delay)
            
            # This should never be reached, but just in case
            raise last_exception
        
        return wrapper
    return decorator

# Usage example
@retry_with_backoff(RetryConfig(
    max_attempts=5,
    base_delay=1.0,
    max_delay=30.0,
    retryable_exceptions=(ConnectionError, TimeoutError)
))
async def call_external_service(url: str) -> dict:
    """Call external service with retry logic"""
    async with httpx.AsyncClient() as client:
        response = await client.get(url, timeout=10.0)
        response.raise_for_status()
        return response.json()
```

### Bulkhead Pattern for Resource Isolation
```python
import asyncio
from asyncio import Semaphore
from typing import Dict, Any
import logging

class ResourcePool:
    def __init__(self, name: str, max_concurrent: int):
        self.name = name
        self.semaphore = Semaphore(max_concurrent)
        self.active_operations = 0
        self.total_operations = 0
        self.failed_operations = 0
        self.logger = logging.getLogger(__name__)
    
    async def execute(self, operation: Callable, *args, **kwargs) -> Any:
        """Execute operation within resource pool limits"""
        async with self.semaphore:
            self.active_operations += 1
            self.total_operations += 1
            
            try:
                result = await operation(*args, **kwargs)
                return result
            except Exception as e:
                self.failed_operations += 1
                self.logger.error(f"Operation failed in pool {self.name}: {e}")
                raise e
            finally:
                self.active_operations -= 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics"""
        return {
            'name': self.name,
            'active_operations': self.active_operations,
            'total_operations': self.total_operations,
            'failed_operations': self.failed_operations,
            'success_rate': (
                (self.total_operations - self.failed_operations) / self.total_operations
                if self.total_operations > 0 else 0
            )
        }

class BulkheadManager:
    def __init__(self):
        self.pools: Dict[str, ResourcePool] = {
            'llm_calls': ResourcePool('llm_calls', max_concurrent=50),
            'database_operations': ResourcePool('database_operations', max_concurrent=100),
            'memory_operations': ResourcePool('memory_operations', max_concurrent=200),
            'tool_executions': ResourcePool('tool_executions', max_concurrent=30),
            'file_operations': ResourcePool('file_operations', max_concurrent=20)
        }
    
    async def execute_in_pool(self, pool_name: str, operation: Callable, *args, **kwargs) -> Any:
        """Execute operation in specified resource pool"""
        if pool_name not in self.pools:
            raise ValueError(f"Unknown resource pool: {pool_name}")
        
        return await self.pools[pool_name].execute(operation, *args, **kwargs)
    
    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all pools"""
        return {name: pool.get_stats() for name, pool in self.pools.items()}

# Global bulkhead manager instance
bulkhead_manager = BulkheadManager()
```

### Health Check System
```python
import asyncio
import time
from typing import Dict, Any, List, Optional
from enum import Enum
import httpx
import psutil

class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"

class HealthCheck:
    def __init__(self, name: str, check_func: Callable, timeout: float = 5.0):
        self.name = name
        self.check_func = check_func
        self.timeout = timeout
        self.last_check_time: Optional[float] = None
        self.last_status: Optional[HealthStatus] = None
        self.last_error: Optional[str] = None
    
    async def execute(self) -> Dict[str, Any]:
        """Execute health check"""
        start_time = time.time()
        
        try:
            result = await asyncio.wait_for(self.check_func(), timeout=self.timeout)
            status = HealthStatus.HEALTHY
            error = None
            
        except asyncio.TimeoutError:
            result = None
            status = HealthStatus.UNHEALTHY
            error = f"Health check timed out after {self.timeout}s"
            
        except Exception as e:
            result = None
            status = HealthStatus.UNHEALTHY
            error = str(e)
        
        duration = time.time() - start_time
        
        self.last_check_time = start_time
        self.last_status = status
        self.last_error = error
        
        return {
            'name': self.name,
            'status': status.value,
            'duration_ms': round(duration * 1000, 2),
            'timestamp': start_time,
            'result': result,
            'error': error
        }

class HealthCheckManager:
    def __init__(self):
        self.checks: List[HealthCheck] = []
        self.register_default_checks()
    
    def register_default_checks(self):
        """Register default system health checks"""
        self.checks.extend([
            HealthCheck('database', self.check_database),
            HealthCheck('redis', self.check_redis),
            HealthCheck('memory', self.check_memory),
            HealthCheck('disk_space', self.check_disk_space),
            HealthCheck('llm_providers', self.check_llm_providers)
        ])
    
    async def check_database(self) -> Dict[str, Any]:
        """Check database connectivity and performance"""
        from backend.shared.database import get_database_session
        
        async with get_database_session() as session:
            start_time = time.time()
            result = await session.execute("SELECT 1")
            query_time = time.time() - start_time
            
            return {
                'connected': True,
                'query_time_ms': round(query_time * 1000, 2),
                'active_connections': session.get_bind().pool.checkedout()
            }
    
    async def check_redis(self) -> Dict[str, Any]:
        """Check Redis connectivity and performance"""
        import redis.asyncio as redis
        
        client = redis.Redis(host='redis', decode_responses=True)
        
        start_time = time.time()
        await client.ping()
        ping_time = time.time() - start_time
        
        info = await client.info()
        
        return {
            'connected': True,
            'ping_time_ms': round(ping_time * 1000, 2),
            'used_memory_mb': round(info['used_memory'] / 1024 / 1024, 2),
            'connected_clients': info['connected_clients']
        }
    
    async def check_memory(self) -> Dict[str, Any]:
        """Check system memory usage"""
        memory = psutil.virtual_memory()
        
        return {
            'total_gb': round(memory.total / 1024 / 1024 / 1024, 2),
            'available_gb': round(memory.available / 1024 / 1024 / 1024, 2),
            'used_percent': memory.percent,
            'status': 'healthy' if memory.percent < 80 else 'degraded' if memory.percent < 90 else 'unhealthy'
        }
    
    async def check_disk_space(self) -> Dict[str, Any]:
        """Check disk space usage"""
        disk = psutil.disk_usage('/')
        
        used_percent = (disk.used / disk.total) * 100
        
        return {
            'total_gb': round(disk.total / 1024 / 1024 / 1024, 2),
            'free_gb': round(disk.free / 1024 / 1024 / 1024, 2),
            'used_percent': round(used_percent, 2),
            'status': 'healthy' if used_percent < 80 else 'degraded' if used_percent < 90 else 'unhealthy'
        }
    
    async def check_llm_providers(self) -> Dict[str, Any]:
        """Check LLM provider connectivity"""
        providers_status = {}
        
        # Check Ollama (local)
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get('http://ollama:11434/api/tags', timeout=5.0)
                providers_status['ollama'] = {
                    'status': 'healthy' if response.status_code == 200 else 'unhealthy',
                    'response_time_ms': response.elapsed.total_seconds() * 1000
                }
        except Exception as e:
            providers_status['ollama'] = {'status': 'unhealthy', 'error': str(e)}
        
        return providers_status
    
    async def run_all_checks(self) -> Dict[str, Any]:
        """Run all health checks concurrently"""
        check_tasks = [check.execute() for check in self.checks]
        results = await asyncio.gather(*check_tasks, return_exceptions=True)
        
        # Process results
        check_results = []
        overall_status = HealthStatus.HEALTHY
        
        for result in results:
            if isinstance(result, Exception):
                check_results.append({
                    'name': 'unknown',
                    'status': HealthStatus.UNHEALTHY.value,
                    'error': str(result)
                })
                overall_status = HealthStatus.UNHEALTHY
            else:
                check_results.append(result)
                if result['status'] == HealthStatus.UNHEALTHY.value:
                    overall_status = HealthStatus.UNHEALTHY
                elif result['status'] == HealthStatus.DEGRADED.value and overall_status == HealthStatus.HEALTHY:
                    overall_status = HealthStatus.DEGRADED
        
        return {
            'status': overall_status.value,
            'timestamp': time.time(),
            'checks': check_results,
            'summary': {
                'total_checks': len(check_results),
                'healthy_checks': len([c for c in check_results if c['status'] == 'healthy']),
                'degraded_checks': len([c for c in check_results if c['status'] == 'degraded']),
                'unhealthy_checks': len([c for c in check_results if c['status'] == 'unhealthy'])
            }
        }

# Global health check manager
health_manager = HealthCheckManager()
```

## Disaster Recovery & Business Continuity

### Backup Strategy
```python
import asyncio
import os
import subprocess
from datetime import datetime, timedelta
from typing import List, Dict, Any
import boto3
import logging

class BackupManager:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.s3_client = boto3.client('s3') if os.getenv('AWS_ACCESS_KEY_ID') else None
        self.backup_retention_days = 30
        self.backup_bucket = os.getenv('BACKUP_BUCKET', 'ai-agent-framework-backups')
    
    async def create_database_backup(self) -> str:
        """Create PostgreSQL database backup"""
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        backup_filename = f"database_backup_{timestamp}.sql"
        backup_path = f"/tmp/{backup_filename}"
        
        # Create database dump
        cmd = [
            'pg_dump',
            '-h', os.getenv('DB_HOST', 'postgres'),
            '-U', os.getenv('DB_USER', 'postgres'),
            '-d', os.getenv('DB_NAME', 'ai_agent_framework'),
            '-f', backup_path,
            '--verbose'
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={**os.environ, 'PGPASSWORD': os.getenv('DB_PASSWORD')}
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            raise Exception(f"Database backup failed: {stderr.decode()}")
        
        self.logger.info(f"Database backup created: {backup_path}")
        
        # Upload to S3 if configured
        if self.s3_client:
            await self.upload_to_s3(backup_path, f"database/{backup_filename}")
        
        return backup_path
    
    async def create_redis_backup(self) -> str:
        """Create Redis backup"""
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        backup_filename = f"redis_backup_{timestamp}.rdb"
        backup_path = f"/tmp/{backup_filename}"
        
        # Trigger Redis BGSAVE
        import redis.asyncio as redis
        client = redis.Redis(host='redis')
        
        await client.bgsave()
        
        # Wait for backup to complete
        while True:
            info = await client.info('persistence')
            if info['rdb_bgsave_in_progress'] == 0:
                break
            await asyncio.sleep(1)
        
        # Copy RDB file
        cmd = ['docker', 'cp', 'redis:/data/dump.rdb', backup_path]
        process = await asyncio.create_subprocess_exec(*cmd)
        await process.communicate()
        
        if process.returncode != 0:
            raise Exception("Redis backup failed")
        
        self.logger.info(f"Redis backup created: {backup_path}")
        
        # Upload to S3 if configured
        if self.s3_client:
            await self.upload_to_s3(backup_path, f"redis/{backup_filename}")
        
        return backup_path
    
    async def upload_to_s3(self, local_path: str, s3_key: str):
        """Upload backup file to S3"""
        try:
            self.s3_client.upload_file(local_path, self.backup_bucket, s3_key)
            self.logger.info(f"Backup uploaded to S3: s3://{self.backup_bucket}/{s3_key}")
        except Exception as e:
            self.logger.error(f"Failed to upload backup to S3: {e}")
            raise e
    
    async def cleanup_old_backups(self):
        """Remove backups older than retention period"""
        cutoff_date = datetime.utcnow() - timedelta(days=self.backup_retention_days)
        
        if self.s3_client:
            # List and delete old S3 objects
            response = self.s3_client.list_objects_v2(Bucket=self.backup_bucket)
            
            for obj in response.get('Contents', []):
                if obj['LastModified'].replace(tzinfo=None) < cutoff_date:
                    self.s3_client.delete_object(Bucket=self.backup_bucket, Key=obj['Key'])
                    self.logger.info(f"Deleted old backup: {obj['Key']}")
    
    async def run_full_backup(self) -> Dict[str, str]:
        """Run complete backup of all systems"""
        backup_results = {}
        
        try:
            # Database backup
            db_backup = await self.create_database_backup()
            backup_results['database'] = db_backup
            
            # Redis backup
            redis_backup = await self.create_redis_backup()
            backup_results['redis'] = redis_backup
            
            # Cleanup old backups
            await self.cleanup_old_backups()
            
            self.logger.info("Full backup completed successfully")
            
        except Exception as e:
            self.logger.error(f"Backup failed: {e}")
            raise e
        
        return backup_results

# Global backup manager
backup_manager = BackupManager()
```

### Monitoring & Alerting
```python
import asyncio
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, List
import httpx
import logging

class AlertManager:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.smtp_server = os.getenv('SMTP_SERVER')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.smtp_username = os.getenv('SMTP_USERNAME')
        self.smtp_password = os.getenv('SMTP_PASSWORD')
        self.alert_recipients = os.getenv('ALERT_RECIPIENTS', '').split(',')
        self.slack_webhook_url = os.getenv('SLACK_WEBHOOK_URL')
        
        # Alert thresholds
        self.thresholds = {
            'error_rate': 0.01,  # 1%
            'response_time_p95': 1.0,  # 1 second
            'memory_usage': 0.85,  # 85%
            'disk_usage': 0.90,  # 90%
            'failed_health_checks': 2
        }
    
    async def send_email_alert(self, subject: str, body: str, severity: str = 'warning'):
        """Send email alert"""
        if not all([self.smtp_server, self.smtp_username, self.smtp_password]):
            self.logger.warning("SMTP not configured, skipping email alert")
            return
        
        try:
            msg = MIMEMultipart()
            msg['From'] = self.smtp_username
            msg['To'] = ', '.join(self.alert_recipients)
            msg['Subject'] = f"[{severity.upper()}] AI Agent Framework: {subject}"
            
            msg.attach(MIMEText(body, 'plain'))
            
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.smtp_username, self.smtp_password)
            server.send_message(msg)
            server.quit()
            
            self.logger.info(f"Email alert sent: {subject}")
            
        except Exception as e:
            self.logger.error(f"Failed to send email alert: {e}")
    
    async def send_slack_alert(self, message: str, severity: str = 'warning'):
        """Send Slack alert"""
        if not self.slack_webhook_url:
            self.logger.warning("Slack webhook not configured, skipping Slack alert")
            return
        
        color_map = {
            'info': '#36a64f',
            'warning': '#ff9500',
            'critical': '#ff0000'
        }
        
        payload = {
            'attachments': [{
                'color': color_map.get(severity, '#ff9500'),
                'title': f'AI Agent Framework Alert ({severity.upper()})',
                'text': message,
                'ts': int(time.time())
            }]
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(self.slack_webhook_url, json=payload)
                response.raise_for_status()
                
            self.logger.info("Slack alert sent successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to send Slack alert: {e}")
    
    async def check_and_alert(self, metrics: Dict[str, Any]):
        """Check metrics against thresholds and send alerts"""
        alerts = []
        
        # Check error rate
        if metrics.get('error_rate', 0) > self.thresholds['error_rate']:
            alerts.append({
                'severity': 'critical',
                'message': f"High error rate detected: {metrics['error_rate']:.2%}"
            })
        
        # Check response time
        if metrics.get('response_time_p95', 0) > self.thresholds['response_time_p95']:
            alerts.append({
                'severity': 'warning',
                'message': f"High response time (P95): {metrics['response_time_p95']:.2f}s"
            })
        
        # Check memory usage
        if metrics.get('memory_usage', 0) > self.thresholds['memory_usage']:
            alerts.append({
                'severity': 'warning',
                'message': f"High memory usage: {metrics['memory_usage']:.1%}"
            })
        
        # Send alerts
        for alert in alerts:
            await self.send_slack_alert(alert['message'], alert['severity'])
            await self.send_email_alert(
                f"{alert['severity'].title()} Alert",
                alert['message'],
                alert['severity']
            )

# Global alert manager
alert_manager = AlertManager()
```

## Operational Runbooks

### Service Recovery Procedures
```markdown
## Database Connection Issues
1. Check database health: `kubectl exec -it postgres-pod -- pg_isready`
2. Verify connection pool: Check active connections in monitoring
3. Restart connection pool: `kubectl rollout restart deployment/agent-manager`
4. If persistent: Scale up database resources or add read replicas

## High Memory Usage
1. Identify memory-consuming processes: `kubectl top pods`
2. Check for memory leaks in application logs
3. Trigger garbage collection: Send SIGUSR1 to Python processes
4. Scale horizontally: `kubectl scale deployment/agent-executor --replicas=5`
5. If critical: Restart affected pods with rolling update

## LLM Provider Failures
1. Check provider status pages
2. Verify API credentials and quotas
3. Switch to backup provider in configuration
4. Enable circuit breaker for failed provider
5. Monitor recovery and gradually re-enable

## Workflow Execution Failures
1. Check BPMN engine logs for errors
2. Verify agent availability and health
3. Check for resource constraints (CPU/memory)
4. Restart workflow orchestrator if needed
5. Resume failed workflows from last checkpoint
```

### Performance Degradation Response
```markdown
## Response Time Increase
1. Check current load and traffic patterns
2. Identify slow database queries in logs
3. Verify cache hit rates and performance
4. Scale up application instances
5. Enable additional caching layers
6. Consider circuit breakers for slow dependencies

## High Error Rates
1. Check error logs for patterns and root causes
2. Verify external service availability
3. Check for configuration changes or deployments
4. Enable graceful degradation modes
5. Scale up resources if capacity-related
6. Rollback recent changes if necessary
```