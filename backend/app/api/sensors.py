# REST API endpoints for sensor management including sensor discovery, nickname management, and data queries for the new sensor-grouped data format.

from fastapi import APIRouter, HTTPException, Depends, status, Query
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import json
from pathlib import Path
import asyncio
from functools import lru_cache

from app.core.config import settings
from app.models.graph import SensorInfo, SensorData, SensorDataResponse

router = APIRouter()

@lru_cache(maxsize=1)
def get_sensors_config_file() -> Path:
    """Get the path to the sensors configuration file."""
    data_dir = Path(settings.data_dir)
    return data_dir / "sensor_config.json"

@lru_cache(maxsize=1)
def get_sensor_nicknames_file() -> Path:
    """Get the path to the sensor nicknames file."""
    data_dir = Path(settings.data_dir)
    return data_dir / "sensor_nicknames.json"

async def read_json_file(file_path: Path) -> Optional[Dict[str, Any]]:
    """Asynchronously read and parse a JSON file."""
    if not file_path.exists():
        return None
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except (IOError, json.JSONDecodeError) as e:
        print(f"Error reading {file_path}: {e}")
        return None

async def write_json_file(file_path: Path, data: Dict[str, Any]):
    """Asynchronously write data to a JSON file."""
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2, default=str)
    except IOError as e:
        print(f"Error writing to {file_path}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to write configuration: {e}")

def get_data_file_path(date: datetime) -> Path:
    """Get file path for sensor data snapshots."""
    data_dir = Path(settings.data_dir)
    data_dir.mkdir(exist_ok=True)
    week_start = date - timedelta(days=date.weekday())
    filename = f"sensors_{week_start.strftime('%Y_%m_%d')}.json"
    return data_dir / filename

async def discover_sensors_from_data() -> List[SensorInfo]:
    """Discover sensors from existing data files."""
    data_dir = Path(settings.data_dir)
    sensors = {}
    
    # Look for data files
    for data_file in data_dir.glob("sensors_*.json"):
        data = await read_json_file(data_file)
        if not data:
            continue
            
        # Check if it's new format (has sensors key)
        if "sensors" in data:
            for sensor_id, sensor_data in data["sensors"].items():
                if sensor_id not in sensors:
                    available_metrics = list(sensor_data.get("metrics", {}).keys())
                    sensors[sensor_id] = SensorInfo(
                        id=sensor_id,
                        mac_address=sensor_data.get("mac_address", sensor_id),
                        nickname=sensor_data.get("nickname"),
                        location=sensor_data.get("location"),
                        model=sensor_data.get("model"),
                        installed_at=sensor_data.get("installed_at"),
                        available_metrics=available_metrics
                    )
        else:
            # Old format - create default sensors
            available_metrics = [key for key in data.keys() if key != "timestamps" and isinstance(data.get(key), list)]
            if available_metrics:
                # For old format, create some default sensors
                default_sensors = [
                    ("sensor_001", "AA:BB:CC:DD:EE:01", "Living Room"),
                    ("sensor_002", "AA:BB:CC:DD:EE:02", "Bedroom"), 
                    ("sensor_003", "AA:BB:CC:DD:EE:03", "Kitchen")
                ]
                
                for sensor_id, mac_addr, location in default_sensors:
                    if sensor_id not in sensors:
                        sensors[sensor_id] = SensorInfo(
                            id=sensor_id,
                            mac_address=mac_addr,
                            nickname=location,
                            location=location,
                            available_metrics=available_metrics
                        )
    
    return list(sensors.values())

async def load_sensor_nicknames() -> Dict[str, str]:
    """Load sensor nicknames from file."""
    nicknames_file = get_sensor_nicknames_file()
    data = await read_json_file(nicknames_file)
    if data:
        return data.get("nicknames", {})
    return {}

