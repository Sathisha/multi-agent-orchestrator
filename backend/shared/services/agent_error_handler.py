"""Agent Error Handling and Recovery Service."""

import asyncio
import json
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, asdict
import logging
import traceback

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, update
import redis.asyncio as redis

from ..models.agent import Agent, AgentExecution
from .base import BaseService


logger = logging.getLogger(__name__)


class ErrorSeverity(str, Enum):
    """Error severity levels."""
    
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RecoveryAction(str, Enum):
    """Recovery action types."""
    
    RETRY = "retry"
    RESTART = "restart"
    FALLBACK = "fallback"
    ESCALATE = "escalate"
    IGNORE = "ignore"


@dataclass
class AgentError:
    """Agent error information."""
    
    error_id: str
    agent_id: str
    tenant_id: str
    execution_id: Optional[str]
    error_type: str
    error_message: str
    stack_trace: Optional[str]
    severity: ErrorSeverity
    timestamp: datetime
    context: Dict[str, Any]
    recovery_attempted: bool = False
    recovery_action: Optional[RecoveryAction] = None
    recovery_success: bool = False
    
    def __post_init__(self):
        if self.context is None:
            self.context = {}


class ErrorPattern:
    """Error pattern for matching and handling specific error types."""
    
    def __init__(
        self,
        pattern_id: str,
        error_type_pattern: str,
        message_pattern: str,
        severity: ErrorSeverity,
        recovery_action: RecoveryAction,
        max_retries: int = 3,
        backoff_seconds: int = 5
    ):
        self.pattern_id = pattern_id
        self.error_type_pattern = error_type_pattern
        self.message_pattern = message_pattern
        self.severity = severity
        self.recovery_action = recovery_action
        self.max_retries = max_retries
        self.backoff_seconds = backoff_seconds
    
    def matches(self, error: AgentError) -> bool:
        """Check if error matches this pattern."""
        import re
        
        type_match = re.search(self.error_type_pattern, error.error_type, re.IGNORECASE)
        message_match = re.search(self.message_pattern, error.error_message, re.IGNORECASE)
        
        return bool(type_match and message_match)


