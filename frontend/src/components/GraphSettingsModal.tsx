// Enhanced settings modal for graph configuration with comprehensive options for chart customization, metrics selection, and visual styling.

import React, { useState, useEffect, useCallback } from 'react'
import { X, Palette, BarChart3, Settings2, Save, RotateCcw } from 'lucide-react'

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

interface GraphSettingsModalProps {
  config: GraphConfig
  isOpen: boolean
  onSave: (updates: Partial<GraphConfig>) => void
  onClose: () => void
  onReset?: () => void
}

const AVAILABLE_METRICS = [
  { id: 'temperature', label: 'Temperature', unit: '°C', color: '#ef4444' },
  { id: 'humidity', label: 'Humidity', unit: '%', color: '#3b82f6' },
  { id: 'co2', label: 'CO₂', unit: 'ppm', color: '#22c55e' },
  { id: 'aqi', label: 'Air Quality', unit: 'AQI', color: '#f59e0b' },
  { id: 'pressure', label: 'Pressure', unit: 'hPa', color: '#8b5cf6' },
  { id: 'light_level', label: 'Light Level', unit: 'lux', color: '#eab308' }
]

const COLOR_SCHEMES = [
  { name: 'Default', colors: ['#3b82f6', '#ef4444', '#22c55e', '#f59e0b', '#8b5cf6', '#ec4899'] },
  { name: 'Monochrome', colors: ['#1f2937', '#374151', '#6b7280', '#9ca3af', '#d1d5db', '#f3f4f6'] },
  { name: 'Green Tones', colors: ['#065f46', '#047857', '#059669', '#10b981', '#34d399', '#6ee7b7'] },
  { name: 'Warm', colors: ['#7c2d12', '#ea580c', '#f97316', '#fb923c', '#fed7aa', '#ffedd5'] },
  { name: 'Purple', colors: ['#581c87', '#7c3aed', '#8b5cf6', '#a78bfa', '#c4b5fd', '#ddd6fe'] },
  { name: 'Sensor Colors', colors: ['#ef4444', '#3b82f6', '#22c55e', '#f59e0b', '#8b5cf6', '#eab308'] }
]

const TIME_RANGES = [
  { value: '1h', label: 'Last Hour' },
  { value: '6h', label: 'Last 6 Hours' },
  { value: '12h', label: 'Last 12 Hours' },
  { value: '24h', label: 'Last 24 Hours' },
  { value: '7d', label: 'Last 7 Days' },
  { value: '30d', label: 'Last 30 Days' }
]

const CHART_TYPES = [
  { value: 'line', label: 'Line Chart', icon: '📈' },
  { value: 'area', label: 'Area Chart', icon: '📊' },
  { value: 'bar', label: 'Bar Chart', icon: '📊' },
  { value: 'scatter', label: 'Scatter Plot', icon: '⚪' }
]

