"""
Apache Superset Configuration for AI Agent Framework

This configuration sets up Superset for monitoring and visualization
with connections to PostgreSQL and Prometheus data sources.
"""

import os
from datetime import timedelta

# Database configuration
SQLALCHEMY_DATABASE_URI = 'postgresql://postgres:postgres@postgres:5432/superset'

# Redis configuration for caching and session storage
REDIS_HOST = 'redis'
REDIS_PORT = 6379
REDIS_DB = 1

# Cache configuration
CACHE_CONFIG = {
    'CACHE_TYPE': 'RedisCache',
    'CACHE_DEFAULT_TIMEOUT': 300,
    'CACHE_KEY_PREFIX': 'superset_',
    'CACHE_REDIS_HOST': REDIS_HOST,
    'CACHE_REDIS_PORT': REDIS_PORT,
    'CACHE_REDIS_DB': REDIS_DB,
}

# Session configuration
SESSION_TYPE = 'redis'
SESSION_REDIS_HOST = REDIS_HOST
SESSION_REDIS_PORT = REDIS_PORT
SESSION_REDIS_DB = 2

# Security configuration
SECRET_KEY = os.environ.get('SUPERSET_SECRET_KEY', 'your-secret-key-here')
WTF_CSRF_ENABLED = True
WTF_CSRF_TIME_LIMIT = None

# Feature flags
FEATURE_FLAGS = {
    'ENABLE_TEMPLATE_PROCESSING': True,
    'DASHBOARD_NATIVE_FILTERS': True,
    'DASHBOARD_CROSS_FILTERS': True,
    'DASHBOARD_RBAC': True,
    'EMBEDDED_SUPERSET': True,
    'GENERIC_CHART_AXES': True,
    'LISTVIEWS_DEFAULT_CARD_VIEW': True,
}

# Authentication configuration
AUTH_TYPE = 1  # Database authentication
AUTH_ROLE_ADMIN = 'Admin'
AUTH_ROLE_PUBLIC = 'Public'

# Default roles
AUTH_USER_REGISTRATION = True
AUTH_USER_REGISTRATION_ROLE = 'Gamma'

# Email configuration (optional)
SMTP_HOST = os.environ.get('SMTP_HOST', 'localhost')
SMTP_STARTTLS = True
SMTP_SSL = False
SMTP_USER = os.environ.get('SMTP_USER', '')
SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', '')
SMTP_MAIL_FROM = os.environ.get('SMTP_MAIL_FROM', 'superset@example.com')

# Logging configuration
ENABLE_TIME_ROTATE = True
TIME_ROTATE_LOG_LEVEL = 'INFO'
FILENAME = os.path.join(os.path.expanduser('~'), 'superset.log')

# Async query configuration
RESULTS_BACKEND = {
    'CACHE_TYPE': 'RedisCache',
    'CACHE_DEFAULT_TIMEOUT': 86400,
    'CACHE_KEY_PREFIX': 'superset_results_',
    'CACHE_REDIS_HOST': REDIS_HOST,
    'CACHE_REDIS_PORT': REDIS_PORT,
    'CACHE_REDIS_DB': 3,
}

# SQL Lab configuration
SQLLAB_CTAS_NO_LIMIT = True
SQLLAB_TIMEOUT = 300
SQLLAB_ASYNC_TIME_LIMIT_SEC = 60 * 60 * 6  # 6 hours

# Dashboard configuration
DASHBOARD_AUTO_REFRESH_MODE = 'fetch'
DASHBOARD_AUTO_REFRESH_INTERVALS = [
    [0, 'Don\'t refresh'],
    [10, '10 seconds'],
    [30, '30 seconds'],
    [60, '1 minute'],
    [300, '5 minutes'],
    [1800, '30 minutes'],
    [3600, '1 hour'],
]

# Chart configuration
DEFAULT_FEATURE_FLAGS = {
    'CLIENT_CACHE': False,
    'ENABLE_EXPLORE_JSON_CSRF_PROTECTION': False,
    'PRESTO_EXPAND_DATA': False,
}

