"""Pydantic schemas for Chain Orchestration API."""

from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict

from shared.models.chain import ChainStatus, ChainNodeType, ChainExecutionStatus


# ============================================================================
# Node Schemas
# ============================================================================

class ChainNodeSchema(BaseModel):
    """Schema for a chain node."""
    node_id: str = Field(..., description="Unique identifier within the chain")
    node_type: ChainNodeType = Field(..., description="Type of node")
    agent_id: Optional[UUID] = Field(None, description="Agent ID if node type is AGENT")
    label: str = Field(..., description="Display label for the node")
    position_x: float = Field(0.0, description="X position on canvas")
    position_y: float = Field(0.0, description="Y position on canvas")
    config: Dict[str, Any] = Field(default_factory=dict, description="Node-specific configuration")
    order_index: int = Field(0, description="Execution order hint")

    model_config = ConfigDict(from_attributes=True)


class ChainNodeResponse(ChainNodeSchema):
    """Response schema for a chain node with database fields."""
    id: UUID
    chain_id: UUID
    created_at: datetime
    updated_at: datetime


# ============================================================================
# Edge Schemas
# ============================================================================

class ChainEdgeSchema(BaseModel):
    """Schema for a chain edge (connection between nodes)."""
    edge_id: str = Field(..., description="Unique identifier within the chain")
    source_node_id: str = Field(..., description="Source node ID")
    target_node_id: str = Field(..., description="Target node ID")
    condition: Optional[Dict[str, Any]] = Field(None, description="Conditional routing logic")
    label: Optional[str] = Field(None, description="Display label for the edge")

    model_config = ConfigDict(from_attributes=True)


class ChainEdgeResponse(ChainEdgeSchema):
    """Response schema for a chain edge with database fields."""
    id: UUID
    chain_id: UUID
    created_at: datetime
    updated_at: datetime


# ============================================================================
# Chain Schemas
# ============================================================================

class ChainCreateRequest(BaseModel):
    """Request schema for creating a new chain."""
    name: str = Field(..., min_length=1, max_length=255, description="Chain name")
    description: Optional[str] = Field(None, description="Chain description")
    category: Optional[str] = Field(None, description="Chain category")
    tags: List[str] = Field(default_factory=list, description="Tags for categorization")
    nodes: List[ChainNodeSchema] = Field(default_factory=list, description="Chain nodes")
    edges: List[ChainEdgeSchema] = Field(default_factory=list, description="Chain edges")
    input_schema: Optional[Dict[str, Any]] = Field(None, description="JSON schema for inputs")
    output_schema: Optional[Dict[str, Any]] = Field(None, description="JSON schema for outputs")
    status: ChainStatus = Field(ChainStatus.DRAFT, description="Chain status")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class ChainUpdateRequest(BaseModel):
    """Request schema for updating a chain."""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Chain name")
    description: Optional[str] = Field(None, description="Chain description")
    category: Optional[str] = Field(None, description="Chain category")
    tags: Optional[List[str]] = Field(None, description="Tags for categorization")
    nodes: Optional[List[ChainNodeSchema]] = Field(None, description="Chain nodes")
    edges: Optional[List[ChainEdgeSchema]] = Field(None, description="Chain edges")
    input_schema: Optional[Dict[str, Any]] = Field(None, description="JSON schema for inputs")
    output_schema: Optional[Dict[str, Any]] = Field(None, description="JSON schema for outputs")
    status: Optional[ChainStatus] = Field(None, description="Chain status")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class ChainResponse(BaseModel):
    """Response schema for a chain."""
    id: UUID
    name: str
    description: Optional[str]
    status: str
    version: str
    category: Optional[str]
    tags: List[str]
    nodes: List[ChainNodeResponse]
    edges: List[ChainEdgeResponse]
    input_schema: Optional[Dict[str, Any]]
    output_schema: Optional[Dict[str, Any]]
    execution_count: int
    last_executed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict, alias="chain_metadata")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ChainListResponse(BaseModel):
    """Response schema for listing chains (lighter version)."""
    id: UUID
    name: str
    description: Optional[str]
    status: str
    version: str
    category: Optional[str]
    tags: List[str]
    node_count: int = Field(0, description="Number of nodes in the chain")
    execution_count: int
    last_executed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Execution Schemas
# ============================================================================

class ChainExecuteRequest(BaseModel):
    """Request schema for executing a chain."""
    input_data: Dict[str, Any] = Field(..., description="Input data for the chain")
    execution_name: Optional[str] = Field(None, description="Name for this execution")
    variables: Optional[Dict[str, Any]] = Field(None, description="Initial variables")
    correlation_id: Optional[str] = Field(None, description="Correlation ID for tracking")
    model_override: Optional[Dict[str, Any]] = Field(None, description="Global model override for all agents in the chain")


class ChainExecutionResponse(BaseModel):
    """Response schema for chain execution."""
    id: UUID
    chain_id: UUID
    execution_name: Optional[str]
    status: str
    input_data: Dict[str, Any]
    output_data: Optional[Dict[str, Any]]
    variables: Dict[str, Any]
    node_results: Dict[str, Any]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    duration_seconds: Optional[int]
    current_node_id: Optional[str]
    completed_nodes: List[str]
    active_edges: List[str] = Field(default_factory=list)
    edge_results: Optional[Dict[str, Any]] = None
    error_message: Optional[str]
    error_details: Optional[Dict[str, Any]]
    correlation_id: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChainExecutionListResponse(BaseModel):
    """Response schema for listing executions (lighter version)."""
    id: UUID
    chain_id: UUID
    execution_name: Optional[str]
    status: str
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    duration_seconds: Optional[int]
    error_message: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChainExecutionLogResponse(BaseModel):
    """Response schema for execution logs."""
    id: UUID
    execution_id: UUID
    node_id: Optional[str]
    event_type: str
    message: str
    level: str
    timestamp: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict, alias="log_metadata")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# ============================================================================
# Validation Schemas
# ============================================================================

class ChainValidationResult(BaseModel):
    """Result of chain validation."""
    is_valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    details: Dict[str, Any] = Field(default_factory=dict)


class ChainExecutionStatusResponse(BaseModel):
    """Quick status response for execution."""
    execution_id: UUID
    status: ChainExecutionStatus
    current_node_id: Optional[str]
    completed_nodes: List[str]
    active_edges: List[str] = Field(default_factory=list)
    node_states: Optional[Dict[str, str]] = Field(None, description="Status of each node (pending, running, completed, failed, skipped)")
    progress_percentage: float = Field(0.0, ge=0.0, le=100.0)
    error_message: Optional[str]
