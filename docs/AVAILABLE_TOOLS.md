# Available Tools in AI Agent Framework

## Currently Integrated Tools

### 1. **Calculator**
- **Name**: `calculator`
- **Description**: Perform basic mathematical operations
- **API Key Required**: ❌ No
- **Capabilities**: Add, subtract, multiply, divide
- **Example Use**: "What is 15 * 27?"

### 2. **Web Search** (DuckDuckGo)
- **Name**: `web_search`
- **Description**: Search the internet using DuckDuckGo
- **API Key Required**: ❌ No (uses free DuckDuckGo API)
- **Configuration**: None required, works out of the box
- **Capabilities**: 
  - Search queries
  - Returns titles, snippets, and URLs
  - Up to 10 results per query
- **Example Use**: "Search for latest Python tutorials"

### 2. **HTTP Fetch**
- **Name**: `http_fetch`
- **Description**: Fetch and extract content from any URL
- **API Key Required**: ❌ No
- **Configuration**: None required
- **Capabilities**:
  - GET requests to any URL
  - Automatic text extraction from HTML
  - Content type detection
- **Example Use**: "Get the content from https://example.com"

### 3. **Wikipedia**
- **Name**: `wikipedia`
- **Description**: Search Wikipedia and get article summaries
- **API Key Required**: ❌ No (uses free Wikipedia API)
- **Configuration**: None required
- **Capabilities**:
  - Search articles
  - Get summaries (customizable length)
  - Direct article URLs
- **Example Use**: "What is quantum computing according to Wikipedia?"

### 4. **DateTime**
- **Name**: `datetime`
- **Description**: Get current date and time in any timezone
- **API Key Required**: ❌ No
- **Configuration**: None required
- **Capabilities**:
  - Multiple timezone support
  - Custom formatting
  - Timestamp conversion
- **Example Use**: "What time is it in Tokyo?"

### 5. **JSON Parser**
- **Name**: `json_parser`
- **Description**: Parse and extract data from JSON
- **API Key Required**: ❌ No
- **Configuration**: None required
- **Capabilities**:
  - Parse JSON strings
  - Extract nested data using dot notation
  - Validation
- **Example Use**: "Parse this JSON and get user.address.city"

---

## How to Enable Built-in Tools

### Step 1: Register Tools (One-time setup)

Run this script to register all built-in tools:

```bash
docker-compose exec backend python -c "
from shared.services.builtin_tools import BUILTIN_TOOLS
from shared.services.tool_registry import ToolRegistryService
from shared.database.connection import AsyncSessionLocal
from shared.models.tool import ToolRequest
import asyncio

async def register_builtin_tools():
    async with AsyncSessionLocal() as session:
        tool_service = ToolRegistryService(session)
        
        for tool_data in BUILTIN_TOOLS:
            tool_request = ToolRequest(**tool_data)
            try:
                tool = await tool_service.create_tool(
                    user_id='system',
                    tool_request=tool_request
                )
                print(f'✅ Registered: {tool.name}')
            except Exception as e:
                print(f'⚠️  {tool_data[\"name\"]}: {e}')

asyncio.run(register_builtin_tools())
"
```

### Step 2: Add Tools to Agents

```bash
# Get tool IDs
curl http://localhost:8001/api/v1/tools \
  -H "Authorization: Bearer $TOKEN" | jq '.[] | {id, name}'

# Update agent with tools
curl -X PUT http://localhost:8001/api/v1/agents/$AGENT_ID \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "available_tools": ["web_search_tool_id", "wikipedia_tool_id"]
  }'
```

---

## Additional Tools Available (Require API Keys)

