# REST API endpoints for graph management including CRUD operations for dashboard charts, real-time data retrieval, and customizable visualization settings for sensor metrics.

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import uuid

from app.core.config import settings
from app.models.graph import GraphModel, GraphSettings, GraphData, GraphLayout

router = APIRouter()

def get_graphs_dir() -> Path:
    """Get the directory for graph configuration files."""
    graphs_dir = Path(settings.data_dir) / "graphs"
    graphs_dir.mkdir(exist_ok=True)
    return graphs_dir

def save_graph_to_file(graph: GraphModel) -> None:
    """Save graph configuration to JSON file."""
    graphs_dir = get_graphs_dir()
    graph_file = graphs_dir / f"{graph.id}.json"
    
    # Update timestamp
    graph.updated_at = datetime.now()
    
    with open(graph_file, 'w') as f:
        json.dump(graph.dict(), f, indent=2, default=str)

def load_graph_from_file(graph_id: str) -> Optional[GraphModel]:
    """Load graph configuration from JSON file."""
    graphs_dir = get_graphs_dir()
    graph_file = graphs_dir / f"{graph_id}.json"
    
    if not graph_file.exists():
        return None
    
    try:
        with open(graph_file, 'r') as f:
            data = json.load(f)
        return GraphModel(**data)
    except Exception as e:
        print(f"Error loading graph {graph_id}: {e}")
        return None

def delete_graph_file(graph_id: str) -> bool:
    """Delete graph configuration file."""
    graphs_dir = get_graphs_dir()
    graph_file = graphs_dir / f"{graph_id}.json"
    
    if graph_file.exists():
        graph_file.unlink()
        return True
    return False

def load_all_graphs() -> Dict[str, GraphModel]:
    """Load all graph configurations from files."""
    graphs_dir = get_graphs_dir()
    graphs = {}
    
    for graph_file in graphs_dir.glob("*.json"):
        graph_id = graph_file.stem
        graph = load_graph_from_file(graph_id)
        if graph:
            graphs[graph_id] = graph
    
    return graphs

def create_default_graphs() -> None:
    """Create default graph configurations if none exist."""
    graphs_dir = get_graphs_dir()
    
    if list(graphs_dir.glob("*.json")):
        return  # Already have graphs
    
    default_graphs = [
        GraphModel(
            id="temp-humidity",
            title="Temperature & Humidity",
            chart_type="line",
            metrics=["temperature", "humidity"],
            time_range="24h",
            settings=GraphSettings(
                color_scheme=["#3b82f6", "#ef4444"],
                show_legend=True,
                show_grid=True
            ),
            layout=GraphLayout(x=0, y=0, width=6, height=4)
        ),
        GraphModel(
            id="co2-aqi",
            title="CO₂ & Air Quality",
            chart_type="area",
            metrics=["co2", "aqi"],
            time_range="12h",
            settings=GraphSettings(
                color_scheme=["#22c55e", "#f59e0b"],
                show_legend=True,
                show_grid=True
            ),
            layout=GraphLayout(x=6, y=0, width=6, height=4)
        ),
        GraphModel(
            id="pressure",
            title="Atmospheric Pressure",
            chart_type="line",
            metrics=["pressure"],
            time_range="24h",
            settings=GraphSettings(
                color_scheme=["#8b5cf6"],
                show_legend=True,
                show_grid=True
            ),
            layout=GraphLayout(x=0, y=4, width=6, height=4)
        ),
        GraphModel(
            id="light-level",
            title="Light Level",
            chart_type="bar",
            metrics=["light_level"],
            time_range="6h",
            settings=GraphSettings(
                color_scheme=["#eab308"],
                show_legend=True,
                show_grid=True
            ),
            layout=GraphLayout(x=6, y=4, width=6, height=4)
        )
    ]
    
    for graph in default_graphs:
        save_graph_to_file(graph)

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
    create_default_graphs()  # Ensure default graphs exist
    graphs = load_all_graphs()
    return list(graphs.values())

