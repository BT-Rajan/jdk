/* ── JDK UI Utilities ────────────────────────────────────────────────────── */

function toast(msg, type = 'info', duration = 3500) {
  const icons = { success: '✓', error: '✕', info: 'ℹ' };
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.innerHTML = `<span>${icons[type] || 'ℹ'}</span><span>${msg}</span>`;
  document.getElementById('toast-container').appendChild(el);
  setTimeout(() => el.remove(), duration);
}

function openModal(html) {
  document.getElementById('modal-body').innerHTML = html;
  document.getElementById('modal-overlay').classList.remove('hidden');
}

function closeModal() {
  document.getElementById('modal-overlay').classList.add('hidden');
  document.getElementById('modal-body').innerHTML = '';
}

document.getElementById('modal-overlay').addEventListener('click', e => {
  if (e.target === document.getElementById('modal-overlay')) closeModal();
});

function loading(text = 'Loading…') {
  return `<div class="loading"><div class="spinner"></div>${text}</div>`;
}

function emptyState(icon, title, sub = '') {
  return `<div class="empty-state">
    <div class="empty-state-icon">${icon}</div>
    <div class="empty-state-title">${title}</div>
    ${sub ? `<div class="empty-state-sub">${sub}</div>` : ''}
  </div>`;
}

function badge(text, style = 'muted') {
  return `<span class="badge badge-${style}">${text}</span>`;
}

function statusBadge(status) {
  const map = {
    'Open':               'info',
    'Approved':           'info',
    'Production Planned': 'warn',
    'In Production':      'warn',
    'Ready For Shipment': 'ok',
    'Shipped':            'ok',
    'Closed':             'muted',
    'Cancelled':          'danger',
    'OK':                 'ok',
    'LOW':                'warn',
    'CRITICAL':           'danger',
    'SHORTAGE':           'danger',
    'CAN PRODUCE':        'info',
    'READY FOR SHIPMENT': 'ok',
    'RAW MATERIAL SHORTAGE': 'danger',
    'Active':             'ok',
    'Inactive':           'muted',
  };
  return badge(status, map[status] || 'muted');
}

function priorityBadge(p) {
  const map = { Critical: 'danger', High: 'warn', Normal: 'info', Low: 'muted' };
  return badge(p, map[p] || 'muted');
}

function fmt(n, dec = 1) {
  const f = parseFloat(n);
  if (isNaN(f)) return '—';
  return f.toLocaleString('en-US', { minimumFractionDigits: dec, maximumFractionDigits: dec });
}

function fmtDate(d) {
  if (!d) return '—';
  return new Date(d).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
}

function table(headers, rows, opts = {}) {
  if (!rows || rows.length === 0) {
    return emptyState(opts.emptyIcon || '📭', opts.emptyTitle || 'No data', opts.emptySub || '');
  }
  const ths = headers.map(h => `<th>${h.label}</th>`).join('');
  const trs = rows.map(row => {
    const tds = headers.map(h => {
      let val = h.render ? h.render(row) : (row[h.key] ?? '—');
      const cls = h.mono ? 'td-mono' : h.muted ? 'td-muted' : '';
      return `<td${cls ? ` class="${cls}"` : ''}>${val}</td>`;
    }).join('');
    return `<tr>${tds}</tr>`;
  }).join('');
  return `<div class="table-wrap"><table><thead><tr>${ths}</tr></thead><tbody>${trs}</tbody></table></div>`;
}

function kpiCard(label, value, sub, color = 'var(--accent)') {
  return `<div class="kpi-card">
    <div class="kpi-bar" style="background:${color}"></div>
    <div class="kpi-label">${label}</div>
    <div class="kpi-value">${value}</div>
    ${sub ? `<div class="kpi-sub">${sub}</div>` : ''}
  </div>`;
}

function formRow(...fields) {
  return `<div class="form-row">${fields.join('')}</div>`;
}

function inputGroup(id, label, type = 'text', extra = '') {
  return `<div class="input-group">
    <label for="${id}">${label}</label>
    <input id="${id}" type="${type}" ${extra}/>
  </div>`;
}

function selectGroup(id, label, options, selected = '') {
  const opts = options.map(o => {
    const val = typeof o === 'string' ? o : o.value;
    const lbl = typeof o === 'string' ? o : o.label;
    return `<option value="${val}"${val === selected ? ' selected' : ''}>${lbl}</option>`;
  }).join('');
  return `<div class="input-group">
    <label for="${id}">${label}</label>
    <select id="${id}">${opts}</select>
  </div>`;
}

// Tab system
function tabs(items) {
  const btns = items.map((t, i) =>
    `<button class="tab-btn${i === 0 ? ' active' : ''}" data-tab="${t.id}">${t.label}</button>`
  ).join('');
  const panels = items.map((t, i) =>
    `<div class="tab-panel${i === 0 ? ' active' : ''}" id="tab-${t.id}">${t.content}</div>`
  ).join('');
  return `<div class="tabs" id="tab-strip">${btns}</div>${panels}`;
}

document.addEventListener('click', e => {
  const btn = e.target.closest('.tab-btn');
  if (!btn) return;
  const strip = btn.closest('.tabs');
  if (!strip) return;
  strip.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  const tabId = btn.dataset.tab;
  const container = strip.parentElement;
  container.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  const panel = container.querySelector(`#tab-${tabId}`);
  if (panel) panel.classList.add('active');
});
