# Configuration management for IDES 2.0 environment variables, database connections, and system settings with validation and defaults for sensor data collection intervals.

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
import os

class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Database Configuration
    influx_url: str = Field(default="http://localhost:8086", description="InfluxDB connection URL")
    influx_token: str = Field(default="", description="InfluxDB authentication token")
    influx_org: str = Field(default="ides", description="InfluxDB organization")
    influx_bucket: str = Field(default="sensors", description="InfluxDB bucket for sensor data")
    
    # LLM Configuration
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API key for AI insights")
    llm_backend: str = Field(default="local", description="LLM backend: 'local' or 'openai'")
    local_llm_url: str = Field(default="http://localhost:11434", description="Local LLM service URL (Ollama)")
    
    # Data Collection Settings
    collection_interval: int = Field(default=30, description="Sensor data collection interval in seconds")
    data_retention_weeks: int = Field(default=4, description="Number of weeks to retain historical data")
    
    # System Settings
    debug: bool = Field(default=True, description="Enable debug mode")
    cors_origins: list = Field(default=["http://localhost:5173", "http://localhost:3000"], description="Allowed CORS origins")
    
    # Data Storage
    data_dir: str = Field(default="data", description="Directory for JSON data snapshots")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

# Global settings instance
settings = Settings()