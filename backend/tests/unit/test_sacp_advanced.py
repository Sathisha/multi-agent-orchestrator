import pytest
import json
import uuid
from uuid import uuid4
from unittest.mock import AsyncMock, patch, MagicMock

from shared.models.agent import Agent, AgentType, AgentStatus
from shared.models.chain import Chain, ChainNode, ChainEdge, ChainNodeType, ChainStatus
from shared.services.chain_orchestrator import ChainOrchestratorService

@pytest.mark.unit
@pytest.mark.asyncio
class TestSACPAdvanced:

    @pytest.fixture
    def orchestrator(self):
        return ChainOrchestratorService()

    @pytest.fixture
    async def sacp_agent(self, async_session):
        agent = Agent(
            id=uuid.uuid4(),
            name="SACP Advanced Agent",
            description="Test Agent for SACP Robustness",
            type=AgentType.CHATBOT,
            status=AgentStatus.ACTIVE,
            config={
                "use_standard_response_format": True,
                "model_name": "test-model",
                "llm_provider": "mock"
            },
            system_prompt="Base prompt."
        )
        async_session.add(agent)
        await async_session.commit()
        return agent

    @pytest.fixture
    async def sacp_chain(self, async_session, sacp_agent):
        chain = Chain(
            id=uuid.uuid4(),
            name="SACP Advanced Chain",
            status=ChainStatus.ACTIVE,
            execution_count=0
        )
        async_session.add(chain)
        
        node_start = ChainNode(chain_id=chain.id, node_id="start", node_type=ChainNodeType.START, label="Start")
        node_agent = ChainNode(chain_id=chain.id, node_id="agent1", node_type=ChainNodeType.AGENT, label="Agent 1", agent_id=sacp_agent.id)
        node_end = ChainNode(chain_id=chain.id, node_id="end", node_type=ChainNodeType.END, label="End")
        
        async_session.add_all([node_start, node_agent, node_end])
        
        edge1 = ChainEdge(chain_id=chain.id, edge_id=str(uuid.uuid4()), source_node_id="start", target_node_id="agent1")
        edge2 = ChainEdge(chain_id=chain.id, edge_id=str(uuid.uuid4()), source_node_id="agent1", target_node_id="end")
        
        async_session.add_all([edge1, edge2])
        await async_session.commit()
        return chain

    async def test_sacp_parsing_robustness_markdown(self, async_session, orchestrator, sacp_chain):
        """Test parsing when LLM wraps JSON in markdown blocks."""
        expected_json = {
            "thought": "Wrapped in markdown",
            "status": "success",
            "data": {"key": "val"},
            "message": "Hello"
        }
        raw_content = f"""Here is the JSON:
```json
{json.dumps(expected_json)}
```"""
        
        mock_response = MagicMock()
        mock_response.content = raw_content
        mock_response.model = "test-model"
        mock_response.usage = MagicMock(total_tokens=10)

        with patch("shared.services.llm_service.LLMService.generate_response", new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = mock_response
            
            execution = await orchestrator.execute_chain(
                async_session,
                sacp_chain.id,
                {"input": "Start"},
                execution_name="SACP Markdown Test"
            )
            
            assert execution.status == "completed"
            agent_result = execution.node_results.get("agent1", {})
            assert agent_result.get("output") == expected_json

    async def test_sacp_fallback_mechanism(self, async_session, orchestrator, sacp_chain):
        """Test fallback mechanism when JSON is completely invalid."""
        raw_content = "This is not JSON at all. I failed."
        
        mock_response = MagicMock()
        mock_response.content = raw_content
        mock_response.model = "test-model"
        mock_response.usage = MagicMock(total_tokens=10)

        with patch("shared.services.llm_service.LLMService.generate_response", new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = mock_response
            
            execution = await orchestrator.execute_chain(
                async_session,
                sacp_chain.id,
                {"input": "Start"},
                execution_name="SACP Fallback Test"
            )
            
            assert execution.status == "completed"
            agent_result = execution.node_results.get("agent1", {})
            output = agent_result.get("output", {})
            
            # Verify Fallback Structure
            assert output["status"] == "failure"
            assert output["thought"] == "Failed to parse JSON response" # Matching current implementation
            assert output["message"] == raw_content
            assert output["data"] == {}
