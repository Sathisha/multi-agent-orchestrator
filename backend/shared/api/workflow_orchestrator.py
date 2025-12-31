"""API endpoints for BPMN Workflow Orchestrator."""

import logging
from typing import Dict, List, Optional, Any, Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy import select, and_, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..database import get_database_session
from ..middleware.tenant import get_tenant_context, TenantContext
from ..middleware.security import SecurityConfig
from ..api.auth import get_current_user
from ..models.user import User
from ..models.workflow import (
    Workflow, WorkflowExecution, ExecutionLog,
    WorkflowRequest, WorkflowResponse, WorkflowExecutionRequest, 
    WorkflowExecutionResponse, ExecutionLogResponse, WorkflowExecutionControlRequest,
    WorkflowStatistics, WorkflowStatus, ExecutionStatus, ExecutionPriority
)
from ..services.workflow_orchestrator import WorkflowOrchestratorService, BPMNValidationError, WorkflowExecutionError
from ..services.rbac import RBACService, require_permission


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/workflows", tags=["Workflow Orchestrator"])

# Initialize services lazily
_workflow_orchestrator_instance: Optional[WorkflowOrchestratorService] = None


def get_workflow_orchestrator_service() -> WorkflowOrchestratorService:
    """Get or create the workflow orchestrator service singleton."""
    global _workflow_orchestrator_instance
    if _workflow_orchestrator_instance is None:
        _workflow_orchestrator_instance = WorkflowOrchestratorService()
    return _workflow_orchestrator_instance


async def get_rbac_service(
    session: AsyncSession = Depends(get_database_session)
) -> RBACService:
    """Get RBAC service with the current database session."""
    return RBACService(session)


def require_permission_dependency(permission: str):
    """Dependency factory for permission checking."""
    async def _require_permission(
        current_user: User = Depends(get_current_user),
        tenant_context: TenantContext = Depends(get_tenant_context),
        rbac_service: RBACService = Depends(get_rbac_service)
    ):
        await require_permission(rbac_service, current_user.id, permission, tenant_context.tenant_id)
    return _require_permission


@router.on_event("startup")
async def startup_event():
    """Initialize workflow orchestrator on startup."""
    try:
        service = get_workflow_orchestrator_service()
        await service.initialize()
        logger.info("Workflow orchestrator API initialized")
    except Exception as e:
        logger.error(f"Failed to initialize workflow orchestrator API: {e}")


@router.on_event("shutdown")
async def shutdown_event():
    """Shutdown workflow orchestrator."""
    try:
        service = get_workflow_orchestrator_service()
        await service.shutdown()
        logger.info("Workflow orchestrator API shutdown completed")
    except Exception as e:
        logger.error(f"Error during workflow orchestrator API shutdown: {e}")


@router.post("/", response_model=WorkflowResponse, status_code=status.HTTP_201_CREATED)
async def create_workflow(
    workflow_request: WorkflowRequest,
    session: AsyncSession = Depends(get_database_session),
    current_user: User = Depends(get_current_user),
    tenant_context: TenantContext = Depends(get_tenant_context),
    rbac_service: RBACService = Depends(get_rbac_service)
):
    """Create a new BPMN workflow."""
    # Check permissions
    await require_permission(rbac_service, current_user.id, "workflow:create", tenant_context.tenant_id)
    
    # Get service instance
    workflow_orchestrator = get_workflow_orchestrator_service()
    
    try:
        # Validate BPMN XML
        validation_result = await workflow_orchestrator.validate_bpmn(
            workflow_request.bpmn_xml, 
            tenant_context.tenant_id
        )
        
        if not validation_result['valid']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "BPMN validation failed",
                    "errors": validation_result['errors'],
                    "warnings": validation_result['warnings']
                }
            )
        
        # Extract process definition key from BPMN
        from ..services.bpmn_utils import BPMNParser
        bpmn_parser = BPMNParser()
        process_definition_key = bpmn_parser.extract_process_definition_key(workflow_request.bpmn_xml)
        
        if not process_definition_key:
            # Fallback to generating from name
            process_definition_key = workflow_request.name.lower().replace(' ', '_')
        
        # Create workflow
        workflow = Workflow(
            tenant_id=tenant_context.tenant_id,
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
            required_agents=validation_result.get('agent_dependencies', []),
            required_tools=validation_result.get('tool_dependencies', []),
            created_by=current_user.id
        )
        
        session.add(workflow)
        await session.commit()
        await session.refresh(workflow)
        
        logger.info(f"Created workflow {workflow.name} (ID: {workflow.id}) for tenant {tenant_context.tenant_id}")
        
        return WorkflowResponse.model_validate(workflow)
        
    except BPMNValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"BPMN validation error: {e}"
        )
    except Exception as e:
        logger.error(f"Failed to create workflow: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create workflow: {e}"
        )


