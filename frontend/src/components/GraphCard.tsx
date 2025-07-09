// Graph card component for IDES 2.0 displaying individual sensor data charts with interactive controls, flip animation for settings, and real-time data updates via Chart.js integration.

import React, { useState } from 'react'
import { Settings, X, BarChart3 } from 'lucide-react'

interface GraphCardProps {
  id: string
  title: string
  chartType: string
  metrics: string[]
  timeRange: string
  onRemove: () => void
  forecastData?: any
  accuracyMetrics?: any
}

const GraphCard: React.FC<GraphCardProps> = ({
  id: _id,
  title,
  chartType,
  metrics,
  timeRange,
  onRemove,
  forecastData: _forecastData,
  accuracyMetrics
}) => {
  const [isFlipped, setIsFlipped] = useState(false)

  const handleSettingsClick = () => {
    setIsFlipped(!isFlipped)
  }

  // Mock chart data for demonstration (commented out for now)
  // const mockData = {
  //   labels: ['12:00', '13:00', '14:00', '15:00', '16:00', '17:00'],
  //   datasets: [
  //     {
  //       label: metrics[0] || 'Data',
  //       data: [22.1, 22.3, 22.8, 23.1, 22.9, 22.7],
  //       borderColor: 'rgb(59, 130, 246)',
  //       backgroundColor: 'rgba(59, 130, 246, 0.1)',
  //     }
  //   ]
  // }

  return (
    <div className="graph-card relative overflow-hidden">
      {!isFlipped ? (
        // Front of card - Chart display
        <div className="graph-card-front p-4">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
            <div className="flex items-center space-x-2">
              <button
                onClick={handleSettingsClick}
                className="p-1 text-gray-400 hover:text-gray-600 transition-colors"
              >
                <Settings className="h-4 w-4" />
              </button>
              <button
                onClick={onRemove}
                className="p-1 text-gray-400 hover:text-red-600 transition-colors"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          </div>

          {/* Chart placeholder */}
          <div className="chart-container flex items-center justify-center bg-gray-50 rounded">
            <div className="text-center">
              <BarChart3 className="h-12 w-12 text-gray-400 mx-auto mb-2" />
              <p className="text-sm text-gray-500">
                {chartType.toUpperCase()} Chart
              </p>
              <p className="text-xs text-gray-400 mt-1">
                {metrics.join(', ')} • {timeRange}
              </p>
            </div>
          </div>

          {/* Forecast accuracy if available */}
          {accuracyMetrics && (
            <div className="mt-3 text-xs text-gray-500">
              <span className="font-medium">Forecast Accuracy:</span> {accuracyMetrics.mae}% MAE
            </div>
          )}
        </div>
      ) : (
        // Back of card - Settings
        <div className="graph-card-back p-4">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900">Settings</h3>
            <button
              onClick={handleSettingsClick}
              className="p-1 text-gray-400 hover:text-gray-600 transition-colors"
            >
              <X className="h-4 w-4" />
            </button>
          </div>

          <div className="space-y-4">
            {/* Chart Type */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Chart Type
              </label>
              <select className="form-select w-full" defaultValue={chartType}>
                <option value="line">Line Chart</option>
                <option value="area">Area Chart</option>
                <option value="bar">Bar Chart</option>
                <option value="scatter">Scatter Plot</option>
              </select>
            </div>

            {/* Metrics */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Metrics
              </label>
              <div className="space-y-2">
                {['temperature', 'humidity', 'co2', 'aqi', 'pressure', 'light_level'].map((metric) => (
                  <label key={metric} className="flex items-center">
                    <input
                      type="checkbox"
                      defaultChecked={metrics.includes(metric)}
                      className="mr-2"
                    />
                    <span className="text-sm capitalize">{metric.replace('_', ' ')}</span>
                  </label>
                ))}
              </div>
            </div>

            {/* Time Range */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Time Range
              </label>
              <select className="form-select w-full" defaultValue={timeRange}>
                <option value="1h">Last Hour</option>
                <option value="6h">Last 6 Hours</option>
                <option value="24h">Last 24 Hours</option>
                <option value="7d">Last 7 Days</option>
                <option value="30d">Last 30 Days</option>
              </select>
            </div>

            {/* Actions */}
            <div className="flex space-x-2 pt-2">
              <button className="btn-primary flex-1">
                Apply Changes
              </button>
              <button 
                onClick={handleSettingsClick}
                className="btn-secondary flex-1"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default GraphCard