import logging
"""Agent Executor API endpoints for managing agent execution lifecycle."""

from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from ..database.connection import get_async_db
from ..services.agent_executor import AgentExecutorService, ExecutionStatus, lifecycle_manager
from ..services.auth import get_current_user
from ..models.agent import AgentExecution, Agent
from ..models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/agent-executor", tags=["agent-executor"])


class ExecuteAgentRequest(BaseModel):
    """Request model for executing an agent."""
    input_data: Dict[str, Any] = Field(..., description="Input data for agent execution")
    session_id: Optional[str] = Field(None, description="Session ID for conversation continuity")
    timeout_seconds: int = Field(300, ge=30, le=3600, description="Execution timeout in seconds")


class ExecuteAgentResponse(BaseModel):
    """Response model for agent execution."""
    execution_id: str = Field(..., description="Unique execution identifier")
    agent_id: str = Field(..., description="Agent identifier")
    status: str = Field(..., description="Current execution status")
    message: str = Field(..., description="Status message")


class ExecutionStatusResponse(BaseModel):
    """Response model for execution status."""
    execution_id: UUID = Field(..., description="Execution identifier")
    agent_id: UUID = Field(..., description="Agent identifier")
    status: str = Field(..., description="Current status")
    output_data: Optional[Dict[str, Any]] = Field(None, description="Execution output data")
    started_at: Optional[datetime] = Field(None, description="Start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")
    execution_time_ms: Optional[int] = Field(None, description="Execution time in milliseconds")
    tokens_used: Optional[int] = Field(None, description="Tokens consumed")
    cost: Optional[float] = Field(None, description="Execution cost")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    is_active: bool = Field(..., description="Whether execution is currently active")
    progress: Optional[Dict[str, Any]] = Field(None, description="Execution progress information")


class ActiveExecutionResponse(BaseModel):
    """Response model for active execution."""
    execution_id: UUID = Field(..., description="Execution identifier")
    agent_id: UUID = Field(..., description="Agent identifier")
    status: str = Field(..., description="Current status")
    started_at: datetime = Field(..., description="Start timestamp")
    # runtime_seconds: float = Field(..., description="Current runtime in seconds") # Optional in recent refactor? kept it
    progress: Optional[Dict[str, Any]] = Field(None, description="Progress information")


class SystemStatusResponse(BaseModel):
    """Response model for system status."""
    total_active_executions: int = Field(..., description="Total active executions")
    monitoring_enabled: bool = Field(..., description="Whether monitoring is enabled")


