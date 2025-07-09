// Main dashboard page for IDES 2.0 displaying real-time sensor data charts, AI-powered insights, and responsive grid layout with WebSocket updates for live environmental monitoring.

import React, { useState, useEffect } from 'react'
import { Plus, RefreshCw, MessageSquare } from 'lucide-react'
import GraphCard from '../components/GraphCard'
import PromptInput from '../components/PromptInput'
import { useForecastMetrics } from '../hooks/useForecastMetrics'

interface DashboardProps {
  wsConnection: boolean
  lastUpdate?: any
}

interface GraphConfig {
  id: string
  title: string
  chartType: string
  metrics: string[]
  timeRange: string
  data?: any
}

const Dashboard: React.FC<DashboardProps> = ({ wsConnection, lastUpdate }) => {
  const [graphs, setGraphs] = useState<GraphConfig[]>([])
  const [loading, setLoading] = useState(true)
  const [showPrompt, setShowPrompt] = useState(false)
  
  const { forecastData, accuracy } = useForecastMetrics()

  // Initialize with default graphs
  useEffect(() => {
    const defaultGraphs: GraphConfig[] = [
      {
        id: 'temp-humidity',
        title: 'Temperature & Humidity',
        chartType: 'line',
        metrics: ['temperature', 'humidity'],
        timeRange: '24h'
      },
      {
        id: 'co2-aqi',
        title: 'CO₂ & Air Quality',
        chartType: 'area',
        metrics: ['co2', 'aqi'],
        timeRange: '12h'
      },
      {
        id: 'pressure',
        title: 'Atmospheric Pressure',
        chartType: 'line',
        metrics: ['pressure'],
        timeRange: '24h'
      },
      {
        id: 'light-level',
        title: 'Light Level',
        chartType: 'bar',
        metrics: ['light_level'],
        timeRange: '6h'
      }
    ]
    
    setGraphs(defaultGraphs)
    setLoading(false)
  }, [])

  // Handle WebSocket updates
  useEffect(() => {
    if (lastUpdate && lastUpdate.type === 'sensor_update') {
      // Update graph data with new sensor readings
      console.log('New sensor data:', lastUpdate.data)
      // In a real implementation, this would update the graph data
    }
  }, [lastUpdate])

  const handleAddGraph = () => {
    const newGraph: GraphConfig = {
      id: `graph-${Date.now()}`,
      title: 'New Graph',
      chartType: 'line',
      metrics: ['temperature'],
      timeRange: '24h'
    }
    setGraphs([...graphs, newGraph])
  }

  const handleRemoveGraph = (graphId: string) => {
    setGraphs(graphs.filter(g => g.id !== graphId))
  }

  const handlePromptSubmit = async (prompt: string) => {
    try {
      const response = await fetch('/api/prompt', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt })
      })
      
      const result = await response.json()
      
      // If AI suggests a chart, add it to the dashboard
      if (result.chart_config) {
        const aiGraph: GraphConfig = {
          id: result.chart_config.id || `ai-${Date.now()}`,
          title: result.chart_config.title,
          chartType: result.chart_config.chart_type,
          metrics: result.chart_config.metrics,
          timeRange: result.chart_config.time_range
        }
        setGraphs([...graphs, aiGraph])
      }
      
      // Show AI response
      console.log('AI Response:', result.response)
    } catch (error) {
      console.error('Failed to process prompt:', error)
    }
  }

  const refreshData = async () => {
    setLoading(true)
    try {
      // Fetch latest data for all graphs
      await Promise.all(
        graphs.map(async (graph) => {
          const response = await fetch(`/api/graphs/${graph.id}/data`)
          if (response.ok) {
            const data = await response.json()
            // Update graph data
            console.log(`Updated data for ${graph.id}:`, data)
          }
        })
      )
    } catch (error) {
      console.error('Failed to refresh data:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="h-8 w-8 animate-spin text-blue-600" />
        <span className="ml-2 text-gray-600">Loading dashboard...</span>
      </div>
    )
  }

  return (
    <div className="max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            Environmental Dashboard
          </h1>
          <p className="text-gray-600 mt-1">
            Real-time indoor sensor monitoring with AI insights
          </p>
        </div>
        
        <div className="flex items-center space-x-3">
          <button
            onClick={() => setShowPrompt(!showPrompt)}
            className="btn-secondary flex items-center"
          >
            <MessageSquare className="h-4 w-4 mr-2" />
            AI Assistant
          </button>
          
          <button
            onClick={refreshData}
            className="btn-primary flex items-center"
            disabled={loading}
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
          
          <button
            onClick={handleAddGraph}
            className="btn-primary flex items-center"
          >
            <Plus className="h-4 w-4 mr-2" />
            Add Graph
          </button>
        </div>
      </div>

      {/* AI Prompt Input */}
      {showPrompt && (
        <div className="mb-6">
          <PromptInput onSubmit={handlePromptSubmit} />
        </div>
      )}

      {/* Connection Status */}
      <div className="mb-6">
        <div className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${
          wsConnection 
            ? 'bg-green-100 text-green-800' 
            : 'bg-red-100 text-red-800'
        }`}>
          <div className={`w-2 h-2 rounded-full mr-2 ${
            wsConnection ? 'bg-green-600' : 'bg-red-600'
          }`} />
          {wsConnection ? 'Live Data Stream Active' : 'Offline - Historical Data Only'}
        </div>
      </div>

      {/* Graph Grid */}
      <div className="dashboard-grid">
        {graphs.map((graph) => (
          <GraphCard
            key={graph.id}
            id={graph.id}
            title={graph.title}
            chartType={graph.chartType}
            metrics={graph.metrics}
            timeRange={graph.timeRange}
            onRemove={() => handleRemoveGraph(graph.id)}
            forecastData={forecastData[graph.metrics[0]]}
            accuracyMetrics={accuracy[graph.metrics[0]]}
          />
        ))}
      </div>

      {/* Empty State */}
      {graphs.length === 0 && (
        <div className="text-center py-12">
          <div className="mx-auto h-12 w-12 text-gray-400">
            <svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
          </div>
          <h3 className="mt-2 text-sm font-medium text-gray-900">
            No graphs configured
          </h3>
          <p className="mt-1 text-sm text-gray-500">
            Get started by adding your first sensor data visualization.
          </p>
          <div className="mt-6">
            <button
              onClick={handleAddGraph}
              className="btn-primary"
            >
              <Plus className="h-4 w-4 mr-2" />
              Add your first graph
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

export default Dashboard