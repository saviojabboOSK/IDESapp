# External weather API worker for fetching outdoor environmental data to complement indoor sensors, providing correlation analysis and enhanced forecasting context.

import asyncio
import aiohttp
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

class ExternalWeatherWorker:
    """Worker for fetching external weather data to complement indoor sensors."""
    
    def __init__(self):
        self.last_fetch_time = datetime.now()
        self.api_key = None  # Would be configured in settings
        self.base_url = "https://api.openweathermap.org/data/2.5"
        self.session = None
        
    async def fetch_weather_data(self):
        """Fetch current weather data from external API."""
        try:
            logger.info("Fetching external weather data...")
            
            # For demo, generate mock weather data
            # In production, this would call actual weather APIs
            weather_data = await self._fetch_mock_weather_data()
            
            # Save weather data
            await self._save_weather_data(weather_data)
            
            # Calculate correlations with indoor data
            correlations = await self._analyze_indoor_outdoor_correlation(weather_data)
            
            self.last_fetch_time = datetime.now()
            logger.info("External weather data fetch completed")
            
        except Exception as e:
            logger.error(f"Weather data fetch failed: {e}")
    
    async def _fetch_mock_weather_data(self) -> Dict[str, Any]:
        """Generate mock weather data for demonstration."""
        import random
        
        # Simulate realistic outdoor conditions
        base_temp = 18.0 + random.uniform(-8, 12)  # Outdoor temp range
        base_humidity = 60.0 + random.uniform(-20, 30)
        wind_speed = random.uniform(0, 15)
        pressure = 1013.25 + random.uniform(-10, 10)
        
        # Weather conditions
        conditions = ["clear", "partly_cloudy", "cloudy", "rain", "snow"]
        condition = random.choice(conditions)
        
        weather_data = {
            "timestamp": datetime.now().isoformat(),
            "location": {
                "city": "Demo City",
                "country": "US",
                "latitude": 40.7128,
                "longitude": -74.0060
            },
            "current": {
                "temperature": round(base_temp, 1),
                "humidity": max(0, min(100, round(base_humidity, 1))),
                "pressure": round(pressure, 2),
                "wind_speed": round(wind_speed, 1),
                "wind_direction": random.randint(0, 360),
                "condition": condition,
                "visibility": random.uniform(5, 20),
                "uv_index": max(0, random.randint(0, 11)),
                "air_quality": {
                    "aqi": random.randint(20, 150),
                    "pm25": random.uniform(5, 50),
                    "pm10": random.uniform(10, 80),
                    "co": random.uniform(0.1, 2.0),
                    "no2": random.uniform(10, 100),
                    "o3": random.uniform(50, 200)
                }
            },
            "forecast": {
                "next_24h": [
                    {
                        "hour": i,
                        "temperature": round(base_temp + random.uniform(-3, 3), 1),
                        "humidity": max(0, min(100, round(base_humidity + random.uniform(-10, 10), 1))),
                        "condition": random.choice(conditions)
                    }
                    for i in range(24)
                ]
            }
        }
        
        return weather_data
    
    async def _save_weather_data(self, weather_data: Dict[str, Any]):
        """Save weather data to JSON file."""
        try:
            data_dir = Path(settings.data_dir)
            data_dir.mkdir(exist_ok=True)
            
            # Save to daily weather file
            today = datetime.now().strftime("%Y_%m_%d")
            weather_file = data_dir / f"weather_{today}.json"
            
            # Load existing data
            existing_data = {"readings": []}
            if weather_file.exists():
                try:
                    with open(weather_file, 'r') as f:
                        existing_data = json.load(f)
                except Exception:
                    pass
            
            # Add new reading
            existing_data["readings"].append(weather_data)
            
            # Keep only last 100 readings per day
            existing_data["readings"] = existing_data["readings"][-100:]
            existing_data["last_updated"] = datetime.now().isoformat()
            
            # Save updated data
            with open(weather_file, 'w') as f:
                json.dump(existing_data, f, indent=2)
            
            logger.debug(f"Weather data saved to {weather_file}")
            
        except Exception as e:
            logger.error(f"Failed to save weather data: {e}")
    
    async def _analyze_indoor_outdoor_correlation(self, weather_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze correlation between indoor and outdoor conditions."""
        try:
            # Load recent indoor data
            indoor_data = await self._load_recent_indoor_data()
            
            if not indoor_data:
                return {"error": "No indoor data available for correlation"}
            
            outdoor_current = weather_data.get("current", {})
            
            # Calculate simple correlations
            correlations = {
                "timestamp": datetime.now().isoformat(),
                "outdoor_conditions": {
                    "temperature": outdoor_current.get("temperature"),
                    "humidity": outdoor_current.get("humidity"),
                    "pressure": outdoor_current.get("pressure"),
                    "air_quality": outdoor_current.get("air_quality", {}).get("aqi")
                },
                "indoor_averages": {},
                "temperature_correlation": {
                    "coefficient": 0.65,  # Mock correlation
                    "description": "Moderate positive correlation between outdoor and indoor temperature"
                },
                "humidity_correlation": {
                    "coefficient": 0.42,
                    "description": "Weak positive correlation between outdoor and indoor humidity"
                },
                "pressure_correlation": {
                    "coefficient": 0.89,
                    "description": "Strong positive correlation - pressure equalizes quickly"
                },
                "insights": []
            }
            
            # Calculate indoor averages
            for metric in ["temperature", "humidity", "pressure"]:
                if metric in indoor_data:
                    values = indoor_data[metric][-10:]  # Last 10 readings
                    if values:
                        correlations["indoor_averages"][metric] = sum(values) / len(values)
            
            # Generate insights
            indoor_temp = correlations["indoor_averages"].get("temperature", 0)
            outdoor_temp = outdoor_current.get("temperature", 0)
            
            if outdoor_temp - indoor_temp > 5:
                correlations["insights"].append("Outdoor temperature significantly higher than indoor")
            elif indoor_temp - outdoor_temp > 5:
                correlations["insights"].append("Indoor heating appears effective in cold weather")
            
            if outdoor_current.get("humidity", 0) > 80:
                correlations["insights"].append("High outdoor humidity may affect indoor comfort")
            
            return correlations
            
        except Exception as e:
            logger.error(f"Correlation analysis failed: {e}")
            return {"error": str(e)}
    
    async def _load_recent_indoor_data(self) -> Dict[str, Any]:
        """Load recent indoor sensor data for correlation analysis."""
        try:
            data_dir = Path(settings.data_dir)
            
            # Find most recent sensor data file
            latest_file = None
            for file_path in data_dir.glob("sensors_*.json"):
                if latest_file is None or file_path.stat().st_mtime > latest_file.stat().st_mtime:
                    latest_file = file_path
            
            if latest_file and latest_file.exists():
                with open(latest_file, 'r') as f:
                    return json.load(f)
            
        except Exception as e:
            logger.error(f"Failed to load indoor data: {e}")
        
        return {}
    
    async def get_current_weather(self) -> Dict[str, Any]:
        """Get current weather data."""
        try:
            data_dir = Path(settings.data_dir)
            today = datetime.now().strftime("%Y_%m_%d")
            weather_file = data_dir / f"weather_{today}.json"
            
            if weather_file.exists():
                with open(weather_file, 'r') as f:
                    data = json.load(f)
                    
                if data.get("readings"):
                    return data["readings"][-1]  # Most recent reading
            
        except Exception as e:
            logger.error(f"Failed to get current weather: {e}")
        
        return {}
    
    async def get_weather_history(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get weather history for specified number of days."""
        history = []
        
        try:
            data_dir = Path(settings.data_dir)
            
            for i in range(days):
                date = datetime.now() - timedelta(days=i)
                date_str = date.strftime("%Y_%m_%d")
                weather_file = data_dir / f"weather_{date_str}.json"
                
                if weather_file.exists():
                    with open(weather_file, 'r') as f:
                        data = json.load(f)
                        
                    if data.get("readings"):
                        # Get daily summary (last reading of the day)
                        history.append({
                            "date": date_str,
                            "data": data["readings"][-1]
                        })
                        
        except Exception as e:
            logger.error(f"Failed to get weather history: {e}")
        
        return history
    
    async def get_correlation_insights(self) -> Dict[str, Any]:
        """Get insights about indoor/outdoor correlations."""
        try:
            # This would analyze historical correlations
            # For now, return sample insights
            
            return {
                "summary": "Indoor/Outdoor Environmental Correlation Analysis",
                "period": "Last 7 days",
                "key_findings": [
                    "Indoor temperature follows outdoor trends with 2-3 hour delay",
                    "HVAC system maintains stable indoor conditions during extreme weather",
                    "Indoor air quality shows minimal correlation with outdoor AQI",
                    "Pressure changes are reflected indoors within 30 minutes"
                ],
                "recommendations": [
                    "Consider pre-cooling during hot outdoor temperature forecasts",
                    "Monitor indoor humidity when outdoor humidity exceeds 80%",
                    "Outdoor air quality alerts could trigger indoor air filtration"
                ],
                "correlations": {
                    "temperature": 0.65,
                    "humidity": 0.42,
                    "pressure": 0.89,
                    "air_quality": 0.15
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get correlation insights: {e}")
            return {"error": str(e)}
    
    async def cleanup(self):
        """Cleanup resources."""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def get_status(self) -> Dict[str, Any]:
        """Get worker status information."""
        return {
            "worker": "external_weather",
            "status": "running",
            "last_fetch": self.last_fetch_time.isoformat(),
            "api_configured": bool(self.api_key),
            "base_url": self.base_url
        }