async def save_sensor_nicknames(nicknames: Dict[str, str]):
    """Save sensor nicknames to file."""
    nicknames_file = get_sensor_nicknames_file()
    data = {
        "nicknames": nicknames,
        "updated_at": datetime.now().isoformat()
    }
    await write_json_file(nicknames_file, data)

@router.get("/", response_model=List[SensorInfo])
async def get_all_sensors():
    """Get all available sensors with their information."""
    
    # First try to load from config file
    config_file = get_sensors_config_file()
    config_data = await read_json_file(config_file)
    
    if config_data and "sensors" in config_data:
        sensors = []
        # Also discover available metrics from data files
        discovered_sensors = await discover_sensors_from_data()
        discovered_metrics = {s.id: s.available_metrics for s in discovered_sensors}
        
        for sensor_data in config_data["sensors"]:
            sensor = SensorInfo(**sensor_data)
            # Add discovered metrics if available
            if sensor.id in discovered_metrics:
                sensor.available_metrics = discovered_metrics[sensor.id]
            sensors.append(sensor)
    else:
        # Discover sensors from data files
        sensors = await discover_sensors_from_data()
    
    # Load and apply nicknames
    nicknames = await load_sensor_nicknames()
    for sensor in sensors:
        if sensor.id in nicknames:
            sensor.nickname = nicknames[sensor.id]
    
    return sensors

@router.get("/{sensor_id}", response_model=SensorInfo)
async def get_sensor(sensor_id: str):
    """Get specific sensor information."""
    sensors = await get_all_sensors()
    sensor = next((s for s in sensors if s.id == sensor_id), None)
    
    if not sensor:
        raise HTTPException(status_code=404, detail="Sensor not found")
    
    return sensor

@router.get("/{sensor_id}/data")
async def get_sensor_data(
    sensor_id: str,
    start_time: Optional[datetime] = Query(None, description="Start time for data query"),
    end_time: Optional[datetime] = Query(None, description="End time for data query"),
    metrics: Optional[List[str]] = Query(None, description="Specific metrics to retrieve"),
    limit: int = Query(1000, description="Maximum number of data points")
):
    """Get sensor data with time range and metric filtering."""
    
    # Get sensor info
    sensor = await get_sensor(sensor_id)
    
    # Set default time range
    end_dt = end_time or datetime.utcnow()
    start_dt = start_time or end_dt - timedelta(hours=24)
    
    # Collect data from relevant files
    current_date = start_dt.date()
    all_data_points = []
    
    while current_date <= end_dt.date():
        data_file = get_data_file_path(datetime.combine(current_date, datetime.min.time()))
        data = await read_json_file(data_file)
        
        if data and "sensors" in data and sensor_id in data["sensors"]:
            # New format
            sensor_data = data["sensors"][sensor_id]
            sensor_metrics = sensor_data.get("metrics", {})
            
            for metric_name, metric_data in sensor_metrics.items():
                if metrics and metric_name not in metrics:
                    continue
                    
                timestamps = metric_data.get("timestamps", [])
                values = metric_data.get("values", [])
                
                for i, (ts_str, value) in enumerate(zip(timestamps, values)):
                    try:
                        ts = datetime.fromisoformat(ts_str)
                        if start_dt <= ts <= end_dt:
                            # Find or create data point for this timestamp
                            data_point = next((dp for dp in all_data_points if dp["timestamp"] == ts_str), None)
                            if not data_point:
                                data_point = {"timestamp": ts_str}
                                all_data_points.append(data_point)
                            data_point[metric_name] = value
                    except (ValueError, TypeError):
                        continue
        
        elif data and "timestamps" in data:
            # Old format - assume data belongs to this sensor (for backward compatibility)
            timestamps = data.get("timestamps", [])
            for i, ts_str in enumerate(timestamps):
                try:
                    ts = datetime.fromisoformat(ts_str)
                    if start_dt <= ts <= end_dt:
                        data_point = {"timestamp": ts_str}
                        
                        # Add metric data if it exists and is requested
                        for metric_name in sensor.available_metrics:
                            if metrics and metric_name not in metrics:
                                continue
                            if metric_name in data and i < len(data[metric_name]):
                                data_point[metric_name] = data[metric_name][i]
                        
                        all_data_points.append(data_point)
                except (ValueError, TypeError):
                    continue
        
        current_date += timedelta(days=1)
    
    # Sort by timestamp and limit results
    all_data_points.sort(key=lambda x: x["timestamp"])
    limited_data = all_data_points[-limit:] if limit > 0 else all_data_points
    
    # Format response
    if limited_data:
        sensor_data = SensorData(
            sensor_id=sensor_id,
            timestamps=[dp["timestamp"] for dp in limited_data],
            values={
                metric: [dp.get(metric) for dp in limited_data]
                for metric in (metrics or sensor.available_metrics)
                if any(metric in dp for dp in limited_data)
            }
        )
        time_range = {
            "start": limited_data[0]["timestamp"],
            "end": limited_data[-1]["timestamp"]
        }
    else:
        sensor_data = SensorData(sensor_id=sensor_id, timestamps=[], values={})
        time_range = {"start": start_dt.isoformat(), "end": end_dt.isoformat()}
    
    return SensorDataResponse(
        sensor=sensor,
        data=sensor_data,
        total_points=len(limited_data),
        time_range=time_range
    )

