
import pytest
from unittest.mock import MagicMock, patch
from uuid import uuid4
from sqlalchemy import select
from shared.models.workflow import Workflow, WorkflowStatus, ExecutionStatus

# Minimal valid BPMN XML for testing
MINIMAL_BPMN_XML = """<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL" xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI" xmlns:dc="http://www.omg.org/spec/DD/20100524/DC" xmlns:di="http://www.omg.org/spec/DD/20100524/DI" id="Definitions_1" targetNamespace="http://bpmn.io/schema/bpmn">
  <bpmn:process id="Process_1" isExecutable="true">
    <bpmn:startEvent id="StartEvent_1" />
    <bpmn:endEvent id="EndEvent_1" />
    <bpmn:sequenceFlow id="Flow_1" sourceRef="StartEvent_1" targetRef="EndEvent_1" />
  </bpmn:process>
  <bpmndi:BPMNDiagram id="BPMNDiagram_1">
    <bpmndi:BPMNPlane id="BPMNPlane_1" bpmnElement="Process_1">
      <bpmndi:BPMNShape id="_BPMNShape_StartEvent_2" bpmnElement="StartEvent_1">
        <dc:Bounds x="179" y="99" width="36" height="36" />
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="Event_1_di" bpmnElement="EndEvent_1">
        <dc:Bounds x="432" y="99" width="36" height="36" />
      </bpmndi:BPMNShape>
      <bpmndi:BPMNEdge id="Flow_1_di" bpmnElement="Flow_1">
        <di:waypoint x="215" y="117" />
        <di:waypoint x="432" y="117" />
      </bpmndi:BPMNEdge>
    </bpmndi:BPMNPlane>
  </bpmndi:BPMNDiagram>
</bpmn:definitions>
"""

@pytest.mark.integration
@pytest.mark.asyncio
class TestWorkflowScenarios:
    
    async def create_agent_payload(self):
        return {
            "name": f"Test Agent {uuid4()}",
            "description": "Agent for Workflow Test",
            "type": "conversational",
            "config": {"temperature": 0.7},
            "system_prompt": "You are a helpful assistant."
        }
        
    async def create_workflow_payload(self):
        return {
            "name": f"Test Workflow {uuid4()}",
            "description": "Workflow for integration test",
            "version": "1.0.0",
            "bpmn_xml": MINIMAL_BPMN_XML,
            "category": "test",
            "tags": ["test", "integration"],
            "input_schema": {"type": "object", "properties": {"message": {"type": "string"}}},
            "output_schema": {"type": "object", "properties": {"result": {"type": "string"}}},
            "timeout_minutes": 5,
            "max_concurrent_executions": 10
        }



    async def test_agent_creation_flow(self, async_client):

        """Test creating an agent as a prerequisite for workflows (if needed later)."""

        payload = await self.create_agent_payload()

        response = await async_client.post("/api/v1/agents", json=payload)

        assert response.status_code == 201

        data = response.json()

        assert data["name"] == payload["name"]

        assert "id" in data

        return data["id"]



    async def test_workflow_lifecycle(self, async_client, async_session, mock_zeebe_client):
        """Test creating, executing and checking status of a workflow."""
        from unittest.mock import AsyncMock
        assert isinstance(mock_zeebe_client.create_process_instance, AsyncMock)
        assert isinstance(mock_zeebe_client.topology, AsyncMock)

        # 1. Create Workflow
        payload = await self.create_workflow_payload()
        response = await async_client.post("/api/v1/workflows", json=payload)

        if response.status_code == 400:
             pytest.fail(f"BPMN Validation failed: {response.json()}")

        assert response.status_code == 201
        workflow_data = response.json()
        workflow_id = workflow_data["id"]

        assert workflow_data["name"] == payload["name"]
        assert workflow_data["status"] == WorkflowStatus.DRAFT



        



        # 2. Get Workflow
        response = await async_client.get(f"/api/v1/workflows/{workflow_id}")
        assert response.status_code == 200
        assert response.json()["id"] == workflow_id

        # 2.5 Manually activate workflow via SQL
        from sqlalchemy import update, select

        print(f"DEBUG: Updating workflow {workflow_id} to active")
        stmt = update(Workflow).where(Workflow.id == workflow_id).values(status=WorkflowStatus.ACTIVE.value)
        result = await async_session.execute(stmt)
        await async_session.commit()
        print(f"DEBUG: Update result rowcount: {result.rowcount}")

        # Verify in DB directly
        result = await async_session.execute(select(Workflow).where(Workflow.id == workflow_id))
        wf = result.scalar_one()
        print(f"DEBUG: Workflow status in DB: {wf.status}")
        assert wf.status == "active"

        # Verify status update via API
        response = await async_client.get(f"/api/v1/workflows/{workflow_id}")
        print(f"DEBUG: API Workflow status: {response.json().get('status')}")
        assert response.status_code == 200
        assert response.json()["status"] == "active", f"Workflow status mismatch: {response.json()}"

        # 3. Execute Workflow
        execution_payload = {
            "input_data": {"message": "Hello Workflow"},
            "priority": "normal",
            "correlation_id": str(uuid4())
        }
        
        # Ensure Zeebe client is mocked for this call
        mock_zeebe_client.create_process_instance.return_value = {"processInstanceKey": 12345}

        response = await async_client.post(f"/api/v1/workflows/{workflow_id}/execute", json=execution_payload)



        

        if response.status_code != 200:
             print(f"Execution Error: {response.json()}")

        assert response.status_code == 200
        execution_data = response.json()
        assert "id" in execution_data
        # Status might be PENDING or RUNNING depending on how fast the service updates it 
        # (mocked create_process_instance is synchronous here but service logic awaits it)
        assert execution_data["status"] in [ExecutionStatus.PENDING, ExecutionStatus.RUNNING, ExecutionStatus.COMPLETED]
        
        execution_id = execution_data["id"]
        
        # 4. List Executions
        response = await async_client.get("/api/v1/workflows/executions")
        assert response.status_code == 200
        executions = response.json()
        assert len(executions) > 0
        assert any(e["id"] == execution_id for e in executions)

