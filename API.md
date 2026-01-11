# API Documentation

Welcome to the Multi-Agent Orchestrator API documentation. This guide provides comprehensive information about all available APIs, authentication, and common use cases.

## 📚 Quick Links

- **[Interactive API Docs (Swagger UI)](https://sathisha.github.io/multi-agent-orchestrator/api/swagger-ui.html)** - Test APIs in your browser
- **[OpenAPI Specification](https://sathisha.github.io/multi-agent-orchestrator/api/openapi.json)** - Download machine-readable spec
- **[Local API Docs](http://localhost:8000/docs)** - When running locally

## 🎯 Overview

The Multi-Agent Orchestrator provides a comprehensive REST API for creating, managing, and executing AI agents and workflows. The API is built with FastAPI and follows OpenAPI 3.1 standards.

### Base URL

**Development:** `http://localhost:8000`  
**Production:** Configure based on your deployment

### API Versioning

The API uses URL path versioning for backward compatibility:
- **v1**: `/api/v1/*` - Current stable version
- Legacy endpoints without version prefix are supported but deprecated

## 🔐 Authentication

The API supports multiple authentication methods:

### 1. API Key Authentication (Recommended for Integrations)

API keys provide secure, revocable access to the API without requiring user credentials.

**Creating an API Key:**
```bash
POST /api/api-keys
Content-Type: application/json
Authorization: Bearer <your-jwt-token>

{
  "name": "My Integration Key",
  "expires_at": "2026-12-31T23:59:59Z",
  "scopes": ["agents:read", "agents:execute"]
}
```

**Using an API Key:**
```bash
GET /api/agents
X-API-Key: <your-api-key>
```

**Available Scopes:**
- `agents:read` - Read agent configurations
- `agents:write` - Create and update agents
- `agents:execute` - Execute agents and workflows
- `agents:delete` - Delete agents
- `models:read` - Read LLM model configurations
- `models:write` - Manage LLM models
- `admin:*` - Full administrative access

### 2. JWT Bearer Token Authentication

For user-based authentication, the API uses JWT tokens.

**Login:**
```bash
POST /api/auth/login
Content-Type: application/json

{
  "username": "your-username",
  "password": "your-password"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

**Using JWT Token:**
```bash
GET /api/agents
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

### 3. Session-Based Authentication

The API also supports session cookies for web applications.

## 📡 Core API Endpoints

### Agents

Manage AI agents with custom configurations and capabilities.

#### List All Agents
```bash
GET /api/agents
```

#### Create Agent
```bash
POST /api/agents
Content-Type: application/json

{
  "name": "Customer Support Agent",
  "description": "Handles customer inquiries",
  "system_prompt": "You are a helpful customer support agent...",
  "llm_model_id": 1,
  "temperature": 0.7,
  "max_tokens": 2000,
  "tools": ["web_search", "knowledge_base"]
}
```

#### Get Agent Details
```bash
GET /api/agents/{agent_id}
```

#### Update Agent
```bash
PUT /api/agents/{agent_id}
Content-Type: application/json

{
  "name": "Updated Agent Name",
  "temperature": 0.8
}
```

#### Delete Agent
```bash
DELETE /api/agents/{agent_id}
```

### Agent Execution

Execute agents and workflows with input data.

#### Execute Agent
```bash
POST /api/agents/{agent_id}/execute
Content-Type: application/json

{
  "input": "What is the weather in San Francisco?",
  "context": {
    "user_id": "user123",
    "session_id": "session456"
  },
  "streaming": false
}
```

#### Execute Workflow (BPMN)
```bash
POST /api/v1/chains/{chain_id}/execute
Content-Type: application/json

{
  "input_data": {
    "query": "Analyze customer sentiment",
    "source": "support_tickets"
  }
}
```

#### Get Execution Status
```bash
GET /api/v1/executions/{execution_id}
```

#### Get Execution Logs
```bash
GET /api/v1/executions/{execution_id}/logs
```

### LLM Models

Manage language model configurations.

#### List Models
```bash
GET /api/llm-models
```

#### Create Model Configuration
```bash
POST /api/llm-models
Content-Type: application/json

{
  "name": "GPT-4",
  "provider": "openai",
  "model_identifier": "gpt-4",
  "api_key": "sk-...",
  "parameters": {
    "temperature": 0.7,
    "max_tokens": 4000
  }
}
```

#### Test Model
```bash
POST /api/llm-models/{model_id}/test
Content-Type: application/json

{
  "prompt": "Hello, how are you?",
  "temperature": 0.7
}
```

### LLM Providers

Manage LLM provider configurations (OpenAI, Anthropic, Azure OpenAI, Ollama).

#### List Providers
```bash
GET /api/llm-providers
```

#### Create Provider
```bash
POST /api/llm-providers
Content-Type: application/json

{
  "name": "OpenAI Production",
  "provider_type": "openai",
  "api_key": "sk-...",
  "config": {
    "organization": "org-..."
  }
}
```

### Tools & MCP Servers

Manage tools and Model Context Protocol (MCP) servers.

#### List Tools
```bash
GET /api/tools
```

#### List MCP Servers
```bash
GET /api/mcp-servers
```

#### Create MCP Server
```bash
POST /api/mcp-servers
Content-Type: application/json

{
  "name": "Web Search Server",
  "server_type": "stdio",
  "command": "python",
  "args": ["-m", "mcp_server_web_search"],
  "enabled": true
}
```

### Memory & Context

Manage agent memory and conversation context.

#### Store Memory
```bash
POST /api/memory
Content-Type: application/json

{
  "agent_id": 1,
  "session_id": "session123",
  "content": "User prefers concise answers",
  "memory_type": "preference"
}
```

#### Search Memory
```bash
POST /api/memory/search
Content-Type: application/json

{
  "agent_id": 1,
  "query": "user preferences",
  "limit": 5
}
```

### Monitoring & Health

System monitoring and health check endpoints.

#### Health Check
```bash
GET /health
```

#### System Metrics
```bash
GET /api/monitoring/metrics
```

#### Database Health
```bash
GET /api/monitoring/database
```

#### Cache Health
```bash
GET /api/monitoring/cache
```

## 🚀 Common Use Cases

### Use Case 1: Execute a Simple Agent

```bash
# 1. Create an agent
curl -X POST http://localhost:8000/api/agents \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "name": "Q&A Agent",
    "system_prompt": "You are a helpful assistant",
    "llm_model_id": 1
  }'

# 2. Execute the agent
curl -X POST http://localhost:8000/api/agents/1/execute \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "input": "What is the capital of France?"
  }'
```

### Use Case 2: Create and Execute a Workflow

```bash
# 1. Create a workflow (BPMN)
curl -X POST http://localhost:8000/api/v1/chains \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "name": "Customer Support Workflow",
    "description": "Multi-step customer support process",
    "workflow_definition": {...}
  }'

# 2. Execute the workflow
curl -X POST http://localhost:8000/api/v1/chains/1/execute \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "input_data": {
      "customer_query": "I need help with my order"
    }
  }'

# 3. Check execution status
curl -X GET http://localhost:8000/api/v1/executions/abc-123 \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Use Case 3: Agent with Tools

```bash
# 1. Create agent with tools enabled
curl -X POST http://localhost:8000/api/agents \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "name": "Research Agent",
    "system_prompt": "You help users research topics",
    "llm_model_id": 1,
    "tools": ["web_search", "wikipedia"]
  }'

# 2. Execute with tool usage
curl -X POST http://localhost:8000/api/agents/1/execute \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "input": "Find recent news about AI advancements"
  }'
```

### Use Case 4: Expose Workflow as API

```bash
# 1. Create API key for workflow
curl -X POST http://localhost:8000/api/api-keys \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "name": "Workflow API Key",
    "scopes": ["agents:execute"],
    "metadata": {
      "workflow_id": 1
    }
  }'

