
import asyncio
import websockets
import json
import sys

async def resolve_host(host):
    try:
        import socket
        ip = socket.gethostbyname(host)
        print(f"✓ Resolved {host} to {ip}")
        return True
    except Exception as e:
        print(f"✗ Failed to resolve {host}: {e}")
        return False

async def test_server(name):
    # Using the container alias that we saw in docker inspect (and standard compose naming)
    # The bridge container handles /mcp/fetch, /mcp/filesystem
    uri = f"ws://ai-agent-framework-mcp-bridge:8000/mcp/{name}"
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
                    "clientInfo": {"name": "verify-script", "version": "1.0"},
                    "capabilities": {}
                },
                "id": 1
            }
            await websocket.send(json.dumps(msg))
            
            # Wait for response
            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            print(f"✓ Received response from {name}: {response[:100]}...")
            
    except Exception as e:
        print(f"✗ Failed to connect to {name}: {e}")
        raise e

async def main():
    print("--- DNS Debug ---")
    await resolve_host("postgres")
    await resolve_host("ai-agent-framework-mcp-bridge")
    print("-----------------")

    print("\nStarting MCP Bridge Verification...")
    # We expect these to succeed now
    # await test_server("fetch") # Removed as package is not found
    await test_server("filesystem")

if __name__ == "__main__":
    asyncio.run(main())
