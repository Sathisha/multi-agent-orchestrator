
import asyncio
import httpx
import uuid
import sys

# Configuration
BASE_URL = "http://localhost:8000/api/v1"
EMAIL = f"test_workflow_{uuid.uuid4()}@example.com"
PASSWORD = "TestPassword123"

# Basic BPMN XML
TEST_BPMN_XML = """<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL" xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI" xmlns:dc="http://www.omg.org/spec/DD/20100524/DC" xmlns:di="http://www.omg.org/spec/DD/20100524/DI" id="Definitions_1" targetNamespace="http://bpmn.io/schema/bpmn" exporter="Camunda Modeler" exporterVersion="5.0.0">
  <bpmn:process id="Process_Test_1" isExecutable="true">
    <bpmn:startEvent id="StartEvent_1" />
    <bpmn:sequenceFlow id="Flow_1" sourceRef="StartEvent_1" targetRef="EndEvent_1" />
    <bpmn:endEvent id="EndEvent_1" />
  </bpmn:process>
  <bpmndi:BPMNDiagram id="BPMNDiagram_1">
    <bpmndi:BPMNPlane id="BPMNPlane_1" bpmnElement="Process_Test_1">
      <bpmndi:BPMNShape id="_BPMNShape_StartEvent_2" bpmnElement="StartEvent_1">
        <dc:Bounds x="173" y="102" width="36" height="36" />
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="EndEvent_1_di" bpmnElement="EndEvent_1">
        <dc:Bounds x="400" y="102" width="36" height="36" />
      </bpmndi:BPMNShape>
      <bpmndi:BPMNEdge id="Flow_1_di" bpmnElement="Flow_1">
        <di:waypoint x="209" y="120" />
        <di:waypoint x="400" y="120" />
      </bpmndi:BPMNEdge>
    </bpmndi:BPMNPlane>
  </bpmndi:BPMNDiagram>
</bpmn:definitions>"""


def log(msg):
    print(msg)
    with open("api_test.log", "a") as f:
        f.write(msg + "\n")

async def verify_workflow():
    # Clear log
    with open("api_test.log", "w") as f:
        f.write("Starting test...\n")

    async with httpx.AsyncClient() as client:
        # 0. Health Check
        try:
            r = await client.get("http://localhost:8000/health")
            r.raise_for_status()
            log("✅ Backend is healthy")
        except Exception as e:
            log(f"❌ Backend not reachable: {e}")
            sys.exit(1)

        # 1. Register/Login
        log(f"ℹ️ Creating user {EMAIL}...")
        r = await client.post(f"{BASE_URL}/auth/register", json={
            "email": EMAIL,
            "password": PASSWORD,
            "full_name": "Workflow Tester"
        })
        if r.status_code != 201:
            log(f"⚠️ Registration failed ({r.status_code}), trying login...")
        
        r = await client.post(f"{BASE_URL}/auth/login", json={
            "email": EMAIL,
            "password": PASSWORD
        })
        if r.status_code != 200:
            log(f"❌ Login failed: {r.text}")
            sys.exit(1)
            
        token = r.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        log("✅ Logged in successfully")

        # 2. Create Workflow
        log("ℹ️ Creating workflow...")
        workflow_data = {
            "name": f"Verification Workflow {uuid.uuid4()}",
            "description": "Created by Verification Script",
            "bpmn_xml": TEST_BPMN_XML,
            "version": "1.0"
        }
        r = await client.post(f"{BASE_URL}/workflows", json=workflow_data, headers=headers)
        if r.status_code != 201:
            log(f"❌ Create failed: {r.text}")
            sys.exit(1)
        
        workflow = r.json()
        workflow_id = workflow["id"]
        log(f"✅ Workflow created: ID {workflow_id}")

        # 3. List Workflows
        log("ℹ️ Listing workflows...")
        r = await client.get(f"{BASE_URL}/workflows", headers=headers)
        if r.status_code != 200:
             log(f"❌ List failed: {r.text}")
             sys.exit(1)
        

        workflows = r.json()
        log(f"DEBUG: Looking for {workflow_id}")
        found_ids = [w['id'] for w in workflows]
        log(f"DEBUG: Found IDs: {found_ids}")
        
        if any(w["id"] == workflow_id for w in workflows):
            log("✅ Workflow found in list")
        else:
            log("❌ Workflow NOT found in list")
            sys.exit(1)

        # 4. Execute Workflow
        log("ℹ️ Executing workflow...")
        r = await client.post(f"{BASE_URL}/workflows/{workflow_id}/execute", json={"input_data": {}}, headers=headers)
        if r.status_code != 200:
            log(f"❌ Execution failed: {r.text}")
            # Zeebe might not be ready or workflow not deployed?
            # 500 error here would be what we want to catch if any.
            sys.exit(1)
        
        execution = r.json()
        execution_id = execution["id"]
        log(f"✅ Execution started: ID {execution_id}, Status: {execution['status']}")

        # 5. Check Status
        log("ℹ️ Checking execution status...")
        r = await client.get(f"{BASE_URL}/workflows/executions/{execution_id}", headers=headers)
        if r.status_code != 200:
            log(f"❌ Status check failed: {r.text}")
            sys.exit(1)
        
        status_data = r.json()
        log(f"✅ Status verified: {status_data['status']}")
        
        # Success
        log("\n🎉 ALL CHECKS PASSED")


if __name__ == "__main__":
    try:
        asyncio.run(verify_workflow())
    except Exception as e:
        import traceback
        msg = f"❌ FATAL ERROR: {e}\n{traceback.format_exc()}"
        print(msg)
        with open("api_test.log", "a") as f:
            f.write(msg + "\n")
        sys.exit(1)
