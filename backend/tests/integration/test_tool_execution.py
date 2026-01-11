"""
Integration tests for tool execution functionality.

Tests direct tool creation, validation, and execution via API.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.tool import Tool, ToolType, ToolStatus


# Sample calculator tool code
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

GREETING_TOOL_CODE = """
def execute(name: str) -> dict:
    '''Simple greeting tool for testing.'''
    return {
        'greeting': f'Hello, {name}! Welcome to the AI Agent Framework.'
    }
"""


@pytest.fixture
async def calculator_tool_data():
    """Sample calculator tool request data."""
    return {
        "name": "calculator",
        "description": "Performs basic mathematical operations: add, subtract, multiply, divide",
        "version": "1.0.0",
        "tool_type": "custom",
        "code": CALCULATOR_TOOL_CODE,
        "input_schema": {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": ["add", "subtract", "multiply", "divide"],
                    "description": "The mathematical operation to perform"
                },
                "a": {
                    "type": "number",
                    "description": "First operand"
                },
                "b": {
                    "type": "number",
                    "description": "Second operand"
                }
            },
            "required": ["operation", "a", "b"]
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "result": {"type": "number"}
            }
        },
        "category": "math",
        "tags": ["calculator", "math", "arithmetic"],
        "timeout_seconds": 30
    }


@pytest.fixture
async def greeting_tool_data():
    """Sample greeting tool request data."""
    return {
        "name": "greeter",
        "description": "Greets a user by name",
        "version": "1.0.0",
        "tool_type": "custom",
        "code": GREETING_TOOL_CODE,
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Name of the person to greet"
                }
            },
            "required": ["name"]
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "greeting": {"type": "string"}
            }
        },
        "category": "communication",
        "tags": ["greeting", "social"],
        "timeout_seconds": 10
    }


@pytest.mark.asyncio
class TestToolCreation:
    """Tests for tool creation via API."""
    
    async def test_create_calculator_tool(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        calculator_tool_data: dict
    ):
        """Test creating a calculator tool."""
        response = await async_client.post(
            "/api/v1/tools",
            json=calculator_tool_data,
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        
        assert data["name"] == "calculator"
        assert data["tool_type"] == "custom"
        assert data["status"] == "draft"
        assert "id" in data
        
        return data["id"]
    
    async def test_create_greeting_tool(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        greeting_tool_data: dict
    ):
        """Test creating a greeting tool."""
        response = await async_client.post(
            "/api/v1/tools",
            json=greeting_tool_data,
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        
        assert data["name"] == "greeter"
        assert "id" in data


@pytest.mark.asyncio
class TestToolExecution:
    """Tests for tool execution via API."""
    
    async def test_execute_calculator_addition(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        calculator_tool_data: dict
    ):
        """Test executing calculator tool for addition."""
        # First create the tool
        create_response = await async_client.post(
            "/api/v1/tools",
            json=calculator_tool_data,
            headers=auth_headers
        )
        assert create_response.status_code == 201
        tool_id = create_response.json()["id"]
        
        # Execute the tool
        execution_request = {
            "tool_id": tool_id,
            "inputs": {
                "operation": "add",
                "a": 15,
                "b": 27
            }
        }
        
        exec_response = await async_client.post(
            f"/api/v1/tools/{tool_id}/execute",
            json=execution_request,
            headers=auth_headers
        )
        
        assert exec_response.status_code == 200
        result = exec_response.json()
        
        assert result["status"] == "completed"
        assert result["outputs"]["result"] == 42
        assert result["outputs"]["operation"] == "add"
    
    async def test_execute_calculator_multiply(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        calculator_tool_data: dict
    ):
        """Test executing calculator tool for multiplication."""
        # Create tool
        create_response = await async_client.post(
            "/api/v1/tools",
            json=calculator_tool_data,
            headers=auth_headers
        )
        tool_id = create_response.json()["id"]
        
        # Execute
        exec_response = await async_client.post(
            f"/api/v1/tools/{tool_id}/execute",
            json={
                "tool_id": tool_id,
                "inputs": {
                    "operation": "multiply",
                    "a": 6,
                    "b": 7
                }
            },
            headers=auth_headers
        )
        
        assert exec_response.status_code == 200
        result = exec_response.json()
        assert result["outputs"]["result"] == 42
    
    async def test_execute_greeting_tool(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        greeting_tool_data: dict
    ):
        """Test executing greeting tool."""
        # Create tool
        create_response = await async_client.post(
            "/api/v1/tools",
            json=greeting_tool_data,
            headers=auth_headers
        )
        tool_id = create_response.json()["id"]
        
        # Execute
        exec_response = await async_client.post(
            f"/api/v1/tools/{tool_id}/execute",
            json={
                "tool_id": tool_id,
                "inputs": {
                    "name": "Alice"
                }
            },
            headers=auth_headers
        )
        
        assert exec_response.status_code == 200
        result = exec_response.json()
        assert "Hello, Alice" in result["outputs"]["greeting"]


@pytest.mark.asyncio
class TestToolValidation:
    """Tests for tool validation via API."""
    
    async def test_validate_calculator_tool(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        calculator_tool_data: dict
    ):
        """Test validating a calculator tool."""
        # Create tool
        create_response = await async_client.post(
            "/api/v1/tools",
            json=calculator_tool_data,
            headers=auth_headers
        )
        tool_id = create_response.json()["id"]
        
        # Validate
        validate_response = await async_client.post(
            f"/api/v1/tools/{tool_id}/validate",
            headers=auth_headers
        )
        
        assert validate_response.status_code == 200
        result = validate_response.json()
        
        assert result["is_valid"] is True
        assert len(result.get("errors", [])) == 0


@pytest.mark.asyncio
class TestToolDiscovery:
    """Tests for tool discovery via API."""
    
    async def test_list_tools(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        calculator_tool_data: dict
    ):
        """Test listing all tools."""
        # Create a tool first
        await async_client.post(
            "/api/v1/tools",
            json=calculator_tool_data,
            headers=auth_headers
        )
        
        # List tools
        list_response = await async_client.get(
            "/api/v1/tools",
            headers=auth_headers
        )
        
        assert list_response.status_code == 200
        tools = list_response.json()
        
        assert isinstance(tools, list)
        assert len(tools) > 0
        assert any(tool["name"] == "calculator" for tool in tools)
    
    async def test_discover_tools_endpoint(
        self,
        async_client: AsyncClient,
        auth_headers: dict
    ):
        """Test tools discovery endpoint."""
        response = await async_client.get(
            "/api/v1/tools/discover/",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "available_tools" in data
        assert "categories" in data
        assert "capabilities" in data
