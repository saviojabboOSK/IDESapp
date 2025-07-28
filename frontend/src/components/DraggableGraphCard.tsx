// Enhanced draggable graph card component for IDES 2.0 with integrated settings panel, real-time data updates, and drag-and-drop functionality using react-grid-layout.
import React from 'react'
import { Line, Bar, Scatter } from 'react-chartjs-2'
import { 
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  Filler,
  ArcElement
} from 'chart.js'
import { X, BarChart3, Settings, Trash2, Expand, RefreshCw, GripVertical } from 'lucide-react'

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
  sensor_id?: string
  sensors?: Array<{
    sensor_id: string
    metrics: string[]
  }>
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
  data: { [metric: string]: (number | null)[] }
  sensor_metadata?: { [sensorId: string]: { nickname: string } }
}

interface DraggableGraphCardProps {
  config: GraphConfig
  onEdit: () => void
  onDelete: (id: string) => void
  data?: GraphData
  isLoading?: boolean
}

const AVAILABLE_METRICS: { [key: string]: string } = {
  'bvoc_equiv': 'BVOC Equivalent',
  'co2_equiv': 'CO₂ Equivalent', 
  'comp_farenheit': 'Temperature',
  'comp_gas': 'Gas Sensor',
  'comp_humidity': 'Humidity',
  'temperature': 'Temperature',
  'humidity': 'Humidity',
  'co2': 'CO₂',
  'aqi': 'Air Quality Index',
  'pressure': 'Pressure',
  'light_level': 'Light Level'
}

// Color generator for metrics 
const getMetricColor = (index: number): string => {
  const colors = [
    'rgb(99, 102, 241)',   // Indigo
    'rgb(239, 68, 68)',    // Red
    'rgb(34, 197, 94)',    // Green
    'rgb(245, 158, 11)',   // Yellow
    'rgb(168, 85, 247)',   // Purple
    'rgb(6, 182, 212)',    // Cyan
    'rgb(251, 113, 133)',  // Pink
    'rgb(132, 204, 22)',   // Lime
    'rgb(249, 115, 22)',   // Orange
    'rgb(139, 92, 246)',   // Violet
  ]
  return colors[index % colors.length]
}

