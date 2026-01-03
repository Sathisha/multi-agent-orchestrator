"""
Seed script to create admin user and sample data for testing.
"""
import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import select
from shared.database.connection import AsyncSessionLocal
from shared.models.user import User
from shared.models.agent import Agent, AgentType, AgentStatus
from shared.models.workflow import Workflow, WorkflowStatus
from shared.models.tool import Tool, ToolType, ToolStatus, MCPServer, MCPServerStatus
from shared.services.auth import AuthService
import uuid


async def create_admin_user():
    """Create admin user: admin/admin"""
    async with AsyncSessionLocal() as session:
        auth_service = AuthService(session)
        
        # Check if admin exists
        result = await session.execute(select(User).where(User.email == "admin@example.com"))
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            print("✓ Admin user already exists")
            return existing_user
        
        # Create admin user
        user = await auth_service.register_user(
            email="admin@example.com",
            password="admin",
            full_name="Admin User"
        )
        
        # Set as system admin
        user.is_system_admin = True
        await session.commit()
        
        print("✓ Created admin user: admin@example.com / admin")
        return user


async def create_sample_agents(user_id: uuid.UUID):
    """Create sample agents"""
    async with AsyncSessionLocal() as session:
        # Check if agents exist
        result = await session.execute(select(Agent))
        if result.scalars().first():
            print("✓ Sample agents already exist")
            return
        
        agents = [
            Agent(
                id=uuid.uuid4(),
                name="Customer Support Bot",
                description="AI assistant for handling customer inquiries and support tickets",
                type=AgentType.CONVERSATIONAL,
                status=AgentStatus.ACTIVE,
                version="1.0",
                system_prompt="You are a helpful customer support assistant. Be polite, professional, and solve customer issues efficiently.",
                config={
                    "model": "gpt-4",
                    "temperature": 0.7,
                    "max_tokens": 2000
                },
                available_tools=["Weather Checker", "Wikipedia Search", "Internet Search", "Time & Date"],
                created_by=user_id,
                updated_by=user_id
            ),
            Agent(
                id=uuid.uuid4(),
                name="Research Assistant",
                description="Helps with research tasks, finding information, and data analysis",
                type=AgentType.TASK,
                status=AgentStatus.ACTIVE,
                version="1.0",
                system_prompt="You are a research assistant. Help users find accurate information, analyze data, and provide well-sourced answers.",
                config={
                    "model": "gpt-4",
                    "temperature": 0.3,
                    "max_tokens": 3000
                },
                available_tools=["Wikipedia Search", "Internet Search", "Calculator", "JSON Parser"],
                capabilities=["research", "data_analysis", "fact_checking"],
                tags=["research", "information"],
                created_by=user_id,
                updated_by=user_id
            ),
            Agent(
                id=uuid.uuid4(),
                name="Content Writer",
                description="Creates engaging blog posts and marketing content",
                type=AgentType.CONVERSATIONAL,
                status=AgentStatus.DRAFT,
                version="1.0",
                system_prompt="You are a creative content writer. Write engaging, SEO-optimized content.",
                config={
                    "model": "gpt-3.5-turbo",
                    "temperature": 0.9,
                    "max_tokens": 2500
                },
                available_tools=["Wikipedia Search", "Internet Search", "Text Transformer"],
                capabilities=["writing", "seo", "marketing"],
                tags=["content", "marketing"],
                created_by=user_id,
                updated_by=user_id
            ),
            Agent(
                id=uuid.uuid4(),
                name="Data Analyst",
                description="Analyzes datasets and generates insights",
                type=AgentType.TASK,
                status=AgentStatus.ACTIVE,
                version="1.0",
                system_prompt="You are a data analyst. Analyze data, identify patterns, and provide actionable insights.",
                config={
                    "model": "gpt-4",
                    "temperature": 0.2,
                    "max_tokens": 2000
                },
                available_tools=["Calculator", "JSON Parser", "HTTP Request", "File Hash Calculator"],
                capabilities=["data_analysis", "visualization", "reporting"],
                tags=["analytics", "data"],
                created_by=user_id,
                updated_by=user_id
            ),
        ]
        
        for agent in agents:
            session.add(agent)
        
        await session.commit()
        print(f"✓ Created {len(agents)} sample agents")


