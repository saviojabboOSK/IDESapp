// Enhanced graph builder modal with multi-sensor comparison, metric filtering per sensor, and improved scrolling UI.

import React, { useState, useCallback, useEffect } from 'react'
import { X, Wand2, Save, Activity, Plus, Minus } from 'lucide-react'

interface SensorInfo {
  id: string
  mac_address: string
  nickname?: string
  location?: string
  available_metrics: string[]
}

interface SensorSelection {
  sensor_id: string
  metrics: string[]
}

interface GraphConfig {
  title: string
  chart_type: string
  sensor_id?: string
  sensors?: SensorSelection[] // Support multiple sensors
  metrics: string[]
  time_range: string
  custom_start_time?: string
  custom_end_time?: string
  settings: {
    color_scheme: string[]
    show_legend: boolean
    show_grid: boolean
    animate?: boolean
    smooth_lines?: boolean
    fill_area?: boolean
    show_points?: boolean
  }
  layout: {
    x: number
    y: number
    width: number
    height: number
  }
}

interface GraphBuilderModalEnhancedProps {
  isOpen: boolean
  onSave: (config: GraphConfig) => void
  onClose: () => void
  onAIGenerate?: (prompt: string) => void
}

const CHART_TYPES = [
  { value: 'line', label: 'Line Chart', icon: '📈', desc: 'Best for trends over time' },
  { value: 'area', label: 'Area Chart', icon: '📊', desc: 'Filled areas show volume' },
  { value: 'bar', label: 'Bar Chart', icon: '📊', desc: 'Compare values at points in time' },
  { value: 'scatter', label: 'Scatter Plot', icon: '⚪', desc: 'Show correlation between metrics' }
]

const TIME_RANGES = [
  { value: '1h', label: '1 Hour' },
  { value: '6h', label: '6 Hours' },
  { value: '12h', label: '12 Hours' },
  { value: '24h', label: '24 Hours' },
  { value: '7d', label: '7 Days' },
  { value: '30d', label: '30 Days' },
  { value: 'custom', label: 'Custom Range' }
]

const DEFAULT_COLOR_SCHEMES = [
  ['#3b82f6', '#ef4444', '#22c55e', '#f59e0b', '#8b5cf6', '#ec4899'],
  ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b'],
  ['#e11d48', '#0891b2', '#ca8a04', '#9333ea', '#c2410c', '#059669']
]

const METRIC_CONFIG: {[key: string]: {label: string, unit: string, color: string}} = {
  bvoc_equiv: { label: 'BVOC Equivalent', unit: 'ppb', color: '#3b82f6' },
  co2_equiv: { label: 'CO₂ Equivalent', unit: 'ppm', color: '#ef4444' },
  comp_farenheit: { label: 'Temperature', unit: '°F', color: '#22c55e' },
  comp_gas: { label: 'Gas Sensor', unit: 'value', color: '#f59e0b' },
  comp_humidity: { label: 'Humidity', unit: '%', color: '#8b5cf6' }
}

const AI_SUGGESTIONS = [
  "Show temperature and humidity from lab sensor A",
  "Compare CO2 levels between sensor A and B",
  "Monitor gas levels across all sensors",
  "Track humidity changes in sensor C today",
  "Visualize BVOC trends for the past week"
]

