"""Agent Executor API endpoints for managing agent execution lifecycle."""

from typing import List, Optional, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from ..database.connection import get_async_db
from ..services.agent_executor import AgentExecutorService, ExecutionStatus, lifecycle_manager
from ..middleware.tenant import get_tenant_aware_session
from ..models.agent import AgentExecution

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
    
    execution_id: str = Field(..., description="Execution identifier")
    agent_id: str = Field(..., description="Agent identifier")
    status: str = Field(..., description="Current status")
    started_at: Optional[str] = Field(None, description="Start timestamp")
    completed_at: Optional[str] = Field(None, description="Completion timestamp")
    execution_time_ms: Optional[int] = Field(None, description="Execution time in milliseconds")
    tokens_used: Optional[int] = Field(None, description="Tokens consumed")
    cost: Optional[float] = Field(None, description="Execution cost")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    is_active: bool = Field(..., description="Whether execution is currently active")
    progress: Optional[Dict[str, Any]] = Field(None, description="Execution progress information")


class ActiveExecutionResponse(BaseModel):
    """Response model for active execution."""
    
    execution_id: str = Field(..., description="Execution identifier")
    agent_id: str = Field(..., description="Agent identifier")
    status: str = Field(..., description="Current status")
    started_at: str = Field(..., description="Start timestamp")
    runtime_seconds: float = Field(..., description="Current runtime in seconds")
    progress: Dict[str, Any] = Field(..., description="Progress information")


class SystemStatusResponse(BaseModel):
    """Response model for system status."""
    
    total_active_executions: int = Field(..., description="Total active executions across all tenants")
    tenant_count: int = Field(..., description="Number of active tenants")
    monitoring_enabled: bool = Field(..., description="Whether monitoring is enabled")
    tenant_stats: Dict[str, Any] = Field(..., description="Per-tenant statistics")


@router.post("/{agent_id}/execute", response_model=ExecuteAgentResponse)
async def execute_agent(
    agent_id: UUID,
    request: ExecuteAgentRequest,
    background_tasks: BackgroundTasks,
    session_and_context = Depends(get_tenant_aware_session),
    current_user: Dict[str, Any] = Depends(lambda: {"user_id": "system"})  # TODO: Replace with actual auth
):
    """Execute an agent asynchronously."""
    session, tenant_context = session_and_context
    
    if not tenant_context:
        raise HTTPException(status_code=400, detail="Tenant context required")
    
    executor = lifecycle_manager.get_executor(session, tenant_context.tenant_id)
    
    try:
        execution_id = await executor.start_agent_execution(
            agent_id=str(agent_id),
            input_data=request.input_data,
            session_id=request.session_id,
            timeout_seconds=request.timeout_seconds,
            created_by=current_user["user_id"]
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
        raise HTTPException(status_code=500, detail=f"Failed to start execution: {str(e)}")


@router.post("/executions/{execution_id}/stop")
async def stop_execution(
    execution_id: UUID,
    session_and_context = Depends(get_tenant_aware_session),
    current_user: Dict[str, Any] = Depends(lambda: {"user_id": "system"})  # TODO: Replace with actual auth
):
    """Stop a running agent execution."""
    session, tenant_context = session_and_context
    
    if not tenant_context:
        raise HTTPException(status_code=400, detail="Tenant context required")
    
    executor = lifecycle_manager.get_executor(session, tenant_context.tenant_id)
    
    success = await executor.stop_agent_execution(str(execution_id))
    
    if not success:
        raise HTTPException(status_code=404, detail="Execution not found or not running")
    
    return {"message": "Execution stopped successfully"}


@router.post("/executions/{execution_id}/restart", response_model=ExecuteAgentResponse)
async def restart_execution(
    execution_id: UUID,
    session_and_context = Depends(get_tenant_aware_session),
    current_user: Dict[str, Any] = Depends(lambda: {"user_id": "system"})  # TODO: Replace with actual auth
):
    """Restart a failed or cancelled agent execution."""
    session, tenant_context = session_and_context
    
    if not tenant_context:
        raise HTTPException(status_code=400, detail="Tenant context required")
    
    executor = lifecycle_manager.get_executor(session, tenant_context.tenant_id)
    
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
    session_and_context = Depends(get_tenant_aware_session)
):
    """Get the status of an agent execution."""
    session, tenant_context = session_and_context
    
    if not tenant_context:
        raise HTTPException(status_code=400, detail="Tenant context required")
    
    executor = lifecycle_manager.get_executor(session, tenant_context.tenant_id)
    
    status_info = await executor.get_execution_status(str(execution_id))
    
    if not status_info:
        raise HTTPException(status_code=404, detail="Execution not found")
    
    return ExecutionStatusResponse(**status_info)


