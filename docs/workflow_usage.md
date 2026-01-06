# Workflow Usage Guide

This guide explains how to create, test, and use workflows (chains) in the AI Agent Framework, both through the UI and programmatically via API.

---

## Table of Contents
1. [Creating a Workflow](#creating-a-workflow)
2. [Testing a Workflow](#testing-a-workflow)
3. [Using Workflows via API](#using-workflows-via-api)
4. [API Key Management](#api-key-management)
5. [Code Examples](#code-examples)
6. [Troubleshooting](#troubleshooting)

---

## Creating a Workflow

### Via UI
1. Navigate to **Workflows** in the left sidebar
2. Click **"New Workflow"** button
3. Configure your workflow:
   - **Name**: Give your workflow a descriptive name
   - **Description**: Add details about what the workflow does
   - **Category**: Optional categorization
   - **Tags**: Add searchable tags

### Adding Nodes
1. Drag and drop nodes from the node palette onto the canvas:
   - **Start Node**: Entry point for the workflow
   - **Agent Node**: Execute an AI agent task
   - **Conditional Node**: Branch logic based on conditions
   - **Parallel Split/Join**: Run multiple agents concurrently
   - **End Node**: Exit point for the workflow

2. Configure each node by clicking on it:
   - **Agent Nodes**: Select which agent to execute
   - **Conditional Nodes**: Define branching logic
   - **Input/Output Mapping**: Configure data flow

### Connecting Nodes
1. Click and drag from an output handle to an input handle
2. Add edge labels to describe the connection
3. For conditional edges, specify the condition expression

### Saving
Click **"Save"** to persist your workflow. The workflow must have at least a Start and End node to be valid.

---

## Testing a Workflow

### Using the Test Button
1. Open your workflow in the editor
2. Click **"Test Workflow"** button in the top toolbar
3. In the test dialog:
   - **Input Data**: Provide JSON input for the workflow
   - **Execution Name**: Optional name for this test run
   - **Variables**: Optional runtime variables

4. Click **"Execute"**
5. Monitor execution progress in real-time:
   - Node states are color-coded (pending, running, completed, failed)
   - View execution logs
   - Check output data when completed

### Viewing Execution History
1. Navigate to the **Executions** tab in the workflow detail view
2. Click on any execution to see:
   - Execution status and duration
   - Input and output data
   - Detailed logs for each node
   - Error messages if failed

---

## Using Workflows via API

### Overview
Workflows can be executed programmatically using REST API with API Key authentication. This is ideal for:
- Integration with external systems
- Scheduled/automated execution
- Webhook triggers
- CI/CD pipelines

### Getting Started

#### 1. Obtain API Endpoint
1. Open your workflow in the UI
2. Click **"Use as API"** button
3. Copy the API endpoint URL:
   ```
   POST http://localhost:8000/api/v1/chains/{chain_id}/execute
   ```

#### 2. Generate API Key
1. In the "Use as API" modal, click **"Generate New API Key"**
2. Provide a name (e.g., "Production Integration")
3. **IMPORTANT**: Copy the API key immediately - it's shown only once!
4. Store the key securely (environment variables, secrets manager, etc.)

#### 3. Make API Calls
Use the `X-API-Key` header to authenticate your requests:

```bash
curl -X POST "http://localhost:8000/api/v1/chains/{chain_id}/execute" \
  -H "X-API-Key: your-api-key-here" \
  -H "Content-Type: application/json" \
  -d '{
    "input_data": {
      "query": "What is the weather today?"
    },
    "execution_name": "API Test Run",
    "variables": {}
  }'
```

#### Response
```json
{
  "id": "execution-uuid",
  "chain_id": "chain-uuid",
  "status": "pending",
  "input_data": {...},
  "created_at": "2026-01-06T05:30:00Z"
}
```

Status code: `202 Accepted` (execution started asynchronously)

---

## API Key Management

### Creating API Keys
1. Open workflow → Click **"Use as API"**
2. Click **"Generate New API Key"**
3. Enter a descriptive name
4. Copy and securely store the key

### Viewing Existing Keys
In the "Use as API" modal, you'll see a list of active keys with:
- Key name
- Key prefix (first 8 characters)
- Creation date
- Last used timestamp

### Revoking API Keys
1. Find the key in the list
2. Click **"Revoke"**
3. Confirm revocation
4. The key will immediately stop working

### Best Practices
- **Rotate keys regularly**: Generate new keys every 90 days
- **Use descriptive names**: Indicate the purpose/system using the key
- **Limit scope**: Create separate keys for each integration
- **Secure storage**: Never commit keys to source control
- **Monitor usage**: Check "Last Used" timestamps for anomalies

---

## Code Examples

### cURL
```bash
curl -X POST "http://localhost:8000/api/v1/chains/abc-123/execute" \
  -H "X-API-Key: sk_live_1234567890abcdef" \
  -H "Content-Type: application/json" \
  -d '{
    "input_data": {"message": "Hello"},
    "execution_name": "cURL Test"
  }'
```

### Python
```python
import requests

API_KEY = "sk_live_1234567890abcdef"
CHAIN_ID = "abc-123"
BASE_URL = "http://localhost:8000"

def execute_workflow(input_data):
    url = f"{BASE_URL}/api/v1/chains/{CHAIN_ID}/execute"
    headers = {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "input_data": input_data,
        "execution_name": "Python Script Execution"
    }
    
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()

# Execute
result = execute_workflow({"query": "Analyze this data"})
print(f"Execution ID: {result['id']}")
print(f"Status: {result['status']}")

# Poll for completion
execution_id = result['id']
status_url = f"{BASE_URL}/api/v1/chains/executions/{execution_id}/status"
status_response = requests.get(status_url, headers=headers)
print(status_response.json())
```

### JavaScript (Node.js)
```javascript
const axios = require('axios');

const API_KEY = 'sk_live_1234567890abcdef';
const CHAIN_ID = 'abc-123';
const BASE_URL = 'http://localhost:8000';

async function executeWorkflow(inputData) {
  try {
    const response = await axios.post(
      `${BASE_URL}/api/v1/chains/${CHAIN_ID}/execute`,
      {
        input_data: inputData,
        execution_name: 'Node.js Execution'
      },
      {
        headers: {
          'X-API-Key': API_KEY,
          'Content-Type': 'application/json'
        }
      }
    );
    
    console.log('Execution ID:', response.data.id);
    console.log('Status:', response.data.status);
    return response.data;
  } catch (error) {
    console.error('Error:', error.response?.data || error.message);
    throw error;
  }
}

// Execute
executeWorkflow({ message: 'Hello from Node.js' });
```

### Polling for Execution Status
```python
import time
import requests

def poll_execution_status(execution_id, api_key, max_wait=300, interval=5):
    """Poll execution status until completion or timeout."""
    url = f"http://localhost:8000/api/v1/chains/executions/{execution_id}/status"
    headers = {"X-API-Key": api_key}
    
    start_time = time.time()
    while time.time() - start_time < max_wait:
        response = requests.get(url, headers=headers)
        data = response.json()
        
        status = data['status']
        print(f"Status: {status} ({data['progress_percentage']:.1f}%)")
        
        if status in ['completed', 'failed', 'cancelled']:
            return data
        
        time.sleep(interval)
    
    raise TimeoutError(f"Execution did not complete within {max_wait}s")

# Usage
execution = execute_workflow({"query": "test"})
final_status = poll_execution_status(execution['id'], API_KEY)
print(f"Final status: {final_status['status']}")
```

---

## Troubleshooting

### Authentication Errors

**401 Unauthorized: Invalid or expired API Key**
- Verify the API key is correct
- Check if the key has been revoked
- Ensure the `X-API-Key` header is set correctly

**403 Forbidden: Missing authentication credentials**
- Add the `X-API-Key` header to your request
- Check for typos in the header name (case-sensitive)

### Execution Errors

**400 Bad Request: Invalid input data**
- Verify your `input_data` matches the workflow's expected schema
- Check JSON formatting is correct
- Review workflow input schema definition

**404 Not Found: Chain not found**
- Verify the chain ID in the URL is correct
- Ensure the workflow exists and is not deleted

**500 Internal Server Error**
- Check backend logs for detailed error messages
- Verify all agent nodes have valid agent references
- Ensure workflow is properly validated before execution

### Common Issues

**Execution stuck in "pending" status**
- Check if the backend service is running
- Review backend logs for worker errors
- Verify database connectivity

**Slow execution**
- Review node configurations for inefficiencies
- Check if parallel nodes can be used
- Monitor LLM API rate limits

**Execution fails silently**
- Check execution logs in the UI
- Review agent configurations
- Verify agent LLM models are accessible

---

## Additional Resources

- **API Documentation**: Visit `http://localhost:8000/docs` for interactive API documentation
- **Agent Configuration**: See `docs/agent_usage.md` for configuring agents
- **LLM Models**: See `docs/llm_models.md` for supported model providers
- **Self-Hosting**: See `docs/deployment.md` for production deployment guides

---

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review backend logs: `docker compose logs backend`
3. Open an issue on GitHub with:
   - Workflow configuration
   - Execution logs
   - Error messages
   - Steps to reproduce
