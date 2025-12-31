"""
Monitoring API Endpoints

This module provides REST API endpoints for monitoring and observability:
- Health checks and system status
- Metrics collection and export
- Alert management
- Performance monitoring
"""

from fastapi import APIRouter, HTTPException, Response, Depends
from typing import Dict, Any, List
import logging

from ..services.monitoring import monitoring_service, HealthStatus
from ..services.auth import get_current_user
from ..models.user import User


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/monitoring", tags=["monitoring"])


@router.get("/health")
async def get_health_status():
    """
    Get overall system health status
    
    Returns comprehensive health information including:
    - Overall system status
    - Individual component health checks
    - Performance metrics
    - Error details if any
    """
    try:
        status = await monitoring_service.get_system_status()
        return status
    except Exception as e:
        logger.error(f"Error getting health status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get health status")


@router.get("/health/{component}")
async def get_component_health(component: str):
    """
    Get health status for a specific component
    
    Args:
        component: Component name (database, redis, system_resources, etc.)
    """
    try:
        result = await monitoring_service.health_checker.run_health_check(component)
        
        return {
            'name': result.name,
            'status': result.status.value,
            'duration_ms': result.duration_ms,
            'timestamp': result.timestamp.isoformat(),
            'details': result.details,
            'error': result.error
        }
    except Exception as e:
        logger.error(f"Error getting component health for {component}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get health status for {component}")


@router.get("/metrics")
async def get_metrics():
    """
    Get Prometheus metrics data
    
    Returns metrics in Prometheus format for scraping
    """
    try:
        metrics_data = monitoring_service.get_metrics_data()
        return Response(content=metrics_data, media_type="text/plain")
    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get metrics")


@router.get("/alerts")
async def get_active_alerts(current_user: User = Depends(get_current_user)):
    """
    Get active system alerts
    
    Requires authentication to view alerts
    """
    try:
        alerts = await monitoring_service.get_active_alerts()
        return {
            'alerts': alerts,
            'count': len(alerts)
        }
    except Exception as e:
        logger.error(f"Error getting active alerts: {e}")
        raise HTTPException(status_code=500, detail="Failed to get active alerts")


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str, current_user: User = Depends(get_current_user)):
    """
    Acknowledge an alert
    
    Args:
        alert_id: ID of the alert to acknowledge
    """
    try:
        # Update alert status in Redis
        if monitoring_service.redis_client:
            await monitoring_service.redis_client.hset(
                alert_id, 
                'acknowledged', 
                'true'
            )
            await monitoring_service.redis_client.hset(
                alert_id, 
                'acknowledged_by', 
                current_user.username
            )
            await monitoring_service.redis_client.hset(
                alert_id, 
                'acknowledged_at', 
                datetime.utcnow().isoformat()
            )
        
        return {"message": "Alert acknowledged successfully"}
    except Exception as e:
        logger.error(f"Error acknowledging alert {alert_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to acknowledge alert")


@router.get("/system/resources")
async def get_system_resources():
    """
    Get current system resource usage
    
    Returns CPU, memory, disk, and network statistics
    """
    try:
        result = await monitoring_service.health_checker.run_health_check('system_resources')
        
        if result.status == HealthStatus.UNHEALTHY:
            raise HTTPException(status_code=503, detail="System resources unhealthy")
        
        return {
            'status': result.status.value,
            'resources': result.details,
            'timestamp': result.timestamp.isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting system resources: {e}")
        raise HTTPException(status_code=500, detail="Failed to get system resources")


@router.get("/database/status")
async def get_database_status():
    """
    Get database connection and performance status
    """
    try:
        result = await monitoring_service.health_checker.run_health_check('database')
        
        return {
            'status': result.status.value,
            'connection_info': result.details,
            'duration_ms': result.duration_ms,
            'timestamp': result.timestamp.isoformat(),
            'error': result.error
        }
    except Exception as e:
        logger.error(f"Error getting database status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get database status")


@router.get("/cache/status")
async def get_cache_status():
    """
    Get Redis cache status and performance metrics
    """
    try:
        result = await monitoring_service.health_checker.run_health_check('redis')
        
        return {
            'status': result.status.value,
            'cache_info': result.details,
            'duration_ms': result.duration_ms,
            'timestamp': result.timestamp.isoformat(),
            'error': result.error
        }
    except Exception as e:
        logger.error(f"Error getting cache status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get cache status")


@router.get("/services/external")
async def get_external_services_status():
    """
    Get status of external services (Kong, Keycloak, etc.)
    """
    try:
        result = await monitoring_service.health_checker.run_health_check('external_services')
        
        return {
            'status': result.status.value,
            'services': result.details,
            'duration_ms': result.duration_ms,
            'timestamp': result.timestamp.isoformat(),
            'error': result.error
        }
    except Exception as e:
        logger.error(f"Error getting external services status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get external services status")


@router.get("/providers/llm")
async def get_llm_providers_status():
    """
    Get status of LLM providers (Ollama, OpenAI, etc.)
    """
    try:
        result = await monitoring_service.health_checker.run_health_check('llm_providers')
        
        return {
            'status': result.status.value,
            'providers': result.details,
            'duration_ms': result.duration_ms,
            'timestamp': result.timestamp.isoformat(),
            'error': result.error
        }
    except Exception as e:
        logger.error(f"Error getting LLM providers status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get LLM providers status")


@router.get("/performance/summary")
async def get_performance_summary(current_user: User = Depends(get_current_user)):
    """
    Get performance summary with key metrics
    
    Requires authentication to view performance data
    """
    try:
        # Get all health check results
        health_results = await monitoring_service.health_checker.run_all_health_checks()
        
        # Extract key performance metrics
        summary = {
            'timestamp': datetime.utcnow().isoformat(),
            'overall_health': 'healthy',
            'metrics': {}
        }
        
        # System resources
        if 'system_resources' in health_results:
            system_details = health_results['system_resources'].details or {}
            summary['metrics']['system'] = {
                'cpu_percent': system_details.get('cpu_percent', 0),
                'memory_percent': system_details.get('memory_percent', 0),
                'disk_percent': system_details.get('disk_percent', 0)
            }
        
        # Database performance
        if 'database' in health_results:
            db_details = health_results['database'].details or {}
            summary['metrics']['database'] = {
                'query_time_ms': db_details.get('query_time_ms', 0),
                'active_connections': db_details.get('checked_out_connections', 0),
                'pool_size': db_details.get('pool_size', 0)
            }
        
        # Cache performance
        if 'redis' in health_results:
            redis_details = health_results['redis'].details or {}
            summary['metrics']['cache'] = {
                'ping_time_ms': redis_details.get('ping_time_ms', 0),
                'used_memory_mb': redis_details.get('used_memory_mb', 0),
                'connected_clients': redis_details.get('connected_clients', 0)
            }
        
        # Determine overall health
        unhealthy_count = sum(1 for result in health_results.values() 
                            if result.status == HealthStatus.UNHEALTHY)
        degraded_count = sum(1 for result in health_results.values() 
                           if result.status == HealthStatus.DEGRADED)
        
        if unhealthy_count > 0:
            summary['overall_health'] = 'unhealthy'
        elif degraded_count > 0:
            summary['overall_health'] = 'degraded'
        
        return summary
        
    except Exception as e:
        logger.error(f"Error getting performance summary: {e}")
        raise HTTPException(status_code=500, detail="Failed to get performance summary")


# Add missing import
from datetime import datetime