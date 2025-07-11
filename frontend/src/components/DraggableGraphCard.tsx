// Enhanced draggable graph card component for IDES 2.0 with integrated settings panel, real-time data updates, and drag-and-drop functionality using react-grid-layout.
import React, { useState, useCallback } from 'react'
import { Settings, X, BarChart3 } from 'lucide-react'
import { Bar, Line, Scatter } from 'react-chartjs-2'
import GraphSettingsModal from './GraphSettingsModal'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  ArcElement,
  Filler,
} from 'chart.js'
ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  ArcElement,
  Filler
)

interface GraphConfig {
  id: string
  title: string
  chart_type: string
  metrics: string[]
  time_range: string
  settings: {
    color_scheme: string[]
    show_legend: boolean
    show_grid: boolean
    animate?: boolean
    smooth_lines?: boolean
    fill_area?: boolean
    show_points?: boolean
    y_axis_min?: number
    y_axis_max?: number
  }
  layout: {
    x: number
    y: number
    width: number
    height: number
  }
  is_ai_generated?: boolean
  auto_refresh?: boolean
  refresh_interval?: number
}

interface GraphData {
  labels: string[]
  data: { [metric: string]: number[] }
}

interface DraggableGraphCardProps {
  config: GraphConfig
  onUpdate: (id: string, updates: Partial<GraphConfig>) => void
  onDelete: (id: string) => void
  data?: GraphData
  isLoading?: boolean
}

const AVAILABLE_METRICS = [
  { id: 'temperature', label: 'Temperature', unit: '°C' },
  { id: 'humidity', label: 'Humidity', unit: '%' },
  { id: 'co2', label: 'CO₂', unit: 'ppm' },
  { id: 'aqi', label: 'Air Quality', unit: 'AQI' },
  { id: 'pressure', label: 'Pressure', unit: 'hPa' },
  { id: 'light_level', label: 'Light Level', unit: 'lux' },
]

const DraggableGraphCard: React.FC<DraggableGraphCardProps> = ({
  config,
  onUpdate,
  onDelete,
  data,
  isLoading = false,
}) => {
  const [showSettingsModal, setShowSettingsModal] = useState(false)

  const handleSaveSettings = useCallback(
    (updates: Partial<GraphConfig>) => {
      onUpdate(config.id, updates)
      setShowSettingsModal(false)
    },
    [config.id, onUpdate],
  )

  const handleDeleteClick = () => {
    if (window.confirm(`Are you sure you want to delete the graph "${config.title}"?`)) {
      onDelete(config.id)
    }
  }

  // Prepare chart data
  const chartData = React.useMemo(() => {
    if (!data || !config.metrics.length) {
      return null
    }
    const labels = data.labels || []
    const datasets = config.metrics.map((metric: string, idx: number) => ({
      label: AVAILABLE_METRICS.find(m => m.id === metric)?.label || metric,
      data: data.data?.[metric] || [],
      borderColor: config.settings.color_scheme[idx % config.settings.color_scheme.length],
      backgroundColor: config.settings.color_scheme[idx % config.settings.color_scheme.length] + '20',
      fill: config.chart_type === 'area' || config.settings.fill_area,
      tension: config.settings.smooth_lines ? 0.4 : 0,
      pointRadius: config.settings.show_points ? 3 : 0,
      pointHoverRadius: 5,
    }))
    return { labels, datasets }
  }, [data, config])

  const chartOptions = React.useMemo(
    () => ({
      responsive: true,
      maintainAspectRatio: false,
      animation: {
        duration: config.settings.animate ? 750 : 0,
      },
      plugins: {
        legend: {
          display: config.settings.show_legend,
          labels: { color: '#374151' },
        },
        title: { display: false },
      },
      scales: {
        x: {
          grid: { display: config.settings.show_grid },
          ticks: { color: '#6b7280' },
        },
        y: {
          grid: { display: config.settings.show_grid },
          ticks: { color: '#6b7280' },
          min: config.settings.y_axis_min,
          max: config.settings.y_axis_max,
        },
      },
    }),
    [config.settings]
  )

  const renderChart = () => {
    if (!chartData) {
      return (
        <div className="flex flex-col items-center justify-center h-full text-gray-500">
          <BarChart3 className="h-12 w-12 mb-2" />
          <p className="font-medium">No Data Available</p>
          <p className="text-sm text-center">
            {config.metrics.join(', ')} • {config.time_range}
          </p>
        </div>
      )
    }
    const ChartComponent =
      config.chart_type === 'bar'
        ? Bar
        : config.chart_type === 'scatter'
        ? Scatter
        : Line
    return (
      <div className="h-full">
        <ChartComponent data={chartData} options={chartOptions} />
      </div>
    )
  }

  return (
    <div className="graph-card bg-white rounded-lg shadow-md border border-gray-200 relative overflow-hidden h-full flex flex-col">
      {/* Main Card Content */}
      <div className="p-4 flex-1 flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between mb-3">
          <div className="drag-handle flex items-center space-x-2 cursor-move flex-1 min-w-0">
            <h3 className="text-lg font-semibold text-gray-900 truncate" title={config.title}>
              {config.title}
            </h3>
            {config.is_ai_generated && (
              <span className="px-2 py-1 text-xs bg-purple-100 text-purple-800 rounded-full flex-shrink-0">
                AI
              </span>
            )}
            {isLoading && (
              <div className="animate-spin rounded-full h-4 w-4 border-2 border-blue-600 border-t-transparent flex-shrink-0"></div>
            )}
          </div>

          <div className="flex items-center space-x-1 flex-shrink-0 ml-2">
            <button
              onClick={(e) => {
                e.stopPropagation();
                setShowSettingsModal(true);
              }}
              className="p-1.5 text-gray-500 hover:text-blue-600 hover:bg-blue-50 rounded-md transition-colors"
              title="Settings"
            >
              <Settings className="h-4 w-4" />
            </button>
            <button
              onClick={(e) => {
                e.stopPropagation();
                handleDeleteClick();
              }}
              className="p-1.5 text-gray-500 hover:text-red-600 hover:bg-red-50 rounded-md transition-colors"
              title="Delete"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>
        {/* Chart Area */}
        <div className="flex-1 min-h-0">{renderChart()}</div>
        {/* Footer Info */}
        <div className="mt-2 text-xs text-gray-500 flex items-center justify-between">
          <span>
            {config.metrics.length} metric{config.metrics.length !== 1 ? 's' : ''}
          </span>
          <span>{config.time_range}</span>
        </div>
      </div>
      {/* Settings Modal */}
      {showSettingsModal && (
        <GraphSettingsModal
          config={config}
          isOpen={showSettingsModal}
          onSave={handleSaveSettings}
          onClose={() => setShowSettingsModal(false)}
        />
      )}
    </div>
  )
}

export default DraggableGraphCard