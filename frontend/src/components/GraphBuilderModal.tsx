// Enhanced graph builder modal for creating new graphs with comprehensive configuration options and AI assistance integration.

import React, { useState, useCallback } from 'react'
import { X, Wand2, Save } from 'lucide-react'

interface GraphConfig {
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
  }
  layout: {
    x: number
    y: number
    width: number
    height: number
  }
}

interface GraphBuilderModalProps {
  isOpen: boolean
  onSave: (config: GraphConfig) => void
  onClose: () => void
  onAIGenerate?: (prompt: string) => void
}

const AVAILABLE_METRICS = [
  { id: 'temperature', label: 'Temperature', unit: '°C', color: '#ef4444' },
  { id: 'humidity', label: 'Humidity', unit: '%', color: '#3b82f6' },
  { id: 'co2', label: 'CO₂', unit: 'ppm', color: '#22c55e' },
  { id: 'aqi', label: 'Air Quality', unit: 'AQI', color: '#f59e0b' },
  { id: 'pressure', label: 'Pressure', unit: 'hPa', color: '#8b5cf6' },
  { id: 'light_level', label: 'Light Level', unit: 'lux', color: '#eab308' }
]

const CHART_TYPES = [
  { value: 'line', label: 'Line Chart', icon: '📈', desc: 'Best for trends over time' },
  { value: 'area', label: 'Area Chart', icon: '📊', desc: 'Filled areas show volume' },
  { value: 'bar', label: 'Bar Chart', icon: '📊', desc: 'Compare values at points in time' },
  { value: 'scatter', label: 'Scatter Plot', icon: '⚪', desc: 'Show correlation between metrics' }
]

const TIME_RANGES = [
  { value: '1h', label: 'Last Hour' },
  { value: '6h', label: 'Last 6 Hours' },
  { value: '12h', label: 'Last 12 Hours' },
  { value: '24h', label: 'Last 24 Hours' },
  { value: '7d', label: 'Last 7 Days' },
  { value: '30d', label: 'Last 30 Days' }
]

const DEFAULT_COLOR_SCHEMES = [
  ['#3b82f6', '#ef4444', '#22c55e', '#f59e0b', '#8b5cf6', '#ec4899'],
  ['#ef4444', '#3b82f6', '#22c55e', '#f59e0b', '#8b5cf6', '#eab308'], // Sensor colors
  ['#1f2937', '#374151', '#6b7280', '#9ca3af'], // Monochrome
  ['#065f46', '#047857', '#059669', '#10b981'], // Green tones
]

const AI_SUGGESTIONS = [
  "Show temperature and humidity trends",
  "Monitor air quality over time",
  "Compare all environmental metrics",
  "Track pressure changes today",
  "Visualize light levels for the week"
]

