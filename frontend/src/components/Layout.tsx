import { ReactNode } from 'react'
import { Link, useLocation } from 'react-router-dom'

interface LayoutProps {
  user: any
  onLogout: () => void
  children: ReactNode
}

const navItems = [
  { path: '/', label: 'Dashboard', icon: '📊' },
  { path: '/orders', label: 'Orders', icon: '📋' },
  { path: '/inventory', label: 'Inventory', icon: '📦' },
  { path: '/products', label: 'Products', icon: '🏭' },
  { path: '/customers', label: 'Customers', icon: '👥' },
  { path: '/mrp', label: 'MRP Report', icon: '📈' },
]

export default function Layout({ user, onLogout, children }: LayoutProps) {
  const location = useLocation()
  
  return (
    <div className="min-h-screen bg-surface flex">
      {/* Sidebar */}
      <aside className="w-64 bg-navy text-white flex flex-col">
        <div className="p-6 border-b border-blue">
          <h1 className="text-xl font-bold">🏭 JDK Smart Factory</h1>
          <p className="text-xs text-muted mt-1">Enterprise Platform v2.0</p>
        </div>
        
        <nav className="flex-1 p-4">
          {navItems.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              className={`flex items-center gap-3 px-4 py-3 rounded-lg mb-1 transition-colors ${
                location.pathname === item.path
                  ? 'bg-accent text-white'
                  : 'text-gray-300 hover:bg-white/10'
              }`}
            >
              <span>{item.icon}</span>
              <span className="font-medium">{item.label}</span>
            </Link>
          ))}
        </nav>
        
        <div className="p-4 border-t border-blue">
          <div className="mb-3">
            <p className="font-medium">{user?.username}</p>
            <span className="text-xs bg-accent/20 text-accent px-2 py-1 rounded-full">
              {user?.role}
            </span>
          </div>
          <button
            onClick={onLogout}
            className="w-full py-2 px-4 bg-white/10 hover:bg-white/20 rounded-lg text-sm transition-colors"
          >
            Sign Out
          </button>
        </div>
      </aside>
      
      {/* Main Content */}
      <main className="flex-1 overflow-auto">
        <header className="bg-white border-b border-light px-8 py-4">
          <h2 className="text-2xl font-bold text-navy">
            {navItems.find(i => i.path === location.pathname)?.label || 'JDK Smart Factory'}
          </h2>
        </header>
        <div className="p-8">
          {children}
        </div>
      </main>
    </div>
  )
}
