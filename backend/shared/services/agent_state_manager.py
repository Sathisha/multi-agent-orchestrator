"""Agent State Management Service for tracking agent states and monitoring."""

import asyncio
import json
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Any, Optional, List, Set
from dataclasses import dataclass, asdict
import logging

import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func

from ..models.agent import Agent, AgentExecution, AgentStatus
from .base import BaseService


logger = logging.getLogger(__name__)


class AgentState(str, Enum):
    """Agent runtime states."""
    
    IDLE = "idle"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"
    MAINTENANCE = "maintenance"


@dataclass
class AgentRuntimeInfo:
    """Runtime information for an agent."""
    
    agent_id: str
    tenant_id: str
    state: AgentState
    last_execution_id: Optional[str] = None
    active_executions: int = 0
    total_executions: int = 0
    last_activity: Optional[datetime] = None
    error_count: int = 0
    last_error: Optional[str] = None
    resource_usage: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.resource_usage is None:
            self.resource_usage = {}
        if self.last_activity is None:
            self.last_activity = datetime.utcnow()


class AgentStateManager(BaseService):
    """Service for managing agent runtime states and monitoring."""
    
    def __init__(self, session: AsyncSession, tenant_id: str, redis_client: Optional[redis.Redis] = None):
        super().__init__(session, Agent, tenant_id)
        self.redis_client = redis_client or redis.Redis(host='redis', decode_responses=True)
        self.state_cache: Dict[str, AgentRuntimeInfo] = {}
        self.monitoring_enabled = True
        self.state_ttl = 3600  # 1 hour TTL for state data
        
    async def initialize_agent_state(self, agent_id: str) -> AgentRuntimeInfo:
        """Initialize runtime state for an agent."""
        # Get agent from database
        agent = await self.get_by_id(agent_id)
        if not agent:
            raise ValueError(f"Agent {agent_id} not found")
        
        # Create runtime info
        runtime_info = AgentRuntimeInfo(
            agent_id=agent_id,
            tenant_id=self.tenant_id,
            state=AgentState.IDLE if agent.status == AgentStatus.ACTIVE else AgentState.MAINTENANCE,
            last_activity=datetime.utcnow()
        )
        
        # Store in cache and Redis
        await self._store_agent_state(runtime_info)
        
        logger.info(f"Initialized state for agent {agent_id}: {runtime_info.state}")
        return runtime_info
    
    async def update_agent_state(
        self,
        agent_id: str,
        state: AgentState,
        execution_id: Optional[str] = None,
        error_message: Optional[str] = None,
        resource_usage: Optional[Dict[str, Any]] = None
    ) -> Optional[AgentRuntimeInfo]:
        """Update agent runtime state."""
        runtime_info = await self.get_agent_state(agent_id)
        if not runtime_info:
            runtime_info = await self.initialize_agent_state(agent_id)
        
        # Update state information
        old_state = runtime_info.state
        runtime_info.state = state
        runtime_info.last_activity = datetime.utcnow()
        
        if execution_id:
            runtime_info.last_execution_id = execution_id
        
        if error_message:
            runtime_info.error_count += 1
            runtime_info.last_error = error_message
            runtime_info.state = AgentState.ERROR
        
        if resource_usage:
            runtime_info.resource_usage.update(resource_usage)
        
        # Update execution counts based on state transitions
        if old_state != AgentState.RUNNING and state == AgentState.RUNNING:
            runtime_info.active_executions += 1
            runtime_info.total_executions += 1
        elif old_state == AgentState.RUNNING and state != AgentState.RUNNING:
            runtime_info.active_executions = max(0, runtime_info.active_executions - 1)
        
        # Store updated state
        await self._store_agent_state(runtime_info)
        
        logger.debug(f"Updated agent {agent_id} state: {old_state} -> {state}")
        return runtime_info
    
    async def get_agent_state(self, agent_id: str) -> Optional[AgentRuntimeInfo]:
        """Get current agent runtime state."""
        # Check cache first
        if agent_id in self.state_cache:
            return self.state_cache[agent_id]
        
        # Check Redis
        state_key = self._get_state_key(agent_id)
        state_data = await self.redis_client.get(state_key)
        
        if state_data:
            try:
                data = json.loads(state_data)
                # Convert datetime strings back to datetime objects
                if data.get('last_activity'):
                    data['last_activity'] = datetime.fromisoformat(data['last_activity'])
                
                runtime_info = AgentRuntimeInfo(**data)
                self.state_cache[agent_id] = runtime_info
                return runtime_info
            except (json.JSONDecodeError, TypeError) as e:
                logger.error(f"Failed to deserialize agent state for {agent_id}: {e}")
        
        return None
    
    async def list_agent_states(
        self,
        state_filter: Optional[AgentState] = None,
        active_only: bool = False
    ) -> List[AgentRuntimeInfo]:
        """List agent states for the tenant."""
        # Get all agent IDs for the tenant
        stmt = select(Agent.id).where(Agent.tenant_id == self.tenant_id)
        if active_only:
            stmt = stmt.where(Agent.status == AgentStatus.ACTIVE)
        
        result = await self.session.execute(stmt)
        agent_ids = [row[0] for row in result.fetchall()]
        
        # Get states for all agents
        states = []
        for agent_id in agent_ids:
            state = await self.get_agent_state(agent_id)
            if state:
                if state_filter is None or state.state == state_filter:
                    states.append(state)
        
        return states
    
    async def get_agent_health_status(self, agent_id: str) -> Dict[str, Any]:
        """Get comprehensive health status for an agent."""
        runtime_info = await self.get_agent_state(agent_id)
        if not runtime_info:
            return {"status": "unknown", "message": "Agent state not found"}
        
        # Calculate health metrics
        now = datetime.utcnow()
        last_activity_minutes = (now - runtime_info.last_activity).total_seconds() / 60
        
        # Determine health status
        if runtime_info.state == AgentState.ERROR:
            health_status = "unhealthy"
            message = f"Agent in error state: {runtime_info.last_error}"
        elif runtime_info.state == AgentState.MAINTENANCE:
            health_status = "maintenance"
            message = "Agent is in maintenance mode"
        elif last_activity_minutes > 60:  # No activity for over an hour
            health_status = "stale"
            message = f"No activity for {last_activity_minutes:.1f} minutes"
        elif runtime_info.error_count > 10:  # High error rate
            health_status = "degraded"
            message = f"High error count: {runtime_info.error_count}"
        else:
            health_status = "healthy"
            message = "Agent is operating normally"
        
        return {
            "agent_id": agent_id,
            "status": health_status,
            "message": message,
            "state": runtime_info.state.value,
            "active_executions": runtime_info.active_executions,
            "total_executions": runtime_info.total_executions,
            "error_count": runtime_info.error_count,
            "last_activity_minutes": last_activity_minutes,
            "resource_usage": runtime_info.resource_usage
        }
    
    async def cleanup_stale_states(self, max_age_hours: int = 24) -> int:
        """Clean up stale agent states."""
        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
        cleaned_count = 0
        
        # Get all states for the tenant
        states = await self.list_agent_states()
        
        for state in states:
            if state.last_activity < cutoff_time:
                await self._remove_agent_state(state.agent_id)
                cleaned_count += 1
        
        logger.info(f"Cleaned up {cleaned_count} stale agent states")
        return cleaned_count
    
    async def get_tenant_statistics(self) -> Dict[str, Any]:
        """Get overall statistics for the tenant."""
        states = await self.list_agent_states()
        
        # Count states
        state_counts = {}
        for state_enum in AgentState:
            state_counts[state_enum.value] = 0
        
        total_active_executions = 0
        total_executions = 0
        total_errors = 0
        
        for state in states:
            state_counts[state.state.value] += 1
            total_active_executions += state.active_executions
            total_executions += state.total_executions
            total_errors += state.error_count
        
        return {
            "tenant_id": self.tenant_id,
            "total_agents": len(states),
            "state_distribution": state_counts,
            "total_active_executions": total_active_executions,
            "total_executions": total_executions,
            "total_errors": total_errors,
            "error_rate": total_errors / max(total_executions, 1)
        }
    
    async def start_monitoring(self):
        """Start background monitoring for agent states."""
        if not self.monitoring_enabled:
            return
        
        # Start monitoring task
        asyncio.create_task(self._monitoring_loop())
        logger.info(f"Started agent state monitoring for tenant {self.tenant_id}")
    
    async def _monitoring_loop(self):
        """Background monitoring loop."""
        while self.monitoring_enabled:
            try:
                # Clean up stale states every hour
                await self.cleanup_stale_states(max_age_hours=2)
                
                # Update statistics
                stats = await self.get_tenant_statistics()
                await self._store_tenant_stats(stats)
                
                # Wait 1 hour before next cleanup
                await asyncio.sleep(3600)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in agent state monitoring loop: {str(e)}")
                await asyncio.sleep(300)  # Wait 5 minutes before retrying
    
    async def _store_agent_state(self, runtime_info: AgentRuntimeInfo):
        """Store agent state in cache and Redis."""
        # Update local cache
        self.state_cache[runtime_info.agent_id] = runtime_info
        
        # Store in Redis with TTL
        state_key = self._get_state_key(runtime_info.agent_id)
        
        # Convert to JSON-serializable format
        data = asdict(runtime_info)
        if data['last_activity']:
            data['last_activity'] = data['last_activity'].isoformat()
        
        await self.redis_client.setex(
            state_key,
            self.state_ttl,
            json.dumps(data, default=str)
        )
    
    async def _remove_agent_state(self, agent_id: str):
        """Remove agent state from cache and Redis."""
        # Remove from cache
        if agent_id in self.state_cache:
            del self.state_cache[agent_id]
        
        # Remove from Redis
        state_key = self._get_state_key(agent_id)
        await self.redis_client.delete(state_key)
    
    async def _store_tenant_stats(self, stats: Dict[str, Any]):
        """Store tenant statistics in Redis."""
        stats_key = f"agent_stats:tenant:{self.tenant_id}"
        await self.redis_client.setex(
            stats_key,
            300,  # 5 minute TTL
            json.dumps(stats, default=str)
        )
    
    def _get_state_key(self, agent_id: str) -> str:
        """Get Redis key for agent state."""
        return f"agent_state:tenant:{self.tenant_id}:agent:{agent_id}"


