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
except ImportError as e:
    logger.error(f"Failed to import memory manager: {e}")
    class MemoryManagerService:
        def __init__(self, session, tenant_id=None, memory_manager=None): 
            self.session = session
            self.tenant_id = tenant_id
            self.memory_manager = memory_manager
        async def semantic_search(self, *args, **kwargs): return []
        async def store_memory(self, *args, **kwargs): pass
        async def get_conversation_history(self, *args, **kwargs): return []
        async def get_user_preferences(self, *args, **kwargs): return []
    
    async def create_memory_manager_service(session, tenant_id):
        return MemoryManagerService(session, tenant_id)

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


SACP_INSTRUCTION = """
### SYSTEM PROTOCOL: RESPONSE FORMAT INSTRUCTIONS
You are a highly organized AI agent integrated into a larger workflow.
CRITICAL: You MUST provide your response in a valid JSON format.
DO NOT include any text outside the JSON block.
DO NOT use markdown code blocks (```json ... ```) unless specifically asked, but the raw response MUST be parseable JSON.

Your response schema is:
{
    "thought": "Your reasoning process here...",
    "status": "success" | "failure" | "clarification_needed",
    "data": {
        "key": "value"
        // Any structured data extracted or generated
    },
    "message": "The final human-readable answer."
}

Example:
{
    "thought": "I need to calculate the sum. 5+5 is 10.",
    "status": "success",
    "data": { "result": 10 },
    "message": "The result is 10."
}
"""

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
    user_id: Optional[str] = None
    
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
            timeout_seconds=timeout_seconds,
            user_id=created_by
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
    
    async def execute_agent(self, agent_id: str, input_data: Dict[str, Any], config: Optional[Dict[str, Any]] = None, user_id: Optional[str] = None) -> AgentExecutionResult:
        """Execute agent synchronously/inline and return result."""
        execution_id = str(uuid.uuid4())
        context = AgentExecutionContext(
            execution_id=execution_id,
            agent_id=agent_id,
            input_data=input_data,
            config=config or {},
            started_at=datetime.utcnow(),
            user_id=user_id
        )
        
        # Track it
        self.lifecycle.active_executions[execution_id] = context
        
        try:
            # Create memory service if needed
            if self.memory_service is None:
                try:
                    from ..services.memory_manager import create_memory_manager_service
                    self.memory_service = await create_memory_manager_service(self.session, "default")
                except ImportError:
                    logger.warning("Could not import memory manager service")
                    
            # Execute logic inline
            return await self._execute_agent_logic(context)
        finally:
            self._cleanup_execution(execution_id)

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
        
        result = {
            "execution_id": execution_id,
            "agent_id": execution.agent_id,
            "status": execution.status,
            "output_data": execution.output_data,
            "started_at": execution.started_at.isoformat() if execution.started_at else None,
            "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
            "execution_time_ms": execution.execution_time_ms,
            "tokens_used": execution.tokens_used,
            "cost": execution.cost,
            "error_message": execution.error_message,
            "is_active": is_active,
            "progress": self._get_execution_progress(context) if context else None
        }
        logger.debug(f"Returning execution status for {execution_id}: status={result['status']}, has_output={result['output_data'] is not None}")
        return result

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
        logger.info(f"[EXEC-BG] Starting background execution for {context.execution_id}")
        try:
            async with AsyncSessionLocal() as session:
                logger.debug(f"[EXEC-BG] Created new session for execution {context.execution_id}")
                # Create a fresh executor instance for the background task
                # this avoids "another operation in progress" errors by not sharing sessions
                executor = AgentExecutorService(session)
                logger.debug(f"[EXEC-BG] Creating memory service for execution {context.execution_id}")
                executor.memory_service = await create_memory_manager_service(session, "default")
                logger.debug(f"[EXEC-BG] Memory service created, executing logic for {context.execution_id}")
                await executor._execute_agent_logic(context)
                logger.info(f"[EXEC-BG] Background execution completed for {context.execution_id}")
        except Exception as e:
            logger.error(f"[EXEC-BG] Background execution failed for {context.execution_id}: {e}", exc_info=True)

    async def _execute_agent_logic(self, context: AgentExecutionContext) -> AgentExecutionResult:
        logger.info(f"[EXEC-LOGIC] Starting execution logic for {context.execution_id}")
        start_time = time.time()
        try:
            logger.debug(f"[EXEC-LOGIC] Fetching agent {context.agent_id}")
            agent = await self._get_agent(context.agent_id)
            if not agent:
                raise ValueError(f"Agent {context.agent_id} not found")
            logger.debug(f"[EXEC-LOGIC] Agent {context.agent_id} found: {agent.name}")

            # RAG Context Retrieval
            rag_context_str = ""
            if context.user_id:
                try:
                    # Import here to avoid circular dependencies
                    from .rag_service import RAGService
                    # Use a new session for RAG service to ensure thread safety if needed, or reuse current
                    # Since we are in _execute_agent_logic (async), self.session is active.
                    
                    # Ensure memory_manager is passed correctly
                    memory_manager = None
                    if self.memory_service and hasattr(self.memory_service, 'memory_manager'):
                        memory_manager = self.memory_service.memory_manager
                        
                    rag_service = RAGService(self.session, memory_manager)
                    
                    query_text = ""
                    if isinstance(context.input_data, dict):
                        query_text = str(context.input_data.get("message", "")) or str(context.input_data)
                    else:
                        query_text = str(context.input_data)
                        
                    if query_text:
                        # Convert string UUIDs to UUID objects if necessary
                        owner_uuid = uuid.UUID(context.user_id)
                        agent_uuid = uuid.UUID(context.agent_id)
                        
                        results = await rag_service.query(
                            query_text=query_text,
                            owner_id=owner_uuid,
                            limit=5,
                            agent_id=agent_uuid
                        )
                        
                        if results:
                            rag_entries = []
                            for item in results:
                                source_name = item.get('metadata', {}).get('source_name', 'Unknown Source')
                                content = item.get('content', '')
                                rag_entries.append(f"Source: {source_name}\nContent: {content}")
                            
                            rag_context_str = "\n\n".join(rag_entries)
                            logger.info(f"[EXEC-LOGIC] Retrieved {len(results)} RAG items for execution {context.execution_id}")
                except Exception as e:
                    logger.error(f"[EXEC-LOGIC] Error retrieving RAG context: {e}")

            # Guardrails, Memory... (Simplified logic for brevity but preserving key flows)
            memory_context = []
            memory_enabled = context.config.get("memory_enabled", True)
            logger.debug(f"[EXEC-LOGIC] Memory enabled: {memory_enabled}")
            
            if memory_enabled:
                if self.memory_service is not None:
                    logger.debug(f"[EXEC-LOGIC] Performing semantic search for execution {context.execution_id}")
                    try:
                        memory_results = await self.memory_service.semantic_search(
                            agent_id=context.agent_id,
                            query=str(context.input_data),
                            limit=5
                        )
                        memory_context = [res.content for res in memory_results]
                        logger.debug(f"[EXEC-LOGIC] Retrieved {len(memory_context)} memory items")
                    except Exception as e:
                        logger.error(f"[EXEC-LOGIC] Memory search failed: {e}")
                        # Continue without memory if it fails
                else:
                    logger.warning(f"[EXEC-LOGIC] Memory enabled but memory_service is None for execution {context.execution_id}")

            logger.debug(f"[EXEC-LOGIC] Preparing messages for execution {context.execution_id}")
            
            # Create agent config from agent.config dict, effectively handling overrides from context.config
            from ..models.agent import AgentConfig, LLMProvider
            
            # Base config from agent definition
            base_config = agent.config or {}
            # Override with context config (runtime overrides)
            merged_config = {**base_config, **context.config}
            
            raw_provider = merged_config.get("llm_provider", "ollama")
            # Defensive check: if frontend for some reason sent "unknown", fallback to "ollama"
            if raw_provider == "unknown":
                raw_provider = "ollama"
                
            agent_config = AgentConfig(
                name=agent.name,
                model=merged_config.get("model_name", "llama3.2:latest"),
                temperature=merged_config.get("temperature", 0.7),
                max_tokens=merged_config.get("max_tokens", 2000),
                llm_provider=raw_provider
            )

            # Fetch LLM Model for credentials (always do this if possible)
            custom_creds = None
            try:
                from ..services.llm_model import LLMModelService
                model_service = LLMModelService(self.session)
                llm_models = await model_service.list_llm_models()
                
                logger.info(f"[EXEC-LOGIC] Looking for model with provider='{raw_provider}' and name='{agent_config.model}'")
                logger.info(f"[EXEC-LOGIC] Available models: {[(m.provider, m.name, m.id) for m in llm_models]}")
                
                # Normalize provider name for matching (handle display names like "Google Gemini" -> "google")
                def normalize_provider(provider_str: str) -> str:
                    """Normalize provider name to match enum values."""
                    provider_lower = provider_str.lower().strip()
                    # Map common variations to canonical names
                    if 'google' in provider_lower or 'gemini' in provider_lower:
                        return 'google'
                    elif 'openai' in provider_lower:
                        return 'openai'
                    elif 'anthropic' in provider_lower or 'claude' in provider_lower:
                        return 'anthropic'
                    elif 'azure' in provider_lower:
                        return 'azure-openai'
                    elif 'ollama' in provider_lower:
                        return 'ollama'
                    return provider_lower
                
                normalized_target_provider = normalize_provider(raw_provider)
                
                # Find matching model by normalized provider and name (case insensitive)
                target_model = next((m for m in llm_models 
                                   if normalize_provider(m.provider) == normalized_target_provider 
                                   and m.name.strip().lower() == agent_config.model.strip().lower()), None)
                
                # If exact match fails, try partial match for model name?
                if not target_model:
                     target_model = next((m for m in llm_models 
                                   if normalize_provider(m.provider) == normalized_target_provider 
                                   and agent_config.model.strip().lower() in m.name.strip().lower()), None)
                
                if target_model:
                    logger.info(f"[EXEC-LOGIC] Found matching model: {target_model.name} (provider: {target_model.provider}, id: {target_model.id})")
                    custom_creds = {}
                    if target_model.api_key:
                        custom_creds["api_key"] = target_model.api_key
                        logger.info(f"[EXEC-LOGIC] Using API key from model {target_model.id}")
                    if target_model.api_base:
                        # Handle Ollama connection - prioritize internal networking if available
                        base_url = target_model.api_base
                        # Only apply to Ollama provider
                        if raw_provider.lower() == "ollama":
                            import os
                            env_ollama_url = os.environ.get("OLLAMA_BASE_URL")
                            # If we are in Docker and the DB says localhost, switch to the internal service
                            if base_url and ("localhost" in base_url or "127.0.0.1" in base_url) and env_ollama_url:
                                base_url = env_ollama_url
                                logger.info(f"[EXEC-LOGIC] Switched Ollama URL from localhost to {base_url}")
                        
                        custom_creds["base_url"] = base_url
                    
                    # Handle specific credential keys for different providers
                    if raw_provider.lower() == "openai" and target_model.api_key:
                        custom_creds = {"api_key": target_model.api_key}
                        if target_model.api_base:
                            custom_creds["base_url"] = target_model.api_base
                    elif raw_provider.lower() == "anthropic" and target_model.api_key:
                        custom_creds = {"api_key": target_model.api_key}
                    elif raw_provider.lower() == "google" and target_model.api_key:
                        custom_creds = {"api_key": target_model.api_key}
                        logger.info(f"[EXEC-LOGIC] Set Google API key from model")
                        if target_model.api_base:
                            custom_creds["base_url"] = target_model.api_base
                    elif raw_provider.lower() == "azure-openai" and target_model.api_key:
                        custom_creds = {
                            "api_key": target_model.api_key,
                            "endpoint": target_model.api_base,
                            "api_version": "2023-05-15"
                        }
                else:
                    logger.warning(f"[EXEC-LOGIC] No matching model found for provider='{raw_provider}' name='{agent_config.model}'. Available: {[(m.provider, m.name) for m in llm_models]}")
            except Exception as e:
                logger.error(f"[EXEC-LOGIC] Failed to fetch model credentials: {e}", exc_info=True)

            # Check if agent has tools configured
            available_tools = agent.available_tools or []
            tool_executions = []
            
            if available_tools:
                logger.info(f"[EXEC-LOGIC] Phase 1: Tool Analysis & Execution for {context.execution_id}")
                try:
                    from ..services.tool_executor import ToolExecutorService
                    tool_executor = ToolExecutorService(self.session, llm_service=self.llm_service)
                    
                    # Analyze input and execute tools if needed
                    user_input_str = str(context.input_data.get("message", context.input_data))
                    
                    # Phase 1: Tool Decision & Execution
                    tool_executions, tool_usage = await tool_executor.analyze_and_execute_tools(
                        user_input=user_input_str,
                        available_tools=available_tools,
                        agent_id=context.agent_id,
                        agent_config=agent_config,
                        credentials=custom_creds
                    )
                    
                    if tool_executions:
                        logger.info(f"[EXEC-LOGIC] Phase 1 Completed: Executed {len(tool_executions)} tool(s)")
                        logger.debug(f"[EXEC-LOGIC] Phase 1 Token Usage: {tool_usage}")
                    else:
                        logger.info(f"[EXEC-LOGIC] Phase 1 Completed: No tools executed")
                        
                except Exception as e:
                    logger.error(f"[EXEC-LOGIC] Tool execution failed: {e}", exc_info=True)
                    # Continue without tools if they fail
                    tool_usage = {"total_tokens": 0}
            else:
                tool_usage = {"total_tokens": 0}

            logger.info(f"[EXEC-LOGIC] Phase 2: Final Response Generation for {context.execution_id}")
            
            system_prompt = agent.system_prompt or "You are a helpful assistant."
            
            # Inject RAG Context
            if rag_context_str:
                system_prompt += f"\n\n### RELEVANT KNOWLEDGE BASE CONTEXT ###\nUse the following information to answer the user's request if relevant.\n\n{rag_context_str}\n"

            if memory_context:
                system_prompt += f"\nContext from memory: {', '.join(memory_context)}"
            
            # Inject Success/Failure Criteria
            success_criteria = agent.config.get("success_criteria")
            failure_criteria = agent.config.get("failure_criteria")
            
            if success_criteria or failure_criteria:
                 system_prompt += "\n\n### EVALUATION CRITERIA\n"
                 if success_criteria:
                     system_prompt += f"SUCCESS CRITERIA:\n{success_criteria}\n\n"
                     system_prompt += "If the success criteria are met, set the 'status' field in your JSON response to 'success'.\n"
                 if failure_criteria:
                     system_prompt += f"FAILURE CRITERIA:\n{failure_criteria}\n\n"
                     system_prompt += "If the failure criteria are met, set the 'status' field in your JSON response to 'failure'.\n"

            # Inject Standard Agent Communication Protocol if enabled
            if agent.config.get("use_standard_protocol") or agent.config.get("use_standard_response_format") or success_criteria or failure_criteria:
                system_prompt += f"\n\n{SACP_INSTRUCTION}"
            
            # Add tool results to context if available
            if tool_executions:
                from ..services.tool_executor import ToolExecutorService
                # Reuse the existing tool_executor if possible or just call formatting
                tool_executor_fmt = ToolExecutorService(self.session)
                tool_context = tool_executor_fmt.format_tool_results_for_context(tool_executions)
                system_prompt += tool_context
            
            # Extract user message - if it's a dict with 'message', use that
            # Also handle chat_history if present
            user_input = context.input_data
            user_content = ""
            chat_history = []
            
            if isinstance(user_input, dict):
                # Extract Message
                if "message" in user_input:
                    user_content = str(user_input["message"])
                elif "input" in user_input:
                     user_content = str(user_input["input"])
                else:
                    user_content = str(user_input)
                
                # Extract History
                if "chat_history" in user_input and isinstance(user_input["chat_history"], list):
                    chat_history = user_input["chat_history"]
                    logger.debug(f"[EXEC-LOGIC] Found {len(chat_history)} history messages in input")
            else:
                user_content = str(user_input)

            messages = [{"role": "system", "content": system_prompt}]
            
            # Add History
            for hist_msg in chat_history:
                if isinstance(hist_msg, dict) and "role" in hist_msg and "content" in hist_msg:
                    messages.append({"role": hist_msg["role"], "content": hist_msg["content"]})
            
            # Add Current Message
            messages.append({"role": "user", "content": user_content})
            
            logger.info(f"[EXEC-LOGIC] Calling LLM service for execution {context.execution_id} (timeout: {context.timeout_seconds}s)")
            
            llm_response = await asyncio.wait_for(
                self.llm_service.generate_response(messages, agent_config, stream=False, credentials=custom_creds),
                timeout=context.timeout_seconds
            )
            logger.info(f"[EXEC-LOGIC] LLM response received for execution {context.execution_id}")
            
            # Store memory
            if context.config.get("memory_enabled", True) and context.session_id:
                logger.debug(f"[EXEC-LOGIC] Storing memory for execution {context.execution_id}")
                await self.memory_service.store_memory(
                    agent_id=context.agent_id,
                    content=f"InOut: {context.input_data} -> {llm_response.content}",
                    session_id=context.session_id,
                    metadata={"execution_id": context.execution_id}
                )
                logger.debug(f"[EXEC-LOGIC] Memory stored for execution {context.execution_id}")

            execution_time_ms = int((time.time() - start_time) * 1000)
            
            # Calculate total tokens (Phase 1 + Phase 2)
            phase2_tokens = llm_response.usage.total_tokens if llm_response.usage else 0
            phase1_tokens = tool_usage.get("total_tokens", 0)
            total_tokens_used = phase1_tokens + phase2_tokens
            
            logger.info(f"[EXEC-LOGIC] Token Usage - Phase 1: {phase1_tokens}, Phase 2: {phase2_tokens}, Total: {total_tokens_used}")
            cost = 0.0 # Simplify cost
            
            logger.debug(f"[EXEC-LOGIC] Creating execution result for {context.execution_id}")
            result = AgentExecutionResult(
                execution_id=context.execution_id,
                status=ExecutionStatus.COMPLETED,
                output_data={"content": llm_response.content, "model": llm_response.model},
                tokens_used=total_tokens_used,
                execution_time_ms=execution_time_ms,
                cost=cost,
                completed_at=datetime.utcnow()
            )
            
            logger.info(f"[EXEC-LOGIC] Updating execution result to COMPLETED for {context.execution_id}")
            await self._update_execution_result(result)
            logger.info(f"[EXEC-LOGIC] Execution {context.execution_id} completed successfully in {execution_time_ms}ms")
            return result

        except Exception as e:
            logger.error(f"[EXEC-LOGIC] Execution {context.execution_id} failed: {e}", exc_info=True)
            result = AgentExecutionResult(
                execution_id=context.execution_id,
                status=ExecutionStatus.FAILED,
                error_message=str(e),
                execution_time_ms=int((time.time() - start_time) * 1000),
                completed_at=datetime.utcnow()
            )
            logger.info(f"[EXEC-LOGIC] Updating execution result to FAILED for {context.execution_id}")
            await self._update_execution_result(result)
            logger.info(f"[EXEC-LOGIC] Execution {context.execution_id} marked as failed")
            return result
        finally:
            logger.debug(f"[EXEC-LOGIC] Cleaning up execution {context.execution_id}")
            self._cleanup_execution(context.execution_id)
            logger.debug(f"[EXEC-LOGIC] Cleanup completed for execution {context.execution_id}")

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
            "model": agent.config.get("model_name", "llama3.2:latest"),
            "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": str(context.input_data)}],
            "stream": False
        }
    
    def _get_execution_progress(self, context) -> Dict:
        return {"runtime": (datetime.utcnow() - context.started_at).total_seconds()}