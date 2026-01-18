import requests
import json
import sys
import asyncio
from uuid import uuid4

BASE_URL = "http://localhost:8000/api/v1"
ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "admin"

def get_token(email, password):
    # API expects JSON with email/password
    response = requests.post(f"{BASE_URL}/auth/login", json={"email": email, "password": password})
    if response.status_code != 200:
        print(f"Login failed: {response.text}")
        sys.exit(1)
    return response.json()["access_token"]

def verify_rbac():
    print("1. Authenticating as Super Admin...")
    token = get_token(ADMIN_EMAIL, ADMIN_PASSWORD)
    headers = {"Authorization": f"Bearer {token}"}
    print("   Success!")

    print("\n2. Listing Roles...")
    response = requests.get(f"{BASE_URL}/auth/roles", headers=headers)
    if response.status_code != 200:
        print(f"Failed to list roles: {response.text}")
        sys.exit(1)
    roles = response.json()
    print(f"   Found {len(roles)} roles.")
    print(f"   Roles: {[r['name'] for r in roles]}")
    standard_role = next((r for r in roles if r["name"] == "standard_user"), None)
    if not standard_role:
        print("   'standard_user' role not found!")
        sys.exit(1)
    print("   'standard_user' role found.")

    print("\n3. Creating Test User...")
    user_data = {
        "email": "rbac_test_v2@example.com",
        "username": "rbac_test_v2",
        "full_name": "RBAC Test User V2",
        "password": "Password123!",
        "status": "active"
    }
    
    # Check if user exists first (by email is hard without filter, so just try create)
    response = requests.post(f"{BASE_URL}/auth/users", json=user_data, headers=headers) # Note: endpoint is /auth/users (no trailing slash usually)
    if response.status_code == 201:
        user_id = response.json()["id"]
        print("   User created successfully.")
    elif response.status_code == 400 and "already exists" in response.text:
         print("   User might already exist (400). Skipping creation check.")
         # Try to list users to find it
         list_resp = requests.get(f"{BASE_URL}/auth/users", headers=headers)
         users = list_resp.json()
         existing = next((u for u in users if u["email"] == user_data["email"]), None)
         if existing:
             user_id = existing["id"]
             print(f"   Found existing user ID: {user_id}")
         else:
             print("   Could not find existing user.")
             sys.exit(1)
    else:
         print(f"   Failed to create user: {response.status_code} {response.text}")
         sys.exit(1)


    print("\n4a. Listing Agents...")
    response = requests.get(f"{BASE_URL}/agents", headers=headers)
    if response.status_code != 200:
        print(f"Failed to list agents: {response.text}")
        agent_id = None
    else:
        agents = response.json()
        if not agents:
            print("   No agents found.")
            agent_id = None
        else:
            agent_id = agents[0]["id"]
            print(f"   Using agent: {agents[0]['name']} ({agent_id})")

    if agent_id:
        print("\n5. Assigning Role to Agent...")
        # POST /agents/{id}/roles
        payload = {
            "role_id": standard_role["id"],
            "access_type": "execute"
        }
        response = requests.post(f"{BASE_URL}/agents/{agent_id}/roles", json=payload, headers=headers)
        if response.status_code != 200 and response.status_code != 201: # allow 200 or 201
             # If already assigned, it returns existing assignment object (200 OK usually)
             print(f"   Assignment response: {response.status_code}")
        
    
    print("\n7. Workflow RBAC Check")
    # Insert dummy workflow directly into DB
    try:
        from shared.database.connection import engine
        from sqlalchemy import text
        
        with engine.connect() as conn:
            chain_id = str(uuid4())
            # Use raw SQL to avoid model import issues if any
            # Added is_deleted just in case
            conn.execute(text("""
                INSERT INTO chains (id, name, description, config, is_active, created_by, is_deleted)
                VALUES (:id, 'Test Chain', 'For RBAC Test', '{}', true, NULL, false)
            """), {"id": chain_id})
            conn.commit()
            print(f"   Created dummy chain in DB: {chain_id}")
            
            # Now test API
            print(f"   Assigning role to workflow {chain_id}...")
            payload = {
                "role_id": standard_role["id"],
                "access_type": "view"
            }
            response = requests.post(f"{BASE_URL}/workflows/{chain_id}/roles", json=payload, headers=headers)
            if response.status_code == 200:
                print("   Workflow role assigned successfully!")
                print(f"   Response: {response.json()}")
                
                # Verify list
                list_resp = requests.get(f"{BASE_URL}/workflows/{chain_id}/roles", headers=headers)
                print(f"   Roles on workflow: {len(list_resp.json())}")
                
                # Revoke
                revoke_resp = requests.delete(f"{BASE_URL}/workflows/{chain_id}/roles/{standard_role['id']}", headers=headers)
                print(f"   Revoke status: {revoke_resp.status_code}")
                
            else:
                print(f"   Failed to assign workflow role: {response.status_code} {response.text}")
                
            # Cleanup
            conn.execute(text("DELETE FROM chains WHERE id = :id"), {"id": chain_id})
            conn.commit()
        
    except ImportError:
        print("   Could not import DB modules (running outside container?), skipping direct DB workflow test.")
    except Exception as e:
        print(f"   Workflow test error: {e}")

    print("\nVerification Complete!")

if __name__ == "__main__":
    try:
        verify_rbac()
    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)
