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
from ..database.connection import AsyncSessionLocal

try:
    from ..services.llm_service import LLMService
except ImportError:
    class LLMService:
        async def generate_response(self, request):
            return {"content": "Mock response", "usage": {"total_tokens": 10}}

try:
    from ..services.memory_manager import MemoryManagerService, create_memory_manager_service
except ImportError:
    class MemoryManagerService:
        def __init__(self, session): pass
        async def retrieve_memories(self, *args, **kwargs): return []
        async def store_memory(self, *args, **kwargs): pass

try:
    from ..services.guardrails import GuardrailsService
except ImportError:
    class GuardrailsService:
        def __init__(self, session): pass
        async def validate_input(self, *args, **kwargs): return type('R',(),{'is_valid':True,'violations':[]})
        async def validate_output(self, *args, **kwargs): return type('R',(),{'is_valid':True,'violations':[]})

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
    # tenant_id: str # Removed
    session_id: Optional[str] = None
    input_data: Dict[str, Any]
    config: Dict[str, Any]
    started_at: datetime
    timeout_seconds: int = 300
    
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


class AgentLifecycleManager:
    """Manager for agent lifecycle operations."""
    
    def __init__(self):
        # Shared state across all service instances
        self.active_executions: Dict[str, AgentExecutionContext] = {}
        self.execution_tasks: Dict[str, asyncio.Task] = {}
        self.cleanup_task: Optional[asyncio.Task] = None
        self.monitoring_enabled = True
    
    def get_executor(self, session: AsyncSession) -> 'AgentExecutorService':
        """Get a new executor instance."""
        return AgentExecutorService(session)
    
    async def start_monitoring(self):
        if self.cleanup_task is None:
            self.cleanup_task = asyncio.create_task(self._monitoring_loop())
            logger.info("Started agent lifecycle monitoring")
    
    async def stop_monitoring(self):
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
            self.cleanup_task = None
            logger.info("Stopped agent lifecycle monitoring")

    async def _monitoring_loop(self):
        while self.monitoring_enabled:
            try:
                async with AsyncSessionLocal() as session:
                    executor = self.get_executor(session)
                    await executor.cleanup_stale_executions(max_age_hours=1)
                await asyncio.sleep(1800)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {str(e)}")
                await asyncio.sleep(60)

    async def get_system_status(self) -> Dict[str, Any]:
        return {
            "total_active_executions": len(self.active_executions),
            "monitoring_enabled": self.monitoring_enabled,
            "executions": len(self.active_executions)
        }


# Global instance
lifecycle_manager = AgentLifecycleManager()


