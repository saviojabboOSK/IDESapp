# OpenAI API service implementation for cloud-based AI analysis of sensor data with GPT models, providing advanced natural language processing and chart generation capabilities.

import openai
import asyncio
import json
import logging
from typing import Dict, Any, Optional, List

from app.llm.base import LLMService

logger = logging.getLogger(__name__)

class OpenAILLMService(LLMService):
    """OpenAI API service implementation."""
    
    def __init__(self, api_key: str, model: str = "gpt-3.5-turbo", **kwargs):
        super().__init__(**kwargs)
        self.api_key = api_key
        self.model = model
        openai.api_key = api_key
        
    async def generate_response(self, prompt: str, **kwargs) -> str:
        """Generate response using OpenAI API."""
        try:
            # Prepare messages for chat completion
            messages = [
                {
                    "role": "system",
                    "content": "You are an expert in indoor environmental monitoring and data analysis. Provide clear, practical insights about sensor data and building conditions. When suggesting charts, use JSON format."
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ]
            
            # Make async API call
            response = await asyncio.to_thread(
                openai.ChatCompletion.create,
                model=self.model,
                messages=messages,
                temperature=kwargs.get("temperature", 0.7),
                max_tokens=kwargs.get("max_tokens", 1000),
                top_p=kwargs.get("top_p", 0.9)
            )
            
            if response.choices:
                return response.choices[0].message.content.strip()
            else:
                return "No response generated from OpenAI"
                
        except openai.error.AuthenticationError:
            logger.error("OpenAI authentication failed - check API key")
            return "Error: OpenAI authentication failed. Please check your API key."
        except openai.error.RateLimitError:
            logger.error("OpenAI rate limit exceeded")
            return "Error: OpenAI rate limit exceeded. Please try again later."
        except openai.error.APIError as e:
            logger.error(f"OpenAI API error: {e}")
            return f"Error: OpenAI API error - {str(e)}"
        except Exception as e:
            logger.error(f"OpenAI unexpected error: {e}")
            return f"Error: Unexpected error with OpenAI service - {str(e)}"
    
    async def check_availability(self) -> bool:
        """Check if OpenAI API is available and API key is valid."""
        try:
            # Test with a simple request
            response = await asyncio.to_thread(
                openai.ChatCompletion.create,
                model=self.model,
                messages=[{"role": "user", "content": "Test"}],
                max_tokens=5
            )
            
            self.is_available = bool(response.choices)
            return self.is_available
            
        except Exception as e:
            logger.warning(f"OpenAI availability check failed: {e}")
            self.is_available = False
            return False
    
    async def analyze_sensor_data(self, data: Dict[str, Any], query: str) -> Dict[str, Any]:
        """Enhanced sensor data analysis with OpenAI."""
        # Create structured prompt for better results
        enhanced_prompt = f"""
Analyze the following indoor environmental sensor data and answer: {query}

Sensor Data:
{self._format_sensor_data(data)}

Please provide a JSON response with the following structure:
{{
  "answer": "Direct answer to the question",
  "insights": ["Key insight 1", "Key insight 2", "Key insight 3"],
  "recommendations": ["Action 1", "Action 2"],
  "chart_suggestion": {{
    "type": "line|area|bar",
    "metrics": ["relevant_metrics"],
    "reason": "Why this chart would be helpful"
  }},
  "concerns": ["Any concerning patterns or values"]
}}

Focus on practical, actionable insights for building management.
"""
        
        try:
            response = await self.generate_response(enhanced_prompt)
            
            # Try to parse JSON response
            try:
                parsed = json.loads(response)
                return {
                    "analysis": parsed,
                    "status": "success",
                    "model": self.model,
                    "service": "openai"
                }
            except json.JSONDecodeError:
                # Fallback to plain text response
                return {
                    "analysis": {"answer": response},
                    "status": "success",
                    "model": self.model,
                    "service": "openai"
                }
                
        except Exception as e:
            return {
                "analysis": f"OpenAI analysis failed: {str(e)}",
                "status": "error",
                "model": self.model,
                "service": "openai"
            }
    
    async def suggest_chart_config(self, query: str, available_metrics: List[str]) -> Dict[str, Any]:
        """Advanced chart configuration with OpenAI."""
        config_prompt = f"""
User wants to visualize: "{query}"

Available sensor metrics: {', '.join(available_metrics)}

Create a comprehensive chart configuration in JSON format:
{{
  "chart_type": "line|area|bar|scatter|pie",
  "metrics": ["selected_metrics"],
  "time_range": "1h|6h|24h|7d|30d",
  "title": "Descriptive chart title",
  "settings": {{
    "color_scheme": ["#color1", "#color2"],
    "show_legend": true,
    "show_grid": true,
    "smooth_lines": true
  }},
  "explanation": "Why this configuration is optimal",
  "insights": "What patterns this chart will reveal"
}}

Consider:
- Best chart type for the data relationships
- Appropriate time range for the query
- Color choices for accessibility
- What insights the visualization will provide
"""
        
        try:
            response = await self.generate_response(config_prompt)
            parsed = json.loads(response)
            return {
                "config": parsed,
                "status": "success",
                "service": "openai"
            }
        except Exception as e:
            return {
                "config": f"Chart config generation failed: {str(e)}",
                "status": "error",
                "service": "openai"
            }
    
    async def generate_forecast_insights(self, metric: str, historical_data: List[float]) -> Dict[str, Any]:
        """Generate detailed forecast insights with OpenAI."""
        # Calculate basic statistics
        if historical_data:
            recent_avg = sum(historical_data[-5:]) / len(historical_data[-5:])
            overall_avg = sum(historical_data) / len(historical_data)
            trend = "increasing" if recent_avg > overall_avg else "decreasing" if recent_avg < overall_avg else "stable"
        else:
            recent_avg = overall_avg = 0
            trend = "unknown"
        
        forecast_prompt = f"""
Analyze the forecast for {metric} with the following context:

Historical data points: {historical_data[-20:]}  # Last 20 readings
Recent average: {recent_avg:.2f}
Overall average: {overall_avg:.2f}
Apparent trend: {trend}

Provide detailed forecast insights in JSON format:
{{
  "trend_analysis": "Detailed trend description",
  "confidence_level": "high|medium|low",
  "key_factors": ["Factor 1", "Factor 2", "Factor 3"],
  "predictions": {{
    "next_24h": "Prediction for next 24 hours",
    "next_week": "Prediction for next week"
  }},
  "recommendations": ["Recommended action 1", "Recommended action 2"],
  "risk_assessment": "Any risks or concerns",
  "seasonal_notes": "Seasonal or cyclical patterns"
}}

Consider typical patterns for {metric} in indoor environments.
"""
        
        try:
            response = await self.generate_response(forecast_prompt)
            parsed = json.loads(response)
            return {
                "insights": parsed,
                "status": "success",
                "service": "openai"
            }
        except Exception as e:
            return {
                "insights": f"Forecast insights failed: {str(e)}",
                "status": "error",
                "service": "openai"
            }
    
    def get_service_info(self) -> Dict[str, Any]:
        """Get service configuration information."""
        return {
            "service_type": "openai",
            "model": self.model,
            "is_available": self.is_available,
            "api_key_configured": bool(self.api_key),
            "description": "OpenAI GPT API service"
        }