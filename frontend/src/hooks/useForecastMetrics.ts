// Forecast metrics hook for IDES 2.0 providing access to AI-generated predictions, accuracy tracking, and trend analysis for sensor data visualization and insights.

import { useState, useEffect } from 'react'

interface ForecastData {
  timestamps: string[]
  values: number[]
  confidence: string
  accuracy_metrics?: {
    mae: number
    rmse: number
    mape: number
  }
}

interface UseForecastMetricsReturn {
  forecastData: Record<string, ForecastData>
  accuracy: Record<string, any>
  loading: boolean
  refreshForecasts: () => Promise<void>
}

export const useForecastMetrics = (): UseForecastMetricsReturn => {
  const [forecastData, setForecastData] = useState<Record<string, ForecastData>>({})
  const [accuracy, setAccuracy] = useState<Record<string, any>>({})
  const [loading, setLoading] = useState(false)

  const refreshForecasts = async (): Promise<void> => {
    setLoading(true)
    try {
      const response = await fetch('/api/forecasts')
      if (response.ok) {
        const data = await response.json()
        setForecastData(data.forecasts || {})
        setAccuracy(data.accuracy || {})
      }
    } catch (error) {
      console.error('Failed to fetch forecasts:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    refreshForecasts()
    
    // Refresh forecasts every 10 minutes
    const interval = setInterval(refreshForecasts, 10 * 60 * 1000)
    
    return () => clearInterval(interval)
  }, [])

  return {
    forecastData,
    accuracy,
    loading,
    refreshForecasts
  }
}