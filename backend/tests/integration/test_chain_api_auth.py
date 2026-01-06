import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4

@pytest.mark.asyncio
async def test_execute_chain_auth(
    async_client: AsyncClient,
    async_db_session: AsyncSession
):
    """Test chain execution with and without auth."""
    # Use real auth dependency for this test
    from main import app
    from shared.api.auth import get_current_user_or_api_key
    app.dependency_overrides[get_current_user_or_api_key] = get_current_user_or_api_key
    
    # 1. Create a chain
    chain_data = {
        "name": "Auth Test Chain",
        "description": "Testing Auth",
        "nodes": [],
        "edges": []
    }
    response = await async_client.post("/api/v1/chains", json=chain_data)
    # Auth middleware (if applied globally) might block this too? 
    # Current implementation secured only execute endpoint or global?
    # Based on main.py, audit is global, but not strict auth on all endpoints unless defined?
    # Chains create endpoint in chains.py uses Depends(get_async_db) but NOT get_current_user?
    # Wait, create_chain in chains.py:
    # @router.post("", response_model=ChainResponse, status_code=status.HTTP_201_CREATED)
    # async def create_chain(...):
    # It seems UNPROTECTED currently! (I only secured execute_chain)
    
    assert response.status_code == 201
    chain_id = response.json()["id"]
    
    # 2. Execute without auth
    execute_url = f"/api/v1/chains/{chain_id}/execute"
    payload = {"input_data": {"test": "val"}}
    
    resp_no_auth = await async_client.post(execute_url, json=payload)
    assert resp_no_auth.status_code == 401
    
    # 3. Execute with invalid API Key
    resp_bad_key = await async_client.post(
        execute_url, 
        json=payload, 
        headers={"X-API-Key": "invalid_key"}
    )
    assert resp_bad_key.status_code == 401
    
    # 4. Execute with valid API Key
    # We need a valid API Key. 
    # The fixture sample_api_key_headers should provide one if I define it, 
    # OR I can create one via API if I have a user token.
    # Let's assume I need to create one.
    
    # Register user to get token
    # (Assuming basic fixtures exist or I do it manually)
    # Actually, simpler: Use the dependency injection override or just create key in DB.
    
    # Generate a key directly in DB for this test to avoid dependency on other APIs
    from shared.models.api_key import APIKey
    from shared.services.api_key import APIKeyService
    from datetime import datetime
    
    # Create user for the key
    # (Need a user ID, maybe use a random UUID if FK not strict or create user)
    # Using existing test fixtures usually provides a user. 
    # I'll rely on db_session to insert one.
    
    user_id = uuid4() 
    # Note: If FK constraint exists, I need a real user.
    # Let's try to fetch a user from fixture or create one.
    # I'll try creating a key via Service.
    
    service = APIKeyService(async_db_session)
    # Create key
    # We need a user_id.
    # Let's create a dummy user first?
    # Or just use the service.
    
    # Since this is integration test, it's better to use the fixture `admin_user` or similar if available.
    # I'll blindly try to use a random UUID, if it fails I'll fix it.
    
    api_key, plain_key = await service.create_api_key(
        user_id=user_id,
        name="Test Key"
    )
    
    headers = {"X-API-Key": plain_key}
    
    resp_valid = await async_client.post(execute_url, json=payload, headers=headers)
    assert resp_valid.status_code == 202
    
