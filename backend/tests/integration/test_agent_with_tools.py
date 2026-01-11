"""
Integration tests for agents using tools.

Tests the complete flow: user input -> tool selection -> tool execution -> final response.
"""

import pytest
from httpx import AsyncClient


# Import the calculator tool code from test_tool_execution
CALCULATOR_TOOL_CODE = """
def execute(operation: str, a: float, b: float) -> dict:
    '''Simple calculator tool for testing.'''
    operations = {
        'add': lambda x, y: x + y,
        'subtract': lambda x, y: x - y,
        'multiply': lambda x, y: x * y,
        'divide': lambda x, y: x / y if y != 0 else None
    }
    
    if operation not in operations:
        return {'error': f'Unknown operation: {operation}'}
    
    result = operations[operation](a, b)
    
    if result is None:
        return {'error': 'Division by zero'}
    
    return {
        'operation': operation,
        'a': a,
        'b': b,
        'result': result
    }
"""


@pytest.fixture
async def calculator_tool_id(async_client: AsyncClient, auth_headers: dict):
    """Create a calculator tool and return its ID."""
    tool_data = {
        "name": "calculator",
        "description": "Performs basic mathematical operations: add, subtract, multiply, divide",
        "version": "1.0.0",
        "tool_type": "custom",
        "code": CALCULATOR_TOOL_CODE,
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
            "properties": {"result": {"type": "number"}}
        },
        "category": "math",
        "tags": ["calculator", "math"],
        "timeout_seconds": 30
    }
    
    response = await async_client.post(
        "/api/v1/tools",
        json=tool_data,
        headers=auth_headers
    )
    
    assert response.status_code == 201
    return response.json()["id"]


@pytest.fixture
async def math_agent_id(async_client: AsyncClient, auth_headers: dict, calculator_tool_id: str):
    """Create an agent configured with calculator tool."""
    agent_data = {
        "name": "Math Assistant",
        "description": "An agent that can perform mathematical calculations",
        "type": "task",
        "status": "active",
        "system_prompt": "You are a helpful math assistant. When the user asks for calculations, use the calculator tool to compute the result accurately.",
        "config": {
            "model_name": "tinyllama",
            "llm_provider": "ollama",
            "temperature": 0.3,
            "max_tokens": 500,
            "memory_enabled": False
        },
        "available_tools": [calculator_tool_id],
        "tags": ["math", "calculator"]
    }
    
    response = await async_client.post(
        "/api/v1/agents",
        json=agent_data,
        headers=auth_headers
    )
    
    assert response.status_code == 201
    return response.json()["id"]


