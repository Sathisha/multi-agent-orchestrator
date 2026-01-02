"""Chain Orchestrator Service for executing agent chains."""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
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
        correlation_id: Optional[str] = None,
        timeout_seconds: int = 300  # Global timeout: 5 minutes default
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
            started_at=datetime.now(timezone.utc),
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
            chain.last_executed_at = datetime.now(timezone.utc)
            await session.commit()
            
            # Execute the chain with timeout
            logger.info(f"Starting chain execution {execution.id} with timeout {timeout_seconds}s")
            try:
                await asyncio.wait_for(
                    self._execute_chain_internal(
                        session, execution, nodes, edges, input_data
                    ),
                    timeout=timeout_seconds
                )
            except asyncio.TimeoutError:
                logger.error(f"Chain execution {execution.id} timed out after {timeout_seconds}s")
                raise ChainExecutionError(f"Chain execution timeout after {timeout_seconds} seconds")
            
            # Mark as completed
            execution.status = ChainExecutionStatus.COMPLETED
            execution.completed_at = datetime.now(timezone.utc)
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
            execution.completed_at = datetime.now(timezone.utc)
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
        """Internal method to execute chain logic with support for parallel paths and conditions."""
        # 1. Build Graphs
        node_map = {node.node_id: node for node in nodes}
        adj_list = defaultdict(list)          # source -> [dest]
        reverse_adj_list = defaultdict(list)  # dest -> [source]
        
        # Edge management
        edge_map = {} # (source, target) -> edge
        incoming_edges_map = defaultdict(list) # dest -> [edge]
        
        for edge in edges:
            adj_list[edge.source_node_id].append(edge.target_node_id)
            reverse_adj_list[edge.target_node_id].append(edge.source_node_id)
            edge_map[(edge.source_node_id, edge.target_node_id)] = edge
            incoming_edges_map[edge.target_node_id].append(edge)
            
        # 2. Initialize State
        # Node Status: PENDING, RUNNING, COMPLETED, FAILED, SKIPPED
        node_states = {node.node_id: "PENDING" for node in nodes}
        
        # Active Edges: set of edge_ids that are traversed/active
        active_edges = set()
        
        # Inactive Edges: set of edge_ids that were NOT taken (condition false)
        # We need this to determine if a node should be SKIPPED (all incoming edges inactive)
        inactive_edges = set()
        
        context = {
            'input': initial_input,
            'variables': execution.variables.copy() if execution.variables else {},
            'node_outputs': {}
        }
        
        # 3. Identify Initial Ready Nodes
        # Start nodes or nodes with 0 in-degree
        ready_queue = deque([
            n.node_id for n in nodes 
            if not incoming_edges_map[n.node_id] 
            or n.node_type == ChainNodeType.START
        ])
        
        # Also include nodes where all incoming edges are from NON-EXISTENT nodes? (Orphans?)
        # Validation checks this, so assume graph is valid.
        
        running_tasks = set()
        
        async def process_node_task(node_id: str):
            """Execute a single node."""
            node = node_map[node_id]
            node_states[node_id] = "RUNNING"
            
            # Log Start
            await self._log_execution_event(
                session, execution.id, node_id, "node_started",
                f"Starting execution of node {node.label}", "INFO"
            )
            
            try:
                # Prepare Input
                # Note: We pass active_edges to ensure we only aggregate from active paths
                node_input = self._prepare_node_input(node, context, incoming_edges_map, active_edges)
                
                # Execute Logic
                node_output = await self._execute_node(session, node, node_input, context)
                
                # Store Output
                context['node_outputs'][node_id] = node_output
                execution.node_results[node_id] = node_output
                execution.completed_nodes.append(node_id)
                # await session.commit() # Batch commit in main loop? Or here? 
                # Commit here to update progress safely
                
                # Log Success
                await self._log_execution_event(
                    session, execution.id, node_id, "node_completed",
                    f"Node {node.label} completed", "INFO", output_data=node_output
                )
                
                return node_id, "COMPLETED", node_output
                
            except Exception as e:
                logger.error(f"Error executing node {node_id}: {e}", exc_info=True)
                await self._log_execution_event(
                    session, execution.id, node_id, "node_failed",
                    f"Node {node.label} failed: {str(e)}", "ERROR", error_message=str(e)
                )
                return node_id, "FAILED", None
        
        # 4. Execution Loop
        while ready_queue or running_tasks:
            
            # Launch new tasks
            while ready_queue:
                node_id = ready_queue.popleft()
                if node_states[node_id] != "PENDING":
                    continue
                
                # Update DB to show Running
                execution.current_node_id = node_id
                # await session.commit() 
                
                task = asyncio.create_task(process_node_task(node_id))
                task.set_name(node_id)
                running_tasks.add(task)
            
            if not running_tasks:
                break
                
            # Wait for ONE task to complete
            done, pending = await asyncio.wait(
                running_tasks, 
                return_when=asyncio.FIRST_COMPLETED
            )
            running_tasks = pending
            
            for task in done:
                node_id = task.get_name()
                try:
                    nid, status, output = await task
                    node_states[node_id] = status
                    
                    if status == "FAILED":
                        raise ChainExecutionError(f"Node {node_id} failed")
                    
                    # If Completed, evaluate successors
                    if status == "COMPLETED":
                        # Check outgoing edges
                        successors = adj_list[node_id]
                        for succ_id in successors:
                            edge = edge_map.get((node_id, succ_id))
                            if not edge: continue
                            
                            is_met = True
                            if edge.condition:
                                is_met = self._evaluate_condition(edge.condition, output)
                            
                            if is_met:
                                active_edges.add(edge.edge_id)
                            else:
                                inactive_edges.add(edge.edge_id)
                        
                        # Check readiness of all successors
                        # For each successor, check if ALL incoming edges are resolved
                        for succ_id in successors:
                            succ_incoming = incoming_edges_map[succ_id]
                            
                            all_resolved = True
                            any_active = False
                            
                            for in_edge in succ_incoming:
                                if in_edge.edge_id in active_edges:
                                    any_active = True
                                elif in_edge.edge_id in inactive_edges:
                                    pass # Resolved as inactive
                                else:
                                    # Not resolved yet (source node not done?)
                                    # Check source node status
                                    # Actually simpler: just check if edge_id is in active or inactive sets
                                    all_resolved = False
                                    break
                            
                            if all_resolved:
                                if any_active:
                                    # Ready to run
                                    if node_states[succ_id] == "PENDING":
                                        ready_queue.append(succ_id)
                                else:
                                    # All incoming edges inactive -> SKIP
                                    if node_states[succ_id] == "PENDING":
                                        node_states[succ_id] = "SKIPPED"
                                        # Propagate SKIP to its successors?
                                        # To propagate, we treat it as "Done" but with no output/active edges
                                        # So outgoing edges are ALL inactive?
                                        # Yes.
                                        
                                        # Queue it for "Skip Processing" - simply iterate recursively or add to queue?
                                        # Let's handle it immediately here
                                        queue_to_skip = deque([succ_id])
                                        while queue_to_skip:
                                            skip_nid = queue_to_skip.popleft()
                                            
                                            # Log log?
                                            # await self._log_execution_event(session, execution.id, skip_nid, "node_skipped", "Node skipped due to conditions", "INFO")
                                            
                                            # Mark outgoing edges inactive
                                            for out_succ in adj_list[skip_nid]:
                                                out_edge = edge_map.get((skip_nid, out_succ))
                                                if out_edge:
                                                    inactive_edges.add(out_edge.edge_id)
                                                
                                                # Check if successor is now fully inactive-resolved
                                                succ_inc = incoming_edges_map[out_succ]
                                                succ_all_resolved = True
                                                succ_any_active = False
                                                for sie in succ_inc:
                                                    if sie.edge_id in active_edges:
                                                        succ_any_active = True
                                                    elif sie.edge_id not in inactive_edges:
                                                        succ_all_resolved = False
                                                        break
                                                
                                                if succ_all_resolved and not succ_any_active:
                                                    if node_states[out_succ] == "PENDING":
                                                        node_states[out_succ] = "SKIPPED"
                                                        queue_to_skip.append(out_succ)

                except ChainExecutionError:
                    raise
                except Exception as e:
                    logger.error(f"Unexpected error in execution loop: {e}", exc_info=True)
                    raise ChainExecutionError(f"Trapped error: {e}")

        # Set final output
        # Find END nodes that were COMPLETED
        end_nodes = [n for n in nodes if n.node_type == ChainNodeType.END and node_states[n.node_id] == "COMPLETED"]
        if end_nodes and end_nodes[0].node_id in context['node_outputs']:
             execution.output_data = context['node_outputs'][end_nodes[0].node_id]
        else:
            # Fallback: get last completed node
            # Or just empty
             execution.output_data = {}  # Could improve heuristics here
        
        # Save node states in metadata or some field? 
        # (For later UI feature)
        execution.node_results['__states__'] = node_states
        
        await session.commit()
    def _evaluate_condition(self, condition: Dict[str, Any], source_output: Any) -> bool:
        """
        Evaluate if a condition is met based on the source node's output.
        
        Condition format:
        {
            "rules": [
                {
                    "field": "key_in_output",
                    "operator": "eq|neq|contains|gt|lt",
                    "value": "expected_value"
                }
            ],
            "logic": "AND"  # or "OR" (default AND)
        }
        
        If source_output is not a dict, 'field' access works if field is empty or special val?
        Assume source_output is typically a dict (JSON).
        """
        if not condition or not condition.get("rules"):
            return True
            
        rules = condition.get("rules", [])
        logic = condition.get("logic", "AND").upper()
        
        results = []
        for rule in rules:
            field = rule.get("field")
            operator = rule.get("operator", "eq")
            expected_value = rule.get("value")
            
            # Get actual value
            actual_value = source_output
            if isinstance(source_output, dict) and field:
                # Support dot notation? For now simple key access
                actual_value = source_output.get(field)
            elif field:
                # Field specified but output is not dict
                actual_value = None
                
            # Compare
            match = False
            try:
                if operator == "eq":
                    match = str(actual_value) == str(expected_value)
                elif operator == "neq":
                    match = str(actual_value) != str(expected_value)
                elif operator == "contains":
                    match = str(expected_value) in str(actual_value)
                elif operator == "gt":
                    match = float(actual_value) > float(expected_value)
                elif operator == "lt":
                    match = float(actual_value) < float(expected_value)
                elif operator == "exists":
                    match = actual_value is not None
            except Exception:
                match = False
                
            results.append(match)
            
        if not results:
            return True
            
        if logic == "OR":
            return any(results)
        else:
            return all(results)

    def _prepare_node_input(
        self,
        node: ChainNode,
        context: Dict[str, Any],
        incoming_edges_map: Dict[str, List],  # Changed from graph
        active_edges: Optional[Set[str]] = None
    ) -> Dict[str, Any]:
        """
        Prepare input data for a node based on its predecessors.
        Only considers ACTIVE edges if active_edges is provided.
        
        Edges without conditions simply pass data through from predecessor to successor.
        """
        # Find active predecessor nodes via incoming edges
        predecessors = []
        incoming_edges = incoming_edges_map.get(node.node_id, [])
        
        for edge in incoming_edges:
            # If active_edges is None, consider all (no condition filtering)
            # If active_edges is set, edge must be in it
            if active_edges is None or edge.edge_id in active_edges:
                predecessors.append(edge.source_node_id)
        
        if not predecessors:
            # No active predecessors - use initial input
            return context['input']
            
        elif len(predecessors) == 1:
            # Single predecessor - pass through its output
            return context['node_outputs'].get(predecessors[0], {})
        else:
            # Multiple active predecessors - aggregate outputs
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
            from shared.services.agent_executor import AgentExecutorService
            self.agent_executor = AgentExecutorService(session)
        
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
            timestamp=datetime.now(timezone.utc),
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
        execution.completed_at = datetime.now(timezone.utc)
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
