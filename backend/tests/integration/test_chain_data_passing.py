
import pytest
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.chain import Chain, ChainNode, ChainEdge, ChainNodeType, ChainStatus, ChainExecutionStatus
from shared.models.agent import Agent, AgentType, AgentStatus
from shared.services.chain_orchestrator import ChainOrchestratorService

@pytest.mark.integration
@pytest.mark.asyncio
class TestChainDataPassing:
    """Test data passing and traceability in chains."""

    @pytest.fixture
    def orchestrator(self):
        return ChainOrchestratorService()

    async def test_input_mapping(self, async_session, orchestrator):
        """Test Input Mapping: Node 2 Input uses Node 1 Output."""
        try:
            agent = Agent(
                name=f"Echo Agent {uuid4()}",
                description="Agent that echos input",
                type=AgentType.CHATBOT,
                status=AgentStatus.ACTIVE,
                config={
                    "name": "Echo Agent",
                    "model": "mock-model-v1",
                    "llm_provider": "mock",
                    "temperature": 0.0
                }
            )
            async_session.add(agent)
            await async_session.commit()
            await async_session.refresh(agent)
        except Exception as e:
            pytest.fail(f"Agent creation failed: {str(e)}")
        
        # Node 1: Produces some output
        # For testing, we might need to mock the actual agent execution or rely on the agent simply echoing.
        # Since we modified ChainOrchestrator to use AgentExecutor, and we are in integration test, 
        # let's assume AgentExecutor routes to a real or mock LLM.
        # If we use "mock" provider in config, AgentExecutor might fail if not handled, 
        # unless we mock LLMService.
        # But wait, shared/services/agent_executor.py attempts to import LLMService.
        # Checking agent_executor.py again (step 15):
        # try: from ..services.llm_service import LLMService ... except ImportError: ... Mock response
        
        # Let's hope the environment uses the real AgentExecutor.
        # To ensure deterministic output, we might want to manually set node_outputs in a mocked execution 
        # OR rely on a predictable LLM response (or mock the LLM service).
        # In `test_chain_execution_patterns.py`, it seems to run end-to-end.
        
        # Let's try to pass data and see.
        
        chain = Chain(name="Data Passing Test", status=ChainStatus.ACTIVE)
        async_session.add(chain)
        await async_session.flush()

        # Node 1
        node1 = ChainNode(
            chain_id=chain.id,
            node_id="node1",
            node_type=ChainNodeType.AGENT,
            agent_id=agent.id,
            label="Node 1",
            config={"input_map": {}} # No map, uses chain input
        )
        async_session.add(node1)
        
        # Node 2: Uses output from Node 1
        node2 = ChainNode(
            chain_id=chain.id,
            node_id="node2",
            node_type=ChainNodeType.AGENT,
            agent_id=agent.id, # Reusing same agent is fine
            label="Node 2",
            # Map 'previous_content' in input to 'content' field of node1 output (assuming agent output has 'content')
            config={"input_map": {"message": "{{node1.content}}"}} 
        )
        async_session.add(node2)
        
        # Edge 1 -> 2
        edge = ChainEdge(
            chain_id=chain.id,
            edge_id="e1",
            source_node_id="node1",
            target_node_id="node2"
        )
        async_session.add(edge)
        
        await async_session.commit()

        # Execute
        # Input to chain: {"message": "Hello World"}
        # Node 1 Input: {"message": "Hello World"} (Default)
        # Node 1 Output: Expected {"content": "Mock response", ...} (If using mock LLMService)
        # Node 2 Input: {"message": "Mock response"} (Mapped)
        
        # We need to ensure LLMService is mocked to return predictable data.
        # Or we can verify that whatever Node 1 produced was passed to Node 2.
        
        execution = await orchestrator.execute_chain(
            async_session,
            chain.id,
            input_data={"message": "Hello World"}
        )
        
        assert execution.status == ChainExecutionStatus.COMPLETED
        
        # Verify Node Results Traceability
        # node_results should contain 'input' and 'output'
        results = execution.node_results
        
        assert "node1" in results
        assert "node2" in results
        
        # Check traceability structure
        assert "input" in results["node1"]
        assert "output" in results["node1"]
        
        # Check Data Mapping
        node1_out = results["node1"]["output"]
        node2_in = results["node2"]["input"]
        
        # If mapping worked, node2_in['message'] should equal node1_out['content']
        # Note: 'content' is the standard field for LLM response content in this system (step 15, line 543)
        
        print(f"Node 1 Output: {node1_out}")
        print(f"Node 2 Input: {node2_in}")
        
        # Handling the case where output might be a string or dict
        val1 = node1_out.get('content') if isinstance(node1_out, dict) else str(node1_out)
        val2 = node2_in.get('message')
        
        assert val2 == val1
