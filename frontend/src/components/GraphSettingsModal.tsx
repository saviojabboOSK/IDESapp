// Enhanced settings modal for graph configuration with comprehensive options for chart customization, metrics selection, and visual styling.

import React, { useState, useEffect, useCallback } from 'react';
import { X, Save, Activity, Plus, Minus } from 'lucide-react';

// Define GraphConfig directly in this file since we're extending it
interface GraphConfig {
  id: string;
  title: string;
  chart_type: string;
  sensor_id?: string;
  sensors?: Array<{
    sensor_id: string;
    metrics: string[];
  }>;
  metrics: string[];
  time_range: string;
  custom_start_time?: string;
  custom_end_time?: string;
  settings: {
    color_scheme: string[];
    show_legend: boolean;
    show_grid: boolean;
    animate?: boolean;
    smooth_lines?: boolean;
    fill_area?: boolean;
    show_points?: boolean;
    y_axis_min?: number;
    y_axis_max?: number;
  };
  layout: {
    x: number;
    y: number;
    width: number;
    height: number;
  };
  is_ai_generated?: boolean;
  auto_refresh?: boolean;
  refresh_interval?: number;
};

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

interface GraphSettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (config: GraphConfig) => void;
  graph: GraphConfig | null;
}

// Removed unused AVAILABLE_METRICS constant

const CHART_TYPES = [
  { value: 'line', label: 'Line Chart', icon: '📈', desc: 'Best for trends over time' },
  { value: 'area', label: 'Area Chart', icon: '📊', desc: 'Filled areas show volume' },
  { value: 'bar', label: 'Bar Chart', icon: '📊', desc: 'Compare values at points in time' },
  { value: 'scatter', label: 'Scatter Plot', icon: '⚪', desc: 'Show correlation between metrics' }
];

const TIME_RANGES = [
  { value: '1h', label: '1 Hour' },
  { value: '6h', label: '6 Hours' },
  { value: '12h', label: '12 Hours' },
  { value: '24h', label: '24 Hours' },
  { value: '7d', label: '7 Days' },
  { value: '30d', label: '30 Days' },
  { value: 'custom', label: 'Custom Range' }
];

const DEFAULT_COLOR_SCHEMES = [
  ['#3b82f6', '#ef4444', '#22c55e', '#f59e0b', '#8b5cf6', '#ec4899'],
  ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b'],
  ['#e11d48', '#0891b2', '#ca8a04', '#9333ea', '#c2410c', '#059669']
];

const METRIC_CONFIG: {[key: string]: {label: string, unit: string, color: string}} = {
  bvoc_equiv: { label: 'BVOC Equivalent', unit: 'ppb', color: '#3b82f6' },
  co2_equiv: { label: 'CO₂ Equivalent', unit: 'ppm', color: '#ef4444' },
  comp_farenheit: { label: 'Temperature', unit: '°F', color: '#22c55e' },
  comp_gas: { label: 'Gas Sensor', unit: 'value', color: '#f59e0b' },
  comp_humidity: { label: 'Humidity', unit: '%', color: '#8b5cf6' },
  temperature: { label: 'Temperature', unit: '°C', color: '#ef4444' },
  humidity: { label: 'Humidity', unit: '%', color: '#3b82f6' },
  co2: { label: 'CO₂', unit: 'ppm', color: '#22c55e' },
  aqi: { label: 'Air Quality', unit: 'AQI', color: '#f59e0b' },
  pressure: { label: 'Pressure', unit: 'hPa', color: '#8b5cf6' },
  light_level: { label: 'Light Level', unit: 'lux', color: '#eab308' }
};