@router.get("/", response_model=List[WorkflowResponse])
async def list_workflows(
    status_filter: Optional[WorkflowStatus] = Query(None, description="Filter by workflow status"),
    category: Optional[str] = Query(None, description="Filter by category"),
    limit: int = Query(50, ge=1, le=100, description="Number of workflows to return"),
    offset: int = Query(0, ge=0, description="Number of workflows to skip"),
    session: AsyncSession = Depends(get_database_session),
    current_user: User = Depends(get_current_user),
    tenant_context: TenantContext = Depends(get_tenant_context),
    rbac_service: RBACService = Depends(get_rbac_service)
):
    """List workflows for the current tenant."""
    # Check permissions
    await require_permission(rbac_service, current_user.id, "workflow:read", tenant_context.tenant_id)
    
    try:
        # Build query
        stmt = select(Workflow).where(Workflow.tenant_id == tenant_context.tenant_id)
        
        if status_filter:
            stmt = stmt.where(Workflow.status == status_filter)
        
        if category:
            stmt = stmt.where(Workflow.category == category)
        
        stmt = stmt.order_by(desc(Workflow.created_at)).offset(offset).limit(limit)
        
        result = await session.execute(stmt)
        workflows = result.scalars().all()
        
        # Add execution count for each workflow
        workflow_responses = []
        for workflow in workflows:
            execution_count_stmt = select(func.count(WorkflowExecution.id)).where(
                WorkflowExecution.workflow_id == workflow.id
            )
            execution_count_result = await session.execute(execution_count_stmt)
            execution_count = execution_count_result.scalar() or 0
            
            workflow_dict = workflow.__dict__.copy()
            workflow_dict['execution_count'] = execution_count
            workflow_responses.append(WorkflowResponse.model_validate(workflow_dict))
        
        return workflow_responses
        
    except Exception as e:
        logger.error(f"Failed to list workflows: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list workflows: {e}"
        )


@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(
    workflow_id: UUID,
    session: AsyncSession = Depends(get_database_session),
    current_user: User = Depends(get_current_user),
    tenant_context: TenantContext = Depends(get_tenant_context),
    rbac_service: RBACService = Depends(get_rbac_service)
):
    """Get a specific workflow."""
    # Check permissions
    await require_permission(rbac_service, current_user.id, "workflow:read", tenant_context.tenant_id)
    
    try:
        stmt = select(Workflow).where(
            and_(Workflow.id == workflow_id, Workflow.tenant_id == tenant_context.tenant_id)
        )
        result = await session.execute(stmt)
        workflow = result.scalar_one_or_none()
        
        if not workflow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow {workflow_id} not found"
            )
        
        # Add execution count
        execution_count_stmt = select(func.count(WorkflowExecution.id)).where(
            WorkflowExecution.workflow_id == workflow.id
        )
        execution_count_result = await session.execute(execution_count_stmt)
        execution_count = execution_count_result.scalar() or 0
        
        workflow_dict = workflow.__dict__.copy()
        workflow_dict['execution_count'] = execution_count
        
        return WorkflowResponse.model_validate(workflow_dict)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get workflow {workflow_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get workflow: {e}"
        )