# 2. External users can call with API key
curl -X POST http://localhost:8000/api/v1/chains/1/execute \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_API_KEY" \
  -d '{
    "input_data": {...}
  }'
```

## ⚡ Rate Limiting

The API implements rate limiting to ensure fair usage:

- **Default:** 100 requests per minute per API key
- **Burst:** Up to 200 requests in a short burst
- **Headers:** Rate limit info is returned in response headers:
  - `X-RateLimit-Limit`: Maximum requests per window
  - `X-RateLimit-Remaining`: Remaining requests
  - `X-RateLimit-Reset`: Time when limit resets

## 📊 Response Formats

### Success Response
```json
{
  "id": 1,
  "name": "Agent Name",
  "created_at": "2026-01-10T14:30:00Z",
  "data": {...}
}
```

### Error Response
```json
{
  "detail": "Error message",
  "error_code": "VALIDATION_ERROR",
  "timestamp": "2026-01-10T14:30:00Z"
}
```

### HTTP Status Codes

- `200 OK` - Successful GET/PUT request
- `201 Created` - Successful POST request
- `204 No Content` - Successful DELETE request
- `400 Bad Request` - Invalid request data
- `401 Unauthorized` - Missing or invalid authentication
- `403 Forbidden` - Insufficient permissions
- `404 Not Found` - Resource not found
- `429 Too Many Requests` - Rate limit exceeded
- `500 Internal Server Error` - Server error

## 🔧 Best Practices

### 1. Use API Keys for Integrations
For machine-to-machine communication, always use API keys instead of user credentials.

### 2. Handle Rate Limits Gracefully
```python
import time
import requests

