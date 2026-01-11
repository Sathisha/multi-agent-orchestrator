import pytest
import asyncio
import json
from httpx import AsyncClient
from uuid import uuid4

@pytest.mark.asyncio
async def test_agent_tool_usage_e2e(async_client: AsyncClient):
    """
    E2E test to verify that an agent can:
    1. Be created with a tool.
    2. Use the tool via LLM routing (Ollama).
    3. Summarize the result.
    """
    
    # 1. Create a Calculator Tool
    tool_name = f"calc_{uuid4().hex[:6]}"
    tool_payload = {
        "name": tool_name,
        "description": "A calculator for basic math. Use this for ANY math question.",
        "version": "1.0.0",
        "tool_type": "custom",
        "code": """
def execute(inputs, context=None):
    op = inputs.get("operation")
    a = float(inputs.get("a", 0))
    b = float(inputs.get("b", 0))
    if op == "add": return {"result": a + b}
    if op == "multiply": return {"result": a * b}
    return {"error": "unknown op"}
""",
        "input_schema": {
            "type": "object",
            "properties": {
                "operation": {"type": "string", "enum": ["add", "multiply"]},
                "a": {"type": "number"},
                "b": {"type": "number"}
            },
            "required": ["operation", "a", "b"]
        }
    }
    
    response = await async_client.post("/api/v1/tools", json=tool_payload)
    assert response.status_code == 201
    tool_id = response.json()["id"]
    
    # 2. Create an Agent with this Tool
    agent_name = f"agent_{uuid4().hex[:6]}"
    agent_payload = {
        "name": agent_name,
        "description": "Math assistant",
        "type": "conversational",
        "system_prompt": "You are a math expert. Always use the calculator tool.",
        "available_tools": [tool_name],
        "config": {
            "model_name": "llama3.2:latest",
            "llm_provider": "ollama",
            "temperature": 0
        }
    }
    
    response = await async_client.post("/api/v1/agents", json=agent_payload)
    assert response.status_code == 201
    agent_id = response.json()["id"]
    
    # NEW: Activate the Agent (it starts as DRAFT)
    response = await async_client.post(f"/api/v1/agents/{agent_id}/activate")
    assert response.status_code == 200
    
    # 3. Execute Agent with a Math Question
    # Note: We use 123 + 456 = 579
    execution_payload = {
        "input_data": {
            "message": "Calculate 123 + 456"
        },
        "timeout_seconds": 120
    }
    
    # Start execution using the agent-executor endpoint
    response = await async_client.post(f"/api/v1/agent-executor/{agent_id}/execute", json=execution_payload)
    assert response.status_code in [200, 201]
    
    execution_id = response.json().get("execution_id")
    assert execution_id is not None
    
    # 4. Poll for Completion
    status = "pending"
    data = {}
    for _ in range(60): # 120 seconds total max
        resp = await async_client.get(f"/api/v1/agent-executor/executions/{execution_id}/status")
        assert resp.status_code == 200
        data = resp.json()
        status = data["status"]
        if status in ["completed", "failed"]:
            break
        await asyncio.sleep(2)
            
    assert status == "completed", f"Execution failed or timed out: {data.get('error_message')}. Data: {data}"
    
    # 5. Verify Results
    output_content = data["output_data"]["content"]
    assert "579" in output_content
    print(f"\nSUCCESS: Agent responded with: {output_content}")