const DraggableGraphCard: React.FC<DraggableGraphCardProps> = ({
  config,
  onEdit,
  onDelete,
  data,
  isLoading = false,
}) => {
  const handleDeleteClick = () => {
    if (window.confirm(`Are you sure you want to delete the graph "${config.title}"?`)) {
      onDelete(config.id)
    }
  }

  // Prepare chart data
  const chartData = React.useMemo(() => {
    console.log(`DEBUG: Preparing chart data for ${config.id}`, data)
    
    if (!data) {
      console.log(`DEBUG: No data object available for graph ${config.id}`)
      return null
    }

    if (!data.labels) {
      console.log(`DEBUG: No labels in data for graph ${config.id}`)
      return null
    }

    if (!data.data) {
      console.log(`DEBUG: No data.data in data for graph ${config.id}`)
      return null
    }

    // Use all available data keys
    const dataKeys = Object.keys(data.data)
    console.log(`DEBUG: Data keys for graph ${config.id}:`, dataKeys)
    
    if (dataKeys.length === 0) {
      console.log(`DEBUG: Empty dataKeys for graph ${config.id}`)
      return null
    }

    const datasets = dataKeys.map((key, index) => {
      const values = data.data[key] || []
      
      console.log(`DEBUG: Graph ${config.id} - Values for ${key}:`, 
        values.length > 0 
          ? `${values.filter(v => v !== null).length} non-null out of ${values.length} values` 
          : 'EMPTY ARRAY');
      
      // Enhanced label generation for multi-sensor support
      let label = key
      
      // Check if this is multi-sensor data format (sensor_001_comp_farenheit)
      if (key.includes('_') && key.startsWith('sensor_')) {
        const parts = key.split('_')
        if (parts.length >= 3) {
          const sensorId = `${parts[0]}_${parts[1]}` // sensor_001
          const metric = parts.slice(2).join('_') // comp_farenheit
          // Use sensor metadata if available, otherwise format nicely
          if (data.sensor_metadata && data.sensor_metadata[sensorId]) {
            const sensorName = data.sensor_metadata[sensorId].nickname
            label = `${sensorName}, ${AVAILABLE_METRICS[metric] || metric}`
          } else {
            label = `${sensorId} ${AVAILABLE_METRICS[metric] || metric}`
          }
        }
      } else {
        // Single sensor format - just use the metric name
        label = AVAILABLE_METRICS[key] || key
      }
      
      console.log(`DEBUG: Graph ${config.id} - Dataset ${index} label:`, label);

      return {
        label,
        data: values, // Simple array format for Chart.js
        borderColor: getMetricColor(index),
        backgroundColor: getMetricColor(index).replace('rgb', 'rgba').replace(')', ', 0.1)'),
        tension: 0.1,
        pointRadius: 2,
        pointHoverRadius: 5,
      }
    })

    return {
      labels: data.labels,
      datasets,
    }
  }, [data])

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
    console.log(`DEBUG: Rendering chart for ${config.id}`, { 
      hasChartData: !!chartData,
      hasData: !!data,
      dataLabels: data?.labels?.length,
      dataKeys: data?.data ? Object.keys(data.data) : [],
      metrics: config.metrics
    })
    
    // Check if we have any valid data points (not just empty arrays)
    const hasValidData = data && data.data && Object.values(data.data).some(arr => arr && arr.length > 0 && arr.some(val => val !== null));
    
    if (!chartData || !hasValidData) {
      console.log(`DEBUG: No valid chart data available for ${config.id}, showing empty state`)
      
      // Let's create a test button to fetch data directly
      const handleFetchTestData = async () => {
        try {
          console.log(`Manually fetching data for graph ${config.id}...`);
          const response = await fetch(`/api/graphs/${config.id}/data?limit=30`);
          const result = await response.json();
          console.log('Manual fetch result:', result);
        } catch (err) {
          console.error('Error in manual fetch:', err);
        }
      };
      
      return (
        <div className="flex flex-col items-center justify-center h-full text-gray-500">
          <div className="h-12 w-12 mb-2">📊</div>
          <p className="font-medium">
            {isLoading ? 'Loading Data...' : 'No Data Available'}
          </p>
          <p className="text-sm text-center">
            {config.metrics.join(', ')} • {config.time_range}
          </p>
          <p className="text-xs text-gray-400 mt-2">
            Graph ID: {config.id.substring(0, 8)}...
          </p>
          <button 
            onClick={handleFetchTestData}
            className="mt-2 text-xs px-3 py-1 bg-blue-100 text-blue-800 rounded hover:bg-blue-200"
          >
            Debug: Test API
          </button>
        </div>
      )
    }

    // Select the appropriate chart component based on chart type
    let ChartComponent;
    if (config.chart_type === 'bar') {
      ChartComponent = Bar;
    } else if (config.chart_type === 'scatter') {
      ChartComponent = Scatter;
    } else {
      ChartComponent = Line;
    }

    console.log(`DEBUG: Rendering ${config.chart_type} chart with data:`, chartData);

    return (
      <div className="h-full w-full">
        <ChartComponent
          key={`${config.layout.width}-${config.layout.height}`}
          data={chartData}
          options={chartOptions}
        />
      </div>
    )
  }

  return (
    <div className="graph-card bg-white rounded-lg shadow-md border border-gray-200 relative h-full flex flex-col">
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
                onEdit();
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
        <div className="flex-1 min-h-0 w-full">{renderChart()}</div>
        {/* Footer Info */}
        <div className="mt-2 text-xs text-gray-500 flex items-center justify-between">
          <span>
            {config.metrics.length} metric{config.metrics.length !== 1 ? 's' : ''}
          </span>
          <span>{config.time_range}</span>
        </div>
      </div>
    </div>
  )
}

export default DraggableGraphCard