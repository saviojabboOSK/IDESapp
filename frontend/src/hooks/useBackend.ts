// Backend health monitoring hook for IDES 2.0 providing real-time API status checks, connection monitoring, and service availability detection for dashboard reliability.

import { useState, useEffect } from 'react'

interface BackendStatus {
  api: string
  websocket: string
  scheduler: string
}

interface UseBackendReturn {
  isHealthy: boolean
  backendStatus: BackendStatus | null
  lastCheck: Date | null
  checkHealth: () => Promise<void>
}

export const useBackend = (): UseBackendReturn => {
  const [isHealthy, setIsHealthy] = useState(false)
  const [backendStatus, setBackendStatus] = useState<BackendStatus | null>(null)
  const [lastCheck, setLastCheck] = useState<Date | null>(null)

  const checkHealth = async (): Promise<void> => {
    try {
      const response = await fetch('/api/health', {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      })

      if (response.ok) {
        const data = await response.json()
        setIsHealthy(data.status === 'healthy')
        setBackendStatus(data.services || null)
      } else {
        setIsHealthy(false)
        setBackendStatus(null)
      }
    } catch (error) {
      console.error('Backend health check failed:', error)
      setIsHealthy(false)
      setBackendStatus(null)
    } finally {
      setLastCheck(new Date())
    }
  }

  // Check health on mount and then every 30 seconds
  useEffect(() => {
    checkHealth()
    
    const interval = setInterval(() => {
      checkHealth()
    }, 30000) // 30 seconds

    return () => clearInterval(interval)
  }, [])

  return {
    isHealthy,
    backendStatus,
    lastCheck,
    checkHealth
  }
}