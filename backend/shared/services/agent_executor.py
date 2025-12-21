"""Agent Executor Service for managing agent lifecycle and execution."""

import asyncio
import json
import time
import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Any, Optional, List, Callable
from contextlib import asynccontextmanager
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, update
from pydantic import BaseModel, Field

from ..models.agent import Agent, AgentExecution, AgentStatus
try:
    from ..services.llm_service import LLMService
except ImportError:
    # Fallback for when LLM service dependencies are not available
    class LLMService:
        async def generate_response(self, request):
            return {
                "content": "Mock response for testing",
                "usage": {"total_tokens": 10}
            }

try:
    from ..services.memory_manager import MemoryManagerService
except ImportError:
    # Fallback for when memory service is not available
    class MemoryManagerService:
        def __init__(self, session, tenant_id):
            pass
        async def retrieve_memories(self, agent_id, query, limit):
            return []
        async def store_memory(self, agent_id, content, session_id, metadata):
            pass

try:
    from ..services.guardrails import GuardrailsService
except ImportError:
    # Fallback for when guardrails service is not available
    class GuardrailsService:
        def __init__(self, session, tenant_id):
            pass
        async def validate_input(self, content, context):
            return type('ValidationResult', (), {'is_valid': True, 'violations': []})()
        async def validate_output(self, content, context):
            return type('ValidationResult', (), {'is_valid': True, 'violations': []})()
from .base import BaseService


logger = logging.getLogger(__name__)


class ExecutionStatus(str, Enum):
    """Agent execution status values."""
    
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class AgentExecutionContext(BaseModel):
    """Context for agent execution."""
    
    execution_id: str
    agent_id: str
    tenant_id: str
    session_id: Optional[str] = None
    input_data: Dict[str, Any]
    config: Dict[str, Any]
    started_at: datetime
    timeout_seconds: int = 300  # 5 minutes default timeout
    
    class Config:
        arbitrary_types_allowed = True


class AgentExecutionResult(BaseModel):
    """Result of agent execution."""
    
    execution_id: str
    status: ExecutionStatus
    output_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    tokens_used: Optional[int] = None
    execution_time_ms: Optional[int] = None
    cost: Optional[float] = None
    completed_at: Optional[datetime] = None


