"""BPMN Workflow Orchestrator Service for the AI Agent Framework."""

import asyncio
import json
import logging
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set, Tuple
from uuid import UUID, uuid4

from lxml import etree
from pyzeebe import ZeebeClient, ZeebeWorker, Job
from pyzeebe.errors import ZeebeBackPressureError, ZeebeGatewayUnavailableError
from sqlalchemy import select, update, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..database import get_database_session
from ..models.workflow import (
    Workflow, WorkflowExecution, ExecutionLog, WorkflowStatus, 
    ExecutionStatus, ExecutionPriority, NodeType
)
from ..models.agent import Agent
from ..services.agent_executor import AgentExecutorService
from ..services.memory_manager import MemoryManagerService
from ..services.guardrails import GuardrailsService
from ..services.bpmn_utils import BPMNValidator, DependencyAnalyzer, BPMNParser
from .base import BaseService


logger = logging.getLogger(__name__)


class BPMNValidationError(Exception):
    """Exception raised when BPMN validation fails."""
    pass


class WorkflowExecutionError(Exception):
    """Exception raised during workflow execution."""
    pass


class CircularDependencyError(Exception):
    """Exception raised when circular dependencies are detected."""
    pass


class WorkflowOrchestratorService(BaseService):
    """Service for orchestrating BPMN workflows with AI agents."""
    
    def __init__(
        self,
        zeebe_gateway_address: str = "localhost:26500",
        agent_executor: Optional[AgentExecutorService] = None,
        memory_manager: Optional[MemoryManagerService] = None,
        guardrails_service: Optional[GuardrailsService] = None
    ):
        super().__init__()
        self.zeebe_gateway_address = zeebe_gateway_address
        self.zeebe_client: Optional[ZeebeClient] = None
        self.zeebe_worker: Optional[ZeebeWorker] = None
        self.agent_executor = agent_executor or AgentExecutorService()
        self.memory_manager = memory_manager or MemoryManagerService()
        self.guardrails_service = guardrails_service or GuardrailsService()
        
        # BPMN utilities
        self.bpmn_validator = BPMNValidator()
        self.dependency_analyzer = DependencyAnalyzer()
        self.bpmn_parser = BPMNParser()
        
        # Active executions tracking
        self.active_executions: Dict[str, Dict[str, Any]] = {}
        
        # BPMN namespace for parsing
        self.bpmn_ns = {
            'bpmn': 'http://www.omg.org/spec/BPMN/20100524/MODEL',
            'bpmndi': 'http://www.omg.org/spec/BPMN/20100524/DI',
            'zeebe': 'http://camunda.org/schema/zeebe/1.0'
        }
    
    async def initialize(self):
        """Initialize the workflow orchestrator and connect to Zeebe."""
        try:
            self.zeebe_client = ZeebeClient(grpc_channel_options=[
                ('grpc.keepalive_time_ms', 30000),
                ('grpc.keepalive_timeout_ms', 5000),
                ('grpc.keepalive_permit_without_calls', True),
                ('grpc.http2.max_pings_without_data', 0),
                ('grpc.http2.min_time_between_pings_ms', 10000),
                ('grpc.http2.min_ping_interval_without_data_ms', 300000)
            ])
            
            # Test connection
            topology = await self.zeebe_client.topology()
            logger.info(f"Connected to Zeebe cluster with {len(topology.brokers)} brokers")
            
            # Initialize worker for agent tasks
            self.zeebe_worker = ZeebeWorker(grpc_channel_options=[
                ('grpc.keepalive_time_ms', 30000),
                ('grpc.keepalive_timeout_ms', 5000),
                ('grpc.keepalive_permit_without_calls', True)
            ])
            
            # Register task handlers
            await self._register_task_handlers()
            
            logger.info("Workflow orchestrator initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize workflow orchestrator: {e}")
            raise WorkflowExecutionError(f"Initialization failed: {e}")
    
    async def shutdown(self):
        """Shutdown the workflow orchestrator."""
        try:
            if self.zeebe_worker:
                await self.zeebe_worker.stop()
            if self.zeebe_client:
                await self.zeebe_client.close()
            logger.info("Workflow orchestrator shutdown completed")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
    
    async def validate_bpmn(self, bpmn_xml: str, tenant_id: str) -> Dict[str, Any]:
        """
        Validate BPMN XML for correctness and AI agent compatibility.
        
        Args:
            bpmn_xml: BPMN XML content to validate
            tenant_id: Tenant ID for context
            
        Returns:
            Validation result with errors and warnings
        """
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'agent_dependencies': [],
            'tool_dependencies': [],
            'circular_dependencies': []
        }
        
        try:
            # Use BPMN validator for structure validation
            structure_validation = self.bpmn_validator.validate_structure(bpmn_xml)
            validation_result.update(structure_validation)
            
            if not validation_result['valid']:
                return validation_result
            
            # Analyze dependencies
            dependencies = self.dependency_analyzer.analyze_dependencies(bpmn_xml)
            validation_result['agent_dependencies'] = dependencies['agents']
            validation_result['tool_dependencies'] = dependencies['tools']
            validation_result['circular_dependencies'] = dependencies['circular_references']
            
            if dependencies['circular_references']:
                validation_result['errors'].extend([
                    f"Circular dependency detected: {ref}" for ref in dependencies['circular_references']
                ])
                validation_result['valid'] = False
            
            # Validate agent and tool dependencies
            await self._validate_dependencies(validation_result, tenant_id)
            
        except Exception as e:
            validation_result['errors'].append(f"Validation error: {e}")
            validation_result['valid'] = False
        
        return validation_result
    
    async def _validate_dependencies(self, validation_result: Dict[str, Any], tenant_id: str):
        """Validate that all required agents and tools are available."""
        async with get_database_session() as session:
            # Check agent dependencies
            for agent_id in validation_result['agent_dependencies']:
                try:
                    agent_uuid = UUID(agent_id)
                    stmt = select(Agent).where(
                        and_(Agent.id == agent_uuid, Agent.tenant_id == tenant_id)
                    )
                    result = await session.execute(stmt)
                    agent = result.scalar_one_or_none()
                    
                    if not agent:
                        validation_result['errors'].append(f"Required agent {agent_id} not found")
                        validation_result['valid'] = False
                    elif agent.status != 'active':
                        validation_result['warnings'].append(f"Agent {agent_id} is not active")
                        
                except ValueError:
                    validation_result['errors'].append(f"Invalid agent ID format: {agent_id}")
                    validation_result['valid'] = False
    
    async def deploy_workflow(self, workflow_id: UUID, tenant_id: str) -> Dict[str, Any]:
        """
        Deploy a workflow to the Zeebe engine.
        
        Args:
            workflow_id: ID of the workflow to deploy
            tenant_id: Tenant ID for context
            
        Returns:
            Deployment result
        """
        async with get_database_session() as session:
            # Get workflow
            stmt = select(Workflow).where(
                and_(Workflow.id == workflow_id, Workflow.tenant_id == tenant_id)
            )
            result = await session.execute(stmt)
            workflow = result.scalar_one_or_none()
            
            if not workflow:
                raise WorkflowExecutionError(f"Workflow {workflow_id} not found")
            
            # Validate BPMN before deployment
            validation_result = await self.validate_bpmn(workflow.bpmn_xml, tenant_id)
            if not validation_result['valid']:
                raise BPMNValidationError(f"BPMN validation failed: {validation_result['errors']}")
            
            try:
                # Deploy to Zeebe
                deployment = await self.zeebe_client.deploy_resource(
                    resource_name=f"{workflow.name}_{workflow.version}.bpmn",
                    resource_content=workflow.bpmn_xml.encode('utf-8')
                )
                
                # Update workflow status
                workflow.status = WorkflowStatus.ACTIVE
                await session.commit()
                
                logger.info(f"Deployed workflow {workflow.name} (ID: {workflow_id})")
                
                return {
                    'deployment_key': deployment.key,
                    'process_definition_key': workflow.process_definition_key,
                    'version': deployment.processes[0].version if deployment.processes else 1,
                    'resource_name': deployment.processes[0].resource_name if deployment.processes else None
                }
                
            except (ZeebeBackPressureError, ZeebeGatewayUnavailableError) as e:
                logger.error(f"Zeebe deployment failed: {e}")
                raise WorkflowExecutionError(f"Deployment failed: {e}")
    
    async def start_workflow_execution(
        self,
        workflow_id: UUID,
        tenant_id: str,
        input_data: Optional[Dict[str, Any]] = None,
        variables: Optional[Dict[str, Any]] = None,
        priority: ExecutionPriority = ExecutionPriority.NORMAL,
        correlation_id: Optional[str] = None
    ) -> UUID:
        """
        Start a new workflow execution.
        
        Args:
            workflow_id: ID of the workflow to execute
            tenant_id: Tenant ID for context
            input_data: Input data for the workflow
            variables: Runtime variables
            priority: Execution priority
            correlation_id: Correlation ID for tracing
            
        Returns:
            Execution ID
        """
        async with get_database_session() as session:
            # Get workflow
            stmt = select(Workflow).where(
                and_(Workflow.id == workflow_id, Workflow.tenant_id == tenant_id)
            )
            result = await session.execute(stmt)
            workflow = result.scalar_one_or_none()
            
            if not workflow:
                raise WorkflowExecutionError(f"Workflow {workflow_id} not found")
            
            if workflow.status != WorkflowStatus.ACTIVE:
                raise WorkflowExecutionError(f"Workflow {workflow_id} is not active")
            
            # Check concurrent execution limit
            active_count_stmt = select(WorkflowExecution).where(
                and_(
                    WorkflowExecution.workflow_id == workflow_id,
                    WorkflowExecution.status.in_([ExecutionStatus.PENDING, ExecutionStatus.RUNNING])
                )
            )
            active_count_result = await session.execute(active_count_stmt)
            active_count = len(active_count_result.scalars().all())
            
            if active_count >= workflow.max_concurrent_executions:
                raise WorkflowExecutionError(
                    f"Maximum concurrent executions ({workflow.max_concurrent_executions}) reached"
                )
            
            # Create execution record
            execution = WorkflowExecution(
                id=uuid4(),
                tenant_id=tenant_id,
                workflow_id=workflow_id,
                status=ExecutionStatus.PENDING,
                priority=priority,
                input_data=input_data or {},
                variables=variables or {},
                correlation_id=correlation_id or str(uuid4())
            )
            
            session.add(execution)
            await session.commit()
            
            try:
                # Prepare workflow variables
                workflow_variables = {
                    'executionId': str(execution.id),
                    'tenantId': tenant_id,
                    'correlationId': execution.correlation_id,
                    **(variables or {}),
                    **(input_data or {})
                }
                
                # Start process instance in Zeebe
                process_instance = await self.zeebe_client.create_process_instance(
                    bpmn_process_id=workflow.process_definition_key,
                    variables=workflow_variables
                )
                
                # Update execution with Zeebe process instance key
                execution.status = ExecutionStatus.RUNNING
                execution.started_at = datetime.utcnow()
                execution.variables = {
                    **execution.variables,
                    'zeebeProcessInstanceKey': process_instance.process_instance_key
                }
                
                await session.commit()
                
                # Track active execution
                self.active_executions[str(execution.id)] = {
                    'workflow_id': str(workflow_id),
                    'tenant_id': tenant_id,
                    'process_instance_key': process_instance.process_instance_key,
                    'started_at': execution.started_at
                }
                
                # Log execution start
                await self._log_execution_event(
                    execution.id,
                    'workflow_start',
                    'WORKFLOW_STARTED',
                    f"Workflow execution started for {workflow.name}",
                    input_data=input_data,
                    variables=workflow_variables
                )
                
                logger.info(f"Started workflow execution {execution.id} for workflow {workflow.name}")
                
                return execution.id
                
            except Exception as e:
                # Update execution status to failed
                execution.status = ExecutionStatus.FAILED
                execution.error_message = str(e)
                execution.completed_at = datetime.utcnow()
                await session.commit()
                
                logger.error(f"Failed to start workflow execution: {e}")
                raise WorkflowExecutionError(f"Failed to start execution: {e}")
    
    async def _register_task_handlers(self):
        """Register task handlers for different types of BPMN tasks."""
        
        @self.zeebe_worker.task(task_type="agent_task")
        async def handle_agent_task(job: Job) -> Dict[str, Any]:
            """Handle agent execution tasks."""
            try:
                variables = job.variables
                execution_id = variables.get('executionId')
                tenant_id = variables.get('tenantId')
                agent_id = variables.get('agentId')
                task_input = variables.get('taskInput', {})
                
                logger.info(f"Executing agent task for agent {agent_id} in execution {execution_id}")
                
                # Log task start
                await self._log_execution_event(
                    UUID(execution_id),
                    job.element_id,
                    'AGENT_TASK_STARTED',
                    f"Started agent task for agent {agent_id}",
                    agent_id=UUID(agent_id) if agent_id else None,
                    input_data=task_input
                )
                
                # Execute agent
                result = await self.agent_executor.execute_agent(
                    agent_id=UUID(agent_id),
                    input_data=task_input,
                    tenant_id=tenant_id,
                    execution_context={
                        'workflow_execution_id': execution_id,
                        'bpmn_element_id': job.element_id,
                        'correlation_id': variables.get('correlationId')
                    }
                )
                
                # Log task completion
                await self._log_execution_event(
                    UUID(execution_id),
                    job.element_id,
                    'AGENT_TASK_COMPLETED',
                    f"Completed agent task for agent {agent_id}",
                    agent_id=UUID(agent_id) if agent_id else None,
                    output_data=result
                )
                
                return {
                    'agentResult': result,
                    'taskCompleted': True,
                    'completedAt': datetime.utcnow().isoformat()
                }
                
            except Exception as e:
                logger.error(f"Agent task execution failed: {e}")
                
                # Log task failure
                await self._log_execution_event(
                    UUID(execution_id),
                    job.element_id,
                    'AGENT_TASK_FAILED',
                    f"Agent task failed: {e}",
                    agent_id=UUID(agent_id) if agent_id else None,
                    error_details={'error': str(e)}
                )
                
                raise
        
        @self.zeebe_worker.task(task_type="tool_task")
        async def handle_tool_task(job: Job) -> Dict[str, Any]:
            """Handle tool execution tasks."""
            try:
                variables = job.variables
                execution_id = variables.get('executionId')
                tool_name = variables.get('toolName')
                tool_input = variables.get('toolInput', {})
                
                logger.info(f"Executing tool task for tool {tool_name} in execution {execution_id}")
                
                # Log task start
                await self._log_execution_event(
                    UUID(execution_id),
                    job.element_id,
                    'TOOL_TASK_STARTED',
                    f"Started tool task for tool {tool_name}",
                    tool_name=tool_name,
                    input_data=tool_input
                )
                
                # Execute tool (placeholder - would integrate with tool registry)
                result = await self._execute_tool(tool_name, tool_input)
                
                # Log task completion
                await self._log_execution_event(
                    UUID(execution_id),
                    job.element_id,
                    'TOOL_TASK_COMPLETED',
                    f"Completed tool task for tool {tool_name}",
                    tool_name=tool_name,
                    output_data=result
                )
                
                return {
                    'toolResult': result,
                    'taskCompleted': True,
                    'completedAt': datetime.utcnow().isoformat()
                }
                
            except Exception as e:
                logger.error(f"Tool task execution failed: {e}")
                
                # Log task failure
                await self._log_execution_event(
                    UUID(execution_id),
                    job.element_id,
                    'TOOL_TASK_FAILED',
                    f"Tool task failed: {e}",
                    tool_name=tool_name,
                    error_details={'error': str(e)}
                )
                
                raise
        
        # Start the worker
        await self.zeebe_worker.work()
    
    async def _execute_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool (placeholder implementation)."""
        # This would integrate with the tool registry service
        # For now, return a placeholder result
        return {
            'tool_name': tool_name,
            'input': tool_input,
            'output': f"Tool {tool_name} executed successfully",
            'executed_at': datetime.utcnow().isoformat()
        }
    
    async def _log_execution_event(
        self,
        execution_id: UUID,
        node_id: str,
        event_type: str,
        message: str,
        level: str = "INFO",
        input_data: Optional[Dict[str, Any]] = None,
        output_data: Optional[Dict[str, Any]] = None,
        variables: Optional[Dict[str, Any]] = None,
        agent_id: Optional[UUID] = None,
        tool_name: Optional[str] = None,
        error_details: Optional[Dict[str, Any]] = None,
        duration_ms: Optional[int] = None
    ):
        """Log an execution event."""
        async with get_database_session() as session:
            # Get execution to determine tenant_id
            execution = await session.get(WorkflowExecution, execution_id)
            if not execution:
                logger.warning(f"Execution {execution_id} not found for logging")
                return
            
            log_entry = ExecutionLog(
                id=uuid4(),
                tenant_id=execution.tenant_id,
                execution_id=execution_id,
                node_id=node_id,
                event_type=event_type,
                message=message,
                level=level,
                timestamp=datetime.utcnow(),
                input_data=input_data or {},
                output_data=output_data or {},
                variables=variables or {},
                agent_id=agent_id,
                tool_name=tool_name,
                error_details=error_details or {},
                duration_ms=duration_ms
            )
            
            session.add(log_entry)
            await session.commit()
    
    async def get_workflow_execution_status(
        self, 
        execution_id: UUID, 
        tenant_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get the current status of a workflow execution."""
        async with get_database_session() as session:
            stmt = select(WorkflowExecution).options(
                selectinload(WorkflowExecution.workflow),
                selectinload(WorkflowExecution.execution_logs)
            ).where(
                and_(
                    WorkflowExecution.id == execution_id,
                    WorkflowExecution.tenant_id == tenant_id
                )
            )
            
            result = await session.execute(stmt)
            execution = result.scalar_one_or_none()
            
            if not execution:
                return None
            
            # Calculate progress if running
            progress_percentage = None
            if execution.status == ExecutionStatus.RUNNING:
                progress_percentage = await self._calculate_execution_progress(execution)
            
            return {
                'id': str(execution.id),
                'workflow_id': str(execution.workflow_id),
                'workflow_name': execution.workflow.name,
                'status': execution.status.value,
                'priority': execution.priority.value,
                'started_at': execution.started_at.isoformat() if execution.started_at else None,
                'completed_at': execution.completed_at.isoformat() if execution.completed_at else None,
                'duration_seconds': execution.duration_seconds,
                'current_node_id': execution.current_node_id,
                'progress_percentage': progress_percentage,
                'error_message': execution.error_message,
                'retry_count': execution.retry_count,
                'correlation_id': execution.correlation_id,
                'input_data': execution.input_data,
                'output_data': execution.output_data,
                'variables': execution.variables
            }
    
    async def _calculate_execution_progress(self, execution: WorkflowExecution) -> float:
        """Calculate execution progress as a percentage."""
        if not execution.completed_nodes or not execution.workflow:
            return 0.0
        
        try:
            # Use BPMN parser to count total nodes
            all_elements = self.bpmn_parser.get_all_elements(execution.workflow.bpmn_xml)
            total_nodes = len(all_elements)
            
            if total_nodes == 0:
                return 0.0
            
            completed_count = len(execution.completed_nodes)
            return min(100.0, (completed_count / total_nodes) * 100.0)
            
        except Exception as e:
            logger.warning(f"Failed to calculate progress for execution {execution.id}: {e}")
            return 0.0
    
    async def pause_workflow_execution(self, execution_id: UUID, tenant_id: str, reason: Optional[str] = None):
        """Pause a running workflow execution."""
        async with get_database_session() as session:
            stmt = select(WorkflowExecution).where(
                and_(
                    WorkflowExecution.id == execution_id,
                    WorkflowExecution.tenant_id == tenant_id,
                    WorkflowExecution.status == ExecutionStatus.RUNNING
                )
            )
            
            result = await session.execute(stmt)
            execution = result.scalar_one_or_none()
            
            if not execution:
                raise WorkflowExecutionError(f"Running execution {execution_id} not found")
            
            # Update status
            execution.status = ExecutionStatus.PAUSED
            await session.commit()
            
            # Log pause event
            await self._log_execution_event(
                execution_id,
                'workflow_control',
                'WORKFLOW_PAUSED',
                f"Workflow execution paused: {reason or 'No reason provided'}",
                level="WARN"
            )
            
            logger.info(f"Paused workflow execution {execution_id}")
    
    async def resume_workflow_execution(self, execution_id: UUID, tenant_id: str, reason: Optional[str] = None):
        """Resume a paused workflow execution."""
        async with get_database_session() as session:
            stmt = select(WorkflowExecution).where(
                and_(
                    WorkflowExecution.id == execution_id,
                    WorkflowExecution.tenant_id == tenant_id,
                    WorkflowExecution.status == ExecutionStatus.PAUSED
                )
            )
            
            result = await session.execute(stmt)
            execution = result.scalar_one_or_none()
            
            if not execution:
                raise WorkflowExecutionError(f"Paused execution {execution_id} not found")
            
            # Update status
            execution.status = ExecutionStatus.RUNNING
            await session.commit()
            
            # Log resume event
            await self._log_execution_event(
                execution_id,
                'workflow_control',
                'WORKFLOW_RESUMED',
                f"Workflow execution resumed: {reason or 'No reason provided'}"
            )
            
            logger.info(f"Resumed workflow execution {execution_id}")
    
    async def cancel_workflow_execution(self, execution_id: UUID, tenant_id: str, reason: Optional[str] = None):
        """Cancel a workflow execution."""
        async with get_database_session() as session:
            stmt = select(WorkflowExecution).where(
                and_(
                    WorkflowExecution.id == execution_id,
                    WorkflowExecution.tenant_id == tenant_id,
                    WorkflowExecution.status.in_([
                        ExecutionStatus.PENDING, 
                        ExecutionStatus.RUNNING, 
                        ExecutionStatus.PAUSED
                    ])
                )
            )
            
            result = await session.execute(stmt)
            execution = result.scalar_one_or_none()
            
            if not execution:
                raise WorkflowExecutionError(f"Active execution {execution_id} not found")
            
            try:
                # Cancel in Zeebe if process instance exists
                process_instance_key = execution.variables.get('zeebeProcessInstanceKey')
                if process_instance_key:
                    await self.zeebe_client.cancel_process_instance(process_instance_key)
                
                # Update status
                execution.status = ExecutionStatus.CANCELLED
                execution.completed_at = datetime.utcnow()
                execution.calculate_duration()
                await session.commit()
                
                # Remove from active executions
                if str(execution_id) in self.active_executions:
                    del self.active_executions[str(execution_id)]
                
                # Log cancellation event
                await self._log_execution_event(
                    execution_id,
                    'workflow_control',
                    'WORKFLOW_CANCELLED',
                    f"Workflow execution cancelled: {reason or 'No reason provided'}",
                    level="WARN"
                )
                
                logger.info(f"Cancelled workflow execution {execution_id}")
                
            except Exception as e:
                logger.error(f"Failed to cancel workflow execution {execution_id}: {e}")
                raise WorkflowExecutionError(f"Failed to cancel execution: {e}")
    
    async def get_execution_logs(
        self,
        execution_id: UUID,
        tenant_id: str,
        limit: int = 100,
        offset: int = 0,
        level_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get execution logs for a workflow execution."""
        async with get_database_session() as session:
            # Verify execution exists and belongs to tenant
            execution_stmt = select(WorkflowExecution).where(
                and_(
                    WorkflowExecution.id == execution_id,
                    WorkflowExecution.tenant_id == tenant_id
                )
            )
            execution_result = await session.execute(execution_stmt)
            execution = execution_result.scalar_one_or_none()
            
            if not execution:
                return []
            
            # Build logs query
            stmt = select(ExecutionLog).where(ExecutionLog.execution_id == execution_id)
            
            if level_filter:
                stmt = stmt.where(ExecutionLog.level == level_filter.upper())
            
            stmt = stmt.order_by(ExecutionLog.timestamp.desc()).offset(offset).limit(limit)
            
            result = await session.execute(stmt)
            logs = result.scalars().all()
            
            return [
                {
                    'id': str(log.id),
                    'node_id': log.node_id,
                    'event_type': log.event_type,
                    'message': log.message,
                    'level': log.level,
                    'timestamp': log.timestamp.isoformat(),
                    'duration_ms': log.duration_ms,
                    'agent_id': str(log.agent_id) if log.agent_id else None,
                    'tool_name': log.tool_name,
                    'error_code': log.error_code,
                    'input_data': log.input_data,
                    'output_data': log.output_data,
                    'variables': log.variables,
                    'error_details': log.error_details
                }
                for log in logs
            ]