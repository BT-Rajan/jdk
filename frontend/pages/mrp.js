/* ── MRP Run ─────────────────────────────────────────────────────────────── */
async function renderMRP(el) {
  el.innerHTML = `
    <div class="page-header">
      <div class="page-title-group">
        <div class="page-title">Material Requirements Planning</div>
        <div class="page-sub">Full multi-order feasibility and procurement plan</div>
      </div>
      <div class="page-actions" id="mrp-actions">
        <button class="btn btn-primary" id="mrp-run-btn" onclick="runMRP()">▶ Run MRP</button>
      </div>
    </div>
    <div id="mrp-content">
      <div class="empty-state">
        <div class="empty-state-icon">⚙️</div>
        <div class="empty-state-title">Click "Run MRP" to analyse all open orders</div>
        <div class="empty-state-sub">Calculates material requirements, feasibility and reorder alerts across your full order book</div>
      </div>
    </div>`;
}

async function runMRP() {
  const btn = document.getElementById('mrp-run-btn');
  const el  = document.getElementById('mrp-content');
  btn.disabled = true;
  btn.textContent = '⏳ Running…';
  el.innerHTML = loading('Running MRP across all open orders…');

  const res = await api.runMRP();
  btn.disabled = false;
  btn.textContent = '▶ Run MRP';

  if (!res?.ok) {
    el.innerHTML = `<div class="alert alert-danger">MRP Error: ${res?.error}</div>`;
    return;
  }

  const d = res.data;
  const feasData = d.order_feasibility || [];
  const matSum   = d.raw_material_requirements_summary || [];
  const alerts   = d.reorder_alerts || [];
  const matDet   = d.order_material_detail || [];

  // Summary KPIs
  const totalOrders  = feasData.length;
  const readyOrders  = feasData.filter(r => r.feasibility_status === 'READY FOR SHIPMENT').length;
  const canProduce   = feasData.filter(r => r.feasibility_status === 'CAN PRODUCE').length;
  const shortages    = feasData.filter(r => r.feasibility_status === 'RAW MATERIAL SHORTAGE').length;
  const critAlerts   = alerts.filter(a => a.severity === 'CRITICAL').length;

  const kpis = `<div class="kpi-grid" style="margin-bottom:1.25rem;">
    ${kpiCard('Total Orders', totalOrders, 'in scope', 'var(--accent)')}
    ${kpiCard('Ready to Ship', readyOrders, 'from existing stock', 'var(--success)')}
    ${kpiCard('Can Produce', canProduce, 'materials available', 'var(--info)')}
    ${kpiCard('Shortage', shortages, 'need procurement', shortages > 0 ? 'var(--danger)' : 'var(--success)')}
    ${kpiCard('Reorder Alerts', critAlerts, 'critical items', critAlerts > 0 ? 'var(--danger)' : 'var(--success)')}
  </div>`;

  // Feasibility table
  const feasTable = table([
    { key: 'order_no',            label: 'Order No', mono: true },
    { key: 'customer',            label: 'Customer' },
    { key: 'product',             label: 'Product' },
    { key: 'order_demand_kg',     label: 'Demand (kg)',  render: r => fmt(r.order_demand_kg, 0) },
    { key: 'shipment_ready_kg',   label: 'Ship Ready',  render: r => fmt(r.shipment_ready_kg, 0) },
    { key: 'production_required_kg', label: 'Produce', render: r => fmt(r.production_required_kg, 0) },
    { key: 'earliest_delivery_date', label: 'Earliest Delivery', muted: true },
    { key: 'estimated_material_cost', label: 'Est. Cost',  render: r => r.estimated_material_cost ? `₹${fmt(r.estimated_material_cost, 0)}` : '—', muted: true },
    { key: 'priority',            label: 'Priority',  render: r => priorityBadge(r.priority) },
    { key: 'feasibility_status',  label: 'Status',    render: r => statusBadge(r.feasibility_status) },
  ], feasData, { emptyIcon: '📋', emptyTitle: 'No orders to plan' });

  // Material summary
  const matSumTable = table([
    { key: 'material',    label: 'Material' },
    { key: 'required_qty',label: 'Total Required', render: r => fmt(r.required_qty, 0) },
    { key: 'current_stock',label: 'In Stock',      render: r => fmt(r.current_stock, 0) },
    { key: 'net_shortage', label: 'Net Shortage',  render: r => r.net_shortage > 0
        ? `<span style="color:var(--danger-text);font-weight:700">${fmt(r.net_shortage, 0)}</span>`
        : badge('OK', 'ok') },
  ], matSum, { emptyIcon: '✅', emptyTitle: 'No material requirements' });

  // Reorder alerts
  const alertTable = table([
    { key: 'material',       label: 'Material' },
    { key: 'current_stock',  label: 'Current',    render: r => fmt(r.current_stock, 0) },
    { key: 'reorder_point',  label: 'Reorder At', render: r => fmt(r.reorder_point, 0), muted: true },
    { key: 'minimum_stock',  label: 'Min Stock',  render: r => fmt(r.minimum_stock, 0), muted: true },
    { key: 'lead_time_days', label: 'Lead (days)',muted: true },
    { key: 'severity',       label: 'Severity',   render: r => statusBadge(r.severity) },
  ], alerts, { emptyIcon: '✅', emptyTitle: 'No reorder alerts', emptySub: 'All materials are above reorder points' });

  // Export button
  const actionsEl = document.getElementById('mrp-actions');
  if (actionsEl && !actionsEl.querySelector('#mrp-export-btn')) {
    const exportBtn = document.createElement('button');
    exportBtn.id = 'mrp-export-btn';
    exportBtn.className = 'btn btn-success';
    exportBtn.textContent = '⬇ Export Excel';
    exportBtn.onclick = exportMRPExcel;
    actionsEl.insertBefore(exportBtn, document.getElementById('mrp-run-btn'));
  }

  el.innerHTML = kpis + tabs([
    { id: 'feas',    label: `Order Feasibility (${feasData.length})`,     content: `<div style="margin-top:.75rem;">${feasTable}</div>` },
    { id: 'matsum',  label: `Material Requirements (${matSum.length})`,   content: `<div style="margin-top:.75rem;">${matSumTable}</div>` },
    { id: 'alerts',  label: `Reorder Alerts (${alerts.length})`,          content: `<div style="margin-top:.75rem;">${alertTable}</div>` },
    { id: 'matdet',  label: `Order-Material Detail (${matDet.length})`,   content: `<div style="margin-top:.75rem;">${renderMatDetail(matDet)}</div>` },
  ]);
}