async def create_sample_workflows(user_id: uuid.UUID):
    """Create sample workflows"""
    async with AsyncSessionLocal() as session:
        # Check if workflows exist
        result = await session.execute(select(Workflow))
        if result.scalars().first():
            print("✓ Sample workflows already exist")
            return
        
        workflows = [
            Workflow(
                id=uuid.uuid4(),
                name="Customer Onboarding",
                description="Automated workflow for onboarding new customers",
                version="1.0",
                status=WorkflowStatus.ACTIVE,
                process_definition_key="customer_onboarding",
                bpmn_xml='<?xml version="1.0" encoding="UTF-8"?><definitions></definitions>',
                category="customer_management",
                tags=["onboarding", "automation"],
                input_schema={"type": "object", "properties": {"customer_email": {"type": "string"}}},
                output_schema={"type": "object", "properties": {"status": {"type": "string"}}},
                created_by=user_id,
                updated_by=user_id
            ),
            Workflow(
                id=uuid.uuid4(),
                name="Content Review Pipeline",
                description="Multi-stage content review and approval workflow",
                version="1.0",
                status=WorkflowStatus.DRAFT,
                process_definition_key="content_review",
                bpmn_xml='<?xml version="1.0" encoding="UTF-8"?><definitions></definitions>',
                category="content",
                tags=["review", "content"],
                created_by=user_id,
                updated_by=user_id
            ),
            Workflow(
                id=uuid.uuid4(),
                name="Data Processing Pipeline",
                description="ETL workflow for processing and analyzing data",
                version="1.0",
                status=WorkflowStatus.ACTIVE,
                process_definition_key="data_pipeline",
                bpmn_xml='<?xml version="1.0" encoding="UTF-8"?><definitions></definitions>',
                category="data",
                tags=["etl", "analytics"],
                created_by=user_id,
                updated_by=user_id
            ),
        ]
        
        for workflow in workflows:
            session.add(workflow)
        
        await session.commit()
        print(f"✓ Created {len(workflows)} sample workflows")


