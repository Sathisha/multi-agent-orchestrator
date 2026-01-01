"""API endpoints for BPMN Workflow Orchestrator."""

import logging
from typing import Dict, List, Optional, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy import select, and_, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_async_db
from ..services.auth import get_current_user
from ..models.user import User
from ..models.workflow import (
    Workflow, WorkflowExecution, ExecutionLog,
    WorkflowStatus, ExecutionStatus
)
from ..schemas.workflow import (
    WorkflowRequest, WorkflowResponse, WorkflowExecutionRequest, 
    WorkflowExecutionResponse, ExecutionLogResponse, WorkflowExecutionControlRequest,
    WorkflowStatistics
)
from ..services.workflow_orchestrator import WorkflowOrchestratorService, BPMNValidationError, WorkflowExecutionError
# from ..services.rbac import RBACService # RBAC currently disabled/simplified in this refactor to avoid complexity

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/workflows", tags=["Workflow Orchestrator"])

# Initialize services lazily
_workflow_orchestrator_instance: Optional[WorkflowOrchestratorService] = None

def get_workflow_orchestrator_service() -> WorkflowOrchestratorService:
    global _workflow_orchestrator_instance
    if _workflow_orchestrator_instance is None:
        _workflow_orchestrator_instance = WorkflowOrchestratorService()
    return _workflow_orchestrator_instance

@router.on_event("startup")
async def startup_event():
    try:
        service = get_workflow_orchestrator_service()
        await service.initialize()
        logger.info("Workflow orchestrator API initialized")
    except Exception as e:
        logger.error(f"Failed to initialize workflow orchestrator API: {e}")

@router.on_event("shutdown")
async def shutdown_event():
    try:
        service = get_workflow_orchestrator_service()
        await service.shutdown()
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")

@router.post("/", response_model=WorkflowResponse, status_code=status.HTTP_201_CREATED)
async def create_workflow(
    workflow_request: WorkflowRequest,
    session: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    workflow_orchestrator = get_workflow_orchestrator_service()
    
    try:
        validation_result = await workflow_orchestrator.validate_bpmn(workflow_request.bpmn_xml)
        if not validation_result['valid']:
            raise HTTPException(status_code=400, detail={"message": "BPMN validation failed", "errors": validation_result['errors']})
        
        # Simple extraction or default
        process_definition_key = workflow_request.name.lower().replace(' ', '_')
        
        workflow = Workflow(
            name=workflow_request.name,
            description=workflow_request.description,
            version=workflow_request.version,
            bpmn_xml=workflow_request.bpmn_xml,
            process_definition_key=process_definition_key,
            status=WorkflowStatus.DRAFT,
            category=workflow_request.category,
            tags=workflow_request.tags,
            input_schema=workflow_request.input_schema or {},
            output_schema=workflow_request.output_schema or {},
            default_variables=workflow_request.default_variables or {},
            timeout_minutes=workflow_request.timeout_minutes,
            max_concurrent_executions=workflow_request.max_concurrent_executions,
            created_by=current_user.id
        )
        
        session.add(workflow)
        await session.commit()
        await session.refresh(workflow)
        
        return WorkflowResponse.model_validate(workflow)
        
    except BPMNValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_model=List[WorkflowResponse])
async def list_workflows(
    status_filter: Optional[WorkflowStatus] = Query(None),
    category: Optional[str] = Query(None),
    limit: int = 50,
    offset: int = 0,
    session: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    try:
        stmt = select(Workflow)
        if status_filter: stmt = stmt.where(Workflow.status == status_filter)
        if category: stmt = stmt.where(Workflow.category == category)
        stmt = stmt.order_by(desc(Workflow.created_at)).offset(offset).limit(limit)
        
        result = await session.execute(stmt)
        workflows = result.scalars().all()
        
        responses = []
        for wf in workflows:
            wf_dict = wf.__dict__.copy()
            # Count executions (simplified)
            stmt_count = select(func.count(WorkflowExecution.id)).where(WorkflowExecution.workflow_id == wf.id)
            wf_dict['execution_count'] = (await session.execute(stmt_count)).scalar() or 0
            responses.append(WorkflowResponse.model_validate(wf_dict))
            
        return responses
    except Exception as e:
        logger.error(f"Failed to list workflows: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/executions", response_model=List[WorkflowExecutionResponse])
async def list_executions(
    status_filter: Optional[ExecutionStatus] = Query(None),
    limit: int = 50,
    offset: int = 0,
    session: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    try:
        stmt = select(WorkflowExecution, Workflow.name).join(Workflow, Workflow.id == WorkflowExecution.workflow_id)
        if status_filter: stmt = stmt.where(WorkflowExecution.status == status_filter)
        stmt = stmt.order_by(desc(WorkflowExecution.started_at)).offset(offset).limit(limit)
        
        result = await session.execute(stmt)
        rows = result.all()
        
        responses = []
        for execution, wf_name in rows:
            ex_dict = execution.__dict__.copy()
            ex_dict['workflow_name'] = wf_name
            responses.append(WorkflowExecutionResponse.model_validate(ex_dict))
            
        return responses
    except Exception as e:
        logger.error(f"Failed to list executions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{workflow_id}/execute", response_model=WorkflowExecutionResponse)
async def start_workflow_execution(
    workflow_id: UUID,
    execution_request: WorkflowExecutionRequest,
    current_user: User = Depends(get_current_user)
):
    workflow_orchestrator = get_workflow_orchestrator_service()
    try:
        execution_id = await workflow_orchestrator.start_workflow_execution(
            workflow_id=workflow_id,
            input_data=execution_request.input_data,
            variables=execution_request.variables,
            priority=execution_request.priority,
            correlation_id=execution_request.correlation_id
        )
        
        status_info = await workflow_orchestrator.get_workflow_execution_status(execution_id)
        return WorkflowExecutionResponse.model_validate(status_info)
    except Exception as e:
        logger.error(f"Failed execution start: {e}")
        raise HTTPException(status_code=500, detail=str(e))