You want a flexible filter system for comparing metrics across three data sources:

Cloud Data (e.g., Cisco API)
Local Data (e.g., InfluxDB)
External Data (e.g., weather, air quality APIs)
Filter Hierarchy:

Source: Cloud / Local / External
Building: (for Cloud/Local) Select building
Floor: Select floor
Room/Area: Select room or general area (optionally aggregate sensor data)
Metric/Data Type: Select metric (e.g., temperature, humidity, device count, air quality, etc.)
External Data:

Source: External
Location: City/Region
Metric/Data Type: Weather, air quality, temp, humidity, etc.
Comparison Example:

Compare humidity in Cloud Data (Building X, Floor Y, Room Z)
vs.
Temperature in Local Data (Building X, Floor A, Room B)
vs.
External weather data (City, humidity)