const GraphBuilderModalEnhanced: React.FC<GraphBuilderModalEnhancedProps> = ({
  isOpen,
  onSave,
  onClose,
  onAIGenerate
}) => {
  const [sensors, setSensors] = useState<SensorInfo[]>([])
  const [loading, setLoading] = useState(false)
  const [sensorSelections, setSensorSelections] = useState<SensorSelection[]>([{ sensor_id: '', metrics: [] }])
  const [config, setConfig] = useState<GraphConfig>({
    title: '',
    chart_type: 'line',
    sensors: [],
    metrics: [],
    time_range: '24h',
    settings: {
      color_scheme: DEFAULT_COLOR_SCHEMES[0],
      show_legend: true,
      show_grid: true,
      animate: true,
      smooth_lines: false,
      fill_area: false,
      show_points: false
    },
    layout: { x: 0, y: 0, width: 6, height: 4 }
  })
  const [aiPrompt, setAiPrompt] = useState('')

  const loadSensors = useCallback(async () => {
    setLoading(true)
    try {
      const response = await fetch('/api/sensors/')
      if (response.ok) {
        const sensorData = await response.json()
        setSensors(sensorData)
      }
    } catch (error) {
      console.error('Failed to load sensors:', error)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (isOpen) {
      loadSensors()
    }
  }, [isOpen, loadSensors])

  const addSensorSelection = () => {
    setSensorSelections([...sensorSelections, { sensor_id: '', metrics: [] }])
  }

  const removeSensorSelection = (index: number) => {
    if (sensorSelections.length > 1) {
      setSensorSelections(sensorSelections.filter((_, i) => i !== index))
    }
  }

  const updateSensorSelection = (index: number, sensor_id: string) => {
    const newSelections = [...sensorSelections]
    newSelections[index] = { sensor_id, metrics: [] }
    setSensorSelections(newSelections)
  }

  const updateSensorMetrics = (index: number, metrics: string[]) => {
    const newSelections = [...sensorSelections]
    newSelections[index].metrics = metrics
    setSensorSelections(newSelections)
  }

  const getSelectedSensor = (sensor_id: string) => {
    return sensors.find(s => s.id === sensor_id)
  }

  const generateTitle = () => {
    const validSelections = sensorSelections.filter(s => s.sensor_id && s.metrics.length > 0)
    if (validSelections.length === 0) return ''
    
    if (validSelections.length === 1) {
      const sensor = getSelectedSensor(validSelections[0].sensor_id)
      const sensorName = sensor?.nickname || sensor?.id || 'Sensor'
      const metricNames = validSelections[0].metrics.map(m => METRIC_CONFIG[m]?.label || m)
      return `${sensorName} - ${metricNames.join(', ')}`
    } else {
      const sensorNames = validSelections.map(s => {
        const sensor = getSelectedSensor(s.sensor_id)
        return sensor?.nickname || sensor?.id || 'Sensor'
      })
      return `Comparison: ${sensorNames.join(' vs ')}`
    }
  }

  const handleSave = () => {
    const validSelections = sensorSelections.filter(s => s.sensor_id && s.metrics.length > 0)
    if (validSelections.length === 0) return

    // Flatten all metrics for backward compatibility
    const allMetrics = validSelections.flatMap(s => s.metrics)
    
    const finalConfig: GraphConfig = {
      ...config,
      title: config.title || generateTitle(),
      sensors: validSelections,
      metrics: allMetrics,
      // Keep sensor_id for single sensor backward compatibility
      sensor_id: validSelections.length === 1 ? validSelections[0].sensor_id : undefined
    }

    onSave(finalConfig)
    onClose()
  }

  const isValid = sensorSelections.some(s => s.sensor_id && s.metrics.length > 0) && config.title.trim().length > 0

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-5xl w-full h-[90vh] flex flex-col">
        {/* Fixed Header */}
        <div className="flex items-center justify-between p-6 border-b flex-shrink-0">
          <div>
            <h2 className="text-xl font-semibold text-gray-900">Create New Graph</h2>
            <p className="text-sm text-gray-500 mt-1">Select sensors and configure visualization</p>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Scrollable Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
              <span className="ml-2 text-gray-600">Loading sensors...</span>
            </div>
          ) : (
            <div className="space-y-8">
              {/* AI Assistant Section */}
              <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg p-6 border border-blue-200">
                <div className="flex items-center mb-4">
                  <Wand2 className="h-5 w-5 text-blue-600 mr-2" />
                  <h3 className="text-lg font-medium text-gray-900">AI Graph Assistant</h3>
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                  {AI_SUGGESTIONS.map((suggestion, index) => (
                    <button
                      key={index}
                      onClick={() => setAiPrompt(suggestion)}
                      className="text-left p-3 bg-white rounded border hover:border-blue-300 hover:bg-blue-50 transition-colors text-sm"
                    >
                      {suggestion}
                    </button>
                  ))}
                </div>

                <div className="flex space-x-2">
                  <input
                    type="text"
                    placeholder="Describe the graph you want to create..."
                    value={aiPrompt}
                    onChange={(e) => setAiPrompt(e.target.value)}
                    className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                  <button
                    onClick={() => onAIGenerate?.(aiPrompt)}
                    disabled={!aiPrompt.trim()}
                    className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Generate
                  </button>
                </div>
              </div>

              {/* Sensor Selection Section */}
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-lg font-medium text-gray-900">Sensor Selection</h3>
                  <button
                    onClick={addSensorSelection}
                    className="flex items-center px-3 py-2 text-sm border border-gray-300 rounded-md hover:bg-gray-50"
                    disabled={sensorSelections.length >= 3}
                  >
                    <Plus className="h-4 w-4 mr-1" />
                    Add Sensor
                  </button>
                </div>

                {sensorSelections.map((selection, index) => (
                  <div key={index} className="border border-gray-200 rounded-lg p-4 space-y-4">
                    <div className="flex items-center justify-between">
                      <h4 className="font-medium text-gray-700">
                        Sensor {index + 1}
                        {index > 0 && (
                          <button
                            onClick={() => removeSensorSelection(index)}
                            className="ml-2 p-1 text-red-500 hover:text-red-700"
                          >
                            <Minus className="h-4 w-4" />
                          </button>
                        )}
                      </h4>
                    </div>

                    {/* Sensor Selection */}
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Choose Sensor
                      </label>
                      <select
                        value={selection.sensor_id}
                        onChange={(e) => updateSensorSelection(index, e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      >
                        <option value="">Select a sensor...</option>
                        {sensors.map((sensor) => (
                          <option key={sensor.id} value={sensor.id}>
                            {sensor.nickname || sensor.id} ({sensor.mac_address})
                          </option>
                        ))}
                      </select>
                    </div>

                    {/* Metrics Selection */}
                    {selection.sensor_id && (
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          Available Metrics
                        </label>
                        <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                          {getSelectedSensor(selection.sensor_id)?.available_metrics.map((metric) => {
                            const metricInfo = METRIC_CONFIG[metric] || { label: metric, unit: 'value', color: '#6b7280' }
                            const isSelected = selection.metrics.includes(metric)
                            
                            return (
                              <button
                                key={metric}
                                onClick={() => {
                                  const newMetrics = isSelected
                                    ? selection.metrics.filter(m => m !== metric)
                                    : [...selection.metrics, metric]
                                  updateSensorMetrics(index, newMetrics)
                                }}
                                className={`p-3 rounded-lg border text-left transition-colors ${
                                  isSelected
                                    ? 'border-blue-500 bg-blue-50 text-blue-900'
                                    : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                                }`}
                              >
                                <div className="flex items-center">
                                  <div
                                    className="w-3 h-3 rounded-full mr-2"
                                    style={{ backgroundColor: metricInfo.color }}
                                  />
                                  <Activity className="h-4 w-4 mr-2 text-gray-500" />
                                </div>
                                <div className="mt-1">
                                  <div className="font-medium text-sm">{metricInfo.label}</div>
                                  <div className="text-xs text-gray-500">{metricInfo.unit}</div>
                                </div>
                              </button>
                            )
                          })}
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>

              {/* Graph Configuration */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Basic Settings */}
                <div className="space-y-4">
                  <h3 className="text-lg font-medium text-gray-900">Graph Settings</h3>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Graph Title
                    </label>
                    <input
                      type="text"
                      value={config.title}
                      onChange={(e) => setConfig({ ...config, title: e.target.value })}
                      placeholder={generateTitle() || "Enter graph title..."}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Chart Type
                    </label>
                    <div className="grid grid-cols-2 gap-2">
                      {CHART_TYPES.map((type) => (
                        <button
                          key={type.value}
                          onClick={() => setConfig({ ...config, chart_type: type.value })}
                          className={`p-3 rounded-lg border text-left transition-colors ${
                            config.chart_type === type.value
                              ? 'border-blue-500 bg-blue-50'
                              : 'border-gray-200 hover:border-gray-300'
                          }`}
                        >
                          <div className="text-lg mb-1">{type.icon}</div>
                          <div className="font-medium text-sm">{type.label}</div>
                          <div className="text-xs text-gray-500">{type.desc}</div>
                        </button>
                      ))}
                    </div>
                  </div>
                </div>

                {/* Time Range */}
                <div className="space-y-4">
                  <h3 className="text-lg font-medium text-gray-900">Time Range</h3>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Time Period
                    </label>
                    <select
                      value={config.time_range}
                      onChange={(e) => setConfig({ ...config, time_range: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    >
                      {TIME_RANGES.map((range) => (
                        <option key={range.value} value={range.value}>
                          {range.label}
                        </option>
                      ))}
                    </select>
                  </div>

                  {config.time_range === 'custom' && (
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Start Time
                        </label>
                        <input
                          type="datetime-local"
                          value={config.custom_start_time || ''}
                          onChange={(e) => setConfig({ ...config, custom_start_time: e.target.value })}
                          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          End Time
                        </label>
                        <input
                          type="datetime-local"
                          value={config.custom_end_time || ''}
                          onChange={(e) => setConfig({ ...config, custom_end_time: e.target.value })}
                          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
                        />
                      </div>
                    </div>
                  )}

                  {/* Display Options */}
                  <div className="space-y-3">
                    <h4 className="font-medium text-gray-700">Display Options</h4>
                    <div className="space-y-2">
                      <label className="flex items-center">
                        <input
                          type="checkbox"
                          checked={config.settings.show_legend}
                          onChange={(e) => setConfig({
                            ...config,
                            settings: { ...config.settings, show_legend: e.target.checked }
                          })}
                          className="rounded border-gray-300 text-blue-600 focus:border-blue-300 focus:ring focus:ring-offset-0 focus:ring-blue-200 focus:ring-opacity-50"
                        />
                        <span className="ml-2 text-sm text-gray-700">Show legend</span>
                      </label>
                      <label className="flex items-center">
                        <input
                          type="checkbox"
                          checked={config.settings.show_grid}
                          onChange={(e) => setConfig({
                            ...config,
                            settings: { ...config.settings, show_grid: e.target.checked }
                          })}
                          className="rounded border-gray-300 text-blue-600 focus:border-blue-300 focus:ring focus:ring-offset-0 focus:ring-blue-200 focus:ring-opacity-50"
                        />
                        <span className="ml-2 text-sm text-gray-700">Show grid</span>
                      </label>
                      <label className="flex items-center">
                        <input
                          type="checkbox"
                          checked={config.settings.animate}
                          onChange={(e) => setConfig({
                            ...config,
                            settings: { ...config.settings, animate: e.target.checked }
                          })}
                          className="rounded border-gray-300 text-blue-600 focus:border-blue-300 focus:ring focus:ring-offset-0 focus:ring-blue-200 focus:ring-opacity-50"
                        />
                        <span className="ml-2 text-sm text-gray-700">Animate transitions</span>
                      </label>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Fixed Footer */}
        <div className="border-t bg-gray-50 px-6 py-4 flex justify-between items-center flex-shrink-0">
          <div className="text-sm text-gray-500">
            {sensorSelections.filter(s => s.sensor_id && s.metrics.length > 0).length} sensor(s) selected
          </div>
          <div className="flex space-x-3">
            <button
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={!isValid}
              className="flex items-center px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Save className="h-4 w-4 mr-2" />
              Create Graph
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default GraphBuilderModalEnhanced
