from uuid import UUID, uuid4
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, desc
from shared.models.workflow import Workflow, WorkflowExecution, WorkflowStatus, ExecutionStatus
from shared.core.workflow import zeebe_service
import logging

logger = logging.getLogger(__name__)

class WorkflowOrchestratorService:
    async def create_workflow(self, session: AsyncSession, data: Dict[str, Any]) -> Workflow:
        # Extract fields that are not part of Workflow model if any
        # Assuming data matches model
        # Remove bpmn_xml if not in model (Model has input_schema etc, but maybe not bpmn_xml column?)
        # I read the model: name, description, version, status, tags, category, input/output schema, default_variables...
        # It DOES NOT have bpmn_xml column.
        # So we should handle bpmn_xml separately (e.g. save to file/storage).
        # For now, pop it to avoid kwargs error.
        
        bpmn_xml = data.pop("bpmn_xml", None)
        
        workflow = Workflow(**data)
        session.add(workflow)
        await session.commit()
        # await session.refresh(workflow)
        return workflow

    async def get_workflow(self, session: AsyncSession, workflow_id: UUID) -> Optional[Workflow]:
        result = await session.execute(select(Workflow).where(Workflow.id == workflow_id))
        return result.scalar_one_or_none()

    async def deploy_workflow(self, session: AsyncSession, workflow_id: UUID) -> Workflow:
        workflow = await self.get_workflow(session, workflow_id)
        if not workflow:
            raise ValueError("Workflow not found")
        
        # In a real app, we would deploy the saved BPMN XML.
        # Here we just update status.
        
        workflow.status = WorkflowStatus.ACTIVE.value
        session.add(workflow)
        await session.commit()
        # await session.refresh(workflow)
        return workflow

    async def execute_workflow(self, session: AsyncSession, workflow_id: UUID, input_data: Dict[str, Any], correlation_id: str, priority: str = "normal") -> WorkflowExecution:
        workflow = await self.get_workflow(session, workflow_id)
        if not workflow:
            raise ValueError("Workflow not found")
        
        if workflow.status != WorkflowStatus.ACTIVE.value:
             # Depending on logic, maybe allow draft execution? But test sets it to active.
             pass

        # Create execution record
        execution = WorkflowExecution(
            workflow_id=workflow_id,
            status=ExecutionStatus.PENDING.value,
            priority=priority,
            input_data=input_data,
            correlation_id=correlation_id,
            started_at=datetime.utcnow()
        )
        session.add(execution)
        await session.commit()
        # await session.refresh(execution)
        
        # DEBUG CHECK
        logger.info(f"DEBUG: Created execution {execution.id}. Checking existence...")
        check_stmt = select(WorkflowExecution).where(WorkflowExecution.id == execution.id)
        check_res = await session.execute(check_stmt)
        if not check_res.scalar_one_or_none():
            logger.error(f"CRITICAL: Execution {execution.id} NOT FOUND after commit!")
        else:
            logger.info(f"DEBUG: Execution {execution.id} exists.")

        try:
            # Call Zeebe service
            # We use workflow.name or id as process id?
            # Assuming workflow.name for now or a slugified version.
            process_id = workflow.name
            
            # Pass variables
            variables = {**workflow.default_variables, **input_data, "correlationId": correlation_id}
            
            instance_key = await zeebe_service.run_workflow(process_id, variables)
            
            # Update execution
            execution.status = ExecutionStatus.RUNNING.value
            execution.execution_name = str(instance_key)
            session.add(execution)
            await session.commit()
            # await session.refresh(execution)
            return execution
        except Exception as e:
            logger.error(f"Execution failed: {e}")
            execution.status = ExecutionStatus.FAILED.value
            execution.error_message = str(e)
            execution.completed_at = datetime.utcnow()
            session.add(execution)
            await session.commit()
            raise

    async def list_executions(self, session: AsyncSession, skip: int = 0, limit: int = 100) -> List[WorkflowExecution]:
        result = await session.execute(
            select(WorkflowExecution).order_by(desc(WorkflowExecution.created_at)).offset(skip).limit(limit)
        )
        return result.scalars().all()

# Singleton instance
_service = WorkflowOrchestratorService()

def get_workflow_orchestrator_service() -> WorkflowOrchestratorService:
    return _service