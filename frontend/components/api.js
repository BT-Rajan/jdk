/* ── JDK API Client ──────────────────────────────────────────────────────── */
// Empty string = same origin (works when served by Flask on any host/port)
const API_BASE = window.JDK_API_BASE || '';

const api = {
  async _fetch(method, path, body, isFile) {
    const opts = {
      method,
      credentials: 'include',
      headers: isFile ? {} : { 'Content-Type': 'application/json' },
    };
    if (body && !isFile) opts.body = JSON.stringify(body);
    if (body && isFile)  opts.body = body;

    let res;
    try {
      res = await fetch(API_BASE + path, opts);
    } catch (e) {
      return { ok: false, error: 'Cannot reach server. Is it running?' };
    }

    // 401 = not logged in. NEVER call location.reload() — just return the error.
    // app.js init() will show the auth screen; no infinite loop possible.
    if (res.status === 401) {
      return { ok: false, error: 'Not authenticated' };
    }

    try {
      return await res.json();
    } catch (e) {
      return { ok: false, error: 'Server returned non-JSON response (status ' + res.status + ')' };
    }
  },

  get:    (path)       => api._fetch('GET',    path),
  post:   (path, body) => api._fetch('POST',   path, body),
  patch:  (path, body) => api._fetch('PATCH',  path, body),
  delete: (path)       => api._fetch('DELETE', path),
  upload: (path, form) => api._fetch('POST',   path, form, true),

  // Auth
  login:    (u, p) => api.post('/api/auth/login',           { username: u, password: p }),
  signup:   (body) => api.post('/api/auth/signup',          body),
  forgotPw: (body) => api.post('/api/auth/forgot-password', body),
  resetPw:  (body) => api.post('/api/auth/reset-password',  body),
  logout:   ()     => api.post('/api/auth/logout'),
  me:       ()     => api.get('/api/auth/me'),

  // Dashboard
  dashboard: () => api.get('/api/dashboard'),

  // Chat
  chat: (message, history) => api.post('/api/chat', { message, history }),

  // Settings
  getSettings:  ()     => api.get('/api/settings'),
  saveSettings: (body) => api.post('/api/settings', body),

  // Customers
  getCustomers:   ()  => api.get('/api/customers'),
  addCustomer:    (b) => api.post('/api/customers', b),
  deleteCustomer: (n) => api.delete('/api/customers/' + encodeURIComponent(n)),

  // Products
  getProducts:   ()  => api.get('/api/products'),
  upsertProduct: (b) => api.post('/api/products', b),
  deleteProduct: (n) => api.delete('/api/products/' + encodeURIComponent(n)),

  // Formulas
  getFormula:        (p)    => api.get('/api/formulas/'    + encodeURIComponent(p)),
  upsertFormulaLine: (p, b) => api.post('/api/formulas/'   + encodeURIComponent(p), b),
  deleteFormulaLine: (p, m) => api.delete('/api/formulas/' + encodeURIComponent(p) + '/' + encodeURIComponent(m)),

  // Raw Materials
  getRawMaterials: ()  => api.get('/api/raw-materials'),
  upsertMaterial:  (b) => api.post('/api/raw-materials', b),
  deleteMaterial:  (n) => api.delete('/api/raw-materials/' + encodeURIComponent(n)),

  // Suppliers
  getSuppliers:   ()         => api.get('/api/suppliers'),
  addSupplier:    (b)        => api.post('/api/suppliers', b),
  deleteSupplier: (mat, sup) => api.delete('/api/suppliers/' + encodeURIComponent(mat) + '/' + encodeURIComponent(sup)),

  // Inventory
  getFG:           ()  => api.get('/api/inventory/finished-goods'),
  updateFG:        (b) => api.post('/api/inventory/finished-goods', b),
  inventoryHealth: ()  => api.get('/api/inventory/health'),

  // Feasibility
  checkFeasibility: (b) => api.post('/api/feasibility', b),

  // Orders
  getOrders:   (q)      => api.get('/api/orders' + (q ? '?' + new URLSearchParams(q) : '')),
  createOrder: (b)      => api.post('/api/orders', b),
  updateOrder: (no, b)  => api.patch('/api/orders/' + encodeURIComponent(no), b),
  deleteOrder: (no)     => api.delete('/api/orders/' + encodeURIComponent(no)),

  // MRP
  runMRP: () => api.post('/api/mrp/run'),

  // Backup
  restoreMaster: (form) => api.upload('/api/restore/master', form),

  // Production Schedules
  getSchedules:   (q)       => api.get('/api/production-schedule' + (q ? '?' + new URLSearchParams(q) : '')),
  createSchedule: (b)       => api.post('/api/production-schedule', b),
  updateSchedule: (id, b)   => api.patch('/api/production-schedule/' + encodeURIComponent(id), b),
  deleteSchedule: (id)      => api.delete('/api/production-schedule/' + encodeURIComponent(id)),
  scheduleAlerts: ()        => api.get('/api/production-schedule/alerts'),
};