class AgentExecutorService(BaseService):
    """Service for executing agents with lifecycle management."""
    
    def __init__(self, session: AsyncSession, tenant_id: str):
        super().__init__(session, AgentExecution, tenant_id)
        self.active_executions: Dict[str, AgentExecutionContext] = {}
        self.execution_tasks: Dict[str, asyncio.Task] = {}
        self.llm_service = LLMService()
        self.memory_service = MemoryManagerService(session, tenant_id)
        self.guardrails_service = GuardrailsService(session, tenant_id)
        
    async def start_agent_execution(
        self,
        agent_id: str,
        input_data: Dict[str, Any],
        session_id: Optional[str] = None,
        timeout_seconds: int = 300,
        created_by: Optional[str] = None
    ) -> str:
        """Start agent execution asynchronously."""
        # Verify agent exists and is active
        agent = await self._get_agent(agent_id)
        if not agent:
            raise ValueError(f"Agent {agent_id} not found")
        
        if agent.status != AgentStatus.ACTIVE:
            raise ValueError(f"Agent {agent_id} is not active (status: {agent.status})")
        
        # Create execution record
        execution_id = str(uuid.uuid4())
        execution_record = AgentExecution(
            id=execution_id,
            tenant_id=self.tenant_id,
            agent_id=agent_id,
            session_id=session_id,
            input_data=input_data,
            status=ExecutionStatus.PENDING.value,
            started_at=datetime.utcnow(),
            created_by=created_by
        )
        
        self.session.add(execution_record)
        await self.session.commit()
        
        # Create execution context
        context = AgentExecutionContext(
            execution_id=execution_id,
            agent_id=agent_id,
            tenant_id=self.tenant_id,
            session_id=session_id,
            input_data=input_data,
            config=agent.config or {},
            started_at=datetime.utcnow(),
            timeout_seconds=timeout_seconds
        )
        
        # Store active execution
        self.active_executions[execution_id] = context
        
        # Start execution task
        task = asyncio.create_task(self._execute_agent(context))
        self.execution_tasks[execution_id] = task
        
        # Update status to running
        await self._update_execution_status(execution_id, ExecutionStatus.RUNNING)
        
        logger.info(f"Started agent execution {execution_id} for agent {agent_id}")
        return execution_id
    
    async def stop_agent_execution(self, execution_id: str) -> bool:
        """Stop a running agent execution."""
        if execution_id not in self.active_executions:
            return False
        
        # Cancel the task
        if execution_id in self.execution_tasks:
            task = self.execution_tasks[execution_id]
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        # Update status
        await self._update_execution_status(execution_id, ExecutionStatus.CANCELLED)
        
        # Clean up
        self._cleanup_execution(execution_id)
        
        logger.info(f"Stopped agent execution {execution_id}")
        return True
    
    async def restart_agent_execution(self, execution_id: str) -> Optional[str]:
        """Restart a failed or cancelled agent execution."""
        # Get original execution
        execution = await self.get_by_id(execution_id)
        if not execution:
            return None
        
        # Stop current execution if running
        if execution_id in self.active_executions:
            await self.stop_agent_execution(execution_id)
        
        # Start new execution with same parameters
        new_execution_id = await self.start_agent_execution(
            agent_id=execution.agent_id,
            input_data=execution.input_data,
            session_id=execution.session_id,
            created_by=execution.created_by
        )
        
        logger.info(f"Restarted execution {execution_id} as {new_execution_id}")
        return new_execution_id
    
    async def get_execution_status(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Get current execution status and details."""
        execution = await self.get_by_id(execution_id)
        if not execution:
            return None
        
        # Check if execution is active
        is_active = execution_id in self.active_executions
        context = self.active_executions.get(execution_id)
        
        return {
            "execution_id": execution_id,
            "agent_id": execution.agent_id,
            "status": execution.status,
            "started_at": execution.started_at.isoformat() if execution.started_at else None,
            "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
            "execution_time_ms": execution.execution_time_ms,
            "tokens_used": execution.tokens_used,
            "cost": execution.cost,
            "error_message": execution.error_message,
            "is_active": is_active,
            "progress": self._get_execution_progress(context) if context else None
        }
    
    async def list_active_executions(self) -> List[Dict[str, Any]]:
        """List all currently active executions."""
        active_list = []
        
        for execution_id, context in self.active_executions.items():
            execution = await self.get_by_id(execution_id)
            if execution:
                active_list.append({
                    "execution_id": execution_id,
                    "agent_id": context.agent_id,
                    "status": execution.status,
                    "started_at": context.started_at.isoformat(),
                    "runtime_seconds": (datetime.utcnow() - context.started_at).total_seconds(),
                    "progress": self._get_execution_progress(context)
                })
        
        return active_list
    
    async def cleanup_stale_executions(self, max_age_hours: int = 24) -> int:
        """Clean up stale executions that are stuck in running state."""
        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
        
        # Find stale executions
        stmt = select(AgentExecution).where(
            and_(
                AgentExecution.tenant_id == self.tenant_id,
                AgentExecution.status.in_([ExecutionStatus.RUNNING.value, ExecutionStatus.PENDING.value]),
                AgentExecution.started_at < cutoff_time
            )
        )
        
        result = await self.session.execute(stmt)
        stale_executions = result.scalars().all()
        
        cleaned_count = 0
        for execution in stale_executions:
            # Update status to timeout
            execution.status = ExecutionStatus.TIMEOUT.value
            execution.error_message = f"Execution timed out after {max_age_hours} hours"
            execution.completed_at = datetime.utcnow()
            
            # Clean up from active executions
            if execution.id in self.active_executions:
                self._cleanup_execution(execution.id)
            
            cleaned_count += 1
        
        await self.session.commit()
        
        logger.info(f"Cleaned up {cleaned_count} stale executions")
        return cleaned_count
    
    async def _execute_agent(self, context: AgentExecutionContext) -> AgentExecutionResult:
        """Execute agent with full lifecycle management."""
        start_time = time.time()
        
        try:
            # Load agent configuration
            agent = await self._get_agent(context.agent_id)
            if not agent:
                raise ValueError(f"Agent {context.agent_id} not found")
            
            # Apply guardrails to input
            if context.config.get("guardrails_enabled", True):
                input_validation = await self.guardrails_service.validate_input(
                    content=str(context.input_data),
                    context={"agent_id": context.agent_id, "session_id": context.session_id}
                )
                
                if not input_validation.is_valid:
                    raise ValueError(f"Input validation failed: {', '.join(input_validation.violations)}")
            
            # Load agent memory if enabled
            memory_context = []
            if context.config.get("memory_enabled", True):
                memory_context = await self.memory_service.retrieve_memories(
                    agent_id=context.agent_id,
                    query=str(context.input_data),
                    limit=10
                )
            
            # Prepare LLM request
            llm_request = self._prepare_llm_request(agent, context, memory_context)
            
            # Execute LLM call with timeout
            llm_response = await asyncio.wait_for(
                self.llm_service.generate_response(llm_request),
                timeout=context.timeout_seconds
            )
            
            # Apply output guardrails
            if context.config.get("guardrails_enabled", True):
                output_validation = await self.guardrails_service.validate_output(
                    content=llm_response.get("content", ""),
                    context={"agent_id": context.agent_id, "session_id": context.session_id}
                )
                
                if not output_validation.is_valid:
                    raise ValueError(f"Output validation failed: {', '.join(output_validation.violations)}")
            
            # Store memory if enabled
            if context.config.get("memory_enabled", True) and context.session_id:
                await self.memory_service.store_memory(
                    agent_id=context.agent_id,
                    content=f"Input: {context.input_data}\nOutput: {llm_response}",
                    session_id=context.session_id,
                    metadata={"execution_id": context.execution_id}
                )
            
            # Calculate execution metrics
            execution_time_ms = int((time.time() - start_time) * 1000)
            tokens_used = llm_response.get("usage", {}).get("total_tokens", 0)
            cost = self._calculate_cost(tokens_used, agent.config)
            
            # Create result
            result = AgentExecutionResult(
                execution_id=context.execution_id,
                status=ExecutionStatus.COMPLETED,
                output_data=llm_response,
                tokens_used=tokens_used,
                execution_time_ms=execution_time_ms,
                cost=cost,
                completed_at=datetime.utcnow()
            )
            
            # Update execution record
            await self._update_execution_result(result)
            
            logger.info(f"Completed agent execution {context.execution_id}")
            return result
            
        except asyncio.TimeoutError:
            result = AgentExecutionResult(
                execution_id=context.execution_id,
                status=ExecutionStatus.TIMEOUT,
                error_message=f"Execution timed out after {context.timeout_seconds} seconds",
                execution_time_ms=int((time.time() - start_time) * 1000),
                completed_at=datetime.utcnow()
            )
            
        except asyncio.CancelledError:
            result = AgentExecutionResult(
                execution_id=context.execution_id,
                status=ExecutionStatus.CANCELLED,
                error_message="Execution was cancelled",
                execution_time_ms=int((time.time() - start_time) * 1000),
                completed_at=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"Agent execution {context.execution_id} failed: {str(e)}")
            result = AgentExecutionResult(
                execution_id=context.execution_id,
                status=ExecutionStatus.FAILED,
                error_message=str(e),
                execution_time_ms=int((time.time() - start_time) * 1000),
                completed_at=datetime.utcnow()
            )
        
        finally:
            # Clean up execution context
            self._cleanup_execution(context.execution_id)
        
        # Update execution record with error result
        await self._update_execution_result(result)
        return result
    
    async def _get_agent(self, agent_id: str) -> Optional[Agent]:
        """Get agent by ID."""
        stmt = select(Agent).where(
            and_(
                Agent.id == agent_id,
                Agent.tenant_id == self.tenant_id
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    def _prepare_llm_request(
        self,
        agent: Agent,
        context: AgentExecutionContext,
        memory_context: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Prepare LLM request with agent configuration and context."""
        # Build system prompt with memory context
        system_prompt = agent.system_prompt or "You are a helpful AI assistant."
        
        if memory_context:
            memory_text = "\n".join([
                f"Memory: {mem.get('content', '')}" for mem in memory_context[:5]
            ])
            system_prompt += f"\n\nRelevant context from previous conversations:\n{memory_text}"
        
        return {
            "provider": agent.config.get("llm_provider", "ollama"),
            "model": agent.config.get("model_name", "llama2"),
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": str(context.input_data)}
            ],
            "temperature": agent.config.get("temperature", 0.7),
            "max_tokens": agent.config.get("max_tokens", 1000),
            "stream": False
        }
    
    def _calculate_cost(self, tokens_used: int, config: Dict[str, Any]) -> float:
        """Calculate execution cost based on tokens and provider."""
        # Simple cost calculation - can be enhanced with actual provider pricing
        provider = config.get("llm_provider", "ollama")
        
        if provider == "ollama":
            return 0.0  # Local models are free
        elif provider == "openai":
            return tokens_used * 0.00002  # Rough estimate for GPT-3.5
        elif provider == "anthropic":
            return tokens_used * 0.00003  # Rough estimate for Claude
        else:
            return 0.0
    
    def _get_execution_progress(self, context: AgentExecutionContext) -> Dict[str, Any]:
        """Get execution progress information."""
        runtime_seconds = (datetime.utcnow() - context.started_at).total_seconds()
        progress_percentage = min((runtime_seconds / context.timeout_seconds) * 100, 100)
        
        return {
            "runtime_seconds": runtime_seconds,
            "timeout_seconds": context.timeout_seconds,
            "progress_percentage": progress_percentage,
            "estimated_remaining_seconds": max(0, context.timeout_seconds - runtime_seconds)
        }
    
    async def _update_execution_status(self, execution_id: str, status: ExecutionStatus):
        """Update execution status in database."""
        stmt = update(AgentExecution).where(
            and_(
                AgentExecution.id == execution_id,
                AgentExecution.tenant_id == self.tenant_id
            )
        ).values(status=status.value)
        
        await self.session.execute(stmt)
        await self.session.commit()
    
    async def _update_execution_result(self, result: AgentExecutionResult):
        """Update execution with final result."""
        stmt = update(AgentExecution).where(
            and_(
                AgentExecution.id == result.execution_id,
                AgentExecution.tenant_id == self.tenant_id
            )
        ).values(
            status=result.status.value,
            output_data=result.output_data,
            error_message=result.error_message,
            tokens_used=result.tokens_used,
            execution_time_ms=result.execution_time_ms,
            cost=result.cost,
            completed_at=result.completed_at
        )
        
        await self.session.execute(stmt)
        await self.session.commit()
    
    def _cleanup_execution(self, execution_id: str):
        """Clean up execution context and tasks."""
        if execution_id in self.active_executions:
            del self.active_executions[execution_id]
        
        if execution_id in self.execution_tasks:
            task = self.execution_tasks[execution_id]
            if not task.done():
                task.cancel()
            del self.execution_tasks[execution_id]


