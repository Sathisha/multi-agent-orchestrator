# MCP Integration Roadmap

## Current Status
- **Backend**: ✅ **Ready**. Implements `MCPGatewayService` acting as an MCP Client. Supports HTTP/HTTPS and WS/WSS protocols. Database models and API endpoints exist.
- **Frontend**: ❌ **Missing**. No UI for managing servers, discovering tools, or connecting.
- **Infrastructure**: ❌ **Missing**. `docker-compose.yml` does not run any MCP servers. `mcp-config.json` and `start-mcp-servers.sh` exist but are unused and likely incomplete (shell script is a placeholder).

## Answers to User Questions
    *   **Yes**. The "Catalog" items are standard Docker images. To use them in this project, we will add them to our `docker-compose.yml`.
    *   **However**, most of these (e.g., `fetch`) use `stdio` (standard input/output). Our backend (running in a container) cannot easily talk to them directly.
    *   **Solution**: We will build a "Bridge" service that runs these images and exposes them via WebSockets, allowing our backend to connect.
2.  **Do I need an MCP client?**
    *   **No**. The Backend (`backend/shared/services/mcp_gateway.py`) *is* the MCP Client. It handles the protocol negotiation.
    *   **Constraint**: It currently supports HTTP/WebSocket. For Catalog items using `stdio`, we need the "Bridge" mentioned above.

## TODO List

### 1. Infrastructure (Docker & Catalog Integration)
The backend supports HTTP/WS. Standard Catalog servers (like `fetch`, `filesystem`) often use `stdio`.

- [ ] **Create MCP Bridge Service ("The Adapter")**:
    - Create a Node.js-based Docker container in `infrastructure/docker/mcp-bridge`.
    - This service will act as a host for Catalog images.
    - It will expose a WebSocket endpoint (e.g., `ws://mcp-bridge:8000/fetch`) and spawn the underlying Docker tool (e.g., `docker run ... fetch`).
    - *Simpler MVP*: Run the tool *inside* the bridge container as a subprocess (if Node.js) or sidecar.
- [ ] **Update `docker-compose.yml`**:
    - Add the `mcp-bridge` service.
    - Add specific Catalog images we want to support (e.g., `browsertool`, `filesystem`) if they can run standalone.

### 2. Frontend (UI)
We need a UI to manage these connections.

- [ ] **MCP Servers Page**:
    - List configured MCP servers.
    - "Add Server" button (Step-by-step wizard or modal).
        - Name, URL, Protocol (HTTP/WS), Auth (API Key/Basic).
    - Status indicators (Connected, Error, Disconnected).
- [ ] **Server Details & Tool Discovery**:
    - View details of a server.
    - "Discover Tools" button to fetch tools from the server.
    - List available tools with descriptions.
- [ ] **Tool Testing UI** (Optional but recommended):
    - Simple interface to execute a discovered tool and view the result.

### 3. Backend (Validation)
- [ ] **Verify Connection**:
    - Test connection logic with the new Docker service.
    - Ensure `discover_tools` correctly parses the MCP protocol response.

## Architecture Proposal

```mermaid
graph LR
    User[User] --> Frontend[React Frontend]
    Frontend -->|Manage Servers| Backend[Python Backend API]
    Backend -->|MCP Protocol (HTTP/WS)| Bridge[MCP Bridge Service (Docker)]
    Bridge -->|Stdio| Tool1[Filesystem Server]
    Bridge -->|Stdio| Tool2[Fetch Server]
```
