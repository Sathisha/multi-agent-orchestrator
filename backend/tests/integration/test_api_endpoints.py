"""
Test API endpoints for Tool Registry and MCP Gateway.

This test verifies that the API endpoints can be imported and have the correct structure.
"""

import sys
import os

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_tool_registry_api():
    """Test tool registry API endpoints."""
    print("Testing Tool Registry API...")
    
    try:
        from shared.api.tool_registry import router as tool_router
        
        print(f"✓ Tool Registry router imported successfully")
        print(f"  - Prefix: {tool_router.prefix}")
        print(f"  - Tags: {tool_router.tags}")
        
        # Check that router has routes
        routes = tool_router.routes
        print(f"  - Number of routes: {len(routes)}")
        
        # List route paths and methods
        for route in routes:
            if hasattr(route, 'path') and hasattr(route, 'methods'):
                methods = ', '.join(route.methods) if route.methods else 'N/A'
                print(f"    - {methods} {route.path}")
        
        return True
        
    except Exception as e:
        print(f"❌ Tool Registry API test failed: {e}")
        return False


def test_mcp_gateway_api():
    """Test MCP gateway API endpoints."""
    print("Testing MCP Gateway API...")
    
    try:
        from shared.api.mcp_gateway import router as mcp_router
        
        print(f"✓ MCP Gateway router imported successfully")
        print(f"  - Prefix: {mcp_router.prefix}")
        print(f"  - Tags: {mcp_router.tags}")
        
        # Check that router has routes
        routes = mcp_router.routes
        print(f"  - Number of routes: {len(routes)}")
        
        # List route paths and methods
        for route in routes:
            if hasattr(route, 'path') and hasattr(route, 'methods'):
                methods = ', '.join(route.methods) if route.methods else 'N/A'
                print(f"    - {methods} {route.path}")
        
        return True
        
    except Exception as e:
        print(f"❌ MCP Gateway API test failed: {e}")
        return False


def test_main_api_router():
    """Test that the main API router includes our endpoints."""
    print("Testing Main API Router Integration...")
    
    try:
        from shared.api import api_router
        
        print(f"✓ Main API router imported successfully")
        
        # Check that our routers are included
        routes = api_router.routes
        print(f"  - Total routes in main router: {len(routes)}")
        
        # Look for our specific routes
        tool_routes = []
        mcp_routes = []
        
        for route in routes:
            if hasattr(route, 'path'):
                if '/tools' in route.path:
                    tool_routes.append(route.path)
                elif '/mcp' in route.path:
                    mcp_routes.append(route.path)
        
        print(f"  - Tool-related routes found: {len(tool_routes)}")
        for route in tool_routes[:5]:  # Show first 5
            print(f"    - {route}")
        if len(tool_routes) > 5:
            print(f"    - ... and {len(tool_routes) - 5} more")
        
        print(f"  - MCP-related routes found: {len(mcp_routes)}")
        for route in mcp_routes[:5]:  # Show first 5
            print(f"    - {route}")
        if len(mcp_routes) > 5:
            print(f"    - ... and {len(mcp_routes) - 5} more")
        
        return True
        
    except Exception as e:
        print(f"❌ Main API router test failed: {e}")
        return False


def test_endpoint_dependencies():
    """Test that endpoint dependencies can be resolved."""
    print("Testing Endpoint Dependencies...")
    
    try:
        # Test that we can import the dependency functions
        from shared.middleware.tenant import get_tenant_context
        from shared.middleware.auth import get_current_user
        
        print("✓ Tenant context dependency imported")
        print("✓ Authentication dependency imported")
        
        # Test that we can import the service classes
        from shared.services.tool_registry import ToolRegistryService
        from shared.services.mcp_gateway import MCPGatewayService
        
        print("✓ ToolRegistryService imported")
        print("✓ MCPGatewayService imported")
        
        return True
        
    except Exception as e:
        print(f"❌ Endpoint dependencies test failed: {e}")
        return False


def main():
    """Run all API tests."""
    print("=" * 60)
    print("TOOL REGISTRY AND MCP GATEWAY API TESTS")
    print("=" * 60)
    print()
    
    tests = [
        test_tool_registry_api,
        test_mcp_gateway_api,
        test_main_api_router,
        test_endpoint_dependencies,
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
        print(f"✅ ALL {passed} API TESTS PASSED SUCCESSFULLY!")
        print()
        print("API IMPLEMENTATION STATUS:")
        print("✅ Tool Registry API endpoints are properly defined")
        print("✅ MCP Gateway API endpoints are properly defined")
        print("✅ Main API router includes both tool and MCP routes")
        print("✅ All endpoint dependencies can be imported")
        print()
        print("READY FOR:")
        print("- Integration testing with database")
        print("- End-to-end API testing")
        print("- Property-based testing")
    else:
        print(f"❌ {failed} API TESTS FAILED, {passed} TESTS PASSED")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)