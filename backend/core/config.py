"""
Core configuration for Mission Control backend.
Maintains OpenClaw-native boundaries.
"""

from pydantic_settings import BaseSettings
from typing import Optional
import secrets


class Settings(BaseSettings):
    """Application settings - Mission Control owns metadata, OpenClaw owns runtime."""
    
    # Application
    APP_NAME: str = "Mission Control"
    APP_VERSION: str = "2.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    
    # Database - for metadata only, not agent runtime state
    DATABASE_URL: str = "postgresql+asyncpg://mission_control:mission_control@localhost:5432/mission_control"
    SYNC_DATABASE_URL: str = "postgresql://mission_control:mission_control@localhost:5432/mission_control"
    
    # Redis - for caching and SSE pubsub
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Security
    SECRET_KEY: str = secrets.token_urlsafe(32)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # OpenClaw Integration - we reference, not control
    OPENCLAW_GATEWAY_URL: str = "ws://127.0.0.1:18789"
    OPENCLAW_API_URL: str = "http://127.0.0.1:18789"
    OPENCLAW_TOKEN: Optional[str] = None
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # CORS
    FRONTEND_URL: str = "http://localhost:3000"
    CORS_ORIGINS: list = ["http://localhost:3000", "http://localhost:3001"]
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()