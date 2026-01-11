# Quick Start: Using Built-in Tools with Agents

## 1. Register Built-in Tools (One-time setup)

After deploying the application, register all built-in tools:

```bash
make setup-tools
```

This will register:
- **web_search** - Internet search via DuckDuckGo (no API key)
- **calculator** - Perform basic math operations
- **http_fetch** - Fetch content from any URL
- **wikipedia** - Search Wikipedia
- **datetime** - Get current date/time in any timezone
- **json_parser** - Parse and extract JSON data

## 2. Create an Agent with Tools

```bash
# Get authentication token
TOKEN="your_auth_token"

# Get web_search tool ID
SEARCH_TOOL_ID=$(curl -s http://localhost:8001/api/v1/tools \
  -H "Authorization: Bearer $TOKEN" | \
  jq -r '.[] | select(.name=="web_search") | .id')

# Create research agent
curl -X POST http://localhost:8001/api/v1/agents \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"Research Assistant\",
    \"description\": \"An agent that can search the web for information\",
    \"type\": \"task\",
    \"status\": \"active\",
    \"system_prompt\": \"You are a research assistant. When users ask questions, use web search to find current, accurate information. Always cite your sources.\",
    \"config\": {
      \"model_name\": \"llama3:8b\",
      \"llm_provider\": \"ollama\",
      \"temperature\": 0.3,
      \"max_tokens\": 1000
    },
    \"available_tools\": [\"$SEARCH_TOOL_ID\"]
  }"
```

## 3. Test the Agent

```bash
# Get agent ID from creation response
AGENT_ID="agent-id-from-above"

# Ask a question that requires web search
curl -X POST "http://localhost:8001/api/v1/agents/$AGENT_ID/execute" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "input_data": {
      "message": "What are the latest developments in quantum computing?"
    }
  }'
```

The agent will:
1. Detect that web search is needed
2. Execute the web_search tool
3. Get current search results
4. Generate a response incorporating the search results

## 4. Add More Tools to an Agent

```bash
# Get Wikipedia tool ID
WIKI_TOOL_ID=$(curl -s http://localhost:8001/api/v1/tools \
  -H "Authorization: Bearer $TOKEN" | \
  jq -r '.[] | select(.name=="wikipedia") | .id')

# Update agent with multiple tools
curl -X PUT "http://localhost:8001/api/v1/agents/$AGENT_ID" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"available_tools\": [\"$SEARCH_TOOL_ID\", \"$WIKI_TOOL_ID\"]
  }"
```

## 5. List All Available Tools

```bash
curl http://localhost:8001/api/v1/tools \
  -H "Authorization: Bearer $TOKEN" | jq '.[] | {name, description, category}'
```

## 6. Test a Tool Directly

```bash
# Test web search tool directly
curl -X POST "http://localhost:8001/api/v1/tools/$SEARCH_TOOL_ID/execute" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "inputs": {
      "query": "artificial intelligence 2026",
      "num_results": 5
    }
  }'
```

## Available Tools Summary

| Tool | Description | API Key Required |
|------|-------------|------------------|
| web_search | DuckDuckGo internet search | ❌ No |
| calculator | Basic math operations | ❌ No |
| http_fetch | Fetch content from URLs | ❌ No |
| wikipedia | Search Wikipedia articles | ❌ No |
| datetime | Get current date/time | ❌ No |
| json_parser | Parse JSON data | ❌ No |

## Next Steps

- See [AVAILABLE_TOOLS.md](AVAILABLE_TOOLS.md) for tools that require API keys (Google Search, Weather, News, etc.)
- See [TOOLS.md](TOOLS.md) for creating custom tools
- Check the walkthrough for advanced usage patterns
