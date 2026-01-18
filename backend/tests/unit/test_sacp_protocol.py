
import pytest
import json
from unittest.mock import MagicMock, patch, AsyncMock
from uuid import uuid4
from shared.services.chain_orchestrator import ChainOrchestratorService, ChainValidationError, ChainExecutionError
from shared.models.agent import Agent, AgentType, AgentStatus
from shared.models.chain import ChainNode, ChainNodeType
from shared.services.agent_executor import AgentExecutorService, AgentExecutionResult, ExecutionStatus, SACP_INSTRUCTION

@pytest.mark.unit
@pytest.mark.asyncio
class TestSACPProtocol:

    @pytest.fixture
    def orchestrator(self):
        return ChainOrchestratorService()

    async def test_sacp_response_parsing_success(self, async_session, orchestrator):
        """Test that valid JSON response is parsed correctly when SACP is enabled."""
        # Setup Agent
        agent_id = uuid4()
        agent = Agent(
            id=agent_id,
            name="SACP Agent",
            type=AgentType.CHATBOT,
            status=AgentStatus.ACTIVE,
            config={"use_standard_protocol": True}
        )
        async_session.add(agent)
        await async_session.commit()

        # Setup Node
        node = ChainNode(
            node_id="agent_node",
            node_type=ChainNodeType.AGENT,
            agent_id=agent_id
        )

        # Mock AgentExecutor response
        mock_response_content = json.dumps({
            "thought": "Thinking process...",
            "status": "success",
            "data": {"result": 42},
            "message": "The answer is 42"
        })
        
        mock_executor_result = AgentExecutionResult(
            execution_id="exec-123",
            status=ExecutionStatus.COMPLETED,
            output_data={"content": mock_response_content}
        )

        # Patch AgentExecutorService.execute_agent
        with patch("shared.services.agent_executor.AgentExecutorService.execute_agent", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = mock_executor_result
            
            # Execute Node
            result = await orchestrator._execute_agent_node(async_session, node, {"input": "test"}, {})
            
            # Assertions
            assert isinstance(result, dict)
            assert result["status"] == "success"
            assert result["data"]["result"] == 42
            assert result["thought"] == "Thinking process..."

    async def test_sacp_response_parsing_markdown_block(self, async_session, orchestrator):
        """Test parsing when JSON is inside markdown block."""
        # Setup Agent
        agent_id = uuid4()
        agent = Agent(
            id=agent_id,
            name="SACP Agent Markdown",
            type=AgentType.CHATBOT,
            status=AgentStatus.ACTIVE,
            config={"use_standard_protocol": True}
        )
        async_session.add(agent)
        await async_session.commit()

        node = ChainNode(node_id="agent_node", node_type=ChainNodeType.AGENT, agent_id=agent_id)

        # Mock Response
        json_content = json.dumps({
            "thought": "I will use markdown.",
            "status": "success",
            "data": {"key": "val"},
            "message": "Here is json"
        })
        content = f"Here is the result:\n```json\n{json_content}\n```"
        
        mock_executor_result = AgentExecutionResult(
            execution_id="exec-123",
            status=ExecutionStatus.COMPLETED,
            output_data={"content": content}
        )

        with patch("shared.services.agent_executor.AgentExecutorService.execute_agent", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = mock_executor_result
            result = await orchestrator._execute_agent_node(async_session, node, {}, {})
            
            assert result["status"] == "success"
            assert result["data"]["key"] == "val"

    async def test_sacp_response_parsing_fallback(self, async_session, orchestrator):
        """Test fallback mechanism when JSON is invalid."""
        # Setup Agent
        agent_id = uuid4()
        agent = Agent(
            id=agent_id,
            name="SACP Agent Fail",
            type=AgentType.CHATBOT,
            status=AgentStatus.ACTIVE,
            config={"use_standard_protocol": True}
        )
        async_session.add(agent)
        await async_session.commit()

        node = ChainNode(node_id="agent_node", node_type=ChainNodeType.AGENT, agent_id=agent_id)

        # Mock Invalid Response
        raw_content = "I am not returning JSON today."
        
        mock_executor_result = AgentExecutionResult(
            execution_id="exec-123",
            status=ExecutionStatus.COMPLETED,
            output_data={"content": raw_content}
        )

        with patch("shared.services.agent_executor.AgentExecutorService.execute_agent", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = mock_executor_result
            result = await orchestrator._execute_agent_node(async_session, node, {}, {})
            
            assert result["status"] == "failure"
            assert result["data"]["raw_output"] == raw_content
            assert "System Note" in result["thought"]

    async def test_sacp_prompt_injection(self, async_session):
        """Test that SACP instruction is injected into the prompt."""
        # This tests AgentExecutorService logic
        executor = AgentExecutorService(async_session)
        
        agent_id = uuid4()
        agent = Agent(
            id=agent_id,
            name="SACP Agent Prompt",
            type=AgentType.CHATBOT,
            status=AgentStatus.ACTIVE,
            config={"use_standard_protocol": True},
            system_prompt="Base prompt."
        )
        async_session.add(agent)
        await async_session.commit()
        
        # We need to spy on llm_service.generate_response
        with patch.object(executor.llm_service, 'generate_response', new_callable=AsyncMock) as mock_generate:
            # Mock return to avoid failure
            mock_generate.return_value = MagicMock(content="{}", usage=MagicMock(total_tokens=10))
            
            await executor._execute_agent_logic(MagicMock(
                execution_id="test",
                agent_id=str(agent_id),
                input_data={"message": "hi"},
                config={"use_standard_protocol": True}, # Context config usually overrides or matches agent
                session_id=None,
                started_at=None,
                timeout_seconds=30
            ))
            
            # Check call args
            call_args = mock_generate.call_args
            # messages is the first arg
            messages = call_args[0][0]
            system_msg = messages[0]["content"]
            
            assert "Base prompt." in system_msg
            assert "RESPONSE FORMAT INSTRUCTIONS" in system_msg
            assert "valid JSON format" in system_msg

