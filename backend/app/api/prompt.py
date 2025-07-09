# AI-powered natural language processing endpoint that interprets user queries about sensor data and generates appropriate chart configurations or insights using local or OpenAI LLM services.

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import json
import asyncio

from app.llm.base import LLMService
from app.llm.local_service import LocalLLMService
from app.llm.openai_service import OpenAILLMService
from app.core.config import settings
from app.models.graph import GraphModel

router = APIRouter()

# LLM service instance
llm_service: Optional[LLMService] = None

def get_llm_service() -> LLMService:
    """Get configured LLM service instance."""
    global llm_service
    
    if llm_service is None:
        if settings.llm_backend == "openai" and settings.openai_api_key:
            llm_service = OpenAILLMService(api_key=settings.openai_api_key)
        else:
            llm_service = LocalLLMService(base_url=settings.local_llm_url)
    
    return llm_service

def get_recent_sensor_context() -> Dict[str, Any]:
    """Get recent sensor data for LLM context."""
    try:
        from pathlib import Path
        data_dir = Path(settings.data_dir)
        
        # Find most recent data file
        latest_file = None
        for file_path in data_dir.glob("sensors_*.json"):
            if latest_file is None or file_path.stat().st_mtime > latest_file.stat().st_mtime:
                latest_file = file_path
        
        if latest_file and latest_file.exists():
            with open(latest_file, 'r') as f:
                data = json.load(f)
                
                # Get last 10 data points for context
                context = {}
                for key, values in data.items():
                    if isinstance(values, list) and values:
                        context[key] = values[-10:]  # Last 10 readings
                
                return context
    except Exception:
        pass
    
    # Return dummy data if no real data available
    return {
        "timestamps": [datetime.now().isoformat()],
        "temperature": [22.5],
        "humidity": [45.2],
        "co2": [420],
        "aqi": [35]
    }

@router.post("/")
async def process_prompt(request: Dict[str, str]):
    """Process natural language prompt and return AI response with optional chart configuration."""
    user_prompt = request.get("prompt", "").strip()
    
    if not user_prompt:
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")
    
    try:
        # Get LLM service
        llm = get_llm_service()
        
        # Get recent sensor data for context
        sensor_context = get_recent_sensor_context()
        
        # Create enhanced prompt with context
        enhanced_prompt = f"""
User query: {user_prompt}

Current sensor data context (last readings):
Temperature: {sensor_context.get('temperature', [])[-1] if sensor_context.get('temperature') else 'N/A'}°C
Humidity: {sensor_context.get('humidity', [])[-1] if sensor_context.get('humidity') else 'N/A'}%
CO₂: {sensor_context.get('co2', [])[-1] if sensor_context.get('co2') else 'N/A'} ppm
Air Quality Index: {sensor_context.get('aqi', [])[-1] if sensor_context.get('aqi') else 'N/A'}

Available metrics: temperature, humidity, co2, aqi, pressure, light_level

Please respond with a JSON object containing:
1. "response": A natural language answer to the user's question
2. "chart_config": (optional) If a chart would be helpful, include chart configuration
3. "insights": (optional) Any notable patterns or recommendations

Chart config format (if applicable):
{{
  "chart_type": "line|area|bar",
  "metrics": ["metric1", "metric2"],
  "time_range": "1h|6h|24h|7d",
  "title": "Chart Title"
}}
"""
        
        # Get AI response
        ai_response = await llm.generate_response(enhanced_prompt)
        
        # Parse JSON response
        try:
            parsed_response = json.loads(ai_response)
        except json.JSONDecodeError:
            # Fallback if LLM doesn't return valid JSON
            parsed_response = {
                "response": ai_response,
                "chart_config": None,
                "insights": None
            }
        
        # If chart config is provided, create a temporary graph
        chart_data = None
        if parsed_response.get("chart_config"):
            chart_config = parsed_response["chart_config"]
            chart_data = {
                "id": f"ai_generated_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "title": chart_config.get("title", "AI Generated Chart"),
                "chart_type": chart_config.get("chart_type", "line"),
                "metrics": chart_config.get("metrics", ["temperature"]),
                "time_range": chart_config.get("time_range", "24h"),
                "is_ai_generated": True
            }
        
        return {
            "response": parsed_response.get("response", "I understand your query about the sensor data."),
            "chart_config": chart_data,
            "insights": parsed_response.get("insights"),
            "timestamp": datetime.now().isoformat(),
            "llm_backend": settings.llm_backend
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process prompt: {str(e)}")

@router.post("/forecast")
async def generate_forecast_prompt(request: Dict[str, Any]):
    """Generate forecast-specific AI insights for sensor predictions."""
    metric = request.get("metric", "temperature")
    days_ahead = request.get("days", 7)
    
    try:
        llm = get_llm_service()
        sensor_context = get_recent_sensor_context()
        
        # Get recent values for the requested metric
        recent_values = sensor_context.get(metric, [])
        
        forecast_prompt = f"""
Analyze the recent {metric} readings and provide a forecast for the next {days_ahead} days.

Recent {metric} values: {recent_values}

Please provide:
1. Trend analysis of recent readings
2. Predicted values for the next {days_ahead} days
3. Confidence level in the prediction
4. Any notable patterns or anomalies
5. Recommendations based on the forecast

Respond in JSON format with structured forecast data.
"""
        
        ai_response = await llm.generate_response(forecast_prompt)
        
        try:
            forecast_data = json.loads(ai_response)
        except json.JSONDecodeError:
            forecast_data = {"forecast": ai_response}
        
        return {
            "metric": metric,
            "forecast": forecast_data,
            "timestamp": datetime.now().isoformat(),
            "days_ahead": days_ahead
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate forecast: {str(e)}")

@router.get("/available-metrics")
async def get_available_metrics():
    """Get list of available sensor metrics for AI query context."""
    return {
        "metrics": [
            {"name": "temperature", "unit": "°C", "description": "Ambient temperature"},
            {"name": "humidity", "unit": "%", "description": "Relative humidity"},
            {"name": "co2", "unit": "ppm", "description": "Carbon dioxide concentration"},
            {"name": "aqi", "unit": "index", "description": "Air quality index"},
            {"name": "pressure", "unit": "hPa", "description": "Atmospheric pressure"},
            {"name": "light_level", "unit": "lux", "description": "Light intensity"}
        ]
    }