@router.post("/{agent_id}/execute", response_model=ExecuteAgentResponse)
async def execute_agent(
    agent_id: UUID,
    request: ExecuteAgentRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_async_db)
):
    """Execute an agent asynchronously."""
    executor = lifecycle_manager.get_executor(session)
    
    try:
        execution_id = await executor.start_agent_execution(
            agent_id=str(agent_id),
            input_data=request.input_data,
            session_id=request.session_id,
            timeout_seconds=request.timeout_seconds,
            created_by=None  # Use None for system actions
        )
        
        return ExecuteAgentResponse(
            execution_id=execution_id,
            agent_id=str(agent_id),
            status=ExecutionStatus.RUNNING.value,
            message="Agent execution started successfully"
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Failed to start execution for agent {agent_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start execution: {str(e)}. Check backend logs for details.")


@router.post("/executions/{execution_id}/stop")
async def stop_execution(
    execution_id: UUID,
    session: AsyncSession = Depends(get_async_db)
):
    """Stop a running agent execution."""
    executor = lifecycle_manager.get_executor(session)
    
    success = await executor.stop_agent_execution(str(execution_id))
    
    if not success:
        raise HTTPException(status_code=404, detail="Execution not found or not running")
    
    return {"message": "Execution stopped successfully"}


@router.post("/executions/{execution_id}/restart", response_model=ExecuteAgentResponse)
async def restart_execution(
    execution_id: UUID,
    session: AsyncSession = Depends(get_async_db)
):
    """Restart a failed or cancelled agent execution."""
    executor = lifecycle_manager.get_executor(session)
    
    new_execution_id = await executor.restart_agent_execution(str(execution_id))
    
    if not new_execution_id:
        raise HTTPException(status_code=404, detail="Original execution not found")
    
    # Get agent ID from the new execution
    execution_status = await executor.get_execution_status(new_execution_id)
    
    return ExecuteAgentResponse(
        execution_id=new_execution_id,
        agent_id=execution_status["agent_id"],
        status=ExecutionStatus.RUNNING.value,
        message="Execution restarted successfully"
    )


@router.get("/executions/{execution_id}/status", response_model=ExecutionStatusResponse)
async def get_execution_status(
    execution_id: UUID,
    session: AsyncSession = Depends(get_async_db)
):
    """Get the status of an agent execution."""
    executor = lifecycle_manager.get_executor(session)
    
    status_info = await executor.get_execution_status(str(execution_id))
    
    if not status_info:
        raise HTTPException(status_code=404, detail="Execution not found")
    
    return ExecutionStatusResponse(**status_info)


@router.get("/executions/active", response_model=List[ActiveExecutionResponse])
async def list_active_executions(
    session: AsyncSession = Depends(get_async_db)
):
    """List all currently active executions."""
    executor = lifecycle_manager.get_executor(session)
    
    active_executions = await executor.list_active_executions()
    
    return [ActiveExecutionResponse(**execution) for execution in active_executions]


@router.get("/{agent_id}/executions", response_model=List[ExecutionStatusResponse])
async def list_agent_executions(
    agent_id: UUID,
    status_filter: Optional[ExecutionStatus] = None,
    limit: int = 50,
    offset: int = 0,
    session: AsyncSession = Depends(get_async_db)
):
    """List executions for a specific agent."""
    executor = lifecycle_manager.get_executor(session)
    
    from sqlalchemy import select, and_
    
    stmt = select(AgentExecution).where(AgentExecution.agent_id == str(agent_id))
    
    if status_filter:
        stmt = stmt.where(AgentExecution.status == status_filter.value)
    
    stmt = stmt.order_by(AgentExecution.started_at.desc()).limit(limit).offset(offset)
    
    result = await session.execute(stmt)
    executions = result.scalars().all()
    
    execution_responses = []
    for execution in executions:
        is_active = execution.id in lifecycle_manager.active_executions
        progress = None
        
        if is_active:
            context = lifecycle_manager.active_executions[execution.id]
            progress = executor._get_execution_progress(context)
        
        execution_responses.append(ExecutionStatusResponse(
            execution_id=execution.id,
            agent_id=execution.agent_id,
            status=execution.status,
            started_at=execution.started_at.isoformat() if execution.started_at else None,
            completed_at=execution.completed_at.isoformat() if execution.completed_at else None,
            execution_time_ms=execution.execution_time_ms,
            tokens_used=execution.tokens_used,
            cost=execution.cost,
            error_message=execution.error_message,
            is_active=is_active,
            progress=progress
        ))
    
    return execution_responses


@router.post("/cleanup")
async def cleanup_stale_executions(
    max_age_hours: int = 24,
    session: AsyncSession = Depends(get_async_db)
):
    """Clean up stale executions."""
    executor = lifecycle_manager.get_executor(session)
    cleaned_count = await executor.cleanup_stale_executions(max_age_hours)
    
    return {
        "message": f"Cleaned up {cleaned_count} stale executions",
        "cleaned_count": cleaned_count
    }


@router.get("/system/status", response_model=SystemStatusResponse)
async def get_system_status():
    """Get overall system status."""
    status = await lifecycle_manager.get_system_status()
    # Ensure keys match SystemStatusResponse
    return SystemStatusResponse(
        total_active_executions=status.get("total_active_executions", 0),
        monitoring_enabled=status.get("monitoring_enabled", True)
    )

# Health check endpoint
@router.get("/health")
async def executor_health_check():
    """Health check for the agent executor service."""
    status = await lifecycle_manager.get_system_status()
    
    return {
        "status": "healthy",
        "service": "agent-executor",
        "active_executions": status["total_active_executions"],
        "monitoring_enabled": status["monitoring_enabled"]
    }
