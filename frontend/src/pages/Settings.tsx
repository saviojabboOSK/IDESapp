// Settings page for IDES 2.0 system configuration including data collection intervals, LLM backend selection, InfluxDB connections, sensor nickname management, and service health monitoring with real-time status updates.

import React, { useState, useEffect } from 'react'
import { Save, RefreshCw, AlertCircle, CheckCircle } from 'lucide-react'
import SensorSettings from '../components/SensorSettings'

interface SettingsProps {
  backendStatus: any
}

const Settings: React.FC<SettingsProps> = ({ backendStatus }) => {
  const [settings, setSettings] = useState({
    collection_interval: 30,
    data_retention_weeks: 4,
    llm_backend: 'local',
    influx_url: 'http://localhost:8086',
    influx_org: 'ides',
    influx_bucket: 'sensors'
  })

  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState(false)
  const [connectionTests, setConnectionTests] = useState<any>(null)

  useEffect(() => {
    // Load current settings
    loadSettings()
  }, [])

  const loadSettings = async () => {
    try {
      const response = await fetch('/api/settings')
      if (response.ok) {
        const data = await response.json()
        setSettings({
          collection_interval: data.data_collection?.collection_interval || 30,
          data_retention_weeks: data.data_collection?.data_retention_weeks || 4,
          llm_backend: data.llm_configuration?.backend || 'local',
          influx_url: data.database?.influx_url || 'http://localhost:8086',
          influx_org: data.database?.influx_org || 'ides',
          influx_bucket: data.database?.influx_bucket || 'sensors'
        })
      }
    } catch (error) {
      console.error('Failed to load settings:', error)
    }
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      const response = await fetch('/api/settings', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings)
      })

      if (response.ok) {
        console.log('Settings saved successfully')
      } else {
        console.error('Failed to save settings')
      }
    } catch (error) {
      console.error('Error saving settings:', error)
    } finally {
      setSaving(false)
    }
  }

  const testConnections = async () => {
    setTesting(true)
    try {
      const response = await fetch('/api/settings/test-connection', {
        method: 'POST'
      })

      if (response.ok) {
        const data = await response.json()
        setConnectionTests(data.connection_tests)
      }
    } catch (error) {
      console.error('Failed to test connections:', error)
    } finally {
      setTesting(false)
    }
  }

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">System Settings</h1>
        <p className="text-gray-600 mt-1">
          Configure data collection, AI services, sensor management, and system parameters
        </p>
      </div>

      {/* Sensor Management Section */}
      <div className="mb-8">
        <SensorSettings />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Data Collection Settings */}
        <div className="bg-white rounded-lg shadow-md border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Data Collection
          </h2>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Collection Interval (seconds)
              </label>
              <input
                type="number"
                min="10"
                max="3600"
                value={settings.collection_interval}
                onChange={(e) => setSettings({
                  ...settings,
                  collection_interval: parseInt(e.target.value)
                })}
                className="form-input w-full"
              />
              <p className="text-xs text-gray-500 mt-1">
                How often to collect sensor data (10-3600 seconds)
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Data Retention (weeks)
              </label>
              <input
                type="number"
                min="1"
                max="52"
                value={settings.data_retention_weeks}
                onChange={(e) => setSettings({
                  ...settings,
                  data_retention_weeks: parseInt(e.target.value)
                })}
                className="form-input w-full"
              />
              <p className="text-xs text-gray-500 mt-1">
                How long to keep historical data (1-52 weeks)
              </p>
            </div>
          </div>
        </div>

        {/* LLM Configuration */}
        <div className="bg-white rounded-lg shadow-md border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            AI Configuration
          </h2>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                LLM Backend
              </label>
              <select
                value={settings.llm_backend}
                onChange={(e) => setSettings({
                  ...settings,
                  llm_backend: e.target.value
                })}
                className="form-select w-full"
              >
                <option value="local">Local (Ollama)</option>
                <option value="openai">OpenAI API</option>
              </select>
              <p className="text-xs text-gray-500 mt-1">
                Choose between local LLM or OpenAI API
              </p>
            </div>

            {settings.llm_backend === 'openai' && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  OpenAI API Key
                </label>
                <input
                  type="password"
                  placeholder="sk-..."
                  className="form-input w-full"
                />
                <p className="text-xs text-gray-500 mt-1">
                  Your OpenAI API key for GPT models
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Database Configuration */}
        <div className="bg-white rounded-lg shadow-md border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            InfluxDB Configuration
          </h2>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                InfluxDB URL
              </label>
              <input
                type="url"
                value={settings.influx_url}
                onChange={(e) => setSettings({
                  ...settings,
                  influx_url: e.target.value
                })}
                className="form-input w-full"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Organization
              </label>
              <input
                type="text"
                value={settings.influx_org}
                onChange={(e) => setSettings({
                  ...settings,
                  influx_org: e.target.value
                })}
                className="form-input w-full"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Bucket
              </label>
              <input
                type="text"
                value={settings.influx_bucket}
                onChange={(e) => setSettings({
                  ...settings,
                  influx_bucket: e.target.value
                })}
                className="form-input w-full"
              />
            </div>
          </div>
        </div>

        {/* System Status */}
        <div className="bg-white rounded-lg shadow-md border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900">
              System Status
            </h2>
            <button
              onClick={testConnections}
              disabled={testing}
              className="btn-secondary flex items-center"
            >
              <RefreshCw className={`h-4 w-4 mr-2 ${testing ? 'animate-spin' : ''}`} />
              Test Connections
            </button>
          </div>

          <div className="space-y-3">
            {/* Backend Status */}
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-700">Backend API</span>
              <div className="flex items-center">
                {backendStatus ? (
                  <CheckCircle className="h-4 w-4 text-green-600 mr-1" />
                ) : (
                  <AlertCircle className="h-4 w-4 text-red-600 mr-1" />
                )}
                <span className={`text-sm ${
                  backendStatus ? 'text-green-600' : 'text-red-600'
                }`}>
                  {backendStatus ? 'Connected' : 'Disconnected'}
                </span>
              </div>
            </div>

            {/* Connection Test Results */}
            {connectionTests && (
              <>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-700">InfluxDB</span>
                  <div className="flex items-center">
                    {connectionTests.influxdb?.status === 'connected' ? (
                      <CheckCircle className="h-4 w-4 text-green-600 mr-1" />
                    ) : (
                      <AlertCircle className="h-4 w-4 text-red-600 mr-1" />
                    )}
                    <span className={`text-sm ${
                      connectionTests.influxdb?.status === 'connected' 
                        ? 'text-green-600' 
                        : 'text-red-600'
                    }`}>
                      {connectionTests.influxdb?.status || 'Unknown'}
                    </span>
                  </div>
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-700">LLM Service</span>
                  <div className="flex items-center">
                    {connectionTests.llm?.status === 'connected' ? (
                      <CheckCircle className="h-4 w-4 text-green-600 mr-1" />
                    ) : (
                      <AlertCircle className="h-4 w-4 text-red-600 mr-1" />
                    )}
                    <span className={`text-sm ${
                      connectionTests.llm?.status === 'connected' 
                        ? 'text-green-600' 
                        : 'text-red-600'
                    }`}>
                      {connectionTests.llm?.status || 'Unknown'}
                    </span>
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Save Button */}
      <div className="mt-6 flex justify-end">
        <button
          onClick={handleSave}
          disabled={saving}
          className="btn-primary flex items-center"
        >
          {saving ? (
            <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
          ) : (
            <Save className="h-4 w-4 mr-2" />
          )}
          {saving ? 'Saving...' : 'Save Changes'}
        </button>
      </div>
    </div>
  )
}

export default Settings