import { Routes, Route, Navigate } from 'react-router-dom'
import { useState, useEffect } from 'react'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Orders from './pages/Orders'
import Inventory from './pages/Inventory'
import Products from './pages/Products'
import Customers from './pages/Customers'
import MRPReport from './pages/MRPReport'
import Layout from './components/Layout'

// Auth context mock - in production use proper context
export const useAuth = () => {
  const [user, setUser] = useState<any>(null)
  
  useEffect(() => {
    const token = localStorage.getItem('access_token')
    if (token) {
      // Decode and set user (simplified)
      setUser({ username: 'user', role: 'Super Admin' })
    }
  }, [])
  
  const login = (userData: any) => {
    localStorage.setItem('access_token', userData.access_token)
    localStorage.setItem('refresh_token', userData.refresh_token)
    setUser(userData.user)
  }
  
  const logout = () => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    setUser(null)
  }
  
  return { user, login, logout }
}

function App() {
  const { user, login, logout } = useAuth()
  
  if (!user) {
    return <Login onLogin={login} />
  }
  
  return (
    <Layout user={user} onLogout={logout}>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/orders" element={<Orders />} />
        <Route path="/inventory" element={<Inventory />} />
        <Route path="/products" element={<Products />} />
        <Route path="/customers" element={<Customers />} />
        <Route path="/mrp" element={<MRPReport />} />
      </Routes>
    </Layout>
  )
}

export default App
