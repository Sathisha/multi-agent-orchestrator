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
from sqlalchemy.orm.attributes import flag_modified

from shared.models.chain import (
    Chain, ChainNode, ChainEdge, ChainExecution, ChainExecutionLog,
    ChainStatus, ChainNodeType, ChainExecutionStatus
)
from shared.database.connection import get_database_session
from shared.models.agent import Agent
from shared.schemas.chain import ChainValidationResult
from shared.services.base import BaseService
from shared.services.agent_executor import AgentExecutorService

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
        guardrails_service=None,
        session_maker=None
    ):
        """
        Initialize chain orchestrator service.
        
        Args:
            agent_executor_service: Service for executing agents
            memory_manager_service: Service for managing memory
            guardrails_service: Service for guardrails
            session_maker: Session maker to use for parallel tasks
        """
        # ChainOrchestrator handles multiple entities, not a single model
        self.agent_executor = agent_executor_service
        self.memory_manager = memory_manager_service
        self.guardrails = guardrails_service
        self._session_maker = session_maker
        
        logger.info("Chain orchestrator service initialized")

    @property
    def session_maker(self):
        """Get the session maker, defaulting to the one from connection module."""
        if self._session_maker:
            return self._session_maker
        from shared.database.connection import AsyncSessionLocal
        return AsyncSessionLocal
    
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
    
# Third-Party Dependencies

# This document tracks all third-party libraries, frameworks, and Docker images used in the AI Agent Framework project.

# **Last Updated:** January 18, 2026

# ## Recent Changes

# ### January 18, 2026 - Architecture Simplification & Google Gemini Integration
# - **Backend**: Added Google Generative AI SDK (`google-genai>=1.0.0`) for Gemini model support
# - **Backend**: Added built-in tools dependencies (requests, beautifulsoup4, pytz, jsonschema)
# - **Architecture**: Removed Camunda/Zeebe BPMN dependencies (migrated to internal workflow engine)
# - **Infrastructure**: Removed Elasticsearch dependency (no longer needed without Camunda)

