/* ── Production Schedule ─────────────────────────────────────────────────── */

const SCHEDULE_STATUSES = ['Planned', 'Confirmed', 'In Progress', 'Completed', 'Cancelled'];
const SHIFTS = ['Day', 'Night', 'Full Day'];

async function renderSchedule(el) {
  el.innerHTML = `
    <div class="page-header">
      <div class="page-title-group">
        <div class="page-title">Production Schedule</div>
        <div class="page-sub">Plan, track and monitor production runs — material, manpower and time shortages highlighted</div>
      </div>
      <div class="page-actions">
        <button class="btn btn-outline" onclick="scheduleShowAlerts()">⚠ Alerts</button>
        <button class="btn btn-primary" onclick="scheduleOpenForm()">+ New Schedule</button>
      </div>
    </div>
    <div id="schedule-filters" style="display:flex;gap:.5rem;flex-wrap:wrap;margin-bottom:1rem;">
      <select id="sched-filter-status" class="input-sm" onchange="scheduleLoad()" style="min-width:140px;">
        <option value="">All Statuses</option>
        ${SCHEDULE_STATUSES.map(s => `<option>${s}</option>`).join('')}
      </select>
      <select id="sched-filter-product" class="input-sm" style="min-width:180px;" onchange="scheduleLoad()">
        <option value="">All Products</option>
      </select>
      <button class="btn btn-sm btn-outline" onclick="scheduleLoad()">↻ Refresh</button>
    </div>
    <div id="schedule-kpis" style="margin-bottom:1rem;"></div>
    <div id="schedule-gantt" style="margin-bottom:1.5rem;"></div>
    <div id="schedule-table"></div>`;

  await scheduleLoadProducts();
  await scheduleLoad();
}

async function scheduleLoadProducts() {
  const res = await api.getProducts();
  const sel = document.getElementById('sched-filter-product');
  if (res?.ok && sel) {
    (res.data || []).forEach(p => {
      const o = document.createElement('option');
      o.value = o.textContent = p.name;
      sel.appendChild(o);
    });
  }
}

async function scheduleLoad() {
  const status  = document.getElementById('sched-filter-status')?.value || '';
  const product = document.getElementById('sched-filter-product')?.value || '';
  const q = {};
  if (status) q.status = status;

  document.getElementById('schedule-table').innerHTML = loading('Loading schedules…');
  const res = await api.getSchedules(q);
  if (!res?.ok) {
    document.getElementById('schedule-table').innerHTML =
      `<div class="alert alert-danger">Error: ${res?.error}</div>`;
    return;
  }

  let rows = res.data || [];
  if (product) rows = rows.filter(r => r.product === product);

  // Sort by start_date
  rows.sort((a, b) => (a.start_date || '').localeCompare(b.start_date || ''));

  scheduleRenderKPIs(rows);
  scheduleRenderGantt(rows);
  scheduleRenderTable(rows);
}

function scheduleRenderKPIs(rows) {
  const el = document.getElementById('schedule-kpis');
  const active   = rows.filter(r => !['Completed','Cancelled'].includes(r.status));
  const critical = rows.filter(r => r.has_shortage);
  const warnings = rows.filter(r => r.alert_count > 0 && !r.has_shortage);
  const total_kg = rows.filter(r => r.status !== 'Cancelled')
                       .reduce((s, r) => s + parseFloat(r.planned_qty_kg || 0), 0);
  el.innerHTML = `<div class="kpi-grid">
    ${kpiCard('Schedules', rows.length, 'total entries', 'var(--accent)')}
    ${kpiCard('Active', active.length, 'planned / in progress', 'var(--info)')}
    ${kpiCard('Critical Alerts', critical.length, 'material/manpower/time', critical.length > 0 ? 'var(--danger)' : 'var(--success)')}
    ${kpiCard('Warnings', warnings.length, 'capacity / overlap', warnings.length > 0 ? 'var(--warning,#e6a817)' : 'var(--success)')}
    ${kpiCard('Total Planned', fmt(total_kg, 0) + ' kg', 'across all active schedules', 'var(--accent)')}
  </div>`;
}

