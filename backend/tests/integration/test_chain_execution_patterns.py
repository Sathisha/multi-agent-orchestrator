"""
Comprehensive tests for chain execution patterns including parallel and conditional routing.
"""

import pytest
import asyncio
from uuid import uuid4
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.chain import (
    Chain, ChainNode, ChainEdge, ChainExecution,
    ChainNodeType, ChainStatus, ChainExecutionStatus
)
from shared.models.agent import Agent, AgentType, AgentStatus
from shared.services.chain_orchestrator import ChainOrchestratorService


@pytest.mark.integration
@pytest.mark.asyncio
class TestChainExecutionPatterns:
    """Test various chain execution patterns."""

    @pytest.fixture
    async def test_agent(self, async_session: AsyncSession):
        """Create a test agent for use in chains."""
        agent = Agent(
            name=f"Test Agent {uuid4()}",
            description="Test agent for chain execution",
            type=AgentType.CHATBOT,
            status=AgentStatus.ACTIVE,
            template_id="chatbot-basic",
            config={}
        )
        async_session.add(agent)
        await async_session.commit()
        await async_session.refresh(agent)
        return agent

    @pytest.fixture
    def orchestrator(self):
        """Create chain orchestrator service."""
        return ChainOrchestratorService()

    async def create_chain_with_nodes_edges(
        self,
        session: AsyncSession,
        name: str,
        nodes_data: list,
        edges_data: list
    ) -> Chain:
        """Helper to create a chain with nodes and edges."""
        chain = Chain(
            name=name,
            description=f"Test chain: {name}",
            status=ChainStatus.ACTIVE
        )
        session.add(chain)
        await session.flush()

        # Create nodes
        for node_data in nodes_data:
            node = ChainNode(
                chain_id=chain.id,
                node_id=node_data["id"],
                node_type=ChainNodeType[node_data["type"].upper()],
                label=node_data.get("label", node_data["id"]),
                agent_id=node_data.get("agent_id"),
                position_x=node_data.get("x", 0),
                position_y=node_data.get("y", 0),
                config=node_data.get("config", {})
            )
            session.add(node)

        # Create edges
        for edge_data in edges_data:
            edge = ChainEdge(
                chain_id=chain.id,
                edge_id=edge_data["id"],
                source_node_id=edge_data["source"],
                target_node_id=edge_data["target"],
                label=edge_data.get("label"),
                condition=edge_data.get("condition")
            )
            session.add(edge)

        await session.commit()
        await session.refresh(chain)
        return chain

    async def test_sequential_execution(self, async_session, orchestrator):
        """Test basic sequential chain: START -> END."""
        nodes = [
            {"id": "start", "type": "start", "x": 0, "y": 0},
            {"id": "end", "type": "end", "x": 200, "y": 0}
        ]
        edges = [
            {"id": "e1", "source": "start", "target": "end"}
        ]

        chain = await self.create_chain_with_nodes_edges(
            async_session, "Sequential Test", nodes, edges
        )

        # Execute
        execution = await orchestrator.execute_chain(
            async_session,
            chain.id,
            input_data={"message": "test"}
        )

        assert execution.status == ChainExecutionStatus.COMPLETED
        assert execution.completed_at is not None
        assert execution.duration_seconds is not None

    async def test_parallel_split_join(self, async_session, orchestrator):
        """Test parallel execution with split and join nodes."""
        nodes = [
            {"id": "start", "type": "start"},
            {"id": "split", "type": "parallel_split"},
            {"id": "branch1", "type": "parallel_split"},  # Pass-through
            {"id": "branch2", "type": "parallel_split"},  # Pass-through
            {"id": "join", "type": "parallel_join"},
            {"id": "end", "type": "end"}
        ]
        edges = [
            {"id": "e1", "source": "start", "target": "split"},
            {"id": "e2", "source": "split", "target": "branch1"},
            {"id": "e3", "source": "split", "target": "branch2"},
            {"id": "e4", "source": "branch1", "target": "join"},
            {"id": "e5", "source": "branch2", "target": "join"},
            {"id": "e6", "source": "join", "target": "end"}
        ]

        chain = await self.create_chain_with_nodes_edges(
            async_session, "Parallel Test", nodes, edges
        )

        execution = await orchestrator.execute_chain(
            async_session,
            chain.id,
            input_data={"message": "parallel test"}
        )

        assert execution.status == ChainExecutionStatus.COMPLETED
        
        # Verify all nodes executed
        node_results = execution.node_results or {}
        states = node_results.get('__states__', {})
        
        # All branches should have completed
        assert states.get('branch1') == 'COMPLETED'
        assert states.get('branch2') == 'COMPLETED'
        assert states.get('join') == 'COMPLETED'

    async def test_conditional_routing(self, async_session, orchestrator):
        """Test conditional routing based on edge conditions."""
        nodes = [
            {"id": "start", "type": "start"},
            {"id": "branch_a", "type": "parallel_split"},
            {"id": "branch_b", "type": "parallel_split"},
            {"id": "end", "type": "end"}
        ]
        
        # Edge to branch_a has a condition that will pass
        # Edge to branch_b has a condition that will fail (node should be skipped)
        edges = [
            {"id": "e1", "source": "start", "target": "branch_a",
             "condition": {"rules": [{"field": "message", "operator": "eq", "value": "test"}]}},
            {"id": "e2", "source": "start", "target": "branch_b",
             "condition": {"rules": [{"field": "message", "operator": "eq", "value": "other"}]}},
            {"id": "e3", "source": "branch_a", "target": "end"},
            {"id": "e4", "source": "branch_b", "target": "end"}
        ]

        chain = await self.create_chain_with_nodes_edges(
            async_session, "Conditional Test", nodes, edges
        )

        execution = await orchestrator.execute_chain(
            async_session,
            chain.id,
            input_data={"message": "test"}  # Matches branch_a condition
        )

        assert execution.status == ChainExecutionStatus.COMPLETED
        
        # Check node states
        states = execution.node_results.get('__states__', {})
        
        # branch_a should have executed
        assert states.get('branch_a') == 'COMPLETED'
        
        # branch_b should be skipped because condition didn't match
        assert states.get('branch_b') == 'SKIPPED'

    async def test_cycle_detection_validation(self, async_session, orchestrator):
        """Test that cycle detection prevents execution."""
        nodes = [
            {"id": "node1", "type": "parallel_split"},
            {"id": "node2", "type": "parallel_split"},
            {"id": "node3", "type": "parallel_split"}
        ]
        # Create a cycle: node1 -> node2 -> node3 -> node1
        edges = [
            {"id": "e1", "source": "node1", "target": "node2"},
            {"id": "e2", "source": "node2", "target": "node3"},
            {"id": "e3", "source": "node3", "target": "node1"}
        ]

        chain = await self.create_chain_with_nodes_edges(
            async_session, "Cycle Test", nodes, edges
        )

        # Validation should detect cycle
        validation = await orchestrator.validate_chain(async_session, chain.id)
        
        assert validation.is_valid is False
        assert any("cycle" in error.lower() or "cyclic" in error.lower() 
                  for error in validation.errors)

    async def test_disconnected_nodes_warning(self, async_session, orchestrator):
        """Test that disconnected nodes generate warnings."""
        nodes = [
            {"id": "start", "type": "start"},
            {"id": "connected", "type": "parallel_split"},
            {"id": "orphan", "type": "parallel_split"},  # Not connected
            {"id": "end", "type": "end"}
        ]
        edges = [
            {"id": "e1", "source": "start", "target": "connected"},
            {"id": "e2", "source": "connected", "target": "end"}
        ]

        chain = await self.create_chain_with_nodes_edges(
            async_session, "Disconnected Test", nodes, edges
        )

        validation = await orchestrator.validate_chain(async_session, chain.id)
        
        # Should have warnings about orphan node
        assert len(validation.warnings) > 0
        assert any("disconnected" in warning.lower() or "orphan" in warning.lower()
                  for warning in validation.warnings)

    async def test_condition_operators(self, async_session, orchestrator):
        """Test different condition operators (eq, neq, contains, gt, lt)."""
        test_cases = [
            # (input, condition, should_execute)
            ({"value": 10}, {"rules": [{"field": "value", "operator": "gt", "value": "5"}]}, True),
            ({"value": 3}, {"rules": [{"field": "value", "operator": "gt", "value": "5"}]}, False),
            ({"text": "hello world"}, {"rules": [{"field": "text", "operator": "contains", "value": "world"}]}, True),
            ({"text": "hello"}, {"rules": [{"field": "text", "operator": "contains", "value": "world"}]}, False),
            ({"status": "active"}, {"rules": [{"field": "status", "operator": "neq", "value": "inactive"}]}, True),
        ]

        for idx, (input_data, condition, should_execute) in enumerate(test_cases):
            nodes = [
                {"id": "start", "type": "start"},
                {"id": "conditional", "type": "parallel_split"},
                {"id": "end", "type": "end"}
            ]
            edges = [
                {"id": "e1", "source": "start", "target": "conditional", "condition": condition},
                {"id": "e2", "source": "conditional", "target": "end"}
            ]

            chain = await self.create_chain_with_nodes_edges(
                async_session, f"Condition Op Test {idx}", nodes, edges
            )

            execution = await orchestrator.execute_chain(
                async_session,
                chain.id,
                input_data=input_data
            )

            states = execution.node_results.get('__states__', {})
            
            if should_execute:
                assert states.get('conditional') == 'COMPLETED', \
                    f"Test case {idx}: Expected node to execute"
            else:
                assert states.get('conditional') == 'SKIPPED', \
                    f"Test case {idx}: Expected node to be skipped"

    async def test_empty_chain_execution(self, async_session, orchestrator):
        """Test execution of chain with no nodes."""
        chain = Chain(
            name="Empty Chain",
            description="Chain with no nodes",
            status=ChainStatus.ACTIVE
        )
        async_session.add(chain)
        await async_session.commit()

        # Should fail validation
        validation = await orchestrator.validate_chain(async_session, chain.id)
        assert validation.is_valid is False
        assert any("no nodes" in error.lower() for error in validation.errors)


