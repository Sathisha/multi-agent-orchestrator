"""
Standalone test for Tool Registry and MCP Gateway functionality.

This test verifies basic functionality without requiring database or external dependencies.
"""

import sys
import os
import asyncio
from datetime import datetime
from uuid import uuid4

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_tool_models_import():
    """Test that tool models can be imported successfully."""
    print("Testing Tool Models Import...")
    
    try:
        from shared.models.tool import (
            ToolRequest, ToolResponse, ToolType, ToolStatus,
            MCPServerRequest, MCPServerResponse, MCPServerStatus,
            ToolExecutionRequest, ToolExecutionResponse, ToolDiscoveryResponse
        )
        print("✓ All tool models imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False


def test_tool_request_validation():
    """Test tool request validation."""
    print("Testing Tool Request Validation...")
    
    try:
        from shared.models.tool import ToolRequest, ToolType
        
        # Test valid tool request
        tool_request = ToolRequest(
            name="test_tool",
            display_name="Test Tool",
            description="A test tool for validation",
            tool_type=ToolType.CUSTOM,
            code='''def execute(inputs, context=None):
    return {"result": "Hello, " + inputs.get("name", "World")}''',
            entry_point="execute",
            input_schema={
                "type": "object",
                "properties": {
                    "name": {"type": "string"}
                }
            },
            output_schema={
                "type": "object",
                "properties": {
                    "result": {"type": "string"}
                }
            }
        )
        
        print(f"✓ Valid ToolRequest created: {tool_request.name}")
        
        # Test tool request serialization
        tool_dict = tool_request.model_dump()
        assert "name" in tool_dict
        assert "tool_type" in tool_dict
        assert tool_dict["tool_type"] == "custom"
        print("✓ ToolRequest serialization works")
        
        return True
        
    except Exception as e:
        print(f"❌ Tool request validation failed: {e}")
        return False


def test_mcp_server_request_validation():
    """Test MCP server request validation."""
    print("Testing MCP Server Request Validation...")
    
    try:
        from shared.models.tool import MCPServerRequest
        
        # Test valid MCP server request
        mcp_request = MCPServerRequest(
            name="test_mcp_server",
            display_name="Test MCP Server",
            description="A test MCP server",
            url="http://localhost:8080",
            protocol="http"
        )
        
        print(f"✓ Valid MCPServerRequest created: {mcp_request.name}")
        
        # Test MCP server request serialization
        mcp_dict = mcp_request.model_dump()
        assert "name" in mcp_dict
        assert "url" in mcp_dict
        assert "protocol" in mcp_dict
        print("✓ MCPServerRequest serialization works")
        
        return True
        
    except Exception as e:
        print(f"❌ MCP server request validation failed: {e}")
        return False


def test_tool_execution_models():
    """Test tool execution models."""
    print("Testing Tool Execution Models...")
    
    try:
        from shared.models.tool import ToolExecutionRequest, ToolExecutionResponse
        
        # Test execution request
        exec_request = ToolExecutionRequest(
            tool_id=uuid4(),
            inputs={"name": "World"},
            context={"user_id": "test_user"}
        )
        
        print(f"✓ ToolExecutionRequest created for tool: {exec_request.tool_id}")
        
        # Test execution response
        exec_response = ToolExecutionResponse(
            tool_id=exec_request.tool_id,
            execution_id="test_execution_123",
            status="success",
            outputs={"result": "Hello, World"},
            execution_time=150,
            started_at=datetime.utcnow()
        )
        
        print(f"✓ ToolExecutionResponse created: {exec_response.status}")
        
        return True
        
    except Exception as e:
        print(f"❌ Tool execution models failed: {e}")
        return False


def test_tool_discovery_models():
    """Test tool discovery models."""
    print("Testing Tool Discovery Models...")
    
    try:
        from shared.models.tool import ToolDiscoveryResponse
        
        # Test discovery response
        discovery_response = ToolDiscoveryResponse(
            available_tools=[],
            mcp_servers=[],
            categories=["test", "mock", "development"],
            capabilities=["basic", "advanced", "custom"]
        )
        
        print(f"✓ ToolDiscoveryResponse created with {len(discovery_response.categories)} categories")
        print(f"✓ ToolDiscoveryResponse created with {len(discovery_response.capabilities)} capabilities")
        
        return True
        
    except Exception as e:
        print(f"❌ Tool discovery models failed: {e}")
        return False


def test_tool_service_import():
    """Test that tool services can be imported."""
    print("Testing Tool Service Import...")
    
    try:
        from shared.services.tool_registry import ToolRegistryService
        from shared.services.mcp_gateway import MCPGatewayService
        
        print("✓ ToolRegistryService imported successfully")
        print("✓ MCPGatewayService imported successfully")
        
        return True
        
    except ImportError as e:
        print(f"❌ Service import failed: {e}")
        return False


def test_tool_templates():
    """Test tool template functionality."""
    print("Testing Tool Templates...")
    
    try:
        from shared.services.tool_registry import ToolRegistryService
        
        async def run_template_test():
            service = ToolRegistryService()
            templates = await service.get_tool_templates()
            
            print(f"✓ Found {len(templates)} tool templates")
            
            for template in templates:
                print(f"  - {template['name']}: {template['display_name']}")
                
                # Validate template structure
                required_fields = ['name', 'display_name', 'description', 'code', 'input_schema', 'output_schema']
                for field in required_fields:
                    if field not in template:
                        raise AssertionError(f"Template {template['name']} missing field: {field}")
            
            print("✓ All templates have required fields")
            return True
        
        return asyncio.run(run_template_test())
        
    except Exception as e:
        print(f"❌ Tool templates test failed: {e}")
        return False


def test_validation_result():
    """Test validation result class."""
    print("Testing Validation Result...")
    
    try:
        from shared.services.tool_registry import ValidationResult
        
        # Test valid result
        valid_result = ValidationResult(is_valid=True, errors=[])
        assert valid_result.is_valid == True
        assert len(valid_result.errors) == 0
        print("✓ Valid ValidationResult created")
        
        # Test invalid result
        invalid_result = ValidationResult(is_valid=False, errors=["Syntax error", "Missing function"])
        assert invalid_result.is_valid == False
        assert len(invalid_result.errors) == 2
        print("✓ Invalid ValidationResult created")
        
        return True
        
    except Exception as e:
        print(f"❌ Validation result test failed: {e}")
        return False


def test_api_endpoints_import():
    """Test that API endpoints can be imported."""
    print("Testing API Endpoints Import...")
    
    try:
        from shared.api.tool_registry import router as tool_router
        from shared.api.mcp_gateway import router as mcp_router
        
        print("✓ Tool Registry API router imported successfully")
        print("✓ MCP Gateway API router imported successfully")
        
        # Check that routers have the expected attributes
        assert hasattr(tool_router, 'prefix')
        assert hasattr(mcp_router, 'prefix')
        
        print(f"✓ Tool Registry API prefix: {tool_router.prefix}")
        print(f"✓ MCP Gateway API prefix: {mcp_router.prefix}")
        
        return True
        
    except ImportError as e:
        print(f"❌ API endpoints import failed: {e}")
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("TOOL REGISTRY AND MCP GATEWAY STANDALONE TESTS")
    print("=" * 60)
    print()
    
    tests = [
        test_tool_models_import,
        test_tool_request_validation,
        test_mcp_server_request_validation,
        test_tool_execution_models,
        test_tool_discovery_models,
        test_tool_service_import,
        test_tool_templates,
        test_validation_result,
        test_api_endpoints_import,
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
    else:
        print(f"❌ {failed} TESTS FAILED, {passed} TESTS PASSED")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)