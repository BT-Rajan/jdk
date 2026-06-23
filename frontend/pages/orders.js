/* ── Orders ──────────────────────────────────────────────────────────────── */
const ORDER_STATUSES = ['Open','Approved','Production Planned','In Production','Ready For Shipment','Shipped','Closed','Cancelled'];
const ORDER_PRIORITIES = ['Critical','High','Normal','Low'];

async function renderOrders(el) {
  el.innerHTML = `
    <div class="page-header">
      <div class="page-title-group">
        <div class="page-title">Customer Orders</div>
        <div class="page-sub">Manage and track all production orders</div>
      </div>
      <div class="page-actions">
        <button class="btn btn-primary btn-sm" onclick="showCreateOrderModal()">+ New Order</button>
      </div>
    </div>
    <div class="filter-bar">
      <select id="ord-filter-status" onchange="loadOrdersTable()">
        <option value="">All Statuses</option>
        ${ORDER_STATUSES.map(s => `<option>${s}</option>`).join('')}
      </select>
      <select id="ord-filter-priority" onchange="loadOrdersTable()">
        <option value="">All Priorities</option>
        ${ORDER_PRIORITIES.map(p => `<option>${p}</option>`).join('')}
      </select>
      <input type="text" id="ord-search" placeholder="Search orders…" oninput="filterOrdersTable()" style="flex:2;min-width:180px;"/>
    </div>
    <div id="orders-content">${loading()}</div>`;
  await loadOrdersTable();
}

let _allOrders = [];

async function loadOrdersTable() {
  const el = document.getElementById('orders-content');
  if (!el) return;
  el.innerHTML = loading();
  const q = {};
  const st = document.getElementById('ord-filter-status')?.value;
  const pr = document.getElementById('ord-filter-priority')?.value;
  if (st) q.status   = st;
  if (pr) q.priority = pr;

  const res = await api.getOrders(Object.keys(q).length ? q : null);
  if (!res?.ok) { el.innerHTML = `<div class="alert alert-danger">${res?.error}</div>`; return; }
  _allOrders = res.data;
  filterOrdersTable();
}

function filterOrdersTable() {
  const el = document.getElementById('orders-content');
  if (!el) return;
  const q = (document.getElementById('ord-search')?.value || '').toLowerCase();
  const orders = q
    ? _allOrders.filter(o =>
        o.order_no?.toLowerCase().includes(q) ||
        o.customer?.toLowerCase().includes(q) ||
        o.product?.toLowerCase().includes(q))
    : _allOrders;

  el.innerHTML = table([
    { key: 'order_no',       label: 'Order No', mono: true },
    { key: 'customer',       label: 'Customer' },
    { key: 'product',        label: 'Product' },
    { key: 'quantity',       label: 'Quantity', render: r => `${fmt(r.quantity, 0)} ${r.unit}` },
    { key: 'priority',       label: 'Priority',  render: r => priorityBadge(r.priority) },
    { key: 'status',         label: 'Status',    render: r => statusBadge(r.status) },
    { key: 'delivery_date',  label: 'Delivery',  render: r => fmtDate(r.delivery_date), muted: true },
    { key: '_actions',       label: '', render: r => `
      <div style="display:flex;gap:.4rem;">
        <button class="btn btn-secondary btn-sm" onclick="showUpdateStatusModal('${r.order_no.replace(/'/g,"\\'")}','${r.status}')">Status</button>
        <button class="btn btn-ghost btn-sm" title="Feasibility" onclick="quickFeasibility('${r.order_no.replace(/'/g,"\\'")}')">🔍</button>
        <button class="btn btn-danger btn-sm" onclick="deleteOrder('${r.order_no.replace(/'/g,"\\'")}')">✕</button>
      </div>` },
  ], orders, { emptyIcon: '📋', emptyTitle: 'No orders found', emptySub: 'Create your first order or adjust filters' });
}