def call_api_with_retry(url, headers, data, max_retries=3):
    for attempt in range(max_retries):
        response = requests.post(url, headers=headers, json=data)
        
        if response.status_code == 429:
            retry_after = int(response.headers.get('Retry-After', 60))
            time.sleep(retry_after)
            continue
            
        return response
    
    raise Exception("Max retries exceeded")
```

### 3. Use Appropriate Timeouts
```python
import requests

response = requests.post(
    'http://localhost:8000/api/agents/1/execute',
    json={'input': 'Hello'},
    timeout=30  # 30 second timeout
)
```

### 4. Validate Input Data
Always validate and sanitize input data before sending to the API.

### 5. Monitor API Usage
Use the monitoring endpoints to track API usage and performance.

## 🧪 Testing APIs

### Using cURL
```bash
curl -X GET http://localhost:8000/api/agents \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json"
```

### Using Python
```python
import requests

headers = {
    'Authorization': 'Bearer YOUR_TOKEN',
    'Content-Type': 'application/json'
}

response = requests.get(
    'http://localhost:8000/api/agents',
    headers=headers
)

print(response.json())
```

### Using Swagger UI

Visit [http://localhost:8000/docs](http://localhost:8000/docs) when running locally to test APIs interactively.

## 📖 Additional Resources

- **[GitHub Repository](https://github.com/Sathisha/multi-agent-orchestrator)** - Source code and examples
- **[Docker Hub](https://github.com/Sathisha/multi-agent-orchestrator/pkgs/container/multi-agent-orchestrator-backend)** - Pre-built Docker images
- **[Deployment Guide](DEPLOYMENT.md)** - Production deployment instructions

## 🆘 Support

For issues, questions, or contributions:
- Open an issue on [GitHub](https://github.com/Sathisha/multi-agent-orchestrator/issues)
- Check existing documentation and examples
- Review the [OpenAPI specification](https://sathisha.github.io/multi-agent-orchestrator/api/openapi.json)

---

**Last Updated:** January 2026  
**API Version:** v1  
**Status:** ✅ Production Ready
