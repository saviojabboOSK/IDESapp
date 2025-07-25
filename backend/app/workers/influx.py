# InfluxDB worker for automated sensor data collection, JSON snapshot creation, and real-time WebSocket broadcasting to maintain synchronized dashboard state with 30-second intervals.

import asyncio
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional

try:
    from influxdb_client import InfluxDBClient, Point
    from influxdb_client.client.write_api import SYNCHRONOUS
    from influxdb_client.client.query_api import QueryApi
except ImportError:
    # Fallback for demo without InfluxDB
    InfluxDBClient = None
    QueryApi = None
    Point = None
    SYNCHRONOUS = None


from app.core.config import settings

logger = logging.getLogger(__name__)

class InfluxWorker:
    """Worker for collecting sensor data from InfluxDB and creating JSON snapshots."""
    
    def __init__(self):
        self.client: Optional["InfluxDBClient"] = None
        self.query_api: Optional["QueryApi"] = None
        self.last_collection_time = datetime.utcnow()
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
                org=settings.influx_org,
                timeout=10_000
            )
            self.query_api = self.client.query_api()
            
            # Test connection
            if self.client.health().status != "pass":
                raise ConnectionError("InfluxDB health check failed")
            
            logger.info("InfluxDB connection established and health check passed.")
                
        except Exception as e:
            logger.error(f"Failed to initialize InfluxDB connection: {e}", exc_info=True)
            self.client = None
    
    async def collect_sensor_data(self):
        """Collect latest sensor data and update JSON snapshots."""
        try:
            logger.info("Starting sensor data collection...")
            
            # Skip data collection since we're using static CSV data
            # The real sensor data is already converted and available in sensors_2025_07_21.json
            logger.info("Using static CSV data - skipping InfluxDB collection")
            return
            
            # if self.client and self.query_api:
            #     sensor_data = await self._query_influx_data()
            # else:
            #     sensor_data = self._generate_mock_data()
            # 
            # if not sensor_data.get("timestamps"):
            #     logger.info("No new sensor data to process.")
            #     return
            # 
            # await self._save_to_json_snapshot(sensor_data)
            # await self._broadcast_update(sensor_data)
            # 
            # self.last_collection_time = datetime.utcnow()
            # logger.info(f"Sensor data collection completed: {len(sensor_data['timestamps'])} points")
            
        except Exception as e:
            logger.error(f"Sensor data collection failed: {e}", exc_info=True)
    
    async def _query_influx_data(self) -> Dict[str, Any]:
        """Query recent sensor data from InfluxDB."""
        query = f'''
        from(bucket: "{settings.influx_bucket}")
            |> range(start: -1h)
            |> filter(fn: (r) => r["_measurement"] == "sensors")
            |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
            |> sort(columns: ["_time"])
        '''
        try:
            tables = await asyncio.to_thread(self.query_api.query, query)
            
            data = {
                "timestamps": [], "temperature": [], "humidity": [], "co2": [],
                "aqi": [], "pressure": [], "light_level": []
            }
            
            for record in (rec for tbl in tables for rec in tbl.records):
                data["timestamps"].append(record.get_time().isoformat())
                for key in data.keys():
                    if key != "timestamps":
                        data[key].append(record.values.get(key))
            
            return data
            
        except Exception as e:
            logger.error(f"InfluxDB query failed: {e}", exc_info=True)
            return {}

    def _generate_mock_data(self) -> Dict[str, Any]:
        """Generate mock sensor data for demonstration."""
        import random
        
        now = datetime.utcnow()
        timestamps = [(now - timedelta(minutes=59-i)).isoformat() for i in range(60)]
        
        return {
            "timestamps": timestamps,
            "temperature": [round(22.0 + random.uniform(-2, 2), 1) for _ in range(60)],
            "humidity": [round(45.0 + random.uniform(-5, 5), 1) for _ in range(60)],
            "co2": [round(420 + random.uniform(-50, 100), 0) for _ in range(60)],
            "aqi": [max(0, 35 + random.randint(-10, 15)) for _ in range(60)],
            "pressure": [round(1013.25 + random.uniform(-5, 5), 2) for _ in range(60)],
            "light_level": [round(300 + random.uniform(-50, 200), 1) for _ in range(60)],
        }
    
    async def _save_to_json_snapshot(self, data: Dict[str, Any]):
        """Save sensor data to weekly JSON snapshot file efficiently."""
        data_dir = Path(settings.data_dir)
        data_dir.mkdir(exist_ok=True)
        
        now = datetime.utcnow()
        week_start = now - timedelta(days=now.weekday())
        filename = f"sensors_{week_start.strftime('%Y_%m_%d')}.json"
        file_path = data_dir / filename

        try:
            if file_path.exists():
                with open(file_path, 'r') as f:
                    existing_data = json.load(f)
                existing_timestamps = set(existing_data.get("timestamps", []))
            else:
                existing_data = {key: [] for key in data.keys()}
                existing_timestamps = set()

            new_indices = [i for i, ts in enumerate(data["timestamps"]) if ts not in existing_timestamps]

            if not new_indices:
                return

            for key, values in data.items():
                new_values = [values[i] for i in new_indices]
                if key not in existing_data:
                    existing_data[key] = []
                existing_data[key].extend(new_values)

            with open(file_path, 'w') as f:
                json.dump(existing_data, f, indent=2)
            
            logger.debug(f"Saved {len(new_indices)} new data points to {filename}")

        except (IOError, json.JSONDecodeError) as e:
            logger.error(f"Failed to save JSON snapshot to {file_path}: {e}", exc_info=True)

    async def _broadcast_update(self, data: Dict[str, Any]):
        """Broadcast the latest sensor data point via WebSocket."""
        if not self.connection_manager or not data.get("timestamps"):
            return
            
        try:
            latest_idx = -1
            update_data = {
                "timestamp": data["timestamps"][latest_idx],
                "metrics": {
                    metric: values[latest_idx]
                    for metric, values in data.items()
                    if metric != "timestamps" and values
                }
            }
            await self.connection_manager.broadcast_sensor_update(update_data)
        except Exception as e:
            logger.error(f"Failed to broadcast sensor update: {e}", exc_info=True)
    
    def set_connection_manager(self, manager):
        """Set the WebSocket connection manager for broadcasting."""
        self.connection_manager = manager
    
    async def get_status(self) -> Dict[str, Any]:
        """Get worker status information."""
        return {
            "worker": "influx",
            "status": "running",
            "last_collection": self.last_collection_time.isoformat(),
            "influxdb_connected": self.client is not None,
            "collection_interval": settings.collection_interval,
            "data_dir": settings.data_dir
        }
    
    async def cleanup(self):
        """Cleanup resources."""
        if self.client:
            self.client.close()
            logger.info("InfluxDB connection closed")