const GraphBuilderModal: React.FC<GraphBuilderModalProps> = ({
  isOpen,
  onSave,
  onClose,
  onAIGenerate
}) => {
  const [config, setConfig] = useState<GraphConfig>({
    title: '',
    chart_type: 'line',
    metrics: [],
    time_range: '24h',
    settings: {
      color_scheme: DEFAULT_COLOR_SCHEMES[0],
      show_legend: true,
      show_grid: true,
      animate: true,
      smooth_lines: true,
      fill_area: false,
      show_points: false
    },
    layout: {
      x: 0,
      y: 0,
      width: 6,
      height: 4
    }
  })

  const [aiPrompt, setAiPrompt] = useState('')
  const [showAISection, setShowAISection] = useState(false)

  const updateConfig = useCallback((field: string, value: any) => {
    setConfig(prev => {
      const keys = field.split('.')
      const newConfig = JSON.parse(JSON.stringify(prev))
      let current = newConfig
      
      for (let i = 0; i < keys.length - 1; i++) {
        current = current[keys[i]]
      }
      
      current[keys[keys.length - 1]] = value
      return newConfig
    })
  }, [])

  const handleMetricToggle = useCallback((metricId: string) => {
    const newMetrics = config.metrics.includes(metricId)
      ? config.metrics.filter(m => m !== metricId)
      : [...config.metrics, metricId]
    updateConfig('metrics', newMetrics)
    
    // Auto-generate title if empty
    if (!config.title && newMetrics.length > 0) {
      const metricLabels = newMetrics.map(id => 
        AVAILABLE_METRICS.find(m => m.id === id)?.label || id
      )
      updateConfig('title', metricLabels.join(' & '))
    }
  }, [config.metrics, config.title, updateConfig])

  const handleSave = useCallback(() => {
    if (config.metrics.length === 0) return
    onSave(config)
    
    // Reset form
    setConfig({
      title: '',
      chart_type: 'line',
      metrics: [],
      time_range: '24h',
      settings: {
        color_scheme: DEFAULT_COLOR_SCHEMES[0],
        show_legend: true,
        show_grid: true,
        animate: true,
        smooth_lines: true,
        fill_area: false,
        show_points: false
      },
      layout: {
        x: 0,
        y: 0,
        width: 6,
        height: 4
      }
    })
  }, [config, onSave])

  const handleAIGenerate = useCallback(() => {
    if (onAIGenerate && aiPrompt.trim()) {
      onAIGenerate(aiPrompt.trim())
      setAiPrompt('')
      setShowAISection(false)
    }
  }, [onAIGenerate, aiPrompt])

  const isValid = config.metrics.length > 0 && config.title.trim().length > 0

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-3xl w-full max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b">
          <div>
            <h2 className="text-xl font-semibold text-gray-900">Create New Graph</h2>
            <p className="text-sm text-gray-500 mt-1">Configure a new sensor data visualization</p>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto max-h-[calc(90vh-140px)]">
          {/* AI Assistant Section */}
          {onAIGenerate && (
            <div className="mb-6 p-4 bg-gradient-to-r from-purple-50 to-blue-50 border border-purple-200 rounded-lg">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center">
                  <Wand2 className="h-5 w-5 text-purple-600 mr-2" />
                  <h3 className="text-lg font-medium text-gray-900">AI Assistant</h3>
                </div>
                <button
                  onClick={() => setShowAISection(!showAISection)}
                  className="text-sm text-purple-600 hover:text-purple-800"
                >
                  {showAISection ? 'Hide' : 'Show'}
                </button>
              </div>
              
              {showAISection && (
                <div className="space-y-3">
                  <div>
                    <textarea
                      value={aiPrompt}
                      onChange={(e) => setAiPrompt(e.target.value)}
                      placeholder="Describe the chart you want to create..."
                      className="form-textarea w-full h-20 resize-none"
                    />
                  </div>
                  
                  <div className="flex flex-wrap gap-2">
                    {AI_SUGGESTIONS.map((suggestion, idx) => (
                      <button
                        key={idx}
                        onClick={() => setAiPrompt(suggestion)}
                        className="px-3 py-1 text-xs bg-white border border-purple-200 rounded-full hover:bg-purple-50 text-purple-700"
                      >
                        {suggestion}
                      </button>
                    ))}
                  </div>
                  
                  <button
                    onClick={handleAIGenerate}
                    disabled={!aiPrompt.trim()}
                    className="btn-primary w-full flex items-center justify-center"
                  >
                    <Wand2 className="h-4 w-4 mr-2" />
                    Generate with AI
                  </button>
                </div>
              )}
            </div>
          )}

          <div className="space-y-6">
            {/* Basic Information */}
            <div>
              <h3 className="text-lg font-medium text-gray-900 mb-4">Basic Information</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Graph Title *
                  </label>
                  <input
                    type="text"
                    value={config.title}
                    onChange={(e) => updateConfig('title', e.target.value)}
                    className="form-input w-full"
                    placeholder="Enter descriptive title"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Time Range
                  </label>
                  <select
                    value={config.time_range}
                    onChange={(e) => updateConfig('time_range', e.target.value)}
                    className="form-select w-full"
                  >
                    {TIME_RANGES.map(range => (
                      <option key={range.value} value={range.value}>
                        {range.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            </div>

            {/* Chart Type */}
            <div>
              <h3 className="text-lg font-medium text-gray-900 mb-4">Chart Type</h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {CHART_TYPES.map(type => (
                  <button
                    key={type.value}
                    onClick={() => updateConfig('chart_type', type.value)}
                    className={`p-4 border rounded-lg text-center transition-colors ${
                      config.chart_type === type.value
                        ? 'border-blue-500 bg-blue-50 text-blue-700'
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    <div className="text-2xl mb-2">{type.icon}</div>
                    <div className="font-medium text-sm">{type.label}</div>
                    <div className="text-xs text-gray-500 mt-1">{type.desc}</div>
                  </button>
                ))}
              </div>
            </div>

            {/* Metrics Selection */}
            <div>
              <h3 className="text-lg font-medium text-gray-900 mb-4">
                Select Metrics * 
                <span className="text-sm font-normal text-gray-500">
                  ({config.metrics.length} selected)
                </span>
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {AVAILABLE_METRICS.map(metric => (
                  <label
                    key={metric.id}
                    className={`flex items-center p-4 border rounded-lg cursor-pointer transition-colors ${
                      config.metrics.includes(metric.id)
                        ? 'border-blue-500 bg-blue-50'
                        : 'border-gray-200 hover:bg-gray-50'
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={config.metrics.includes(metric.id)}
                      onChange={() => handleMetricToggle(metric.id)}
                      className="mr-3 text-blue-600"
                    />
                    <div
                      className="w-4 h-4 rounded-full mr-3"
                      style={{ backgroundColor: metric.color }}
                    />
                    <div>
                      <span className="font-medium text-gray-900">{metric.label}</span>
                      <span className="text-sm text-gray-500 ml-2">({metric.unit})</span>
                    </div>
                  </label>
                ))}
              </div>
            </div>

            {/* Color Scheme */}
            <div>
              <h3 className="text-lg font-medium text-gray-900 mb-4">Color Scheme</h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {DEFAULT_COLOR_SCHEMES.map((scheme, idx) => (
                  <button
                    key={idx}
                    onClick={() => updateConfig('settings.color_scheme', scheme)}
                    className={`p-3 border rounded-lg transition-colors ${
                      JSON.stringify(config.settings.color_scheme) === JSON.stringify(scheme)
                        ? 'border-blue-500 bg-blue-50'
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    <div className="flex justify-center space-x-1">
                      {scheme.slice(0, 4).map((color, colorIdx) => (
                        <div
                          key={colorIdx}
                          className="w-6 h-6 rounded-full"
                          style={{ backgroundColor: color }}
                        />
                      ))}
                    </div>
                  </button>
                ))}
              </div>
            </div>

            {/* Display Options */}
            <div>
              <h3 className="text-lg font-medium text-gray-900 mb-4">Display Options</h3>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                {[
                  { key: 'show_legend', label: 'Show Legend' },
                  { key: 'show_grid', label: 'Show Grid' },
                  { key: 'animate', label: 'Animations' },
                  { key: 'smooth_lines', label: 'Smooth Lines' },
                  { key: 'fill_area', label: 'Fill Area' },
                  { key: 'show_points', label: 'Show Points' }
                ].map(option => (
                  <label key={option.key} className="flex items-center">
                    <input
                      type="checkbox"
                      checked={config.settings[option.key as keyof typeof config.settings] as boolean}
                      onChange={(e) => updateConfig(`settings.${option.key}`, e.target.checked)}
                      className="mr-2 text-blue-600"
                    />
                    <span className="text-sm text-gray-700">{option.label}</span>
                  </label>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between p-6 border-t bg-gray-50">
          <div className="text-sm text-gray-500">
            {config.metrics.length === 0 && "Select at least one metric to continue"}
            {config.title.trim().length === 0 && config.metrics.length > 0 && "Enter a title for your graph"}
          </div>
          
          <div className="flex space-x-3">
            <button onClick={onClose} className="btn-secondary">
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={!isValid}
              className="btn-primary flex items-center"
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

export default GraphBuilderModal
