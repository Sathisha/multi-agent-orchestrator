from typing import List, Optional, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from shared.database.connection import get_async_db
from shared.services.workflow_orchestrator import get_workflow_orchestrator_service, WorkflowOrchestratorService
from shared.models.workflow import WorkflowStatus, ExecutionStatus

router = APIRouter(prefix="/api/v1/workflows", tags=["Workflows"])

# Pydantic models for request/response
class WorkflowCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    version: str = "1.0.0"
    bpmn_xml: Optional[str] = None
    category: Optional[str] = None
    tags: List[str] = []
    input_schema: Dict[str, Any] = {}
    output_schema: Dict[str, Any] = {}
    timeout_minutes: Optional[int] = None
    max_concurrent_executions: int = 10

class WorkflowResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    version: str
    status: str
    category: Optional[str] = None
    tags: List[str]
    created_at: Any
    updated_at: Any

class WorkflowExecuteRequest(BaseModel):
    input_data: Dict[str, Any]
    priority: str = "normal"
    correlation_id: str

class ExecutionResponse(BaseModel):
    id: UUID
    workflow_id: UUID
    status: str
    execution_name: Optional[str] = None
    started_at: Optional[Any] = None
    completed_at: Optional[Any] = None
    error_message: Optional[str] = None

@router.post("", response_model=WorkflowResponse, status_code=status.HTTP_201_CREATED)
async def create_workflow(
    request: WorkflowCreateRequest,
    session: AsyncSession = Depends(get_async_db),
    service: WorkflowOrchestratorService = Depends(get_workflow_orchestrator_service)
):
    try:
        workflow = await service.create_workflow(session, request.model_dump())
        return workflow
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(
    workflow_id: UUID,
    session: AsyncSession = Depends(get_async_db),
    service: WorkflowOrchestratorService = Depends(get_workflow_orchestrator_service)
):
    workflow = await service.get_workflow(session, workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return workflow

@router.post("/{workflow_id}/execute", response_model=ExecutionResponse)
async def execute_workflow(
    workflow_id: UUID,
    request: WorkflowExecuteRequest,
    session: AsyncSession = Depends(get_async_db),
    service: WorkflowOrchestratorService = Depends(get_workflow_orchestrator_service)
):
    try:
        execution = await service.execute_workflow(
            session, 
            workflow_id, 
            request.input_data, 
            request.correlation_id,
            request.priority
        )
        return execution
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/executions", response_model=List[ExecutionResponse])
async def list_executions(
    skip: int = 0, 
    limit: int = 100,
    session: AsyncSession = Depends(get_async_db),
    service: WorkflowOrchestratorService = Depends(get_workflow_orchestrator_service)
):
    executions = await service.list_executions(session, skip, limit)
    return executions