# backend/influx_service.py
#
# This module handles all interactions with InfluxDB, a time-series database.
# It provides functionality for:
# - Connecting to InfluxDB using environment configuration
# - Querying sensor data across different time windows
# - Converting InfluxDB results into standardized series format
# - Supporting multiple metrics (temperature, humidity, etc.) in single queries

import os
from typing import List, Dict, Any
from influxdb_client import InfluxDBClient

# ─── InfluxDB Configuration ────────────────────────────────────────────────
# Load connection settings from environment variables
# These should be configured in your .env file
URL    = os.getenv("INFLUXDB_URL",  "http://localhost:8086")    # InfluxDB server URL
TOKEN  = os.getenv("INFLUXDB_TOKEN", "")                       # Authentication token
ORG    = os.getenv("INFLUXDB_ORG",   "")                       # Organization name
BUCKET = os.getenv("INFLUXDB_BUCKET","sensors")                # Data bucket name

# ─── Database Client Setup ─────────────────────────────────────────────────
# Initialize InfluxDB client with configuration
# timeout=3000 prevents hanging on slow queries
_client = InfluxDBClient(url=URL, token=TOKEN, org=ORG, timeout=3000)
_query  = _client.query_api()  # Query API for running Flux queries

async def fetch_timeseries(metrics: List[str], window: str = "24h") -> Dict[str,Any]:
    """
    Fetch time-series data for specified metrics from InfluxDB.
    
    This function queries InfluxDB for sensor data and returns it in a standardized
    format suitable for graphing and analysis. It handles multiple metrics in a
    single call and formats the results consistently.
    
    Args:
        metrics: List of sensor types to query (e.g., ["temperature", "humidity"])
        window: Time window for the query (e.g., "24h", "7d", "30d")
        
    Returns:
        Dict containing "series" list with data for each metric:
        {
            "series": [
                {
                    "label": "Temperature",
                    "x": ["2023-01-01T00:00:00Z", "2023-01-01T01:00:00Z", ...],
                    "y": [23.5, 24.1, 23.8, ...]
                },
                ...
            ]
        }
        
    Query Details:
        - Uses Flux query language for InfluxDB 2.x
        - Filters by measurement name (metric type)
        - Sorts results by timestamp
        - Returns only time and value columns
        
    Error Handling:
        - If a metric has no data, it's simply omitted from results
        - Empty series list is returned if no data found for any metric
    """
    series = []
    
    # Query each metric separately to handle different measurement types
    for m in metrics:
        # ── Build Flux query for this metric ──────────────────────────────
        # Flux is InfluxDB's functional query language
        flux = (
            f'from(bucket:"{BUCKET}")'                              # Source bucket
            f' |> range(start:-{window})'                           # Time window (e.g., last 24h)
            f' |> filter(fn: (r) => r["_measurement"] == "{m}")'    # Filter by metric type
            f' |> keep(columns: ["_time","_value"])'                # Keep only time and value
            f' |> sort(columns: ["_time"])'                         # Sort chronologically
        )
        
        # ── Execute query and process results ─────────────────────────────
        records = _query.query(flux)
        
        # Convert InfluxDB records to [timestamp, value] pairs
        pts = [
            [rec.get_time().isoformat()+"Z", rec.get_value()]  # ISO format with Z suffix
            for tbl in records                                 # Iterate through tables
            for rec in tbl.records                             # Iterate through records
        ]
        
        # ── Add to series if data found ───────────────────────────────────
        if pts:
            series.append({
                "label": m.title(),                    # Capitalize metric name (e.g., "Temperature")
                "x": [p[0] for p in pts],             # Extract timestamps for x-axis
                "y": [p[1] for p in pts]              # Extract values for y-axis
            })
    
    return {"series": series}