function scheduleRenderGantt(rows) {
  const el = document.getElementById('schedule-gantt');
  const active = rows.filter(r => r.status !== 'Cancelled' && r.start_date && r.end_date);
  if (active.length === 0) { el.innerHTML = ''; return; }

  const allDates = active.flatMap(r => [r.start_date, r.end_date]).filter(Boolean).sort();
  const minDate  = new Date(allDates[0]);
  const maxDate  = new Date(allDates[allDates.length - 1]);
  // Expand window by a day on each side
  minDate.setDate(minDate.getDate() - 1);
  maxDate.setDate(maxDate.getDate() + 1);
  const totalDays = Math.max((maxDate - minDate) / 86400000, 1);

  const colorMap = {};
  const palette  = ['#4f81e0','#2dc7a4','#e07c4f','#b04fe0','#e0c34f','#e04f72'];
  let ci = 0;
  active.forEach(r => { if (!colorMap[r.product]) colorMap[r.product] = palette[ci++ % palette.length]; });

  const bars = active.map(r => {
    const s   = new Date(r.start_date);
    const e   = new Date(r.end_date);
    const left = ((s - minDate) / 86400000 / totalDays) * 100;
    const width= Math.max(((e - s) / 86400000 + 1) / totalDays * 100, 1.5);
    const color= r.has_shortage ? '#e74c3c' : (r.alert_count > 0 ? '#e6a817' : colorMap[r.product]);
    const label= `${r.schedule_id} · ${r.product} · ${fmt(r.planned_qty_kg,0)} kg`;
    const title= `${r.schedule_id}: ${r.product}\n${r.start_date} → ${r.end_date}\n${fmt(r.planned_qty_kg,0)} kg | ${r.status}` +
                 (r.alert_count > 0 ? `\n⚠ ${r.alert_count} alert(s)` : '');
    return `<div style="position:relative;height:28px;margin-bottom:4px;">
      <div title="${title}" onclick="scheduleEditId('${r.schedule_id}')"
           style="position:absolute;left:${left}%;width:${width}%;min-width:2%;height:100%;
                  background:${color};border-radius:4px;cursor:pointer;display:flex;
                  align-items:center;padding:0 6px;overflow:hidden;white-space:nowrap;
                  color:#fff;font-size:.72rem;font-weight:600;box-sizing:border-box;
                  opacity:${r.status==='Completed'?0.5:1};">
        ${label}
      </div>
    </div>`;
  }).join('');

  // Date ruler
  const labelCount = Math.min(Math.ceil(totalDays), 10);
  const stepDays   = Math.ceil(totalDays / labelCount);
  let ruler = '';
  for (let d = 0; d <= totalDays; d += stepDays) {
    const dt = new Date(minDate); dt.setDate(dt.getDate() + d);
    const pct = (d / totalDays) * 100;
    ruler += `<span style="position:absolute;left:${pct}%;font-size:.68rem;color:var(--text-muted);transform:translateX(-50%);">${dt.toLocaleDateString('en-GB',{day:'numeric',month:'short'})}</span>`;
  }

  el.innerHTML = `
    <div class="card" style="padding:1rem;">
      <div style="font-weight:700;margin-bottom:.75rem;font-size:.85rem;color:var(--text-muted);text-transform:uppercase;letter-spacing:.05em;">
        Timeline View <span style="font-weight:400;font-size:.75rem;margin-left:.5rem;">(click a bar to edit)</span>
        <span style="margin-left:1rem;font-size:.72rem;">
          <span style="background:#e74c3c;color:#fff;padding:1px 6px;border-radius:3px;margin-right:4px;">Critical shortage</span>
          <span style="background:#e6a817;color:#fff;padding:1px 6px;border-radius:3px;margin-right:4px;">Warning</span>
          <span style="background:#4f81e0;color:#fff;padding:1px 6px;border-radius:3px;">OK</span>
        </span>
      </div>
      <div style="position:relative;overflow-x:auto;">
        <div style="position:relative;height:20px;margin-bottom:4px;">${ruler}</div>
        ${bars}
      </div>
    </div>`;
}

function scheduleRenderTable(rows) {
  const el = document.getElementById('schedule-table');
  el.innerHTML = table([
    { key: 'schedule_id',    label: 'ID',           mono: true },
    { key: 'product',        label: 'Product' },
    { key: 'planned_qty_kg', label: 'Qty (kg)',      render: r => fmt(r.planned_qty_kg, 0) },
    { key: 'start_date',     label: 'Start' },
    { key: 'end_date',       label: 'End' },
    { key: 'shift',          label: 'Shift',         muted: true },
    { key: 'manpower',       label: 'Manpower',      render: r => {
      const avail = parseFloat(r.manpower_available || 0);
      const req   = parseFloat(r.manpower_required  || 0);
      if (!req) return `<span class="td-muted">${avail || '—'}</span>`;
      const ok = avail >= req;
      return `<span style="color:${ok?'var(--success-text)':'var(--danger-text)'};font-weight:700;">${avail}/${req}</span>`;
    }},
    { key: 'linked_order_no',label: 'Order',         muted: true, render: r => r.linked_order_no || '—' },
    { key: 'status',         label: 'Status',        render: r => scheduleStatusBadge(r.status) },
    { key: 'alerts',         label: 'Alerts',        render: r => scheduleAlertCell(r) },
    { key: 'actions',        label: '',              render: r => `
      <button class="btn btn-sm btn-outline" onclick="scheduleEditId('${r.schedule_id}')">Edit</button>
      <button class="btn btn-sm btn-outline" style="color:var(--danger-text);" onclick="scheduleDelete('${r.schedule_id}')">✕</button>` },
  ], rows, { emptyIcon: '📅', emptyTitle: 'No schedules yet', emptySub: 'Click "+ New Schedule" to create one' });
}

