import React from 'react'
import { Outlet, Link, NavLink } from 'react-router-dom'
import { Search, AlertTriangle, GitBranch, Map, Info, Home } from 'lucide-react'

function Header() {
  return (
    <header className="bg-white border-b border-gray-200 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Logo */}
          <Link to="/" className="flex items-center space-x-2">
            <div className="w-8 h-8 bg-sentinel-600 rounded-lg flex items-center justify-center">
              <span className="text-white font-bold text-lg">P</span>
            </div>
            <span className="font-bold text-xl text-gray-900">Grigori</span>
          </Link>
          
          {/* Navigation */}
          <nav className="hidden md:flex items-center space-x-1">
            <NavLink
              to="/"
              end
              className={({ isActive }) =>
                `flex items-center px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                  isActive
                    ? 'text-sentinel-600 bg-sentinel-50'
                    : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
                }`
              }
            >
              <Home className="w-4 h-4 mr-1.5" />
              Home
            </NavLink>
            
            <NavLink
              to="/search"
              className={({ isActive }) =>
                `flex items-center px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                  isActive
                    ? 'text-sentinel-600 bg-sentinel-50'
                    : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
                }`
              }
            >
              <Search className="w-4 h-4 mr-1.5" />
              Search
            </NavLink>
            
            <NavLink
              to="/alerts"
              className={({ isActive }) =>
                `flex items-center px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                  isActive
                    ? 'text-sentinel-600 bg-sentinel-50'
                    : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
                }`
              }
            >
              <AlertTriangle className="w-4 h-4 mr-1.5" />
              Red Flags
            </NavLink>
            
            <NavLink
              to="/network"
              className={({ isActive }) =>
                `flex items-center px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                  isActive
                    ? 'text-sentinel-600 bg-sentinel-50'
                    : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
                }`
              }
            >
              <GitBranch className="w-4 h-4 mr-1.5" />
              Network
            </NavLink>
            
            <NavLink
              to="/map"
              className={({ isActive }) =>
                `flex items-center px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                  isActive
                    ? 'text-sentinel-600 bg-sentinel-50'
                    : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
                }`
              }
            >
              <Map className="w-4 h-4 mr-1.5" />
              Risk Map
            </NavLink>
            
            <NavLink
              to="/about"
              className={({ isActive }) =>
                `flex items-center px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                  isActive
                    ? 'text-sentinel-600 bg-sentinel-50'
                    : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
                }`
              }
            >
              <Info className="w-4 h-4 mr-1.5" />
              About
            </NavLink>
          </nav>
          
          {/* Mobile menu button - simplified for now */}
          <button className="md:hidden p-2 rounded-md text-gray-600 hover:bg-gray-100">
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
        </div>
      </div>
    </header>
  )
}

function Footer() {
  return (
    <footer className="bg-white border-t border-gray-200 mt-auto">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="flex flex-col md:flex-row justify-between items-center space-y-4 md:space-y-0">
          <div className="text-sm text-gray-500">
            © 2026 Grigori. Open source procurement intelligence.
          </div>
          <div className="flex items-center space-x-4">
            <span className="text-sm text-gray-500">
              Data source:{' '}
              <a 
                href="https://prozorro.gov.ua" 
                target="_blank" 
                rel="noopener noreferrer"
                className="text-sentinel-600 hover:underline"
              >
                Prozorro Public API
              </a>
            </span>
          </div>
        </div>
      </div>
    </footer>
  )
}

function Layout() {
  return (
    <div className="min-h-screen flex flex-col">
      <Header />
      <main className="flex-1">
        <Outlet />
      </main>
      <Footer />
    </div>
  )
}

export default Layout
