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
    graphs_dir = get_graphs_dir()
    if not any(graphs_dir.glob("*.json")):
        default_graphs = [
            GraphModel(id="temp-humidity", title="Temperature & Humidity", chart_type="line", metrics=["temperature", "humidity"], time_range="24h", settings=GraphSettings(color_scheme=["#3b82f6", "#ef4444"], show_legend=True, show_grid=True), layout=GraphLayout(x=0, y=0, width=6, height=4)),
            GraphModel(id="co2-aqi", title="CO₂ & Air Quality", chart_type="area", metrics=["co2", "aqi"], time_range="12h", settings=GraphSettings(color_scheme=["#22c55e", "#f59e0b"], show_legend=True, show_grid=True), layout=GraphLayout(x=6, y=0, width=6, height=4)),
            GraphModel(id="pressure", title="Atmospheric Pressure", chart_type="line", metrics=["pressure"], time_range="24h", settings=GraphSettings(color_scheme=["#8b5cf6"], show_legend=True, show_grid=True), layout=GraphLayout(x=0, y=4, width=6, height=4)),
            GraphModel(id="light-level", title="Light Level", chart_type="bar", metrics=["light_level"], time_range="6h", settings=GraphSettings(color_scheme=["#eab308"], show_legend=True, show_grid=True), layout=GraphLayout(x=6, y=4, width=6, height=4))
        ]
        await asyncio.gather(*(save_graph_to_file(graph) for graph in default_graphs))

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
    await create_default_graphs_if_needed()
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
    limit: int = 1000
):
    """Get historical data for specific graph with time range filtering."""
    graph = await load_graph_from_file(graph_id)
    if not graph:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Graph not found")
    
    end_dt = end_time or datetime.utcnow()
    start_dt = start_time or end_dt - timedelta(hours=24)
    
    # Collect data from relevant files
    tasks = []
    current_date = start_dt.date()
    while current_date <= end_dt.date():
        data_file = get_data_file_path(datetime.combine(current_date, datetime.min.time()))
        tasks.append(read_json_file(data_file))
        current_date += timedelta(days=1)
        
    file_contents = await asyncio.gather(*tasks)
    
    data_points = []
    for content in filter(None, file_contents):
        timestamps = content.get("timestamps", [])
        for i, ts_str in enumerate(timestamps):
            ts = datetime.fromisoformat(ts_str)
            if start_dt <= ts <= end_dt:
                point = {"timestamp": ts_str}
                for metric in graph.metrics:
                    if metric in content and i < len(content[metric]):
                        point[metric] = content[metric][i]
                data_points.append(point)

    data_points.sort(key=lambda x: x["timestamp"], reverse=True)
    
    return {"graph_id": graph_id, "data": data_points[:limit], "count": len(data_points)}