@router.put("/{workflow_id}", response_model=WorkflowResponse)
async def update_workflow(
    workflow_id: UUID,
    workflow_request: WorkflowRequest,
    session: AsyncSession = Depends(get_database_session),
    current_user: User = Depends(get_current_user),
    tenant_context: TenantContext = Depends(get_tenant_context),
    rbac_service: RBACService = Depends(get_rbac_service)
):
    """Update a workflow."""
    # Get service instance
    workflow_orchestrator = get_workflow_orchestrator_service()
    # Check permissions
    await require_permission(rbac_service, current_user.id, "workflow:update", tenant_context.tenant_id)
    
    try:
        stmt = select(Workflow).where(
            and_(Workflow.id == workflow_id, Workflow.tenant_id == tenant_context.tenant_id)
        )
        result = await session.execute(stmt)
        workflow = result.scalar_one_or_none()
        
        if not workflow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow {workflow_id} not found"
            )
        
        # Validate BPMN XML
        validation_result = await workflow_orchestrator.validate_bpmn(
            workflow_request.bpmn_xml, 
            tenant_context.tenant_id
        )
        
        if not validation_result['valid']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "BPMN validation failed",
                    "errors": validation_result['errors'],
                    "warnings": validation_result['warnings']
                }
            )
        
        # Update workflow
        workflow.name = workflow_request.name
        workflow.description = workflow_request.description
        workflow.version = workflow_request.version
        workflow.bpmn_xml = workflow_request.bpmn_xml
        workflow.category = workflow_request.category
        workflow.tags = workflow_request.tags
        workflow.input_schema = workflow_request.input_schema or {}
        workflow.output_schema = workflow_request.output_schema or {}
        workflow.default_variables = workflow_request.default_variables or {}
        workflow.timeout_minutes = workflow_request.timeout_minutes
        workflow.max_concurrent_executions = workflow_request.max_concurrent_executions
        workflow.required_agents = validation_result.get('agent_dependencies', [])
        workflow.required_tools = validation_result.get('tool_dependencies', [])
        workflow.updated_at = workflow.updated_at  # This will be auto-updated by the model
        
        await session.commit()
        await session.refresh(workflow)
        
        logger.info(f"Updated workflow {workflow.name} (ID: {workflow.id})")
        
        return WorkflowResponse.model_validate(workflow)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update workflow {workflow_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update workflow: {e}"
        )


@router.post("/{workflow_id}/deploy")
async def deploy_workflow(
    workflow_id: UUID,
    current_user: User = Depends(get_current_user),
    tenant_context: TenantContext = Depends(get_tenant_context)
):
    """Deploy a workflow to the Zeebe engine."""
    # Check permissions
    await require_permission(rbac_service, current_user.id, "workflow:deploy", tenant_context.tenant_id)
    
    try:
        deployment_result = await workflow_orchestrator.deploy_workflow(
            workflow_id, 
            tenant_context.tenant_id
        )
        
        logger.info(f"Deployed workflow {workflow_id} for tenant {tenant_context.tenant_id}")
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "Workflow deployed successfully",
                "deployment": deployment_result
            }
        )
        
    except WorkflowExecutionError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to deploy workflow {workflow_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to deploy workflow: {e}"
        )


@router.post("/{workflow_id}/execute", response_model=WorkflowExecutionResponse, status_code=status.HTTP_201_CREATED)
async def start_workflow_execution(
    workflow_id: UUID,
    execution_request: WorkflowExecutionRequest,
    current_user: User = Depends(get_current_user),
    tenant_context: TenantContext = Depends(get_tenant_context)
):
    """Start a new workflow execution."""
    # Check permissions
    await require_permission(rbac_service, current_user.id, "workflow:execute", tenant_context.tenant_id)
    
    try:
        execution_id = await workflow_orchestrator.start_workflow_execution(
            workflow_id=workflow_id,
            tenant_id=tenant_context.tenant_id,
            input_data=execution_request.input_data,
            variables=execution_request.variables,
            priority=execution_request.priority,
            correlation_id=execution_request.correlation_id
        )
        
        # Get execution details
        execution_status = await workflow_orchestrator.get_workflow_execution_status(
            execution_id, 
            tenant_context.tenant_id
        )
        
        if not execution_status:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve execution status"
            )
        
        logger.info(f"Started workflow execution {execution_id} for workflow {workflow_id}")
        
        return WorkflowExecutionResponse.model_validate(execution_status)
        
    except WorkflowExecutionError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to start workflow execution: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start execution: {e}"
        )