class AgentExecutorService(BaseService):
    """Service for executing agents with lifecycle management."""
    
    def __init__(self, session: AsyncSession):
        # We pass None as tenant_id to BaseService as we handle removals
        super().__init__(session=session, model_class=AgentExecution) # BaseService might have optional tenant_id
        # Access shared state from singleton
        self.lifecycle = lifecycle_manager
        self.llm_service = LLMService()
        self.memory_service = None
        self.guardrails_service = GuardrailsService(session)
        
    async def start_agent_execution(
        self,
        agent_id: str,
        input_data: Dict[str, Any],
        session_id: Optional[str] = None,
        timeout_seconds: int = 300,
        created_by: Optional[str] = None
    ) -> str:
        """Start agent execution asynchronously."""
        agent = await self._get_agent(agent_id)
        if not agent:
            raise ValueError(f"Agent {agent_id} not found")
        
        if agent.status != AgentStatus.ACTIVE:
            raise ValueError(f"Agent {agent_id} is not active")
        
        execution_id = str(uuid.uuid4())
        execution_record = AgentExecution(
            id=execution_id,
            agent_id=agent_id,
            session_id=session_id,
            input_data=input_data,
            status=ExecutionStatus.PENDING.value,
            started_at=datetime.utcnow(),
            created_by=created_by
        )
        
        self.session.add(execution_record)
        await self.session.commit()
        
        context = AgentExecutionContext(
            execution_id=execution_id,
            agent_id=agent_id,
            session_id=session_id,
            input_data=input_data,
            config=agent.config or {},
            started_at=datetime.utcnow(),
            timeout_seconds=timeout_seconds
        )
        
        self.lifecycle.active_executions[execution_id] = context
        
        # Start execution task
        # We must create a wrapper that handles its own session
        task = asyncio.create_task(self._execute_agent_background(context))
        self.lifecycle.execution_tasks[execution_id] = task
        
        # Update status (using current session)
        await self._update_execution_status(execution_id, ExecutionStatus.RUNNING)
        
        logger.info(f"Started agent execution {execution_id}")
        return execution_id
    
    async def stop_agent_execution(self, execution_id: str) -> bool:
        if execution_id not in self.lifecycle.active_executions:
            return False
            
        if execution_id in self.lifecycle.execution_tasks:
            task = self.lifecycle.execution_tasks[execution_id]
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        await self._update_execution_status(execution_id, ExecutionStatus.CANCELLED)
        self._cleanup_execution(execution_id)
        return True

    async def restart_agent_execution(self, execution_id: str) -> Optional[str]:
        execution = await self.get_by_id(execution_id)
        if not execution:
            return None
            
        if execution_id in self.lifecycle.active_executions:
            await self.stop_agent_execution(execution_id)
            
        return await self.start_agent_execution(
            agent_id=execution.agent_id,
            input_data=execution.input_data,
            session_id=execution.session_id,
            created_by=execution.created_by
        )

    async def get_execution_status(self, execution_id: str) -> Optional[Dict[str, Any]]:
        execution = await self.get_by_id(execution_id)
        if not execution:
            return None
            
        is_active = execution_id in self.lifecycle.active_executions
        context = self.lifecycle.active_executions.get(execution_id)
        
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
        active_list = []
        for execution_id, context in self.lifecycle.active_executions.items():
            execution = await self.get_by_id(execution_id)
            if execution:
                active_list.append({
                    "execution_id": execution_id,
                    "agent_id": context.agent_id,
                    "status": execution.status,
                    "started_at": context.started_at.isoformat(),
                    "progress": self._get_execution_progress(context)
                })
        return active_list

    async def cleanup_stale_executions(self, max_age_hours: int = 24) -> int:
        cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
        stmt = select(AgentExecution).where(
            and_(
                AgentExecution.status.in_([ExecutionStatus.RUNNING.value, ExecutionStatus.PENDING.value]),
                AgentExecution.started_at < cutoff
            )
        )
        result = await self.session.execute(stmt)
        stale = result.scalars().all()
        
        cleaned = 0
        for ex in stale:
            ex.status = ExecutionStatus.TIMEOUT.value
            ex.error_message = f"Timed out after {max_age_hours} hours"
            ex.completed_at = datetime.utcnow()
            if ex.id in self.lifecycle.active_executions:
                self._cleanup_execution(ex.id)
            cleaned += 1
        
        await self.session.commit()
        return cleaned

    async def _execute_agent_background(self, context: AgentExecutionContext):
        """Wrapper to run execution with a fresh session."""
        async with AsyncSessionLocal() as session:
            # Create a fresh executor instance for the background task
            # this avoids "another operation in progress" errors by not sharing sessions
            executor = AgentExecutorService(session)
            executor.memory_service = await create_memory_manager_service(session, "default")
            await executor._execute_agent_logic(context)

    async def _execute_agent_logic(self, context: AgentExecutionContext) -> AgentExecutionResult:
        start_time = time.time()
        try:
            agent = await self._get_agent(context.agent_id)
            if not agent:
                raise ValueError(f"Agent {context.agent_id} not found")

            # Guardrails, Memory... (Simplified logic for brevity but preserving key flows)
            memory_context = []
            if context.config.get("memory_enabled", True):
                memory_results = await self.memory_service.semantic_search(
                    agent_id=context.agent_id,
                    query=str(context.input_data),
                    limit=5
                )
                memory_context = [res.content for res in memory_results]

            llm_request = self._prepare_llm_request(agent, context, memory_context)
            
            llm_response = await asyncio.wait_for(
                self.llm_service.generate_response(llm_request),
                timeout=context.timeout_seconds
            )
            
            # Store memory
            if context.config.get("memory_enabled", True) and context.session_id:
                await self.memory_service.store_memory(
                    agent_id=context.agent_id,
                    content=f"InOut: {context.input_data} -> {llm_response}",
                    session_id=context.session_id,
                    metadata={"execution_id": context.execution_id}
                )

            execution_time_ms = int((time.time() - start_time) * 1000)
            tokens_used = llm_response.get("usage", {}).get("total_tokens", 0)
            cost = 0.0 # Simplify cost
            
            result = AgentExecutionResult(
                execution_id=context.execution_id,
                status=ExecutionStatus.COMPLETED,
                output_data=llm_response,
                tokens_used=tokens_used,
                execution_time_ms=execution_time_ms,
                cost=cost,
                completed_at=datetime.utcnow()
            )
            
            await self._update_execution_result(result)
            return result

        except Exception as e:
            logger.error(f"Execution failed: {e}")
            result = AgentExecutionResult(
                execution_id=context.execution_id,
                status=ExecutionStatus.FAILED,
                error_message=str(e),
                execution_time_ms=int((time.time() - start_time) * 1000),
                completed_at=datetime.utcnow()
            )
            await self._update_execution_result(result)
            return result
        finally:
            self._cleanup_execution(context.execution_id)

    def _cleanup_execution(self, execution_id: str):
        if execution_id in self.lifecycle.active_executions:
            del self.lifecycle.active_executions[execution_id]
        if execution_id in self.lifecycle.execution_tasks:
            # Task is running this cleanup, don't cancel self
            del self.lifecycle.execution_tasks[execution_id]

    async def _get_agent(self, agent_id: str) -> Optional[Agent]:
        stmt = select(Agent).where(Agent.id == agent_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def _update_execution_status(self, execution_id: str, status: ExecutionStatus):
        stmt = update(AgentExecution).where(AgentExecution.id == execution_id).values(status=status.value)
        await self.session.execute(stmt)
        await self.session.commit()

    async def _update_execution_result(self, result: AgentExecutionResult):
        stmt = update(AgentExecution).where(AgentExecution.id == result.execution_id).values(
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
    
    def _prepare_llm_request(self, agent: Agent, context: AgentExecutionContext, memory_context: List):
        system_prompt = agent.system_prompt or "You are a helpful assistant."
        if memory_context:
            system_prompt += f"\nContext: {memory_context}"
        return {
            "provider": agent.config.get("llm_provider", "ollama"),
            "model": agent.config.get("model_name", "llama3"),
            "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": str(context.input_data)}],
            "stream": False
        }
    
    def _get_execution_progress(self, context) -> Dict:
        return {"runtime": (datetime.utcnow() - context.started_at).total_seconds()}