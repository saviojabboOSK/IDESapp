# REST API endpoints for graph management including CRUD operations for dashboard charts, real-time data retrieval, and customizable visualization settings for sensor metrics.

from fastapi import APIRouter, HTTPException, Depends, status
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import json
from pathlib import Path
import uuid
import asyncio
from functools import lru_cache

from app.core.config import settings
from app.models.graph import GraphModel, GraphSettings, GraphData, GraphLayout

router = APIRouter()

@lru_cache(maxsize=1)
def get_graphs_dir() -> Path:
    """Get the directory for graph configuration files, cached for performance."""
    graphs_dir = Path(settings.data_dir) / "graphs"
    graphs_dir.mkdir(exist_ok=True)
    return graphs_dir

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
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2, default=str)
    except IOError as e:
        print(f"Error writing to {file_path}: {e}")

async def save_graph_to_file(graph: GraphModel) -> None:
    """Save graph configuration to JSON file."""
    graphs_dir = get_graphs_dir()
    graph_file = graphs_dir / f"{graph.id}.json"
    graph.updated_at = datetime.utcnow()
    await write_json_file(graph_file, graph.dict())

async def load_graph_from_file(graph_id: str) -> Optional[GraphModel]:
    """Load graph configuration from JSON file."""
    graphs_dir = get_graphs_dir()
    graph_file = graphs_dir / f"{graph_id}.json"
    data = await read_json_file(graph_file)
    if data:
        return GraphModel(**data)
    return None

async def delete_graph_file(graph_id: str) -> bool:
    """Delete graph configuration file."""
    graphs_dir = get_graphs_dir()
    graph_file = graphs_dir / f"{graph_id}.json"
    if graph_file.exists():
        graph_file.unlink()
        return True
    return False

async def load_all_graphs() -> Dict[str, GraphModel]:
    """Load all graph configurations from files concurrently."""
    graphs_dir = get_graphs_dir()
    tasks = [load_graph_from_file(f.stem) for f in graphs_dir.glob("*.json")]
    results = await asyncio.gather(*tasks)
    return {graph.id: graph for graph in results if graph}

async def create_default_graphs_if_needed() -> None:
    """Create default graph configurations if none exist."""
    # Disabled automatic default graph creation
    # Users should create their own graphs using the graph builder
    pass
    # graphs_dir = get_graphs_dir()
    # if not any(graphs_dir.glob("*.json")):
    #     default_graphs = [
    #         GraphModel(id="temp-humidity", title="Living Room - Temperature & Humidity", chart_type="line", sensor_id="sensor_001", metrics=["temperature", "humidity"], time_range="24h", settings=GraphSettings(color_scheme=["#3b82f6", "#ef4444"], show_legend=True, show_grid=True), layout=GraphLayout(x=0, y=0, width=6, height=4)),
    #         GraphModel(id="co2-aqi", title="Bedroom - CO₂ & Air Quality", chart_type="area", sensor_id="sensor_002", metrics=["co2", "aqi"], time_range="12h", settings=GraphSettings(color_scheme=["#22c55e", "#f59e0b"], show_legend=True, show_grid=True), layout=GraphLayout(x=6, y=0, width=6, height=4)),
    #         GraphModel(id="pressure", title="Kitchen - Atmospheric Pressure", chart_type="line", sensor_id="sensor_003", metrics=["pressure"], time_range="24h", settings=GraphSettings(color_scheme=["#8b5cf6"], show_legend=True, show_grid=True), layout=GraphLayout(x=0, y=4, width=6, height=4)),
    #         GraphModel(id="light-level", title="Living Room - Light Level", chart_type="bar", sensor_id="sensor_001", metrics=["light_level"], time_range="6h", settings=GraphSettings(color_scheme=["#eab308"], show_legend=True, show_grid=True), layout=GraphLayout(x=6, y=4, width=6, height=4))
    #     ]
    #     await asyncio.gather(*(save_graph_to_file(graph) for graph in default_graphs))

def get_data_file_path(date: datetime) -> Path:
    """Get file path for sensor data snapshots."""
    data_dir = Path(settings.data_dir)
    data_dir.mkdir(exist_ok=True)
    week_start = date - timedelta(days=date.weekday())
    filename = f"sensors_{week_start.strftime('%Y_%m_%d')}.json"
    return data_dir / filename

@router.get("/", response_model=List[GraphModel])
async def get_all_graphs():
    """Retrieve all dashboard graphs with their current configurations."""
    # Removed automatic default graph creation - users should create their own graphs
    graphs = await load_all_graphs()
    return list(graphs.values())

@router.get("/{graph_id}", response_model=GraphModel)
async def get_graph(graph_id: str):
    """Get specific graph configuration and recent data."""
    graph = await load_graph_from_file(graph_id)
    if not graph:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Graph not found")
    
    data_file = get_data_file_path(datetime.utcnow())
    recent_data = await read_json_file(data_file)
    
    if recent_data:
        timestamps = recent_data.get("timestamps", [])[-100:]
        graph.data = GraphData(
            timestamps=timestamps,
            values={
                metric: recent_data.get(metric, [])[-100:]
                for metric in graph.metrics
            }
        )
    else:
        graph.data = GraphData(timestamps=[], values={})
    
    return graph

