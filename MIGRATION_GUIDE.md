# IDESapp 2.0 - Sensor-Based Data Architecture Migration

This document explains the new sensor-based architecture and migration process for IDESapp 2.0.

## 🔄 What Changed

### Previous Data Format (v1.0)
```json
{
  "timestamps": ["2025-07-23T12:48:02.702866", ...],
  "temperature": [22.1, 22.3, 22.5, ...],
  "humidity": [45.2, 45.8, 46.1, ...],
  "co2": [420, 425, 430, ...],
  "aqi": [35, 36, 35, ...],
  "pressure": [1013.25, 1013.30, ...],
  "light_level": [300, 320, 340, ...]
}
```

### New Data Format (v2.0)
```json
{
  "sensors": {
    "sensor_001": {
      "mac_address": "AA:BB:CC:DD:EE:01",
      "nickname": "Living Room",
      "location": "Living Room",
      "metrics": {
        "temperature": {
          "timestamps": ["2025-07-23T12:48:02.702866", ...],
          "values": [22.1, 22.3, 22.5, ...]
        },
        "humidity": {
          "timestamps": ["2025-07-23T12:48:02.702866", ...],
          "values": [45.2, 45.8, 46.1, ...]
        }
      }
    },
    "sensor_002": {
      "mac_address": "AA:BB:CC:DD:EE:02",
      "nickname": "Bedroom",
      "location": "Master Bedroom",
      "metrics": { ... }
    }
  },
  "metadata": {
    "version": "2.0",
    "migrated_at": "2025-07-25T...",
    "total_sensors": 2,
    "available_metrics": ["temperature", "humidity", "co2", "aqi", "pressure", "light_level"]
  }
}
```

## 🚀 New Features

### 1. Sensor Selection
- Users first select a sensor by MAC address or nickname
- Only metrics available for that sensor are then selectable
- Graph titles automatically include sensor information

### 2. Sensor Nicknames
- Assign friendly names to sensors via Settings page
- Nicknames are stored persistently and displayed throughout the UI
- Fallback to MAC address if no nickname is set

### 3. Custom Timeframes
- All predefined ranges (1h, 6h, 12h, 24h, 7d, 30d)
- Custom date/time range selection
- Data shows as far back as available, with empty periods for missing data

### 4. Enhanced Graph Builder
- Step-by-step workflow: Sensor → Metrics → Settings
- Real-time metric availability based on selected sensor
- Visual sensor status indicators

## 📦 Migration Process

### Automatic Migration
Run the migration script to automatically convert your data:

```bash
chmod +x run_migration.sh
./run_migration.sh
```

This will:
1. Create sample sensor configuration
2. Backup existing data files (`.backup` extension)
3. Convert data to new sensor-grouped format
4. Preserve all existing data

### Manual Migration
If you need to migrate specific files:

```bash
cd backend

# Create sensor configuration
python3 migrate_sensor_data.py --create-config data/

# Migrate specific file
python3 migrate_sensor_data.py data/sensors_2025_07_21.json data/sensors_2025_07_21_new.json

# Migrate all files in directory
python3 migrate_sensor_data.py data/
```

## 🔧 Backend API Changes

### New Endpoints

#### Sensors Management
- `GET /api/sensors` - List all sensors
- `GET /api/sensors/{sensor_id}` - Get sensor details
- `GET /api/sensors/{sensor_id}/data` - Get sensor data with filtering
- `PUT /api/sensors/{sensor_id}/nickname` - Update sensor nickname
- `GET /api/sensors/{sensor_id}/metrics` - Get available metrics for sensor
- `POST /api/sensors/batch/nicknames` - Update multiple nicknames

#### Enhanced Graph API
- Graphs now support `sensor_id` field
- Custom time ranges with `custom_start_time` and `custom_end_time`
- Backward compatibility maintained for existing graphs

### Configuration Files

#### Sensor Configuration (`backend/data/sensor_config.json`)
```json
{
  "version": "1.0",
  "created_at": "2025-07-25T...",
  "sensors": [
    {
      "id": "sensor_001",
      "mac_address": "AA:BB:CC:DD:EE:01",
      "nickname": "Living Room",
      "location": "Living Room",
      "model": "Environmental Sensor v2.1",
      "installed_at": "2025-01-15T10:00:00"
    }
  ]
}
```

#### Sensor Nicknames (`backend/data/sensor_nicknames.json`)
```json
{
  "nicknames": {
    "sensor_001": "Living Room",
    "sensor_002": "Bedroom",
    "sensor_003": "Kitchen"
  },
  "updated_at": "2025-07-25T..."
}
```

## 🎨 Frontend Changes

### New Components

#### GraphBuilderModalEnhanced
- Replaces the original GraphBuilderModal
- Adds sensor selection step
- Shows available metrics per sensor
- Custom timeframe selection

#### SensorSettings
- New settings page for managing sensor nicknames
- Shows sensor status and last seen information
- Bulk nickname updates

### Updated Components

#### GridDashboard
- Uses new GraphBuilderModalEnhanced
- Supports new graph config format with sensor_id

#### Graph Cards
- Display sensor nickname in titles
- Show which sensor data is from

## 🔍 Data Flow

### Graph Creation Flow
1. User opens Graph Builder
2. System loads available sensors from `/api/sensors`
3. User selects sensor
4. System shows available metrics for selected sensor
5. User selects metrics and configures graph
6. Graph is created with `sensor_id` and `metrics`

### Data Retrieval Flow
1. Graph requests data from `/api/graphs/{graph_id}/data`
2. Backend checks if graph has `sensor_id`
3. If yes, loads data from new sensor-grouped format
4. If no `sensor_id`, falls back to old flat format (backward compatibility)
5. Data is filtered by time range and metrics
6. Response includes properly formatted data points

## 🔒 Backward Compatibility

The new system maintains full backward compatibility:

- Existing graphs without `sensor_id` continue to work
- Old data format is automatically detected and processed
- All existing API endpoints function as before
- Gradual migration - users can update graphs as needed

## 🐛 Troubleshooting

### Common Issues

#### No Sensors Found
- Check if sensor configuration exists: `backend/data/sensor_config.json`
- Run sensor discovery: refresh the Settings page
- Verify data files are in new format

#### Missing Data
- Check data file format in `backend/data/sensors_*.json`
- Verify sensor_id matches between graph config and data
- Check API logs for data loading errors

#### Migration Errors
- Ensure Python 3 is installed
- Check file permissions in `backend/data/` directory
- Verify input data files are valid JSON

### Recovery

If migration fails, restore from backups:
```bash
cd backend/data
for file in *.backup; do
    mv "$file" "${file%.backup}"
done
```

## 📋 Testing

After migration, verify:

1. ✅ Sensors appear in Settings page
2. ✅ Can update sensor nicknames
3. ✅ Graph builder shows sensor selection
4. ✅ Can create graphs with sensor selection
5. ✅ Existing graphs still display data
6. ✅ Custom timeframes work correctly

## 🎯 Next Steps

1. **Configure Sensors**: Update sensor nicknames in Settings
2. **Update Graphs**: Recreate important graphs with sensor selection
3. **Monitor Data**: Verify real-time data updates work correctly
4. **Customize**: Adjust timeframes and visualization settings

For support or questions, refer to the main README.md or create an issue in the repository.
