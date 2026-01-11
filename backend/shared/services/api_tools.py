"""
Additional tools that require API keys.
Copy this file and add your API keys to enable these tools.
"""

# Google Custom Search Tool (Recommended for production)
GOOGLE_SEARCH_TOOL = {
    "name": "google_search",
    "description": "Search the web using Google Custom Search API. More accurate than DuckDuckGo. Requires API key.",
    "version": "1.0.0",
    "tool_type": "custom",
    "code": """
import requests
import os

def execute(query: str, num_results: int = 5) -> dict:
    '''Search using Google Custom Search API.'''
    api_key = os.getenv('GOOGLE_SEARCH_API_KEY')
    engine_id = os.getenv('GOOGLE_SEARCH_ENGINE_ID')
    
    if not api_key or not engine_id:
        return {'error': 'Google Search API key or Engine ID not configured'}
    
    try:
        url = 'https://www.googleapis.com/customsearch/v1'
        params = {
            'key': api_key,
            'cx': engine_id,
            'q': query,
            'num': min(num_results, 10)
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            results = []
            
            for item in data.get('items', []):
                results.append({
                    'title': item.get('title', ''),
                    'snippet': item.get('snippet', ''),
                    'url': item.get('link', '')
                })
            
            return {
                'query': query,
                'results': results,
                'count': len(results),
                'total_results': data.get('searchInformation', {}).get('totalResults', 0)
            }
        else:
            return {'error': f'Google Search API error: {response.status_code}'}
    
    except Exception as e:
        return {'error': str(e)}
""",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "The search query"},
            "num_results": {"type": "integer", "description": "Number of results (max 10)", "default": 5}
        },
        "required": ["query"]
    },
    "category": "web",
    "tags": ["search", "google", "internet"],
    "timeout_seconds": 30
}


# OpenWeatherMap Tool
WEATHER_TOOL = {
    "name": "weather",
    "description": "Get current weather and forecast for any city using OpenWeatherMap API.",
    "version": "1.0.0",
    "tool_type": "custom",
    "code": """
import requests
import os

def execute(city: str, units: str = "metric") -> dict:
    '''Get weather for a city.'''
    api_key = os.getenv('OPENWEATHER_API_KEY')
    
    if not api_key:
        return {'error': 'OpenWeatherMap API key not configured'}
    
    try:
        url = 'https://api.openweathermap.org/data/2.5/weather'
        params = {
            'q': city,
            'appid': api_key,
            'units': units  # metric, imperial, or standard
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            return {
                'city': city,
                'temperature': data['main']['temp'],
                'feels_like': data['main']['feels_like'],
                'humidity': data['main']['humidity'],
                'description': data['weather'][0]['description'],
                'wind_speed': data['wind']['speed'],
                'units': units
            }
        else:
            return {'error': f'Weather API error: {response.status_code}'}
    
    except Exception as e:
        return {'error': str(e)}
""",
    "input_schema": {
        "type": "object",
        "properties": {
            "city": {"type": "string", "description": "City name"},
            "units": {"type": "string", "enum": ["metric", "imperial"], "default": "metric"}
        },
        "required": ["city"]
    },
    "category": "data",
    "tags": ["weather", "forecast"],
    "timeout_seconds": 15
}


# News API Tool
NEWS_TOOL = {
    "name": "news",
    "description": "Get latest news articles using NewsAPI. Requires API key.",
    "version": "1.0.0",
    "tool_type": "custom",
    "code": """
import requests
import os

def execute(query: str, num_articles: int = 5) -> dict:
    '''Get news articles.'''
    api_key = os.getenv('NEWS_API_KEY')
    
    if not api_key:
        return {'error': 'NewsAPI key not configured'}
    
    try:
        url = 'https://newsapi.org/v2/everything'
        params = {
            'q': query,
            'apiKey': api_key,
            'pageSize': min(num_articles, 100),
            'sortBy': 'publishedAt'
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            articles = []
            
            for article in data.get('articles', []):
                articles.append({
                    'title': article.get('title', ''),
                    'description': article.get('description', ''),
                    'url': article.get('url', ''),
                    'source': article.get('source', {}).get('name', ''),
                    'published_at': article.get('publishedAt', '')
                })
            
            return {
                'query': query,
                'articles': articles,
                'total_results': data.get('totalResults', 0)
            }
        else:
            return {'error': f'News API error: {response.status_code}'}
    
    except Exception as e:
        return {'error': str(e)}
""",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query for news"},
            "num_articles": {"type": "integer", "description": "Number of articles", "default": 5}
        },
        "required": ["query"]
    },
    "category": "news",
    "tags": ["news", "articles"],
    "timeout_seconds": 15
}


# All API-based tools
API_TOOLS = [
    GOOGLE_SEARCH_TOOL,
    WEATHER_TOOL,
    NEWS_TOOL
]


def get_api_tools():
    """Get all API-based tools."""
    return API_TOOLS