@router.get("/executions/active", response_model=List[ActiveExecutionResponse])
async def list_active_executions(
    session_and_context = Depends(get_tenant_aware_session)
):
    """List all currently active executions for the tenant."""
    session, tenant_context = session_and_context
    
    if not tenant_context:
        raise HTTPException(status_code=400, detail="Tenant context required")
    
    executor = lifecycle_manager.get_executor(session, tenant_context.tenant_id)
    
    active_executions = await executor.list_active_executions()
    
    return [ActiveExecutionResponse(**execution) for execution in active_executions]


@router.get("/{agent_id}/executions", response_model=List[ExecutionStatusResponse])
async def list_agent_executions(
    agent_id: UUID,
    status_filter: Optional[ExecutionStatus] = None,
    limit: int = 50,
    offset: int = 0,
    session_and_context = Depends(get_tenant_aware_session)
):
    """List executions for a specific agent."""
    session, tenant_context = session_and_context
    
    if not tenant_context:
        raise HTTPException(status_code=400, detail="Tenant context required")
    
    executor = lifecycle_manager.get_executor(session, tenant_context.tenant_id)
    
    # Get executions from database
    from sqlalchemy import select, and_
    
    stmt = select(AgentExecution).where(
        and_(
            AgentExecution.tenant_id == tenant_context.tenant_id,
            AgentExecution.agent_id == str(agent_id)
        )
    )
    
    if status_filter:
        stmt = stmt.where(AgentExecution.status == status_filter.value)
    
    stmt = stmt.order_by(AgentExecution.started_at.desc()).limit(limit).offset(offset)
    
    result = await session.execute(stmt)
    executions = result.scalars().all()
    
    # Convert to response format
    execution_responses = []
    for execution in executions:
        # Check if execution is currently active
        is_active = execution.id in executor.active_executions
        progress = None
        
        if is_active:
            context = executor.active_executions[execution.id]
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
    session_and_context = Depends(get_tenant_aware_session),
    current_user: Dict[str, Any] = Depends(lambda: {"user_id": "system"})  # TODO: Replace with actual auth
):
    """Clean up stale executions for the tenant."""
    session, tenant_context = session_and_context
    
    if not tenant_context:
        raise HTTPException(status_code=400, detail="Tenant context required")
    
    executor = lifecycle_manager.get_executor(session, tenant_context.tenant_id)
    
    cleaned_count = await executor.cleanup_stale_executions(max_age_hours)
    
    return {
        "message": f"Cleaned up {cleaned_count} stale executions",
        "cleaned_count": cleaned_count
    }


@router.get("/system/status", response_model=SystemStatusResponse)
async def get_system_status(
    current_user: Dict[str, Any] = Depends(lambda: {"user_id": "system"})  # TODO: Replace with actual auth
):
    """Get overall system status (admin only)."""
    # TODO: Add admin role check
    
    status = await lifecycle_manager.get_system_status()
    
    return SystemStatusResponse(**status)


@router.post("/system/start-monitoring")
async def start_monitoring(
    current_user: Dict[str, Any] = Depends(lambda: {"user_id": "system"})  # TODO: Replace with actual auth
):
    """Start system monitoring (admin only)."""
    # TODO: Add admin role check
    
    await lifecycle_manager.start_monitoring()
    
    return {"message": "System monitoring started"}


@router.post("/system/stop-monitoring")
async def stop_monitoring(
    current_user: Dict[str, Any] = Depends(lambda: {"user_id": "system"})  # TODO: Replace with actual auth
):
    """Stop system monitoring (admin only)."""
    # TODO: Add admin role check
    
    await lifecycle_manager.stop_monitoring()
    
    return {"message": "System monitoring stopped"}


# Health check endpoint for the executor service
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