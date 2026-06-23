/* ── Feasibility Check ───────────────────────────────────────────────────── */
async function renderFeasibility(el) {
  const prodRes = await api.getProducts();
  const custRes = await api.getCustomers();
  const products  = prodRes?.ok  ? prodRes.data.map(p => p.name) : [];
  const customers = custRes?.ok  ? custRes.data.map(c => c.customer) : [];

  el.innerHTML = `
    <div class="page-header">
      <div class="page-title-group">
        <div class="page-title">Feasibility Check</div>
        <div class="page-sub">Instant order feasibility before committing</div>
      </div>
    </div>
    <div class="two-col" style="align-items:start;">
      <div class="card">
        <div class="card-title">Order Parameters</div>
        ${selectGroup('feas-product',  'Product *',  products.length  ? products  : ['(No products)'])}
        ${selectGroup('feas-customer', 'Customer',   customers.length ? customers : ['(No customers)'])}
        ${formRow(
          inputGroup('feas-qty',  'Quantity *', 'number', 'min="0.1" step="0.1" placeholder="500"'),
          selectGroup('feas-unit', 'Unit', ['bags','kg','tons'])
        )}
        ${inputGroup('feas-bag', 'Bag Size (kg)', 'number', 'min="1" step="0.5" value="25"')}
        <div id="feas-err" class="form-error hidden"></div>
        <button class="btn btn-primary btn-full" id="feas-btn" onclick="runFeasibility()">
          🔍 Check Feasibility
        </button>
      </div>
      <div id="feas-result">
        <div class="empty-state">
          <div class="empty-state-icon">🔍</div>
          <div class="empty-state-title">Enter order details to check feasibility</div>
          <div class="empty-state-sub">Get instant production and delivery estimates</div>
        </div>
      </div>
    </div>`;
}

async function runFeasibility() {
  const btn    = document.getElementById('feas-btn');
  const errEl  = document.getElementById('feas-err');
  const result = document.getElementById('feas-result');

  const qty = parseFloat(document.getElementById('feas-qty').value);
  if (!qty || qty <= 0) {
    errEl.textContent = 'Enter a valid quantity';
    errEl.classList.remove('hidden');
    return;
  }
  errEl.classList.add('hidden');
  btn.disabled = true;
  btn.textContent = '⏳ Checking…';
  result.innerHTML = loading('Running feasibility analysis…');

  const body = {
    product:    document.getElementById('feas-product').value,
    customer:   document.getElementById('feas-customer').value,
    quantity:   qty,
    unit:       document.getElementById('feas-unit').value,
    bag_size_kg: parseFloat(document.getElementById('feas-bag').value) || 25,
  };

  const res = await api.checkFeasibility(body);
  btn.disabled = false;
  btn.textContent = '🔍 Check Feasibility';

  if (!res?.ok) {
    result.innerHTML = `<div class="alert alert-danger">Error: ${res?.error}</div>`;
    return;
  }

  const s   = res.data.summary;
  const mat = res.data.material_detail || [];

  const statusColors = {
    'READY FOR SHIPMENT':     { bg: 'var(--success-bg)', border: 'var(--success)', color: 'var(--success-text)', icon: '✅' },
    'CAN PRODUCE':            { bg: 'var(--info-bg)',    border: 'var(--info)',    color: 'var(--info-text)',    icon: '🏭' },
    'RAW MATERIAL SHORTAGE':  { bg: 'var(--danger-bg)',  border: 'var(--danger)',  color: 'var(--danger-text)',  icon: '⚠️' },
  };
  const sc = statusColors[s.feasibility_status] || statusColors['RAW MATERIAL SHORTAGE'];

  const matTable = mat.length ? table([
    { key: 'material',     label: 'Material' },
    { key: 'required_qty', label: 'Required',      render: r => fmt(r.required_qty, 1) },
    { key: 'current_stock',label: 'In Stock',       render: r => fmt(r.current_stock, 1) },
    { key: 'shortage_qty', label: 'Shortage',       render: r => r.shortage_qty > 0 ? `<span style="color:var(--danger-text)">${fmt(r.shortage_qty, 1)}</span>` : '—' },
    { key: 'lead_time_days', label: 'Lead',         render: r => r.lead_time_days ? `${r.lead_time_days}d` : '—', muted: true },
    { key: 'status',       label: 'Status',         render: r => statusBadge(r.status) },
  ], mat) : '';

  result.innerHTML = `
    <div class="feas-result">
      <div class="feas-status-banner" style="background:${sc.bg};border:1px solid ${sc.border};color:${sc.color}">
        ${sc.icon} ${s.feasibility_status}
      </div>

      <div style="display:grid;grid-template-columns:1fr 1fr;gap:.75rem;margin-bottom:1rem;">
        ${kpiCard('Order Demand', fmt(s.order_demand_kg, 0) + ' kg', `${s.order_qty} ${s.unit}`, 'var(--accent)')}
        ${kpiCard('FG Available', fmt(s.available_to_promise_kg, 0) + ' kg', 'Available to promise', s.available_to_promise_kg >= s.order_demand_kg ? 'var(--success)' : 'var(--warn)')}
        ${kpiCard('Production Needed', fmt(s.production_required_kg, 0) + ' kg', `${s.batches_required} batch(es)`, s.production_required_kg > 0 ? 'var(--warn)' : 'var(--success)')}
        ${kpiCard('Earliest Delivery', s.earliest_delivery_date, `${s.estimated_production_days} production day(s)`, 'var(--purple)')}
      </div>

      ${s.estimated_material_cost > 0 ? `
        <div class="alert alert-info" style="margin-bottom:.75rem;">
          💰 Estimated material cost: <strong>₹${fmt(s.estimated_material_cost, 2)}</strong>
          ${s.limiting_material ? ` &nbsp;·&nbsp; Limiting material: <strong>${s.limiting_material}</strong>` : ''}
        </div>` : ''}

      ${matTable ? `
        <div class="section-header" style="margin-top:.75rem;"><span class="section-title">Material Breakdown</span></div>
        ${matTable}` : ''}
    </div>`;
}