@pytest.mark.asyncio
class TestAgentWithTools:
    """Tests for agents using tools."""
    
    async def test_agent_uses_calculator_for_addition(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        math_agent_id: str
    ):
        """Test that agent uses calculator tool when asked to add numbers."""
        # Execute agent with a math question
        execution_data = {
            "input_data": {
                "message": "What is 15 plus 27?"
            },
            "timeout_seconds": 60
        }
        
        # Start execution
        exec_response = await async_client.post(
            f"/api/v1/agents/{math_agent_id}/execute",
            json=execution_data,
            headers=auth_headers
        )
        
        assert exec_response.status_code in [200, 201]
        execution_id = exec_response.json().get("execution_id") or exec_response.json().get("id")
        
        # Poll for completion (with timeout)
        import asyncio
        for _ in range(30):  # 30 seconds max
            status_response = await async_client.get(
                f"/api/v1/agent-executions/{execution_id}",
                headers=auth_headers
            )
            
            if status_response.status_code == 200:
                status_data = status_response.json()
                if status_data["status"] in ["completed", "failed"]:
                    break
            
            await asyncio.sleep(1)
        
        # Check final result
        assert status_data["status"] == "completed"
        output = status_data.get("output_data", {})
        
        # The output should contain the result 42
        output_content = str(output.get("content", ""))
        assert "42" in output_content or "forty-two" in output_content.lower()
    
    async def test_agent_uses_calculator_for_multiplication(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        math_agent_id: str
    ):
        """Test that agent uses calculator tool for multiplication."""
        execution_data = {
            "input_data": {
                "message": "Calculate 8 times 9"
            },
            "timeout_seconds": 60
        }
        
        exec_response = await async_client.post(
            f"/api/v1/agents/{math_agent_id}/execute",
            json=execution_data,
            headers=auth_headers
        )
        
        assert exec_response.status_code in [200, 201]
        execution_id = exec_response.json().get("execution_id") or exec_response.json().get("id")
        
        # Poll for completion
        import asyncio
        for _ in range(30):
            status_response = await async_client.get(
                f"/api/v1/agent-executions/{execution_id}",
                headers=auth_headers
            )
            
            if status_response.status_code == 200:
                status_data = status_response.json()
                if status_data["status"] in ["completed", "failed"]:
                    break
            
            await asyncio.sleep(1)
        
        assert status_data["status"] == "completed"
        output_content = str(status_data.get("output_data", {}).get("content", ""))
        assert "72" in output_content
    
    async def test_agent_without_tools_still_works(
        self,
        async_client: AsyncClient,
        auth_headers: dict
    ):
        """Test that agent without tools can still respond normally."""
        # Create agent without tools
        agent_data = {
            "name": "Simple Assistant",
            "description": "A simple agent without tools",
            "type": "conversational",
            "status": "active",
            "system_prompt": "You are a helpful assistant.",
            "config": {
                "model_name": "tinyllama",
                "llm_provider": "ollama",
                "temperature": 0.7,
                "max_tokens": 200
            },
            "available_tools": []
        }
        
        agent_response = await async_client.post(
            "/api/v1/agents",
            json=agent_data,
            headers=auth_headers
        )
        agent_id = agent_response.json()["id"]
        
        # Execute
        exec_response = await async_client.post(
            f"/api/v1/agents/{agent_id}/execute",
            json={"input_data": {"message": "Hello!"}},
            headers=auth_headers
        )
        
        assert exec_response.status_code in [200, 201]


@pytest.mark.asyncio
class TestMultipleTools:
    """Tests for agents with multiple tools."""
    
    async def test_agent_selects_correct_tool(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        calculator_tool_id: str
    ):
        """Test that agent selects the appropriate tool based on input."""
        # Create a greeting tool
        greeting_tool_data = {
            "name": "greeter",
            "description": "Greets a user by name",
            "version": "1.0.0",
            "tool_type": "custom",
            "code": """
def execute(name: str) -> dict:
    return {'greeting': f'Hello, {name}!'}
""",
            "input_schema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"}
                },
                "required": ["name"]
            },
            "tags": ["greeting"]
        }
        
        greeter_response = await async_client.post(
            "/api/v1/tools",
            json=greeting_tool_data,
            headers=auth_headers
        )
        greeter_tool_id = greeter_response.json()["id"]
        
        # Create agent with both tools
        agent_data = {
            "name": "Multi-Tool Assistant",
            "description": "Agent with multiple tools",
            "type": "task",
            "status": "active",
            "system_prompt": "You are a helpful assistant with access to calculation and greeting tools.",
            "config": {
                "model_name": "tinyllama",
                "llm_provider": "ollama",
                "temperature": 0.3,
                "max_tokens": 300
            },
            "available_tools": [calculator_tool_id, greeter_tool_id]
        }
        
        agent_response = await async_client.post(
            "/api/v1/agents",
            json=agent_data,
            headers=auth_headers
        )
        agent_id = agent_response.json()["id"]
        
        # Test with calculation request - should use calculator
        calc_response = await async_client.post(
            f"/api/v1/agents/{agent_id}/execute",
            json={"input_data": {"message": "What is 5 plus 3?"}},
            headers=auth_headers
        )
        
        assert calc_response.status_code in [200, 201]
        # The detailed verification would require polling like above
