"""Test Agent Executor API endpoints."""

import asyncio
import httpx

async def test_api_endpoints():
    """Test the Agent Executor API endpoints."""
    print("Testing Agent Executor API endpoints...")
    print("=" * 50)
    
    base_url = "http://localhost:8000"
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        # Test 1: Health endpoint
        print("\n1. Testing health endpoint...")
        try:
            response = await client.get(f"{base_url}/api/v1/agent-executor/health")
            if response.status_code == 200:
                data = response.json()
                print(f"✓ Health endpoint working: {data}")
            else:
                print(f"✗ Health endpoint failed: {response.status_code}")
                print(f"  Response: {response.text}")
        except Exception as e:
            print(f"✗ Health endpoint error: {str(e)}")
        
        # Test 2: System status endpoint
        print("\n2. Testing system status endpoint...")
        try:
            response = await client.get(f"{base_url}/api/v1/agent-executor/system/status")
            if response.status_code == 200:
                data = response.json()
                print(f"✓ System status working:")
                print(f"  Active executions: {data.get('total_active_executions', 0)}")
            else:
                print(f"✗ System status failed: {response.status_code}")
                print(f"  Response: {response.text}")
        except Exception as e:
            print(f"✗ System status error: {str(e)}")
        
        # Test 3: List active executions
        print("\n3. Testing list active executions...")
        try:
            response = await client.get(
                f"{base_url}/api/v1/agent-executor/executions/active"
            )
            if response.status_code == 200:
                data = response.json()
                print(f"✓ Active executions endpoint working: {len(data)} executions")
            else:
                print(f"✗ Active executions failed: {response.status_code}")
                print(f"  Response: {response.text}")
        except Exception as e:
            print(f"✗ Active executions error: {str(e)}")
        
        # Test 4: Test main API root
        print("\n4. Testing main API root...")
        try:
            response = await client.get(f"{base_url}/")
            if response.status_code == 200:
                data = response.json()
                print(f"✓ Main API working: {data.get('message', 'Unknown')}")
            else:
                print(f"✗ Main API failed: {response.status_code}")
        except Exception as e:
            print(f"✗ Main API error: {str(e)}")
        
        # Test 5: Test health check endpoint
        print("\n5. Testing main health endpoint...")
        try:
            response = await client.get(f"{base_url}/health")
            if response.status_code == 200:
                data = response.json()
                print(f"✓ Main health endpoint working: {data.get('status', 'Unknown')}")
            else:
                print(f"✗ Main health failed: {response.status_code}")
        except Exception as e:
            print(f"✗ Main health error: {str(e)}")