const GraphSettingsModal: React.FC<GraphSettingsModalProps> = ({
  config,
  isOpen,
  onSave,
  onClose,
  onReset
}) => {
  const [localConfig, setLocalConfig] = useState<GraphConfig>(config)
  const [activeTab, setActiveTab] = useState<'basic' | 'appearance' | 'advanced'>('basic')
  const [hasChanges, setHasChanges] = useState(false)

  useEffect(() => {
    setLocalConfig(config)
    setHasChanges(false)
  }, [config, isOpen])

  const updateConfig = useCallback((field: string, value: any) => {
    setLocalConfig(prev => {
      const keys = field.split('.')
      const newConfig = JSON.parse(JSON.stringify(prev)) // Deep clone
      let current = newConfig
      
      for (let i = 0; i < keys.length - 1; i++) {
        current = current[keys[i]]
      }
      
      current[keys[keys.length - 1]] = value
      return newConfig
    })
    setHasChanges(true)
  }, [])

  const handleSave = useCallback(() => {
    onSave(localConfig)
    setHasChanges(false)
  }, [localConfig, onSave])

  const handleReset = useCallback(() => {
    if (onReset) {
      onReset()
    }
    setLocalConfig(config)
    setHasChanges(false)
  }, [config, onReset])

  const handleMetricToggle = useCallback((metricId: string) => {
    const newMetrics = localConfig.metrics.includes(metricId)
      ? localConfig.metrics.filter(m => m !== metricId)
      : [...localConfig.metrics, metricId]
    updateConfig('metrics', newMetrics)
  }, [localConfig.metrics, updateConfig])

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b">
          <div>
            <h2 className="text-xl font-semibold text-gray-900">Graph Settings</h2>
            <p className="text-sm text-gray-500 mt-1">Configure {config.title}</p>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b">
          {[
            { key: 'basic', label: 'Basic', icon: BarChart3 },
            { key: 'appearance', label: 'Appearance', icon: Palette },
            { key: 'advanced', label: 'Advanced', icon: Settings2 }
          ].map(tab => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key as any)}
              className={`flex items-center px-6 py-3 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab.key
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              <tab.icon className="h-4 w-4 mr-2" />
              {tab.label}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto max-h-[calc(90vh-200px)]">
          {/* Basic Tab */}
          {activeTab === 'basic' && (
            <div className="space-y-6">
              {/* Title and Type */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Graph Title
                  </label>
                  <input
                    type="text"
                    value={localConfig.title}
                    onChange={(e) => updateConfig('title', e.target.value)}
                    className="form-input w-full"
                    placeholder="Enter graph title"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Chart Type
                  </label>
                  <select
                    value={localConfig.chart_type}
                    onChange={(e) => updateConfig('chart_type', e.target.value)}
                    className="form-select w-full"
                  >
                    {CHART_TYPES.map(type => (
                      <option key={type.value} value={type.value}>
                        {type.icon} {type.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Time Range */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Time Range
                </label>
                <div className="grid grid-cols-3 md:grid-cols-6 gap-2">
                  {TIME_RANGES.map(range => (
                    <button
                      key={range.value}
                      onClick={() => updateConfig('time_range', range.value)}
                      className={`p-2 text-sm rounded-md border transition-colors ${
                        localConfig.time_range === range.value
                          ? 'border-blue-500 bg-blue-50 text-blue-700'
                          : 'border-gray-200 hover:border-gray-300 text-gray-700'
                      }`}
                    >
                      {range.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Metrics Selection */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-3">
                  Metrics to Display
                </label>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {AVAILABLE_METRICS.map(metric => (
                    <label
                      key={metric.id}
                      className="flex items-center p-3 border rounded-lg hover:bg-gray-50 cursor-pointer"
                    >
                      <input
                        type="checkbox"
                        checked={localConfig.metrics.includes(metric.id)}
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
            </div>
          )}

          {/* Appearance Tab */}
          {activeTab === 'appearance' && (
            <div className="space-y-6">
              {/* Color Scheme */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-3">
                  Color Scheme
                </label>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                  {COLOR_SCHEMES.map((scheme, idx) => (
                    <button
                      key={idx}
                      onClick={() => updateConfig('settings.color_scheme', scheme.colors)}
                      className={`p-3 border rounded-lg transition-colors ${
                        JSON.stringify(localConfig.settings.color_scheme) === JSON.stringify(scheme.colors)
                          ? 'border-blue-500 bg-blue-50'
                          : 'border-gray-200 hover:border-gray-300'
                      }`}
                    >
                      <div className="flex justify-center space-x-1 mb-2">
                        {scheme.colors.slice(0, 6).map((color, colorIdx) => (
                          <div
                            key={colorIdx}
                            className="w-4 h-4 rounded-full"
                            style={{ backgroundColor: color }}
                          />
                        ))}
                      </div>
                      <p className="text-xs font-medium text-gray-700">{scheme.name}</p>
                    </button>
                  ))}
                </div>
              </div>

              {/* Display Options */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-3">
                  Display Options
                </label>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {[
                    { key: 'show_legend', label: 'Show Legend', desc: 'Display color legend for metrics' },
                    { key: 'show_grid', label: 'Show Grid', desc: 'Display grid lines on chart' },
                    { key: 'animate', label: 'Animations', desc: 'Enable smooth animations' },
                    { key: 'smooth_lines', label: 'Smooth Lines', desc: 'Use curved line interpolation' },
                    { key: 'fill_area', label: 'Fill Area', desc: 'Fill area under lines' },
                    { key: 'show_points', label: 'Show Points', desc: 'Display data points on lines' }
                  ].map(option => (
                    <label key={option.key} className="flex items-start p-3 border rounded-lg hover:bg-gray-50 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={localConfig.settings[option.key as keyof typeof localConfig.settings] as boolean}
                        onChange={(e) => updateConfig(`settings.${option.key}`, e.target.checked)}
                        className="mt-0.5 mr-3 text-blue-600"
                      />
                      <div>
                        <span className="font-medium text-gray-900">{option.label}</span>
                        <p className="text-sm text-gray-500">{option.desc}</p>
                      </div>
                    </label>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Advanced Tab */}
          {activeTab === 'advanced' && (
            <div className="space-y-6">
              {/* Y-Axis Range */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-3">
                  Y-Axis Range (optional)
                </label>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs text-gray-500 mb-1">Minimum Value</label>
                    <input
                      type="number"
                      step="0.1"
                      placeholder="Auto"
                      value={localConfig.settings.y_axis_min || ''}
                      onChange={(e) => updateConfig('settings.y_axis_min', 
                        e.target.value ? parseFloat(e.target.value) : null)}
                      className="form-input w-full"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-gray-500 mb-1">Maximum Value</label>
                    <input
                      type="number"
                      step="0.1"
                      placeholder="Auto"
                      value={localConfig.settings.y_axis_max || ''}
                      onChange={(e) => updateConfig('settings.y_axis_max', 
                        e.target.value ? parseFloat(e.target.value) : null)}
                      className="form-input w-full"
                    />
                  </div>
                </div>
              </div>

              {/* Auto Refresh Settings */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-3">
                  Auto Refresh
                </label>
                <div className="space-y-3">
                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      checked={localConfig.auto_refresh ?? true}
                      onChange={(e) => updateConfig('auto_refresh', e.target.checked)}
                      className="mr-3 text-blue-600"
                    />
                    <span className="text-gray-700">Enable automatic data refresh</span>
                  </label>
                  
                  {localConfig.auto_refresh !== false && (
                    <div>
                      <label className="block text-xs text-gray-500 mb-1">
                        Refresh Interval (seconds)
                      </label>
                      <input
                        type="number"
                        min="5"
                        max="300"
                        value={localConfig.refresh_interval || 30}
                        onChange={(e) => updateConfig('refresh_interval', parseInt(e.target.value))}
                        className="form-input w-32"
                      />
                    </div>
                  )}
                </div>
              </div>

              {/* Grid Layout */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-3">
                  Grid Layout
                </label>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div>
                    <label className="block text-xs text-gray-500 mb-1">X Position</label>
                    <input
                      type="number"
                      min="0"
                      max="11"
                      value={localConfig.layout.x}
                      onChange={(e) => updateConfig('layout.x', parseInt(e.target.value))}
                      className="form-input w-full"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-gray-500 mb-1">Y Position</label>
                    <input
                      type="number"
                      min="0"
                      value={localConfig.layout.y}
                      onChange={(e) => updateConfig('layout.y', parseInt(e.target.value))}
                      className="form-input w-full"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-gray-500 mb-1">Width</label>
                    <input
                      type="number"
                      min="2"
                      max="12"
                      value={localConfig.layout.width}
                      onChange={(e) => updateConfig('layout.width', parseInt(e.target.value))}
                      className="form-input w-full"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-gray-500 mb-1">Height</label>
                    <input
                      type="number"
                      min="2"
                      max="12"
                      value={localConfig.layout.height}
                      onChange={(e) => updateConfig('layout.height', parseInt(e.target.value))}
                      className="form-input w-full"
                    />
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between p-6 border-t bg-gray-50">
          <div className="flex items-center space-x-2">
            {localConfig.is_ai_generated && (
              <span className="px-2 py-1 text-xs bg-purple-100 text-purple-800 rounded-full">
                AI Generated
              </span>
            )}
            {hasChanges && (
              <span className="text-sm text-amber-600">Unsaved changes</span>
            )}
          </div>
          
          <div className="flex space-x-3">
            {onReset && (
              <button
                onClick={handleReset}
                className="btn-secondary flex items-center"
              >
                <RotateCcw className="h-4 w-4 mr-2" />
                Reset
              </button>
            )}
            <button
              onClick={onClose}
              className="btn-secondary"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              className="btn-primary flex items-center"
              disabled={localConfig.metrics.length === 0}
            >
              <Save className="h-4 w-4 mr-2" />
              Save Changes
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default GraphSettingsModal
