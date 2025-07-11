# External weather API worker for fetching outdoor environmental data to complement indoor sensors, providing correlation analysis and enhanced forecasting context.

import asyncio
import aiohttp
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List
import random
import numpy as np

from app.core.config import settings

logger = logging.getLogger(__name__)

class ExternalWeatherWorker:
    """Worker for fetching external weather data to complement indoor sensors."""
    
    def __init__(self):
        self.api_key = settings.openai_api_key # Placeholder for a real weather API key
        self.base_url = "https://api.openweathermap.org/data/2.5"
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create an aiohttp client session."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session

    async def fetch_weather_data(self):
        """Fetch current weather data from external API or generate mock data."""
        try:
            logger.info("Fetching external weather data...")
            
            if self.api_key:
                weather_data = await self._fetch_real_weather_data()
            else:
                weather_data = self._generate_mock_weather_data()
            
            await self._save_weather_data(weather_data)
            await self._analyze_indoor_outdoor_correlation(weather_data)
            
            logger.info("External weather data fetch completed successfully.")
            
        except Exception as e:
            logger.error(f"Weather data fetch failed: {e}", exc_info=True)

    async def _fetch_real_weather_data(self) -> Dict[str, Any]:
        """Fetch real weather data from OpenWeatherMap API."""
        session = await self._get_session()
        # Example coordinates for New York
        lat, lon = 40.7128, -74.0060
        url = f"{self.base_url}/weather?lat={lat}&lon={lon}&appid={self.api_key}&units=metric"
        
        async with session.get(url) as response:
            response.raise_for_status()
            data = await response.json()
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "location": {"city": data["name"], "country": data["sys"]["country"]},
                "current": {
                    "temperature": data["main"]["temp"],
                    "humidity": data["main"]["humidity"],
                    "pressure": data["main"]["pressure"],
                    "condition": data["weather"][0]["main"],
                },
            }

    def _generate_mock_weather_data(self) -> Dict[str, Any]:
        """Generate mock weather data for demonstration."""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "location": {"city": "Demo City", "country": "US"},
            "current": {
                "temperature": round(18.0 + random.uniform(-8, 12), 1),
                "humidity": round(max(0, min(100, 60.0 + random.uniform(-20, 30))), 1),
                "pressure": round(1013.25 + random.uniform(-10, 10), 2),
                "condition": random.choice(["Clear", "Clouds", "Rain"]),
            },
        }
    
    async def _save_weather_data(self, weather_data: Dict[str, Any]):
        """Save weather data to a daily JSON file."""
        data_dir = Path(settings.data_dir)
        data_dir.mkdir(exist_ok=True)
        weather_file = data_dir / f"weather_{datetime.utcnow().strftime('%Y_%m_%d')}.json"
        
        try:
            readings = []
            if weather_file.exists():
                with open(weather_file, 'r') as f:
                    readings = json.load(f).get("readings", [])
            
            readings.append(weather_data)
            
            with open(weather_file, 'w') as f:
                json.dump({"readings": readings[-100:]}, f, indent=2) # Keep last 100
            
            logger.debug(f"Weather data saved to {weather_file}")
        except (IOError, json.JSONDecodeError) as e:
            logger.error(f"Failed to save weather data: {e}", exc_info=True)
    
    async def _analyze_indoor_outdoor_correlation(self, weather_data: Dict[str, Any]):
        """Analyze correlation between indoor and outdoor conditions."""
        try:
            indoor_data = await self._load_recent_indoor_data()
            if not indoor_data:
                return
            
            outdoor_temp = weather_data.get("current", {}).get("temperature")
            indoor_temps = indoor_data.get("temperature")

            if outdoor_temp is not None and indoor_temps:
                # Simple correlation coefficient calculation
                correlation = np.corrcoef(
                    np.array(indoor_temps[-len(outdoor_temp):] if isinstance(outdoor_temp, list) else [outdoor_temp] * len(indoor_temps)),
                    np.array(indoor_temps)
                )[0, 1]
                logger.info(f"Indoor/Outdoor temperature correlation: {correlation:.2f}")

        except Exception as e:
            logger.error(f"Correlation analysis failed: {e}", exc_info=True)
    
    async def _load_recent_indoor_data(self) -> Dict[str, Any]:
        """Load recent indoor sensor data for correlation analysis."""
        data_dir = Path(settings.data_dir)
        try:
            sensor_files = list(data_dir.glob("sensors_*.json"))
            if not sensor_files:
                return {}
            
            latest_file = max(sensor_files, key=lambda f: f.stat().st_mtime)
            with open(latest_file, 'r') as f:
                return json.load(f)
        except (IOError, json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to load indoor data: {e}", exc_info=True)
            return {}
    
    async def get_current_weather(self) -> Dict[str, Any]:
        """Get the most recent weather data."""
        data_dir = Path(settings.data_dir)
        weather_file = data_dir / f"weather_{datetime.utcnow().strftime('%Y_%m_%d')}.json"
        if not weather_file.exists():
            return {}
        try:
            with open(weather_file, 'r') as f:
                data = json.load(f)
            return data.get("readings", [])[-1] if data.get("readings") else {}
        except (IOError, json.JSONDecodeError) as e:
            logger.error(f"Failed to get current weather: {e}", exc_info=True)
            return {}
    
    async def cleanup(self):
        """Cleanup resources, like the aiohttp session."""
        if self.session and not self.session.closed:
            await self.session.close()
            logger.info("External weather worker session closed.")
    
    async def get_status(self) -> Dict[str, Any]:
        """Get worker status information."""
        return {
            "worker": "external_weather",
            "status": "running",
            "api_configured": bool(self.api_key),
        }