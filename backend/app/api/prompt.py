# AI-powered natural language processing endpoint that interprets user queries about sensor data and generates appropriate chart configurations or insights using local or OpenAI LLM services.

from fastapi import APIRouter, HTTPException, Depends, status
from typing import Dict, Any, Optional, List
from datetime import datetime
import json
import asyncio
from functools import lru_cache
from pathlib import Path

from app.llm.base import LLMService
from app.llm.local_service import LocalLLMService
from app.llm.openai_service import OpenAILLMService
from app.core.config import settings
from app.models.graph import GraphModel, GraphSettings, GraphLayout
from app.api.graphs import save_graph_to_file as save_graph_file

router = APIRouter()

@lru_cache(maxsize=1)
def get_llm_service() -> LLMService:
    """Get configured LLM service instance, cached for performance."""
    if settings.llm_backend == "openai" and settings.openai_api_key:
        return OpenAILLMService(api_key=settings.openai_api_key)
    return LocalLLMService(base_url=settings.local_llm_url)

async def get_recent_sensor_context() -> Dict[str, Any]:
    """Asynchronously get recent sensor data for LLM context."""
    data_dir = Path(settings.data_dir)
    
    try:
        files = list(data_dir.glob("sensors_*.json"))
        if not files:
            return {}
        
        latest_file = max(files, key=lambda f: f.stat().st_mtime)
        
        with open(latest_file, 'r') as f:
            data = json.load(f)
        
        return {key: values[-10:] for key, values in data.items() if isinstance(values, list) and values}
    except (IOError, json.JSONDecodeError, ValueError) as e:
        print(f"Could not read sensor context: {e}")
        return {}

def build_enhanced_prompt(user_prompt: str, context: Dict[str, Any], metrics: List[str]) -> str:
    """Build a detailed prompt for the LLM."""
    context_summary = "\n".join(
        f"- {key.capitalize()}: {values[-1] if values else 'N/A'}"
        for key, values in context.items()
    )
    
    return f"""
User query: "{user_prompt}"

Current sensor data context (last readings):
{context_summary}

Available metrics: {', '.join(metrics)}

Please respond with a JSON object containing:
1. "response": A natural language answer to the user's question.
2. "chart_config": (optional) If a chart would be helpful, include a valid chart configuration.
3. "insights": (optional) Any notable patterns or recommendations.

Chart config format (if applicable):
{{
  "chart_type": "line|area|bar",
  "metrics": ["metric1", "metric2"],
  "time_range": "1h|6h|24h|7d",
  "title": "Chart Title"
}}
"""

async def create_ai_graph(chart_config: Dict[str, Any]) -> Optional[GraphModel]:
    """Create and save a graph model from AI-generated config."""
    try:
        graph = GraphModel(
            id=f"ai-generated-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}",
            title=chart_config.get("title", "AI Generated Chart"),
            chart_type=chart_config.get("chart_type", "line"),
            metrics=chart_config.get("metrics", ["temperature"]),
            time_range=chart_config.get("time_range", "24h"),
            is_ai_generated=True,
            settings=GraphSettings(),
            layout=GraphLayout(x=0, y=0, width=8, height=4)
        )
        await save_graph_file(graph)
        return graph
    except Exception as e:
        print(f"Error creating AI graph: {e}")
        return None

@router.post("/", status_code=status.HTTP_200_OK)
async def process_prompt(request: Dict[str, str], llm: LLMService = Depends(get_llm_service)):
    """Process natural language prompt and return AI response with optional chart configuration."""
    user_prompt = request.get("prompt", "").strip()
    if not user_prompt:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Prompt cannot be empty")

    try:
        metrics_info = await get_available_metrics()
        available_metrics = [m['name'] for m in metrics_info['metrics']]
        sensor_context = await get_recent_sensor_context()
        
        enhanced_prompt = build_enhanced_prompt(user_prompt, sensor_context, available_metrics)
        
        ai_response_str = await llm.generate_response(enhanced_prompt)
        
        try:
            ai_response = json.loads(ai_response_str)
        except json.JSONDecodeError:
            ai_response = {"response": ai_response_str}

        chart_data = None
        if chart_config := ai_response.get("chart_config"):
            if graph_model := await create_ai_graph(chart_config):
                chart_data = graph_model.dict()

        return {
            "response": ai_response.get("response", "Could not generate a response."),
            "chart_config": chart_data,
            "insights": ai_response.get("insights"),
            "timestamp": datetime.utcnow().isoformat(),
            "llm_backend": settings.llm_backend,
        }
        
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to process prompt: {str(e)}")

@router.post("/forecast", status_code=status.HTTP_200_OK)
async def generate_forecast_prompt(request: Dict[str, Any], llm: LLMService = Depends(get_llm_service)):
    """Generate forecast-specific AI insights for sensor predictions."""
    metric = request.get("metric", "temperature")
    days_ahead = request.get("days", 7)
    
    try:
        sensor_context = await get_recent_sensor_context()
        recent_values = sensor_context.get(metric, [])
        
        forecast_prompt = f"""
Analyze the recent {metric} readings and provide a forecast for the next {days_ahead} days.
Recent values: {recent_values}
Respond in JSON with trend analysis, predicted values, confidence, and recommendations.
"""
        
        ai_response_str = await llm.generate_response(forecast_prompt)
        
        try:
            forecast_data = json.loads(ai_response_str)
        except json.JSONDecodeError:
            forecast_data = {"forecast": ai_response_str}
        
        return {
            "metric": metric,
            "forecast": forecast_data,
            "timestamp": datetime.utcnow().isoformat(),
            "days_ahead": days_ahead,
        }
        
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to generate forecast: {str(e)}")

@router.get("/available-metrics", response_model=Dict[str, List[Dict[str, str]]])
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