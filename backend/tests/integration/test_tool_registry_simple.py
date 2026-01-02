"""
Simple test for Tool Registry and MCP Gateway models and basic functionality.

This test focuses on model validation and basic service functionality without
requiring database connections or external dependencies.
"""

import sys
import os
import asyncio
from datetime import datetime
from uuid import uuid4

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_tool_models_basic():
    """Test basic tool model functionality."""
    print("Testing Tool Models Basic Functionality...")
    
    try:
        from shared.models.tool import (
            ToolRequest, ToolResponse, ToolType, ToolStatus,
            MCPServerRequest, MCPServerResponse, MCPServerStatus,
            ToolExecutionRequest, ToolExecutionResponse, ToolDiscoveryResponse
        )
        
        # Test ToolRequest creation and validation
        tool_request = ToolRequest(
            name="test_calculator",
            display_name="Test Calculator",
            description="A simple calculator tool",
            tool_type=ToolType.CUSTOM,
            code='''def execute(inputs, context=None):
    a = inputs.get("a", 0)
    b = inputs.get("b", 0)
    operation = inputs.get("operation", "add")
    
    if operation == "add":
        result = a + b
    elif operation == "subtract":
        result = a - b
    elif operation == "multiply":
        result = a * b
    elif operation == "divide":
        result = a / b if b != 0 else "Error: Division by zero"
    else:
        result = "Error: Unknown operation"
    
    return {"result": result}''',
            entry_point="execute",
            input_schema={
                "type": "object",
                "properties": {
                    "a": {"type": "number"},
                    "b": {"type": "number"},
                    "operation": {"type": "string", "enum": ["add", "subtract", "multiply", "divide"]}
                },
                "required": ["a", "b", "operation"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "result": {"type": ["number", "string"]}
                }
            },
            timeout_seconds=10,
            max_retries=2
        )
        
        print(f"✓ ToolRequest created: {tool_request.name}")
        print(f"  - Type: {tool_request.tool_type}")
        print(f"  - Timeout: {tool_request.timeout_seconds}s")
        print(f"  - Max retries: {tool_request.max_retries}")
        
        # Test serialization
        tool_dict = tool_request.model_dump()
        assert "name" in tool_dict
        assert "tool_type" in tool_dict
        assert tool_dict["tool_type"] == "custom"
        assert tool_dict["timeout_seconds"] == 10
        print("✓ ToolRequest serialization works")
        
        # Test name validation
        try:
            invalid_tool = ToolRequest(
                name="invalid name with spaces!",
                display_name="Invalid Tool",
                description="This should fail validation",
                tool_type=ToolType.CUSTOM
            )
            print("❌ Name validation should have failed")
            return False
        except ValueError as e:
            print("✓ Name validation works correctly")
        
        return True
        
    except Exception as e:
        print(f"❌ Tool models test failed: {e}")
        return False


def test_mcp_server_models():
    """Test MCP server model functionality."""
    print("Testing MCP Server Models...")
    
    try:
        from shared.models.tool import MCPServerRequest, MCPServerResponse, MCPServerStatus
        
        # Test MCPServerRequest creation
        mcp_request = MCPServerRequest(
            name="test_weather_server",
            display_name="Test Weather Server",
            description="A test MCP server for weather data",
            url="https://api.weather.example.com",
            protocol="https",
            port=443,
            auth_type="api_key",
            auth_config={
                "api_key": "test_key_123",
                "key_name": "X-API-Key"
            },
            timeout_seconds=15,
            max_retries=5,
            retry_delay=3,
            health_check_interval=600,
            tags=["weather", "api", "external"],
            category="data_source",
            vendor="Weather Corp"
        )
        
        print(f"✓ MCPServerRequest created: {mcp_request.name}")
        print(f"  - URL: {mcp_request.url}")
        print(f"  - Protocol: {mcp_request.protocol}")
        print(f"  - Auth type: {mcp_request.auth_type}")
        print(f"  - Timeout: {mcp_request.timeout_seconds}s")
        print(f"  - Health check interval: {mcp_request.health_check_interval}s")
        
        # Test serialization
        mcp_dict = mcp_request.model_dump()
        assert "name" in mcp_dict
        assert "url" in mcp_dict
        assert "protocol" in mcp_dict
        assert mcp_dict["timeout_seconds"] == 15
        print("✓ MCPServerRequest serialization works")
        
        # Test URL validation
        try:
            invalid_server = MCPServerRequest(
                name="invalid_server",
                display_name="Invalid Server",
                description="This should fail URL validation",
                url="invalid-url-format",
                protocol="http"
            )
            print("❌ URL validation should have failed")
            return False
        except ValueError as e:
            print("✓ URL validation works correctly")
        
        return True
        
    except Exception as e:
        print(f"❌ MCP server models test failed: {e}")
        return False