function scheduleStatusBadge(s) {
  const map = {
    'Planned':     'info',
    'Confirmed':   'info',
    'In Progress': 'warn',
    'Completed':   'ok',
    'Cancelled':   'muted',
  };
  return badge(s, map[s] || 'muted');
}

function scheduleAlertCell(r) {
  if (!r.alert_count) return badge('OK', 'ok');
  const critical = (r.alerts || []).filter(a => a.severity === 'CRITICAL').length;
  const warnings = (r.alerts || []).filter(a => a.severity === 'WARNING').length;
  const parts = [];
  if (critical) parts.push(`<span class="badge badge-danger">⚠ ${critical} critical</span>`);
  if (warnings) parts.push(`<span class="badge badge-warn">⚡ ${warnings} warning</span>`);
  return `<span style="cursor:pointer;" title="${(r.alerts||[]).map(a=>a.message).join('\n')}">${parts.join(' ')}</span>`;
}

// ── Form ──────────────────────────────────────────────────────────────────────

async function scheduleOpenForm(existing) {
  const productsRes = await api.getProducts();
  const ordersRes   = await api.getOrders();
  const products    = (productsRes?.data || []).filter(p => p.status !== 'Inactive');
  const orders      = (ordersRes?.data || []).filter(o => !['Shipped','Closed','Cancelled'].includes(o.status));

  const sid = existing?.schedule_id || '';
  const isEdit = !!existing;

  const productOpts = products.map(p =>
    `<option value="${p.name}" ${existing?.product === p.name ? 'selected' : ''}>${p.name}</option>`
  ).join('');

  const orderOpts = `<option value="">— none —</option>` + orders.map(o =>
    `<option value="${o.order_no}" ${existing?.linked_order_no === o.order_no ? 'selected' : ''}>${o.order_no} · ${o.customer} · ${o.product}</option>`
  ).join('');

  const statusOpts = SCHEDULE_STATUSES.map(s =>
    `<option value="${s}" ${(existing?.status || 'Planned') === s ? 'selected' : ''}>${s}</option>`
  ).join('');

  const shiftOpts = SHIFTS.map(s =>
    `<option value="${s}" ${(existing?.shift || 'Day') === s ? 'selected' : ''}>${s}</option>`
  ).join('');

  const today = new Date().toISOString().split('T')[0];

  openModal(`
    <h2 style="margin:0 0 1.25rem;">${isEdit ? 'Edit Schedule' : 'New Production Schedule'}</h2>
    <div class="form-row">
      ${inputGroup('sform-id', 'Schedule ID', 'text', `placeholder="Auto-generated" value="${sid}" ${isEdit ? 'readonly' : ''}`)}
      <div class="input-group">
        <label>Product</label>
        <select id="sform-product">${productOpts}</select>
      </div>
    </div>
    <div class="form-row">
      ${inputGroup('sform-qty', 'Planned Qty (kg)', 'number', `min="1" step="any" value="${existing?.planned_qty_kg || ''}" placeholder="e.g. 5000"`)}
      <div class="input-group">
        <label>Linked Order (optional)</label>
        <select id="sform-order">${orderOpts}</select>
      </div>
    </div>
    <div class="form-row">
      ${inputGroup('sform-start', 'Start Date', 'date', `value="${existing?.start_date || today}"`)}
      ${inputGroup('sform-end', 'End Date', 'date', `value="${existing?.end_date || today}"`)}
    </div>
    <div class="form-row">
      <div class="input-group">
        <label>Shift</label>
        <select id="sform-shift">${shiftOpts}</select>
      </div>
      <div class="input-group">
        <label>Status</label>
        <select id="sform-status">${statusOpts}</select>
      </div>
    </div>
    <div class="form-row">
      ${inputGroup('sform-manpower-avail', 'Manpower Available (headcount)', 'number', `min="0" step="1" value="${existing?.manpower_available || 0}"`)}
      ${inputGroup('sform-manpower-req', 'Manpower Required (headcount)', 'number', `min="0" step="1" value="${existing?.manpower_required || 0}"`)}
    </div>
    <div class="input-group" style="margin-bottom:.75rem;">
      <label>Notes</label>
      <textarea id="sform-notes" rows="2" style="width:100%;resize:vertical;">${existing?.notes || ''}</textarea>
    </div>
    <div id="sform-alerts" style="margin-bottom:.75rem;"></div>
    <div style="display:flex;gap:.5rem;justify-content:flex-end;margin-top:1rem;">
      <button class="btn btn-outline" onclick="closeModal()">Cancel</button>
      <button class="btn btn-primary" onclick="scheduleSubmit(${isEdit ? `'${sid}'` : 'null'})">
        ${isEdit ? 'Save Changes' : 'Create Schedule'}
      </button>
    </div>`);
}

