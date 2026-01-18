"""
Built-in Tools Library for AI Agent Framework.

This module provides pre-built tools that can be easily registered and used by agents.
These tools provide common functionalities like web search, HTTP requests, etc.
"""

# Web Search Tool using DuckDuckGo (no API key required)
WEB_SEARCH_TOOL = {
    "name": "web_search",
    "description": "Search the internet using DuckDuckGo. Returns relevant search results with titles, snippets, and URLs. No API key required.",
    "version": "1.0.0",
    "tool_type": "custom",
    "code": """
import requests
from urllib.parse import quote_plus

def execute(inputs: dict, context=None) -> dict:
    '''Search the web using DuckDuckGo Instant Answer API.'''
    try:
        query = inputs.get('query')
        num_results = inputs.get('num_results', 5)
        
        if not query:
            return {'error': 'Query is required'}

        # DuckDuckGo Instant Answer API (free, no key required)
        encoded_query = quote_plus(query)
        url = f"https://api.duckduckgo.com/?q={encoded_query}&format=json&no_html=1"
        
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            results = []
            
            # Get abstract if available
            if data.get('Abstract'):
                results.append({
                    'title': data.get('Heading', 'Search Result'),
                    'snippet': data['Abstract'],
                    'url': data.get('AbstractURL', '')
                })
            
            # Get related topics
            for topic in data.get('RelatedTopics', [])[:num_results]:
                if isinstance(topic, dict) and 'Text' in topic:
                    results.append({
                        'title': topic.get('Text', '')[:100],
                        'snippet': topic.get('Text', ''),
                        'url': topic.get('FirstURL', '')
                    })
            
            return {
                'query': query,
                'results': results[:num_results],
                'count': len(results[:num_results])
            }
        else:
            return {'error': f'Search API error: {response.status_code}'}
    
    except Exception as e:
        return {'error': str(e)}
""",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query"
            },
            "num_results": {
                "type": "integer",
                "description": "Number of results to return (default: 5)",
                "default": 5
            }
        },
        "required": ["query"]
    },
    "output_schema": {
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "results": {"type": "array"},
            "count": {"type": "integer"}
        }
    },
    "category": "web",
    "tags": ["search", "internet", "web", "duckduckgo"],
    "timeout_seconds": 30
}


# HTTP Fetch Tool
HTTP_FETCH_TOOL = {
    "name": "http_fetch",
    "description": "Fetch content from a URL via HTTP GET request. Returns the response body as text.",
    "version": "1.0.0",
    "tool_type": "custom",
    "code": """
import requests
from bs4 import BeautifulSoup

def execute(inputs: dict, context=None) -> dict:
    '''Fetch content from a URL.'''
    try:
        url = inputs.get('url')
        extract_text = inputs.get('extract_text', True)
        
        if not url:
            return {'error': 'URL is required'}

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            content = response.text
            
            # Extract just text if requested
            if extract_text:
                soup = BeautifulSoup(content, 'html.parser')
                # Remove script and style elements
                for script in soup(["script", "style"]):
                    script.decompose()
                text = soup.get_text()
                # Clean up whitespace
                lines = (line.strip() for line in text.splitlines())
                chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                text = ' '.join(chunk for chunk in chunks if chunk)
                content = text[:5000]  # Limit to 5000 chars
            
            return {
                'url': url,
                'status_code': response.status_code,
                'content': content,
                'content_type': response.headers.get('Content-Type', ''),
                'length': len(content)
            }
        else:
            return {
                'error': f'HTTP {response.status_code}',
                'url': url
            }
    
    except Exception as e:
        return {'error': str(e), 'url': url}
""",
    "input_schema": {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "The URL to fetch"
            },
            "extract_text": {
                "type": "boolean",
                "description": "Extract only text content (default: true)",
                "default": True
            }
        },
        "required": ["url"]
    },
    "output_schema": {
        "type": "object",
        "properties": {
            "url": {"type": "string"},
            "status_code": {"type": "integer"},
            "content": {"type": "string"}
        }
    },
    "category": "web",
    "tags": ["http", "fetch", "web", "scraping"],
    "timeout_seconds": 30
}


# Wikipedia Search Tool
WIKIPEDIA_TOOL = {
    "name": "wikipedia",
    "description": "Search Wikipedia and get article summaries. No API key required.",
    "version": "1.0.0",
    "tool_type": "custom",
    "code": """
import requests

def execute(inputs: dict, context=None) -> dict:
    '''Search Wikipedia and get article summary.'''
    try:
        query = inputs.get('query')
        sentences = inputs.get('sentences', 3)
        
        if not query:
            return {'error': 'Query is required'}

        # Wikipedia API requires User-Agent
        headers = {
            'User-Agent': 'AI-Agent-Framework/1.0 (educational purpose)'
        }

        # 1. Search for the page
        params = {
            'action': 'query',
            'format': 'json',
            'list': 'search',
            'srsearch': query,
            'utf8': 1
        }
        
        search_url = 'https://en.wikipedia.org/w/api.php'
        response = requests.get(search_url, params=params, headers=headers, timeout=10)
        
        if response.status_code != 200:
            return {'error': f'Wikipedia API error: {response.status_code}'}
        
        data = response.json()
        search_results = data.get('query', {}).get('search', [])
        
        if not search_results:
            return {'error': 'No results found', 'query': query}
        
        # Get summary of first result
        page_title = search_results[0]['title']
        
        summary_params = {
            'action': 'query',
            'format': 'json',
            'prop': 'extracts',
            'exintro': True,
            'explaintext': True,
            'exsentences': sentences,
            'titles': page_title
        }
        
        summary_response = requests.get(search_url, params=summary_params, headers=headers, timeout=10)
        summary_data = summary_response.json()
        
        pages = summary_data.get('query', {}).get('pages', {})
        if not pages:
             return {'error': 'Failed to retrieve page content'}
             
        page = list(pages.values())[0]
        
        return {
            'query': query,
            'title': page.get('title', ''),
            'summary': page.get('extract', ''),
            'url': f"https://en.wikipedia.org/wiki/{page_title.replace(' ', '_')}"
        }
    
    except Exception as e:
        return {'error': str(e)}
""",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The Wikipedia search query"
            },
            "sentences": {
                "type": "integer",
                "description": "Number of sentences in summary (default: 3)",
                "default": 3
            }
        },
        "required": ["query"]
    },
    "output_schema": {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "summary": {"type": "string"},
            "url": {"type": "string"}
        }
    },
    "category": "knowledge",
    "tags": ["wikipedia", "knowledge", "research"],
    "timeout_seconds": 30
}


