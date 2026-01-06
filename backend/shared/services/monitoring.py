"""
Monitoring and Observability Service

This service provides comprehensive monitoring capabilities including:
- Metrics collection and aggregation
- Health checks and system status monitoring
- Performance tracking and alerting
- Distributed tracing support
"""

import asyncio
import time
import psutil
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import json

from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry, generate_latest
import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from ..database import get_database_session


class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class HealthCheckResult:
    name: str
    status: HealthStatus
    duration_ms: float
    timestamp: datetime
    details: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


@dataclass
class SystemMetrics:
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    active_connections: int
    request_rate: float
    error_rate: float
    response_time_p95: float


class PrometheusMetrics:
    """Prometheus metrics collection"""
    
    def __init__(self):
        self.registry = CollectorRegistry()
        
        # HTTP Request metrics
        self.http_requests_total = Counter(
            'http_requests_total',
            'Total HTTP requests',
            ['method', 'endpoint', 'status_code'],
            registry=self.registry
        )
        
        self.http_request_duration = Histogram(
            'http_request_duration_seconds',
            'HTTP request duration in seconds',
            ['method', 'endpoint'],
            registry=self.registry
        )
        
        # Agent execution metrics
        self.agent_executions_total = Counter(
            'agent_executions_total',
            'Total agent executions',
            ['agent_type', 'status'],
            registry=self.registry
        )
        
        self.agent_execution_duration = Histogram(
            'agent_execution_duration_seconds',
            'Agent execution duration in seconds',
            ['agent_type'],
            registry=self.registry
        )
        
        # System metrics
        self.system_cpu_usage = Gauge(
            'system_cpu_usage_percent',
            'System CPU usage percentage',
            registry=self.registry
        )
        
        self.system_memory_usage = Gauge(
            'system_memory_usage_percent',
            'System memory usage percentage',
            registry=self.registry
        )
        
        self.system_disk_usage = Gauge(
            'system_disk_usage_percent',
            'System disk usage percentage',
            registry=self.registry
        )

        self.active_agents = Gauge(
            'active_agents_gauge',
            'Number of active agents',
            registry=self.registry
        )
        
        # Database metrics
        self.database_connections_active = Gauge(
            'database_connections_active',
            'Active database connections',
            registry=self.registry
        )
        
        self.database_query_duration = Histogram(
            'database_query_duration_seconds',
            'Database query duration in seconds',
            ['query_type'],
            registry=self.registry
        )
        
        # Cache metrics
        self.cache_hits_total = Counter(
            'cache_hits_total',
            'Total cache hits',
            ['cache_type'],
            registry=self.registry
        )
        
        self.cache_misses_total = Counter(
            'cache_misses_total',
            'Total cache misses',
            ['cache_type'],
            registry=self.registry
        )
        
        # LLM Provider metrics
        self.llm_requests_total = Counter(
            'llm_requests_total',
            'Total LLM provider requests',
            ['provider', 'model', 'status'],
            registry=self.registry
        )
        
        self.llm_request_duration = Histogram(
            'llm_request_duration_seconds',
            'LLM request duration in seconds',
            ['provider', 'model'],
            registry=self.registry
        )
        
        # Workflow metrics
        self.workflow_executions_total = Counter(
            'workflow_executions_total',
            'Total workflow executions',
            ['workflow_type', 'status'],
            registry=self.registry
        )
        
        self.workflow_execution_duration = Histogram(
            'workflow_execution_duration_seconds',
            'Workflow execution duration in seconds',
            ['workflow_type'],
            registry=self.registry
        )


