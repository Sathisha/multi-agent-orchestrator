"""API endpoints for Chain Orchestration."""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status, BackgroundTasks
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from shared.database.connection import get_async_db
from shared.models.chain import (
    Chain, ChainNode, ChainEdge, ChainExecution, ChainExecutionLog,
    ChainStatus, ChainExecutionStatus, ChainNodeType
)
from shared.schemas.chain import (
    ChainCreateRequest, ChainUpdateRequest, ChainResponse,
    ChainListResponse, ChainExecuteRequest, ChainExecutionResponse,
    ChainExecutionListResponse, ChainExecutionLogResponse,
    ChainValidationResult, ChainExecutionStatusResponse,
    ChainNodeResponse, ChainEdgeResponse, ChainNodeSchema
)
from shared.api.auth import get_current_user_or_api_key, get_current_user
from shared.services.chain_orchestrator import (
    ChainOrchestratorService,
    ChainValidationError,
    ChainExecutionError
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/chains", tags=["Chains"])


# Global service instance
_chain_orchestrator_instance: Optional[ChainOrchestratorService] = None


def get_chain_orchestrator_service() -> ChainOrchestratorService:
    """Get or create chain orchestrator service instance."""
    global _chain_orchestrator_instance
    if _chain_orchestrator_instance is None:
        _chain_orchestrator_instance = ChainOrchestratorService()
    return _chain_orchestrator_instance


# ============================================================================
# Chain CRUD Endpoints
# ============================================================================

@router.post("", response_model=ChainResponse, status_code=status.HTTP_201_CREATED)
async def create_chain(
    request: ChainCreateRequest,
    session: AsyncSession = Depends(get_async_db)
):
    """
    Create a new chain orchestration workflow.
    
    This endpoint initializes a new chain and its associated nodes and edges.
    If no nodes are provided, it automatically creates default START and END nodes.
    
    - **name**: Descriptive name for the chain.
    - **nodes**: List of orchestration nodes (optional).
    - **edges**: List of connections between nodes (optional).
    """
    try:
        # Create chain
        chain = Chain(
            name=request.name,
            description=request.description,
            status=request.status.value if request.status else ChainStatus.DRAFT,
            category=request.category,
            tags=request.tags or [],
            input_schema=request.input_schema,
            output_schema=request.output_schema,
            chain_metadata=request.metadata or {}
        )
        session.add(chain)
        await session.flush()  # Get chain.id
        
        # Auto-create START and END nodes if no nodes provided
        nodes_to_create = request.nodes if request.nodes else []
        if not nodes_to_create:
            # Auto-create default START and END nodes
            nodes_to_create = [
                ChainNodeSchema(
                    node_id="start",
                    node_type=ChainNodeType.START,
                    label="Start",
                    position_x=100,
                    position_y=300,
                    order_index=0
                ),
                ChainNodeSchema(
                    node_id="end",
                    node_type=ChainNodeType.END,
                    label="End",
                    position_x=400,
                    position_y=300,
                    order_index=1
                )
            ]
            logger.info(f"Auto-created START and END nodes for chain {chain.id}")
        
        # Create nodes
        nodes = []
        for node_data in nodes_to_create:
            node = ChainNode(
                chain_id=chain.id,
                node_id=node_data.node_id,
                node_type=node_data.node_type.value,
                agent_id=node_data.agent_id,
                label=node_data.label,
                position_x=node_data.position_x,
                position_y=node_data.position_y,
                config=node_data.config,
                order_index=node_data.order_index
            )
            session.add(node)
            nodes.append(node)
        
        # Create edges
        edges = []
        for edge_data in request.edges:
            edge = ChainEdge(
                chain_id=chain.id,
                edge_id=edge_data.edge_id,
                source_node_id=edge_data.source_node_id,
                target_node_id=edge_data.target_node_id,
                condition=edge_data.condition,
                label=edge_data.label
            )
            session.add(edge)
            edges.append(edge)
        
        await session.commit()
        await session.refresh(chain)
        
        # Fetch with relationships
        result = await session.execute(
            select(Chain).where(Chain.id == chain.id)
        )
        chain = result.scalar_one()
        
        nodes_result = await session.execute(
            select(ChainNode).where(ChainNode.chain_id == chain.id)
        )
        chain_nodes = list(nodes_result.scalars().all())
        
        edges_result = await session.execute(
            select(ChainEdge).where(ChainEdge.chain_id == chain.id)
        )
        chain_edges = list(edges_result.scalars().all())
        
        logger.info(f"Created chain {chain.id} with {len(chain_nodes)} nodes and {len(chain_edges)} edges")
        
        return ChainResponse(
            id=chain.id,
            name=chain.name,
            description=chain.description,
            status=chain.status,
            version=chain.version,
            category=chain.category,
            tags=chain.tags or [],
            nodes=[ChainNodeResponse.model_validate(n) for n in chain_nodes],
            edges=[ChainEdgeResponse.model_validate(e) for e in chain_edges],
            input_schema=chain.input_schema,
            output_schema=chain.output_schema,
            execution_count=chain.execution_count,
            last_executed_at=chain.last_executed_at,
            created_at=chain.created_at,
            updated_at=chain.updated_at,
            chain_metadata=chain.chain_metadata or {}
        )
        
    except Exception as e:
        logger.error(f"Error creating chain: {e}", exc_info=True)
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create chain: {str(e)}"
        )


