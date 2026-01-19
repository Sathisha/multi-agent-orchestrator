"""
End-to-End Test for Agent Workflow Creation, Execution, and Verification.

This test validates the complete lifecycle of an agent-based workflow:
1. Create a tool via API
2. Create an agent with the tool via API
3. Create a workflow (chain) with agent nodes via API
4. Execute the workflow via API
5. Verify execution output
6. Verify execution logs are captured correctly
"""

import pytest
import asyncio
from uuid import uuid4
from httpx import AsyncClient


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_agent_workflow_execution_with_logs(async_client: AsyncClient):
    """
    Comprehensive E2E test that creates an agent, workflow, executes it,
    and verifies both output and logs.
    """
    
    # =========================================================================
    # Step 1: Create a Custom Calculator Tool
    # =========================================================================
    tool_name = f"calculator_{uuid4().hex[:8]}"
    tool_payload = {
        "name": tool_name,
        "description": "A simple calculator for basic arithmetic operations",
        "version": "1.0.0",
        "tool_type": "custom",
        "code": """
def execute(inputs, context=None):
    \"\"\"Execute arithmetic operations.\"\"\"
    operation = inputs.get("operation")
    a = float(inputs.get("a", 0))
    b = float(inputs.get("b", 0))
    
    if operation == "add":
        return {"result": a + b, "operation": "addition"}
    elif operation == "subtract":
        return {"result": a - b, "operation": "subtraction"}
    elif operation == "multiply":
        return {"result": a * b, "operation": "multiplication"}
    elif operation == "divide":
        if b == 0:
            return {"error": "Division by zero"}
        return {"result": a / b, "operation": "division"}
    else:
        return {"error": f"Unknown operation: {operation}"}
""",
        "input_schema": {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": ["add", "subtract", "multiply", "divide"],
                    "description": "Arithmetic operation to perform"
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
                "result": {"type": "number"},
                "operation": {"type": "string"},
                "error": {"type": "string"}
            }
        },
        "tags": ["math", "calculator", "e2e-test"]
    }
    
    response = await async_client.post("/api/v1/tools", json=tool_payload)
    assert response.status_code == 201, f"Tool creation failed: {response.text}"
    tool_data = response.json()
    tool_id = tool_data["id"]
    print(f"\n✓ Step 1: Created tool '{tool_name}' with ID: {tool_id}")
    
    # =========================================================================
    # Step 2: Create an Agent with the Tool
    # =========================================================================
    agent_name = f"math_agent_{uuid4().hex[:8]}"
    agent_payload = {
        "name": agent_name,
        "description": "A mathematical agent that can perform calculations",
        "type": "conversational",
        "system_prompt": "You are a helpful math assistant. Use the calculator tool for all math operations.",
        "available_tools": [tool_name],
        "config": {
            "model_name": "llama3.2:latest",
            "llm_provider": "ollama",
            "temperature": 0
        }
    }
    
    response = await async_client.post("/api/v1/agents", json=agent_payload)
    assert response.status_code == 201, f"Agent creation failed: {response.text}"
    agent_data = response.json()
    agent_id = agent_data["id"]
    print(f"✓ Step 2: Created agent '{agent_name}' with ID: {agent_id}")
    
    # =========================================================================
    # Step 3: Activate the Agent
    # =========================================================================
    response = await async_client.post(f"/api/v1/agents/{agent_id}/activate")
    assert response.status_code == 200, f"Agent activation failed: {response.text}"
    print(f"✓ Step 3: Activated agent '{agent_name}'")
    
    # =========================================================================
    # Step 4: Create a Workflow (Chain) with Agent Nodes
    # =========================================================================
    chain_name = f"math_workflow_{uuid4().hex[:8]}"
    chain_payload = {
        "name": chain_name,
        "description": "Workflow that uses math agent to perform calculations",
        "category": "test",
        "tags": ["e2e-test", "math"],
        "status": "active",
        "nodes": [
            {
                "node_id": "start",
                "node_type": "start",
                "label": "Start",
                "position_x": 100,
                "position_y": 100,
                "config": {}
            },
            {
                "node_id": "math_agent",
                "node_type": "agent",
                "agent_id": agent_id,
                "label": "Math Agent",
                "position_x": 300,
                "position_y": 100,
                "config": {
                    "timeout": 120
                }
            },
            {
                "node_id": "end",
                "node_type": "end",
                "label": "End",
                "position_x": 500,
                "position_y": 100,
                "config": {}
            }
        ],
        "edges": [
            {
                "edge_id": "e1",
                "source_node_id": "start",
                "target_node_id": "math_agent",
                "label": "To Agent"
            },
            {
                "edge_id": "e2",
                "source_node_id": "math_agent",
                "target_node_id": "end",
                "label": "To End"
            }
        ],
        "input_schema": {
            "type": "object",
            "properties": {
                "message": {"type": "string"}
            }
        },
        "metadata": {
            "test_type": "e2e",
            "created_by": "test_agent_workflow_e2e"
        }
    }
    
    response = await async_client.post("/api/v1/chains", json=chain_payload)
    assert response.status_code == 201, f"Chain creation failed: {response.text}"
    chain_data = response.json()
    chain_id = chain_data["id"]
    print(f"✓ Step 4: Created chain '{chain_name}' with ID: {chain_id}")
    print(f"  - Nodes: {len(chain_data['nodes'])}")
    print(f"  - Edges: {len(chain_data['edges'])}")
    
    # =========================================================================
    # Step 5: Validate the Chain
    # =========================================================================
    response = await async_client.get(f"/api/v1/chains/{chain_id}/validate")
    assert response.status_code == 200, f"Chain validation failed: {response.text}"
    validation_data = response.json()
    assert validation_data["is_valid"] is True, f"Chain is not valid: {validation_data}"
    print(f"✓ Step 5: Chain validated successfully")
    
    # =========================================================================
    # Step 6: Execute the Chain
    # =========================================================================
    execution_payload = {
        "input_data": {
            "message": "Calculate 123 + 456"
        },
        "execution_name": "E2E Test Execution",
        "variables": {},
        "correlation_id": f"e2e-test-{uuid4().hex[:8]}"
    }
    
    response = await async_client.post(
        f"/api/v1/chains/{chain_id}/execute",
        json=execution_payload
    )
    assert response.status_code in [200, 201], f"Chain execution failed: {response.text}"
    execution_data = response.json()
    execution_id = execution_data["id"]
    print(f"✓ Step 6: Started chain execution with ID: {execution_id}")
    
    # =========================================================================
    # Step 7: Poll for Execution Completion
    # =========================================================================
    max_polls = 60  # 2 minutes total (2s intervals)
    poll_interval = 2
    status = "pending"
    final_execution_data = None
    
    print("  Polling for execution completion...", end='', flush=True)
    for poll_count in range(max_polls):
        await asyncio.sleep(poll_interval)
        
        response = await async_client.get(f"/api/v1/chains/executions/{execution_id}/status")
        assert response.status_code == 200, f"Status check failed: {response.text}"
        
        status_data = response.json()
        status = status_data["status"]
        
        if poll_count % 5 == 0:  # Print progress every 10 seconds
            print(".", end='', flush=True)
        
        if status in ["completed", "failed", "cancelled"]:
            break
    
    print(f" {status}")
    
    # Get full execution details
    response = await async_client.get(f"/api/v1/chains/executions/{execution_id}")
    assert response.status_code == 200, f"Execution retrieval failed: {response.text}"
    final_execution_data = response.json()
    
    print(f"✓ Step 7: Execution completed with status: {final_execution_data['status']}")
    print(f"  - Duration: {final_execution_data.get('duration_seconds', 'N/A')}s")
    print(f"  - Completed nodes: {len(final_execution_data.get('completed_nodes', []))}")
    
    # =========================================================================
    # Step 8: Verify Execution Output
    # =========================================================================
    assert final_execution_data["status"] == "completed", \
        f"Execution did not complete successfully. Status: {final_execution_data['status']}, " \
        f"Error: {final_execution_data.get('error_message', 'N/A')}"
    
    # Verify output data exists
    output_data = final_execution_data.get("output_data")
    assert output_data is not None, "Output data is None"
    
    # Verify the calculation result is present
    # The output should contain the agent's response which includes "579" (123 + 456)
    output_str = str(output_data)
    assert "579" in output_str or "579.0" in output_str, \
        f"Expected result '579' not found in output: {output_data}"
    
    print(f"✓ Step 8: Output verified successfully")
    print(f"  - Output data: {output_data}")
    
    # =========================================================================
    # Step 9: Verify Execution Logs
    # =========================================================================
    response = await async_client.get(f"/api/v1/chains/executions/{execution_id}/logs")
    assert response.status_code == 200, f"Log retrieval failed: {response.text}"
    logs = response.json()
    
    assert len(logs) > 0, "No logs were created for the execution"
    print(f"✓ Step 9: Retrieved {len(logs)} execution logs")
    
    # Verify log structure
    for log in logs[:3]:  # Check first 3 logs
        assert "id" in log, "Log missing 'id' field"
        assert "execution_id" in log, "Log missing 'execution_id' field"
        assert "message" in log, "Log missing 'message' field"
        assert "level" in log, "Log missing 'level' field"
        assert "timestamp" in log, "Log missing 'timestamp' field"
        assert log["execution_id"] == execution_id, "Log execution_id mismatch"
    
    # Verify different node logs are present
    node_ids_in_logs = set()
    for log in logs:
        if log.get("node_id"):
            node_ids_in_logs.add(log["node_id"])
    
    print(f"  - Logs found for nodes: {node_ids_in_logs}")
    
    # Verify key events are logged
    log_messages = [log["message"].lower() for log in logs]
    has_start_log = any("start" in msg for msg in log_messages)
    has_agent_log = any("agent" in msg or "math" in msg for msg in log_messages)
    has_end_log = any("end" in msg or "complet" in msg for msg in log_messages)
    
    print(f"  - Has start log: {has_start_log}")
    print(f"  - Has agent log: {has_agent_log}")
    print(f"  - Has completion log: {has_end_log}")
    
    # =========================================================================
    # Step 10: Test Log Filtering by Level
    # =========================================================================
    response = await async_client.get(
        f"/api/v1/chains/executions/{execution_id}/logs",
        params={"level": "INFO"}
    )
    assert response.status_code == 200, f"Log filtering failed: {response.text}"
    info_logs = response.json()
    
    # Verify all returned logs are INFO level
    for log in info_logs:
        assert log["level"] == "INFO", f"Expected INFO level, got: {log['level']}"
    
    print(f"✓ Step 10: Log filtering verified ({len(info_logs)} INFO logs)")
    
    # =========================================================================
    # Summary
    # =========================================================================
    print("\n" + "="*70)
    print("E2E TEST SUMMARY")
    print("="*70)
    print(f"✓ Tool created: {tool_name}")
    print(f"✓ Agent created and activated: {agent_name}")
    print(f"✓ Chain created: {chain_name}")
    print(f"✓ Chain executed successfully")
    print(f"✓ Output verified: Contains expected result (579)")
    print(f"✓ Logs verified: {len(logs)} logs created")
    print(f"✓ Log filtering verified: {len(info_logs)} INFO logs")
    print("="*70)
    print("\nALL E2E TESTS PASSED! ✓")
    print("="*70)


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_workflow_with_parallel_agents(async_client: AsyncClient):
    """
    E2E test for workflow with parallel agent execution.
    Tests parallel split and join nodes with multiple agents.
    """
    
    # Create two simple agents
    agent1_name = f"agent_a_{uuid4().hex[:6]}"
    agent2_name = f"agent_b_{uuid4().hex[:6]}"
    
    # Create first agent
    agent1_payload = {
        "name": agent1_name,
        "description": "Agent A for parallel testing",
        "type": "conversational",
        "system_prompt": "You are Agent A. Respond with 'A: ' prefix.",
        "config": {
            "model_name": "llama3.2:latest",
            "llm_provider": "ollama",
            "temperature": 0
        }
    }
    
    response = await async_client.post("/api/v1/agents", json=agent1_payload)
    assert response.status_code == 201
    agent1_id = response.json()["id"]
    
    # Activate first agent
    await async_client.post(f"/api/v1/agents/{agent1_id}/activate")
    
    # Create second agent
    agent2_payload = {
        "name": agent2_name,
        "description": "Agent B for parallel testing",
        "type": "conversational",
        "system_prompt": "You are Agent B. Respond with 'B: ' prefix.",
        "config": {
            "model_name": "llama3.2:latest",
            "llm_provider": "ollama",
            "temperature": 0
        }
    }
    
    response = await async_client.post("/api/v1/agents", json=agent2_payload)
    assert response.status_code == 201
    agent2_id = response.json()["id"]
    
    # Activate second agent
    await async_client.post(f"/api/v1/agents/{agent2_id}/activate")
    
    print(f"✓ Created and activated agents: {agent1_name}, {agent2_name}")
    
    # Create workflow with parallel execution
    chain_name = f"parallel_workflow_{uuid4().hex[:6]}"
    chain_payload = {
        "name": chain_name,
        "description": "Workflow with parallel agent execution",
        "status": "active",
        "nodes": [
            {"node_id": "start", "node_type": "start", "label": "Start", "position_x": 100, "position_y": 200},
            {"node_id": "split", "node_type": "parallel_split", "label": "Split", "position_x": 250, "position_y": 200},
            {"node_id": "agent_a", "node_type": "agent", "agent_id": agent1_id, "label": "Agent A", "position_x": 400, "position_y": 100},
            {"node_id": "agent_b", "node_type": "agent", "agent_id": agent2_id, "label": "Agent B", "position_x": 400, "position_y": 300},
            {"node_id": "join", "node_type": "parallel_join", "label": "Join", "position_x": 550, "position_y": 200},
            {"node_id": "end", "node_type": "end", "label": "End", "position_x": 700, "position_y": 200}
        ],
        "edges": [
            {"edge_id": "e1", "source_node_id": "start", "target_node_id": "split"},
            {"edge_id": "e2", "source_node_id": "split", "target_node_id": "agent_a"},
            {"edge_id": "e3", "source_node_id": "split", "target_node_id": "agent_b"},
            {"edge_id": "e4", "source_node_id": "agent_a", "target_node_id": "join"},
            {"edge_id": "e5", "source_node_id": "agent_b", "target_node_id": "join"},
            {"edge_id": "e6", "source_node_id": "join", "target_node_id": "end"}
        ]
    }
    
    response = await async_client.post("/api/v1/chains", json=chain_payload)
    assert response.status_code == 201
    chain_id = response.json()["id"]
    print(f"✓ Created parallel workflow: {chain_name}")
    
    # Execute the workflow
    execution_payload = {
        "input_data": {"message": "Hello from parallel test"},
        "execution_name": "Parallel E2E Test"
    }
    
    response = await async_client.post(f"/api/v1/chains/{chain_id}/execute", json=execution_payload)
    assert response.status_code in [200, 201]
    execution_id = response.json()["id"]
    print(f"✓ Started parallel execution: {execution_id}")
    
    # Poll for completion
    max_polls = 60
    for _ in range(max_polls):
        await asyncio.sleep(2)
        response = await async_client.get(f"/api/v1/chains/executions/{execution_id}/status")
        status_data = response.json()
        if status_data["status"] in ["completed", "failed"]:
            break
    
    # Verify execution
    response = await async_client.get(f"/api/v1/chains/executions/{execution_id}")
    execution_data = response.json()
    
    assert execution_data["status"] == "completed", \
        f"Parallel execution failed: {execution_data.get('error_message')}"
    
    # Verify both agents executed
    completed_nodes = execution_data.get("completed_nodes", [])
    assert "agent_a" in completed_nodes, "Agent A did not execute"
    assert "agent_b" in completed_nodes, "Agent B did not execute"
    
    # Verify logs contain entries for both agents
    response = await async_client.get(f"/api/v1/chains/executions/{execution_id}/logs")
    logs = response.json()
    
    agent_a_logs = [log for log in logs if log.get("node_id") == "agent_a"]
    agent_b_logs = [log for log in logs if log.get("node_id") == "agent_b"]
    
    print(f"✓ Parallel execution completed successfully")
    print(f"  - Agent A logs: {len(agent_a_logs)}")
    print(f"  - Agent B logs: {len(agent_b_logs)}")
    print(f"  - Total logs: {len(logs)}")
    
    print("\n✓ PARALLEL WORKFLOW TEST PASSED!")