async function scheduleEditId(id) {
  const res = await api.getSchedules();
  if (!res?.ok) return;
  const sched = (res.data || []).find(s => s.schedule_id === id);
  if (sched) scheduleOpenForm(sched);
}

async function scheduleSubmit(editId) {
  const body = {
    schedule_id:        document.getElementById('sform-id').value.trim(),
    product:            document.getElementById('sform-product').value,
    planned_qty_kg:     parseFloat(document.getElementById('sform-qty').value) || 0,
    linked_order_no:    document.getElementById('sform-order').value,
    start_date:         document.getElementById('sform-start').value,
    end_date:           document.getElementById('sform-end').value,
    shift:              document.getElementById('sform-shift').value,
    status:             document.getElementById('sform-status').value,
    manpower_available: parseFloat(document.getElementById('sform-manpower-avail').value) || 0,
    manpower_required:  parseFloat(document.getElementById('sform-manpower-req').value) || 0,
    notes:              document.getElementById('sform-notes').value.trim(),
  };

  if (!body.product)        { toast('Select a product', 'error'); return; }
  if (!body.planned_qty_kg) { toast('Enter planned quantity', 'error'); return; }
  if (body.start_date > body.end_date) { toast('End date must be on or after start date', 'error'); return; }

  const alertEl = document.getElementById('sform-alerts');
  alertEl.innerHTML = loading('Saving…');

  let res;
  if (editId) {
    res = await api.updateSchedule(editId, body);
  } else {
    res = await api.createSchedule(body);
  }

  if (!res?.ok) {
    alertEl.innerHTML = `<div class="alert alert-danger">${res?.error}</div>`;
    return;
  }

  // Show alerts returned from backend
  const alerts = res.data?.alerts || [];
  if (alerts.length > 0) {
    const alertHtml = alerts.map(a => `
      <div class="alert alert-${a.severity === 'CRITICAL' ? 'danger' : 'warning'}" style="margin-bottom:.4rem;font-size:.82rem;">
        <strong>${a.type.replace(/_/g,' ')}:</strong> ${a.message}
      </div>`).join('');
    alertEl.innerHTML = `<div style="margin-bottom:.5rem;font-weight:600;">⚠ Shortages detected — schedule saved but review needed:</div>${alertHtml}`;
    // Don't close modal — let user see the warnings
    await scheduleLoad();
    toast(`Schedule ${editId ? 'updated' : 'created'} with ${alerts.length} alert(s)`, 'error');
  } else {
    closeModal();
    await scheduleLoad();
    toast(`Schedule ${editId ? 'updated' : 'created'} successfully`, 'success');
  }
}

async function scheduleDelete(id) {
  if (!confirm(`Delete schedule ${id}?`)) return;
  const res = await api.deleteSchedule(id);
  if (res?.ok) {
    toast(`Schedule ${id} deleted`, 'success');
    await scheduleLoad();
  } else {
    toast(res?.error || 'Delete failed', 'error');
  }
}

async function scheduleShowAlerts() {
  openModal(`<h2 style="margin:0 0 1rem;">⚠ Active Schedule Alerts</h2><div id="modal-alert-body">${loading('Loading…')}</div>`);
  const res = await api.scheduleAlerts();
  const el  = document.getElementById('modal-alert-body');
  if (!res?.ok) { el.innerHTML = `<div class="alert alert-danger">${res?.error}</div>`; return; }
  const data = res.data || [];
  if (data.length === 0) {
    el.innerHTML = `<div class="empty-state"><div class="empty-state-icon">✅</div><div class="empty-state-title">No alerts on active schedules</div></div>`;
    return;
  }
  el.innerHTML = data.map(s => `
    <div class="card" style="margin-bottom:.75rem;padding:.9rem;">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:.5rem;">
        <strong>${s.schedule_id} — ${s.product}</strong>
        <span style="font-size:.8rem;color:var(--text-muted);">${s.start_date} → ${s.end_date}</span>
      </div>
      ${s.alerts.map(a => `
        <div style="padding:.4rem .6rem;margin-bottom:.3rem;border-radius:4px;font-size:.82rem;
             background:${a.severity==='CRITICAL'?'var(--danger-bg,#fdf3f3)':'var(--warn-bg,#fffbec)'};
             border-left:3px solid ${a.severity==='CRITICAL'?'var(--danger-text,#c0392b)':'var(--warning,#e6a817)'};">
          <strong>${a.type.replace(/_/g,' ')}</strong>: ${a.message}
        </div>`).join('')}
    </div>`).join('');
}
