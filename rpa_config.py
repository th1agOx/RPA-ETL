"""
Centralized configuration using Pydantic Settings.
Loads from environment variables and .env file.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """
    Application settings with environment variable support.
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Application
    APP_NAME: str = "rpa-etl"
    APP_VERSION: str = "0.2.1"
    DEBUG: bool = False
    
    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_MAX_UPLOAD_SIZE_MB: int = 10
    
    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
    
    # Datadog
    DATADOG_ENABLED: bool = False
    DD_SERVICE: str = "rpa-etl"
    DD_ENV: str = "development"
    DD_VERSION: Optional[str] = None
    
    # n8n
    N8N_WEBHOOK_URL: str = "http://localhost:5678/webhook/rpa-process"
    N8N_ENABLED: bool = False
    
    # Audit Store
    AUDIT_DB_URL: str = "sqlite:///audit.db"
    
    # Security
    ALLOWED_CONTENT_TYPES: list[str] = ["application/pdf"]
    
    @property
    def max_upload_size_bytes(self) -> int:
        """Convert MB to bytes."""
        return self.API_MAX_UPLOAD_SIZE_MB * 1024 * 1024


# Global settings instance
settings = Settings()
