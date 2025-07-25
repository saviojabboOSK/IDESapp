// Settings page component for managing sensor nicknames, data sources, and system preferences.

import React, { useState, useEffect, useCallback } from 'react'
import { Save, Edit2, Check, X, Activity, MapPin, Wifi } from 'lucide-react'

interface SensorInfo {
  id: string
  mac_address: string
  nickname?: string
  location?: string
  model?: string
  last_seen?: string
  is_active: boolean
  available_metrics: string[]
}

const SensorSettings: React.FC = () => {
  const [sensors, setSensors] = useState<SensorInfo[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [tempNickname, setTempNickname] = useState('')
  const [changes, setChanges] = useState<Record<string, string>>({})

  // Load sensors data
  useEffect(() => {
    loadSensors()
  }, [])

  const loadSensors = async () => {
    setLoading(true)
    try {
      const response = await fetch('/api/sensors')
      if (response.ok) {
        const sensorData = await response.json()
        setSensors(sensorData)
      } else {
        console.error('Failed to load sensors')
      }
    } catch (error) {
      console.error('Error loading sensors:', error)
    } finally {
      setLoading(false)
    }
  }

  const startEdit = useCallback((sensor: SensorInfo) => {
    setEditingId(sensor.id)
    setTempNickname(sensor.nickname || '')
  }, [])

  const cancelEdit = useCallback(() => {
    setEditingId(null)
    setTempNickname('')
  }, [])

  const saveNickname = useCallback(async (sensorId: string) => {
    const nickname = tempNickname.trim()
    
    try {
      const response = await fetch(`/api/sensors/${sensorId}/nickname`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ nickname }),
      })

      if (response.ok) {
        // Update local state
        setSensors(prev => prev.map(sensor => 
          sensor.id === sensorId 
            ? { ...sensor, nickname: nickname || undefined }
            : sensor
        ))
        setEditingId(null)
        setTempNickname('')
        
        // Track unsaved changes
        if (nickname) {
          setChanges(prev => ({ ...prev, [sensorId]: nickname }))
        } else {
          setChanges(prev => {
            const updated = { ...prev }
            delete updated[sensorId]
            return updated
          })
        }
      } else {
        console.error('Failed to save nickname')
      }
    } catch (error) {
      console.error('Error saving nickname:', error)
    }
  }, [tempNickname])

  const saveAllChanges = useCallback(async () => {
    if (Object.keys(changes).length === 0) return

    setSaving(true)
    try {
      const response = await fetch('/api/sensors/batch/nicknames', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(changes),
      })

      if (response.ok) {
        setChanges({})
        console.log('All nicknames saved successfully')
      } else {
        console.error('Failed to save all nicknames')
      }
    } catch (error) {
      console.error('Error saving all nicknames:', error)
    } finally {
      setSaving(false)
    }
  }, [changes])

  const getStatusBadge = (sensor: SensorInfo) => {
    if (!sensor.is_active) {
      return <span className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-red-100 text-red-800">Offline</span>
    }
    
    const lastSeen = sensor.last_seen ? new Date(sensor.last_seen) : null
    const now = new Date()
    const timeDiff = lastSeen ? now.getTime() - lastSeen.getTime() : Infinity
    const hoursSinceLastSeen = timeDiff / (1000 * 3600)
    
    if (hoursSinceLastSeen < 1) {
      return <span className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-green-100 text-green-800">Online</span>
    } else if (hoursSinceLastSeen < 24) {
      return <span className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-yellow-100 text-yellow-800">Stale</span>
    } else {
      return <span className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-red-100 text-red-800">Offline</span>
    }
  }

  const formatLastSeen = (lastSeen?: string) => {
    if (!lastSeen) return 'Never'
    
    const date = new Date(lastSeen)
    const now = new Date()
    const diff = now.getTime() - date.getTime()
    const hours = Math.floor(diff / (1000 * 3600))
    const minutes = Math.floor((diff % (1000 * 3600)) / (1000 * 60))
    
    if (hours === 0) {
      return `${minutes}m ago`
    } else if (hours < 24) {
      return `${hours}h ${minutes}m ago`
    } else {
      const days = Math.floor(hours / 24)
      return `${days}d ago`
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <span className="ml-3 text-gray-600">Loading sensors...</span>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Sensor Settings</h2>
          <p className="text-gray-600 mt-1">Manage sensor nicknames and monitor device status</p>
        </div>
        
        {Object.keys(changes).length > 0 && (
          <button
            onClick={saveAllChanges}
            disabled={saving}
            className="btn-primary flex items-center"
          >
            <Save className="h-4 w-4 mr-2" />
            {saving ? 'Saving...' : `Save ${Object.keys(changes).length} Changes`}
          </button>
        )}
      </div>

      {/* Sensors List */}
      <div className="bg-white shadow overflow-hidden sm:rounded-md">
        <div className="px-4 py-3 bg-gray-50 border-b border-gray-200">
          <h3 className="text-lg font-medium text-gray-900">
            Discovered Sensors ({sensors.length})
          </h3>
        </div>
        
        <ul className="divide-y divide-gray-200">
          {sensors.map((sensor) => (
            <li key={sensor.id} className="px-6 py-4 hover:bg-gray-50">
              <div className="flex items-center justify-between">
                <div className="flex items-center flex-1">
                  <div className="flex-shrink-0">
                    <Activity className="h-8 w-8 text-gray-400" />
                  </div>
                  
                  <div className="ml-4 flex-1">
                    <div className="flex items-center">
                      {editingId === sensor.id ? (
                        <div className="flex items-center space-x-2">
                          <input
                            type="text"
                            value={tempNickname}
                            onChange={(e) => setTempNickname(e.target.value)}
                            className="form-input text-lg font-medium"
                            placeholder="Enter nickname"
                            autoFocus
                          />
                          <button
                            onClick={() => saveNickname(sensor.id)}
                            className="p-1 text-green-600 hover:text-green-800"
                          >
                            <Check className="h-5 w-5" />
                          </button>
                          <button
                            onClick={cancelEdit}
                            className="p-1 text-red-600 hover:text-red-800"
                          >
                            <X className="h-5 w-5" />
                          </button>
                        </div>
                      ) : (
                        <div className="flex items-center">
                          <h4 className="text-lg font-medium text-gray-900">
                            {sensor.nickname || sensor.location || `Sensor ${sensor.id}`}
                          </h4>
                          <button
                            onClick={() => startEdit(sensor)}
                            className="ml-2 p-1 text-gray-400 hover:text-gray-600"
                          >
                            <Edit2 className="h-4 w-4" />
                          </button>
                          {changes[sensor.id] && (
                            <span className="ml-2 text-xs text-blue-600 bg-blue-100 px-2 py-1 rounded">
                              Modified
                            </span>
                          )}
                        </div>
                      )}
                    </div>
                    
                    <div className="mt-1 flex items-center space-x-4 text-sm text-gray-500">
                      <div className="flex items-center">
                        <Wifi className="h-4 w-4 mr-1" />
                        <span>{sensor.mac_address}</span>
                      </div>
                      
                      {sensor.location && (
                        <div className="flex items-center">
                          <MapPin className="h-4 w-4 mr-1" />
                          <span>{sensor.location}</span>
                        </div>
                      )}
                    </div>
                    
                    <div className="mt-2 flex items-center space-x-4 text-sm">
                      <span className="text-gray-500">
                        {sensor.available_metrics.length} metrics: {sensor.available_metrics.join(', ')}
                      </span>
                    </div>
                    
                    {sensor.model && (
                      <div className="mt-1 text-xs text-gray-400">
                        Model: {sensor.model}
                      </div>
                    )}
                  </div>
                </div>
                
                <div className="flex items-center space-x-4">
                  <div className="text-right">
                    <div className="text-sm text-gray-500">Last seen</div>
                    <div className="text-sm font-medium text-gray-900">
                      {formatLastSeen(sensor.last_seen)}
                    </div>
                  </div>
                  
                  <div>
                    {getStatusBadge(sensor)}
                  </div>
                </div>
              </div>
            </li>
          ))}
        </ul>
        
        {sensors.length === 0 && (
          <div className="px-6 py-8 text-center">
            <Activity className="mx-auto h-12 w-12 text-gray-400" />
            <h3 className="mt-2 text-sm font-medium text-gray-900">No sensors found</h3>
            <p className="mt-1 text-sm text-gray-500">
              Check your data sources or wait for sensors to start reporting data.
            </p>
          </div>
        )}
      </div>

      {/* Additional Settings */}
      <div className="bg-white shadow sm:rounded-lg">
        <div className="px-4 py-5 sm:p-6">
          <h3 className="text-lg leading-6 font-medium text-gray-900">
            Data Source Settings
          </h3>
          <div className="mt-2 max-w-xl text-sm text-gray-500">
            <p>Configure how sensor data is collected and processed.</p>
          </div>
          <div className="mt-5">
            <button
              type="button"
              className="btn-secondary"
              onClick={() => window.location.reload()}
            >
              Refresh Sensor Discovery
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default SensorSettings
