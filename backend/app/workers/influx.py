# InfluxDB worker for automated sensor data collection, JSON snapshot creation, and real-time WebSocket broadcasting to maintain synchronized dashboard state with 30-second intervals.

import asyncio
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional

try:
    from influxdb_client import InfluxDBClient
    from influxdb_client.client.query_api import QueryApi
except ImportError:
    # Fallback for demo without InfluxDB
    InfluxDBClient = None
    QueryApi = None

from app.core.config import settings

logger = logging.getLogger(__name__)

class InfluxWorker:
    """Worker for collecting sensor data from InfluxDB and creating JSON snapshots."""
    
    def __init__(self):
        self.client: Optional[InfluxDBClient] = None
        self.query_api: Optional[QueryApi] = None
        self.last_collection_time = datetime.now()
        self.connection_manager = None  # Will be set from main app
        
    async def initialize(self):
        """Initialize InfluxDB connection."""
        if InfluxDBClient is None:
            logger.warning("InfluxDB client not available - using mock data")
            return
            
        try:
            self.client = InfluxDBClient(
                url=settings.influx_url,
                token=settings.influx_token,
                org=settings.influx_org
            )
            self.query_api = self.client.query_api()
            
            # Test connection
            health = self.client.health()
            if health.status == "pass":
                logger.info("InfluxDB connection established")
            else:
                logger.error(f"InfluxDB health check failed: {health.message}")
                
        except Exception as e:
            logger.error(f"Failed to initialize InfluxDB connection: {e}")
            self.client = None
    
    async def collect_sensor_data(self):
        """Collect latest sensor data and update JSON snapshots."""
        try:
            logger.info("Starting sensor data collection...")
            
            # Get current data
            if self.client and self.query_api:
                sensor_data = await self._query_influx_data()
            else:
                # Generate mock data for demo
                sensor_data = self._generate_mock_data()
            
            # Save to JSON snapshot
            await self._save_to_json_snapshot(sensor_data)
            
            # Broadcast to WebSocket clients
            await self._broadcast_update(sensor_data)
            
            self.last_collection_time = datetime.now()
            logger.info(f"Sensor data collection completed: {len(sensor_data.get('timestamps', []))} points")
            
        except Exception as e:
            logger.error(f"Sensor data collection failed: {e}")
    
    async def _query_influx_data(self) -> Dict[str, Any]:
        """Query recent sensor data from InfluxDB."""
        try:
            # Query for recent data (last 1 hour)
            query = f'''
            from(bucket: "{settings.influx_bucket}")
                |> range(start: -1h)
                |> filter(fn: (r) => r["_measurement"] == "sensors")
                |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
                |> sort(columns: ["_time"])
            '''
            
            tables = await asyncio.to_thread(self.query_api.query, query)
            
            # Process results
            data = {
                "timestamps": [],
                "temperature": [],
                "humidity": [],
                "co2": [],
                "aqi": [],
                "pressure": [],
                "light_level": []
            }
            
            for table in tables:
                for record in table.records:
                    timestamp = record.get_time().isoformat()
                    data["timestamps"].append(timestamp)
                    
                    # Extract sensor values
                    data["temperature"].append(record.values.get("temperature", 0.0))
                    data["humidity"].append(record.values.get("humidity", 0.0))
                    data["co2"].append(record.values.get("co2", 0.0))
                    data["aqi"].append(record.values.get("aqi", 0))
                    data["pressure"].append(record.values.get("pressure", 0.0))
                    data["light_level"].append(record.values.get("light_level", 0.0))
            
            return data
            
        except Exception as e:
            logger.error(f"InfluxDB query failed: {e}")
            return self._generate_mock_data()
    
    def _generate_mock_data(self) -> Dict[str, Any]:
        """Generate mock sensor data for demonstration."""
        import random
        
        now = datetime.now()
        data = {
            "timestamps": [],
            "temperature": [],
            "humidity": [],
            "co2": [],
            "aqi": [],
            "pressure": [],
            "light_level": []
        }
        
        # Generate 60 data points (last hour)
        for i in range(60):
            timestamp = (now - timedelta(minutes=59-i)).isoformat()
            data["timestamps"].append(timestamp)
            
            # Realistic sensor values with some variation
            base_temp = 22.0 + random.uniform(-2, 2)
            base_humidity = 45.0 + random.uniform(-5, 5)
            base_co2 = 420 + random.uniform(-50, 100)
            base_aqi = 35 + random.randint(-10, 15)
            base_pressure = 1013.25 + random.uniform(-5, 5)
            base_light = 300 + random.uniform(-50, 200)
            
            data["temperature"].append(round(base_temp, 1))
            data["humidity"].append(round(base_humidity, 1))
            data["co2"].append(round(base_co2, 0))
            data["aqi"].append(max(0, base_aqi))
            data["pressure"].append(round(base_pressure, 2))
            data["light_level"].append(round(base_light, 1))
        
        return data
    
    async def _save_to_json_snapshot(self, data: Dict[str, Any]):
        """Save sensor data to weekly JSON snapshot file."""
        try:
            # Create data directory
            data_dir = Path(settings.data_dir)
            data_dir.mkdir(exist_ok=True)
            
            # Generate filename based on week
            now = datetime.now()
            week_start = now - timedelta(days=now.weekday())
            filename = f"sensors_{week_start.strftime('%Y_%m_%d')}.json"
            file_path = data_dir / filename
            
            # Load existing data if file exists
            existing_data = {}
            if file_path.exists():
                try:
                    with open(file_path, 'r') as f:
                        existing_data = json.load(f)
                except Exception as e:
                    logger.warning(f"Failed to load existing data: {e}")
            
            # Merge new data with existing
            merged_data = existing_data.copy()
            for key, values in data.items():
                if key not in merged_data:
                    merged_data[key] = []
                
                # Add only new timestamps
                existing_timestamps = set(merged_data.get("timestamps", []))
                new_points = []
                
                for i, timestamp in enumerate(values):
                    if timestamp not in existing_timestamps:
                        new_points.append(i)
                
                # Append new data points
                for i in new_points:
                    if key == "timestamps":
                        merged_data[key].append(values[i])
                    elif i < len(values):
                        merged_data[key].append(values[i])
            
            # Save updated data
            with open(file_path, 'w') as f:
                json.dump(merged_data, f, indent=2)
            
            logger.debug(f"Saved sensor snapshot to {filename}")
            
        except Exception as e:
            logger.error(f"Failed to save JSON snapshot: {e}")
    
    async def _broadcast_update(self, data: Dict[str, Any]):
        """Broadcast sensor data update via WebSocket."""
        try:
            if self.connection_manager:
                # Get latest data point for broadcast
                if data.get("timestamps"):
                    latest_idx = -1
                    update_data = {
                        "timestamp": data["timestamps"][latest_idx],
                        "metrics": {}
                    }
                    
                    for metric, values in data.items():
                        if metric != "timestamps" and values:
                            update_data["metrics"][metric] = values[latest_idx]
                    
                    await self.connection_manager.broadcast_sensor_update(update_data)
                    
        except Exception as e:
            logger.error(f"Failed to broadcast sensor update: {e}")
    
    def set_connection_manager(self, manager):
        """Set the WebSocket connection manager for broadcasting."""
        self.connection_manager = manager
    
    async def get_status(self) -> Dict[str, Any]:
        """Get worker status information."""
        return {
            "worker": "influx",
            "status": "running",
            "last_collection": self.last_collection_time.isoformat(),
            "influxdb_connected": bool(self.client),
            "collection_interval": settings.collection_interval,
            "data_dir": settings.data_dir
        }
    
    async def cleanup(self):
        """Cleanup resources."""
        if self.client:
            self.client.close()
            logger.info("InfluxDB connection closed")