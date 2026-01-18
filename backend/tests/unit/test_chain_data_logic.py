
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from shared.services.chain_orchestrator import ChainOrchestratorService
from shared.models.chain import ChainNode, ChainNodeType
from shared.models.agent import Agent

class TestChainDataLogic:
    def setup_method(self):
        self.orchestrator = ChainOrchestratorService()

    def test_resolve_value_direct(self):
        """Test resolving direct values."""
        context = {}
        assert self.orchestrator._resolve_value("test", context) == "test"
        assert self.orchestrator._resolve_value(123, context) == 123

    def test_resolve_value_template_success(self):
        """Test resolving template values {{node.field}}."""
        context = {
            "node_outputs": {
                "node1": {"output": "result", "content": "hello"}
            }
        }
        # {{node1.content}} -> "hello"
        val = self.orchestrator._resolve_value("{{node1.content}}", context)
        assert val == "hello"

    def test_resolve_value_template_missing_node(self):
        """Test resolving template with missing node."""
        context = {"node_outputs": {}}
        val = self.orchestrator._resolve_value("{{node1.content}}", context)
        assert val is None

    def test_resolve_value_template_missing_field(self):
        """Test resolving template with missing field."""
        context = {
            "node_outputs": {
                "node1": {"other": "value"}
            }
        }
        val = self.orchestrator._resolve_value("{{node1.content}}", context)
        assert val is None

    def test_prepare_node_input_no_map(self):
        """Test input preparation without input_map (pass-through)."""
        node = ChainNode(id="n2", node_id="node2", config={})
        context = {
            "input": {"original": "input"},
            "node_outputs": {
                "node1": {"content": "prev_output"}
            }
        }
        incoming_edges = {"node2": [MagicMock(source_node_id="node1")]}
        
        # Should aggregate or pass through
        # With 1 predecessor, it passes through the predecessor's output
        result = self.orchestrator._prepare_node_input(node, context, incoming_edges)
        assert result == {"content": "prev_output"}

    def test_prepare_node_input_with_map(self):
        """Test input preparation WITH input_map."""
        node = ChainNode(
            id="n2", 
            node_id="node2", 
            config={
                "input_map": {
                    "new_field": "{{node1.content}}",
                    "static_field": "static_value"
                }
            }
        )
        context = {
            "input": {"original": "input"},
            "node_outputs": {
                "node1": {"content": "dynamic_value"}
            }
        }
        # Even with predecessors, input_map should take precedence/merge
        incoming_edges = {"node2": [MagicMock(source_node_id="node1")]}
        
        result = self.orchestrator._prepare_node_input(node, context, incoming_edges)
        
        # Expect merged result (base input passed through + mapped fields)
        # Base input from 1 predecessor is {"content": "dynamic_value"}
        # Mapped fields: new_field="dynamic_value", static_field="static_value"
        assert result["content"] == "dynamic_value"
        assert result["new_field"] == "dynamic_value"
        assert result["static_field"] == "static_value"

    @pytest.mark.asyncio
    async def test_execute_agent_node_structured_output_injection(self):
        """Test that _execute_agent_node injects schema instructions."""
        # Mock Session
        mock_session = AsyncMock()
        # Mock Agent Query Result
        mock_agent = Agent(id="agent1", name="TestAgent", config={})
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_agent
        mock_session.execute.return_value = mock_result

        # Orchestrator
        orch = ChainOrchestratorService()
        
        # Patch AgentExecutorService to capture input_data
        # Must patch where it is DEFINED because it is imported locally in the method
        with patch('shared.services.agent_executor.AgentExecutorService') as MockExecutorCls:
            mock_executor = AsyncMock()
            mock_executor.execute_agent.return_value = MagicMock(output_data={"res": "ok"})
            MockExecutorCls.return_value = mock_executor
            
            # Node with output_schema
            node = ChainNode(
                node_id="node1",
                agent_id="agent1", 
                node_type=ChainNodeType.AGENT,
                config={
                    "output_schema": {"type": "object", "properties": {"foo": {"type": "string"}}}
                }
            )
            
            input_data = {"message": "user input"}
            context = {}
            
            await orch._execute_agent_node(mock_session, node, input_data, context)
            
            # Verify call args
            call_args = mock_executor.execute_agent.call_args
            assert call_args is not None
            _, kwargs = call_args
            passed_input = kwargs['input_data']
            
            # Verify injection
            assert "IMPORTANT: You MUST return your response in a valid JSON format" in passed_input['message']
            assert '"foo":' in passed_input['message']

