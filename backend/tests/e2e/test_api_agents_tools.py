import pytest
from httpx import AsyncClient
from uuid import uuid4

@pytest.mark.asyncio
async def test_agent_tool_lifecycle(async_client: AsyncClient):
    # 1. Create a Custom Tool (Calculator)
    tool_payload = {
        "name": f"calculator_{uuid4().hex[:8]}",
        "description": "A simple calculator tool",
        "version": "1.0.0",
        "tool_type": "custom",
        "code": """
def execute(inputs, context=None):
    op = inputs.get("operation")
    a = inputs.get("a")
    b = inputs.get("b")
    
    if op == "add":
        return {"result": a + b}
    elif op == "subtract":
        return {"result": a - b}
    elif op == "multiply":
        return {"result": a * b}
    elif op == "divide":
        return {"result": a / b}
    else:
        return {"error": "Unknown operation"}
""",
        "input_schema": {
            "type": "object",
            "properties": {
                "operation": {"type": "string", "enum": ["add", "subtract", "multiply", "divide"]},
                "a": {"type": "number"},
                "b": {"type": "number"}
            },
            "required": ["operation", "a", "b"]
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "result": {"type": "number"}
            }
        },
        "tags": ["math", "test"]
    }

    response = await async_client.post("/api/v1/tools", json=tool_payload)
    assert response.status_code == 201
    tool_data = response.json()
    tool_id = tool_data["id"]
    assert tool_data["name"] == tool_payload["name"]
    assert tool_data["status"] == "draft" # Default status after creation

    # 2. Validate the Tool (Validation happens automatically on create/update if code changes in some logic, 
    # but let's check validation endpoint too or just use it as is if status allows)
    # The service says: if tool.code: validation_result = await self._validate_tool_code(tool)
    # So it should be validated. But status might be DRAFT.
    # To execute, we might need it to be ACTIVE? The service code said:
    # # Allow executing drafts for testing?
    # # if tool.status != ToolStatus.ACTIVE:
    # #     raise ToolExecutionError(f"Tool is not active (status: {tool.status})")
    # It seems commented out in the service I read, so DRAFT is fine.

    # 3. Execute Tool Directly
    execution_payload = {
        "tool_id": tool_id,
        "inputs": {
            "operation": "add",
            "a": 5,
            "b": 3
        }
    }
    
    response = await async_client.post(f"/api/v1/tools/{tool_id}/execute", json=execution_payload)
    assert response.status_code == 200
    exec_data = response.json()
    assert exec_data["status"] == "success"
    assert exec_data["outputs"]["result"] == 8

    # 4. Create an Agent using this Tool
    agent_payload = {
        "name": f"math_agent_{uuid4().hex[:8]}",
        "description": "Agent good at math",
        "type": "conversational",
        "system_prompt": "You are a helpful math assistant. Use the calculator tool for calculations.",
        "available_tools": [tool_data["name"]], # Agent references tools by name usually? Or ID? 
        # API says available_tools: Optional[List[str]]. 
        # Typically these are tool names or keys. Let's assume names for now based on common patterns.
        "llm_config": {
            "provider": "openai",
            "model": "gpt-3.5-turbo",
            "temperature": 0
        }
    }

    response = await async_client.post("/api/v1/agents", json=agent_payload)
    assert response.status_code == 201
    agent_data = response.json()
    agent_id = agent_data["id"]
    assert agent_data["name"] == agent_payload["name"]

    # 5. Execute Agent (Start Execution)
    exec_req = {
        "input_data": {
            "message": "What is 5 + 3?"
        },
        "session_id": "test-session-1"
    }
    
    # Mock LLM service to return a successful response instead of failing due to missing keys
    with patch("shared.services.llm_service.LLMService.generate_response") as mock_gen:
        from shared.models.llm import LLMResponse
        mock_gen.return_value = LLMResponse(content="The result of 5 + 3 is 8.", model="gpt-3.5-turbo")
        
        response = await async_client.post(f"/api/v1/agents/{agent_id}/execute", json=exec_req)
        assert response.status_code == 200
        execution_data = response.json()
        assert execution_data["agent_id"] == agent_id
        assert execution_data["status"] == "completed"
        assert "8" in execution_data["message"]
        print(f"Agent Execution Success: {execution_data.get('message')}")

