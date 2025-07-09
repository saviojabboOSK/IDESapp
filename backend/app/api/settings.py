# System settings API for configuring data collection intervals, LLM backend selection, data retention policies, and InfluxDB connection parameters with validation.

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
import json
from pathlib import Path

from app.core.config import settings

router = APIRouter()

class SettingsUpdate(BaseModel):
    """Model for settings update requests."""
    collection_interval: Optional[int] = Field(None, ge=10, le=3600, description="Collection interval in seconds (10-3600)")
    data_retention_weeks: Optional[int] = Field(None, ge=1, le=52, description="Data retention in weeks (1-52)")
    llm_backend: Optional[str] = Field(None, regex="^(local|openai)$", description="LLM backend: local or openai")
    local_llm_url: Optional[str] = Field(None, description="Local LLM service URL")
    openai_api_key: Optional[str] = Field(None, description="OpenAI API key")
    influx_url: Optional[str] = Field(None, description="InfluxDB connection URL")
    influx_token: Optional[str] = Field(None, description="InfluxDB authentication token")
    influx_org: Optional[str] = Field(None, description="InfluxDB organization")
    influx_bucket: Optional[str] = Field(None, description="InfluxDB bucket name")

@router.get("/")
async def get_settings():
    """Get current system configuration settings."""
    return {
        "data_collection": {
            "collection_interval": settings.collection_interval,
            "data_retention_weeks": settings.data_retention_weeks,
            "data_dir": settings.data_dir
        },
        "llm_configuration": {
            "backend": settings.llm_backend,
            "local_url": settings.local_llm_url,
            "openai_configured": bool(settings.openai_api_key)
        },
        "database": {
            "influx_url": settings.influx_url,
            "influx_org": settings.influx_org,
            "influx_bucket": settings.influx_bucket,
            "influx_configured": bool(settings.influx_token)
        },
        "system": {
            "debug": settings.debug,
            "cors_origins": settings.cors_origins
        }
    }

@router.put("/")
async def update_settings(updates: SettingsUpdate):
    """Update system configuration settings."""
    updated_fields = []
    
    # Update settings object
    for field, value in updates.dict(exclude_unset=True).items():
        if hasattr(settings, field) and value is not None:
            setattr(settings, field, value)
            updated_fields.append(field)
    
    # Save to environment file if it exists
    env_file = Path(".env")
    if env_file.exists():
        try:
            # Read existing .env
            env_content = {}
            with open(env_file, 'r') as f:
                for line in f:
                    if '=' in line and not line.strip().startswith('#'):
                        key, value = line.strip().split('=', 1)
                        env_content[key] = value
            
            # Update with new values
            field_mapping = {
                "collection_interval": "COLLECTION_INTERVAL",
                "data_retention_weeks": "DATA_RETENTION_WEEKS",
                "llm_backend": "LLM_BACKEND",
                "local_llm_url": "LOCAL_LLM_URL",
                "openai_api_key": "OPENAI_API_KEY",
                "influx_url": "INFLUX_URL",
                "influx_token": "INFLUX_TOKEN",
                "influx_org": "INFLUX_ORG",
                "influx_bucket": "INFLUX_BUCKET"
            }
            
            for field in updated_fields:
                if field in field_mapping:
                    env_key = field_mapping[field]
                    env_content[env_key] = str(getattr(settings, field))
            
            # Write back to .env
            with open(env_file, 'w') as f:
                for key, value in env_content.items():
                    f.write(f"{key}={value}\n")
                    
        except Exception as e:
            # Continue even if .env update fails
            pass
    
    return {
        "message": f"Updated {len(updated_fields)} settings",
        "updated_fields": updated_fields,
        "current_settings": await get_settings()
    }

@router.post("/test-connection")
async def test_connections():
    """Test connectivity to external services (InfluxDB, LLM)."""
    results = {}
    
    # Test InfluxDB connection
    try:
        from influxdb_client import InfluxDBClient
        with InfluxDBClient(
            url=settings.influx_url,
            token=settings.influx_token,
            org=settings.influx_org
        ) as client:
            health = client.health()
            results["influxdb"] = {
                "status": "connected" if health.status == "pass" else "failed",
                "message": health.message or "Connection successful",
                "version": health.version or "unknown"
            }
    except Exception as e:
        results["influxdb"] = {
            "status": "failed",
            "message": str(e)
        }
    
    # Test LLM service
    try:
        if settings.llm_backend == "openai":
            import openai
            openai.api_key = settings.openai_api_key
            # Simple test to verify API key
            models = openai.Model.list()
            results["llm"] = {
                "status": "connected",
                "backend": "openai",
                "message": f"Connected with access to {len(models.data)} models"
            }
        else:
            # Test local LLM service
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{settings.local_llm_url}/api/version") as response:
                    if response.status == 200:
                        results["llm"] = {
                            "status": "connected",
                            "backend": "local",
                            "message": "Local LLM service responding"
                        }
                    else:
                        results["llm"] = {
                            "status": "failed",
                            "backend": "local",
                            "message": f"HTTP {response.status}"
                        }
    except Exception as e:
        results["llm"] = {
            "status": "failed",
            "backend": settings.llm_backend,
            "message": str(e)
        }
    
    return {"connection_tests": results}

@router.get("/metrics")
async def get_available_metrics():
    """Get list of available sensor metrics from InfluxDB."""
    try:
        # This would query InfluxDB for available fields
        # For demo, return static list
        return {
            "metrics": [
                {
                    "name": "temperature",
                    "unit": "°C",
                    "type": "float",
                    "description": "Ambient temperature sensor"
                },
                {
                    "name": "humidity",
                    "unit": "%",
                    "type": "float",
                    "description": "Relative humidity sensor"
                },
                {
                    "name": "co2",
                    "unit": "ppm",
                    "type": "float",
                    "description": "Carbon dioxide concentration"
                },
                {
                    "name": "aqi",
                    "unit": "index",
                    "type": "integer",
                    "description": "Air quality index"
                },
                {
                    "name": "pressure",
                    "unit": "hPa",
                    "type": "float",
                    "description": "Atmospheric pressure"
                },
                {
                    "name": "light_level",
                    "unit": "lux",
                    "type": "float",
                    "description": "Ambient light level"
                }
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch metrics: {str(e)}")

@router.post("/reset")
async def reset_settings():
    """Reset all settings to default values."""
    # Reset to defaults (this would typically reload from defaults)
    default_values = {
        "collection_interval": 30,
        "data_retention_weeks": 4,
        "llm_backend": "local",
        "local_llm_url": "http://localhost:11434",
        "influx_url": "http://localhost:8086",
        "influx_org": "ides",
        "influx_bucket": "sensors"
    }
    
    for field, value in default_values.items():
        setattr(settings, field, value)
    
    return {
        "message": "Settings reset to defaults",
        "current_settings": await get_settings()
    }