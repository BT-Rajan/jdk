import axios from 'axios'

const API_BASE = '/api'

export const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// Response interceptor for token refresh
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      // Try to refresh token
      const refreshToken = localStorage.getItem('refresh_token')
      if (refreshToken) {
        try {
          const response = await axios.post(`${API_BASE}/auth/refresh`, {
            refresh_token: refreshToken,
          })
          localStorage.setItem('access_token', response.data.access_token)
          localStorage.setItem('refresh_token', response.data.refresh_token)
          // Retry original request
          error.config.headers.Authorization = `Bearer ${response.data.access_token}`
          return api(error.config)
        } catch {
          localStorage.removeItem('access_token')
          localStorage.removeItem('refresh_token')
          window.location.href = '/login'
        }
      }
    }
    return Promise.reject(error)
  }
)

// Auth APIs
export const authApi = {
  login: (username: string, password: string) => {
    const formData = new FormData()
    formData.append('username', username)
    formData.append('password', password)
    return api.post('/auth/login', formData, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    })
  },
  logout: () => api.post('/auth/logout'),
  me: () => api.get('/auth/me'),
}

// Dashboard API
export const dashboardApi = {
  getStats: () => api.get('/mrp/dashboard/stats'),
}

// Orders API
export const ordersApi = {
  list: (params?: any) => api.get('/orders', { params }),
  get: (id: number) => api.get(`/orders/${id}`),
  create: (data: any) => api.post('/orders', data),
  update: (id: number, data: any) => api.put(`/orders/${id}`, data),
  delete: (id: number) => api.delete(`/orders/${id}`),
}

// Inventory API
export const inventoryApi = {
  listMaterials: () => api.get('/inventory/materials'),
  updateInventory: (id: number, data: any) => api.put(`/inventory/materials/${id}/inventory`, data),
  listFinishedGoods: () => api.get('/inventory/finished-goods'),
  updateFinishedGoods: (id: number, data: any) => api.put(`/inventory/finished-goods/${id}`, data),
  listSuppliers: (materialId?: number) => api.get('/inventory/suppliers', { params: { material_id: materialId } }),
}

// Products API
export const productsApi = {
  list: () => api.get('/products'),
  get: (id: number) => api.get(`/products/${id}`),
  create: (data: any) => api.post('/products', data),
  update: (id: number, data: any) => api.put(`/products/${id}`, data),
  getFormulas: (id: number) => api.get(`/products/${id}/formulas`),
}

// Customers API
export const customersApi = {
  list: () => api.get('/customers'),
  create: (data: any) => api.post('/customers', data),
  update: (id: number, data: any) => api.put(`/customers/${id}`, data),
}

// MRP API
export const mrpApi = {
  run: () => api.get('/mrp/run'),
  getOrderFeasibility: (orderId: number) => api.get(`/mrp/orders/${orderId}/feasibility`),
}
