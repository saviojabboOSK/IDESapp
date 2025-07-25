// Grid-based dashboard layout using react-grid-layout for draggable and resizable graph cards with persistent positioning and real-time data synchronization.

import React, { useState, useEffect, useCallback } from 'react'
import { Responsive, WidthProvider, Layout } from 'react-grid-layout'
import { Plus, RefreshCw, MessageSquare, Grid } from 'lucide-react'
import DraggableGraphCard from './DraggableGraphCard'
import PromptInput from './PromptInput'
import GraphBuilderModalEnhanced from './GraphBuilderModalEnhanced'
import GraphSettingsModal from './GraphSettingsModal'
import 'react-grid-layout/css/styles.css'

const ResponsiveGridLayout = WidthProvider(Responsive)

interface GraphConfig {
  id: string
  title: string
  chart_type: string
  sensor_id?: string  // New field for sensor selection
  metrics: string[]
  time_range: string
  custom_start_time?: string  // New field for custom timeframes
  custom_end_time?: string    // New field for custom timeframes
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
  [graphId: string]: {
    labels: string[]
    data: { [metric: string]: number[] }
  }
}

interface GridDashboardProps {
  wsConnection: boolean
  lastUpdate?: any
}

const GridDashboard: React.FC<GridDashboardProps> = ({ wsConnection, lastUpdate }) => {
  const [graphs, setGraphs] = useState<GraphConfig[]>([])
  const [layouts, setLayouts] = useState<{ [key: string]: Layout[] }>({})
  const [loading, setLoading] = useState(true)
  const [showPrompt, setShowPrompt] = useState(false)
  const [showGraphBuilder, setShowGraphBuilder] = useState(false)
  const [graphData, setGraphData] = useState<GraphData>({})
  const [refreshing, setRefreshing] = useState(false)
  const [editingGraph, setEditingGraph] = useState<GraphConfig | null>(null)
  const [dataLoading, setDataLoading] = useState(false)

  // Load graphs from backend
  const loadGraphs = useCallback(async () => {
    try {
      setLoading(true)
      const response = await fetch('/api/graphs')
      if (response.ok) {
        const fetchedGraphs = await response.json()
        setGraphs(fetchedGraphs)
        
        // Convert graph layouts to react-grid-layout format
        const newLayouts: { [key: string]: Layout[] } = {
          lg: fetchedGraphs.map((graph: GraphConfig) => ({
            i: graph.id,
            x: graph.layout.x,
            y: graph.layout.y,
            w: graph.layout.width,
            h: graph.layout.height,
            minW: 2,
            minH: 2
          }))
        }
        setLayouts(newLayouts)
        
        // Load data for each graph immediately after graphs are set
        await loadAllGraphData(fetchedGraphs)
      } else {
        console.error('Failed to fetch graphs:', response.status, response.statusText)
      }
    } catch (error) {
      console.error('Failed to load graphs:', error)
    } finally {
      setLoading(false)
    }
  }, [])

  // Load data for all graphs
  const loadAllGraphData = useCallback(async (graphList: GraphConfig[]) => {
    if (!graphList || graphList.length === 0) {
      console.log('No graphs to load data for')
      return
    }

    const dataPromises = graphList.map(async (graph) => {
      try {
        const response = await fetch(`/api/graphs/${graph.id}/data?limit=100`)
        if (response.ok) {
          const result = await response.json()
          
          // Ensure we have valid data
          if (!result.data || !Array.isArray(result.data)) {
            console.warn(`No valid data returned for graph ${graph.id}`)
            return {
              graphId: graph.id,
              data: {
                labels: [],
                data: graph.metrics.reduce((acc, metric) => {
                  acc[metric] = []
                  return acc
                }, {} as { [metric: string]: number[] })
              }
            }
          }

          return {
            graphId: graph.id,
            data: {
              labels: result.data.map((point: any) => 
                new Date(point.timestamp).toLocaleTimeString('en-US', { 
                  hour: '2-digit', 
                  minute: '2-digit' 
                })
              ),
              data: graph.metrics.reduce((acc, metric) => {
                acc[metric] = result.data.map((point: any) => point[metric] || 0)
                return acc
              }, {} as { [metric: string]: number[] })
            }
          }
        } else {
          console.error(`Failed to load data for graph ${graph.id}:`, response.status, response.statusText)
          // Return empty data structure on API failure
          return {
            graphId: graph.id,
            data: {
              labels: [],
              data: graph.metrics.reduce((acc, metric) => {
                acc[metric] = []
                return acc
              }, {} as { [metric: string]: number[] })
            }
          }
        }
      } catch (error) {
        console.error(`Failed to load data for graph ${graph.id}:`, error)
        // Return empty data structure on error
        return {
          graphId: graph.id,
          data: {
            labels: [],
            data: graph.metrics.reduce((acc, metric) => {
              acc[metric] = []
              return acc
            }, {} as { [metric: string]: number[] })
          }
        }
      }
    })

    try {
      const results = await Promise.all(dataPromises)
      const newGraphData: GraphData = {}
      
      results.forEach((result) => {
        if (result) {
          newGraphData[result.graphId] = result.data
        }
      })
      
      setGraphData(newGraphData)
      console.log('Graph data loaded for', Object.keys(newGraphData).length, 'graphs')
    } catch (error) {
      console.error('Failed to load graph data:', error)
    }
  }, [])

  // Handle layout change
  const handleLayoutChange = useCallback((layout: Layout[], allLayouts: { [key: string]: Layout[] }) => {
    setLayouts(allLayouts)
    
    // Update backend with new positions
    const updates = layout.map(item => {
      const graph = graphs.find(g => g.id === item.i)
      if (graph) {
        return {
          id: graph.id,
          layout: {
            x: item.x,
            y: item.y,
            width: item.w,
            height: item.h
          }
        }
      }
      return null
    }).filter(Boolean)

    // Debounced update to backend
    debounceLayoutUpdate(updates)
  }, [graphs])

  // Debounced function to update layout in backend
  const debounceLayoutUpdate = useCallback(
    debounce(async (updates: any[]) => {
      try {
        // Use the new batch layout update endpoint
        await fetch('/api/graphs/batch/layout', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(updates)
        })
      } catch (error) {
        console.error('Failed to update layouts:', error)
      }
    }, 1000),
    []
  )

  // Create new graph
  const handleAddGraph = useCallback(() => {
    setShowGraphBuilder(true)
  }, [])

  // Handle graph creation from builder
  const handleCreateGraph = useCallback(async (graphConfig: any) => {
    try {
      const response = await fetch('/api/graphs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(graphConfig)
      })

      if (response.ok) {
        await loadGraphs()
        setShowGraphBuilder(false)
      }
    } catch (error) {
      console.error('Failed to create graph:', error)
    }
  }, [loadGraphs])

  // Update graph configuration
  const handleUpdateGraph = useCallback(async (id: string, updates: Partial<GraphConfig>) => {
    try {
      const response = await fetch(`/api/graphs/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates)
      })

      if (response.ok) {
        const updatedGraph = await response.json()
        // Update local state
        setGraphs(prev => prev.map(graph => 
          graph.id === id ? updatedGraph : graph
        ))
        
        await loadAllGraphData(graphs)
        setEditingGraph(null)
      }
    } catch (error) {
      console.error('Failed to update graph:', error)
    }
  }, [loadAllGraphData, graphs])

  // Delete graph
  const handleDeleteGraph = useCallback(async (id: string) => {
    try {
      const response = await fetch(`/api/graphs/${id}`, {
        method: 'DELETE'
      })

      if (response.ok) {
        setGraphs(prev => prev.filter(graph => graph.id !== id))
        setGraphData(prev => {
          const newData = { ...prev }
          delete newData[id]
          return newData
        })
      }
    } catch (error) {
      console.error('Failed to delete graph:', error)
    }
  }, [])

  // Handle AI prompt
  const handlePromptSubmit = useCallback(async (prompt: string) => {
    try {
      const response = await fetch('/api/prompt', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt })
      })
      
      const result = await response.json()
      
      // If AI created a new graph, reload graphs
      if (result.chart_config) {
        await loadGraphs()
      }
      
      // Show AI response (you might want to add a notification system)
      console.log('AI Response:', result.response)
    } catch (error) {
      console.error('Failed to process prompt:', error)
    }
  }, [loadGraphs])

  // Handle AI generation from graph builder
  const handleAIGenerate = useCallback(async (prompt: string) => {
    try {
      const response = await fetch('/api/prompt', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt })
      })
      
      const result = await response.json()
      
      if (result.chart_config) {
        await loadGraphs()
        setShowGraphBuilder(false)
      }
    } catch (error) {
      console.error('Failed to generate graph with AI:', error)
    }
  }, [loadGraphs])

  // Refresh all data
  const handleRefresh = useCallback(async () => {
    setRefreshing(true)
    try {
      await loadAllGraphData(graphs)
    } finally {
      setRefreshing(false)
    }
  }, [graphs, loadAllGraphData])

  // WebSocket updates
  useEffect(() => {
    if (lastUpdate && lastUpdate.type === 'sensor_update') {
      // Update graph data with new sensor readings
      loadAllGraphData(graphs)
    }
  }, [lastUpdate, graphs, loadAllGraphData])

  // Initial load with retry mechanism
  useEffect(() => {
    const initializeApp = async () => {
      let retries = 3
      while (retries > 0) {
        try {
          await loadGraphs()
          break // Success, exit retry loop
        } catch (error) {
          console.error('Failed to initialize app, retrying...', error)
          retries--
          if (retries > 0) {
            await new Promise(resolve => setTimeout(resolve, 2000)) // Wait 2s before retry
          }
        }
      }
    }
    
    initializeApp()
  }, [loadGraphs])

  // Auto-refresh data every 30 seconds
  useEffect(() => {
    if (graphs.length === 0) return

    const interval = setInterval(() => {
      console.log('Auto-refreshing graph data...')
      loadAllGraphData(graphs)
    }, 30000) // 30 seconds

    return () => clearInterval(interval)
  }, [graphs, loadAllGraphData])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="h-8 w-8 animate-spin text-blue-600" />
        <span className="ml-2 text-gray-600">Loading dashboard...</span>
      </div>
    )
  }

  return (
    <div className="max-w-full mx-auto p-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            Environmental Dashboard
          </h1>
          <p className="text-gray-600 mt-1">
            Drag and resize charts • Real-time data with AI insights
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
            onClick={handleRefresh}
            className="btn-primary flex items-center"
            disabled={refreshing}
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${refreshing ? 'animate-spin' : ''}`} />
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

      {/* Grid Layout */}
      {graphs.length > 0 ? (
        <ResponsiveGridLayout
          className="layout"
          layouts={layouts}
          onLayoutChange={handleLayoutChange}
          breakpoints={{ lg: 1200, md: 996, sm: 768, xs: 480, xxs: 0 }}
          cols={{ lg: 12, md: 10, sm: 6, xs: 4, xxs: 2 }}
          rowHeight={60}
          margin={[16, 16]}
          containerPadding={[0, 0]}
          isDraggable={true}
          isResizable={true}
          draggableHandle=".drag-handle"
          onResizeStop={(_, __, newItem) => {
            const graph = graphs.find(g => g.id === newItem.i);
            if (graph) {
              const updates = {
                layout: {
                  ...graph.layout,
                  width: newItem.w,
                  height: newItem.h,
                }
              };
              handleUpdateGraph(graph.id, updates);
            }
          }}
        >
          {graphs.map((graph) => (
            <div key={graph.id}>
              <DraggableGraphCard
                config={graph}
                onEdit={() => setEditingGraph(graph)}
                onDelete={handleDeleteGraph}
                data={graphData[graph.id]}
                isLoading={refreshing}
              />
            </div>
          ))}
        </ResponsiveGridLayout>
      ) : (
        /* Empty State */
        <div className="text-center py-12">
          <div className="mx-auto h-12 w-12 text-gray-400">
            <Grid className="h-12 w-12" />
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
      
      {/* Graph Builder Modal */}
      <GraphBuilderModalEnhanced
        isOpen={showGraphBuilder}
        onSave={handleCreateGraph}
        onClose={() => setShowGraphBuilder(false)}
        onAIGenerate={handleAIGenerate}
      />
      
      {editingGraph && (
        <GraphSettingsModal
          graph={editingGraph}
          isOpen={!!editingGraph}
          onSave={(config) => handleUpdateGraph(config.id, config)}
          onClose={() => setEditingGraph(null)}
        />
      )}
    </div>
  )
}

// Debounce utility function
function debounce<T extends (...args: any[]) => any>(func: T, wait: number): T {
  let timeout: number | null = null
  return ((...args: any[]) => {
    if (timeout) clearTimeout(timeout)
    timeout = setTimeout(() => func(...args), wait)
  }) as T
}

export default GridDashboard