const GraphSettingsModal: React.FC<GraphSettingsModalProps> = ({
  isOpen,
  onClose,
  onSave,
  graph,
}) => {
  const [config, setConfig] = useState<GraphConfig | null>(null);
  const [sensors, setSensors] = useState<SensorInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [sensorSelections, setSensorSelections] = useState<SensorSelection[]>([]);

  useEffect(() => {
    if (graph) {
      setConfig(JSON.parse(JSON.stringify(graph))); // Deep copy

      // Initialize sensor selections if graph has them
      if (graph.sensors && graph.sensors.length > 0) {
        setSensorSelections(JSON.parse(JSON.stringify(graph.sensors)));
      } else if (graph.sensor_id) {
        // Handle legacy format with single sensor
        setSensorSelections([{
          sensor_id: graph.sensor_id,
          metrics: [...graph.metrics]
        }]);
      } else {
        setSensorSelections([{ sensor_id: '', metrics: [] }]);
      }

      // Load available sensors
      loadSensors();
    }
  }, [graph]);

  const loadSensors = useCallback(async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/sensors/');
      if (response.ok) {
        const sensorData = await response.json();
        setSensors(sensorData);
      }
    } catch (error) {
      console.error('Failed to load sensors:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  const updateConfig = useCallback((field: string, value: any) => {
    setConfig((prev: GraphConfig | null) => {
      if (!prev) return null;
      const newConfig = { ...prev };
      let current: any = newConfig;
      const keys = field.split('.');
      for (let i = 0; i < keys.length - 1; i++) {
        current = current[keys[i]];
      }
      current[keys[keys.length - 1]] = value;
      return newConfig;
    });
  }, []);

  // Removed unused handleMetricToggle function as it's replaced by sensor-specific metric selection

  const addSensorSelection = () => {
    setSensorSelections([...sensorSelections, { sensor_id: '', metrics: [] }]);
  };

  const removeSensorSelection = (index: number) => {
    if (sensorSelections.length > 1) {
      setSensorSelections(sensorSelections.filter((_, i) => i !== index));
    }
  };

  const updateSensorSelection = (index: number, sensor_id: string) => {
    const newSelections = [...sensorSelections];
    newSelections[index] = { sensor_id, metrics: [] };
    setSensorSelections(newSelections);
  };

  const updateSensorMetrics = (index: number, metrics: string[]) => {
    const newSelections = [...sensorSelections];
    newSelections[index].metrics = metrics;
    setSensorSelections(newSelections);
  };

  const getSelectedSensor = (sensor_id: string) => {
    return sensors.find(s => s.id === sensor_id);
  };

  const getMetricColor = (sensorIndex: number, metricIndex: number) => {
    if (!config) return '#6b7280';
    // Calculate color index based on sensor and metric position
    const colorIndex = (sensorIndex * 5 + metricIndex) % (config.settings.color_scheme?.length || 1);
    return config.settings.color_scheme?.[colorIndex] || '#6b7280';
  };

  const handleSave = () => {
    if (!config) return;

    // Process sensor selections
    const validSelections = sensorSelections.filter(s => s.sensor_id && s.metrics.length > 0);
    if (validSelections.length === 0) return;

    // Flatten all metrics for backward compatibility
    const allMetrics = validSelections.flatMap(s => s.metrics);
    
    const updatedConfig = {
      ...config,
      sensors: validSelections,
      metrics: allMetrics,
      // Keep sensor_id for single sensor backward compatibility
      sensor_id: validSelections.length === 1 ? validSelections[0].sensor_id : undefined
    };

    onSave(updatedConfig);
  };

  if (!isOpen || !config) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-5xl w-full h-[90vh] flex flex-col">
        {/* Fixed Header */}
        <div className="flex items-center justify-between p-6 border-b flex-shrink-0">
          <div>
            <h2 className="text-xl font-semibold text-gray-900">Edit Graph</h2>
            <p className="text-sm text-gray-500 mt-1">Customize your sensor data visualization</p>
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
                        <div className="flex items-center justify-between mb-2">
                          <label className="block text-sm font-medium text-gray-700">
                            Available Metrics
                          </label>
                          <div className="flex space-x-2">
                            <button
                              onClick={() => {
                                const allMetrics = getSelectedSensor(selection.sensor_id)?.available_metrics || []
                                updateSensorMetrics(index, allMetrics)
                              }}
                              className="px-2 py-1 text-xs bg-blue-100 text-blue-700 rounded hover:bg-blue-200"
                            >
                              Select All
                            </button>
                            <button
                              onClick={() => updateSensorMetrics(index, [])}
                              className="px-2 py-1 text-xs bg-gray-100 text-gray-700 rounded hover:bg-gray-200"
                            >
                              Clear All
                            </button>
                          </div>
                        </div>
                        <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                          {getSelectedSensor(selection.sensor_id)?.available_metrics.map((metric: string, metricIndex: number) => {
                            const metricInfo = METRIC_CONFIG[metric] || { label: metric, unit: 'value', color: '#6b7280' }
                            const isSelected = selection.metrics.includes(metric)
                            // Use consistent color from the graph's color scheme
                            const metricColor = getMetricColor(index, metricIndex)
                            
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
                                    style={{ backgroundColor: isSelected ? metricColor : '#d1d5db' }}
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
                      Graph Title *
                    </label>
                    <input
                      type="text"
                      value={config.title}
                      onChange={(e) => updateConfig('title', e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      placeholder="Enter descriptive title"
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
                          onClick={() => updateConfig('chart_type', type.value)}
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
                  
                  {/* Color Scheme */}
                  <div className="space-y-3">
                    <h3 className="text-lg font-medium text-gray-900">Color Scheme</h3>
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
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
                      onChange={(e) => updateConfig('time_range', e.target.value)}
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
                          onChange={(e) => updateConfig('custom_start_time', e.target.value)}
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
                          onChange={(e) => updateConfig('custom_end_time', e.target.value)}
                          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
                        />
                      </div>
                    </div>
                  )}

                  {/* Y-Axis Range */}
                  <div className="space-y-3">
                    <h4 className="font-medium text-gray-700">Y-Axis Range</h4>
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="block text-sm text-gray-700 mb-1">Minimum (optional)</label>
                        <input
                          type="number"
                          value={config.settings.y_axis_min ?? ''}
                          onChange={(e) => updateConfig('settings.y_axis_min', e.target.value ? Number(e.target.value) : undefined)}
                          placeholder="Auto"
                          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
                        />
                      </div>
                      <div>
                        <label className="block text-sm text-gray-700 mb-1">Maximum (optional)</label>
                        <input
                          type="number"
                          value={config.settings.y_axis_max ?? ''}
                          onChange={(e) => updateConfig('settings.y_axis_max', e.target.value ? Number(e.target.value) : undefined)}
                          placeholder="Auto"
                          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
                        />
                      </div>
                    </div>
                  </div>

                  {/* Display Options */}
                  <div className="space-y-3">
                    <h4 className="font-medium text-gray-700">Display Options</h4>
                    <div className="grid grid-cols-2 gap-2">
                      {[
                        { key: 'show_legend', label: 'Show Legend' },
                        { key: 'show_grid', label: 'Show Grid' },
                        { key: 'animate', label: 'Animations' },
                        { key: 'smooth_lines', label: 'Smooth Lines' },
                        { key: 'fill_area', label: 'Fill Area' },
                        { key: 'show_points', label: 'Show Points' }
                      ].map(option => (
                        <label key={option.key} className="flex items-center p-2 border rounded-lg hover:bg-gray-50">
                          <input
                            type="checkbox"
                            checked={config.settings[option.key as keyof typeof config.settings] as boolean}
                            onChange={(e) => updateConfig(`settings.${option.key}`, e.target.checked)}
                            className="mr-2 text-blue-600 rounded focus:ring-blue-500"
                          />
                          <span className="text-sm text-gray-700">{option.label}</span>
                        </label>
                      ))}
                    </div>
                  </div>

                  {/* Auto Refresh */}
                  <div className="space-y-3">
                    <h4 className="font-medium text-gray-700">Auto Refresh</h4>
                    <div className="flex items-center">
                      <input
                        type="checkbox"
                        id="auto_refresh"
                        checked={config.auto_refresh || false}
                        onChange={(e) => updateConfig('auto_refresh', e.target.checked)}
                        className="mr-2 text-blue-600 rounded focus:ring-blue-500"
                      />
                      <label htmlFor="auto_refresh" className="text-sm text-gray-700">
                        Enable auto refresh
                      </label>
                    </div>
                    
                    {config.auto_refresh && (
                      <div>
                        <label className="block text-sm text-gray-700 mb-1">
                          Refresh interval (seconds)
                        </label>
                        <input
                          type="number"
                          min="5"
                          max="3600"
                          value={config.refresh_interval || 30}
                          onChange={(e) => updateConfig('refresh_interval', Number(e.target.value))}
                          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
                        />
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Fixed Footer */}
        <div className="border-t bg-gray-50 px-6 py-4 flex justify-between items-center flex-shrink-0">
          <div className="text-sm text-gray-500">
            {sensorSelections.filter(s => s.sensor_id && s.metrics.length > 0).length === 0 && "Select at least one sensor and metric"}
            {config.title.trim().length === 0 && sensorSelections.some(s => s.sensor_id && s.metrics.length > 0) && "Enter a title for your graph"}
          </div>
          
          <div className="flex space-x-3">
            <button onClick={onClose} className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500">
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={!config.title.trim().length || !sensorSelections.some(s => s.sensor_id && s.metrics.length > 0)}
              className="flex items-center px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Save className="h-4 w-4 mr-2" />
              Save Changes
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default GraphSettingsModal;