@router.get("", response_model=List[ChainListResponse])
async def list_chains(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status_filter: Optional[str] = Query(None, alias="status"),
    category: Optional[str] = None,
    session: AsyncSession = Depends(get_async_db)
):
    """
    List all orchestration chains with optional filtering.
    
    Returns a lightweight list of chains including metadata like node counts and execution history summary.
    Use this endpoint for population chain lists in the UI.
    """
    try:
        # Build query
        query = select(Chain)
        
        if status_filter:
            query = query.where(Chain.status == status_filter)
        if category:
            query = query.where(Chain.category == category)
        
        query = query.offset(skip).limit(limit).order_by(Chain.created_at.desc())
        
        result = await session.execute(query)
        chains = result.scalars().all()
        
        # Get node counts for each chain
        response_list = []
        for chain in chains:
            node_count_result = await session.execute(
                select(func.count(ChainNode.id)).where(ChainNode.chain_id == chain.id)
            )
            node_count = node_count_result.scalar_one()
            
            response_list.append(ChainListResponse(
                id=chain.id,
                name=chain.name,
                description=chain.description,
                status=chain.status,
                version=chain.version,
                category=chain.category,
                tags=chain.tags or [],
                node_count=node_count,
                execution_count=chain.execution_count,
                last_executed_at=chain.last_executed_at,
                created_at=chain.created_at,
                updated_at=chain.updated_at
            ))
        
        return response_list
        
    except Exception as e:
        logger.error(f"Error listing chains: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list chains: {str(e)}"
        )