@router.get("/{workflow_id}/executions", response_model=List[WorkflowExecutionResponse])
async def list_workflow_executions(
    workflow_id: UUID,
    status_filter: Optional[ExecutionStatus] = Query(None, description="Filter by execution status"),
    limit: int = Query(50, ge=1, le=100, description="Number of executions to return"),
    offset: int = Query(0, ge=0, description="Number of executions to skip"),
    current_user: User = Depends(get_current_user),
    tenant_context: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_database_session)
):
    """List executions for a specific workflow."""
    # Check permissions
    await require_permission(rbac_service, current_user.id, "workflow:read", tenant_context.tenant_id)
    
    try:
        # Verify workflow exists and belongs to tenant
        workflow_stmt = select(Workflow).where(
            and_(Workflow.id == workflow_id, Workflow.tenant_id == tenant_context.tenant_id)
        )
        workflow_result = await session.execute(workflow_stmt)
        workflow = workflow_result.scalar_one_or_none()
        
        if not workflow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow {workflow_id} not found"
            )
        
        # Build executions query
        stmt = select(WorkflowExecution).where(WorkflowExecution.workflow_id == workflow_id)
        
        if status_filter:
            stmt = stmt.where(WorkflowExecution.status == status_filter)
        
        stmt = stmt.order_by(desc(WorkflowExecution.created_at)).offset(offset).limit(limit)
        
        result = await session.execute(stmt)
        executions = result.scalars().all()
        
        # Convert to response models
        execution_responses = []
        for execution in executions:
            progress_percentage = None
            if execution.status == ExecutionStatus.RUNNING:
                progress_percentage = await workflow_orchestrator._calculate_execution_progress(execution)
            
            execution_dict = execution.__dict__.copy()
            execution_dict['workflow_id'] = str(execution.workflow_id)
            execution_dict['progress_percentage'] = progress_percentage
            execution_responses.append(WorkflowExecutionResponse.model_validate(execution_dict))
        
        return execution_responses
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list workflow executions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list executions: {e}"
        )


@router.get("/executions/{execution_id}", response_model=WorkflowExecutionResponse)
async def get_workflow_execution(
    execution_id: UUID,
    current_user: User = Depends(get_current_user),
    tenant_context: TenantContext = Depends(get_tenant_context)
):
    """Get details of a specific workflow execution."""
    # Check permissions
    await require_permission(rbac_service, current_user.id, "workflow:read", tenant_context.tenant_id)
    
    try:
        execution_status = await workflow_orchestrator.get_workflow_execution_status(
            execution_id, 
            tenant_context.tenant_id
        )
        
        if not execution_status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Execution {execution_id} not found"
            )
        
        return WorkflowExecutionResponse.model_validate(execution_status)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get workflow execution {execution_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get execution: {e}"
        )


@router.post("/executions/{execution_id}/control")
async def control_workflow_execution(
    execution_id: UUID,
    control_request: WorkflowExecutionControlRequest,
    current_user: User = Depends(get_current_user),
    tenant_context: TenantContext = Depends(get_tenant_context)
):
    """Control a workflow execution (pause, resume, cancel)."""
    # Check permissions
    await require_permission(rbac_service, current_user.id, "workflow:control", tenant_context.tenant_id)
    
    try:
        action = control_request.action.lower()
        reason = control_request.reason
        
        if action == "pause":
            await workflow_orchestrator.pause_workflow_execution(
                execution_id, 
                tenant_context.tenant_id, 
                reason
            )
            message = "Workflow execution paused"
            
        elif action == "resume":
            await workflow_orchestrator.resume_workflow_execution(
                execution_id, 
                tenant_context.tenant_id, 
                reason
            )
            message = "Workflow execution resumed"
            
        elif action == "cancel":
            await workflow_orchestrator.cancel_workflow_execution(
                execution_id, 
                tenant_context.tenant_id, 
                reason
            )
            message = "Workflow execution cancelled"
            
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid action: {action}"
            )
        
        logger.info(f"Executed {action} on workflow execution {execution_id}")
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": message, "action": action, "reason": reason}
        )
        
    except WorkflowExecutionError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to control workflow execution {execution_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to control execution: {e}"
        )


@router.get("/executions/{execution_id}/logs", response_model=List[ExecutionLogResponse])
async def get_execution_logs(
    execution_id: UUID,
    level_filter: Optional[str] = Query(None, description="Filter by log level (DEBUG, INFO, WARN, ERROR)"),
    limit: int = Query(100, ge=1, le=1000, description="Number of log entries to return"),
    offset: int = Query(0, ge=0, description="Number of log entries to skip"),
    current_user: User = Depends(get_current_user),
    tenant_context: TenantContext = Depends(get_tenant_context)
):
    """Get execution logs for a workflow execution."""
    # Check permissions
    await require_permission(rbac_service, current_user.id, "workflow:read", tenant_context.tenant_id)
    
    try:
        logs = await workflow_orchestrator.get_execution_logs(
            execution_id=execution_id,
            tenant_id=tenant_context.tenant_id,
            limit=limit,
            offset=offset,
            level_filter=level_filter
        )
        
        return [ExecutionLogResponse.model_validate(log) for log in logs]
        
    except Exception as e:
        logger.error(f"Failed to get execution logs for {execution_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get execution logs: {e}"
        )