### 1. **Google Search** (Recommended for Production)
- **API**: Google Custom Search JSON API
- **Free Tier**: 100 queries/day
- **Paid**: $5 per 1000 queries after free tier
- **How to Get Key**:
  1. Go to [Google Cloud Console](https://console.cloud.google.com/)
  2. Create a project
  3. Enable "Custom Search API"
  4. Create credentials (API Key)
  5. Create a Custom Search Engine at [CSE Control Panel](https://programmablesearchengine.google.com/)
- **Environment Variable**: `GOOGLE_SEARCH_API_KEY`, `GOOGLE_SEARCH_ENGINE_ID`

**Tool Code Template**:
```python
def execute(query: str) -> dict:
    api_key = os.getenv('GOOGLE_SEARCH_API_KEY')
    engine_id = os.getenv('GOOGLE_SEARCH_ENGINE_ID')
    url = f'https://www.googleapis.com/customsearch/v1?key={api_key}&cx={engine_id}&q={query}'
    response = requests.get(url)
    return response.json()
```

### 2. **Weather Data** (OpenWeatherMap)
- **API**: OpenWeatherMap API
- **Free Tier**: 1000 calls/day  
- **How to Get Key**:
  1. Go to [OpenWeatherMap](https://openweathermap.org/api)
  2. Sign up for free account
  3. Generate API key in account settings
- **Environment Variable**: `OPENWEATHER_API_KEY`

### 3. **News Articles** (NewsAPI)
- **API**: NewsAPI.org
- **Free Tier**: 100 requests/day, articles up to 1 month old
- **How to Get Key**:
  1. Visit [NewsAPI](https://newsapi.org/)
  2. Get free API key
- **Environment Variable**: `NEWS_API_KEY`

### 4. **Email Sending** (SendGrid)
- **API**: SendGrid Email API
- **Free Tier**: 100 emails/day
- **How to Get Key**:
  1. Sign up at [SendGrid](https://sendgrid.com/)
  2. Create API key in Settings > API Keys
- **Environment Variable**: `SENDGRID_API_KEY`

### 5. **Translation** (Google Translate)
- **API**: Google Cloud Translation API
- **Free Tier**: First 500,000 characters/month
- **How to Get Key**:
  1. Google Cloud Console
  2. Enable Cloud Translation API
  3. Create service account key
- **Environment Variable**: `GOOGLE_TRANSLATE_API_KEY`

### 6. **Speech-to-Text** (OpenAI Whisper)
- **API**: OpenAI Whisper API
- **Pricing**: $0.006 per minute
- **How to Get Key**:
  1. Go to [OpenAI Platform](https://platform.openai.com/)
  2. Create API key
- **Environment Variable**: `OPENAI_API_KEY`

### 7. **Image Generation** (DALL-E or Stable Diffusion)
- **API**: OpenAI DALL-E or Stability AI
- **Pricing**: Varies
- **How to Get Key**:
  - OpenAI: Same as above
  - Stability AI: [DreamStudio](https://dreamstudio.ai/)
- **Environment Variable**: `OPENAI_API_KEY` or `STABILITY_API_KEY`

### 8. **Database Queries** (Built-in PostgreSQL)
- **API**: Direct database connection
- **Configuration**: Already configured in docker-compose
- **Environment Variable**: `DATABASE_URL` (already set)

---

## Useful Tools to Add

### High Priority

1. **Web Search (Google)** - More accurate than DuckDuckGo
2. **Weather** - Real-time weather information
3. **News** - Latest news articles
4. **Email** - Send notifications and emails

### Medium Priority

5. **File Operations** - Read/write local files
6. **Database Queries** - Query your PostgreSQL database
7. **Translation** - Multi-language support
8. **Calendar** - Schedule and reminder management

### Nice to Have

9. **Image Generation** - Create images from descriptions
10. **Speech-to-Text** - Transcribe audio
11. **PDF Parser** - Extract text from PDFs
12. **Slack/Teams Integration** - Chat notifications

---

## Configuration Example

### Add API Keys to Docker Compose

Edit `docker-compose.yml`:

```yaml
backend:
  environment:
    # Existing vars...
    - GOOGLE_SEARCH_API_KEY=${GOOGLE_SEARCH_API_KEY}
    - GOOGLE_SEARCH_ENGINE_ID=${GOOGLE_SEARCH_ENGINE_ID}
    - OPENWEATHER_API_KEY=${OPENWEATHER_API_KEY}
    - NEWS_API_KEY=${NEWS_API_KEY}
    - SENDGRID_API_KEY=${SENDGRID_API_KEY}
```

### Create `.env` File

```bash
# .env file in project root
GOOGLE_SEARCH_API_KEY=your_key_here
GOOGLE_SEARCH_ENGINE_ID=your_engine_id
OPENWEATHER_API_KEY=your_key_here
NEWS_API_KEY=your_key_here
SENDGRID_API_KEY=your_key_here
```

---

## Testing Tools

### Test Web Search

```bash
# Get web_search tool ID
TOOL_ID=$(curl -s http://localhost:8001/api/v1/tools \
  -H "Authorization: Bearer $TOKEN" | \
  jq -r '.[] | select(.name=="web_search") | .id')

# Execute search
curl -X POST "http://localhost:8001/api/v1/tools/$TOOL_ID/execute" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "inputs": {
      "query": "latest AI developments 2026",
      "num_results": 5
    }
  }'
```

### Test Wikipedia

```bash
TOOL_ID=$(curl -s http://localhost:8001/api/v1/tools \
  -H "Authorization: Bearer $TOKEN" | \
  jq -r '.[] | select(.name=="wikipedia") | .id')

curl -X POST "http://localhost:8001/api/v1/tools/$TOOL_ID/execute" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "inputs": {
      "query": "Artificial Intelligence",
      "sentences": 5
    }
  }'
```

### Test with Agent

```bash
# Create agent with web search capability
curl -X POST http://localhost:8001/api/v1/agents \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "name": "Research Assistant",
    "description": "Agent that can search the web",
    "type": "task",
    "status": "active",
    "system_prompt": "You are a research assistant. Use web search to find current information.",
    "config": {
      "model_name": "llama3:8b",
      "llm_provider": "ollama"
    },
    "available_tools": ["'$TOOL_ID'"]
  }'

# Ask agent to search
curl -X POST "http://localhost:8001/api/v1/agents/$AGENT_ID/execute" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "input_data": {
      "message": "What are the latest developments in quantum computing?"
    }
  }'
```

---

## Summary

**Currently Available (No API Key)**:
- ✅ Web Search (DuckDuckGo)
- ✅ HTTP Fetch
- ✅ Wikipedia
- ✅ DateTime
- ✅ JSON Parser

**Easy to Add (Free/Cheap API Keys)**:
- Google Search (best for production)
- Weather (OpenWeatherMap)
- News (NewsAPI)
- Email (SendGrid)

**Main Internet Search Capability**: ✅ Already available via DuckDuckGo (no key required) or upgrade to Google Custom Search for better results.
