#!/usr/bin/env python3
"""Test workflow execution and monitor logs."""
import requests
import time
import json

# Configuration
BASE_URL = "http://localhost:8001"
CHAIN_ID = "fee9e6ce-c973-4781-9b7d-fa90e4e3dd50"

# Test workflow execution
print("🚀 Triggering workflow execution...")
response = requests.post(
    f"{BASE_URL}/api/v1/chains/{CHAIN_ID}/execute",
    headers={"Content-Type": "application/json"},
    json={"input_data": {"query": "Why is the sky blue?"}}
)

if response.status_code == 200:
    result = response.json()
    execution_id = result.get("execution_id")
    print(f"✅ Execution started: {execution_id}")
    
    # Poll for completion
    for i in range(30):
        time.sleep(1)
        status_response = requests.get(f"{BASE_URL}/api/v1/chain-executions/{execution_id}")
        if status_response.status_code == 200:
            status_data = status_response.json()
            print(f"Status: {status_data.get('status')}")
            
            if status_data.get("status") in ["completed", "failed"]:
                print("\n📊 Final Result:")
                print(json.dumps(status_data, indent=2))
                
                # Get node results
                if status_data.get("node_results"):
                    print("\n📝 Node Results:")
                    for node_id, result in status_data["node_results"].items():
                        if node_id != "__states__":
                            print(f"\n  Node: {node_id}")
                            print(f"  Output: {result.get('output', {})}")
                break
else:
    print(f"❌ Failed to start execution: {response.status_code}")
    print(response.text)
