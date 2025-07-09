// WebSocket hook for IDES 2.0 providing real-time connection to backend sensor data streams with automatic reconnection and message handling for live dashboard updates.

import { useState, useEffect, useRef } from 'react'

interface UseWebSocketReturn {
  isConnected: boolean
  lastMessage: any
  sendMessage: (message: string) => void
  connect: () => void
  disconnect: () => void
}

export const useWebSocket = (url: string): UseWebSocketReturn => {
  const [isConnected, setIsConnected] = useState(false)
  const [lastMessage, setLastMessage] = useState(null)
  const ws = useRef<WebSocket | null>(null)
  const reconnectTimeout = useRef<number | null>(null)

  const connect = () => {
    try {
      ws.current = new WebSocket(url)
      
      ws.current.onopen = () => {
        setIsConnected(true)
        console.log('WebSocket connected')
        
        // Clear any pending reconnection
        if (reconnectTimeout.current) {
          clearTimeout(reconnectTimeout.current)
          reconnectTimeout.current = null
        }
      }
      
      ws.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          setLastMessage(data)
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error)
        }
      }
      
      ws.current.onclose = () => {
        setIsConnected(false)
        console.log('WebSocket disconnected')
        
        // Attempt to reconnect after 3 seconds
        reconnectTimeout.current = setTimeout(() => {
          console.log('Attempting to reconnect...')
          connect()
        }, 3000)
      }
      
      ws.current.onerror = (error) => {
        console.error('WebSocket error:', error)
        setIsConnected(false)
      }
      
    } catch (error) {
      console.error('Failed to create WebSocket connection:', error)
      setIsConnected(false)
    }
  }

  const disconnect = () => {
    if (reconnectTimeout.current) {
      clearTimeout(reconnectTimeout.current)
      reconnectTimeout.current = null
    }
    
    if (ws.current) {
      ws.current.close()
      ws.current = null
    }
    
    setIsConnected(false)
  }

  const sendMessage = (message: string) => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.send(message)
    } else {
      console.warn('WebSocket is not connected')
    }
  }

  useEffect(() => {
    connect()
    
    return () => {
      disconnect()
    }
  }, [url])

  return {
    isConnected,
    lastMessage,
    sendMessage,
    connect,
    disconnect
  }
}