@pytest.mark.unit
class TestChainOrchestratorHelpers:
    """Test helper methods in ChainOrchestratorService."""

    def test_evaluate_condition_eq(self):
        """Test EQ operator in condition evaluation."""
        orchestrator = ChainOrchestratorService()
        
        condition = {"rules": [{"field": "status", "operator": "eq", "value": "active"}]}
        output = {"status": "active"}
        
        assert orchestrator._evaluate_condition(condition, output) is True
        
        output = {"status": "inactive"}
        assert orchestrator._evaluate_condition(condition, output) is False

    def test_evaluate_condition_contains(self):
        """Test CONTAINS operator."""
        orchestrator = ChainOrchestratorService()
        
        condition = {"rules": [{"field": "message", "operator": "contains", "value": "error"}]}
        
        assert orchestrator._evaluate_condition(condition, {"message": "error occurred"}) is True
        assert orchestrator._evaluate_condition(condition, {"message": "success"}) is False

    def test_evaluate_condition_and_logic(self):
        """Test AND logic with multiple rules."""
        orchestrator = ChainOrchestratorService()
        
        condition = {
            "rules": [
                {"field": "status", "operator": "eq", "value": "active"},
                {"field": "count", "operator": "gt", "value": "5"}
            ],
            "logic": "AND"
        }
        
        # Both conditions met
        assert orchestrator._evaluate_condition(condition, {"status": "active", "count": 10}) is True
        
        # Only one condition met
        assert orchestrator._evaluate_condition(condition, {"status": "active", "count": 3}) is False

    def test_evaluate_condition_or_logic(self):
        """Test OR logic with multiple rules."""
        orchestrator = ChainOrchestratorService()
        
        condition = {
            "rules": [
                {"field": "status", "operator": "eq", "value": "active"},
                {"field": "status", "operator": "eq", "value": "pending"}
            ],
            "logic": "OR"
        }
        
        assert orchestrator._evaluate_condition(condition, {"status": "active"}) is True
        assert orchestrator._evaluate_condition(condition, {"status": "pending"}) is True
        assert orchestrator._evaluate_condition(condition, {"status": "inactive"}) is False

    def test_cycle_detection(self):
        """Test cycle detection algorithm."""
        orchestrator = ChainOrchestratorService()
        
        # Create cycle: A -> B -> C -> A
        nodes = [
            ChainNode(node_id="A"),
            ChainNode(node_id="B"),
            ChainNode(node_id="C")
        ]
        edges = [
            ChainEdge(source_node_id="A", target_node_id="B"),
            ChainEdge(source_node_id="B", target_node_id="C"),
            ChainEdge(source_node_id="C", target_node_id="A")
        ]
        
        result = orchestrator._check_for_cycles(nodes, edges)
        assert result['has_cycle'] is True
        assert len(result['cycle_path']) >= 3

    def test_no_cycle(self):
        """Test cycle detection with valid DAG."""
        orchestrator = ChainOrchestratorService()
        
        # Valid DAG: A -> B -> C
        nodes = [
            ChainNode(node_id="A"),
            ChainNode(node_id="B"),
            ChainNode(node_id="C")
        ]
        edges = [
            ChainEdge(source_node_id="A", target_node_id="B"),
            ChainEdge(source_node_id="B", target_node_id="C")
        ]
        
        result = orchestrator._check_for_cycles(nodes, edges)
        assert result['has_cycle'] is False
