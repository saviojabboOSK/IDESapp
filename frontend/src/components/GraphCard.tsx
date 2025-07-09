// Graph card component for IDES 2.0 displaying individual sensor data charts with interactive controls, flip animation for settings, and real-time data updates via Chart.js integration.

import React, { useState } from 'react'
import { Settings, X, BarChart3 } from 'lucide-react'
import { Bar, Line, Scatter } from 'react-chartjs-2'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
} from 'chart.js'

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
)

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
  const [localChartType, setLocalChartType] = useState(chartType)
  const [localMetrics, setLocalMetrics] = useState<string[]>(metrics)
  const [localTimeRange, setLocalTimeRange] = useState(timeRange)

  const handleSettingsClick = () => setIsFlipped(!isFlipped)

  const handleMetricChange = (metric: string) => {
    setLocalMetrics((prev) =>
      prev.includes(metric)
        ? prev.filter((m) => m !== metric)
        : [...prev, metric]
    )
  }

  const handleApply = () => {
    // Optionally, you can call a prop callback to update parent state
    setIsFlipped(false)
  }

  // Prepare chart data
  const chartData = React.useMemo(() => {
    if (!_forecastData || !localMetrics.length) {
      return null
    }
    // Assume _forecastData is an object: { labels: [], data: { metric1: [], metric2: [] } }
    const labels = _forecastData.labels || []
    const datasets = localMetrics.map((metric, idx) => ({
      label: metric,
      data: _forecastData.data?.[metric] || [],
      borderColor: [
        'rgb(59,130,246)',
        'rgb(16,185,129)',
        'rgb(239,68,68)',
        'rgb(245,158,11)',
        'rgb(168,85,247)',
        'rgb(34,197,94)'
      ][idx % 6],
      backgroundColor: [
        'rgba(59,130,246,0.2)',
        'rgba(16,185,129,0.2)',
        'rgba(239,68,68,0.2)',
        'rgba(245,158,11,0.2)',
        'rgba(168,85,247,0.2)',
        'rgba(34,197,94,0.2)'
      ][idx % 6],
      fill: localChartType === 'area',
      tension: 0.4
    }))
    return { labels, datasets }
  }, [_forecastData, localMetrics, localChartType])

  const chartOptions = {
    responsive: true,
    plugins: {
      legend: { display: true, labels: { color: '#111' } },
      title: { display: false }
    },
    scales: {
      x: { ticks: { color: '#111' } },
      y: { ticks: { color: '#111' } }
    }
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
    <div className="graph-card relative overflow-hidden bg-white rounded-lg shadow-md border border-gray-200">
      {!isFlipped ? (
        // Front of card - Chart display
        <div className="graph-card-front p-4">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-bold text-black drop-shadow-sm">{title}</h3>
            <div className="flex items-center space-x-2">
              <button
                onClick={handleSettingsClick}
                className="p-1 text-gray-700 hover:text-blue-600 transition-colors"
                aria-label="Settings"
              >
                <Settings className="h-5 w-5" />
              </button>
              <button
                onClick={onRemove}
                className="p-1 text-gray-700 hover:text-red-600 transition-colors"
                aria-label="Remove"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
          </div>

          {/* Chart display */}
          <div className="chart-container flex items-center justify-center bg-gray-100 rounded-lg min-h-[220px]">
            {chartData ? (
              localChartType === 'bar' ? (
                <Bar data={chartData} options={chartOptions} className="w-full h-48" />
              ) : localChartType === 'line' || localChartType === 'area' ? (
                <Line data={chartData} options={chartOptions} className="w-full h-48" />
              ) : localChartType === 'scatter' ? (
                <Scatter data={chartData} options={chartOptions} className="w-full h-48" />
              ) : null
            ) : (
              <div className="text-center">
                <BarChart3 className="h-12 w-12 text-gray-400 mx-auto mb-2" />
                <p className="text-base font-semibold text-gray-700">No Data</p>
                <p className="text-xs text-gray-500 mt-1">
                  {localMetrics.join(', ')} • {localTimeRange}
                </p>
              </div>
            )}
          </div>

          {/* Forecast accuracy if available */}
          {accuracyMetrics && (
            <div className="mt-3 text-xs text-black bg-gray-100 rounded px-2 py-1 inline-block">
              <span className="font-semibold">Forecast Accuracy:</span> {accuracyMetrics.mae}% MAE
            </div>
          )}
        </div>
      ) : (
        // Back of card - Settings
        <div className="graph-card-back p-4 bg-gray-900 text-white rounded-lg">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-bold text-white">Settings</h3>
            <button
              onClick={handleSettingsClick}
              className="p-1 text-gray-300 hover:text-white transition-colors"
              aria-label="Close Settings"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          <div className="space-y-4">
            {/* Chart Type */}
            <div>
              <label className="block text-sm font-semibold text-white mb-1">
                Chart Type
              </label>
              <select
                className="form-select w-full bg-gray-800 text-white border-gray-600 rounded"
                value={localChartType}
                onChange={e => setLocalChartType(e.target.value)}
              >
                <option value="line">Line Chart</option>
                <option value="area">Area Chart</option>
                <option value="bar">Bar Chart</option>
                <option value="scatter">Scatter Plot</option>
              </select>
            </div>

            {/* Metrics */}
            <div>
              <label className="block text-sm font-semibold text-white mb-1">
                Metrics
              </label>
              <div className="space-y-2">
                {['temperature', 'humidity', 'co2', 'aqi', 'pressure', 'light_level'].map((metric) => (
                  <label key={metric} className="flex items-center">
                    <input
                      type="checkbox"
                      checked={localMetrics.includes(metric)}
                      onChange={() => handleMetricChange(metric)}
                      className="mr-2 accent-blue-500"
                    />
                    <span className="text-sm capitalize text-white">{metric.replace('_', ' ')}</span>
                  </label>
                ))}
              </div>
            </div>

            {/* Time Range */}
            <div>
              <label className="block text-sm font-semibold text-white mb-1">
                Time Range
              </label>
              <select
                className="form-select w-full bg-gray-800 text-white border-gray-600 rounded"
                value={localTimeRange}
                onChange={e => setLocalTimeRange(e.target.value)}
              >
                <option value="1h">Last Hour</option>
                <option value="6h">Last 6 Hours</option>
                <option value="24h">Last 24 Hours</option>
                <option value="7d">Last 7 Days</option>
                <option value="30d">Last 30 Days</option>
              </select>
            </div>

            {/* Actions */}
            <div className="flex space-x-2 pt-2">
              <button
                className="btn-primary flex-1 bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 rounded"
                onClick={handleApply}
              >
                Apply Changes
              </button>
              <button
                onClick={handleSettingsClick}
                className="btn-secondary flex-1 bg-gray-700 hover:bg-gray-600 text-white font-bold py-2 rounded"
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