function renderMatDetail(rows) {
  return table([
    { key: 'order_no',     label: 'Order No', mono: true },
    { key: 'product',      label: 'Product' },
    { key: 'material',     label: 'Material' },
    { key: 'required_qty', label: 'Required', render: r => fmt(r.required_qty, 1) },
    { key: 'current_stock',label: 'In Stock', render: r => fmt(r.current_stock, 1) },
    { key: 'shortage_qty', label: 'Shortage', render: r => r.shortage_qty > 0
        ? `<span style="color:var(--danger-text)">${fmt(r.shortage_qty, 1)}</span>` : '—' },
    { key: 'status', label: 'Status', render: r => statusBadge(r.status) },
  ], rows, { emptyIcon: '✅', emptyTitle: 'No detail records' });
}

async function exportMRPExcel() {
  const btn = document.getElementById('mrp-export-btn');
  btn.disabled = true;
  btn.textContent = '⏳ Exporting…';
  // POST to get export, then trigger download
  const res = await fetch(`${window.JDK_API_BASE || ''}/api/mrp/export`, { method: 'POST', credentials: 'include' });
  if (res.ok) {
    const blob = await res.blob();
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement('a');
    a.href     = url;
    a.download = 'jdk_mrp_report.xlsx';
    a.click();
    URL.revokeObjectURL(url);
    toast('Excel report downloaded', 'success');
  } else {
    toast('Export failed', 'error');
  }
  btn.disabled = false;
  btn.textContent = '⬇ Export Excel';
}
