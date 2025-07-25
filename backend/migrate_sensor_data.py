#!/usr/bin/env python3
"""
Migration script to convert existing flat sensor data format to grouped-by-sensor format.

Current format:
{
  "timestamps": [...],
  "temperature": [...],
  "humidity": [...],
  "co2": [...],
  "aqi": [...],
  "pressure": [...],
  "light_level": [...]
}

New format:
{
  "sensors": {
    "sensor_id_1": {
      "mac_address": "AA:BB:CC:DD:EE:01",
      "nickname": "Living Room Sensor",
      "location": "Living Room", 
      "metrics": {
        "temperature": {
          "timestamps": [...],
          "values": [...]
        },
        "humidity": {
          "timestamps": [...],
          "values": [...]
        },
        ...
      }
    },
    "sensor_id_2": {
      ...
    }
  },
  "metadata": {
    "version": "2.0",
    "migrated_at": "2025-07-25T...",
    "total_sensors": 2,
    "available_metrics": ["temperature", "humidity", "co2", "aqi", "pressure", "light_level"]
  }
}
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
import uuid


def generate_mock_sensor_info(num_sensors: int = 3) -> List[Dict[str, str]]:
    """Generate mock sensor information for demonstration."""
    locations = ["Living Room", "Bedroom", "Kitchen", "Office", "Basement", "Garage"]
    sensor_infos = []
    
    for i in range(num_sensors):
        mac_parts = [f"{j:02X}" for j in range(6)]
        mac_parts[-1] = f"{i+1:02X}"  # Make last part unique
        mac_address = ":".join(mac_parts)
        
        location = locations[i % len(locations)]
        
        sensor_infos.append({
            "id": f"sensor_{i+1:03d}",
            "mac_address": mac_address, 
            "nickname": f"{location} Sensor",
            "location": location
        })
    
    return sensor_infos


def migrate_data_file(input_file: Path, output_file: Path, sensor_infos: List[Dict[str, str]] = None) -> bool:
    """Migrate a single data file from old format to new format."""
    
    if not input_file.exists():
        print(f"Input file {input_file} does not exist")
        return False
    
    print(f"Migrating {input_file} -> {output_file}")
    
    # Load existing data
    try:
        with open(input_file, 'r') as f:
            old_data = json.load(f)
    except Exception as e:
        print(f"Error reading {input_file}: {e}")
        return False
    
    if "timestamps" not in old_data:
        print(f"Invalid data format in {input_file} - missing timestamps")
        return False
    
    timestamps = old_data["timestamps"]
    num_points = len(timestamps)
    
    # Available metrics from old format
    available_metrics = [key for key in old_data.keys() if key != "timestamps" and isinstance(old_data[key], list)]
    
    if not available_metrics:
        print(f"No metric data found in {input_file}")
        return False
    
    # Generate sensor info if not provided
    if sensor_infos is None:
        # Auto-detect how many sensors we might have based on data patterns
        # For now, let's split data across 3 sensors as an example
        num_sensors = 3
        sensor_infos = generate_mock_sensor_info(num_sensors)
    
    # Create new data structure
    new_data = {
        "sensors": {},
        "metadata": {
            "version": "2.0",
            "migrated_at": datetime.now().isoformat(),
            "total_sensors": len(sensor_infos),
            "available_metrics": available_metrics,
            "migration_source": str(input_file),
            "total_data_points": num_points
        }
    }
    
    # Distribute data points across sensors
    # For demonstration, we'll chunk the data by time ranges
    points_per_sensor = max(1, num_points // len(sensor_infos))
    
    for i, sensor_info in enumerate(sensor_infos):
        sensor_id = sensor_info["id"]
        
        # Calculate data range for this sensor
        start_idx = i * points_per_sensor
        if i == len(sensor_infos) - 1:  # Last sensor gets remaining data
            end_idx = num_points
        else:
            end_idx = min(start_idx + points_per_sensor, num_points)
        
        if start_idx >= num_points:
            # No more data for this sensor
            continue
            
        sensor_timestamps = timestamps[start_idx:end_idx]
        
        new_data["sensors"][sensor_id] = {
            "mac_address": sensor_info["mac_address"],
            "nickname": sensor_info["nickname"],
            "location": sensor_info["location"],
            "metrics": {}
        }
        
        # Add metric data for this sensor
        for metric in available_metrics:
            if metric in old_data and len(old_data[metric]) > start_idx:
                metric_values = old_data[metric][start_idx:end_idx]
                
                # Ensure we have matching timestamp and value counts
                min_length = min(len(sensor_timestamps), len(metric_values))
                
                new_data["sensors"][sensor_id]["metrics"][metric] = {
                    "timestamps": sensor_timestamps[:min_length],
                    "values": metric_values[:min_length]
                }
    
    # Save migrated data
    try:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w') as f:
            json.dump(new_data, f, indent=2)
        print(f"Successfully migrated to {output_file}")
        return True
    except Exception as e:
        print(f"Error writing {output_file}: {e}")
        return False


def migrate_all_data_files(data_dir: Path, backup_suffix: str = ".backup") -> bool:
    """Migrate all sensor data files in a directory."""
    
    if not data_dir.exists():
        print(f"Data directory {data_dir} does not exist")
        return False
    
    # Find all sensor data files
    sensor_files = list(data_dir.glob("sensors_*.json"))
    
    if not sensor_files:
        print(f"No sensor data files found in {data_dir}")
        return False
    
    print(f"Found {len(sensor_files)} sensor data files to migrate")
    
    # Load or generate sensor configuration
    sensor_config_file = data_dir / "sensor_config.json"
    sensor_infos = None
    
    if sensor_config_file.exists():
        try:
            with open(sensor_config_file, 'r') as f:
                config = json.load(f)
                sensor_infos = config.get("sensors", [])
                print(f"Loaded sensor configuration with {len(sensor_infos)} sensors")
        except Exception as e:
            print(f"Error loading sensor config: {e}")
    
    success_count = 0
    
    for sensor_file in sensor_files:
        # Create backup
        backup_file = sensor_file.with_suffix(sensor_file.suffix + backup_suffix)
        try:
            backup_file.write_text(sensor_file.read_text())
            print(f"Created backup: {backup_file}")
        except Exception as e:
            print(f"Warning: Could not create backup for {sensor_file}: {e}")
        
        # Migrate the file
        if migrate_data_file(sensor_file, sensor_file, sensor_infos):
            success_count += 1
    
    print(f"Migration complete: {success_count}/{len(sensor_files)} files migrated successfully")
    return success_count == len(sensor_files)


def create_sample_sensor_config(data_dir: Path) -> None:
    """Create a sample sensor configuration file."""
    config_file = data_dir / "sensor_config.json"
    
    sample_config = {
        "version": "1.0",
        "created_at": datetime.now().isoformat(),
        "sensors": [
            {
                "id": "sensor_001",
                "mac_address": "AA:BB:CC:DD:EE:01",
                "nickname": "Living Room",
                "location": "Living Room",
                "model": "Environmental Sensor v2.1",
                "installed_at": "2025-01-15T10:00:00"
            },
            {
                "id": "sensor_002", 
                "mac_address": "AA:BB:CC:DD:EE:02",
                "nickname": "Bedroom",
                "location": "Master Bedroom",
                "model": "Environmental Sensor v2.1",
                "installed_at": "2025-01-15T10:30:00"
            },
            {
                "id": "sensor_003",
                "mac_address": "AA:BB:CC:DD:EE:03", 
                "nickname": "Kitchen",
                "location": "Kitchen",
                "model": "Environmental Sensor v2.1",
                "installed_at": "2025-01-15T11:00:00"
            }
        ]
    }
    
    try:
        with open(config_file, 'w') as f:
            json.dump(sample_config, f, indent=2)
        print(f"Created sample sensor configuration: {config_file}")
    except Exception as e:
        print(f"Error creating sensor config: {e}")


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python migrate_sensor_data.py <data_directory>  # Migrate all files in directory")
        print("  python migrate_sensor_data.py <input_file> <output_file>  # Migrate single file")
        print("  python migrate_sensor_data.py --create-config <data_directory>  # Create sample sensor config")
        sys.exit(1)
    
    if sys.argv[1] == "--create-config":
        if len(sys.argv) != 3:
            print("Usage: python migrate_sensor_data.py --create-config <data_directory>")
            sys.exit(1)
        data_dir = Path(sys.argv[2])
        create_sample_sensor_config(data_dir)
        return
    
    if len(sys.argv) == 2:
        # Migrate all files in directory
        data_dir = Path(sys.argv[1])
        success = migrate_all_data_files(data_dir)
        sys.exit(0 if success else 1)
    
    elif len(sys.argv) == 3:
        # Migrate single file
        input_file = Path(sys.argv[1])
        output_file = Path(sys.argv[2])
        success = migrate_data_file(input_file, output_file)
        sys.exit(0 if success else 1)
    
    else:
        print("Invalid arguments")
        sys.exit(1)


if __name__ == "__main__":
    main()