@router.post("/", response_model=GraphModel, status_code=status.HTTP_201_CREATED)
async def create_graph(graph_data: Dict[str, Any]):
    """Create new dashboard graph with specified configuration."""
    if 'id' not in graph_data or not graph_data['id']:
        graph_data['id'] = str(uuid.uuid4())
    
    graph = GraphModel(**graph_data)
    await save_graph_to_file(graph)
    return graph

@router.put("/{graph_id}", response_model=GraphModel)
async def update_graph(graph_id: str, updates: Dict[str, Any]):
    """Update existing graph configuration and settings."""
    graph = await load_graph_from_file(graph_id)
    if not graph:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Graph not found")
    
    update_data = graph.dict()
    
    def deep_merge(base, update):
        for k, v in update.items():
            if k in base and isinstance(base[k], dict) and isinstance(v, dict):
                deep_merge(base[k], v)
            else:
                base[k] = v

    deep_merge(update_data, updates)
    
    updated_graph = GraphModel(**update_data)
    updated_graph.updated_at = datetime.utcnow()
    
    await save_graph_to_file(updated_graph)
    return updated_graph

@router.delete("/{graph_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_graph(graph_id: str):
    """Remove graph from dashboard."""
    if not await delete_graph_file(graph_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Graph not found")

@router.post("/batch/layout", status_code=status.HTTP_200_OK)
async def update_batch_layout(layout_updates: List[Dict[str, Any]]):
    """Update layout for multiple graphs simultaneously."""
    
    async def update_single_layout(update):
        graph_id = update.get("id")
        layout_data = update.get("layout")
        if not graph_id or not layout_data:
            return None
        
        graph = await load_graph_from_file(graph_id)
        if graph:
            graph.layout = GraphLayout(**layout_data)
            await save_graph_to_file(graph)
            return graph_id
        return None

    results = await asyncio.gather(*(update_single_layout(up) for up in layout_updates))
    updated_ids = [gid for gid in results if gid]
    
    return {"updated_graphs": updated_ids, "count": len(updated_ids)}

@router.get("/{graph_id}/data")
async def get_graph_data(
    graph_id: str,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    limit: int = 5000  # Increased default limit for high-frequency sensor data
):
    """Get historical data for specific graph with time range filtering."""
    graph = await load_graph_from_file(graph_id)
    if not graph:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Graph not found")
    
    # Handle custom time ranges
    if graph.custom_start_time and graph.custom_end_time:
        start_dt = graph.custom_start_time
        end_dt = graph.custom_end_time
    else:
        # For historical data, use the actual data time range instead of current time
        # First, determine the time range of available data
        data_dir = Path(__file__).parent.parent.parent / "data"
        sensor_file = data_dir / "sensors_2025_07_21.json"
        
        data_end_time = datetime.utcnow()
        data_start_time = data_end_time - timedelta(hours=24)  # Default fallback
        
        if sensor_file.exists():
            try:
                # Read a small sample to determine actual data time range
                content = await read_json_file(sensor_file)
                if content and "sensors" in content:
                    # Find any sensor with data to determine time range
                    for sensor_data in content["sensors"].values():
                        metrics = sensor_data.get("metrics", {})
                        for metric_data in metrics.values():
                            timestamps = metric_data.get("timestamps", [])
                            if timestamps:
                                # Parse first and last timestamps
                                first_ts = datetime.fromisoformat(timestamps[0].replace('Z', '').replace('+00:00', ''))
                                last_ts = datetime.fromisoformat(timestamps[-1].replace('Z', '').replace('+00:00', ''))
                                data_start_time = first_ts
                                data_end_time = last_ts
                                break
                        if data_start_time != data_end_time - timedelta(hours=24):
                            break
            except:
                pass
        
        # Apply the requested time range relative to the data's actual time range
        if graph.time_range == "1h":
            start_dt = max(data_start_time, data_end_time - timedelta(hours=1))
            end_dt = data_end_time
        elif graph.time_range == "6h":
            start_dt = max(data_start_time, data_end_time - timedelta(hours=6))
            end_dt = data_end_time
        elif graph.time_range == "12h":
            start_dt = max(data_start_time, data_end_time - timedelta(hours=12))
            end_dt = data_end_time
        elif graph.time_range == "24h":
            start_dt = max(data_start_time, data_end_time - timedelta(hours=24))
            end_dt = data_end_time
        elif graph.time_range == "7d":
            start_dt = max(data_start_time, data_end_time - timedelta(days=7))
            end_dt = data_end_time
        elif graph.time_range == "30d":
            start_dt = max(data_start_time, data_end_time - timedelta(days=30))
            end_dt = data_end_time
        else:
            # Default to all available data
            start_dt = data_start_time
            end_dt = data_end_time
    
    data_points = []
    
    # Try to load real sensor data from available files
    # Use absolute path to the data directory
    data_dir = Path(__file__).parent.parent.parent / "data"
    sensor_files = [
        data_dir / "sensors_2025_07_21.json",
        data_dir / "sensors_from_csv.json"
    ]
    
    for sensor_file in sensor_files:
        if sensor_file.exists():
            content = await read_json_file(sensor_file)
            if not content or "sensors" not in content:
                continue
                
            # Handle multi-sensor comparison (new enhanced format)
            if hasattr(graph, 'sensors') and graph.sensors:
                # Multi-sensor graph
                for sensor_selection in graph.sensors:
                    sensor_id = sensor_selection.get('sensor_id')
                    selected_metrics = sensor_selection.get('metrics', [])
                    
                    if sensor_id in content["sensors"]:
                        sensor_data = content["sensors"][sensor_id]
                        sensor_metrics = sensor_data.get("metrics", {})
                        
                        # Collect timestamps and values for selected metrics
                        for metric in selected_metrics:
                            if metric in sensor_metrics:
                                timestamps = sensor_metrics[metric].get("timestamps", [])
                                values = sensor_metrics[metric].get("values", [])
                                
                                for ts_str, value in zip(timestamps, values):
                                    try:
                                        # Handle different timestamp formats
                                        ts_clean = ts_str.replace('Z', '').replace('+00:00', '')
                                        if '.' in ts_clean:
                                            ts = datetime.fromisoformat(ts_clean)
                                        else:
                                            ts = datetime.fromisoformat(ts_clean)
                                        
                                        # Apply time range filtering
                                        if start_dt <= ts <= end_dt:
                                            # Find existing point or create new one
                                            existing_point = next((p for p in data_points if p["timestamp"] == ts_str), None)
                                            if existing_point:
                                                existing_point[f"{sensor_id}_{metric}"] = value
                                            else:
                                                point = {"timestamp": ts_str, f"{sensor_id}_{metric}": value}
                                                data_points.append(point)
                                    except (ValueError, TypeError):
                                        continue
                        
            # Handle single sensor graph (backward compatibility)
            elif graph.sensor_id and graph.sensor_id in content["sensors"]:
                sensor_data = content["sensors"][graph.sensor_id]
                sensor_metrics = sensor_data.get("metrics", {})
                
                # Collect all timestamps from requested metrics
                all_timestamps = set()
                metric_data = {}
                
                for metric in graph.metrics:
                    if metric in sensor_metrics:
                        timestamps = sensor_metrics[metric].get("timestamps", [])
                        values = sensor_metrics[metric].get("values", [])
                        metric_data[metric] = dict(zip(timestamps, values))
                        all_timestamps.update(timestamps)
                
                # Create data points for each timestamp
                for ts_str in all_timestamps:
                    try:
                        # Handle different timestamp formats - parse for filtering
                        ts_clean = ts_str.replace('Z', '').replace('+00:00', '')
                        if '.' in ts_clean:
                            ts = datetime.fromisoformat(ts_clean)
                        else:
                            ts = datetime.fromisoformat(ts_clean)
                        
                        # Apply time range filtering
                        if start_dt <= ts <= end_dt:
                            point = {"timestamp": ts_str}
                            for metric in graph.metrics:
                                point[metric] = metric_data.get(metric, {}).get(ts_str)
                            data_points.append(point)
                    except (ValueError, TypeError):
                        continue
            
            # If we found data in this file, break and use it
            if data_points:
                break

    # Remove duplicates and sort by timestamp
    unique_points = {}
    for point in data_points:
        ts = point["timestamp"]
        if ts not in unique_points:
            unique_points[ts] = point
        else:
            # Merge data points with same timestamp
            unique_points[ts].update(point)
    
    data_points = list(unique_points.values())
    
    # Sort by timestamp (parse for sorting but keep original format)
    def parse_timestamp_for_sort(ts_str):
        try:
            ts_clean = ts_str.replace('Z', '').replace('+00:00', '')
            return datetime.fromisoformat(ts_clean)
        except:
            return datetime.min
    
    data_points.sort(key=lambda x: parse_timestamp_for_sort(x["timestamp"]))
    
    # Apply limit with intelligent sampling
    if len(data_points) > limit:
        # Instead of taking evenly spaced points, take more recent points with some historical context
        # Keep the most recent 70% and sample the rest evenly
        recent_count = int(limit * 0.7)
        historical_count = limit - recent_count
        
        # Take most recent points
        recent_points = data_points[-recent_count:]
        
        # Sample historical points evenly if we have enough
        if len(data_points) > recent_count:
            historical_data = data_points[:-recent_count]
            if len(historical_data) > historical_count:
                step = len(historical_data) // historical_count
                historical_points = historical_data[::max(1, step)][:historical_count]
            else:
                historical_points = historical_data
            
            data_points = historical_points + recent_points
        else:
            data_points = recent_points
    
    return {"graph_id": graph_id, "data": data_points, "count": len(data_points)}