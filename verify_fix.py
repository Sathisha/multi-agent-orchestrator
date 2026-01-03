import requests
import json

BASE_URL = "http://localhost:8001/api/v1"
ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "admin"

def verify_tool_registry():
    print(f"Authenticating as {ADMIN_EMAIL}...")
    try:
        auth_response = requests.post(
            f"{BASE_URL}/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        auth_response.raise_for_status()
        token = auth_response.json()["access_token"]
        print("Authentication successful.")
        
        print("Listing tools...")
        headers = {"Authorization": f"Bearer {token}"}
        tools_response = requests.get(
            f"{BASE_URL}/tools?limit=1",
            headers=headers
        )
        tools_response.raise_for_status()
        tools = tools_response.json()
        print(f"Successfully retrieved {len(tools)} tools.")
        print(f"First tool: {tools[0]['name'] if tools else 'None'}")
        return True
    except Exception as e:
        print(f"Verification failed: {e}")
        if hasattr(e, 'response') and e.response is not None:
             print(f"Response status: {e.response.status_code}")
             print(f"Response text: {e.response.text}")
        return False

if __name__ == "__main__":
    if verify_tool_registry():
        print("✅ ToolRegistryService fix verified!")
    else:
        print("❌ Verification failed.")