def test_tool_execution_models():
    """Test tool execution models."""
    print("Testing Tool Execution Models...")
    
    try:
        from shared.models.tool import ToolExecutionRequest, ToolExecutionResponse
        
        tool_id = uuid4()
        
        # Test execution request
        exec_request = ToolExecutionRequest(
            tool_id=tool_id,
            inputs={
                "a": 10,
                "b": 5,
                "operation": "multiply"
            },
            context={
                "user_id": "test_user_123",
                "session_id": "session_456"
            },
            timeout_override=20
        )
        
        print(f"✓ ToolExecutionRequest created for tool: {exec_request.tool_id}")
        print(f"  - Inputs: {exec_request.inputs}")
        print(f"  - Context keys: {list(exec_request.context.keys())}")
        print(f"  - Timeout override: {exec_request.timeout_override}s")
        
        # Test execution response
        exec_response = ToolExecutionResponse(
            tool_id=tool_id,
            execution_id="exec_" + str(uuid4()),
            status="success",
            outputs={"result": 50},
            execution_time=125,  # milliseconds
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow()
        )
        
        print(f"✓ ToolExecutionResponse created: {exec_response.status}")
        print(f"  - Execution ID: {exec_response.execution_id}")
        print(f"  - Outputs: {exec_response.outputs}")
        print(f"  - Execution time: {exec_response.execution_time}ms")
        
        # Test error response
        error_response = ToolExecutionResponse(
            tool_id=tool_id,
            execution_id="exec_error_" + str(uuid4()),
            status="error",
            outputs={},
            error="Division by zero",
            execution_time=50,
            started_at=datetime.utcnow()
        )
        
        print(f"✓ Error ToolExecutionResponse created: {error_response.status}")
        print(f"  - Error: {error_response.error}")
        
        return True
        
    except Exception as e:
        print(f"❌ Tool execution models test failed: {e}")
        return False


def test_tool_discovery_models():
    """Test tool discovery models."""
    print("Testing Tool Discovery Models...")
    
    try:
        from shared.models.tool import ToolDiscoveryResponse, ToolResponse, MCPServerResponse
        
        # Create mock tool responses
        mock_tools = []
        mock_servers = []
        
        # Test discovery response
        discovery_response = ToolDiscoveryResponse(
            available_tools=mock_tools,
            mcp_servers=mock_servers,
            categories=["calculator", "data_processing", "weather", "utilities"],
            capabilities=["basic_math", "data_transformation", "api_calls", "file_processing"]
        )
        
        print(f"✓ ToolDiscoveryResponse created")
        print(f"  - Available tools: {len(discovery_response.available_tools)}")
        print(f"  - MCP servers: {len(discovery_response.mcp_servers)}")
        print(f"  - Categories: {discovery_response.categories}")
        print(f"  - Capabilities: {discovery_response.capabilities}")
        
        # Test serialization
        discovery_dict = discovery_response.model_dump()
        assert "available_tools" in discovery_dict
        assert "mcp_servers" in discovery_dict
        assert "categories" in discovery_dict
        assert "capabilities" in discovery_dict
        print("✓ ToolDiscoveryResponse serialization works")
        
        return True
        
    except Exception as e:
        print(f"❌ Tool discovery models test failed: {e}")
        return False


