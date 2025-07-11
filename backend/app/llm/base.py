# Abstract base class for Large Language Model services providing a unified interface for both local and cloud-based AI services with common methods for sensor data analysis.

from abc import ABC, abstractmethod
from typing import Dict, Any, List
import asyncio
import logging

logger = logging.getLogger(__name__)

class LLMService(ABC):
    """Abstract base class for LLM services."""
    
    def __init__(self, **kwargs):
        """Initialize LLM service with configuration."""
        self.config = kwargs
        self.is_available = False
        
    @abstractmethod
    async def generate_response(self, prompt: str, **kwargs) -> str:
        """Generate AI response for given prompt."""
        pass
    
    @abstractmethod
    async def check_availability(self) -> bool:
        """Check if LLM service is available and responding."""
        pass
    
    async def _safe_generate(self, builder, *args, **kwargs) -> Dict[str, Any]:
        """Wrapper for safe prompt generation and response handling."""
        try:
            if not self.is_available:
                await self.check_availability()
            if not self.is_available:
                return {"error": "LLM service is unavailable", "status": "error"}

            prompt = builder(*args)
            response = await self.generate_response(prompt, **kwargs)
            return {"response": response, "status": "success"}
        except Exception as e:
            logger.error(f"LLM generation failed: {e}", exc_info=True)
            return {"error": f"LLM interaction failed: {str(e)}", "status": "error"}

    async def analyze_sensor_data(self, data: Dict[str, Any], query: str) -> Dict[str, Any]:
        """Analyze sensor data and provide insights."""
        return await self._safe_generate(self._build_analysis_prompt, data, query)
    
    async def suggest_chart_config(self, query: str, available_metrics: List[str]) -> Dict[str, Any]:
        """Suggest chart configuration based on user query."""
        return await self._safe_generate(self._build_chart_config_prompt, query, available_metrics)
    
    async def generate_forecast_insights(self, metric: str, historical_data: List[float]) -> Dict[str, Any]:
        """Generate insights about forecast data."""
        return await self._safe_generate(self._build_forecast_prompt, metric, historical_data)
    
    def _build_analysis_prompt(self, data: Dict[str, Any], query: str) -> str:
        """Build prompt for sensor data analysis."""
        return f"""
Analyze the following sensor data and answer this question: {query}

Sensor Data:
{self._format_sensor_data(data)}

Please provide:
1. A clear answer to the question
2. Notable patterns or trends
3. Any recommendations or insights
4. If helpful, suggest a chart type to visualize the data

Keep the response concise and practical.
"""
    
    def _build_chart_config_prompt(self, query: str, metrics: List[str]) -> str:
        """Build prompt for chart configuration suggestions."""
        return f"""
User wants to visualize: {query}

Available metrics: {', '.join(metrics)}

Suggest a chart configuration in JSON format:
{{
  "chart_type": "line|area|bar|scatter",
  "metrics": ["metric1", "metric2"],
  "time_range": "1h|6h|24h|7d",
  "title": "Descriptive Title",
  "insights": "Why this visualization is helpful"
}}

Consider what chart type best represents the requested data.
"""
    
    def _build_forecast_prompt(self, metric: str, data: List[float]) -> str:
        """Build prompt for forecast analysis."""
        return f"""
Analyze the forecast for {metric} with recent values: {data[-10:]}

Provide insights about:
1. Trend direction (increasing, decreasing, stable)
2. Seasonality or patterns
3. Confidence in the forecast
4. Potential factors affecting the metric
5. Recommended actions based on the forecast

Keep the response practical and actionable.
"""
    
    def _format_sensor_data(self, data: Dict[str, Any]) -> str:
        """Format sensor data for LLM prompt."""
        formatted = []
        for metric, values in data.items():
            if isinstance(values, list) and values:
                if metric == "timestamps":
                    continue
                latest = values[-1]
                avg = sum(values) / len(values)
                formatted.append(f"{metric}: {latest} (avg: {avg:.2f})")
        return "\n".join(formatted)
    
    async def health_check(self) -> Dict[str, Any]:
        """Check service health and return status."""
        try:
            self.is_available = await self.check_availability()
            return {
                "service": self.__class__.__name__,
                "status": "healthy" if self.is_available else "unavailable",
                "config": {k: v for k, v in self.config.items() if "key" not in k.lower()}
            }
        except Exception as e:
            logger.error(f"LLM health check for {self.__class__.__name__} failed: {e}", exc_info=True)
            return {
                "service": self.__class__.__name__,
                "status": "error",
                "error": str(e)
            }