# Date/Time Tool
DATETIME_TOOL = {
    "name": "datetime",
    "description": "Get current date and time in various formats and timezones.",
    "version": "1.0.0",
    "tool_type": "custom",
    "code": """
from datetime import datetime
import pytz

def execute(inputs: dict, context=None) -> dict:
    '''Get current date and time.'''
    try:
        timezone = inputs.get('timezone', 'UTC')
        format_string = inputs.get('format_string')
        
        tz = pytz.timezone(timezone)
        now = datetime.now(tz)
        
        result = {
            'timezone': timezone,
            'iso': now.isoformat(),
            'timestamp': int(now.timestamp()),
            'year': now.year,
            'month': now.month,
            'day': now.day,
            'hour': now.hour,
            'minute': now.minute,
            'second': now.second,
            'weekday': now.strftime('%A'),
            'formatted': now.strftime('%Y-%m-%d %H:%M:%S %Z')
        }
        
        if format_string:
            result['custom_format'] = now.strftime(format_string)
        
        return result
    
    except Exception as e:
        return {'error': str(e)}
""",
    "input_schema": {
        "type": "object",
        "properties": {
            "timezone": {
                "type": "string",
                "description": "Timezone name (e.g., 'UTC', 'America/New_York')",
                "default": "UTC"
            },
            "format_string": {
                "type": "string",
                "description": "Optional custom format string (strftime format)"
            }
        }
    },
    "category": "utility",
    "tags": ["datetime", "time", "timezone"],
    "timeout_seconds": 5
}


# JSON Parser Tool
JSON_PARSER_TOOL = {
    "name": "json_parser",
    "description": "Parse and extract data from JSON strings.",
    "version": "1.0.0",
    "tool_type": "custom",
    "code": """
import json

def execute(inputs: dict, context=None) -> dict:
    '''Parse JSON and optionally extract data using dot notation path.'''
    try:
        json_string = inputs.get('json_string')
        path = inputs.get('path')
        
        if not json_string:
            return {'error': 'JSON string is required'}

        data = json.loads(json_string)
        
        if path:
            # Navigate using dot notation (e.g., "user.address.city")
            keys = path.split('.')
            result = data
            for key in keys:
                if isinstance(result, dict):
                    result = result.get(key)
                elif isinstance(result, list) and key.isdigit():
                    result = result[int(key)]
                else:
                    return {'error': f'Invalid path: {path}'}
            
            return {'data': result, 'path': path}
        
        return {'data': data}
    
    except json.JSONDecodeError as e:
        return {'error': f'Invalid JSON: {str(e)}'}
    except Exception as e:
        return {'error': str(e)}
""",
    "input_schema": {
        "type": "object",
        "properties": {
            "json_string": {
                "type": "string",
                "description": "The JSON string to parse"
            },
            "path": {
                "type": "string",
                "description": "Optional dot-notation path to extract (e.g., 'user.name')"
            }
        },
        "required": ["json_string"]
    },
    "category": "utility",
    "tags": ["json", "parser", "data"],
    "timeout_seconds": 10
}


# Calculator Tool
CALCULATOR_TOOL = {
    "name": "calculator",
    "description": "Perform basic mathematical operations (add, subtract, multiply, divide). Use this tool for any math questions.",
    "version": "1.0.0",
    "tool_type": "custom",
    "code": """
def execute(inputs: dict, context=None) -> dict:
    '''Simple calculator tool.'''
    try:
        operation = inputs.get('operation', 'add')
        a = inputs.get('a')
        b = inputs.get('b')
        
        if a is None or b is None:
            return {'error': 'Parameters a and b are required'}
            
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
    except Exception as e:
        return {'error': str(e)}
""",
    "input_schema": {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["add", "subtract", "multiply", "divide"],
                "description": "The operation to perform"
            },
            "a": {
                "type": "number",
                "description": "First number"
            },
            "b": {
                "type": "number",
                "description": "Second number"
            }
        },
        "required": ["operation", "a", "b"]
    },
    "output_schema": {
        "type": "object",
        "properties": {
            "result": {"type": "number"}
        }
    },
    "category": "math",
    "tags": ["math", "calculation", "calculator"],
    "timeout_seconds": 10
}


# All available built-in tools
BUILTIN_TOOLS = [
    WEB_SEARCH_TOOL,
    HTTP_FETCH_TOOL,
    WIKIPEDIA_TOOL,
    DATETIME_TOOL,
    JSON_PARSER_TOOL,
    CALCULATOR_TOOL
]


def get_builtin_tools():
    """Get all built-in tools."""
    return BUILTIN_TOOLS


def get_tool_by_name(name: str):
    """Get a specific built-in tool by name."""
    for tool in BUILTIN_TOOLS:
        if tool["name"] == name:
            return tool
    return None
