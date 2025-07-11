// Main dashboard page for IDES 2.0 displaying real-time sensor data charts with draggable grid layout, AI-powered insights, and WebSocket updates for live environmental monitoring.

import React from 'react'
import GridDashboard from '../components/GridDashboard'

interface DashboardProps {
  wsConnection: boolean
  lastUpdate?: any
}

const Dashboard: React.FC<DashboardProps> = ({ wsConnection, lastUpdate }) => {
  return <GridDashboard wsConnection={wsConnection} lastUpdate={lastUpdate} />
}

export default Dashboard