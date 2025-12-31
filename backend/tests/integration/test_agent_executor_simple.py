"""Simple test script for Agent Executor Service without LLM dependencies."""

import asyncio
from datetime import datetime

print("Testing Agent Executor Service Components...")
print("=" * 50)

# Test 1: Import core modules
print("\n1. Testing imports...")
try:
    from shared.services.agent_state_manager import AgentStateManager, AgentState, AgentRuntimeInfo
    print("✓ AgentStateManager imported successfully")
except Exception as e:
    print(f"✗ Failed to import AgentStateManager: {str(e)}")

try:
    from shared.services.agent_error_handler import AgentErrorHandler, ErrorSeverity, RecoveryAction
    print("✓ AgentErrorHandler imported successfully")
except Exception as e:
    print(f"✗ Failed to import AgentErrorHandler: {str(e)}")

# Test 2: Test data structures
print("\n2. Testing data structures...")
try:
    runtime_info = AgentRuntimeInfo(
        agent_id="test-agent-123",
        tenant_id="test-tenant-123",
        state=AgentState.IDLE,
        active_executions=0,
        total_executions=0
    )
    print(f"✓ Created AgentRuntimeInfo: state={runtime_info.state}")
except Exception as e:
    print(f"✗ Failed to create AgentRuntimeInfo: {str(e)}")

# Test 3: Test enums
print("\n3. Testing enums...")
try:
    states = [state.value for state in AgentState]
    print(f"✓ AgentState values: {', '.join(states)}")
    
    severities = [sev.value for sev in ErrorSeverity]
    print(f"✓ ErrorSeverity values: {', '.join(severities)}")
    
    actions = [action.value for action in RecoveryAction]
    print(f"✓ RecoveryAction values: {', '.join(actions)}")
except Exception as e:
    print(f"✗ Failed to test enums: {str(e)}")

# Test 4: Test API endpoint imports
print("\n4. Testing API endpoint imports...")
try:
    from shared.api.agent_executor import router
    print(f"✓ Agent executor router imported successfully")
    print(f"  Router prefix: {router.prefix}")
    print(f"  Router tags: {router.tags}")
except Exception as e:
    print(f"✗ Failed to import agent executor router: {str(e)}")

# Test 5: Check if router is registered
print("\n5. Checking API router registration...")
try:
    from shared.api import api_router
    
    # Check if agent executor routes are included
    routes = [route.path for route in api_router.routes]
    executor_routes = [r for r in routes if 'agent-executor' in r]
    
    if executor_routes:
        print(f"✓ Found {len(executor_routes)} agent executor routes:")
        for route in executor_routes[:5]:  # Show first 5
            print(f"  - {route}")
    else:
        print("✗ No agent executor routes found in API router")
except Exception as e:
    print(f"✗ Failed to check API router: {str(e)}")

# Test 6: Test Docker configuration
print("\n6. Checking Docker configuration...")
try:
    import os
    
    db_url = os.getenv('DATABASE_URL', 'Not set')
    redis_url = os.getenv('REDIS_URL', 'Not set')
    
    print(f"✓ DATABASE_URL: {db_url[:50]}...")
    print(f"✓ REDIS_URL: {redis_url}")
except Exception as e:
    print(f"✗ Failed to check environment: {str(e)}")

# Test 7: Test lifecycle manager
print("\n7. Testing lifecycle manager...")
try:
    from shared.services.agent_executor import lifecycle_manager
    print("✓ Lifecycle manager imported successfully")
    print(f"  Monitoring enabled: {lifecycle_manager.monitoring_enabled}")
except Exception as e:
    print(f"✗ Failed to import lifecycle manager: {str(e)}")

# Test 8: Test global state manager
print("\n8. Testing global state manager...")
try:
    from shared.services.agent_state_manager import global_state_manager
    print("✓ Global state manager imported successfully")
except Exception as e:
    print(f"✗ Failed to import global state manager: {str(e)}")

# Test 9: Test global error handler
print("\n9. Testing global error handler...")
try:
    from shared.services.agent_error_handler import global_error_handler
    print("✓ Global error handler imported successfully")
except Exception as e:
    print(f"✗ Failed to import global error handler: {str(e)}")

print("\n" + "=" * 50)
print("✓ Agent Executor Service component tests completed!")
print("\nNote: Full integration tests require:")
print("  - Database connection")
print("  - Redis connection")
print("  - LLM provider setup")
print("  - Running agent instances")
