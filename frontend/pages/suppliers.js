/* ── Suppliers ───────────────────────────────────────────────────────────── */
async function renderSuppliers(el) {
  el.innerHTML = `
    <div class="page-header">
      <div class="page-title-group">
        <div class="page-title">Suppliers</div>
        <div class="page-sub">Vendor pricing, lead times and sourcing</div>
      </div>
      <div class="page-actions">
        <button class="btn btn-primary btn-sm" onclick="showSupplierModal()">+ Add Supplier</button>
      </div>
    </div>
    <div id="suppliers-content">${loading()}</div>`;
  await loadSuppliersTable();
}

async function loadSuppliersTable() {
  const el = document.getElementById('suppliers-content');
  if (!el) return;
  el.innerHTML = loading();
  const res = await api.getSuppliers();
  if (!res?.ok) { el.innerHTML = `<div class="alert alert-danger">${res?.error}</div>`; return; }

  const t = table([
    { key: 'material',          label: 'Material' },
    { key: 'supplier_name',     label: 'Supplier' },
    { key: 'price',             label: 'Price/kg', render: r => r.price ? `₹${fmt(r.price, 2)}` : '—' },
    { key: 'lead_time_days',    label: 'Lead (days)', render: r => r.lead_time_days ? `${r.lead_time_days}d` : '—', muted: true },
    { key: 'minimum_order_qty', label: 'MOQ (kg)', render: r => fmt(r.minimum_order_qty, 0), muted: true },
    { key: 'payment_terms',     label: 'Terms', muted: true },
    { key: 'delivery_cost',     label: 'Delivery Cost', render: r => r.delivery_cost ? `₹${fmt(r.delivery_cost, 2)}` : '—', muted: true },
    { key: '_del', label: '', render: r => `<button class="btn btn-danger btn-sm" onclick="deleteSupplier('${r.material.replace(/'/g,"\\'")}','${r.supplier_name.replace(/'/g,"\\'")}')">Remove</button>` },
  ], res.data, { emptyIcon: '🚚', emptyTitle: 'No suppliers yet', emptySub: 'Add suppliers to enable cost calculation in MRP' });

  el.innerHTML = `<div class="card">${t}</div>`;
}

async function showSupplierModal() {
  const matRes = await api.getRawMaterials();
  const materials = matRes?.ok ? matRes.data.map(m => m.material) : [];

  openModal(`
    <h3 style="margin-bottom:1.25rem;font-size:1rem;font-weight:700;">Add Supplier</h3>
    ${selectGroup('sup-mat', 'Raw Material *', materials.length ? materials : ['(Add materials first)'])}
    ${inputGroup('sup-name', 'Supplier Name *', 'text', 'placeholder="Ramco Cements Ltd"')}
    ${formRow(
      inputGroup('sup-price', 'Price per kg (₹)', 'number', 'min="0" step="0.01" placeholder="0.00"'),
      inputGroup('sup-lead',  'Lead Time (days)',  'number', 'min="0" step="1"   placeholder="7"')
    )}
    ${formRow(
      inputGroup('sup-moq',   'Min Order Qty (kg)', 'number', 'min="0" step="1" placeholder="1000"'),
      inputGroup('sup-del',   'Delivery Cost (₹)',  'number', 'min="0" step="0.01" placeholder="0.00"')
    )}
    ${inputGroup('sup-terms', 'Payment Terms', 'text', 'placeholder="Net 30"')}
    <div id="sup-err" class="form-error hidden"></div>
    <div style="display:flex;gap:.5rem;margin-top:1rem;">
      <button class="btn btn-primary" style="flex:1" onclick="submitSupplier()">Add Supplier</button>
      <button class="btn btn-secondary" onclick="closeModal()">Cancel</button>
    </div>`);
}

async function submitSupplier() {
  const body = {
    material:          document.getElementById('sup-mat').value,
    supplier_name:     document.getElementById('sup-name').value.trim(),
    price:             parseFloat(document.getElementById('sup-price').value) || 0,
    lead_time_days:    parseFloat(document.getElementById('sup-lead').value)  || 0,
    minimum_order_qty: parseFloat(document.getElementById('sup-moq').value)   || 0,
    delivery_cost:     parseFloat(document.getElementById('sup-del').value)   || 0,
    payment_terms:     document.getElementById('sup-terms').value.trim(),
  };
  if (!body.supplier_name) {
    document.getElementById('sup-err').textContent = 'Supplier name required';
    document.getElementById('sup-err').classList.remove('hidden');
    return;
  }
  const res = await api.addSupplier(body);
  if (res?.ok) { closeModal(); toast('Supplier added', 'success'); await loadSuppliersTable(); }
  else { document.getElementById('sup-err').textContent = res?.error; document.getElementById('sup-err').classList.remove('hidden'); }
}

async function deleteSupplier(material, name) {
  if (!confirm(`Remove supplier "${name}" for ${material}?`)) return;
  const res = await api.deleteSupplier(material, name);
  if (res?.ok) { toast('Supplier removed', 'success'); await loadSuppliersTable(); }
  else toast(res?.error, 'error');
}
