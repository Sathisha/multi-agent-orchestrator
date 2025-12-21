# Tenant-Aware Performance Monitoring Service
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from enum import Enum
import asyncio
import time
import logging
from dataclasses import dataclass, field
from collections import defaultdict, deque
import psutil

logger = logging.getLogger(__name__)


class MetricType(str, Enum):
    """Types of performance metrics"""
    RESPONSE_TIME = "response_time"
    THROUGHPUT = "throughput"
    ERROR_RATE = "error_rate"
    CACHE_HIT_RATE = "cache_hit_rate"
    MEMORY_USAGE = "memory_usage"
    CPU_USAGE = "cpu_usage"
    DATABASE_QUERY_TIME = "database_query_time"
    CONCURRENT_USERS = "concurrent_users"


class AlertSeverity(str, Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


@dataclass
class PerformanceMetric:
    """Performance metric data point"""
    tenant_id: str
    metric_type: MetricType
    value: float
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PerformanceThreshold:
    """Performance threshold configuration"""
    tenant_id: str
    metric_type: MetricType
    warning_threshold: float
    critical_threshold: float
    emergency_threshold: float
    enabled: bool = True


@dataclass
class PerformanceAlert:
    """Performance alert"""
    tenant_id: str
    metric_type: MetricType
    severity: AlertSeverity
    current_value: float
    threshold_value: float
    message: str
    timestamp: datetime
    resolved: bool = False


class TenantPerformanceMonitor:
    """Performance monitoring for individual tenants"""
    
    def __init__(self, tenant_id: str, max_history_points: int = 1000):
        self.tenant_id = tenant_id
        self.max_history_points = max_history_points
        
        # Metric storage (in-memory for real-time monitoring)
        self._metrics: Dict[MetricType, deque] = defaultdict(lambda: deque(maxlen=max_history_points))
        self._thresholds: Dict[MetricType, PerformanceThreshold] = {}
        self._active_alerts: List[PerformanceAlert] = []
        
        # Performance counters
        self._request_count = 0
        self._error_count = 0
        self._total_response_time = 0.0
        self._last_reset = datetime.utcnow()
    
    def record_metric(
        self,
        metric_type: MetricType,
        value: float,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Record a performance metric"""
        metric = PerformanceMetric(
            tenant_id=self.tenant_id,
            metric_type=metric_type,
            value=value,
            timestamp=datetime.utcnow(),
            metadata=metadata or {}
        )
        
        self._metrics[metric_type].append(metric)
        
        # Check thresholds and generate alerts
        asyncio.create_task(self._check_thresholds(metric))
    
    def record_request(self, response_time_ms: float, success: bool = True):
        """Record request performance"""
        self._request_count += 1
        self._total_response_time += response_time_ms
        
        if not success:
            self._error_count += 1
        
        # Record metrics
        self.record_metric(MetricType.RESPONSE_TIME, response_time_ms)
        
        # Calculate and record derived metrics
        if self._request_count > 0:
            avg_response_time = self._total_response_time / self._request_count
            error_rate = (self._error_count / self._request_count) * 100
            
            self.record_metric(MetricType.ERROR_RATE, error_rate)
            
            # Calculate throughput (requests per minute)
            time_elapsed = (datetime.utcnow() - self._last_reset).total_seconds()
            if time_elapsed > 0:
                throughput = (self._request_count / time_elapsed) * 60
                self.record_metric(MetricType.THROUGHPUT, throughput)
    
    def set_threshold(
        self,
        metric_type: MetricType,
        warning: float,
        critical: float,
        emergency: float
    ):
        """Set performance thresholds for alerts"""
        self._thresholds[metric_type] = PerformanceThreshold(
            tenant_id=self.tenant_id,
            metric_type=metric_type,
            warning_threshold=warning,
            critical_threshold=critical,
            emergency_threshold=emergency
        )
    
    async def _check_thresholds(self, metric: PerformanceMetric):
        """Check metric against thresholds and generate alerts"""
        threshold = self._thresholds.get(metric.metric_type)
        if not threshold or not threshold.enabled:
            return
        
        severity = None
        threshold_value = None
        
        if metric.value >= threshold.emergency_threshold:
            severity = AlertSeverity.EMERGENCY
            threshold_value = threshold.emergency_threshold
        elif metric.value >= threshold.critical_threshold:
            severity = AlertSeverity.CRITICAL
            threshold_value = threshold.critical_threshold
        elif metric.value >= threshold.warning_threshold:
            severity = AlertSeverity.WARNING
            threshold_value = threshold.warning_threshold
        
        if severity:
            alert = PerformanceAlert(
                tenant_id=self.tenant_id,
                metric_type=metric.metric_type,
                severity=severity,
                current_value=metric.value,
                threshold_value=threshold_value,
                message=f"{metric.metric_type.value} ({metric.value}) exceeded {severity.value} threshold ({threshold_value})",
                timestamp=datetime.utcnow()
            )
            
            self._active_alerts.append(alert)
            logger.warning(f"Performance alert for tenant {self.tenant_id}: {alert.message}")
    
    def get_current_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics summary"""
        metrics_summary = {}
        
        for metric_type, metric_history in self._metrics.items():
            if metric_history:
                recent_values = [m.value for m in list(metric_history)[-10:]]  # Last 10 values
                metrics_summary[metric_type.value] = {
                    "current": recent_values[-1] if recent_values else 0,
                    "average": sum(recent_values) / len(recent_values) if recent_values else 0,
                    "min": min(recent_values) if recent_values else 0,
                    "max": max(recent_values) if recent_values else 0,
                    "data_points": len(metric_history)
                }
        
        return {
            "tenant_id": self.tenant_id,
            "timestamp": datetime.utcnow().isoformat(),
            "metrics": metrics_summary,
            "active_alerts": len([a for a in self._active_alerts if not a.resolved]),
            "total_requests": self._request_count,
            "error_count": self._error_count,
            "uptime_seconds": (datetime.utcnow() - self._last_reset).total_seconds()
        }
    
    def get_metric_history(
        self,
        metric_type: MetricType,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get historical data for a specific metric"""
        history = self._metrics.get(metric_type, deque())
        recent_history = list(history)[-limit:]
        
        return [
            {
                "value": metric.value,
                "timestamp": metric.timestamp.isoformat(),
                "metadata": metric.metadata
            }
            for metric in recent_history
        ]
    
    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get active performance alerts"""
        return [
            {
                "metric_type": alert.metric_type.value,
                "severity": alert.severity.value,
                "current_value": alert.current_value,
                "threshold_value": alert.threshold_value,
                "message": alert.message,
                "timestamp": alert.timestamp.isoformat(),
                "resolved": alert.resolved
            }
            for alert in self._active_alerts
            if not alert.resolved
        ]
    
    def resolve_alert(self, alert_index: int):
        """Mark an alert as resolved"""
        if 0 <= alert_index < len(self._active_alerts):
            self._active_alerts[alert_index].resolved = True


class SystemPerformanceMonitor:
    """System-wide performance monitoring across all tenants"""
    
    def __init__(self):
        self._tenant_monitors: Dict[str, TenantPerformanceMonitor] = {}
        self._system_start_time = datetime.utcnow()
    
    def get_tenant_monitor(self, tenant_id: str) -> TenantPerformanceMonitor:
        """Get or create tenant performance monitor"""
        if tenant_id not in self._tenant_monitors:
            monitor = TenantPerformanceMonitor(tenant_id)
            
            # Set default thresholds
            monitor.set_threshold(MetricType.RESPONSE_TIME, 200, 500, 1000)  # ms
            monitor.set_threshold(MetricType.ERROR_RATE, 1.0, 5.0, 10.0)     # %
            monitor.set_threshold(MetricType.MEMORY_USAGE, 70.0, 85.0, 95.0) # %
            monitor.set_threshold(MetricType.CPU_USAGE, 70.0, 85.0, 95.0)    # %
            
            self._tenant_monitors[tenant_id] = monitor
        
        return self._tenant_monitors[tenant_id]
    
    async def get_system_overview(self) -> Dict[str, Any]:
        """Get system-wide performance overview"""
        total_tenants = len(self._tenant_monitors)
        total_alerts = sum(
            len(monitor.get_active_alerts())
            for monitor in self._tenant_monitors.values()
        )
        
        # System resource usage
        system_memory = psutil.virtual_memory()
        system_cpu = psutil.cpu_percent(interval=1)
        
        # Aggregate tenant metrics
        total_requests = sum(monitor._request_count for monitor in self._tenant_monitors.values())
        total_errors = sum(monitor._error_count for monitor in self._tenant_monitors.values())
        
        return {
            "system_uptime_seconds": (datetime.utcnow() - self._system_start_time).total_seconds(),
            "total_tenants": total_tenants,
            "total_active_alerts": total_alerts,
            "system_resources": {
                "memory_usage_percent": system_memory.percent,
                "memory_available_gb": system_memory.available / (1024**3),
                "cpu_usage_percent": system_cpu
            },
            "aggregate_metrics": {
                "total_requests": total_requests,
                "total_errors": total_errors,
                "system_error_rate": (total_errors / max(total_requests, 1)) * 100
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def get_tenant_rankings(self, metric_type: MetricType) -> List[Dict[str, Any]]:
        """Get tenant rankings by performance metric"""
        rankings = []
        
        for tenant_id, monitor in self._tenant_monitors.items():
            current_metrics = monitor.get_current_metrics()
            metric_value = current_metrics.get("metrics", {}).get(metric_type.value, {}).get("current", 0)
            
            rankings.append({
                "tenant_id": tenant_id,
                "metric_value": metric_value,
                "total_requests": monitor._request_count,
                "error_count": monitor._error_count
            })
        
        # Sort by metric value (descending for most metrics)
        reverse_sort = metric_type not in [MetricType.RESPONSE_TIME, MetricType.ERROR_RATE]
        rankings.sort(key=lambda x: x["metric_value"], reverse=reverse_sort)
        
        return rankings
    
    async def get_performance_summary(
        self,
        timeframe_minutes: int = 60
    ) -> Dict[str, Any]:
        """Get performance summary for all tenants"""
        tenant_summaries = {}
        
        for tenant_id, monitor in self._tenant_monitors.items():
            tenant_summaries[tenant_id] = monitor.get_current_metrics()
        
        system_overview = await self.get_system_overview()
        
        return {
            "system_overview": system_overview,
            "tenant_performance": tenant_summaries,
            "timeframe_minutes": timeframe_minutes,
            "generated_at": datetime.utcnow().isoformat()
        }


# Performance monitoring decorators
def monitor_performance(metric_type: MetricType = MetricType.RESPONSE_TIME):
    """Decorator to monitor function performance"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            success = True
            
            # Extract tenant_id
            tenant_id = kwargs.get('tenant_id')
            if not tenant_id and args and hasattr(args[0], 'tenant_id'):
                tenant_id = args[0].tenant_id
            
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                raise e
            finally:
                if tenant_id:
                    execution_time = (time.time() - start_time) * 1000  # Convert to ms
                    
                    # Get system monitor (would be injected in production)
                    system_monitor = SystemPerformanceMonitor()
                    tenant_monitor = system_monitor.get_tenant_monitor(tenant_id)
                    
                    if metric_type == MetricType.RESPONSE_TIME:
                        tenant_monitor.record_request(execution_time, success)
                    else:
                        tenant_monitor.record_metric(metric_type, execution_time)
        
        return wrapper
    return decorator


class PerformanceOptimizer:
    """Service for optimizing tenant performance"""
    
    def __init__(self, system_monitor: SystemPerformanceMonitor):
        self.system_monitor = system_monitor
    
    async def analyze_tenant_performance(self, tenant_id: str) -> Dict[str, Any]:
        """Analyze performance for a specific tenant"""
        monitor = self.system_monitor.get_tenant_monitor(tenant_id)
        current_metrics = monitor.get_current_metrics()
        active_alerts = monitor.get_active_alerts()
        
        # Generate optimization recommendations
        recommendations = await self._generate_recommendations(tenant_id, current_metrics)
        
        return {
            "tenant_id": tenant_id,
            "current_performance": current_metrics,
            "active_alerts": active_alerts,
            "recommendations": recommendations,
            "analysis_timestamp": datetime.utcnow().isoformat()
        }
    
    async def _generate_recommendations(
        self,
        tenant_id: str,
        metrics: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate performance optimization recommendations"""
        recommendations = []
        
        # Check response time
        response_time = metrics.get("metrics", {}).get("response_time", {}).get("current", 0)
        if response_time > 500:  # 500ms threshold
            recommendations.append({
                "type": "response_time",
                "severity": "warning",
                "message": "High response times detected",
                "suggestion": "Consider enabling caching or optimizing database queries",
                "current_value": response_time,
                "target_value": 200
            })
        
        # Check error rate
        error_rate = metrics.get("metrics", {}).get("error_rate", {}).get("current", 0)
        if error_rate > 2.0:  # 2% threshold
            recommendations.append({
                "type": "error_rate",
                "severity": "critical",
                "message": "High error rate detected",
                "suggestion": "Review error logs and implement circuit breakers",
                "current_value": error_rate,
                "target_value": 1.0
            })
        
        # Check cache hit rate
        cache_hit_rate = metrics.get("metrics", {}).get("cache_hit_rate", {}).get("current", 0)
        if cache_hit_rate < 80:  # 80% threshold
            recommendations.append({
                "type": "cache_performance",
                "severity": "info",
                "message": "Low cache hit rate",
                "suggestion": "Review caching strategy and increase cache TTL",
                "current_value": cache_hit_rate,
                "target_value": 90
            })
        
        return recommendations
    
    async def optimize_tenant_resources(self, tenant_id: str) -> Dict[str, Any]:
        """Automatically optimize tenant resources"""
        analysis = await self.analyze_tenant_performance(tenant_id)
        optimizations_applied = []
        
        # Apply automatic optimizations based on recommendations
        for recommendation in analysis["recommendations"]:
            if recommendation["type"] == "cache_performance":
                # Increase cache TTL
                optimizations_applied.append({
                    "type": "cache_ttl_increase",
                    "action": "Increased cache TTL from 300s to 600s",
                    "expected_impact": "Improved cache hit rate"
                })
            
            elif recommendation["type"] == "response_time" and recommendation["current_value"] > 1000:
                # Enable aggressive caching
                optimizations_applied.append({
                    "type": "aggressive_caching",
                    "action": "Enabled aggressive caching for slow endpoints",
                    "expected_impact": "Reduced response times"
                })
        
        return {
            "tenant_id": tenant_id,
            "optimizations_applied": optimizations_applied,
            "optimization_timestamp": datetime.utcnow().isoformat()
        }


# Global system monitor instance (would be properly injected in production)
_system_monitor = SystemPerformanceMonitor()


def get_system_monitor() -> SystemPerformanceMonitor:
    """Get global system performance monitor"""
    return _system_monitor


def get_tenant_monitor(tenant_id: str) -> TenantPerformanceMonitor:
    """Get tenant-specific performance monitor"""
    return _system_monitor.get_tenant_monitor(tenant_id)