class AgentLifecycleManager:
    """Manager for agent lifecycle operations across multiple tenants."""
    
    def __init__(self):
        self.executors: Dict[str, AgentExecutorService] = {}
        self.cleanup_task: Optional[asyncio.Task] = None
        self.monitoring_enabled = True
    
    def get_executor(self, session: AsyncSession, tenant_id: str) -> AgentExecutorService:
        """Get or create executor for tenant."""
        if tenant_id not in self.executors:
            self.executors[tenant_id] = AgentExecutorService(session, tenant_id)
        return self.executors[tenant_id]
    
    async def start_monitoring(self):
        """Start background monitoring and cleanup tasks."""
        if self.cleanup_task is None:
            self.cleanup_task = asyncio.create_task(self._monitoring_loop())
            logger.info("Started agent lifecycle monitoring")
    
    async def stop_monitoring(self):
        """Stop background monitoring."""
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
            self.cleanup_task = None
            logger.info("Stopped agent lifecycle monitoring")
    
    async def _monitoring_loop(self):
        """Background monitoring loop for cleanup and health checks."""
        while self.monitoring_enabled:
            try:
                # Clean up stale executions every 30 minutes
                for executor in self.executors.values():
                    await executor.cleanup_stale_executions(max_age_hours=1)
                
                # Wait 30 minutes before next cleanup
                await asyncio.sleep(1800)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {str(e)}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get overall system status for all tenants."""
        total_active = 0
        tenant_stats = {}
        
        for tenant_id, executor in self.executors.items():
            active_executions = await executor.list_active_executions()
            total_active += len(active_executions)
            tenant_stats[tenant_id] = {
                "active_executions": len(active_executions),
                "executions": active_executions
            }
        
        return {
            "total_active_executions": total_active,
            "tenant_count": len(self.executors),
            "monitoring_enabled": self.monitoring_enabled,
            "tenant_stats": tenant_stats
        }


# Global lifecycle manager instance
lifecycle_manager = AgentLifecycleManager()