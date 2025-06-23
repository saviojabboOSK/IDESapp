# influx_service.py
import os
from influxdb_client import InfluxDBClient

URL    = os.getenv("INFLUXDB_URL", "http://localhost:8086")
TOKEN  = os.getenv("INFLUXDB_TOKEN", "<YOUR_TOKEN>")
ORG    = os.getenv("INFLUXDB_ORG", "<YOUR_ORG>")
BUCKET = os.getenv("INFLUXDB_BUCKET", "sensors")

_client    = InfluxDBClient(url=URL, token=TOKEN, org=ORG)
_query_api = _client.query_api()

async def fetch_timeseries(metric: str, floor: int, window: str = "1m"):
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
