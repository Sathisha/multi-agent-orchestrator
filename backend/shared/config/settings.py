"""Application configuration management using Pydantic Settings."""

import os
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """Database configuration settings."""
    
    url: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/ai_agent_framework",
        description="Database connection URL"
    )
    async_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/ai_agent_framework",
        description="Async database connection URL"
    )
    echo: bool = Field(default=False, description="Enable SQL query logging")
    pool_size: int = Field(default=10, description="Connection pool size")
    max_overflow: int = Field(default=20, description="Maximum pool overflow")
    
    model_config = SettingsConfigDict(env_prefix="DATABASE_")


class RedisSettings(BaseSettings):
    """Redis configuration settings."""
    
    url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL"
    )
    max_connections: int = Field(default=10, description="Maximum Redis connections")
    
    model_config = SettingsConfigDict(env_prefix="REDIS_")


class SecuritySettings(BaseSettings):
    """Security and authentication settings."""
    
    secret_key: str = Field(
        default="your-secret-key-change-in-production",
        description="Secret key for JWT signing"
    )
    algorithm: str = Field(default="HS256", description="JWT algorithm")
    access_token_expire_minutes: int = Field(
        default=30, description="Access token expiration in minutes"
    )
    
    # Keycloak settings
    keycloak_server_url: Optional[str] = Field(
        default=None, description="Keycloak server URL"
    )
    keycloak_realm: str = Field(default="ai-agent-framework", description="Keycloak realm")
    keycloak_client_id: str = Field(default="ai-agent-framework", description="Keycloak client ID")
    keycloak_client_secret: Optional[str] = Field(
        default=None, description="Keycloak client secret"
    )
    
    model_config = SettingsConfigDict(env_prefix="SECURITY_")


class LoggingSettings(BaseSettings):
    """Logging configuration settings."""
    
    level: str = Field(default="INFO", description="Log level")
    format: str = Field(default="json", description="Log format (json or console)")
    
    model_config = SettingsConfigDict(env_prefix="LOG_")


class APISettings(BaseSettings):
    """API server configuration settings."""
    
    host: str = Field(default="0.0.0.0", description="API server host")
    port: int = Field(default=8000, description="API server port")
    reload: bool = Field(default=False, description="Enable auto-reload in development")
    workers: int = Field(default=1, description="Number of worker processes")
    
    # CORS settings
    cors_origins: list[str] = Field(
        default=["http://localhost:3000"], description="Allowed CORS origins"
    )
    cors_credentials: bool = Field(default=True, description="Allow CORS credentials")
    cors_methods: list[str] = Field(
        default=["GET", "POST", "PUT", "DELETE"], description="Allowed CORS methods"
    )
    cors_headers: list[str] = Field(
        default=["*"], description="Allowed CORS headers"
    )
    
    model_config = SettingsConfigDict(env_prefix="API_")


class MemorySettings(BaseSettings):
    """Memory system configuration settings."""
    
    embedding_provider: str = Field(
        default="ollama",
        description="Embedding provider to use (openai, ollama, or local)"
    )
    embedding_model: str = Field(
        default="nomic-embed-text",
        description="Embedding model name"
    )
    openai_api_key: Optional[str] = Field(
        default=None,
        description="OpenAI API key for embeddings (uses OPENAI_API_KEY env if not set)"
    )
    ollama_base_url: str = Field(
        default="http://ollama:11434",
        description="Base URL for Ollama API"
    )
    vector_db_path: str = Field(
        default="./data/chroma",
        description="Path to vector database storage"
    )
    
    model_config = SettingsConfigDict(env_prefix="MEMORY_")



class LLMSettings(BaseSettings):
    """LLM configuration settings."""
    
    rate_limit_per_minute: int = Field(
        default=60,
        description="Maximum number of LLM calls per minute"
    )
    
    model_config = SettingsConfigDict(env_prefix="LLM_")


class Settings(BaseSettings):
    """Main application settings."""
    
    # Environment
    environment: str = Field(default="development", description="Environment name")
    debug: bool = Field(default=False, description="Enable debug mode")
    
    # Service identification
    service_name: str = Field(default="ai-agent-framework", description="Service name")
    version: str = Field(default="0.1.0", description="Service version")
    
    # Component settings
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    api: APISettings = Field(default_factory=APISettings)
    memory: MemorySettings = Field(default_factory=MemorySettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)

    # Zeebe settings
    zeebe_gateway_host: str = Field(default="zeebe", description="Zeebe gateway host")
    zeebe_gateway_port: int = Field(default=26500, description="Zeebe gateway port")
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get the global settings instance."""
    return settings