@router.get("/{workflow_id}/statistics", response_model=WorkflowStatistics)
async def get_workflow_statistics(
    workflow_id: UUID,
    current_user: User = Depends(get_current_user),
    tenant_context: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_database_session),
    rbac_service: RBACService = Depends(get_rbac_service)
):
    """Get statistics for a workflow."""
    # Check permissions
    await require_permission(rbac_service, current_user.id, "workflow:read", tenant_context.tenant_id)
    
    try:
        # Verify workflow exists
        workflow_stmt = select(Workflow).where(
            and_(Workflow.id == workflow_id, Workflow.tenant_id == tenant_context.tenant_id)
        )
        workflow_result = await session.execute(workflow_stmt)
        workflow = workflow_result.scalar_one_or_none()
        
        if not workflow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow {workflow_id} not found"
            )
        
        # Calculate statistics
        total_stmt = select(func.count(WorkflowExecution.id)).where(
            WorkflowExecution.workflow_id == workflow_id
        )
        total_result = await session.execute(total_stmt)
        total_executions = total_result.scalar() or 0
        
        successful_stmt = select(func.count(WorkflowExecution.id)).where(
            and_(
                WorkflowExecution.workflow_id == workflow_id,
                WorkflowExecution.status == ExecutionStatus.COMPLETED
            )
        )
        successful_result = await session.execute(successful_stmt)
        successful_executions = successful_result.scalar() or 0
        
        failed_stmt = select(func.count(WorkflowExecution.id)).where(
            and_(
                WorkflowExecution.workflow_id == workflow_id,
                WorkflowExecution.status == ExecutionStatus.FAILED
            )
        )
        failed_result = await session.execute(failed_stmt)
        failed_executions = failed_result.scalar() or 0
        
        # Calculate average duration
        avg_duration_stmt = select(func.avg(WorkflowExecution.duration_seconds)).where(
            and_(
                WorkflowExecution.workflow_id == workflow_id,
                WorkflowExecution.duration_seconds.isnot(None)
            )
        )
        avg_duration_result = await session.execute(avg_duration_stmt)
        average_duration_seconds = avg_duration_result.scalar()
        
        # Calculate success rate
        success_rate = (successful_executions / total_executions * 100) if total_executions > 0 else 0.0
        
        statistics = WorkflowStatistics(
            total_executions=total_executions,
            successful_executions=successful_executions,
            failed_executions=failed_executions,
            average_duration_seconds=float(average_duration_seconds) if average_duration_seconds else None,
            success_rate=success_rate
        )
        
        return statistics
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get workflow statistics for {workflow_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get statistics: {e}"
        )


@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workflow(
    workflow_id: UUID,
    current_user: User = Depends(get_current_user),
    tenant_context: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_database_session),
    rbac_service: RBACService = Depends(get_rbac_service)
):
    """Delete a workflow."""
    # Check permissions
    await require_permission(rbac_service, current_user.id, "workflow:delete", tenant_context.tenant_id)
    
    try:
        stmt = select(Workflow).where(
            and_(Workflow.id == workflow_id, Workflow.tenant_id == tenant_context.tenant_id)
        )
        result = await session.execute(stmt)
        workflow = result.scalar_one_or_none()
        
        if not workflow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow {workflow_id} not found"
            )
        
        # Check for active executions
        active_executions_stmt = select(func.count(WorkflowExecution.id)).where(
            and_(
                WorkflowExecution.workflow_id == workflow_id,
                WorkflowExecution.status.in_([
                    ExecutionStatus.PENDING,
                    ExecutionStatus.RUNNING,
                    ExecutionStatus.PAUSED
                ])
            )
        )
        active_count_result = await session.execute(active_executions_stmt)
        active_count = active_count_result.scalar() or 0
        
        if active_count > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot delete workflow with {active_count} active executions"
            )
        
        # Delete workflow (cascades to executions and logs)
        await session.delete(workflow)
        await session.commit()
        
        logger.info(f"Deleted workflow {workflow.name} (ID: {workflow_id})")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete workflow {workflow_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete workflow: {e}"
        )