@router.get("/{chain_id}", response_model=ChainResponse)
async def get_chain(
    chain_id: UUID,
    session: AsyncSession = Depends(get_async_db)
):
    """
    Get full details of a specific chain.
    
    Returns the complete chain configuration, including all nodes, edges, and schemas.
    Required for rendering the visual Chain Builder canvas.
    """
    try:
        # Get chain
        result = await session.execute(
            select(Chain).where(Chain.id == chain_id)
        )
        chain = result.scalar_one_or_none()
        
        if not chain:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Chain {chain_id} not found"
            )
        
        # Get nodes
        nodes_result = await session.execute(
            select(ChainNode).where(ChainNode.chain_id == chain_id).order_by(ChainNode.order_index)
        )
        chain_nodes = list(nodes_result.scalars().all())
        
        # Get edges
        edges_result = await session.execute(
            select(ChainEdge).where(ChainEdge.chain_id == chain_id)
        )
        chain_edges = list(edges_result.scalars().all())
        
        return ChainResponse(
            id=chain.id,
            name=chain.name,
            description=chain.description,
            status=chain.status,
            version=chain.version,
            category=chain.category,
            tags=chain.tags or [],
            nodes=[ChainNodeResponse.model_validate(n) for n in chain_nodes],
            edges=[ChainEdgeResponse.model_validate(e) for e in chain_edges],
            input_schema=chain.input_schema,
            output_schema=chain.output_schema,
            execution_count=chain.execution_count,
            last_executed_at=chain.last_executed_at,
            created_at=chain.created_at,
            updated_at=chain.updated_at,
            chain_metadata=chain.chain_metadata or {}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting chain {chain_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get chain: {str(e)}"
        )


@router.put("/{chain_id}", response_model=ChainResponse)
async def update_chain(
    chain_id: UUID,
    request: ChainUpdateRequest,
    session: AsyncSession = Depends(get_async_db)
):
    """
    Update an existing chain configuration.
    
    Supports partial updates of metadata and full replacement of node/edge graphs.
    When updating nodes or edges, the existing graph is replaced with the new one.
    """
    try:
        # Get chain
        result = await session.execute(
            select(Chain).where(Chain.id == chain_id)
        )
        chain = result.scalar_one_or_none()
        
        if not chain:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Chain {chain_id} not found"
            )
        
        # Update basic fields
        if request.name is not None:
            chain.name = request.name
        if request.description is not None:
            chain.description = request.description
        if request.category is not None:
            chain.category = request.category
        if request.tags is not None:
            chain.tags = request.tags
        if request.status is not None:
            chain.status = request.status.value
        if request.input_schema is not None:
            chain.input_schema = request.input_schema
        if request.output_schema is not None:
            chain.output_schema = request.output_schema
        if request.metadata is not None:
            chain.chain_metadata = request.metadata
        
        # Update nodes if provided
        if request.nodes is not None:
            # Delete existing nodes (cascades to edges if configured)
            await session.execute(
                delete(ChainNode).where(ChainNode.chain_id == chain_id)
            )
            
            # Create new nodes
            for node_data in request.nodes:
                node = ChainNode(
                    chain_id=chain.id,
                    node_id=node_data.node_id,
                    node_type=node_data.node_type.value,
                    agent_id=node_data.agent_id,
                    label=node_data.label,
                    position_x=node_data.position_x,
                    position_y=node_data.position_y,
                    config=node_data.config,
                    order_index=node_data.order_index
                )
                session.add(node)
        
        # Update edges if provided
        if request.edges is not None:
            # Delete existing edges
            await session.execute(
                delete(ChainEdge).where(ChainEdge.chain_id == chain_id)
            )
            
            # Create new edges
            for edge_data in request.edges:
                edge = ChainEdge(
                    chain_id=chain.id,
                    edge_id=edge_data.edge_id,
                    source_node_id=edge_data.source_node_id,
                    target_node_id=edge_data.target_node_id,
                    condition=edge_data.condition,
                    label=edge_data.label
                )
                session.add(edge)
        
        await session.commit()
        await session.refresh(chain)
        
        # Fetch updated chain with relationships
        nodes_result = await session.execute(
            select(ChainNode).where(ChainNode.chain_id == chain_id).order_by(ChainNode.order_index)
        )
        chain_nodes = list(nodes_result.scalars().all())
        
        edges_result = await session.execute(
            select(ChainEdge).where(ChainEdge.chain_id == chain_id)
        )
        chain_edges = list(edges_result.scalars().all())
        
        logger.info(f"Updated chain {chain_id}")
        
        return ChainResponse(
            id=chain.id,
            name=chain.name,
            description=chain.description,
            status=chain.status,
            version=chain.version,
            category=chain.category,
            tags=chain.tags or [],
            nodes=[ChainNodeResponse.model_validate(n) for n in chain_nodes],
            edges=[ChainEdgeResponse.model_validate(e) for e in chain_edges],
            input_schema=chain.input_schema,
            output_schema=chain.output_schema,
            execution_count=chain.execution_count,
            last_executed_at=chain.last_executed_at,
            created_at=chain.created_at,
            updated_at=chain.updated_at,
            chain_metadata=chain.chain_metadata or {}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating chain {chain_id}: {e}", exc_info=True)
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update chain: {str(e)}"
        )


@router.delete("/{chain_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chain(
    chain_id: UUID,
    session: AsyncSession = Depends(get_async_db)
):
    """Delete a chain."""
    try:
        result = await session.execute(
            select(Chain).where(Chain.id == chain_id)
        )
        chain = result.scalar_one_or_none()
        
        if not chain:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Chain {chain_id} not found"
            )
        
        await session.delete(chain)
        await session.commit()
        
        logger.info(f"Deleted chain {chain_id}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting chain {chain_id}: {e}", exc_info=True)
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete chain: {str(e)}"
        )


# ============================================================================
# Chain Validation
# ============================================================================

@router.post("/{chain_id}/validate", response_model=ChainValidationResult)
async def validate_chain(
    chain_id: UUID,
    session: AsyncSession = Depends(get_async_db),
    orchestrator: ChainOrchestratorService = Depends(get_chain_orchestrator_service)
):
    """
    Validate chain structure and configuration.
    
    Checks for cycles, invalid agent references, disconnected nodes, etc.
    """
    try:
        validation_result = await orchestrator.validate_chain(session, chain_id)
        return validation_result
        
    except Exception as e:
        logger.error(f"Error validating chain {chain_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate chain: {str(e)}"
        )


# ============================================================================
# Chain Execution
# ============================================================================