def test_enum_values():
    """Test enum values and their string representations."""
    print("Testing Enum Values...")
    
    try:
        from shared.models.tool import ToolType, ToolStatus, MCPServerStatus
        
        # Test ToolType enum
        assert ToolType.CUSTOM == "custom"
        assert ToolType.MCP_SERVER == "mcp_server"
        assert ToolType.BUILTIN == "builtin"
        print("✓ ToolType enum values correct")
        
        # Test ToolStatus enum
        assert ToolStatus.DRAFT == "draft"
        assert ToolStatus.ACTIVE == "active"
        assert ToolStatus.INACTIVE == "inactive"
        assert ToolStatus.DEPRECATED == "deprecated"
        assert ToolStatus.ERROR == "error"
        print("✓ ToolStatus enum values correct")
        
        # Test MCPServerStatus enum
        assert MCPServerStatus.DISCONNECTED == "disconnected"
        assert MCPServerStatus.CONNECTING == "connecting"
        assert MCPServerStatus.CONNECTED == "connected"
        assert MCPServerStatus.ERROR == "error"
        assert MCPServerStatus.AUTHENTICATION_FAILED == "authentication_failed"
        print("✓ MCPServerStatus enum values correct")
        
        return True
        
    except Exception as e:
        print(f"❌ Enum values test failed: {e}")
        return False


def test_model_field_validation():
    """Test model field validation rules."""
    print("Testing Model Field Validation...")
    
    try:
        from shared.models.tool import ToolRequest, MCPServerRequest
        
        # Test timeout validation
        try:
            ToolRequest(
                name="test_tool",
                display_name="Test Tool",
                description="Test",
                timeout_seconds=500  # Should fail (max 300)
            )
            print("❌ Timeout validation should have failed")
            return False
        except ValueError:
            print("✓ Timeout validation works (max 300 seconds)")
        
        # Test retry validation
        try:
            ToolRequest(
                name="test_tool",
                display_name="Test Tool", 
                description="Test",
                max_retries=15  # Should fail (max 10)
            )
            print("❌ Max retries validation should have failed")
            return False
        except ValueError:
            print("✓ Max retries validation works (max 10)")
        
        # Test port validation
        try:
            MCPServerRequest(
                name="test_server",
                display_name="Test Server",
                description="Test",
                url="https://example.com",
                protocol="https",
                port=70000  # Should fail (max 65535)
            )
            print("❌ Port validation should have failed")
            return False
        except ValueError:
            print("✓ Port validation works (max 65535)")
        
        return True
        
    except Exception as e:
        print(f"❌ Field validation test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("TOOL REGISTRY AND MCP GATEWAY SIMPLE TESTS")
    print("=" * 60)
    print()
    
    tests = [
        test_tool_models_basic,
        test_mcp_server_models,
        test_tool_execution_models,
        test_tool_discovery_models,
        test_enum_values,
        test_model_field_validation,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {e}")
            failed += 1
        print()
    
    print("=" * 60)
    if failed == 0:
        print(f"✅ ALL {passed} TESTS PASSED SUCCESSFULLY!")
        print()
        print("IMPLEMENTATION STATUS:")
        print("✅ Tool and MCP Server models are complete and working")
        print("✅ Request/Response models with validation are functional")
        print("✅ Execution and discovery models are implemented")
        print("✅ All enum values and field validation work correctly")
        print()
        print("NEXT STEPS:")
        print("- Database integration tests (requires DB setup)")
        print("- Service layer integration tests")
        print("- API endpoint tests")
        print("- Property-based testing for completeness")
    else:
        print(f"❌ {failed} TESTS FAILED, {passed} TESTS PASSED")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)