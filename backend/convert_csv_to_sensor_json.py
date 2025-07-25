#!/usr/bin/env python3
"""
Smart CSV to Sensor JSON Converter for IDESapp
Automatically detects MAC addresses, metrics, timestamps from InfluxDB CSV exports
"""

import csv
import json
import pandas as pd
from datetime import datetime
from collections import defaultdict
from pathlib import Path
import argparse

def parse_timestamp(timestamp_str):
    """Parse various timestamp formats to ISO format"""
    # Handle RFC3339 format from InfluxDB
    if timestamp_str.endswith('Z'):
        # Remove Z and parse
        dt = datetime.fromisoformat(timestamp_str[:-1])
        return dt.isoformat()
    
    # Handle other common formats
    try:
        # Try parsing as ISO format
        dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        return dt.isoformat()
    except:
        # Fallback to original string
        return timestamp_str

def detect_csv_structure(csv_file):
    """Automatically detect the structure of the CSV file"""
    with open(csv_file, 'r') as f:
        # Read first few lines to understand structure
        lines = []
        for i, line in enumerate(f):
            lines.append(line.strip())
            if i >= 10:  # Read enough lines to understand structure
                break
    
    # Find the actual header line (skip InfluxDB metadata)
    header_line = None
    data_start = 0
    
    for i, line in enumerate(lines):
        if line and not line.startswith('measurement_time') and not line.startswith('false') and not line.startswith('dateTime'):
            # Look for the actual column headers
            if '_time' in line and '_value' in line and '_field' in line:
                header_line = line
                data_start = i
                break
    
    if not header_line:
        raise ValueError("Could not detect CSV structure. Expected InfluxDB export format.")
    
    headers = [h.strip() for h in header_line.split(',')]
    
    # Fix missing MAC address column name in InfluxDB exports
    if len(headers) == 4 and headers[3] == '':
        headers[3] = 'mac_address'
    elif len(headers) == 3:
        headers.append('mac_address')
    
    print(f"Detected headers: {headers}")
    print(f"Data starts at line: {data_start + 1}")
    
    return headers, data_start

def analyze_data(csv_file, headers, data_start):
    """Analyze the CSV data to extract MAC addresses, metrics, and time range"""
    
    # Read the CSV with pandas, skipping metadata lines
    df = pd.read_csv(csv_file, skiprows=data_start, names=headers)
    
    # Clean up any empty rows
    df = df.dropna()
    
    print(f"Loaded {len(df)} data points")
    
    # Extract unique information
    mac_addresses = df['mac_address'].unique() if 'mac_address' in df.columns else []
    metrics = df['_field'].unique() if '_field' in df.columns else []
    
    # Filter out empty/invalid MAC addresses
    mac_addresses = [mac for mac in mac_addresses if mac and str(mac) != 'nan']
    metrics = [metric for metric in metrics if metric and str(metric) != 'nan']
    
    # Time range
    time_col = '_time'
    timestamps = pd.to_datetime(df[time_col])
    time_range = {
        'start': timestamps.min().isoformat(),
        'end': timestamps.max().isoformat(),
        'count': len(timestamps)
    }
    
    print(f"Found {len(mac_addresses)} MAC addresses: {mac_addresses}")
    print(f"Found {len(metrics)} metrics: {metrics}")
    print(f"Time range: {time_range['start']} to {time_range['end']}")
    
    return mac_addresses, metrics, time_range, df

def create_sensor_config(mac_addresses, output_dir):
    """Create sensor configuration based on detected MAC addresses"""
    
    sensors = []
    for i, mac in enumerate(mac_addresses, 1):
        # Generate friendly names based on MAC address patterns
        sensor_id = f"sensor_{i:03d}"
        
        # Create location names based on MAC patterns or sequential naming
        locations = ["Living Room", "Bedroom", "Kitchen", "Office", "Basement", "Garage"]
        location = locations[(i-1) % len(locations)]
        
        sensor = {
            "id": sensor_id,
            "mac_address": mac,
            "nickname": location,
            "location": location,
            "model": "Environmental Sensor v2.1",
            "installed_at": "2025-01-15T10:00:00"
        }
        sensors.append(sensor)
    
    config = {
        "version": "1.0",
        "created_at": datetime.now().isoformat(),
        "sensors": sensors
    }
    
    config_file = Path(output_dir) / "sensor_config.json"
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"Created sensor configuration: {config_file}")
    return sensors