@router.post("/{chain_id}/execute", response_model=ChainExecutionResponse, status_code=status.HTTP_202_ACCEPTED)
async def execute_chain(
    chain_id: UUID,
    request: ChainExecuteRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_async_db),
    orchestrator: ChainOrchestratorService = Depends(get_chain_orchestrator_service),
    # Secure endpoint: requires User (Token) or System (API Key)
    current_user_or_key = Depends(get_current_user_or_api_key)
):
    """
    Execute a chain.
    
    Starts asynchronous execution of the chain with the provided input data.
    """
    try:
        # Create execution record
        execution = await orchestrator.create_execution(
            session=session,
            chain_id=chain_id,
            input_data=request.input_data,
            execution_name=request.execution_name,
            variables=request.variables,
            correlation_id=request.correlation_id
        )
        
        # Schedule background execution
        background_tasks.add_task(orchestrator.run_execution_background, execution.id)
        
        return ChainExecutionResponse.model_validate(execution)
        
    except ChainValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except ChainExecutionError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error executing chain {chain_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute chain: {str(e)}"
        )


@router.get("/{chain_id}/executions", response_model=List[ChainExecutionListResponse])
async def get_chain_executions(
    chain_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    session: AsyncSession = Depends(get_async_db)
):
    """Get execution history for a chain."""
    try:
        result = await session.execute(
            select(ChainExecution)
            .where(ChainExecution.chain_id == chain_id)
            .order_by(ChainExecution.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        executions = result.scalars().all()
        
        return [ChainExecutionListResponse.model_validate(e) for e in executions]
        
    except Exception as e:
        logger.error(f"Error getting executions for chain {chain_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get chain executions: {str(e)}"
        )


@router.get("/executions/{execution_id}", response_model=ChainExecutionResponse)
async def get_execution(
    execution_id: UUID,
    session: AsyncSession = Depends(get_async_db)
):
    """Get detailed execution information."""
    try:
        result = await session.execute(
            select(ChainExecution).where(ChainExecution.id == execution_id)
        )
        execution = result.scalar_one_or_none()
        
        if not execution:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Execution {execution_id} not found"
            )
        
        return ChainExecutionResponse.model_validate(execution)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting execution {execution_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get execution: {str(e)}"
        )


@router.get("/executions/{execution_id}/status", response_model=ChainExecutionStatusResponse)
async def get_execution_status(
    execution_id: UUID,
    session: AsyncSession = Depends(get_async_db)
):
    """Get quick status of an execution (for polling)."""
    try:
        result = await session.execute(
            select(ChainExecution).where(ChainExecution.id == execution_id)
        )
        execution = result.scalar_one_or_none()
        
        if not execution:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Execution {execution_id} not found"
            )
        
        # Calculate progress
        total_nodes_result = await session.execute(
            select(func.count(ChainNode.id)).where(ChainNode.chain_id == execution.chain_id)
        )
        total_nodes = total_nodes_result.scalar_one()
        completed_count = len(execution.completed_nodes) if execution.completed_nodes else 0
        progress = (completed_count / total_nodes * 100.0) if total_nodes > 0 else 0.0
        
        # Extract node states if available
        node_states = None
        if execution.node_results and isinstance(execution.node_results, dict) and '__states__' in execution.node_results:
            node_states = execution.node_results['__states__']
        
        return ChainExecutionStatusResponse(
            execution_id=execution.id,
            status=ChainExecutionStatus(execution.status),
            current_node_id=execution.current_node_id,
            completed_nodes=execution.completed_nodes or [],
            node_states=node_states,
            progress_percentage=progress,
            error_message=execution.error_message
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting execution status {execution_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get execution status: {str(e)}"
        )


@router.post("/executions/{execution_id}/cancel", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_execution(
    execution_id: UUID,
    session: AsyncSession = Depends(get_async_db),
    orchestrator: ChainOrchestratorService = Depends(get_chain_orchestrator_service)
):
    """Cancel a running execution."""
    try:
        await orchestrator.cancel_execution(session, execution_id)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error cancelling execution {execution_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel execution: {str(e)}"
        )


@router.get("/executions/{execution_id}/logs", response_model=List[ChainExecutionLogResponse])
async def get_execution_logs(
    execution_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    level: Optional[str] = None,
    session: AsyncSession = Depends(get_async_db)
):
    """Get logs for an execution."""
    try:
        query = select(ChainExecutionLog).where(ChainExecutionLog.execution_id == execution_id)
        
        if level:
            query = query.where(ChainExecutionLog.level == level.upper())
        
        query = query.order_by(ChainExecutionLog.timestamp).offset(skip).limit(limit)
        
        result = await session.execute(query)
        logs = result.scalars().all()
        
        return [ChainExecutionLogResponse.model_validate(log) for log in logs]
        
    except Exception as e:
        logger.error(f"Error getting execution logs {execution_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get execution logs: {str(e)}"
        )
