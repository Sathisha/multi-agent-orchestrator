
import asyncio
import websockets
import json
import sys

async def test_server(name, port=8090):
    uri = f"ws://localhost:{port}/mcp/{name}"
    print(f"Connecting to {uri}...")
    try:
        async with websockets.connect(uri) as websocket:
            print(f"✓ Connected to {name}")
            
            # Send standard JSON-RPC Initialize
            msg = {
                "jsonrpc": "2.0",
                "method": "initialize",
                "params": {
                    "protocolVersion": "1.0",
                    "clientInfo": {"name": "test-script", "version": "1.0"},
                    "capabilities": {}
                },
                "id": 1
            }
            await websocket.send(json.dumps(msg))
            
            # Wait for response
            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            print(f"✓ Received response from {name}: {response[:100]}...")
            
            # Send initialized notification
            await websocket.send(json.dumps({
                "jsonrpc": "2.0",
                "method": "notifications/initialized"
            }))

            # Test a tool list (optional)
            await websocket.send(json.dumps({
                "jsonrpc": "2.0",
                "method": "tools/list",
                "id": 2
            }))
            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            print(f"✓ Received tools list from {name}: {response[:100]}...")

    except Exception as e:
        print(f"✗ Failed to connect or communicate with {name}: {e}")
        # sys.exit(1) # Don't exit hard so we can test others

async def main():
    await test_server("fetch")
    await test_server("filesystem")

if __name__ == "__main__":
    asyncio.run(main())