@router.put("/{sensor_id}/nickname")
async def update_sensor_nickname(sensor_id: str, nickname_data: Dict[str, str]):
    """Update sensor nickname."""
    nickname = nickname_data.get("nickname", "").strip()
    
    # Verify sensor exists
    await get_sensor(sensor_id)
    
    # Load current nicknames
    nicknames = await load_sensor_nicknames()
    
    if nickname:
        nicknames[sensor_id] = nickname
    elif sensor_id in nicknames:
        del nicknames[sensor_id]
    
    # Save updated nicknames
    await save_sensor_nicknames(nicknames)
    
    return {"sensor_id": sensor_id, "nickname": nickname}

@router.get("/{sensor_id}/metrics")
async def get_sensor_metrics(sensor_id: str):
    """Get available metrics for a specific sensor."""
    sensor = await get_sensor(sensor_id)
    
    metric_details = []
    for metric in sensor.available_metrics:
        # Default metric information
        metric_info = {
            "name": metric,
            "display_name": metric.replace("_", " ").title(),
            "unit": "value"
        }
        
        # Add specific units for known metrics
        if metric == "temperature":
            metric_info.update({"unit": "°C", "min_value": -40, "max_value": 85})
        elif metric == "humidity":
            metric_info.update({"unit": "%", "min_value": 0, "max_value": 100})
        elif metric == "co2":
            metric_info.update({"unit": "ppm", "min_value": 400, "max_value": 5000})
        elif metric == "aqi":
            metric_info.update({"unit": "AQI", "min_value": 0, "max_value": 500})
        elif metric == "pressure":
            metric_info.update({"unit": "hPa", "min_value": 950, "max_value": 1050})
        elif metric == "light_level":
            metric_info.update({"unit": "lux", "min_value": 0, "max_value": 10000})
        
        metric_details.append(metric_info)
    
    return {"sensor_id": sensor_id, "metrics": metric_details}

@router.post("/batch/nicknames")
async def update_multiple_nicknames(nickname_updates: Dict[str, str]):
    """Update nicknames for multiple sensors."""
    # Load current nicknames
    nicknames = await load_sensor_nicknames()
    
    # Update with new values
    for sensor_id, nickname in nickname_updates.items():
        if nickname.strip():
            nicknames[sensor_id] = nickname.strip()
        elif sensor_id in nicknames:
            del nicknames[sensor_id]
    
    # Save updated nicknames
    await save_sensor_nicknames(nicknames)
    
    return {"updated_sensors": list(nickname_updates.keys()), "total_nicknames": len(nicknames)}
