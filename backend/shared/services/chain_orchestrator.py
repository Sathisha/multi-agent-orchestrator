"""Chain Orchestrator Service for executing agent chains."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set, Tuple
from uuid import UUID
from collections import defaultdict, deque

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from shared.models.chain import (
    Chain, ChainNode, ChainEdge, ChainExecution, ChainExecutionLog,
    ChainStatus, ChainNodeType, ChainExecutionStatus
)
from shared.models.agent import Agent
from shared.schemas.chain import ChainValidationResult
from shared.services.base import BaseService

logger = logging.getLogger(__name__)


class ChainValidationError(Exception):
    """Raised when chain validation fails."""
    pass


class ChainExecutionError(Exception):
    """Raised when chain execution fails."""
    pass


class CyclicDependencyError(ChainValidationError):
    """Raised when a cyclic dependency is detected in the chain."""
    pass


class ChainOrchestratorService(BaseService):
    """Service for orchestrating agent chains."""
    
    def __init__(
        self,
        agent_executor_service=None,
        memory_manager_service=None,
        guardrails_service=None
    ):
        """
        Initialize chain orchestrator service.
        
        Args:
            agent_executor_service: Service for executing agents
            memory_manager_service: Service for managing memory
            guardrails_service: Service for guardrails
        """
        self.agent_executor = agent_executor_service
        self.memory_manager = memory_manager_service
        self.guardrails = guardrails_service
        
        logger.info("Chain orchestrator service initialized")
    
    async def validate_chain(
        self, 
        session: AsyncSession, 
        chain_id: UUID
    ) -> ChainValidationResult:
        """
        Validate chain structure and configuration.
        
        Args:
            session: Database session
            chain_id: Chain ID to validate
            
        Returns:
            Validation result with errors and warnings
        """
        errors = []
        warnings = []
        details = {}
        
        try:
            # Load chain
            result = await session.execute(
                select(Chain).where(Chain.id == chain_id)
            )
            chain = result.scalar_one_or_none()
            
            if not chain:
                errors.append(f"Chain {chain_id} not found")
                return ChainValidationResult(
                    is_valid=False,
                    errors=errors,
                    warnings=warnings,
                    details=details
                )
            
            # Load nodes and edges
            nodes_result = await session.execute(
                select(ChainNode).where(ChainNode.chain_id == chain_id)
            )
            nodes = list(nodes_result.scalars().all())
            
            edges_result = await session.execute(
                select(ChainEdge).where(ChainEdge.chain_id == chain_id)
            )
            edges = list(edges_result.scalars().all())
            
            if not nodes:
                errors.append("Chain has no nodes")
                return ChainValidationResult(
                    is_valid=False,
                    errors=errors,
                    warnings=warnings,
                    details=details
                )
            
            # Build node map
            node_map = {node.node_id: node for node in nodes}
            details['node_count'] = len(nodes)
            details['edge_count'] = len(edges)
            
            # Validate edges reference valid nodes
            for edge in edges:
                if edge.source_node_id not in node_map:
                    errors.append(
                        f"Edge {edge.edge_id} references non-existent source node {edge.source_node_id}"
                    )
                if edge.target_node_id not in node_map:
                    errors.append(
                        f"Edge {edge.edge_id} references non-existent target node {edge.target_node_id}"
                    )
            
            # Check for cycles
            cycle_check = self._check_for_cycles(nodes, edges)
            if cycle_check['has_cycle']:
                errors.append(f"Chain contains cyclic dependencies: {cycle_check['cycle_path']}")
                details['cycle_detected'] = True
            
            # Validate agent references exist
            agent_nodes = [n for n in nodes if n.node_type == ChainNodeType.AGENT]
            for node in agent_nodes:
                if not node.agent_id:
                    errors.append(f"Agent node {node.node_id} has no agent_id")
                else:
                    # Check if agent exists
                    agent_result = await session.execute(
                        select(Agent).where(Agent.id == node.agent_id)
                    )
                    agent = agent_result.scalar_one_or_none()
                    if not agent:
                        errors.append(f"Agent node {node.node_id} references non-existent agent {node.agent_id}")
                    elif agent.status != "active":
                        warnings.append(
                            f"Agent node {node.node_id} references inactive agent '{agent.name}'"
                        )
            
            # Check for disconnected nodes (orphans)
            connected_nodes = set()
            for edge in edges:
                connected_nodes.add(edge.source_node_id)
                connected_nodes.add(edge.target_node_id)
            
            disconnected = set(node_map.keys()) - connected_nodes
            if len(disconnected) > 1:  # More than just a start node
                warnings.append(f"Chain has {len(disconnected)} disconnected nodes: {list(disconnected)}")
            
            # Check for start and end nodes
            start_nodes = [n for n in nodes if n.node_type == ChainNodeType.START]
            end_nodes = [n for n in nodes if n.node_type == ChainNodeType.END]
            
            if not start_nodes and len(nodes) > 1:
                warnings.append("Chain has no explicit start node")
            if len(start_nodes) > 1:
                warnings.append(f"Chain has multiple start nodes: {[n.node_id for n in start_nodes]}")
            if not end_nodes and len(nodes) > 1:
                warnings.append("Chain has no explicit end node")
            
            is_valid = len(errors) == 0
            
            return ChainValidationResult(
                is_valid=is_valid,
                errors=errors,
                warnings=warnings,
                details=details
            )
            
        except Exception as e:
            logger.error(f"Error validating chain {chain_id}: {e}", exc_info=True)
            errors.append(f"Validation error: {str(e)}")
            return ChainValidationResult(
                is_valid=False,
                errors=errors,
                warnings=warnings,
                details=details
            )
    
    def _check_for_cycles(
        self, 
        nodes: List[ChainNode], 
        edges: List[ChainEdge]
    ) -> Dict[str, Any]:
        """
        Check for cycles in the chain using DFS.
        
        Args:
            nodes: List of chain nodes
            edges: List of chain edges
            
        Returns:
            Dictionary with has_cycle and cycle_path
        """
        # Build adjacency list
        graph = defaultdict(list)
        for edge in edges:
            graph[edge.source_node_id].append(edge.target_node_id)
        
        visited = set()
        rec_stack = set()
        cycle_path = []
        
        def dfs(node_id: str, path: List[str]) -> bool:
            """DFS to detect cycles."""
            visited.add(node_id)
            rec_stack.add(node_id)
            path.append(node_id)
            
            for neighbor in graph.get(node_id, []):
                if neighbor not in visited:
                    if dfs(neighbor, path):
                        return True
                elif neighbor in rec_stack:
                    # Found a cycle
                    cycle_start = path.index(neighbor)
                    cycle_path.extend(path[cycle_start:] + [neighbor])
                    return True
            
            rec_stack.remove(node_id)
            path.pop()
            return False
        
        node_ids = [node.node_id for node in nodes]
        for node_id in node_ids:
            if node_id not in visited:
                if dfs(node_id, []):
                    return {'has_cycle': True, 'cycle_path': cycle_path}
        
        return {'has_cycle': False, 'cycle_path': []}
    
    def _topological_sort(
        self, 
        nodes: List[ChainNode], 
        edges: List[ChainEdge]
    ) -> List[str]:
        """
        Perform topological sort to determine execution order.
        
        Args:
            nodes: List of chain nodes
            edges: List of chain edges
            
        Returns:
            List of node IDs in execution order
            
        Raises:
            CyclicDependencyError: If the graph contains cycles
        """
        # Build adjacency list and in-degree map
        graph = defaultdict(list)
        in_degree = {node.node_id: 0 for node in nodes}
        
        for edge in edges:
            graph[edge.source_node_id].append(edge.target_node_id)
            in_degree[edge.target_node_id] = in_degree.get(edge.target_node_id, 0) + 1
        
        # Find all nodes with no incoming edges
        queue = deque([node_id for node_id, degree in in_degree.items() if degree == 0])
        result = []
        
        while queue:
            node_id = queue.popleft()
            result.append(node_id)
            
            # Reduce in-degree for neighbors
            for neighbor in graph[node_id]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        # If result doesn't contain all nodes, there's a cycle
        if len(result) != len(nodes):
            raise CyclicDependencyError("Chain contains cyclic dependencies")
        
        return result
    
    async def execute_chain(
        self,
        session: AsyncSession,
        chain_id: UUID,
        input_data: Dict[str, Any],
        execution_name: Optional[str] = None,
        variables: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None
    ) -> ChainExecution:
        """
        Execute a chain.
        
        Args:
            session: Database session
            chain_id: Chain ID to execute
            input_data: Input data for the chain
            execution_name: Optional name for this execution
            variables: Optional initial variables
            correlation_id: Optional correlation ID
            
        Returns:
            ChainExecution object
            
        Raises:
            ChainValidationError: If chain validation fails
            ChainExecutionError: If execution fails
        """
        logger.info(f"Starting chain execution for chain {chain_id}")
        
        # Validate chain first
        validation_result = await self.validate_chain(session, chain_id)
        if not validation_result.is_valid:
            raise ChainValidationError(
                f"Chain validation failed: {', '.join(validation_result.errors)}"
            )
        
        # Load chain with nodes and edges
        nodes_result = await session.execute(
            select(ChainNode).where(ChainNode.chain_id == chain_id).order_by(ChainNode.order_index)
        )
        nodes = list(nodes_result.scalars().all())
        
        edges_result = await session.execute(
            select(ChainEdge).where(ChainEdge.chain_id == chain_id)
        )
        edges = list(edges_result.scalars().all())
        
        # Create execution record
        execution = ChainExecution(
            chain_id=chain_id,
            execution_name=execution_name,
            status=ChainExecutionStatus.RUNNING,
            input_data=input_data,
            variables=variables or {},
            node_results={},
            started_at=datetime.utcnow(),
            completed_nodes=[],
            correlation_id=correlation_id
        )
        session.add(execution)
        await session.commit()
        await session.refresh(execution)
        
        try:
            # Update chain execution count
            chain_result = await session.execute(
                select(Chain).where(Chain.id == chain_id)
            )
            chain = chain_result.scalar_one()
            chain.execution_count += 1
            chain.last_executed_at = datetime.utcnow()
            await session.commit()
            
            # Execute the chain
            await self._execute_chain_internal(
                session, execution, nodes, edges, input_data
            )
            
            # Mark as completed
            execution.status = ChainExecutionStatus.COMPLETED
            execution.completed_at = datetime.utcnow()
            if execution.started_at:
                execution.duration_seconds = int(
                    (execution.completed_at - execution.started_at).total_seconds()
                )
            
            await session.commit()
            await session.refresh(execution)
            
            logger.info(f"Chain execution {execution.id} completed successfully")
            return execution
            
        except Exception as e:
            logger.error(f"Chain execution {execution.id} failed: {e}", exc_info=True)
            
            # Mark as failed
            execution.status = ChainExecutionStatus.FAILED
            execution.error_message = str(e)
            execution.error_details = {'exception_type': type(e).__name__}
            execution.completed_at = datetime.utcnow()
            if execution.started_at:
                execution.duration_seconds = int(
                    (execution.completed_at - execution.started_at).total_seconds()
                )
            
            await session.commit()
            await session.refresh(execution)
            
            raise ChainExecutionError(f"Chain execution failed: {str(e)}") from e
    
    async def _execute_chain_internal(
        self,
        session: AsyncSession,
        execution: ChainExecution,
        nodes: List[ChainNode],
        edges: List[ChainEdge],
        initial_input: Dict[str, Any]
    ):
        """Internal method to execute chain logic."""
        # Build node and edge maps
        node_map = {node.node_id: node for node in nodes}
        
        # Build adjacency list for the graph
        graph = defaultdict(list)
        for edge in edges:
            graph[edge.source_node_id].append({
                'target': edge.target_node_id,
                'edge': edge
            })
        
        # Determine execution order
        execution_order = self._topological_sort(nodes, edges)
        
        # Execution context
        context = {
            'input': initial_input,
            'variables': execution.variables.copy() if execution.variables else {},
            'node_outputs': {}
        }
        
        # Execute nodes in order
        for node_id in execution_order:
            node = node_map[node_id]
            
            # Update current node
            execution.current_node_id = node_id
            await session.commit()
            
            # Log event
            await self._log_execution_event(
                session,
                execution.id,
                node_id,
                "node_started",
                f"Starting execution of node {node.label}",
                "INFO"
            )
            
            try:
                # Prepare input for this node
                node_input = self._prepare_node_input(node, context, graph)
                
                # Execute based on node type
                node_output = await self._execute_node(session, node, node_input, context)
                
                # Store result
                context['node_outputs'][node_id] = node_output
                execution.node_results[node_id] = node_output
                execution.completed_nodes.append(node_id)
                
                await session.commit()
                
                # Log success
                await self._log_execution_event(
                    session,
                    execution.id,
                    node_id,
                    "node_completed",
                    f"Node {node.label} completed successfully",
                    "INFO",
                    output_data=node_output
                )
                
            except Exception as e:
                logger.error(f"Error executing node {node_id}: {e}", exc_info=True)
                
                # Log error
                await self._log_execution_event(
                    session,
                    execution.id,
                    node_id,
                    "node_failed",
                    f"Node {node.label} failed: {str(e)}",
                    "ERROR",
                    error_message=str(e)
                )
                
                raise
        
        # Set final output
        # If there's an END node, use its output; otherwise use last node's output
        end_nodes = [n for n in nodes if n.node_type == ChainNodeType.END]
        if end_nodes and end_nodes[0].node_id in context['node_outputs']:
            execution.output_data = context['node_outputs'][end_nodes[0].node_id]
        elif execution_order:
            execution.output_data = context['node_outputs'].get(execution_order[-1], {})
        else:
            execution.output_data = {}
    
    def _prepare_node_input(
        self,
        node: ChainNode,
        context: Dict[str, Any],
        graph: Dict[str, List[Dict]]
    ) -> Dict[str, Any]:
        """Prepare input data for a node based on its predecessors."""
        # For START nodes or nodes with no predecessors, use initial input
        # For other nodes, use outputs from predecessor nodes
        
        # Find predecessor nodes
        predecessors = []
        for source_id, targets in graph.items():
            for target_info in targets:
                if target_info['target'] == node.node_id:
                    predecessors.append(source_id)
        
        if not predecessors:
            # Use initial input
            return context['input']
        elif len(predecessors) == 1:
            # Use output from single predecessor
            pred_output = context['node_outputs'].get(predecessors[0], {})
            return pred_output
        else:
            # Multiple predecessors - aggregate outputs
            aggregated = {
                'inputs': [context['node_outputs'].get(pred_id, {}) for pred_id in predecessors]
            }
            return aggregated
    
    async def _execute_node(
        self,
        session: AsyncSession,
        node: ChainNode,
        input_data: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a single node based on its type."""
        if node.node_type == ChainNodeType.AGENT:
            return await self._execute_agent_node(session, node, input_data, context)
        elif node.node_type == ChainNodeType.AGGREGATOR:
            return await self._execute_aggregator_node(node, input_data, context)
        elif node.node_type == ChainNodeType.CONDITION:
            return await self._execute_condition_node(node, input_data, context)
        elif node.node_type in [ChainNodeType.START, ChainNodeType.END]:
            # Pass-through nodes
            return input_data
        elif node.node_type == ChainNodeType.PARALLEL_SPLIT:
            # Pass input to all outgoing edges
            return input_data
        elif node.node_type == ChainNodeType.PARALLEL_JOIN:
            # Aggregate inputs (already done in prepare_node_input)
            return input_data
        else:
            logger.warning(f"Unknown node type: {node.node_type}, treating as pass-through")
            return input_data
    
    async def _execute_agent_node(
        self,
        session: AsyncSession,
        node: ChainNode,
        input_data: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute an agent node."""
        if not self.agent_executor:
            # Import here to avoid circular dependency
            from shared.services.agent_executor import lifecycle_manager
            self.agent_executor = lifecycle_manager.get_executor(session)
        
        if not node.agent_id:
            raise ChainExecutionError(f"Agent node {node.node_id} has no agent_id")
        
        # Load agent
        agent_result = await session.execute(
            select(Agent).where(Agent.id == node.agent_id)
        )
        agent = agent_result.scalar_one_or_none()
        
        if not agent:
            raise ChainExecutionError(f"Agent {node.agent_id} not found")
        
        # Execute agent
        logger.info(f"Executing agent {agent.name} (node {node.node_id})")
        
        execution_result = await self.agent_executor.execute_agent(
            agent_id=agent.id,
            input_data=input_data,
            config=node.config or {}
        )
        
        # Return agent output
        return execution_result.output_data or {}
    
    async def _execute_aggregator_node(
        self,
        node: ChainNode,
        input_data: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute an aggregator node (combines multiple inputs)."""
        aggregation_type = node.config.get('aggregation_type', 'merge')
        
        # Get inputs
        inputs = input_data.get('inputs', [])
        
        if aggregation_type == 'merge':
            # Merge all inputs into one dict
            result = {}
            for item in inputs:
                if isinstance(item, dict):
                    result.update(item)
            return result
        elif aggregation_type == 'concat':
            # Concatenate as list
            return {'aggregated_results': inputs}
        elif aggregation_type == 'first':
            # Take first non-empty result
            for item in inputs:
                if item:
                    return item
            return {}
        else:
            # Default: return as list
            return {'results': inputs}
    
    async def _execute_condition_node(
        self,
        node: ChainNode,
        input_data: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a condition node (routing logic)."""
        # For now, just pass through
        # In the future, evaluate conditions and modify routing
        return input_data
    
    async def _log_execution_event(
        self,
        session: AsyncSession,
        execution_id: UUID,
        node_id: Optional[str],
        event_type: str,
        message: str,
        level: str = "INFO",
        **kwargs
    ):
        """Log an execution event."""
        log_entry = ChainExecutionLog(
            execution_id=execution_id,
            node_id=node_id,
            event_type=event_type,
            message=message,
            level=level,
            timestamp=datetime.utcnow(),
            log_metadata=kwargs
        )
        session.add(log_entry)
        await session.commit()
    
    async def cancel_execution(
        self,
        session: AsyncSession,
        execution_id: UUID
    ):
        """Cancel a running execution."""
        result = await session.execute(
            select(ChainExecution).where(ChainExecution.id == execution_id)
        )
        execution = result.scalar_one_or_none()
        
        if not execution:
            raise ValueError(f"Execution {execution_id} not found")
        
        if execution.status != ChainExecutionStatus.RUNNING:
            raise ValueError(f"Execution {execution_id} is not running")
        
        execution.status = ChainExecutionStatus.CANCELLED
        execution.completed_at = datetime.utcnow()
        if execution.started_at:
            execution.duration_seconds = int(
                (execution.completed_at - execution.started_at).total_seconds()
            )
        
        await session.commit()
        
        await self._log_execution_event(
            session,
            execution_id,
            None,
            "execution_cancelled",
            "Execution cancelled by user",
            "WARNING"
        )
        
        logger.info(f"Execution {execution_id} cancelled")
