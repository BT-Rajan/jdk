/* ── Dashboard ───────────────────────────────────────────────────────────── */
async function renderDashboard(el) {
  el.innerHTML = `
    <div class="page-header">
      <div class="page-title-group">
        <div class="page-title">Dashboard</div>
        <div class="page-sub">Live production & inventory snapshot</div>
      </div>
      <div class="page-actions">
        <button class="btn btn-primary btn-sm" onclick="App.navigate('chat')">💬 Ask AI</button>
        <button class="btn btn-secondary btn-sm" onclick="renderDashboard(document.getElementById('page-container'))">↻ Refresh</button>
      </div>
    </div>
    <div id="dash-content">${loading()}</div>`;

  const res = await api.dashboard();
  if (!res?.ok) {
    document.getElementById('dash-content').innerHTML = `<div class="alert alert-danger">Failed to load dashboard: ${res?.error || 'Unknown error'}</div>`;
    return;
  }

  const d = res.data;
  const k = d.kpis;
  const alerts = d.alerts;

  let alertHtml = '';
  if (alerts.critical_materials?.length)
    alertHtml += `<div class="alert alert-danger">⚠️ <strong>Critical stock:</strong> ${alerts.critical_materials.join(', ')} — below minimum level.</div>`;
  if (alerts.critical_orders > 0)
    alertHtml += `<div class="alert alert-danger">🚨 <strong>${alerts.critical_orders} critical order(s)</strong> require immediate attention.</div>`;

  const kpis = `<div class="kpi-grid">
    ${kpiCard('Active Products', k.active_products, '', 'var(--accent)')}
    ${kpiCard('Customers', k.customers, '', 'var(--purple)')}
    ${kpiCard('Open Orders', k.open_orders, `${k.critical_orders} critical`, k.critical_orders > 0 ? 'var(--danger)' : 'var(--accent)')}
    ${kpiCard('Suppliers', k.suppliers, '', 'var(--success)')}
    ${kpiCard('Stock Alerts', k.stock_alerts, `${k.critical_stock} critical`, k.critical_stock > 0 ? 'var(--danger)' : k.stock_alerts > 0 ? 'var(--warn)' : 'var(--success)')}
  </div>`;

  const fgTable = table([
    { key: 'product', label: 'Product' },
    { key: 'category', label: 'Category', muted: true },
    { key: 'available_kg', label: 'Available (kg)', render: r => fmt(r.available_kg, 0) },
    { key: 'available_bags', label: 'Bags', render: r => fmt(r.available_bags, 0) },
    { key: 'status', label: 'Status', render: r => statusBadge(r.status) },
  ], d.finished_goods, { emptyIcon: '📦', emptyTitle: 'No finished goods', emptySub: 'Update inventory to see stock here' });

  const invTable = table([
    { key: 'material', label: 'Material' },
    { key: 'current_stock', label: 'Stock', render: r => fmt(r.current_stock, 0) },
    { key: 'reorder_point', label: 'Reorder At', render: r => fmt(r.reorder_point, 0), muted: true },
    { key: 'status', label: 'Status', render: r => statusBadge(r.status) },
  ], d.inventory_health, { emptyIcon: '🪨', emptyTitle: 'No inventory data' });

  const openTable = table([
    { key: 'order_no', label: 'Order No', mono: true },
    { key: 'customer', label: 'Customer' },
    { key: 'product', label: 'Product' },
    { key: 'quantity', label: 'Qty', render: r => `${fmt(r.quantity, 0)} ${r.unit}` },
    { key: 'priority', label: 'Priority', render: r => priorityBadge(r.priority) },
    { key: 'status', label: 'Status', render: r => statusBadge(r.status) },
    { key: 'delivery_date', label: 'Delivery', render: r => fmtDate(r.delivery_date), muted: true },
  ], d.open_orders, { emptyIcon: '📋', emptyTitle: 'No open orders', emptySub: 'All caught up!' });

  document.getElementById('dash-content').innerHTML = `
    ${alertHtml}
    ${kpis}
    <div class="two-col" style="margin-bottom:1rem;">
      <div class="card">
        <div class="section-header"><span class="section-title">Finished Goods</span>
          <button class="btn btn-ghost btn-sm" onclick="App.navigate('inventory')">View all →</button>
        </div>
        ${fgTable}
      </div>
      <div class="card">
        <div class="section-header"><span class="section-title">Inventory Health</span>
          <button class="btn btn-ghost btn-sm" onclick="App.navigate('materials')">Manage →</button>
        </div>
        ${invTable}
      </div>
    </div>
    <div class="card">
      <div class="section-header"><span class="section-title">Open Orders</span>
        <button class="btn btn-ghost btn-sm" onclick="App.navigate('orders')">View all →</button>
      </div>
      ${openTable}
    </div>`;
}
