
import pytest
from uuid import uuid4
from shared.models.chain import ChainStatus, ChainNodeType, ChainExecutionStatus

@pytest.mark.integration
@pytest.mark.asyncio
class TestChainsAPI:
    
    async def create_valid_chain_payload(self):
        return {
            "name": f"API Test Chain {uuid4()}",
            "description": "Created via API Test",
            "status": "draft",
            "nodes": [
                {
                    "node_id": "start",
                    "node_type": "start",
                    "label": "Start",
                    "position_x": 0,
                    "position_y": 0
                },
                {
                    "node_id": "end",
                    "node_type": "end",
                    "label": "End",
                    "position_x": 200,
                    "position_y": 0
                }
            ],
            "edges": [
                {
                    "edge_id": "e1",
                    "source_node_id": "start",
                    "target_node_id": "end",
                    "label": "Connects"
                }
            ]
        }

    async def test_create_chain(self, test_client):
        payload = await self.create_valid_chain_payload()
        response = test_client.post("/api/v1/chains", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == payload["name"]
        assert len(data["nodes"]) == 2
        assert len(data["edges"]) == 1
        return data["id"]

    async def test_get_chain(self, test_client):
        # Create first
        payload = await self.create_valid_chain_payload()
        create_res = test_client.post("/api/v1/chains", json=payload)
        chain_id = create_res.json()["id"]

        # Get
        response = test_client.get(f"/api/v1/chains/{chain_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == chain_id
        assert data["name"] == payload["name"]

    async def test_update_chain(self, test_client):
        # Create first
        payload = await self.create_valid_chain_payload()
        create_res = test_client.post("/api/v1/chains", json=payload)
        chain_id = create_res.json()["id"]

        # Update
        update_payload = payload.copy()
        update_payload["name"] = "Updated Chain Name"
        update_payload["description"] = "Updated Description"
        
        # Add a node
        update_payload["nodes"].append({
            "node_id": "mid", 
            "node_type": "parallel_split", # Using a type that doesn't require agent_id for simplicity
            "label": "Mid", 
            "position_x": 100, 
            "position_y": 0
        })
        
        response = test_client.put(f"/api/v1/chains/{chain_id}", json=update_payload)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Chain Name"
        assert len(data["nodes"]) == 3

    async def test_list_chains(self, test_client):
        # Create a couple of chains
        payload1 = await self.create_valid_chain_payload()
        res1 = test_client.post("/api/v1/chains", json=payload1)
        assert res1.status_code == 201
        
        payload2 = await self.create_valid_chain_payload()
        res2 = test_client.post("/api/v1/chains", json=payload2)
        assert res2.status_code == 201

        response = test_client.get("/api/v1/chains")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 2
        # Verify structure of list item (lighter version)
        item = data[0]
        assert "node_count" in item
        assert "nodes" not in item # List view shouldn't have full nodes

    async def test_delete_chain(self, test_client):
        # Create first
        payload = await self.create_valid_chain_payload()
        create_res = test_client.post("/api/v1/chains", json=payload)
        chain_id = create_res.json()["id"]

        # Delete
        response = test_client.delete(f"/api/v1/chains/{chain_id}")
        assert response.status_code == 204

        # Verify gone
        get_res = test_client.get(f"/api/v1/chains/{chain_id}")
        assert get_res.status_code == 404

    async def test_execute_chain_api(self, test_client):
        # Create a simple chain
        payload = await self.create_valid_chain_payload()
        create_res = test_client.post("/api/v1/chains", json=payload)
        chain_id = create_res.json()["id"]

        # Execute
        exec_payload = {"input_data": {"test": "data"}}
        response = test_client.post(f"/api/v1/chains/{chain_id}/execute", json=exec_payload)
        
        # It might fail validation if we didn't set it up perfectly (e.g. valid agent IDs if we used agents), 
        # but here we used start/end nodes which should be valid pass-through.
        assert response.status_code == 202
        data = response.json()
        assert data["status"] in [ChainExecutionStatus.PENDING, ChainExecutionStatus.RUNNING, ChainExecutionStatus.COMPLETED]
        execution_id = data["id"]

        # Get execution status
        status_res = test_client.get(f"/api/v1/chains/executions/{execution_id}/status")
        assert status_res.status_code == 200
