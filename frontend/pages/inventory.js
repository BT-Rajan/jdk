/* ── Inventory ───────────────────────────────────────────────────────────── */
async function renderInventory(el) {
  el.innerHTML = `
    <div class="page-header">
      <div class="page-title-group">
        <div class="page-title">Inventory</div>
        <div class="page-sub">Finished goods stock and raw material health</div>
      </div>
      <div class="page-actions">
        <button class="btn btn-primary btn-sm" onclick="showUpdateFGModal()">+ Update Finished Goods</button>
      </div>
    </div>
    <div id="inv-content">${loading()}</div>`;
  await loadInventoryContent();
}

async function loadInventoryContent() {
  const el = document.getElementById('inv-content');
  if (!el) return;
  el.innerHTML = loading();

  const [fgRes, healthRes] = await Promise.all([api.getFG(), api.inventoryHealth()]);

  const fgTable = table([
    { key: 'product',        label: 'Product' },
    { key: 'category',       label: 'Category', muted: true },
    { key: 'available_kg',   label: 'Available (kg)', render: r => fmt(r.available_kg, 0) },
    { key: 'available_bags', label: 'Bags',           render: r => fmt(r.available_bags, 0) },
    { key: '_edit', label: '', render: r => `<button class="btn btn-secondary btn-sm" onclick="showUpdateFGModal('${r.product.replace(/'/g,"\\'")}', ${r.available_kg}, ${r.available_bags})">Update</button>` },
  ], fgRes?.data || [], { emptyIcon: '📦', emptyTitle: 'No finished goods data' });

  const rawTable = table([
    { key: 'material',           label: 'Material' },
    { key: 'current_stock',      label: 'Current (kg)',  render: r => fmt(r.current_stock, 0) },
    { key: 'minimum_stock',      label: 'Min',           render: r => fmt(r.minimum_stock, 0), muted: true },
    { key: 'reorder_point',      label: 'Reorder At',    render: r => fmt(r.reorder_point, 0), muted: true },
    { key: 'stock_vs_reorder_%', label: 'Stock vs Reorder', render: r => {
      const pct = r['stock_vs_reorder_%'] ?? 0;
      const color = pct >= 100 ? 'var(--success)' : pct >= 50 ? 'var(--warn)' : 'var(--danger)';
      return `<div style="display:flex;align-items:center;gap:8px;">
        <span style="font-family:var(--font-mono);font-size:.75rem;">${pct}%</span>
        <div class="progress-bar" style="width:80px;flex-shrink:0;">
          <div class="progress-fill" style="width:${Math.min(pct,100)}%;background:${color}"></div>
        </div>
      </div>`;
    }},
    { key: 'lead_time_days', label: 'Lead (days)', muted: true },
    { key: 'status',         label: 'Status', render: r => statusBadge(r.status) },
  ], healthRes?.data || [], { emptyIcon: '🪨', emptyTitle: 'No raw material inventory' });

  el.innerHTML = `
    <div class="card" style="margin-bottom:1rem;">
      <div class="section-header">
        <span class="section-title">Finished Goods Stock</span>
      </div>
      ${fgTable}
    </div>
    <div class="card">
      <div class="section-header">
        <span class="section-title">Raw Material Health</span>
        <button class="btn btn-ghost btn-sm" onclick="App.navigate('materials')">Manage levels →</button>
      </div>
      ${rawTable}
    </div>`;
}

async function showUpdateFGModal(product = '', kg = 0, bags = 0) {
  const prodRes = await api.getProducts();
  const products = prodRes?.ok ? prodRes.data.map(p => p.name) : [];

  openModal(`
    <h3 style="margin-bottom:1.25rem;font-size:1rem;font-weight:700;">Update Finished Goods</h3>
    ${product
      ? `<div class="input-group"><label>Product</label><input type="text" value="${product}" disabled/></div>`
      : selectGroup('fg-product', 'Product *', products)
    }
    <input type="hidden" id="fg-product-hidden" value="${product}"/>
    ${formRow(
      inputGroup('fg-kg',   'Available (kg)',   'number', `min="0" step="0.1" value="${kg}"`),
      inputGroup('fg-bags', 'Available (bags)', 'number', `min="0" step="1"   value="${bags}"`)
    )}
    <div id="fg-err" class="form-error hidden"></div>
    <div style="display:flex;gap:.5rem;margin-top:1rem;">
      <button class="btn btn-primary" style="flex:1" onclick="submitFGUpdate('${product}')">Update Stock</button>
      <button class="btn btn-secondary" onclick="closeModal()">Cancel</button>
    </div>`);
}

async function submitFGUpdate(presetProduct) {
  const product = presetProduct || document.getElementById('fg-product')?.value || document.getElementById('fg-product-hidden')?.value;
  const body = {
    product,
    available_kg:   parseFloat(document.getElementById('fg-kg').value)   || 0,
    available_bags: parseFloat(document.getElementById('fg-bags').value) || 0,
  };
  if (!body.product) {
    document.getElementById('fg-err').textContent = 'Product required';
    document.getElementById('fg-err').classList.remove('hidden');
    return;
  }
  const res = await api.updateFG(body);
  if (res?.ok) { closeModal(); toast('Stock updated', 'success'); await loadInventoryContent(); }
  else { document.getElementById('fg-err').textContent = res?.error; document.getElementById('fg-err').classList.remove('hidden'); }
}
