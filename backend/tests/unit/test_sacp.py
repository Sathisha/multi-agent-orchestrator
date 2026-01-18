import pytest
import json
import uuid
from uuid import uuid4
from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock

from shared.models.agent import Agent, AgentType, AgentStatus
from shared.models.chain import Chain, ChainNode, ChainEdge, ChainNodeType, ChainStatus
from shared.services.chain_orchestrator import ChainOrchestratorService
from shared.services.agent_executor import AgentExecutorService

@pytest.mark.unit
@pytest.mark.asyncio
class TestStandardAgentCommunicationProtocol:

    @pytest.fixture
    def orchestrator(self):
        return ChainOrchestratorService()

    async def test_sacp_execution_and_parsing(self, async_session, orchestrator):
        # 1. Create Agent with SACP enabled
        agent = Agent(
            id=uuid.uuid4(),
            name="SACP Agent",
            description="Test Agent",
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
        
        # 2. Create Chain
        chain = Chain(
            id=uuid.uuid4(),
            name="SACP Chain",
            status=ChainStatus.ACTIVE,
            execution_count=0
        )
        async_session.add(chain)
        
        node_start = ChainNode(
            chain_id=chain.id,
            node_id="start",
            node_type=ChainNodeType.START,
            label="Start"
        )
        node_agent = ChainNode(
            chain_id=chain.id,
            node_id="agent1",
            node_type=ChainNodeType.AGENT,
            label="Agent 1",
            agent_id=agent.id,
            config={}
        )
        node_end = ChainNode(
            chain_id=chain.id,
            node_id="end",
            node_type=ChainNodeType.END,
            label="End"
        )
        async_session.add_all([node_start, node_agent, node_end])
        
        edge1 = ChainEdge(
            chain_id=chain.id,
            edge_id=str(uuid.uuid4()),
            source_node_id="start",
            target_node_id="agent1"
        )
        edge2 = ChainEdge(
            chain_id=chain.id,
            edge_id=str(uuid.uuid4()),
            source_node_id="agent1",
            target_node_id="end"
        )
        async_session.add_all([edge1, edge2])
        await async_session.commit()

        # 3. Mock LLM Response
        expected_json = {
            "thought": "Testing SACP",
            "status": "success",
            "data": {"foo": "bar", "nested": {"val": 123}},
            "message": "Hello World"
        }
        
        mock_response = MagicMock()
        mock_response.content = json.dumps(expected_json)
        mock_response.model = "test-model"
        mock_response.usage = MagicMock(total_tokens=10)

        # Patch LLMService.generate_response
        # We need to match where AgentExecutorService imports LLMService from
        # In shared/services/agent_executor.py it is: from ..services.llm_service import LLMService
        with patch("shared.services.llm_service.LLMService.generate_response", new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = mock_response
            
            # Execute
            execution = await orchestrator.execute_chain(
                async_session,
                chain.id,
                {"input": "Start"},
                execution_name="SACP Test"
            )
            
            # 4. Assertions
            assert execution.status == "completed"
            
            # Check node results
            agent_result = execution.node_results.get("agent1", {})
            assert agent_result.get("output") == expected_json
            
            # Check data.nested.val access
            assert agent_result["output"]["data"]["nested"]["val"] == 123

            # Verify prompt injection
            call_args = mock_generate.call_args
            assert call_args is not None
            messages = call_args[0][0] # First arg is messages
            system_message = next(m for m in messages if m["role"] == "system")
            assert "SYSTEM PROTOCOL: RESPONSE FORMAT INSTRUCTIONS" in system_message["content"]
            assert "Base prompt." in system_message["content"]

    async def test_condition_nested_access(self, async_session, orchestrator):
        # 1. Reuse/Create Agent
        agent = Agent(
            id=uuid.uuid4(),
            name="SACP Agent 2",
            status=AgentStatus.ACTIVE,
            config={"use_standard_response_format": True},
            system_prompt="Prompt"
        )
        async_session.add(agent)
        
        chain = Chain(id=uuid.uuid4(), name="Condition Chain", status=ChainStatus.ACTIVE, execution_count=0)
        async_session.add(chain)
        
        # Start -> Agent -> End
        node_start = ChainNode(chain_id=chain.id, node_id="start", node_type=ChainNodeType.START, label="S")
        node_agent = ChainNode(chain_id=chain.id, node_id="agent1", node_type=ChainNodeType.AGENT, label="A", agent_id=agent.id)
        node_end = ChainNode(chain_id=chain.id, node_id="end", node_type=ChainNodeType.END, label="E")
        async_session.add_all([node_start, node_agent, node_end])
        
        edge1 = ChainEdge(
            chain_id=chain.id, 
            edge_id=str(uuid.uuid4()),
            source_node_id="start", 
            target_node_id="agent1"
        )
        
        # Edge with condition: data.score > 0.5
        edge2 = ChainEdge(
            chain_id=chain.id, 
            edge_id=str(uuid.uuid4()),
            source_node_id="agent1", 
            target_node_id="end",
            condition={
                "rules": [
                    {
                        "field": "data.score",
                        "operator": "gt",
                        "value": 0.5
                    }
                ]
            }
        )
        async_session.add_all([edge1, edge2])
        await async_session.commit()
        
        # Mock Response with score 0.9
        expected_json = {
            "thought": "High score",
            "status": "success",
            "data": {"score": 0.9},
            "message": "Win"
        }
        
        mock_response = MagicMock()
        mock_response.content = json.dumps(expected_json)
        mock_response.model = "test-model"
        mock_response.usage = MagicMock(total_tokens=10)
        
        with patch("shared.services.llm_service.LLMService.generate_response", new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = mock_response
            
            execution = await orchestrator.execute_chain(
                async_session,
                chain.id,
                {"input": "go"}
            )
            
            assert execution.status == "completed"
            assert "end" in execution.completed_nodes
            
            # Verify edge was taken
            active_edges = execution.active_edges
            assert edge2.edge_id in active_edges
