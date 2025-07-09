// Main React application component orchestrating the IDES 2.0 dashboard with routing, real-time WebSocket connections, and responsive layout for sensor data visualization.

import { Routes, Route } from 'react-router-dom'
import Navbar from './components/Navbar'
import Dashboard from './pages/Dashboard'
import Settings from './pages/Settings'
import { useWebSocket } from './hooks/useWebSocket'
import { useBackend } from './hooks/useBackend'

function App() {
  // Initialize WebSocket connection for real-time updates
  const { isConnected, lastMessage } = useWebSocket('ws://localhost:8000/ws')
  
  // Initialize backend health monitoring
  const { isHealthy, backendStatus } = useBackend()

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar 
        isConnected={isConnected} 
        backendHealth={isHealthy}
      />
      
      <main className="container mx-auto px-4 py-6">
        <Routes>
          <Route 
            path="/" 
            element={
              <Dashboard 
                wsConnection={isConnected}
                lastUpdate={lastMessage}
              />
            } 
          />
          <Route 
            path="/settings" 
            element={
              <Settings 
                backendStatus={backendStatus}
              />
            } 
          />
        </Routes>
      </main>
      
      {/* Status indicators */}
      <div className="fixed bottom-4 right-4 space-y-2">
        <div className={`px-3 py-1 rounded text-sm ${
          isConnected 
            ? 'bg-green-100 text-green-800' 
            : 'bg-red-100 text-red-800'
        }`}>
          WebSocket: {isConnected ? 'Connected' : 'Disconnected'}
        </div>
        
        <div className={`px-3 py-1 rounded text-sm ${
          isHealthy 
            ? 'bg-green-100 text-green-800' 
            : 'bg-yellow-100 text-yellow-800'
        }`}>
          Backend: {isHealthy ? 'Healthy' : 'Checking...'}
        </div>
      </div>
    </div>
  )
}

export default App