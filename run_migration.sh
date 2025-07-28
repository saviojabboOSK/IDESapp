#!/bin/bash

# Migration script to update IDESapp to use sensor-grouped data format
# This script will backup existing data and convert it to the new format

set -e

echo "🔄 Starting IDESapp sensor data migration..."

# Check if backend directory exists
if [ ! -d "backend" ]; then
    echo "❌ Backend directory not found. Please run this script from the IDESapp root directory."
    exit 1
fi

# Navigate to backend directory
cd backend

# Check if Python environment is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed."
    exit 1
fi

echo "📋 Creating sample sensor configuration..."
python3 migrate_sensor_data.py --create-config data/

echo "🔄 Migrating sensor data files..."
python3 migrate_sensor_data.py data/

echo "✅ Migration completed successfully!"

echo ""
echo "📊 Summary of changes:"
echo "  - Created sensor configuration file with 3 sample sensors"
echo "  - Migrated existing data files to new sensor-grouped format"
echo "  - Original files backed up with .backup extension"
echo ""
echo "🔧 Next steps:"
echo "  1. Review sensor configuration in backend/data/sensor_config.json"
echo "  2. Update sensor nicknames via the Settings page in the web interface"
echo "  3. Create new graphs using the enhanced graph builder"
echo ""
echo "🚀 Start the application:"
echo "  Backend: cd backend && python -m uvicorn app.main:app --reload"
echo "  Frontend: cd frontend && npm run dev"