def convert_csv_to_sensor_json(csv_file, output_file, sensor_config):
    """Convert CSV data to sensor-grouped JSON format"""
    
    # Detect CSV structure
    headers, data_start = detect_csv_structure(csv_file)
    
    # Analyze the data
    mac_addresses, metrics, time_range, df = analyze_data(csv_file, headers, data_start)
    
    # Create sensor mapping
    sensor_map = {sensor['mac_address']: sensor for sensor in sensor_config}
    
    # Group data by sensor and metric
    sensors_data = defaultdict(lambda: {
        'mac_address': '',
        'nickname': '',
        'location': '',
        'metrics': defaultdict(lambda: {'timestamps': [], 'values': []})
    })
    
    print("Converting data to sensor-grouped format...")
    
    # Process each row
    for _, row in df.iterrows():
        timestamp = parse_timestamp(str(row['_time']))     # _time
        value = float(row['_value'])                       # _value  
        metric = str(row['_field'])                        # _field
        mac_address = str(row['mac_address'])              # mac_address
        
        # Find sensor info
        sensor_info = sensor_map.get(mac_address, {})
        sensor_id = None
        
        # Find sensor ID by MAC address
        for sensor in sensor_config:
            if sensor['mac_address'] == mac_address:
                sensor_id = sensor['id']
                break
        
        if not sensor_id:
            # Create a new sensor ID if not found
            sensor_id = f"sensor_{len(sensor_config) + 1:03d}"
            print(f"Warning: MAC address {mac_address} not in config, using {sensor_id}")
        
        # Add to sensors data
        if sensor_id not in sensors_data:
            sensors_data[sensor_id].update({
                'mac_address': mac_address,
                'nickname': sensor_info.get('nickname', f'Sensor {sensor_id}'),
                'location': sensor_info.get('location', f'Location {sensor_id}')
            })
        
        # Add the data point
        sensors_data[sensor_id]['metrics'][metric]['timestamps'].append(timestamp)
        sensors_data[sensor_id]['metrics'][metric]['values'].append(value)
    
    # Create final JSON structure
    final_data = {
        'sensors': dict(sensors_data),
        'metadata': {
            'version': '2.0',
            'converted_at': datetime.now().isoformat(),
            'source_file': str(csv_file),
            'total_sensors': len(sensors_data),
            'available_metrics': list(metrics),
            'time_range': time_range
        }
    }
    
    # Write output file
    with open(output_file, 'w') as f:
        json.dump(final_data, f, indent=2)
    
    print(f"Converted data saved to: {output_file}")
    print(f"Total sensors: {len(sensors_data)}")
    print(f"Total metrics per sensor: {len(metrics)}")
    
    return final_data

def main():
    parser = argparse.ArgumentParser(description='Convert InfluxDB CSV to sensor JSON format')
    parser.add_argument('csv_file', help='Input CSV file from InfluxDB')
    parser.add_argument('-o', '--output', help='Output JSON file', default='sensors_converted.json')
    parser.add_argument('-d', '--data-dir', help='Data directory for config files', default='data')
    parser.add_argument('--no-config', action='store_true', help='Skip sensor config creation')
    
    args = parser.parse_args()
    
    csv_file = Path(args.csv_file)
    output_file = Path(args.output)
    data_dir = Path(args.data_dir)
    
    if not csv_file.exists():
        print(f"Error: CSV file {csv_file} not found")
        return 1
    
    # Create data directory if it doesn't exist
    data_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # First pass: analyze data to get MAC addresses
        headers, data_start = detect_csv_structure(csv_file)
        mac_addresses, metrics, time_range, _ = analyze_data(csv_file, headers, data_start)
        
        # Create or load sensor configuration
        config_file = data_dir / "sensor_config.json"
        
        if not args.no_config:
            if config_file.exists():
                print(f"Loading existing sensor config: {config_file}")
                with open(config_file, 'r') as f:
                    config = json.load(f)
                    sensor_config = config.get('sensors', [])
            else:
                print("Creating new sensor configuration...")
                sensor_config = create_sensor_config(mac_addresses, data_dir)
        else:
            # Create minimal config from detected MAC addresses
            sensor_config = []
            for i, mac in enumerate(mac_addresses, 1):
                sensor_config.append({
                    'id': f'sensor_{i:03d}',
                    'mac_address': mac,
                    'nickname': f'Sensor {i}',
                    'location': f'Location {i}'
                })
        
        # Convert the data
        result = convert_csv_to_sensor_json(csv_file, output_file, sensor_config)
        
        print("\n✅ Conversion completed successfully!")
        print(f"📊 Processed {result['metadata']['time_range']['count']} data points")
        print(f"🔧 Found {result['metadata']['total_sensors']} sensors")
        print(f"📈 Detected metrics: {', '.join(result['metadata']['available_metrics'])}")
        
        return 0
        
    except Exception as e:
        print(f"❌ Error during conversion: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    exit(main())