class HealthChecker:
    """System health monitoring"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.checks = {
            'database': self._check_database,
            'redis': self._check_redis,
            'system_resources': self._check_system_resources,
            'llm_providers': self._check_llm_providers,
            'external_services': self._check_external_services
        }
    
    async def run_health_check(self, check_name: str) -> HealthCheckResult:
        """Run a specific health check"""
        if check_name not in self.checks:
            return HealthCheckResult(
                name=check_name,
                status=HealthStatus.UNHEALTHY,
                duration_ms=0,
                timestamp=datetime.utcnow(),
                error=f"Unknown health check: {check_name}"
            )
        
        start_time = time.time()
        timestamp = datetime.utcnow()
        
        try:
            check_func = self.checks[check_name]
            details = await asyncio.wait_for(check_func(), timeout=10.0)
            
            duration_ms = (time.time() - start_time) * 1000
            
            # Determine status based on details
            status = self._determine_status(check_name, details)
            
            return HealthCheckResult(
                name=check_name,
                status=status,
                duration_ms=duration_ms,
                timestamp=timestamp,
                details=details
            )
            
        except asyncio.TimeoutError:
            duration_ms = (time.time() - start_time) * 1000
            return HealthCheckResult(
                name=check_name,
                status=HealthStatus.UNHEALTHY,
                duration_ms=duration_ms,
                timestamp=timestamp,
                error="Health check timed out"
            )
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self.logger.error(f"Health check {check_name} failed: {e}")
            return HealthCheckResult(
                name=check_name,
                status=HealthStatus.UNHEALTHY,
                duration_ms=duration_ms,
                timestamp=timestamp,
                error=str(e)
            )
    
    async def run_all_health_checks(self) -> Dict[str, HealthCheckResult]:
        """Run all health checks concurrently"""
        tasks = {
            name: self.run_health_check(name)
            for name in self.checks.keys()
        }
        
        results = await asyncio.gather(*tasks.values(), return_exceptions=True)
        
        return {
            name: result if isinstance(result, HealthCheckResult) else HealthCheckResult(
                name=name,
                status=HealthStatus.UNHEALTHY,
                duration_ms=0,
                timestamp=datetime.utcnow(),
                error=str(result)
            )
            for name, result in zip(tasks.keys(), results)
        }
    
    async def _check_database(self) -> Dict[str, Any]:
        """Check database connectivity and performance"""
        async with get_database_session() as session:
            # Test basic connectivity
            start_time = time.time()
            result = await session.execute(text("SELECT 1"))
            query_time = (time.time() - start_time) * 1000
            
            # Get connection pool stats
            pool = session.get_bind().pool
            
            return {
                'connected': True,
                'query_time_ms': round(query_time, 2),
                'pool_size': pool.size(),
                'checked_out_connections': pool.checkedout(),
                'overflow_connections': pool.overflow(),
                'checked_in_connections': pool.checkedin()
            }
    
    async def _check_redis(self) -> Dict[str, Any]:
        """Check Redis connectivity and performance"""
        client = redis.Redis(host='redis', port=6379, decode_responses=True)
        
        try:
            # Test connectivity
            start_time = time.time()
            await client.ping()
            ping_time = (time.time() - start_time) * 1000
            
            # Get Redis info
            info = await client.info()
            
            return {
                'connected': True,
                'ping_time_ms': round(ping_time, 2),
                'used_memory_mb': round(info['used_memory'] / 1024 / 1024, 2),
                'connected_clients': info['connected_clients'],
                'total_commands_processed': info['total_commands_processed'],
                'keyspace_hits': info.get('keyspace_hits', 0),
                'keyspace_misses': info.get('keyspace_misses', 0)
            }
        finally:
            await client.close()
    
    async def _check_system_resources(self) -> Dict[str, Any]:
        """Check system resource usage"""
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # Memory usage
        memory = psutil.virtual_memory()
        
        # Disk usage
        disk = psutil.disk_usage('/')
        
        # Network stats
        network = psutil.net_io_counters()
        
        return {
            'cpu_percent': round(cpu_percent, 2),
            'memory_total_gb': round(memory.total / 1024 / 1024 / 1024, 2),
            'memory_available_gb': round(memory.available / 1024 / 1024 / 1024, 2),
            'memory_percent': round(memory.percent, 2),
            'disk_total_gb': round(disk.total / 1024 / 1024 / 1024, 2),
            'disk_free_gb': round(disk.free / 1024 / 1024 / 1024, 2),
            'disk_percent': round((disk.used / disk.total) * 100, 2),
            'network_bytes_sent': network.bytes_sent,
            'network_bytes_recv': network.bytes_recv
        }
    
    async def _check_llm_providers(self) -> Dict[str, Any]:
        """Check LLM provider connectivity"""
        import httpx
        
        providers_status = {}
        
        # Check Ollama
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get('http://ollama:11434/api/tags', timeout=5.0)
                providers_status['ollama'] = {
                    'status': 'healthy' if response.status_code == 200 else 'unhealthy',
                    'response_time_ms': response.elapsed.total_seconds() * 1000,
                    'models': response.json().get('models', []) if response.status_code == 200 else []
                }
        except Exception as e:
            providers_status['ollama'] = {
                'status': 'unhealthy',
                'error': str(e)
            }
        
        return providers_status
    
    async def _check_external_services(self) -> Dict[str, Any]:
        """Check external service connectivity"""
        import httpx
        
        services_status = {}
        
        # Check Kong API Gateway
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get('http://kong:8001/status', timeout=5.0)
                services_status['kong'] = {
                    'status': 'healthy' if response.status_code == 200 else 'unhealthy',
                    'response_time_ms': response.elapsed.total_seconds() * 1000
                }
        except Exception as e:
            services_status['kong'] = {
                'status': 'unhealthy',
                'error': str(e)
            }
        
        # Check Keycloak
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get('http://keycloak:8080/', timeout=5.0)
                services_status['keycloak'] = {
                    'status': 'healthy' if response.status_code == 200 else 'unhealthy',
                    'response_time_ms': response.elapsed.total_seconds() * 1000
                }
        except Exception as e:
            services_status['keycloak'] = {
                'status': 'unhealthy',
                'error': str(e)
            }
        
        return services_status
    
    def _determine_status(self, check_name: str, details: Dict[str, Any]) -> HealthStatus:
        """Determine health status based on check details"""
        if check_name == 'system_resources':
            cpu_percent = details.get('cpu_percent', 0)
            memory_percent = details.get('memory_percent', 0)
            disk_percent = details.get('disk_percent', 0)
            
            if cpu_percent > 90 or memory_percent > 90 or disk_percent > 95:
                return HealthStatus.UNHEALTHY
            elif cpu_percent > 80 or memory_percent > 80 or disk_percent > 90:
                return HealthStatus.DEGRADED
            else:
                return HealthStatus.HEALTHY
        
        elif check_name == 'database':
            query_time = details.get('query_time_ms', 0)
            if query_time > 1000:  # 1 second
                return HealthStatus.UNHEALTHY
            elif query_time > 500:  # 500ms
                return HealthStatus.DEGRADED
            else:
                return HealthStatus.HEALTHY
        
        elif check_name == 'redis':
            ping_time = details.get('ping_time_ms', 0)
            if ping_time > 100:  # 100ms
                return HealthStatus.DEGRADED
            else:
                return HealthStatus.HEALTHY
        
        elif check_name == 'llm_providers':
            unhealthy_count = sum(1 for provider in details.values() if provider.get('status') == 'unhealthy')
            if unhealthy_count == len(details):
                return HealthStatus.UNHEALTHY
            elif unhealthy_count > 0:
                return HealthStatus.DEGRADED
            else:
                return HealthStatus.HEALTHY
        
        elif check_name == 'external_services':
            unhealthy_count = sum(1 for service in details.values() if service.get('status') == 'unhealthy')
            if unhealthy_count > len(details) // 2:
                return HealthStatus.UNHEALTHY
            elif unhealthy_count > 0:
                return HealthStatus.DEGRADED
            else:
                return HealthStatus.HEALTHY
        
        return HealthStatus.HEALTHY


class MonitoringService:
    """Main monitoring service"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.metrics = PrometheusMetrics()
        self.health_checker = HealthChecker()
        self.redis_client = None
        self._monitoring_task = None
        
        # Alert thresholds
        self.alert_thresholds = {
            'cpu_usage': 80.0,
            'memory_usage': 85.0,
            'disk_usage': 90.0,
            'error_rate': 5.0,  # 5%
            'response_time_p95': 2.0,  # 2 seconds
            'database_query_time': 1000.0,  # 1 second
        }
    
    async def start(self):
        """Start monitoring service"""
        self.redis_client = redis.Redis(host='redis', port=6379, decode_responses=True)
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        self.logger.info("Monitoring service started")
    
    async def stop(self):
        """Stop monitoring service"""
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        
        if self.redis_client:
            await self.redis_client.close()
        
        self.logger.info("Monitoring service stopped")
    
    async def _monitoring_loop(self):
        """Main monitoring loop"""
        while True:
            try:
                # Collect system metrics
                await self._collect_system_metrics()
                
                # Run health checks
                health_results = await self.health_checker.run_all_health_checks()
                await self._store_health_results(health_results)
                
                # Check for alerts
                await self._check_alerts(health_results)
                
                # Wait for next iteration
                await asyncio.sleep(30)  # Run every 30 seconds
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(30)
    
    async def _collect_system_metrics(self):
        """Collect and update system metrics"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            self.metrics.system_cpu_usage.set(cpu_percent)
            
            # Memory usage
            memory = psutil.virtual_memory()
            self.metrics.system_memory_usage.set(memory.percent)
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            self.metrics.system_disk_usage.set(disk_percent)
            
            # Database connections (if available)
            try:
                async with get_database_session() as session:
                    pool = session.get_bind().pool
                    self.metrics.database_connections_active.set(pool.checkedout())
                    
                    # Update active agents count
                    result = await session.execute(text("SELECT count(*) FROM agents WHERE status = 'active'"))
                    active_count = result.scalar() or 0
                    self.metrics.active_agents.set(active_count)
            except Exception as e:
                self.logger.warning(f"Could not collect database/business metrics: {e}")
            
        except Exception as e:
            self.logger.error(f"Error collecting system metrics: {e}")
    
    async def _store_health_results(self, health_results: Dict[str, HealthCheckResult]):
        """Store health check results in Redis"""
        try:
            if not self.redis_client:
                return
            
            for name, result in health_results.items():
                key = f"health_check:{name}"
                data = {
                    'status': result.status.value,
                    'duration_ms': str(result.duration_ms),
                    'timestamp': result.timestamp.isoformat(),
                    'details': json.dumps(result.details) if result.details else "",
                    'error': result.error or ""
                }
                
                await self.redis_client.hset(key, mapping=data)
                await self.redis_client.expire(key, 3600)  # Expire after 1 hour
                
        except Exception as e:
            self.logger.error(f"Error storing health results: {e}")
    
    async def _check_alerts(self, health_results: Dict[str, HealthCheckResult]):
        """Check for alert conditions"""
        try:
            alerts = []
            
            # Check system resource alerts
            system_result = health_results.get('system_resources')
            if system_result and system_result.details:
                details = system_result.details
                
                if details.get('cpu_percent', 0) > self.alert_thresholds['cpu_usage']:
                    alerts.append({
                        'type': 'system',
                        'severity': 'warning',
                        'message': f"High CPU usage: {details['cpu_percent']:.1f}%",
                        'threshold': self.alert_thresholds['cpu_usage']
                    })
                
                if details.get('memory_percent', 0) > self.alert_thresholds['memory_usage']:
                    alerts.append({
                        'type': 'system',
                        'severity': 'warning',
                        'message': f"High memory usage: {details['memory_percent']:.1f}%",
                        'threshold': self.alert_thresholds['memory_usage']
                    })
                
                if details.get('disk_percent', 0) > self.alert_thresholds['disk_usage']:
                    alerts.append({
                        'type': 'system',
                        'severity': 'critical',
                        'message': f"High disk usage: {details['disk_percent']:.1f}%",
                        'threshold': self.alert_thresholds['disk_usage']
                    })
            
            # Check database performance alerts
            db_result = health_results.get('database')
            if db_result and db_result.details:
                query_time = db_result.details.get('query_time_ms', 0)
                if query_time > self.alert_thresholds['database_query_time']:
                    alerts.append({
                        'type': 'database',
                        'severity': 'warning',
                        'message': f"Slow database queries: {query_time:.1f}ms",
                        'threshold': self.alert_thresholds['database_query_time']
                    })
            
            # Store alerts
            if alerts:
                await self._store_alerts(alerts)
                
        except Exception as e:
            self.logger.error(f"Error checking alerts: {e}")
    
    async def _store_alerts(self, alerts: List[Dict[str, Any]]):
        """Store alerts in Redis"""
        try:
            if not self.redis_client:
                return
            
            for alert in alerts:
                alert_id = f"alert:{int(time.time())}:{hash(alert['message'])}"
                alert_data = {
                    **alert,
                    'timestamp': datetime.utcnow().isoformat(),
                    'acknowledged': "0"
                }
                
                await self.redis_client.hset(alert_id, mapping=alert_data)
                await self.redis_client.expire(alert_id, 86400)  # Expire after 24 hours
                
                # Add to active alerts list
                await self.redis_client.lpush('active_alerts', alert_id)
                await self.redis_client.ltrim('active_alerts', 0, 99)  # Keep last 100 alerts
                
                self.logger.warning(f"Alert triggered: {alert['message']}")
                
        except Exception as e:
            self.logger.error(f"Error storing alerts: {e}")
    
    def get_metrics_data(self) -> str:
        """Get Prometheus metrics data"""
        return generate_latest(self.metrics.registry).decode('utf-8')
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get current system status"""
        health_results = await self.health_checker.run_all_health_checks()
        
        # Determine overall status
        statuses = [result.status for result in health_results.values()]
        if HealthStatus.UNHEALTHY in statuses:
            overall_status = HealthStatus.UNHEALTHY
        elif HealthStatus.DEGRADED in statuses:
            overall_status = HealthStatus.DEGRADED
        else:
            overall_status = HealthStatus.HEALTHY
        
        return {
            'overall_status': overall_status.value,
            'timestamp': datetime.utcnow().isoformat(),
            'health_checks': {
                name: {
                    'status': result.status.value,
                    'duration_ms': result.duration_ms,
                    'error': result.error,
                    'details': result.details
                }
                for name, result in health_results.items()
            }
        }
    
    async def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get active alerts"""
        try:
            if not self.redis_client:
                return []
            
            alert_ids = await self.redis_client.lrange('active_alerts', 0, -1)
            alerts = []
            
            for alert_id in alert_ids:
                alert_data = await self.redis_client.hgetall(alert_id)
                if alert_data:
                    alerts.append(alert_data)
            
            return alerts
            
        except Exception as e:
            self.logger.error(f"Error getting active alerts: {e}")
            return []

    async def get_dashboard_statistics(self) -> Dict[str, Any]:
        """Get aggregated statistics for dashboard"""
        try:
            from ..services.agent_service import agent_service
            # Import tools and workflows services when available
            # from ..services.tool_service import tool_service
            
            # Get agent stats
            async with get_database_session() as session:
                # This is a placeholder until we have direct service access or DB counts
                # implementing basic counts via direct DB queries for now
                
                # Agents count
                result = await session.execute(text("SELECT count(*), status FROM agents GROUP BY status"))
                agent_rows = result.fetchall()
                
                total_agents = sum(row[0] for row in agent_rows)
                active_agents = sum(row[0] for row in agent_rows if row[1] == 'active')
                
                # Tools count (placeholder until tool table/service is ready)
                # result = await session.execute(text("SELECT count(*) FROM tools"))
                # total_tools = result.scalar() or 0
                total_tools = 0 
                
                # Workflows count (placeholder)
                # result = await session.execute(text("SELECT count(*), status FROM workflows GROUP BY status"))
                # workflow_rows = result.fetchall()
                # total_workflows = sum(row[0] for row in workflow_rows)
                total_workflows = 0
                active_workflows = 0
                
            return {
                "agents": {
                    "total": total_agents,
                    "active": active_agents,
                    "inactive": total_agents - active_agents
                },
                "tools": {
                    "total": total_tools,
                    "available": total_tools # Assuming all are available for now
                },
                "workflows": {
                    "total": total_workflows,
                    "active": active_workflows,
                    "completed": total_workflows - active_workflows
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error getting dashboard statistics: {e}")
            return {
                "agents": {"total": 0, "active": 0, "inactive": 0},
                "tools": {"total": 0, "available": 0},
                "workflows": {"total": 0, "active": 0, "completed": 0}
            }
    
    async def get_metrics_history(self, metric_name: str, start_time: int, end_time: int, step: str = "30s") -> List[Dict[str, Any]]:
        """
        Query Prometheus for historical metric data
        
        Args:
            metric_name: Name of the Prometheus metric
            start_time: Start timestamp (unix epoch)
            end_time: End timestamp (unix epoch)
            step: Query resolution step
        """
        import httpx
        
        # Map internal metric names to Prometheus query names
        metric_map = {
            'cpu_usage': 'system_cpu_usage_percent',
            'memory_usage': 'system_memory_usage_percent',
            'active_agents': 'active_agents_gauge'
        }
        
        query = metric_map.get(metric_name, metric_name)
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    'http://prometheus:9090/api/v1/query_range',
                    params={
                        'query': query,
                        'start': start_time,
                        'end': end_time,
                        'step': step
                    },
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data['status'] == 'success' and data['data']['result']:
                        # Extract values from the first result series
                        # Prometheus returns [timestamp, value]
                        values = data['data']['result'][0]['values']
                        return [
                            {'timestamp': int(v[0]), 'value': float(v[1])}
                            for v in values
                        ]
                        
            return []
            
        except Exception as e:
            self.logger.error(f"Error querying Prometheus history: {e}")
            return []



# Global monitoring service instance
monitoring_service = MonitoringService()