@router.get("/{graph_id}", response_model=GraphModel)
async def get_graph(graph_id: str):
    """Get specific graph configuration and recent data."""
    graph = load_graph_from_file(graph_id)
    if not graph:
        raise HTTPException(status_code=404, detail="Graph not found")
    
    # Load recent data for this graph
    try:
        data_file = get_data_file_path(datetime.now())
        if data_file.exists():
            with open(data_file, 'r') as f:
                recent_data = json.load(f)
                # Filter data for this graph's metrics
                graph.data = GraphData(
                    timestamps=recent_data.get("timestamps", [])[-100:],  # Last 100 points
                    values={
                        metric: recent_data.get(metric, [])[-100:]
                        for metric in graph.metrics
                    }
                )
    except Exception as e:
        # Return graph without data if file read fails
        graph.data = GraphData(timestamps=[], values={})
    
    return graph

@router.post("/", response_model=GraphModel)
async def create_graph(graph_data: Dict[str, Any]):
    """Create new dashboard graph with specified configuration."""
    # Generate ID if not provided
    if 'id' not in graph_data or not graph_data['id']:
        graph_data['id'] = str(uuid.uuid4())
    
    graph = GraphModel(**graph_data)
    save_graph_to_file(graph)
    return graph

@router.put("/{graph_id}", response_model=GraphModel)
async def update_graph(graph_id: str, updates: Dict[str, Any]):
    """Update existing graph configuration and settings."""
    graph = load_graph_from_file(graph_id)
    if not graph:
        raise HTTPException(status_code=404, detail="Graph not found")
    
    # Deep merge updates to preserve nested structures
    update_data = graph.dict()
    
    def deep_merge(base_dict, update_dict):
        """Recursively merge dictionaries."""
        for key, value in update_dict.items():
            if key in base_dict and isinstance(base_dict[key], dict) and isinstance(value, dict):
                deep_merge(base_dict[key], value)
            else:
                base_dict[key] = value
    
    deep_merge(update_data, updates)
    
    # Ensure updated_at is refreshed
    update_data['updated_at'] = datetime.now()
    
    updated_graph = GraphModel(**update_data)
    save_graph_to_file(updated_graph)
    return updated_graph

@router.delete("/{graph_id}", status_code=204)
async def delete_graph(graph_id: str):
    """Remove graph from dashboard."""
    if not delete_graph_file(graph_id):
        raise HTTPException(status_code=404, detail="Graph not found")
    return

@router.post("/batch/layout")
async def update_batch_layout(layout_updates: List[Dict[str, Any]]):
    """Update layout for multiple graphs simultaneously."""
    updated_graphs = []
    
    for update in layout_updates:
        graph_id = update.get("id")
        layout = update.get("layout")
        
        if not graph_id or not layout:
            continue
            
        graph = load_graph_from_file(graph_id)
        if graph:
            graph.layout = GraphLayout(**layout)
            graph.updated_at = datetime.now()
            save_graph_to_file(graph)
            updated_graphs.append(graph_id)
    
    return {"updated_graphs": updated_graphs, "count": len(updated_graphs)}

@router.get("/{graph_id}/data")
async def get_graph_data(
    graph_id: str,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    limit: Optional[int] = 1000
):
    """Get historical data for specific graph with time range filtering."""
    graph = load_graph_from_file(graph_id)
    if not graph:
        raise HTTPException(status_code=404, detail="Graph not found")
    
    # Parse time range
    end_dt = datetime.fromisoformat(end_time) if end_time else datetime.now()
    start_dt = datetime.fromisoformat(start_time) if start_time else end_dt - timedelta(hours=24)
    
    # Collect data from relevant files
    data_points = []
    current_date = start_dt.date()
    
    while current_date <= end_dt.date():
        data_file = get_data_file_path(datetime.combine(current_date, datetime.min.time()))
        if data_file.exists():
            try:
                with open(data_file, 'r') as f:
                    file_data = json.load(f)
                    # Filter by time range and add to results
                    for i, timestamp in enumerate(file_data.get("timestamps", [])):
                        ts = datetime.fromisoformat(timestamp)
                        if start_dt <= ts <= end_dt:
                            point = {"timestamp": timestamp}
                            for metric in graph.metrics:
                                if metric in file_data and i < len(file_data[metric]):
                                    point[metric] = file_data[metric][i]
                            data_points.append(point)
            except Exception:
                pass  # Skip corrupted files
        
        current_date += timedelta(days=1)
    
    # Sort by timestamp and limit results
    data_points.sort(key=lambda x: x["timestamp"])
    if limit:
        data_points = data_points[-limit:]
    
    return {"graph_id": graph_id, "data": data_points, "count": len(data_points)}