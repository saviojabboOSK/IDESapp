// Navigation component for IDES 2.0 dashboard with system status indicators, real-time connection monitoring, and responsive menu for sensor data visualization interface.

import React from 'react'
import { Link, useLocation } from 'react-router-dom'
import { Home, Settings, Wifi, WifiOff } from 'lucide-react'

interface NavbarProps {
  isConnected: boolean
  backendHealth: boolean
}

const Navbar: React.FC<NavbarProps> = ({ isConnected, backendHealth }) => {
  const location = useLocation()

  const isActive = (path: string) => location.pathname === path

  return (
    <nav className="bg-white shadow-sm border-b border-gray-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-24">
          {/* Left side: Square logo + Horizontal logo + Navigation */}
          <div className="flex items-center space-x-4">
            {/* Square logo - far left */}
            <div className="flex-shrink-0">
              <img 
                src="/assets/OshkoshLogoBlack.png" 
                alt="Square Logo" 
                className="h-20 w-20 object-contain"
              />
            </div>
            
            {/* Horizontal rectangular logo - next to square */}
            <div className="flex-shrink-0">
              <img 
                src="/assets/ADICLogoBlack.png" 
                alt="Horizontal Logo" 
                className="h-16 w-auto object-contain max-w-[240px]"
              />
            </div>

            {/* Navigation menu */}
            <div className="hidden sm:ml-6 sm:flex sm:space-x-8">
              <Link
                to="/"
                className={`inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium ${
                  isActive('/') 
                    ? 'border-blue-500 text-gray-900' 
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <Home className="h-4 w-4 mr-2" />
                Dashboard
              </Link>
              
              <Link
                to="/settings"
                className={`inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium ${
                  isActive('/settings') 
                    ? 'border-blue-500 text-gray-900' 
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <Settings className="h-4 w-4 mr-2" />
                Settings
              </Link>
            </div>
          </div>

          {/* Center: Middle logo */}
          <div className="flex-shrink-0 absolute left-1/2 transform -translate-x-1/2">
            <img 
              src="/assets/IDESLogoBlack.png" 
              alt="Middle Logo" 
              className="h-16 w-auto object-contain max-w-[200px]"
            />
          </div>

          {/* Right side: Status indicators + Right logo */}
          <div className="flex items-center space-x-4">
            {/* WebSocket status */}
            <div className="flex items-center space-x-2">
              {isConnected ? (
                <Wifi className="h-5 w-5 text-green-600" />
              ) : (
                <WifiOff className="h-5 w-5 text-red-600" />
              )}
              <span className={`text-sm ${isConnected ? 'text-green-600' : 'text-red-600'}`}>
                {isConnected ? 'Live' : 'Offline'}
              </span>
            </div>

            {/* Backend health */}
            <div className={`flex items-center px-3 py-1 rounded-full text-xs font-medium ${
              backendHealth 
                ? 'bg-green-100 text-green-800' 
                : 'bg-red-100 text-red-800'
            }`}>
              <div className={`w-2 h-2 rounded-full mr-2 ${
                backendHealth ? 'bg-green-600' : 'bg-red-600'
              }`} />
              {backendHealth ? 'Healthy' : 'Error'}
            </div>

            {/* Right logo - far right */}
            <div className="flex-shrink-0">
              <img 
                src="/assets/BWLogo.png" 
                alt="Right Logo" 
                className="h-16 w-auto object-contain max-w-[200px]"
              />
            </div>
          </div>
        </div>
      </div>

      {/* Mobile menu */}
      <div className="sm:hidden">
        <div className="pt-2 pb-3 space-y-1">
          {/* Mobile logo row */}
          <div className="flex justify-between items-center px-3 pb-2">
            <div className="flex items-center space-x-2">
              <img 
                src="/assets/OshkoshLogoBlack.png" 
                alt="Square Logo" 
                className="h-16 w-16 object-contain"
              />
              <img 
                src="/assets/ADICLogoBlack.png" 
                alt="Horizontal Logo" 
                className="h-12 w-auto object-contain max-w-[160px]"
              />
            </div>
            <img 
              src="/assets/BWLogo.png" 
              alt="Right Logo" 
              className="h-12 w-auto object-contain max-w-[120px]"
            />
          </div>
          
          <Link
            to="/"
            className={`block pl-3 pr-4 py-2 border-l-4 text-base font-medium ${
              isActive('/') 
                ? 'bg-blue-50 border-blue-500 text-blue-700' 
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:bg-gray-50 hover:border-gray-300'
            }`}
          >
            Dashboard
          </Link>
          
          <Link
            to="/settings"
            className={`block pl-3 pr-4 py-2 border-l-4 text-base font-medium ${
              isActive('/settings') 
                ? 'bg-blue-50 border-blue-500 text-blue-700' 
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:bg-gray-50 hover:border-gray-300'
            }`}
          >
            Settings
          </Link>
        </div>
      </div>
    </nav>
  )
}

export default Navbar