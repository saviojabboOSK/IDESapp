# Script to convert filtered_influx_data.csv to the expected sensors_YYYY_MM_DD.json format for IDESapp
# Usage: python convert_csv_to_json.py <input_csv> <output_json>

import csv
import json
import sys
from datetime import datetime
from collections import defaultdict

if len(sys.argv) != 3:
    print("Usage: python convert_csv_to_json.py <input_csv> <output_json>")
    sys.exit(1)

input_csv = sys.argv[1]
output_json = sys.argv[2]

# These are the expected fields in the JSON output
data = defaultdict(list)

with open(input_csv, 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        # Adjust these field names if your CSV columns differ
        # Try to match the JSON keys: timestamps, temperature, humidity, co2, aqi, pressure, light_level
        # Example mapping for InfluxDB export:
        # _time, temperature, humidity, co2, aqi, pressure, light_level
        ts = row.get('_time') or row.get('time')
        if ts:
            data['timestamps'].append(ts)
        for key in ['temperature', 'humidity', 'co2', 'aqi', 'pressure', 'light_level']:
            val = row.get(key)
            if val is not None:
                try:
                    val = float(val)
                except ValueError:
                    val = None
            data[key].append(val)

# Remove empty lists for missing columns
data = {k: v for k, v in data.items() if v}

with open(output_json, 'w') as f:
    json.dump(data, f, indent=2)

print(f"Converted {input_csv} to {output_json}")
