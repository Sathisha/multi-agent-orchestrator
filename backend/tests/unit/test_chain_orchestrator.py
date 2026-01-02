
import pytest
import uuid
from uuid import uuid4
from sqlalchemy import select
from shared.models.chain import Chain, ChainNode, ChainEdge, ChainNodeType, ChainStatus
from shared.services.chain_orchestrator import ChainOrchestratorService, ChainValidationError

@pytest.mark.unit
@pytest.mark.asyncio
class TestChainOrchestrator:

    @pytest.fixture
    def orchestrator(self):
        return ChainOrchestratorService()

    async def create_chain_structure(self, session, nodes_data, edges_data):
        chain = Chain(
            name=f"Test Chain {uuid4()}",
            description="Test Chain Description",
            status=ChainStatus.DRAFT
        )
        session.add(chain)
        await session.flush()

        for n_data in nodes_data:
            node = ChainNode(
                chain_id=chain.id,
                node_id=n_data["id"],
                node_type=n_data["type"],
                label=n_data["label"],
                agent_id=n_data.get("agent_id")
            )
            session.add(node)
        
        for e_data in edges_data:
            edge = ChainEdge(
                chain_id=chain.id,
                edge_id=e_data["id"],
                source_node_id=e_data["source"],
                target_node_id=e_data["target"]
            )
            session.add(edge)
        
        await session.commit()
        return chain.id

    async def test_validate_valid_chain(self, async_session, orchestrator):
        """Test validation of a valid chain."""
        nodes = [
            {"id": "start", "type": ChainNodeType.START, "label": "Start"},
            {"id": "agent1", "type": ChainNodeType.AGENT, "label": "Agent 1", "agent_id": uuid4()},
            {"id": "end", "type": ChainNodeType.END, "label": "End"}
        ]
        edges = [
            {"id": "e1", "source": "start", "target": "agent1"},
            {"id": "e2", "source": "agent1", "target": "end"}
        ]
        
        chain_id = await self.create_chain_structure(async_session, nodes, edges)
        
        # Mock agent check since we use random UUID for agent_id
        # We need to create a fake agent or mock the check.
        # Ideally, we should create a real agent in DB, but for unit test speed we might want to skip or mock.
        # But validate_chain checks DB for agent. So let's create a dummy agent.
        from shared.models.agent import Agent, AgentType, AgentStatus
        
        # We need to update the agent_id to a real one
        real_agent = Agent(
            name="Test Agent",
            description="Test Agent",
            type=AgentType.CHATBOT,
            status=AgentStatus.ACTIVE,
            template_id="chatbot-basic"
        )
        async_session.add(real_agent)
        await async_session.flush()
        
        # Update node with real agent id
        stmt = select(ChainNode).where(ChainNode.chain_id == chain_id, ChainNode.node_id == "agent1")
        result = await async_session.execute(stmt)
        node = result.scalar_one()
        node.agent_id = real_agent.id
        await async_session.commit()

        validation = await orchestrator.validate_chain(async_session, chain_id)
        
        assert validation.is_valid is True
        assert len(validation.errors) == 0

    async def test_validate_cyclic_chain(self, async_session, orchestrator):
        """Test validation detects cycles."""
        nodes = [
            {"id": "start", "type": ChainNodeType.START, "label": "Start"},
            {"id": "node1", "type": ChainNodeType.AGENT, "label": "Node 1", "agent_id": uuid4()},
            {"id": "node2", "type": ChainNodeType.AGENT, "label": "Node 2", "agent_id": uuid4()}
        ]
        edges = [
            {"id": "e1", "source": "start", "target": "node1"},
            {"id": "e2", "source": "node1", "target": "node2"},
            {"id": "e3", "source": "node2", "target": "node1"}  # Cycle
        ]
        
        chain_id = await self.create_chain_structure(async_session, nodes, edges)
        
        validation = await orchestrator.validate_chain(async_session, chain_id)
        
        assert validation.is_valid is False
        assert any("cyclic" in e.lower() for e in validation.errors)

    async def test_validate_disconnected_nodes(self, async_session, orchestrator):
        """Test validation warns about disconnected nodes."""
        nodes = [
            {"id": "start", "type": ChainNodeType.START, "label": "Start"},
            {"id": "node1", "type": ChainNodeType.AGENT, "label": "Node 1", "agent_id": uuid4()},
            {"id": "orphan", "type": ChainNodeType.AGENT, "label": "Orphan", "agent_id": uuid4()}
        ]
        edges = [
            {"id": "e1", "source": "start", "target": "node1"}
        ]
        
        chain_id = await self.create_chain_structure(async_session, nodes, edges)
        
        validation = await orchestrator.validate_chain(async_session, chain_id)
        
        # It might still be valid but have warnings
        # The service implementation returns is_valid based on errors only, warnings don't invalidate.
        # But let's check warnings.
        assert any("disconnected" in w.lower() for w in validation.warnings)

    async def test_check_for_cycles_logic(self, orchestrator):
        """Test the internal cycle detection logic directly."""
        # A -> B -> C -> A
        nodes = [
            ChainNode(node_id="A"), ChainNode(node_id="B"), ChainNode(node_id="C")
        ]
        edges = [
            ChainEdge(source_node_id="A", target_node_id="B"),
            ChainEdge(source_node_id="B", target_node_id="C"),
            ChainEdge(source_node_id="C", target_node_id="A")
        ]
        
        result = orchestrator._check_for_cycles(nodes, edges)
        assert result['has_cycle'] is True
        assert len(result['cycle_path']) > 0

        # A -> B -> C (No cycle)
        edges_no_cycle = [
            ChainEdge(source_node_id="A", target_node_id="B"),
            ChainEdge(source_node_id="B", target_node_id="C")
        ]
        result = orchestrator._check_for_cycles(nodes, edges_no_cycle)
        assert result['has_cycle'] is False
