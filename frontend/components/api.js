/* ── JDK API Client ──────────────────────────────────────────────────────── */
const API_BASE = window.JDK_API_BASE || 'http://localhost:5000';

const api = {
  async _fetch(method, path, body, isFile) {
    const opts = {
      method,
      credentials: 'include',
      headers: isFile ? {} : { 'Content-Type': 'application/json' },
    };
    if (body && !isFile) opts.body = JSON.stringify(body);
    if (body && isFile) opts.body = body;

    const res = await fetch(`${API_BASE}${path}`, opts);
    if (res.status === 401) {
      sessionStorage.clear();
      window.location.reload();
      return;
    }
    const data = await res.json().catch(() => ({ ok: false, error: 'Network error' }));
    return data;
  },

  get:    (path)        => api._fetch('GET',    path),
  post:   (path, body)  => api._fetch('POST',   path, body),
  patch:  (path, body)  => api._fetch('PATCH',  path, body),
  delete: (path)        => api._fetch('DELETE', path),
  upload: (path, form)  => api._fetch('POST',   path, form, true),

  // Convenience download
  download(path, filename) {
    const a = document.createElement('a');
    a.href = `${API_BASE}${path}`;
    a.download = filename;
    a.click();
  },

  // Auth
  login:         (u, p) => api.post('/api/auth/login',    { username: u, password: p }),
  signup:        (body)  => api.post('/api/auth/signup',   body),
  forgotPw:      (ident) => api.post('/api/auth/forgot-password', ident),
  resetPw:       (body)  => api.post('/api/auth/reset-password', body),
  logout:        ()      => api.post('/api/auth/logout'),
  me:            ()      => api.get('/api/auth/me'),

  // Dashboard
  dashboard: () => api.get('/api/dashboard'),

  // Chat
  chat: (message, history) => api.post('/api/chat', { message, history }),

  // Settings
  getSettings:  ()     => api.get('/api/settings'),
  saveSettings: (body) => api.post('/api/settings', body),

  // Customers
  getCustomers:   ()    => api.get('/api/customers'),
  addCustomer:    (b)   => api.post('/api/customers', b),
  deleteCustomer: (n)   => api.delete(`/api/customers/${encodeURIComponent(n)}`),

  // Products
  getProducts:   ()   => api.get('/api/products'),
  upsertProduct: (b)  => api.post('/api/products', b),
  deleteProduct: (n)  => api.delete(`/api/products/${encodeURIComponent(n)}`),

  // Formulas
  getFormula:         (p)    => api.get(`/api/formulas/${encodeURIComponent(p)}`),
  upsertFormulaLine:  (p, b) => api.post(`/api/formulas/${encodeURIComponent(p)}`, b),
  deleteFormulaLine:  (p, m) => api.delete(`/api/formulas/${encodeURIComponent(p)}/${encodeURIComponent(m)}`),

  // Raw Materials
  getRawMaterials:   ()  => api.get('/api/raw-materials'),
  upsertMaterial:    (b) => api.post('/api/raw-materials', b),
  deleteMaterial:    (n) => api.delete(`/api/raw-materials/${encodeURIComponent(n)}`),

  // Suppliers
  getSuppliers:    ()  => api.get('/api/suppliers'),
  addSupplier:     (b) => api.post('/api/suppliers', b),
  deleteSupplier:  (mat, sup) => api.delete(`/api/suppliers/${encodeURIComponent(mat)}/${encodeURIComponent(sup)}`),

  // Inventory
  getFG:           ()  => api.get('/api/inventory/finished-goods'),
  updateFG:        (b) => api.post('/api/inventory/finished-goods', b),
  inventoryHealth: ()  => api.get('/api/inventory/health'),

  // Feasibility
  checkFeasibility: (b) => api.post('/api/feasibility', b),

  // Orders
  getOrders:    (q)  => api.get('/api/orders' + (q ? '?' + new URLSearchParams(q).toString() : '')),
  createOrder:  (b)  => api.post('/api/orders', b),
  updateOrder:  (no, b) => api.patch(`/api/orders/${encodeURIComponent(no)}`, b),
  deleteOrder:  (no) => api.delete(`/api/orders/${encodeURIComponent(no)}`),

  // MRP
  runMRP:    () => api.post('/api/mrp/run'),
  exportMRP: () => `${API_BASE}/api/mrp/export`,

  // Backup
  backupMaster:    () => api.download('/api/backup/master',    'master_data_backup.json'),
  backupOrders:    () => api.download('/api/backup/orders',    'customer_orders_backup.json'),
  backupCustomers: () => api.download('/api/backup/customers', 'customers_backup.json'),
  restoreMaster:   (form) => api.upload('/api/restore/master', form),
};