class GlobalAgentStateManager:
    """Global manager for agent states across all tenants."""
    
    def __init__(self):
        self.tenant_managers: Dict[str, AgentStateManager] = {}
        self.redis_client = redis.Redis(host='redis', decode_responses=True)
        self.monitoring_task: Optional[asyncio.Task] = None
    
    def get_manager(self, session: AsyncSession, tenant_id: str) -> AgentStateManager:
        """Get or create state manager for tenant."""
        if tenant_id not in self.tenant_managers:
            self.tenant_managers[tenant_id] = AgentStateManager(
                session, tenant_id, self.redis_client
            )
        return self.tenant_managers[tenant_id]
    
    async def start_global_monitoring(self):
        """Start global monitoring across all tenants."""
        if self.monitoring_task is None:
            self.monitoring_task = asyncio.create_task(self._global_monitoring_loop())
            logger.info("Started global agent state monitoring")
    
    async def stop_global_monitoring(self):
        """Stop global monitoring."""
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
            self.monitoring_task = None
            logger.info("Stopped global agent state monitoring")
    
    async def get_global_statistics(self) -> Dict[str, Any]:
        """Get statistics across all tenants."""
        total_agents = 0
        total_active_executions = 0
        total_executions = 0
        total_errors = 0
        tenant_count = len(self.tenant_managers)
        
        tenant_stats = {}
        
        for tenant_id, manager in self.tenant_managers.items():
            try:
                stats = await manager.get_tenant_statistics()
                tenant_stats[tenant_id] = stats
                
                total_agents += stats["total_agents"]
                total_active_executions += stats["total_active_executions"]
                total_executions += stats["total_executions"]
                total_errors += stats["total_errors"]
                
            except Exception as e:
                logger.error(f"Failed to get stats for tenant {tenant_id}: {e}")
        
        return {
            "total_tenants": tenant_count,
            "total_agents": total_agents,
            "total_active_executions": total_active_executions,
            "total_executions": total_executions,
            "total_errors": total_errors,
            "global_error_rate": total_errors / max(total_executions, 1),
            "tenant_stats": tenant_stats
        }
    
    async def _global_monitoring_loop(self):
        """Global monitoring loop."""
        while True:
            try:
                # Get global statistics
                stats = await self.get_global_statistics()
                
                # Store global stats
                await self.redis_client.setex(
                    "agent_stats:global",
                    300,  # 5 minute TTL
                    json.dumps(stats, default=str)
                )
                
                # Log summary
                logger.info(
                    f"Global agent stats: {stats['total_agents']} agents, "
                    f"{stats['total_active_executions']} active executions, "
                    f"{stats['global_error_rate']:.2%} error rate"
                )
                
                # Wait 5 minutes before next update
                await asyncio.sleep(300)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in global monitoring loop: {str(e)}")
                await asyncio.sleep(60)


# Global state manager instance
global_state_manager = GlobalAgentStateManager()