# ### January 6, 2026 - Dependency Synchronization
# - **Backend**: Verified against `backend/requirements.txt`
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
    async def create_execution(
        self,
        session: AsyncSession,
        chain_id: UUID,
        input_data: Dict[str, Any],
        execution_name: Optional[str] = None,
        variables: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
        model_override: Optional[Dict[str, Any]] = None
    ) -> ChainExecution:
        """Create execution record without running it."""
        # Validate chain first
        validation_result = await self.validate_chain(session, chain_id)
        if not validation_result.is_valid:
            raise ChainValidationError(
                f"Chain validation failed: {', '.join(validation_result.errors)}"
            )
        
        # Prepare variables, injecting model override if present
        exec_variables = variables or {}
        if model_override:
            exec_variables['_model_override'] = model_override

        # Create execution record
        execution = ChainExecution(
            chain_id=chain_id,
            execution_name=execution_name,
            status=ChainExecutionStatus.RUNNING, # Ideally QUEUED, but keeping RUNNING for now
            input_data=input_data,
            variables=exec_variables,
            node_results={},
            started_at=datetime.now(timezone.utc),
            completed_nodes=[],
            active_edges=[],
            edge_results={},
            correlation_id=correlation_id
        )
        session.add(execution)
        await session.commit()
        await session.refresh(execution)
        
        # Update chain execution count
        chain_result = await session.execute(
            select(Chain).where(Chain.id == chain_id)
        )
        chain = chain_result.scalar_one()
        chain.execution_count += 1
        chain.last_executed_at = datetime.now(timezone.utc)
        await session.commit()
        
        return execution

    async def run_execution_background(self, execution_id: UUID, timeout_seconds: int = 300):
        """Run execution in a separate session (for background tasks)."""
        async with get_database_session() as session:
            try:
                # Load execution
                result = await session.execute(
                    select(ChainExecution).where(ChainExecution.id == execution_id)
                )
                execution = result.scalar_one_or_none()
                if not execution:
                    logger.error(f"Execution {execution_id} not found for background run")
                    return

                # Load components
                nodes_result = await session.execute(
                    select(ChainNode).where(ChainNode.chain_id == execution.chain_id).order_by(ChainNode.order_index)
                )
                nodes = list(nodes_result.scalars().all())
                
                edges_result = await session.execute(
                    select(ChainEdge).where(ChainEdge.chain_id == execution.chain_id)
                )
                edges = list(edges_result.scalars().all())

                # Run logic
                await self._run_execution_logic(session, execution, nodes, edges, execution.input_data, timeout_seconds)

            except Exception as e:
                logger.error(f"Background execution {execution_id} failed: {e}", exc_info=True)

    async def execute_chain(
        self,
        session: AsyncSession,
        chain_id: UUID,
        input_data: Dict[str, Any],
        execution_name: Optional[str] = None,
        variables: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
        model_override: Optional[Dict[str, Any]] = None,
        timeout_seconds: int = 300
    ) -> ChainExecution:
        """Execute chain synchronously (legacy/backward compatibility)."""
        logger.info(f"Starting synchronous chain execution for chain {chain_id}")
        
        execution = await self.create_execution(
            session, chain_id, input_data, execution_name, variables, correlation_id, model_override
        )
        
        # Load components for execution
        nodes_result = await session.execute(
            select(ChainNode).where(ChainNode.chain_id == chain_id).order_by(ChainNode.order_index)
        )
        nodes = list(nodes_result.scalars().all())
        
        edges_result = await session.execute(
            select(ChainEdge).where(ChainEdge.chain_id == chain_id)
        )
        edges = list(edges_result.scalars().all())

        await self._run_execution_logic(session, execution, nodes, edges, input_data, timeout_seconds)
        return execution

    async def _run_execution_logic(
        self, 
        session: AsyncSession, 
        execution: ChainExecution, 
        nodes: List[ChainNode], 
        edges: List[ChainEdge],
        input_data: Dict[str, Any],
        timeout_seconds: int
    ):
        """Core execution logic wrapper with error handling and updates."""
        try:
            logger.info(f"Starting chain execution logic {execution.id} with timeout {timeout_seconds}s")
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
                start_dt = execution.started_at
                if start_dt.tzinfo is None:
                    start_dt = start_dt.replace(tzinfo=timezone.utc)
                execution.duration_seconds = int(
                    (execution.completed_at - start_dt).total_seconds()
                )
            
            await session.commit()
            await session.refresh(execution)
            logger.info(f"Chain execution {execution.id} completed successfully")
            
        except Exception as e:
            logger.error(f"Chain execution {execution.id} failed: {e}", exc_info=True)
            
            # Mark as failed
            execution.status = ChainExecutionStatus.FAILED
            execution.error_message = str(e)
            execution.error_details = {'exception_type': type(e).__name__}
            execution.completed_at = datetime.now(timezone.utc)
            if execution.started_at:
                start_dt = execution.started_at
                if start_dt.tzinfo is None:
                    start_dt = start_dt.replace(tzinfo=timezone.utc)
                execution.duration_seconds = int(
                    (execution.completed_at - start_dt).total_seconds()
                )
            
            await session.commit()
            await session.refresh(execution)
            
            # Re-raise if synchronous? No, let caller handle or just log.
            # If called from background, this exception is caught by run_execution_background
            # If called from execute_chain, it propagates.
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
        # Inactive Edges: set of edge_ids that were NOT taken (condition false)
        # We need this to determine if a node should be SKIPPED (all incoming edges inactive)
        inactive_edges = set()
        
        # Edge Results: track condition evaluation
        edge_results = {}

        
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
            # Create a dedicated session for this task to allow parallel execution
            # Use the session_maker to ensure we use the same DB as the main loop (Real DB or Test DB)
            async with self.session_maker() as task_session:
                node = node_map[node_id]
                node_states[node_id] = "RUNNING"
                
                # Log Start
                await self._log_execution_event(
                    task_session, execution.id, node_id, "node_started",
                    f"Starting execution of node {node.label}", "INFO"
                )
                
                try:
                    # Prepare Input
                    # Note: We pass active_edges to ensure we only aggregate from active paths
                    node_input = self._prepare_node_input(node, context, incoming_edges_map, active_edges)
                    
                    # Execute Logic
                    # We pass the task_session to ensure isolation
                    node_output = await self._execute_node(task_session, node, node_input, context)
                    
                    # Store Output
                    # context['node_outputs'] stores just the output for easy chaining
                    context['node_outputs'][node_id] = node_output
                    
                    # execution.node_results stores full trace (input + output)
                    execution.node_results[node_id] = {
                        "input": node_input,
                        "output": node_output,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                    execution.completed_nodes.append(node_id)
                    
                    # Mark JSONB fields as modified so SQLAlchemy persists changes
                    flag_modified(execution, "node_results")
                    flag_modified(execution, "completed_nodes")
                    
                    # Log Success
                    await self._log_execution_event(
                        task_session, execution.id, node_id, "node_completed",
                        f"Node {node.label} completed", "INFO", output_data=node_output
                    )
                    
                    await task_session.commit()
                    return node_id, "COMPLETED", node_output
                    
                except Exception as e:
                    logger.error(f"Error executing node {node_id}: {e}", exc_info=True)
                    await self._log_execution_event(
                        task_session, execution.id, node_id, "node_failed",
                        f"Node {node.label} failed: {str(e)}", "ERROR", error_message=str(e)
                    )
                    await task_session.commit()
                    return node_id, "FAILED", None
        
        # 4. Execution Loop
        while ready_queue or running_tasks:
            
            # Launch new tasks
            while ready_queue:
                node_id = ready_queue.popleft()
                if node_states[node_id] != "PENDING":
                    continue
                
                # Update DB to show Running
                # Update DB to show Running
                execution.current_node_id = node_id
                
                # Persist intermediate state
                execution.active_edges = list(active_edges)
                execution.edge_results = edge_results
                await session.commit() 
 
                
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
                                edge_results[edge.edge_id] = {"met": True, "output": output}
                            else:
                                inactive_edges.add(edge.edge_id)
                                edge_results[edge.edge_id] = {"met": False, "output": output}
                        
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
            if execution.completed_nodes:
                last_node_id = execution.completed_nodes[-1]
                execution.output_data = context['node_outputs'].get(last_node_id, {})
            else:
                execution.output_data = {}
        
        # Save execution state
        execution.active_edges = list(active_edges)
        
        # Save node states in metadata or some field? 
        # (For later UI feature)
        execution.node_results['__states__'] = node_states
        execution.completed_nodes = list(execution.completed_nodes) # Ensure list
        
        # Mark JSONB fields as modified for final commit
        flag_modified(execution, "node_results")
        flag_modified(execution, "active_edges")
        flag_modified(execution, "completed_nodes")
        
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
        if not condition:
            return True

        # Handle simplified/legacy condition format (from seed_data.py)
        if "type" in condition:
            cond_type = condition["type"]
            if cond_type == "json_contains":
                field = condition.get("field")
                expected_value = condition.get("value")
                
                # Resolve value logic (duplicated from rules loop for now)
                actual_value = source_output
                if isinstance(source_output, dict) and field:
                    parts = field.split('.')
                    current = source_output
                    found = True
                    for part in parts:
                        if isinstance(current, dict) and part in current:
                            current = current[part]
                        else:
                            found = False
                            break
                    if found:
                        actual_value = current
                    else:
                        actual_value = None
                elif field:
                    actual_value = None
                    
                # Strict comparison for boolean, string looseness for others?
                # Matching logic from rules:
                return str(actual_value) == str(expected_value)
            return False

        if not condition.get("rules"):
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
                # Support dot notation
                parts = field.split('.')
                current = source_output
                found = True
                for part in parts:
                    if isinstance(current, dict) and part in current:
                        current = current[part]
                    else:
                        found = False
                        break
                
                if found:
                    actual_value = current
                else:
                    actual_value = None
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

    def _resolve_value(self, value: Any, context: Dict[str, Any]) -> Any:
        """Resolve value from context variables or node outputs."""
        if isinstance(value, str) and "{{" in value and "}}" in value:
            # Simple replacement for now (can be enhanced with regex or jinja2)
            # Handle direct reference: {{node_id.field}}
            if value.startswith("{{") and value.endswith("}}"):
                path = value[2:-2].strip().split('.')
                if len(path) == 2:
                    node_id, field = path
                    # Check node_outputs first
                    node_output = context['node_outputs'].get(node_id, {})
                    if isinstance(node_output, dict):
                        return node_output.get(field)
                    return None # Reference failed
                elif len(path) == 1:
                    # Referencing simpler things?
                     pass
            
            # Handle string interpolation if needed, but for now stick to direct object mapping
        return value

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
        # 1. Determine base input from connection flow
        base_input = {}
        
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
            base_input = context['input']
            
        elif len(predecessors) == 1:
            # Single predecessor - pass through its output
            base_input = context['node_outputs'].get(predecessors[0], {})
        else:
            # Multiple active predecessors - aggregate outputs
            base_input = {
                'inputs': [context['node_outputs'].get(pred_id, {}) for pred_id in predecessors]
            }
            
        # 2. Apply Input Mapping if defined (overrides/augments base input)
        input_map = node.config.get('input_map')
        if input_map:
            mapped_input = {}
            for key, value in input_map.items():
                mapped_input[key] = self._resolve_value(value, context)
            
            # If base_input is a dict, merge mapping INTO it (mapping takes precedence)
            if isinstance(base_input, dict):
                # We want a new dict with base keys + mapped keys
                # If mapped key conflicts, it overwrites
                return {**base_input, **mapped_input}
            else:
                # If base_input is string/list, we can't easily merge. 
                # If input_map is present, it implies we want structured input.
                # So we simply return the mapped_input, assuming user knows what they want.
                # Unless we define a convention like 'base_content' key.
                return mapped_input
                
        return base_input

    
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
        logger.info(f"DEBUG: _execute_agent_node Input: {input_data.keys()}")
        
        if not self.agent_executor:
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
        
        # Prepare agent logic with support for Structured Output
        output_schema = node.config.get('output_schema')
        
        # Always create a new executor with the CURRENT session to support parallelism
        # self.agent_executor might hold a shared/stale session
        local_agent_executor = AgentExecutorService(session)
        
        # Prepare input
        processed_input = input_data
        
        # Inject output schema instruction if provided
        if output_schema:
            try:
                import json
                schema_str = json.dumps(output_schema, indent=2)
                instruction = f"\n\nIMPORTANT: You MUST return your response in a valid JSON format matching this schema:\n{schema_str}\n\nDo not include any other text."
                
                # If input is string, append
                if isinstance(processed_input, str):
                    processed_input += instruction
                # If input is dict, append to 'message' or 'content' key
                elif isinstance(processed_input, dict):
                    # Create a copy to avoid mutating original input_data
                    processed_input = processed_input.copy()
                    if 'message' in processed_input and isinstance(processed_input['message'], str):
                        processed_input['message'] += instruction
                    else:
                        # Fallback: add to system_instruction if possible, or just log warning that we couldn't inject
                        processed_input['_system_instruction_injection'] = instruction
            except Exception as e:
                logger.warning(f"Failed to inject output schema instruction: {e}")
        
        logger.info(f"[CHAIN] Executing agent node {node.node_id} (agent: {agent.name})")
        logger.debug(f"[CHAIN] Agent node input_data: {input_data}")
        
        # Check for model override in variables
        model_override = context.get('variables', {}).get('_model_override')
        
        # Prepare execution config
        execution_config = node.config or {}
        if model_override:
            # Merge override into config (override wins). Ensure we don't mutate the original node.config
            execution_config = {**execution_config, **model_override}
            logger.info(f"[CHAIN] Applying model override to agent execution: {model_override}")

        execution_result = await local_agent_executor.execute_agent(
            agent_id=str(agent.id),
            input_data=processed_input,
            config=execution_config
        )
        
        logger.info(f"[CHAIN] Agent execution completed. Status: {execution_result.status}")
        logger.debug(f"[CHAIN] Execution result output_data: {execution_result.output_data}")
        
        # Check if execution failed
        if execution_result.status == "FAILED" or execution_result.status == "failed":
            error_output = {
                "error": True,
                "error_message": execution_result.error_message or "Agent execution failed",
                "status": "failed"
            }
            logger.warning(f"[CHAIN] Agent node {node.node_id} failed: {execution_result.error_message}")
            logger.info(f"[CHAIN] Agent node {node.node_id} returning error output: {error_output}")
            return error_output
        
        # Return agent output
        result_data = execution_result.output_data or {}
        logger.debug(f"[CHAIN] Result data after extraction: {result_data}")
        
        # Check if SACP is enabled and parse JSON
        if agent.config.get("use_standard_protocol") or agent.config.get("use_standard_response_format"):
            content = result_data.get("content", "")
            try:
                import json
                import re
                
                json_str = content
                
                # 1. Try to find markdown JSON block
                match = re.search(r"```json\s*(.*?)\s*```", content, re.DOTALL)
                if match:
                    json_str = match.group(1)
                else:
                    # 2. Try to find first { and last }
                    start_idx = content.find('{')
                    end_idx = content.rfind('}')
                    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                        json_str = content[start_idx : end_idx + 1]
                
                # 3. Sanitize
                json_str = json_str.strip()
                
                parsed = json.loads(json_str)
                return parsed
            except Exception as e:
                logger.warning(f"Failed to parse SACP JSON response from agent {agent.name}: {e}")
                # Fallback: Wrap in default structure per spec
                return {
                    "thought": "System Note: LLM failed to provide structured JSON output.",
                    "status": "failure",
                    "data": { "raw_output": content },
                    "message": "The LLM returned an invalid response format."
                }
        
        logger.info(f"[CHAIN] Agent node {node.node_id} returning output: {result_data}")
        return result_data
    
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
        # Don't commit here - logs will be committed with execution updates
        # to avoid concurrent session operations
    
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