async def create_sample_tools(user_id: uuid.UUID):
    """Create sample tools"""
    async with AsyncSessionLocal() as session:
        # Check if tools exist
        result = await session.execute(select(Tool))
        if result.scalars().first():
            print("✓ Sample tools already exist")
            return
        
        tools = [
            # Enhanced Tool #1: Weather Checker
            Tool(
                id=uuid.uuid4(),
                name="Weather Checker",
                description="Get real-time weather information for any location worldwide using the Open-Meteo API. Provides temperature, wind speed, and weather conditions.",
                version="1.0.0",
                tool_type=ToolType.CUSTOM,
                status=ToolStatus.ACTIVE,
                code="""def execute(inputs, context=None):
    import httpx
    from urllib.parse import quote
    
    location = inputs.get('location')
    if not location:
        return {"error": "Location is required"}
    
    try:
        # Get coordinates from location name
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={quote(location)}&count=1&language=en&format=json"
        
        with httpx.Client(timeout=10.0) as client:
            geo_res = client.get(geo_url)
            geo_res.raise_for_status()
            geo_data = geo_res.json()
            
            if not geo_data.get('results'):
                return {"error": f"Location not found: {location}"}
            
            location_data = geo_data['results'][0]
            lat, lon = location_data['latitude'], location_data['longitude']
            location_name = f"{location_data.get('name', '')}, {location_data.get('country', '')}"
            
            # Get weather data
            weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true&timezone=auto"
            weather_res = client.get(weather_url)
            weather_res.raise_for_status()
            weather_data = weather_res.json()
            
            current = weather_data['current_weather']
            
            # Weather code descriptions
            weather_codes = {
                0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
                45: "Foggy", 48: "Depositing rime fog", 51: "Light drizzle", 53: "Moderate drizzle",
                55: "Dense drizzle", 61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
                71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow", 95: "Thunderstorm"
            }
            
            return {
                "success": True,
                "location": location_name,
                "temperature_celsius": current['temperature'],
                "temperature_fahrenheit": round(current['temperature'] * 9/5 + 32, 1),
                "windspeed_kmh": current['windspeed'],
                "weather_code": current['weathercode'],
                "weather_description": weather_codes.get(current['weathercode'], "Unknown"),
                "time": current['time']
            }
    except httpx.HTTPError as e:
        return {"error": f"Weather service error: {str(e)}"}
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}""",
                entry_point="execute",
                input_schema={
                    "type": "object",
                    "properties": {
                        "location": {"type": "string", "description": "City name or location (e.g., 'London', 'New York', 'Tokyo')"}
                    },
                    "required": ["location"]
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "success": {"type": "boolean"},
                        "location": {"type": "string"},
                        "temperature_celsius": {"type": "number"},
                        "temperature_fahrenheit": {"type": "number"},
                        "windspeed_kmh": {"type": "number"},
                        "weather_code": {"type": "integer"},
                        "weather_description": {"type": "string"},
                        "time": {"type": "string"},
                        "error": {"type": "string"}
                    }
                },
                category="information",
                tags=["weather", "api", "real-time", "open-meteo"],
                capabilities=["weather_lookup", "location_search"],
                created_by=user_id,
                updated_by=user_id
            ),
            
            # Enhanced Tool #2: Wikipedia Search
            Tool(
                id=uuid.uuid4(),
                name="Wikipedia Search",
                description="Search and retrieve article summaries from Wikipedia. Returns title, extract, and link to the full article.",
                version="1.0.0",
                tool_type=ToolType.CUSTOM,
                status=ToolStatus.ACTIVE,
                code="""def execute(inputs, context=None):
    import httpx
    from urllib.parse import quote
    
    query = inputs.get('query')
    language = inputs.get('language', 'en')
    
    if not query:
        return {"error": "Query is required"}
    
    try:
        # Search for the page
        search_url = f"https://{language}.wikipedia.org/w/api.php"
        search_params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "format": "json",
            "srlimit": 1
        }
        
        with httpx.Client(timeout=10.0) as client:
            search_res = client.get(search_url, params=search_params)
            search_res.raise_for_status()
            search_data = search_res.json()
            
            if not search_data.get('query', {}).get('search'):
                return {"error": f"No Wikipedia article found for: {query}"}
            
            page_title = search_data['query']['search'][0]['title']
            
            # Get page summary
            summary_url = f"https://{language}.wikipedia.org/api/rest_v1/page/summary/{quote(page_title)}"
            summary_res = client.get(summary_url)
            summary_res.raise_for_status()
            data = summary_res.json()
            
            return {
                "success": True,
                "title": data.get('title'),
                "summary": data.get('extract'),
                "url": data.get('content_urls', {}).get('desktop', {}).get('page'),
                "thumbnail": data.get('thumbnail', {}).get('source') if data.get('thumbnail') else None,
                "language": language
            }
    except httpx.HTTPError as e:
        return {"error": f"Wikipedia service error: {str(e)}"}
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}""",
                entry_point="execute",
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Topic to search for on Wikipedia"},
                        "language": {"type": "string", "description": "Language code (default: 'en')", "default": "en"}
                    },
                    "required": ["query"]
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "success": {"type": "boolean"},
                        "title": {"type": "string"},
                        "summary": {"type": "string"},
                        "url": {"type": "string"},
                        "thumbnail": {"type": "string"},
                        "language": {"type": "string"},
                        "error": {"type": "string"}
                    }
                },
                category="research",
                tags=["wikipedia", "knowledge", "encyclopedia", "research"],
                capabilities=["information_retrieval", "knowledge_base"],
                created_by=user_id,
                updated_by=user_id
            ),
            
            # Enhanced Tool #3: Internet Search
            Tool(
                id=uuid.uuid4(),
                name="Internet Search",
                description="Perform instant answers and web searches using DuckDuckGo API. Get summaries, definitions, and related information.",
                version="1.0.0",
                tool_type=ToolType.CUSTOM,
                status=ToolStatus.ACTIVE,
                code="""def execute(inputs, context=None):
    import httpx
    from urllib.parse import quote
    
    query = inputs.get('query')
    if not query:
        return {"error": "Query is required"}
    
    try:
        url = f"https://api.duckduckgo.com/?q={quote(query)}&format=json&no_html=1"
        
        with httpx.Client(timeout=10.0) as client:
            res = client.get(url)
            res.raise_for_status()
            data = res.json()
            
            abstract = data.get('AbstractText', '')
            related = [
                {
                    "text": topic.get('Text', ''),
                    "url": topic.get('FirstURL', '')
                }
                for topic in data.get('RelatedTopics', [])
                if isinstance(topic, dict) and 'Text' in topic
            ][:5]
            
            return {
                "success": True,
                "query": query,
                "abstract": abstract if abstract else "No instant answer available",
                "abstract_source": data.get('AbstractSource'),
                "abstract_url": data.get('AbstractURL'),
                "related_topics": related,
                "answer": data.get('Answer', ''),
                "definition": data.get('Definition', '')
            }
    except httpx.HTTPError as e:
        return {"error": f"Search service error: {str(e)}"}
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}""",
                entry_point="execute",
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query or question"}
                    },
                    "required": ["query"]
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "success": {"type": "boolean"},
                        "query": {"type": "string"},
                        "abstract": {"type": "string"},
                        "abstract_source": {"type": "string"},
                        "abstract_url": {"type": "string"},
                        "related_topics": {"type": "array"},
                        "answer": {"type": "string"},
                        "definition": {"type": "string"},
                        "error": {"type": "string"}
                    }
                },
                category="search",
                tags=["web", "search", "duckduckgo", "internet"],
                capabilities=["web_search", "instant_answers"],
                created_by=user_id,
                updated_by=user_id
            ),
            
            # New Tool #4: Calculator
            Tool(
                id=uuid.uuid4(),
                name="Calculator",
                description="Perform mathematical calculations including arithmetic, scientific functions, and expressions. Supports +, -, *, /, **, sqrt, sin, cos, tan, log, etc.",
                version="1.0.0",
                tool_type=ToolType.CUSTOM,
                status=ToolStatus.ACTIVE,
                code="""def execute(inputs, context=None):
    import math
    import re
    
    expression = inputs.get('expression', '')
    if not expression:
        return {"error": "Expression is required"}
    
    try:
        # Safe math evaluation - allow only math operations
        allowed_names = {
            'sqrt': math.sqrt, 'sin': math.sin, 'cos': math.cos, 'tan': math.tan,
            'log': math.log, 'log10': math.log10, 'exp': math.exp, 'abs': abs,
            'pow': pow, 'pi': math.pi, 'e': math.e, 'floor': math.floor,
            'ceil': math.ceil, 'round': round
        }
        
        # Remove any potentially dangerous characters
        if re.search(r'[^0-9+\-*/().%\s,a-z]', expression, re.I):
            # Check if it's just function names
            clean_expr = re.sub(r'[a-z]+', '', expression, flags=re.I)
            if re.search(r'[^0-9+\-*/().%\s,]', clean_expr):
                return {"error": "Invalid characters in expression"}
        
        # Evaluate safely
        result = eval(expression, {"__builtins__": {}}, allowed_names)
        
        return {
            "success": True,
            "expression": expression,
            "result": float(result) if isinstance(result, (int, float)) else str(result)
        }
    except ZeroDivisionError:
        return {"error": "Division by zero"}
    except SyntaxError:
        return {"error": "Invalid mathematical expression"}
    except Exception as e:
        return {"error": f"Calculation error: {str(e)}"}""",
                entry_point="execute",
                input_schema={
                    "type": "object",
                    "properties": {
                        "expression": {
                            "type": "string",
                            "description": "Mathematical expression to calculate (e.g., '2+2', 'sqrt(16)', 'sin(pi/2)')"
                        }
                    },
                    "required": ["expression"]
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "success": {"type": "boolean"},
                        "expression": {"type": "string"},
                        "result": {"type": "number"},
                        "error": {"type": "string"}
                    }
                },
                category="utilities",
                tags=["calculator", "math", "arithmetic", "scientific"],
                capabilities=["mathematical_operations", "scientific_functions"],
                created_by=user_id,
                updated_by=user_id
            ),
            
            # New Tool #5: Time & Date
            Tool(
                id=uuid.uuid4(),
                name="Time & Date",
                description="Get current time in any timezone, convert between timezones, format dates, and perform date calculations.",
                version="1.0.0",
                tool_type=ToolType.CUSTOM,
                status=ToolStatus.ACTIVE,
                code="""def execute(inputs, context=None):
    from datetime import datetime, timezone
    import re
    
    action = inputs.get('action', 'current_time')
    tz_name = inputs.get('timezone', 'UTC')
    
    try:
        # Simple timezone offset handling (supports: UTC, EST, PST, GMT+5, etc.)
        offset_match = re.match(r'(UTC|GMT)([+-]\d+)?', tz_name, re.I)
        
        if action == 'current_time':
            now = datetime.now(timezone.utc)
            
            # Handle timezone offset
            if offset_match:
                offset_str = offset_match.group(2) or '+0'
                offset_hours = int(offset_str)
                from datetime import timedelta
                now = now + timedelta(hours=offset_hours)
                tz_display = f"UTC{offset_str}" if offset_str != '+0' else 'UTC'
            else:
                tz_display = tz_name
            
            return {
                "success": True,
                "action": "current_time",
                "timezone": tz_display,
                "datetime": now.strftime('%Y-%m-%d %H:%M:%S'),
                "date": now.strftime('%Y-%m-%d'),
                "time": now.strftime('%H:%M:%S'),
                "iso_format": now.isoformat(),
                "timestamp": int(now.timestamp())
            }
        
        elif action == 'format':
            date_str = inputs.get('date_string')
            fmt = inputs.get('format', '%Y-%m-%d %H:%M:%S')
            
            if not date_str:
                return {"error": "date_string is required for format action"}
            
            # Try to parse common formats
            for parse_fmt in ['%Y-%m-%d', '%Y-%m-%d %H:%M:%S', '%Y/%m/%d', '%d-%m-%Y']:
                try:
                    dt = datetime.strptime(date_str, parse_fmt)
                    return {
                        "success": True,
                        "action": "format",
                        "formatted": dt.strftime(fmt),
                        "iso_format": dt.isoformat()
                    }
                except ValueError:
                    continue
            
            return {"error": "Unable to parse date string. Use format: YYYY-MM-DD or YYYY-MM-DD HH:MM:SS"}
        
        else:
            return {"error": f"Unknown action: {action}. Use 'current_time' or 'format'"}
            
    except Exception as e:
        return {"error": f"Date/time error: {str(e)}"}""",
                entry_point="execute",
                input_schema={
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["current_time", "format"],
                            "description": "Action to perform",
                            "default": "current_time"
                        },
                        "timezone": {
                            "type": "string",
                            "description": "Timezone (e.g., 'UTC', 'UTC+5', 'UTC-8')",
                            "default": "UTC"
                        },
                        "date_string": {
                            "type": "string",
                            "description": "Date string to format (for 'format' action)"
                        },
                        "format": {
                            "type": "string",
                            "description": "Output format (for 'format' action)",
                            "default": "%Y-%m-%d %H:%M:%S"
                        }
                    },
                    "required": []
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "success": {"type": "boolean"},
                        "action": {"type": "string"},
                        "timezone": {"type": "string"},
                        "datetime": {"type": "string"},
                        "date": {"type": "string"},
                        "time": {"type": "string"},
                        "iso_format": {"type": "string"},
                        "timestamp": {"type": "integer"},
                        "formatted": {"type": "string"},
                        "error": {"type": "string"}
                    }
                },
                category="utilities",
                tags=["time", "date", "timezone", "datetime"],
                capabilities=["time_operations", "date_formatting", "timezone_conversion"],
                created_by=user_id,
                updated_by=user_id
            ),
            
            # New Tool #6: Text Transformer
            Tool(
                id=uuid.uuid4(),
                name="Text Transformer",
                description="Transform text with various operations: case conversion, base64 encoding/decoding, URL encoding, string reversal, and more.",
                version="1.0.0",
                tool_type=ToolType.CUSTOM,
                status=ToolStatus.ACTIVE,
                code="""def execute(inputs, context=None):
    import base64
    from urllib.parse import quote, unquote
    
    text = inputs.get('text', '')
    operation = inputs.get('operation', 'upper')
    
    if not text:
        return {"error": "Text is required"}
    
    try:
        result = None
        
        if operation == 'upper':
            result = text.upper()
        elif operation == 'lower':
            result = text.lower()
        elif operation == 'title':
            result = text.title()
        elif operation == 'reverse':
            result = text[::-1]
        elif operation == 'base64_encode':
            result = base64.b64encode(text.encode()).decode()
        elif operation == 'base64_decode':
            result = base64.b64decode(text.encode()).decode()
        elif operation == 'url_encode':
            result = quote(text)
        elif operation == 'url_decode':
            result = unquote(text)
        elif operation == 'snake_case':
            import re
            result = re.sub(r'(?<!^)(?=[A-Z])', '_', text).lower()
            result = re.sub(r'\s+', '_', result)
        elif operation == 'camel_case':
            import re
            words = re.split(r'[_\s]+', text)
            result = words[0].lower() + ''.join(w.capitalize() for w in words[1:])
        elif operation == 'length':
            result = str(len(text))
        elif operation == 'word_count':
            result = str(len(text.split()))
        else:
            return {"error": f"Unknown operation: {operation}"}
        
        return {
            "success": True,
            "operation": operation,
            "original": text,
            "result": result
        }
    except Exception as e:
        return {"error": f"Transformation error: {str(e)}"}""",
                entry_point="execute",
                input_schema={
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "Text to transform"},
                        "operation": {
                            "type": "string",
                            "enum": ["upper", "lower", "title", "reverse", "base64_encode", "base64_decode", 
                                   "url_encode", "url_decode", "snake_case", "camel_case", "length", "word_count"],
                            "description": "Transformation operation to perform",
                            "default": "upper"
                        }
                    },
                    "required": ["text"]
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "success": {"type": "boolean"},
                        "operation": {"type": "string"},
                        "original": {"type": "string"},
                        "result": {"type": "string"},
                        "error": {"type": "string"}
                    }
                },
                category="utilities",
                tags=["text", "string", "transformation", "encoding"],
                capabilities=["text_manipulation", "encoding", "formatting"],
                created_by=user_id,
                updated_by=user_id
            ),
            
            # New Tool #7: JSON Parser
            Tool(
                id=uuid.uuid4(),
                name="JSON Parser",
                description="Validate, format, prettify, and query JSON data. Parse JSON strings and extract specific values.",
                version="1.0.0",
                tool_type=ToolType.CUSTOM,
                status=ToolStatus.ACTIVE,
                code="""def execute(inputs, context=None):
    import json
    
    json_string = inputs.get('json_string', '')
    operation = inputs.get('operation', 'validate')
    query_path = inputs.get('query_path', '')
    
    if not json_string:
        return {"error": "json_string is required"}
    
    try:
        # Parse JSON
        try:
            data = json.loads(json_string)
        except json.JSONDecodeError as e:
            return {"error": f"Invalid JSON: {str(e)}", "valid": False}
        
        if operation == 'validate':
            return {
                "success": True,
                "valid": True,
                "message": "JSON is valid"
            }
        
        elif operation == 'format':
            formatted = json.dumps(data, indent=2, sort_keys=True)
            return {
                "success": True,
                "formatted": formatted,
                "compact": json.dumps(data, separators=(',', ':'))
            }
        
        elif operation == 'query':
            if not query_path:
                return {"error": "query_path is required for query operation"}
            
            # Simple JSONPath implementation (supports: key, key.subkey, key[0])
            result = data
            for part in query_path.split('.'):
                if '[' in part:
                    key, index = part.split('[')
                    index = int(index.rstrip(']'))
                    result = result[key][index] if key else result[index]
                else:
                    result = result[part]
            
            return {
                "success": True,
                "query_path": query_path,
                "result": result
            }
        
        elif operation == 'keys':
            if isinstance(data, dict):
                return {
                    "success": True,
                    "keys": list(data.keys())
                }
            else:
                return {"error": "JSON data is not an object"}
        
        else:
            return {"error": f"Unknown operation: {operation}"}
            
    except KeyError as e:
        return {"error": f"Key not found: {str(e)}"}
    except IndexError as e:
        return {"error": f"Index out of range: {str(e)}"}
    except Exception as e:
        return {"error": f"JSON processing error: {str(e)}"}""",
                entry_point="execute",
                input_schema={
                    "type": "object",
                    "properties": {
                        "json_string": {"type": "string", "description": "JSON string to process"},
                        "operation": {
                            "type": "string",
                            "enum": ["validate", "format", "query", "keys"],
                            "description": "Operation to perform",
                            "default": "validate"
                        },
                        "query_path": {
                            "type": "string",
                            "description": "JSON path for query operation (e.g., 'user.name', 'items[0]')"
                        }
                    },
                    "required": ["json_string"]
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "success": {"type": "boolean"},
                        "valid": {"type": "boolean"},
                        "message": {"type": "string"},
                        "formatted": {"type": "string"},
                        "compact": {"type": "string"},
                        "query_path": {"type": "string"},
                        "result": {},
                        "keys": {"type": "array"},
                        "error": {"type": "string"}
                    }
                },
                category="utilities",
                tags=["json", "parsing", "validation", "data"],
                capabilities=["json_processing", "data_validation", "data_extraction"],
                created_by=user_id,
                updated_by=user_id
            ),
            
            # New Tool #8: HTTP Request
            Tool(
                id=uuid.uuid4(),
                name="HTTP Request",
                description="Make HTTP GET and POST requests to external APIs. Supports custom headers, query parameters, and request bodies.",
                version="1.0.0",
                tool_type=ToolType.CUSTOM,
                status=ToolStatus.ACTIVE,
                code="""def execute(inputs, context=None):
    import httpx
    import json as json_module
    
    url = inputs.get('url')
    method = inputs.get('method', 'GET').upper()
    headers = inputs.get('headers', {})
    params = inputs.get('params', {})
    body = inputs.get('body')
    timeout = inputs.get('timeout', 10)
    
    if not url:
        return {"error": "URL is required"}
    
    if method not in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']:
        return {"error": f"Unsupported method: {method}"}
    
    try:
        with httpx.Client(timeout=timeout) as client:
            if method == 'GET':
                response = client.get(url, headers=headers, params=params)
            elif method == 'POST':
                response = client.post(url, headers=headers, params=params, 
                                     json=body if isinstance(body, dict) else None,
                                     content=body if isinstance(body, str) else None)
            elif method == 'PUT':
                response = client.put(url, headers=headers, params=params,
                                    json=body if isinstance(body, dict) else None,
                                    content=body if isinstance(body, str) else None)
            elif method == 'DELETE':
                response = client.delete(url, headers=headers, params=params)
            elif method == 'PATCH':
                response = client.patch(url, headers=headers, params=params,
                                      json=body if isinstance(body, dict) else None,
                                      content=body if isinstance(body, str) else None)
            
            # Try to parse response as JSON
            try:
                response_body = response.json()
            except:
                response_body = response.text
            
            return {
                "success": True,
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "body": response_body,
                "url": str(response.url)
            }
    except httpx.TimeoutException:
        return {"error": f"Request timeout after {timeout} seconds"}
    except httpx.HTTPError as e:
        return {"error": f"HTTP error: {str(e)}"}
    except Exception as e:
        return {"error": f"Request error: {str(e)}"}""",
                entry_point="execute",
                input_schema={
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "URL to send request to"},
                        "method": {
                            "type": "string",
                            "enum": ["GET", "POST", "PUT", "DELETE", "PATCH"],
                            "description": "HTTP method",
                            "default": "GET"
                        },
                        "headers": {
                            "type": "object",
                            "description": "HTTP headers as key-value pairs",
                            "default": {}
                        },
                        "params": {
                            "type": "object",
                            "description": "Query parameters as key-value pairs",
                            "default": {}
                        },
                        "body": {
                            "description": "Request body (string or object for JSON)",
                        },
                        "timeout": {
                            "type": "integer",
                            "description": "Timeout in seconds",
                            "default": 10
                        }
                    },
                    "required": ["url"]
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "success": {"type": "boolean"},
                        "status_code": {"type": "integer"},
                        "headers": {"type": "object"},
                        "body": {},
                        "url": {"type": "string"},
                        "error": {"type": "string"}
                    }
                },
                category="integration",
                tags=["http", "api", "request", "web"],
                capabilities=["http_requests", "api_integration", "web_scraping"],
                created_by=user_id,
                updated_by=user_id
            ),
            
            # New Tool #9: File Hash Calculator
            Tool(
                id=uuid.uuid4(),
                name="File Hash Calculator",
                description="Calculate cryptographic hashes (MD5, SHA1, SHA256, SHA512) for text content. Useful for data verification and integrity checks.",
                version="1.0.0",
                tool_type=ToolType.CUSTOM,
                status=ToolStatus.ACTIVE,
                code="""def execute(inputs, context=None):
    import hashlib
    
    content = inputs.get('content', '')
    algorithm = inputs.get('algorithm', 'sha256').lower()
    
    if not content:
        return {"error": "Content is required"}
    
    try:
        # Convert content to bytes
        content_bytes = content.encode('utf-8')
        
        # Calculate hash based on algorithm
        if algorithm == 'md5':
            hash_obj = hashlib.md5(content_bytes)
        elif algorithm == 'sha1':
            hash_obj = hashlib.sha1(content_bytes)
        elif algorithm == 'sha256':
            hash_obj = hashlib.sha256(content_bytes)
        elif algorithm == 'sha512':
            hash_obj = hashlib.sha512(content_bytes)
        else:
            return {"error": f"Unsupported algorithm: {algorithm}. Use md5, sha1, sha256, or sha512"}
        
        hash_hex = hash_obj.hexdigest()
        
        return {
            "success": True,
            "algorithm": algorithm,
            "hash": hash_hex,
            "content_length": len(content)
        }
    except Exception as e:
        return {"error": f"Hash calculation error: {str(e)}"}""",
                entry_point="execute",
                input_schema={
                    "type": "object",
                    "properties": {
                        "content": {"type": "string", "description": "Text content to hash"},
                        "algorithm": {
                            "type": "string",
                            "enum": ["md5", "sha1", "sha256", "sha512"],
                            "description": "Hash algorithm to use",
                            "default": "sha256"
                        }
                    },
                    "required": ["content"]
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "success": {"type": "boolean"},
                        "algorithm": {"type": "string"},
                        "hash": {"type": "string"},
                        "content_length": {"type": "integer"},
                        "error": {"type": "string"}
                    }
                },
                category="utilities",
                tags=["hash", "crypto", "md5", "sha256", "checksum"],
                capabilities=["hashing", "data_verification", "cryptography"],
                created_by=user_id,
                updated_by=user_id
            )
        ]
        
        for tool in tools:
            session.add(tool)

        await session.commit()
        print(f"✓ Created {len(tools)} sample tools")


