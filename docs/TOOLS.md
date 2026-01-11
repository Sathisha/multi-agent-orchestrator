# Tools in the AI Agent Framework

This document explains how to create, use, and integrate tools with agents in the AI Agent Framework.

## Table of Contents

- [Overview](#overview)
- [Types of Tools](#types-of-tools)
- [Creating Custom Tools](#creating-custom-tools)
- [Using MCP Tools](#using-mcp-tools)
- [Adding Tools to Agents](#adding-tools-to-agents)
- [How Tool Execution Works](#how-tool-execution-works)
- [Testing Tools](#testing-tools)
- [Best Practices](#best-practices)

## Overview

Tools extend agent capabilities by allowing them to perform actions beyond text generation. Agents can:
- Perform calculations
- Access filesystems
- Make HTTP requests
- Query databases
- Execute custom Python code
- And more...

When an agent with tools receives a user request, it:
1. Analyzes the request to determine if a tool is needed
2. Selects the appropriate tool
3. Executes the tool with extracted parameters
4. Incorporates the tool results into the final response

## Types of Tools

### 1. Custom Tools

Custom tools are Python functions you write and register in the system. They execute in a sandboxed environment.

### 2. MCP Tools

MCP (Model Context Protocol) tools are provided by external servers following the MCP specification. The framework includes servers for:
- **Filesystem operations** (`@modelcontextprotocol/server-filesystem`)
- **HTTP requests** (`@modelcontextprotocol/server-fetch`)

## Creating Custom Tools

### Step 1: Define Tool Code

Create a Python function with the signature `execute(*args, **kwargs) -> dict`:

```python
def execute(operation: str, a: float, b: float) -> dict:
    '''Calculator tool for basic math operations.'''
    operations = {
        'add': lambda x, y: x + y,
        'subtract': lambda x, y: x - y,
        'multiply': lambda x, y: x * y,
        'divide': lambda x, y: x / y if y != 0 else None
    }
    
    if operation not in operations:
        return {'error': f'Unknown operation: {operation}'}
    
    result = operations[operation](a, b)
    
    if result is None:
        return {'error': 'Division by zero'}
    
    return {
        'operation': operation,
        'a': a,
        'b': b,
        'result': result
    }
```

### Step 2: Define Input Schema

Specify the expected parameters using JSON Schema:

```json
{
  "type": "object",
  "properties": {
    "operation": {
      "type": "string",
      "enum": ["add", "subtract", "multiply", "divide"],
      "description": "The mathematical operation to perform"
    },
    "a": {
      "type": "number",
      "description": "First operand"
    },
    "b": {
      "type": "number",
      "description": "Second operand"
    }
  },
  "required": ["operation", "a", "b"]
}
```

### Step 3: Register the Tool

#### Via API:

```bash
curl -X POST http://localhost:8001/api/v1/tools \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "calculator",
    "description": "Performs basic mathematical operations",
    "version": "1.0.0",
    "tool_type": "custom",
    "code": "def execute(operation: str, a: float, b: float) -> dict: ...",
    "input_schema": { ... },
    "output_schema": { ... },
    "category": "math",
    "tags": ["calculator", "math"],
    "timeout_seconds": 30
  }'
```

#### Via Python:

```python
from shared.services.tool_registry import ToolRegistryService
from shared.models.tool import ToolRequest, ToolType

tool_request = ToolRequest(
    name="calculator",
    description="Performs basic mathematical operations",
    tool_type=ToolType.CUSTOM,
    code=calculator_code,
    input_schema=input_schema,
    output_schema=output_schema,
    category="math",
    tags=["calculator", "math"],
    timeout_seconds=30
)

tool_service = ToolRegistryService(session)
tool = await tool_service.create_tool(
    user_id="user-id",
    tool_request=tool_request
)
```

## Using MCP Tools

MCP tools are automatically discovered when the `mcp-servers` container is running.

### Available MCP Servers

The framework includes these MCP servers by default:

#### 1. Filesystem Server
```json
{
  "name": "filesystem",
  "description": "Access to filesystem operations",
  "capabilities": ["read_file", "write_file", "list_directory"]
}
```

#### 2. Fetch Server
```json
{
  "name": "fetch",
  "description": "HTTP request capabilities",
  "capabilities": ["GET", "POST", "PUT", "DELETE"]
}
```

### Discovering MCP Tools

```bash
curl http://localhost:8001/api/v1/tools/discover/ \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Adding Tools to Agents

### Option 1: During Agent Creation

```bash
curl -X POST http://localhost:8001/api/v1/agents \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Math Assistant",
    "description": "An agent that can perform calculations",
    "type": "task",
    "status": "active",
    "system_prompt": "You are a helpful math assistant.",
    "config": {
      "model_name": "tinyllama",
      "llm_provider": "ollama",
      "temperature": 0.3,
      "max_tokens": 500
    },
    "available_tools": ["calculator-tool-id"]
  }'
```

### Option 2: Update Existing Agent

```bash
curl -X PUT http://localhost:8001/api/v1/agents/{agent_id} \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "available_tools": ["calculator-tool-id", "greeter-tool-id"]
  }'
```

## How Tool Execution Works

When an agent with tools receives a request:

1. **Analysis Phase**
   - The `ToolExecutorService` analyzes the user input
   - Determines if a tool is needed
   - Selects the appropriate tool

2. **Execution Phase**
   - Extracts parameters from the user input
   - Calls the tool via `ToolRegistryService`
   - Captures the tool result

3. **Integration Phase**
   - Formats tool results for context
   - Adds tool results to the system prompt
   - Calls the LLM with enriched context

4. **Response Phase**
   - LLM generates final response incorporating tool results
   - Returns complete response to user

### Example Flow

**User Input:** "What is 15 plus 27?"

**Agent Processing:**
```
1. Detect tool needed: calculator
2. Extract parameters: {operation: "add", a: 15, b: 27}
3. Execute tool → Result: {result: 42}
4. Add to context: "Tool Execution Results: calculator returned 42"
5. LLM Response: "The sum of 15 and 27 is 42."
```

## Testing Tools

### Test Tool Directly

```bash
# Create tool
TOOL_ID=$(curl -X POST http://localhost:8001/api/v1/tools \
  -H "Authorization: Bearer $TOKEN" \
  -d @calculator_tool.json | jq -r '.id')

# Execute tool
curl -X POST "http://localhost:8001/api/v1/tools/$TOOL_ID/execute" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "inputs": {"operation": "add", "a": 5, "b": 3}
  }'
```

### Test Tool with Agent

```bash
# Create agent with tool
AGENT_ID=$(curl -X POST http://localhost:8001/api/v1/agents \
  -H "Authorization: Bearer $TOKEN" \
  -d @math_agent.json | jq -r '.id')

# Execute agent
curl -X POST "http://localhost:8001/api/v1/agents/$AGENT_ID/execute" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "input_data": {"message": "Calculate 8 times 9"}
  }'
```

### Automated Tests

Run the tool test suite:

```bash
# Run all tool tests
make test-tools

# Run specific test file
docker-compose exec backend pytest tests/integration/test_tool_execution.py -v

# Run specific test
docker-compose exec backend pytest tests/integration/test_agent_with_tools.py::TestAgentWithTools::test_agent_uses_calculator_for_addition -v
```

## Best Practices

### 1. Tool Design

- **Single Responsibility**: Each tool should do one thing well
- **Clear Descriptions**: Help the routing logic select the right tool
- **Structured Output**: Always return a dict with predictable keys
- **Error Handling**: Return `{"error": "message"}` for failures

### 2. Input Schemas

- **Be Specific**: Use enums for limited choices
- **Provide Descriptions**: Help parameter extraction
- **Set Defaults**: Where appropriate
- **Validate Types**: Use proper JSON Schema types

### 3. Security

- **Timeout Limits**: Set appropriate timeouts (default: 30s)
- **Input Validation**: Validate all inputs in your tool code
- **Resource Limits**: Be mindful of resource usage
- **Sandboxing**: Custom tools run in isolated environments

### 4. Performance

- **Keep Tools Fast**: Aim for <1 second execution time
- **Cache When Possible**: Store frequently accessed data
- **Async Operations**: Use async/await for I/O operations
- **Batch When Possible**: Design tools to handle multiple items

### 5. Testing

- **Unit Test Tools**: Test tools independently first
- **Integration Test Agents**: Test agents with tools together
- **Test Error Cases**: Ensure graceful error handling
- **Test Edge Cases**: Empty inputs, large inputs, etc.

### 6. Agent Configuration

- **Choose Right Model**: Match model capability to complexity
- **System Prompts**: Guide the agent on tool usage
- **Temperature**: Lower for tool-heavy agents (0.3-0.5)
- **Max Tokens**: Ensure enough for tool results + response

## Troubleshooting

### Tool Not Being Called

**Symptom**: Agent doesn't use available tools

**Causes**:
- Tool description doesn't match user input
- Tool not in agent's `available_tools` list
- Routing logic not detecting need for tool

**Solution**:
- Improve tool description with keywords
- Check agent configuration
- Review logs for routing decisions

### Tool Execution Failures

**Symptom**: Tool executes but returns errors

**Causes**:
- Invalid parameters
- Tool timeout
- Runtime errors in tool code

**Solution**:
- Test tool directly with known inputs
- Check tool code for bugs
- Increase timeout if needed
- Review error logs

### MCP Tools Not Available

**Symptom**: MCP tools not discovered

**Causes**:
- `mcp-servers` container not running
- MCP server configuration issues
- Network connectivity problems

**Solution**:
```bash
# Check MCP container status
docker-compose ps mcp-servers

# View MCP container logs
docker-compose logs mcp-servers

# Restart MCP services
docker-compose restart mcp-servers
```

## Examples

### Example 1: Weather Tool

```python
import requests

def execute(city: str) -> dict:
    '''Get current weather for a city.'''
    try:
        # Using a weather API (example)
        api_key = "YOUR_API_KEY"
        url = f"https://api.weather.com/v1/weather?city={city}&key={api_key}"
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            return {
                "city": city,
                "temperature": data["temp"],
                "conditions": data["conditions"],
                "humidity": data["humidity"]
            }
        else:
            return {"error": f"Weather API error: {response.status_code}"}
    
    except Exception as e:
        return {"error": str(e)}
```

### Example 2: Database Query Tool

```python
import psycopg2

def execute(query: str) -> dict:
    '''Execute a read-only database query.'''
    if not query.strip().upper().startswith('SELECT'):
        return {"error": "Only SELECT queries allowed"}
    
    try:
        conn = psycopg2.connect("postgresql://user:pass@host/db")
        cursor = conn.cursor()
        cursor.execute(query)
        
        results = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        
        cursor.close()
        conn.close()
        
        return {
            "columns": columns,
            "rows": results,
            "count": len(results)
        }
    
    except Exception as e:
        return {"error": str(e)}
```

## Further Reading

- [MCP Specification](https://github.com/anthropics/anthropic-sdk-python/tree/main/mcp)
- [Tool Registry API Documentation](http://localhost:8001/docs#/Tool%20Registry)
- [Agent API Documentation](http://localhost:8001/docs#/Agents)