async function showCreateOrderModal() {
  const [prodRes, custRes] = await Promise.all([api.getProducts(), api.getCustomers()]);
  const products  = prodRes?.ok  ? prodRes.data.map(p => p.name)       : [];
  const customers = custRes?.ok  ? custRes.data.map(c => c.customer)   : [];
  const today     = new Date().toISOString().slice(0, 10);

  openModal(`
    <h3 style="margin-bottom:1.25rem;font-size:1rem;font-weight:700;">New Customer Order</h3>
    ${formRow(
      inputGroup('ord-no', 'Order No', 'text', 'placeholder="SO-0001 (auto if blank)"'),
      selectGroup('ord-priority', 'Priority', ORDER_PRIORITIES, 'Normal')
    )}
    ${selectGroup('ord-customer', 'Customer *', customers.length ? customers : ['(No customers)'])}
    ${formRow(
      selectGroup('ord-product', 'Product *', products.length ? products : ['(No products)']),
      selectGroup('ord-status', 'Status', ORDER_STATUSES, 'Open')
    )}
    ${formRow(
      inputGroup('ord-qty',  'Quantity *', 'number', 'min="0.1" step="0.1" placeholder="500"'),
      selectGroup('ord-unit','Unit', ['bags','kg','tons'])
    )}
    ${formRow(
      inputGroup('ord-bag',      'Bag Size (kg)',  'number', 'min="1" step="0.5" value="25"'),
      inputGroup('ord-delivery', 'Delivery Date',  'date',   `value="${today}"`)
    )}
    <div id="ord-err" class="form-error hidden"></div>
    <div style="display:flex;gap:.5rem;margin-top:1rem;">
      <button class="btn btn-primary" style="flex:1" onclick="submitCreateOrder()">Create Order</button>
      <button class="btn btn-secondary" onclick="closeModal()">Cancel</button>
    </div>`);
}

async function submitCreateOrder() {
  const qty = parseFloat(document.getElementById('ord-qty').value);
  if (!qty || qty <= 0) {
    document.getElementById('ord-err').textContent = 'Valid quantity required';
    document.getElementById('ord-err').classList.remove('hidden');
    return;
  }
  const body = {
    order_no:      document.getElementById('ord-no').value.trim() || undefined,
    customer:      document.getElementById('ord-customer').value,
    product:       document.getElementById('ord-product').value,
    quantity:      qty,
    unit:          document.getElementById('ord-unit').value,
    bag_size_kg:   parseFloat(document.getElementById('ord-bag').value)      || 25,
    priority:      document.getElementById('ord-priority').value,
    status:        document.getElementById('ord-status').value,
    delivery_date: document.getElementById('ord-delivery').value,
  };
  const res = await api.createOrder(body);
  if (res?.ok) { closeModal(); toast('Order created', 'success'); await loadOrdersTable(); }
  else { document.getElementById('ord-err').textContent = res?.error; document.getElementById('ord-err').classList.remove('hidden'); }
}

function showUpdateStatusModal(orderNo, currentStatus) {
  openModal(`
    <h3 style="margin-bottom:1.25rem;font-size:1rem;font-weight:700;">Update Order ${orderNo}</h3>
    ${selectGroup('upd-status',   'Status',   ORDER_STATUSES,   currentStatus)}
    ${selectGroup('upd-priority', 'Priority', ORDER_PRIORITIES)}
    <div style="display:flex;gap:.5rem;margin-top:1rem;">
      <button class="btn btn-primary" style="flex:1" onclick="submitUpdateStatus('${orderNo}')">Update</button>
      <button class="btn btn-secondary" onclick="closeModal()">Cancel</button>
    </div>`);
}

async function submitUpdateStatus(orderNo) {
  const body = {
    status:   document.getElementById('upd-status').value,
    priority: document.getElementById('upd-priority').value,
  };
  const res = await api.updateOrder(orderNo, body);
  if (res?.ok) { closeModal(); toast('Order updated', 'success'); await loadOrdersTable(); }
  else toast(res?.error, 'error');
}

function quickFeasibility(orderNo) {
  const order = _allOrders.find(o => o.order_no === orderNo);
  if (!order) return;
  App.navigate('feasibility');
  // Pre-fill after render
  setTimeout(() => {
    const setVal = (id, val) => { const el = document.getElementById(id); if (el) el.value = val; };
    setVal('feas-product',  order.product);
    setVal('feas-customer', order.customer);
    setVal('feas-qty',      order.quantity);
    setVal('feas-unit',     order.unit);
    setVal('feas-bag',      order.bag_size_kg || 25);
  }, 150);
}

async function deleteOrder(orderNo) {
  if (!confirm(`Delete order "${orderNo}"? This cannot be undone.`)) return;
  const res = await api.deleteOrder(orderNo);
  if (res?.ok) { toast('Order deleted', 'success'); await loadOrdersTable(); }
  else toast(res?.error, 'error');
}