# Custom CSS (optional)
CUSTOM_CSS = """
.navbar-brand {
    color: #2c3e50 !important;
}

.dashboard-header {
    background-color: #ecf0f1;
}

.slice_container {
    border: 1px solid #bdc3c7;
    border-radius: 4px;
}
"""

# Data source configurations
DATABASE_CONNECTIONS = {
    'ai_agent_framework': {
        'engine': 'postgresql',
        'host': 'postgres',
        'port': 5432,
        'database': 'ai_agent_framework',
        'username': 'postgres',
        'password': 'postgres',
    },
    'prometheus': {
        'engine': 'prometheus',
        'host': 'prometheus',
        'port': 9090,
    }
}

# Row level security
ROW_LEVEL_SECURITY_FILTERS = {
    'tenant_filter': lambda: f"tenant_id = '{get_current_tenant_id()}'"
}

def get_current_tenant_id():
    """Get current tenant ID from session or context"""
    # This would be implemented based on your authentication system
    return 'default'

# Jinja context for SQL templates
JINJA_CONTEXT_ADDONS = {
    'current_tenant_id': get_current_tenant_id,
}

# Webdriver configuration for reports
WEBDRIVER_BASEURL = 'http://superset:8088'
WEBDRIVER_BASEURL_USER_FRIENDLY = 'http://localhost:8088'

# Thumbnail configuration
THUMBNAIL_SELENIUM_USER = 'admin'
THUMBNAIL_CACHE_CONFIG = CACHE_CONFIG

# Alert and report configuration
ALERT_REPORTS_NOTIFICATION_DRY_RUN = False
WEBDRIVER_TYPE = 'chrome'
WEBDRIVER_OPTION_ARGS = [
    '--force-device-scale-factor=1',
    '--high-dpi-support=1',
    '--headless',
    '--disable-gpu',
    '--disable-dev-shm-usage',
    '--no-sandbox',
    '--disable-setuid-sandbox',
    '--disable-extensions',
]

# Custom security manager (optional)
# from superset.security import SupersetSecurityManager
# CUSTOM_SECURITY_MANAGER = SupersetSecurityManager

# Mapbox configuration (optional)
MAPBOX_API_KEY = os.environ.get('MAPBOX_API_KEY', '')

# Slack configuration for alerts (optional)
SLACK_API_TOKEN = os.environ.get('SLACK_API_TOKEN', '')

# Email reports configuration
EMAIL_REPORTS_SUBJECT_PREFIX = '[Superset] '
EMAIL_REPORTS_CTA = 'Explore in Superset'

# CSV export configuration
CSV_EXPORT = {
    'encoding': 'utf-8',
}

# Excel export configuration
EXCEL_EXPORT = {
    'encoding': 'utf-8',
}

# Public role permissions
PUBLIC_ROLE_LIKE_GAMMA = True

# Enable/disable SQL Lab
ENABLE_JAVASCRIPT_CONTROLS = True

# Time grain configurations
TIME_GRAIN_ADDONS = {
    'PT5M': '5 minutes',
    'PT10M': '10 minutes',
    'PT15M': '15 minutes',
    'PT0.5H': '30 minutes',
    'PT2H': '2 hours',
    'PT6H': '6 hours',
}

# Custom color schemes
CUSTOM_COLOR_PALETTES = [
    {
        'id': 'ai_agent_framework',
        'description': 'AI Agent Framework Colors',
        'colors': [
            '#3498db',  # Blue
            '#e74c3c',  # Red
            '#2ecc71',  # Green
            '#f39c12',  # Orange
            '#9b59b6',  # Purple
            '#1abc9c',  # Turquoise
            '#34495e',  # Dark Blue
            '#e67e22',  # Carrot
        ]
    }
]

# Default color palette
DEFAULT_COLOR_PALETTE = 'ai_agent_framework'