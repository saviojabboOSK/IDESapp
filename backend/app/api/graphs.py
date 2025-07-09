# REST API endpoints for graph management including CRUD operations for dashboard charts, real-time data retrieval, and customizable visualization settings for sensor metrics.

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import json
import os
from pathlib import Path

from app.core.config import settings
from app.models.graph import GraphModel, GraphSettings, GraphData

router = APIRouter()

# In-memory storage for demo (replace with database in production)
graphs_db: Dict[str, GraphModel] = {}

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
    if not graphs_db:
        # Create default graphs for demo
        default_graphs = [
            GraphModel(
                id="temp_humidity",
                title="Temperature & Humidity",
                chart_type="line",
                metrics=["temperature", "humidity"],
                time_range="24h",
                settings=GraphSettings(
                    color_scheme=["#3b82f6", "#ef4444"],
                    show_legend=True,
                    show_grid=True
                )
            ),
            GraphModel(
                id="co2_aqi",
                title="CO₂ & Air Quality",
                chart_type="area",
                metrics=["co2", "aqi"],
                time_range="12h",
                settings=GraphSettings(
                    color_scheme=["#22c55e", "#f59e0b"],
                    show_legend=True,
                    show_grid=True
                )
            )
        ]
        for graph in default_graphs:
            graphs_db[graph.id] = graph
    
    return list(graphs_db.values())

@router.get("/{graph_id}", response_model=GraphModel)
async def get_graph(graph_id: str):
    """Get specific graph configuration and recent data."""
    if graph_id not in graphs_db:
        raise HTTPException(status_code=404, detail="Graph not found")
    
    graph = graphs_db[graph_id]
    
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
    graph = GraphModel(**graph_data)
    graphs_db[graph.id] = graph
    return graph

@router.put("/{graph_id}", response_model=GraphModel)
async def update_graph(graph_id: str, updates: Dict[str, Any]):
    """Update existing graph configuration and settings."""
    if graph_id not in graphs_db:
        raise HTTPException(status_code=404, detail="Graph not found")
    
    graph = graphs_db[graph_id]
    
    # Update fields
    for field, value in updates.items():
        if hasattr(graph, field):
            setattr(graph, field, value)
    
    return graph

@router.delete("/{graph_id}")
async def delete_graph(graph_id: str):
    """Remove graph from dashboard."""
    if graph_id not in graphs_db:
        raise HTTPException(status_code=404, detail="Graph not found")
    
    del graphs_db[graph_id]
    return {"message": f"Graph {graph_id} deleted successfully"}

@router.get("/{graph_id}/data")
async def get_graph_data(
    graph_id: str,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    limit: Optional[int] = 1000
):
    """Get historical data for specific graph with time range filtering."""
    if graph_id not in graphs_db:
        raise HTTPException(status_code=404, detail="Graph not found")
    
    graph = graphs_db[graph_id]
    
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