class AgentErrorHandler(BaseService):
    """Service for handling agent errors and implementing recovery strategies."""
    
    def __init__(self, session: AsyncSession, tenant_id: str, redis_client: Optional[redis.Redis] = None):
        super().__init__(session, AgentExecution, tenant_id)
        self.redis_client = redis_client or redis.Redis(host='redis', decode_responses=True)
        self.error_patterns = self._initialize_error_patterns()
        self.recovery_callbacks: Dict[RecoveryAction, Callable] = {}
        self.error_cache_ttl = 3600  # 1 hour
        
    def _initialize_error_patterns(self) -> List[ErrorPattern]:
        """Initialize default error patterns."""
        return [
            # LLM Provider Errors
            ErrorPattern(
                pattern_id="llm_timeout",
                error_type_pattern="TimeoutError|asyncio.TimeoutError",
                message_pattern="timeout|timed out",
                severity=ErrorSeverity.MEDIUM,
                recovery_action=RecoveryAction.RETRY,
                max_retries=3,
                backoff_seconds=10
            ),
            ErrorPattern(
                pattern_id="llm_rate_limit",
                error_type_pattern="RateLimitError|HTTPException",
                message_pattern="rate limit|too many requests|429",
                severity=ErrorSeverity.MEDIUM,
                recovery_action=RecoveryAction.RETRY,
                max_retries=5,
                backoff_seconds=30
            ),
            ErrorPattern(
                pattern_id="llm_auth_error",
                error_type_pattern="AuthenticationError|HTTPException",
                message_pattern="authentication|unauthorized|401|403",
                severity=ErrorSeverity.HIGH,
                recovery_action=RecoveryAction.ESCALATE,
                max_retries=1
            ),
            
            # Memory Service Errors
            ErrorPattern(
                pattern_id="memory_connection",
                error_type_pattern="ConnectionError|RedisError",
                message_pattern="connection|redis|memory",
                severity=ErrorSeverity.MEDIUM,
                recovery_action=RecoveryAction.RETRY,
                max_retries=3,
                backoff_seconds=5
            ),
            
            # Guardrails Errors
            ErrorPattern(
                pattern_id="guardrails_violation",
                error_type_pattern="ValueError|ValidationError",
                message_pattern="validation failed|guardrail|inappropriate",
                severity=ErrorSeverity.HIGH,
                recovery_action=RecoveryAction.ESCALATE,
                max_retries=0
            ),
            
            # System Errors
            ErrorPattern(
                pattern_id="out_of_memory",
                error_type_pattern="MemoryError|OutOfMemoryError",
                message_pattern="memory|out of memory",
                severity=ErrorSeverity.CRITICAL,
                recovery_action=RecoveryAction.RESTART,
                max_retries=1
            ),
            ErrorPattern(
                pattern_id="database_error",
                error_type_pattern="DatabaseError|SQLAlchemyError",
                message_pattern="database|sql|connection",
                severity=ErrorSeverity.HIGH,
                recovery_action=RecoveryAction.RETRY,
                max_retries=3,
                backoff_seconds=10
            ),
            
            # Generic Fallback
            ErrorPattern(
                pattern_id="generic_error",
                error_type_pattern=".*",
                message_pattern=".*",
                severity=ErrorSeverity.LOW,
                recovery_action=RecoveryAction.RETRY,
                max_retries=2,
                backoff_seconds=5
            )
        ]
    
    async def handle_error(
        self,
        agent_id: str,
        error: Exception,
        execution_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> AgentError:
        """Handle an agent error with automatic recovery."""
        # Create error record
        error_id = f"error_{int(time.time() * 1000)}"
        agent_error = AgentError(
            error_id=error_id,
            agent_id=agent_id,
            tenant_id=self.tenant_id,
            execution_id=execution_id,
            error_type=type(error).__name__,
            error_message=str(error),
            stack_trace=traceback.format_exc(),
            severity=ErrorSeverity.LOW,  # Will be updated by pattern matching
            timestamp=datetime.utcnow(),
            context=context or {}
        )
        
        # Find matching error pattern
        matching_pattern = self._find_matching_pattern(agent_error)
        if matching_pattern:
            agent_error.severity = matching_pattern.severity
            agent_error.recovery_action = matching_pattern.recovery_action
        
        # Store error
        await self._store_error(agent_error)
        
        # Log error
        logger.error(
            f"Agent {agent_id} error: {agent_error.error_message}",
            extra={
                "error_id": error_id,
                "agent_id": agent_id,
                "execution_id": execution_id,
                "severity": agent_error.severity.value,
                "error_type": agent_error.error_type
            }
        )
        
        # Attempt recovery if pattern found
        if matching_pattern and agent_error.recovery_action != RecoveryAction.IGNORE:
            await self._attempt_recovery(agent_error, matching_pattern)
        
        return agent_error
    
    async def get_agent_error_history(
        self,
        agent_id: str,
        hours: int = 24,
        severity_filter: Optional[ErrorSeverity] = None
    ) -> List[AgentError]:
        """Get error history for an agent."""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        # Get errors from Redis
        pattern = f"agent_error:tenant:{self.tenant_id}:agent:{agent_id}:*"
        keys = await self.redis_client.keys(pattern)
        
        errors = []
        for key in keys:
            error_data = await self.redis_client.get(key)
            if error_data:
                try:
                    data = json.loads(error_data)
                    # Convert timestamp string back to datetime
                    data['timestamp'] = datetime.fromisoformat(data['timestamp'])
                    
                    error = AgentError(**data)
                    
                    # Filter by time and severity
                    if error.timestamp >= cutoff_time:
                        if severity_filter is None or error.severity == severity_filter:
                            errors.append(error)
                            
                except (json.JSONDecodeError, TypeError) as e:
                    logger.error(f"Failed to deserialize error data: {e}")
        
        # Sort by timestamp (newest first)
        errors.sort(key=lambda x: x.timestamp, reverse=True)
        return errors
    
    async def get_error_statistics(self, agent_id: str, hours: int = 24) -> Dict[str, Any]:
        """Get error statistics for an agent."""
        errors = await self.get_agent_error_history(agent_id, hours)
        
        # Count by severity
        severity_counts = {}
        for severity in ErrorSeverity:
            severity_counts[severity.value] = 0
        
        # Count by error type
        error_type_counts = {}
        recovery_success_count = 0
        
        for error in errors:
            severity_counts[error.severity.value] += 1
            
            error_type_counts[error.error_type] = error_type_counts.get(error.error_type, 0) + 1
            
            if error.recovery_attempted and error.recovery_success:
                recovery_success_count += 1
        
        return {
            "agent_id": agent_id,
            "time_period_hours": hours,
            "total_errors": len(errors),
            "severity_distribution": severity_counts,
            "error_type_distribution": error_type_counts,
            "recovery_attempts": sum(1 for e in errors if e.recovery_attempted),
            "recovery_successes": recovery_success_count,
            "recovery_success_rate": recovery_success_count / max(len(errors), 1)
        }
    
    async def cleanup_old_errors(self, max_age_hours: int = 168) -> int:  # 1 week default
        """Clean up old error records."""
        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
        
        # Get all error keys for the tenant
        pattern = f"agent_error:tenant:{self.tenant_id}:*"
        keys = await self.redis_client.keys(pattern)
        
        cleaned_count = 0
        for key in keys:
            error_data = await self.redis_client.get(key)
            if error_data:
                try:
                    data = json.loads(error_data)
                    timestamp = datetime.fromisoformat(data['timestamp'])
                    
                    if timestamp < cutoff_time:
                        await self.redis_client.delete(key)
                        cleaned_count += 1
                        
                except (json.JSONDecodeError, TypeError):
                    # Delete corrupted data
                    await self.redis_client.delete(key)
                    cleaned_count += 1
        
        logger.info(f"Cleaned up {cleaned_count} old error records")
        return cleaned_count
    
    def register_recovery_callback(self, action: RecoveryAction, callback: Callable):
        """Register a callback for a specific recovery action."""
        self.recovery_callbacks[action] = callback
    
    def add_error_pattern(self, pattern: ErrorPattern):
        """Add a custom error pattern."""
        # Insert at the beginning so custom patterns take precedence
        self.error_patterns.insert(0, pattern)
    
    def _find_matching_pattern(self, error: AgentError) -> Optional[ErrorPattern]:
        """Find the first matching error pattern."""
        for pattern in self.error_patterns:
            if pattern.matches(error):
                return pattern
        return None
    
    async def _attempt_recovery(self, error: AgentError, pattern: ErrorPattern):
        """Attempt recovery based on the error pattern."""
        error.recovery_attempted = True
        
        try:
            # Check if we have a custom callback for this recovery action
            if pattern.recovery_action in self.recovery_callbacks:
                callback = self.recovery_callbacks[pattern.recovery_action]
                success = await callback(error, pattern)
                error.recovery_success = success
            else:
                # Use default recovery logic
                success = await self._default_recovery(error, pattern)
                error.recovery_success = success
            
            # Update stored error
            await self._store_error(error)
            
            if success:
                logger.info(f"Successfully recovered from error {error.error_id}")
            else:
                logger.warning(f"Recovery failed for error {error.error_id}")
                
        except Exception as recovery_error:
            logger.error(f"Recovery attempt failed: {str(recovery_error)}")
            error.recovery_success = False
            await self._store_error(error)
    
    async def _default_recovery(self, error: AgentError, pattern: ErrorPattern) -> bool:
        """Default recovery logic."""
        if pattern.recovery_action == RecoveryAction.RETRY:
            # For retry, we just log the attempt - actual retry logic should be in the caller
            logger.info(f"Marking error {error.error_id} for retry")
            return True
            
        elif pattern.recovery_action == RecoveryAction.RESTART:
            # For restart, we would need to restart the agent execution
            logger.info(f"Marking error {error.error_id} for restart")
            return True
            
        elif pattern.recovery_action == RecoveryAction.FALLBACK:
            # For fallback, we would use alternative providers or methods
            logger.info(f"Marking error {error.error_id} for fallback")
            return True
            
        elif pattern.recovery_action == RecoveryAction.ESCALATE:
            # For escalation, we would notify administrators
            logger.warning(f"Escalating error {error.error_id}")
            await self._escalate_error(error)
            return True
            
        return False
    
    async def _escalate_error(self, error: AgentError):
        """Escalate error to administrators."""
        # Store escalated error with special key for monitoring
        escalation_key = f"escalated_error:tenant:{self.tenant_id}:{error.error_id}"
        
        escalation_data = {
            "error": asdict(error),
            "escalated_at": datetime.utcnow().isoformat(),
            "requires_attention": True
        }
        
        await self.redis_client.setex(
            escalation_key,
            86400,  # 24 hour TTL
            json.dumps(escalation_data, default=str)
        )
        
        logger.critical(f"Error escalated: {error.error_message}", extra={
            "error_id": error.error_id,
            "agent_id": error.agent_id,
            "severity": error.severity.value
        })
    
    async def _store_error(self, error: AgentError):
        """Store error in Redis."""
        error_key = f"agent_error:tenant:{self.tenant_id}:agent:{error.agent_id}:{error.error_id}"
        
        # Convert to JSON-serializable format
        data = asdict(error)
        data['timestamp'] = data['timestamp'].isoformat()
        
        await self.redis_client.setex(
            error_key,
            self.error_cache_ttl,
            json.dumps(data, default=str)
        )


class GlobalErrorHandler:
    """Global error handler for managing errors across all tenants."""
    
    def __init__(self):
        self.tenant_handlers: Dict[str, AgentErrorHandler] = {}
        self.redis_client = redis.Redis(host='redis', decode_responses=True)
    
    def get_handler(self, session: AsyncSession, tenant_id: str) -> AgentErrorHandler:
        """Get or create error handler for tenant."""
        if tenant_id not in self.tenant_handlers:
            self.tenant_handlers[tenant_id] = AgentErrorHandler(
                session, tenant_id, self.redis_client
            )
        return self.tenant_handlers[tenant_id]
    
    async def get_global_error_statistics(self, hours: int = 24) -> Dict[str, Any]:
        """Get error statistics across all tenants."""
        total_errors = 0
        total_recoveries = 0
        severity_counts = {}
        tenant_stats = {}
        
        for severity in ErrorSeverity:
            severity_counts[severity.value] = 0
        
        for tenant_id, handler in self.tenant_handlers.items():
            try:
                # Get all agents for this tenant (simplified - would need actual agent list)
                # For now, we'll aggregate from Redis keys
                pattern = f"agent_error:tenant:{tenant_id}:*"
                keys = await self.redis_client.keys(pattern)
                
                tenant_errors = 0
                tenant_recoveries = 0
                
                for key in keys:
                    error_data = await self.redis_client.get(key)
                    if error_data:
                        try:
                            data = json.loads(error_data)
                            timestamp = datetime.fromisoformat(data['timestamp'])
                            
                            # Only count recent errors
                            if timestamp >= datetime.utcnow() - timedelta(hours=hours):
                                tenant_errors += 1
                                severity_counts[data['severity']] += 1
                                
                                if data.get('recovery_attempted') and data.get('recovery_success'):
                                    tenant_recoveries += 1
                                    
                        except (json.JSONDecodeError, TypeError):
                            continue
                
                tenant_stats[tenant_id] = {
                    "total_errors": tenant_errors,
                    "successful_recoveries": tenant_recoveries
                }
                
                total_errors += tenant_errors
                total_recoveries += tenant_recoveries
                
            except Exception as e:
                logger.error(f"Failed to get error stats for tenant {tenant_id}: {e}")
        
        return {
            "time_period_hours": hours,
            "total_errors": total_errors,
            "total_recoveries": total_recoveries,
            "recovery_success_rate": total_recoveries / max(total_errors, 1),
            "severity_distribution": severity_counts,
            "tenant_count": len(self.tenant_handlers),
            "tenant_stats": tenant_stats
        }


# Global error handler instance
global_error_handler = GlobalErrorHandler()