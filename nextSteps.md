# Unified Data Filter & Graph System

## Data Sources
- **Cloud Data** (e.g., Cisco Access Points API)
- **Local Data** (e.g., InfluxDB, per building)
- **External Data** (e.g., weather, air quality APIs)

## Filter Hierarchy

### For Cloud/Local Data
- **Source:** Cloud or Local
- **Building:** Select building (e.g., Building X)
- **Floor:** Select floor (e.g., Floor Y)
- **Room/Area:** Select room or general area (optionally aggregate multiple sensors, e.g., mean value)
- **Metric/Data Type:** Select metric (e.g., temperature, humidity, device count, signal strength)

### For External Data
- **Source:** External
- **Location:** Select city or region
- **Metric/Data Type:** Select metric (e.g., weather, air quality, temp, humidity)

## Graphing & Comparison
- Users can add multiple metrics from different sources, buildings, floors, rooms, and metric types to a single graph for comparison.
- Metrics from different sources/areas are plotted together.
- If a dataset is unavailable (e.g., only Local Data is accessible due to WiFi outage), the corresponding graph line is grayed out until data is available again.

## Backend Implementation
- Endpoints to list available sources, buildings, floors, rooms/areas, and metrics.
- Endpoint to fetch time-series metric data for selected filters.
- Endpoint to report data source availability status.

## Data Model
```ts
{
timestamp: string,
value: number,
source: "Cloud" | "Local" | "External",
building?: string,
floor?: string,
roomOrArea?: string,
location?: string, // for external data
metricType: string,
available: boolean
}
```

## Frontend Implementation
- Dynamic dropdowns/selects for each filter level.
- Option to aggregate sensor data (e.g., mean value for an area).
- Graph component displays all selected metrics, with unavailable data grayed out.
- Periodic polling for data updates and source availability.

## Design Considerations
- Modular backend and frontend for easy addition of new sources, locations, metrics, and external APIs.
- Graceful handling of data unavailability, with auto-refresh when data becomes