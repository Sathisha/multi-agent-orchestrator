from typing import List, Dict, Optional, Any
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field

from ..models.workflow import WorkflowStatus, ExecutionStatus, ExecutionPriority

class WorkflowBase(BaseModel):
    name: str
    description: Optional[str] = None
    version: str = "1.0.0"
    category: Optional[str] = None
    tags: List[str] = []
    input_schema: Dict[str, Any] = {}
    output_schema: Dict[str, Any] = {}
    default_variables: Dict[str, Any] = {}
    timeout_minutes: Optional[int] = None
    max_concurrent_executions: int = 10
    retry_policy: Dict[str, Any] = {}

class WorkflowRequest(WorkflowBase):
    pass

class WorkflowResponse(WorkflowBase):
    id: UUID
    status: WorkflowStatus
    created_at: datetime
    updated_at: Optional[datetime] = None
    execution_count: int = 0
    
    class Config:
        from_attributes = True

class WorkflowExecutionRequest(BaseModel):
    input_data: Dict[str, Any] = {}
    variables: Dict[str, Any] = {}
    priority: ExecutionPriority = ExecutionPriority.NORMAL
    correlation_id: Optional[str] = None

class WorkflowExecutionResponse(BaseModel):
    id: UUID
    workflow_id: UUID
    workflow_name: Optional[str] = None
    status: ExecutionStatus
    priority: ExecutionPriority
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    current_node_id: Optional[str] = None
    progress_percentage: Optional[float] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    correlation_id: Optional[str] = None
    input_data: Dict[str, Any] = {}
    output_data: Dict[str, Any] = {}
    variables: Dict[str, Any] = {}

    class Config:
        from_attributes = True

class WorkflowExecutionControlRequest(BaseModel):
    action: str = Field(..., description="Action to perform: pause, resume, cancel")
    reason: Optional[str] = None

class ExecutionLogResponse(BaseModel):
    id: UUID
    node_id: str
    event_type: str
    message: str
    level: str
    timestamp: datetime
    duration_ms: Optional[int] = None
    agent_id: Optional[UUID] = None
    tool_name: Optional[str] = None
    error_details: Dict[str, Any] = {}
    input_data: Dict[str, Any] = {}
    output_data: Dict[str, Any] = {}
    variables: Dict[str, Any] = {}
    
    class Config:
        from_attributes = True

class WorkflowStatistics(BaseModel):
    total_executions: int
    successful_executions: int
    failed_executions: int
    average_duration_seconds: Optional[float] = None
    success_rate: float
