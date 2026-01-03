"""Chain Orchestration Models for the AI Agent Framework."""

import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum

from sqlalchemy import String, Text, ForeignKey, Integer, Float, DateTime, text, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.models.base import SystemEntity


class ChainStatus(str, Enum):
    """Status values for chains."""
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class ChainNodeType(str, Enum):
    """Types of nodes in a chain."""
    AGENT = "agent"
    CONDITION = "condition"
    AGGREGATOR = "aggregator"
    PARALLEL_SPLIT = "parallel_split"
    PARALLEL_JOIN = "parallel_join"
    START = "start"
    END = "end"


class ChainExecutionStatus(str, Enum):
    """Execution status values."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class Chain(SystemEntity):
    """Main chain definition."""
    __tablename__ = "chains"
    
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(50), 
        nullable=False, 
        default=ChainStatus.DRAFT,
        index=True
    )
    version: Mapped[str] = mapped_column(String(50), nullable=False, default="1.0.0")
    category: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    tags: Mapped[List[str]] = mapped_column(
        JSONB, 
        nullable=True, 
        server_default=text("'[]'::jsonb")
    )
    
    # Schema definitions for inputs/outputs
    input_schema: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, 
        nullable=True, 
        server_default=text("'{}'::jsonb")
    )
    output_schema: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, 
        nullable=True, 
        server_default=text("'{}'::jsonb")
    )
    
    # Execution statistics
    execution_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_executed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), 
        nullable=True
    )
    
    # Metadata
    chain_metadata: Mapped[Dict[str, Any]] = mapped_column(
        "metadata",
        JSONB, 
        nullable=True, 
        server_default=text("'{}'::jsonb")
    )


class ChainNode(SystemEntity):
    """Individual nodes in a chain (agents, conditions, aggregators, etc.)."""
    __tablename__ = "chain_nodes"
    
    chain_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("chains.id", ondelete="CASCADE"), 
        nullable=False, 
        index=True
    )
    node_id: Mapped[str] = mapped_column(String(255), nullable=False)  # Unique within chain
    node_type: Mapped[str] = mapped_column(
        String(50), 
        nullable=False, 
        default=ChainNodeType.AGENT
    )
    
    # Reference to agent if node_type is AGENT
    agent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("agents.id"), 
        nullable=True, 
        index=True
    )
    
    # Display properties
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    position_x: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    position_y: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    
    # Node-specific configuration
    config: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, 
        nullable=True, 
        server_default=text("'{}'::jsonb")
    )
    
    # Execution order hint
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    
    __table_args__ = (
        Index('idx_chain_node_unique', 'chain_id', 'node_id', unique=True),
    )


class ChainEdge(SystemEntity):
    """Connections between nodes in a chain."""
    __tablename__ = "chain_edges"
    
    chain_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("chains.id", ondelete="CASCADE"), 
        nullable=False, 
        index=True
    )
    edge_id: Mapped[str] = mapped_column(String(255), nullable=False)  # Unique within chain
    
    # Source and target nodes (references ChainNode.node_id, not ChainNode.id)
    source_node_id: Mapped[str] = mapped_column(String(255), nullable=False)
    target_node_id: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Conditional routing (optional)
    condition: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB, 
        nullable=True, 
        server_default=text("'{}'::jsonb")
    )
    
    # Display label
    label: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Edge metadata
    edge_metadata: Mapped[Dict[str, Any]] = mapped_column(
        "metadata",
        JSONB, 
        nullable=True, 
        server_default=text("'{}'::jsonb")
    )
    
    __table_args__ = (
        Index('idx_chain_edge_unique', 'chain_id', 'edge_id', unique=True),
        Index('idx_chain_edge_source', 'chain_id', 'source_node_id'),
        Index('idx_chain_edge_target', 'chain_id', 'target_node_id'),
    )


class ChainExecution(SystemEntity):
    """Execution tracking for chain runs."""
    __tablename__ = "chain_executions"
    
    chain_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("chains.id"), 
        nullable=False, 
        index=True
    )
    execution_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Execution status
    status: Mapped[str] = mapped_column(
        String(50), 
        nullable=False, 
        default=ChainExecutionStatus.PENDING,
        index=True
    )
    
    # Input/Output data
    input_data: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, 
        nullable=True, 
        server_default=text("'{}'::jsonb")
    )
    output_data: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, 
        nullable=True, 
        server_default=text("'{}'::jsonb")
    )
    
    # Execution context and variables
    variables: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, 
        nullable=True, 
        server_default=text("'{}'::jsonb")
    )
    
    # Node execution results (keyed by node_id)
    node_results: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, 
        nullable=True, 
        server_default=text("'{}'::jsonb")
    )
    
    # Timing information
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), 
        nullable=True,
        index=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), 
        nullable=True
    )
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Current execution state
    current_node_id: Mapped[Optional[str]] = mapped_column(
        String(255), 
        nullable=True,
        index=True
    )
    completed_nodes: Mapped[List[str]] = mapped_column(
        JSONB, 
        nullable=True, 
        server_default=text("'[]'::jsonb")
    )
    
    # Path tracking
    active_edges: Mapped[List[str]] = mapped_column(
        JSONB, 
        nullable=True, 
        server_default=text("'[]'::jsonb")
    )
    edge_results: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, 
        nullable=True, 
        server_default=text("'{}'::jsonb")
    )
    
    # Error tracking
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_details: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, 
        nullable=True, 
        server_default=text("'{}'::jsonb")
    )
    
    # Execution metadata
    triggered_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), 
        nullable=True,
        index=True
    )
    correlation_id: Mapped[Optional[str]] = mapped_column(
        String(255), 
        nullable=True,
        index=True
    )


class ChainExecutionLog(SystemEntity):
    """Detailed logs for chain execution events."""
    __tablename__ = "chain_execution_logs"
    
    execution_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("chain_executions.id", ondelete="CASCADE"), 
        nullable=False, 
        index=True
    )
    node_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    level: Mapped[str] = mapped_column(String(20), default="INFO", nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=datetime.utcnow, 
        nullable=False,
        index=True
    )
    
    # Additional context
    log_metadata: Mapped[Dict[str, Any]] = mapped_column(
        "metadata",
        JSONB, 
        nullable=True, 
        server_default=text("'{}'::jsonb")
    )
