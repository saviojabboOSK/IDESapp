# influx_service.py - Enhanced InfluxDB service with LLM parameter support
import os
from influxdb_client import InfluxDBClient
from typing import List, Dict, Any

URL    = os.getenv("INFLUXDB_URL", "http://localhost:8086")
TOKEN  = os.getenv("INFLUXDB_TOKEN", "<YOUR_TOKEN>")
ORG    = os.getenv("INFLUXDB_ORG", "<YOUR_ORG>")
BUCKET = os.getenv("INFLUXDB_BUCKET", "sensors")

_client    = InfluxDBClient(url=URL, token=TOKEN, org=ORG)
_query_api = _client.query_api()

async def fetch_timeseries(metrics: List[str], time_window: str = "24h") -> Dict[str, Any]:
    """
    Fetch time series data for specified metrics from InfluxDB.
    
    Args:
        metrics: List of metric names to fetch
        time_window: Time window for data (e.g., "1h", "24h", "7d", "30d")
        
    Returns:
        Dictionary with series data formatted for graph generation
    """
    series = []
    
    for metric in metrics:
        flux = f'''
        from(bucket:"{BUCKET}")
          |> range(start: -{time_window})
          |> filter(fn: (r) => r["_measurement"] == "{metric}")
          |> keep(columns: ["_time","_value"])
          |> sort(columns: ["_time"])
        '''
        
        try:
            tables = _query_api.query(flux)
            data_points = []
            
            for table in tables:
                for rec in table.records:
                    timestamp = rec.get_time().isoformat() + "Z"
                    value = rec.get_value()
                    data_points.append([timestamp, value])
            
            if data_points:
                series.append({
                    "name": metric.title(),
                    "data": data_points
                })
                
        except Exception as e:
            print(f"Error fetching metric {metric}: {e}")
            continue
    
    return {"series": series}

# Legacy function for backward compatibility
async def fetch_timeseries_legacy(metric: str, floor: int, window: str = "1m"):
    """Legacy function kept for backward compatibility."""
    flux = f'''
    from(bucket:"{BUCKET}")
      |> range(start: -{window})
      |> filter(fn: (r) => r["_measurement"] == "{metric}")
      |> filter(fn: (r) => r["floor"] == "{floor}")
      |> keep(columns: ["_time","_value"])
    '''
    tables = _query_api.query(flux)
    return [
      {"timestamp": rec.get_time().isoformat(), "value": rec.get_value()}
      for table in tables for rec in table.records
    ]
