
import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from shared.services.agent_executor import AgentExecutorService, AgentExecutionContext
from shared.models.agent import Agent, AgentStatus, AgentType

@pytest.mark.asyncio
async def test_agent_execution_with_rag():
    # Mock dependencies
    mock_session = AsyncMock()
    mock_agent = Agent(
        id=str(uuid.uuid4()),
        name="Test Agent",
        status=AgentStatus.ACTIVE,
        config={"llm_provider": "mock", "model_name": "mock-model"},
        system_prompt="Base prompt.",
        available_tools=[]
    )
    
    # Setup Executor
    mock_executor = AgentExecutorService(mock_session)
    mock_executor._get_agent = AsyncMock(return_value=mock_agent)
    mock_executor.llm_service = MagicMock()
    mock_executor.llm_service.generate_response = AsyncMock(return_value=MagicMock(content="Response", usage=None))
    mock_executor._update_execution_result = AsyncMock()
    mock_executor._cleanup_execution = MagicMock()
    
    # Mock Memory Service (since RAGService is initialized with it)
    mock_executor.memory_service = MagicMock()
    
    # User ID to test
    test_user_id = str(uuid.uuid4())
    
    # Context
    context = AgentExecutionContext(
        execution_id="exec-1",
        agent_id=mock_agent.id,
        input_data={"message": "Hello RAG"},
        config={},
        started_at=datetime.utcnow(),
        user_id=test_user_id
    )
    
    # Patch RAGService where it is defined (shared.services.rag_service)
    # The import in agent_executor is: from .rag_service import RAGService
    # ensuring we patch the class that gets imported.
    with patch("shared.services.rag_service.RAGService") as MockRAGService:
        mock_rag_instance = MockRAGService.return_value
        mock_rag_instance.query = AsyncMock(return_value=[
            {"content": "Secret Info 1", "metadata": {"source_name": "doc1"}},
            {"content": "Secret Info 2", "metadata": {"source_name": "doc2"}}
        ])
        
        # Execute
        await mock_executor._execute_agent_logic(context)
        
        # Verify RAG initialization
        # It's initialized with (session, memory_manager)
        # In _execute_agent_logic: rag_service = RAGService(self.session, self.memory_service)
        MockRAGService.assert_called_with(mock_executor.session, mock_executor.memory_service)
        
        # Verify Query
        mock_rag_instance.query.assert_called_once()
        call_args = mock_rag_instance.query.call_args
        
        assert call_args.kwargs['query_text'] == "Hello RAG"
        assert str(call_args.kwargs['owner_id']) == test_user_id
        assert str(call_args.kwargs['agent_id']) == mock_agent.id
        
        # Verify System Prompt Injection
        llm_call_args = mock_executor.llm_service.generate_response.call_args
        messages = llm_call_args[0][0] # First arg is messages list
        system_message = next(m for m in messages if m['role'] == 'system')
        
        print(f"System Prompt: {system_message['content']}")
        
        assert "Secret Info 1" in system_message['content']
        assert "Secret Info 2" in system_message['content']
        assert "RELEVANT KNOWLEDGE BASE CONTEXT" in system_message['content']

@pytest.mark.asyncio
async def test_agent_execution_without_user_id_skips_rag():
    # Mock dependencies
    mock_session = AsyncMock()
    mock_agent = Agent(
        id=str(uuid.uuid4()),
        name="Test Agent No RAG",
        status=AgentStatus.ACTIVE,
        config={"llm_provider": "mock"},
        system_prompt="Base prompt."
    )
    
    mock_executor = AgentExecutorService(mock_session)
    mock_executor._get_agent = AsyncMock(return_value=mock_agent)
    mock_executor.llm_service = MagicMock()
    mock_executor.llm_service.generate_response = AsyncMock(return_value=MagicMock(content="Response", usage=None))
    mock_executor._update_execution_result = AsyncMock()
    mock_executor._cleanup_execution = MagicMock()
    
    # Context WITHOUT user_id
    context = AgentExecutionContext(
        execution_id="exec-2",
        agent_id=mock_agent.id,
        input_data={"message": "Hello"},
        config={},
        started_at=datetime.utcnow()
        # user_id is None by default
    )
    
    with patch("shared.services.rag_service.RAGService") as MockRAGService:
        await mock_executor._execute_agent_logic(context)
        
        # Should NOT initialize or query RAG
        MockRAGService.assert_not_called()
        
