# System settings API for configuring data collection intervals, LLM backend selection, data retention policies, and InfluxDB connection parameters with validation.

from fastapi import APIRouter, HTTPException, Depends, status
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from pathlib import Path
import asyncio
import aiohttp
from dotenv import dotenv_values, set_key

from app.core.config import settings
from app.llm.local_service import LocalLLMService
from app.llm.openai_service import OpenAILLMService

router = APIRouter()

class SettingsUpdate(BaseModel):
    """Model for settings update requests with validation."""
    collection_interval: Optional[int] = Field(None, ge=10, le=3600)
    data_retention_weeks: Optional[int] = Field(None, ge=1, le=52)
    llm_backend: Optional[str] = Field(None, pattern="^(local|openai)$")
    local_llm_url: Optional[str] = Field(None)
    openai_api_key: Optional[str] = Field(None)
    influx_url: Optional[str] = Field(None)
    influx_token: Optional[str] = Field(None)
    influx_org: Optional[str] = Field(None)
    influx_bucket: Optional[str] = Field(None)

def get_settings_response() -> Dict[str, Any]:
    """Constructs the settings response dictionary."""
    return {
        "data_collection": {
            "collection_interval": settings.collection_interval,
            "data_retention_weeks": settings.data_retention_weeks,
            "data_dir": settings.data_dir,
        },
        "llm_configuration": {
            "backend": settings.llm_backend,
            "local_url": settings.local_llm_url,
            "openai_configured": bool(settings.openai_api_key),
        },
        "database": {
            "influx_url": settings.influx_url,
            "influx_org": settings.influx_org,
            "influx_bucket": settings.influx_bucket,
            "influx_configured": bool(settings.influx_token),
        },
        "system": {
            "debug": settings.debug,
            "cors_origins": settings.cors_origins,
        },
    }

@router.get("/", response_model=Dict[str, Any])
async def get_settings():
    """Get current system configuration settings."""
    return get_settings_response()

@router.put("/", response_model=Dict[str, Any])
async def update_settings(updates: SettingsUpdate):
    """Update system configuration settings and save to .env file."""
    updated_fields = []
    env_file = Path(".env")

    update_data = updates.dict(exclude_unset=True)

    for field, value in update_data.items():
        if hasattr(settings, field):
            setattr(settings, field, value)
            # Use set_key to update the .env file
            set_key(str(env_file), field.upper(), str(value))
            updated_fields.append(field)

    if not updated_fields:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No valid settings provided for update.")

    return {
        "message": f"Updated {len(updated_fields)} settings.",
        "updated_fields": updated_fields,
        "current_settings": get_settings_response(),
    }

async def test_influxdb_connection() -> Dict[str, Any]:
    """Test connectivity to InfluxDB."""
    try:
        from influxdb_client.client.influxdb_client_async import InfluxDBClientAsync
        async with InfluxDBClientAsync(
            url=settings.influx_url, token=settings.influx_token, org=settings.influx_org
        ) as client:
            health = await client.health()
            if health.status == "pass":
                return {"status": "connected", "message": health.message, "version": health.version}
            return {"status": "failed", "message": health.message}
    except Exception as e:
        return {"status": "failed", "message": str(e)}

async def test_llm_connection() -> Dict[str, Any]:
    """Test connectivity to the configured LLM service."""
    try:
        if settings.llm_backend == "openai":
            service = OpenAILLMService(api_key=settings.openai_api_key)
        else:
            service = LocalLLMService(base_url=settings.local_llm_url)
        
        if await service.check_availability():
            return {"status": "connected", "backend": settings.llm_backend}
        return {"status": "failed", "backend": settings.llm_backend, "message": "Service is not available."}
    except Exception as e:
        return {"status": "failed", "backend": settings.llm_backend, "message": str(e)}

@router.post("/test-connections", status_code=status.HTTP_200_OK)
async def test_connections():
    """Test connectivity to external services (InfluxDB, LLM) concurrently."""
    results = await asyncio.gather(test_influxdb_connection(), test_llm_connection())
    return {"connection_tests": {"influxdb": results[0], "llm": results[1]}}

@router.get("/metrics", response_model=Dict[str, List[Dict[str, str]]])
async def get_available_metrics():
    """Get list of available sensor metrics."""
    # In a real application, this could be dynamic based on data
    return {
        "metrics": [
            {"name": "temperature", "unit": "°C", "description": "Ambient temperature"},
            {"name": "humidity", "unit": "%", "description": "Relative humidity"},
            {"name": "co2", "unit": "ppm", "description": "Carbon dioxide concentration"},
            {"name": "aqi", "unit": "index", "description": "Air quality index"},
            {"name": "pressure", "unit": "hPa", "description": "Atmospheric pressure"},
            {"name": "light_level", "unit": "lux", "description": "Ambient light level"},
        ]
    }

@router.post("/reset", status_code=status.HTTP_200_OK)
async def reset_settings():
    """Reset all settings to their default values."""
    # This assumes default values are defined in the Settings class
    # Re-initializing the settings object will load defaults
    settings.__init__()
    
    # Persist default values to .env
    env_file = Path(".env")
    default_settings = SettingsUpdate(**settings.dict())
    for field, value in default_settings.dict(exclude_unset=True).items():
         if value is not None:
            set_key(str(env_file), field.upper(), str(value))

    return {
        "message": "Settings have been reset to their default values.",
        "current_settings": get_settings_response(),
    }