"""
Configuration management using Pydantic Settings.
"""

import os
from typing import Optional, List
from pydantic import Field, validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""
    
    model_config = SettingsConfigDict(
        env_prefix="DDOS_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )
    
    # Core configuration
    bot_token: str = Field(..., description="Telegram bot token")
    admin_chat_id: str = Field(..., description="Admin chat ID for notifications")
    
    # Traffic analysis
    block_threshold: int = Field(
        default=1000,
        description="Packets per second threshold for blocking"
    )
    auto_unblock_minutes: int = Field(
        default=60,
        description="Minutes before automatic unblock"
    )
    monitor_interface: str = Field(
        default="eth0",
        description="Network interface to monitor"
    )
    monitor_port: int = Field(
        default=80,
        description="Port to monitor for attacks"
    )
    rate_window_seconds: int = Field(
        default=10,
        description="Sliding window size for rate limiting"
    )
    
    # Security
    face_similarity_threshold: float = Field(
        default=0.6,
        description="Minimum similarity for face recognition (0.0-1.0)"
    )
    session_timeout_minutes: int = Field(
        default=30,
        description="Session timeout in minutes"
    )
    
    # Performance
    worker_count: int = Field(
        default=4,
        description="Number of worker threads for packet processing"
    )
    max_queue_size: int = Field(
        default=10000,
        description="Maximum queue size for packet processing"
    )
    
    # Logging
    log_level: str = Field(
        default="INFO",
        description="Logging level"
    )
    log_format: str = Field(
        default="json",
        description="Log format (json or text)"
    )
    
    # Redis
    redis_host: str = Field(
        default="localhost",
        description="Redis host"
    )
    redis_port: int = Field(
        default=6379,
        description="Redis port"
    )
    redis_db: int = Field(
        default=0,
        description="Redis database number"
    )
    redis_password: Optional[str] = Field(
        default=None,
        description="Redis password"
    )
    
    # Database
    database_url: str = Field(
        default="sqlite:///data/ddos.db",
        description="Database connection URL"
    )
    
    # Monitoring
    metrics_port: int = Field(
        default=9090,
        description="Port for Prometheus metrics"
    )
    health_port: int = Field(
        default=8080,
        description="Port for health checks"
    )
    
    @validator("face_similarity_threshold")
    def validate_similarity_threshold(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError("face_similarity_threshold must be between 0.0 and 1.0")
        return v
    
    @validator("log_level")
    def validate_log_level(cls, v):
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"log_level must be one of {valid_levels}")
        return v.upper()
    
    @validator("log_format")
    def validate_log_format(cls, v):
        valid_formats = ["json", "text"]
        if v.lower() not in valid_formats:
            raise ValueError(f"log_format must be one of {valid_formats}")
        return v.lower()


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get settings instance."""
    return settings