async def create_sample_mcp_servers(user_id: uuid.UUID):
    """Create sample MCP servers"""
    async with AsyncSessionLocal() as session:
        # Check if MCP servers exist
        result = await session.execute(select(MCPServer))
        if result.scalars().first():
            print("✓ Sample MCP servers already exist")
            return

        mcp_servers = [
            MCPServer(
                id=uuid.uuid4(),
                name="GitHub Integration",
                description="Connect to GitHub repositories to manage issues, pull requests, and code.",
                base_url="https://api.github.com",
                version="1.0.0",
                status=MCPServerStatus.CONNECTED,
                capabilities=["access_repositories", "manage_issues", "code_search"],
                created_by=user_id,
                updated_by=user_id
            ),
            MCPServer(
                id=uuid.uuid4(),
                name="Slack Bot",
                description="Integration with Slack workspace for messaging and notifications.",
                base_url="wss://slack.com/mcp",
                version="1.2.0",
                status=MCPServerStatus.CONNECTED,
                capabilities=["send_messages", "read_channels"],
                created_by=user_id,
                updated_by=user_id
            ),
            MCPServer(
                id=uuid.uuid4(),
                name="Weather API",
                description="External weather provider integration.",
                base_url="https://api.weather.com/mcp",
                version="2.1.0",
                status=MCPServerStatus.DISCONNECTED,
                capabilities=["weather_forecast", "historical_data"],
                created_by=user_id,
                updated_by=user_id
            )
        ]
        
        for server in mcp_servers:
            session.add(server)
        
        await session.commit()
        print(f"✓ Created {len(mcp_servers)} sample MCP servers")


async def wait_for_database():
    """Wait for database to be ready with retry logic."""
    from shared.database.connection import async_engine
    from sqlalchemy import text
    import asyncio
    
    max_retries = 10
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            async with async_engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            print(f"✅ Database connection established")
            return True
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"⏳ Waiting for database... (attempt {attempt + 1}/{max_retries})")
                await asyncio.sleep(retry_delay)
            else:
                print(f"❌ Failed to connect to database after {max_retries} attempts")
                raise


async def main():
    print("🌱 Seeding database with sample data...\n")
    
    try:
        # Wait for database to be ready
        await wait_for_database()
        
        # Create admin user
        admin_user = await create_admin_user()
        
        # Create sample data
        await create_sample_agents(admin_user.id)
        await create_sample_workflows(admin_user.id)
        await create_sample_tools(admin_user.id)
        await create_sample_mcp_servers(admin_user.id)
        
        print("\n✅ Database seeding completed successfully!")
        print("\n📝 Login credentials:")
        print("   Email: admin@example.com")
        print("   Password: admin")
        
    except Exception as e:
        print(f"\n❌ Error seeding database: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
