/* ── Products ────────────────────────────────────────────────────────────── */
async function renderProducts(el) {
  el.innerHTML = `
    <div class="page-header">
      <div class="page-title-group">
        <div class="page-title">Products</div>
        <div class="page-sub">Product catalogue and configurations</div>
      </div>
      <div class="page-actions">
        <button class="btn btn-primary btn-sm" onclick="showProductModal()">+ Add Product</button>
      </div>
    </div>
    <div id="products-content">${loading()}</div>`;
  await loadProductsTable();
}

async function loadProductsTable() {
  const el = document.getElementById('products-content');
  if (!el) return;
  el.innerHTML = loading();
  const res = await api.getProducts();
  if (!res?.ok) { el.innerHTML = `<div class="alert alert-danger">${res?.error}</div>`; return; }

  const t = table([
    { key: 'name', label: 'Product' },
    { key: 'category', label: 'Category', muted: true },
    { key: 'default_bag_size_kg', label: 'Bag Size (kg)', render: r => `${r.default_bag_size_kg} kg` },
    { key: 'status', label: 'Status', render: r => statusBadge(r.status || 'Active') },
    { key: '_actions', label: '', render: r => `
      <div style="display:flex;gap:.4rem;">
        <button class="btn btn-secondary btn-sm" onclick="showProductModal('${r.name.replace(/'/g,"\\'")}')">Edit</button>
        <button class="btn btn-ghost btn-sm" onclick="App.navigate('formulas');window._formulaProduct='${r.name.replace(/'/g,"\\'")}'" title="Manage formula">🧪</button>
        <button class="btn btn-danger btn-sm" onclick="deleteProduct('${r.name.replace(/'/g,"\\'")}')">✕</button>
      </div>` },
  ], res.data, { emptyIcon: '📦', emptyTitle: 'No products defined', emptySub: 'Add products to start managing production' });

  el.innerHTML = `<div class="card">${t}</div>`;
}

function showProductModal(name = null) {
  const isEdit = !!name;
  openModal(`
    <h3 style="margin-bottom:1.25rem;font-size:1rem;font-weight:700;">${isEdit ? 'Edit' : 'Add'} Product</h3>
    <input type="hidden" id="p-old-name" value="${name || ''}"/>
    ${formRow(
      inputGroup('p-name', 'Product Name *', 'text', `placeholder="Cement OPC 53" value="${name || ''}"`),
      inputGroup('p-cat', 'Category', 'text', 'placeholder="Cement"')
    )}
    ${formRow(
      inputGroup('p-bag', 'Bag Size (kg)', 'number', 'min="0.1" step="0.5" value="25"'),
      selectGroup('p-status', 'Status', ['Active', 'Inactive'])
    )}
    <div id="prod-err" class="form-error hidden"></div>
    <div style="display:flex;gap:.5rem;margin-top:1rem;">
      <button class="btn btn-primary" style="flex:1" onclick="submitProduct()">Save Product</button>
      <button class="btn btn-secondary" onclick="closeModal()">Cancel</button>
    </div>`);

  if (isEdit) {
    // Pre-fill from current data
    api.getProducts().then(res => {
      if (!res?.ok) return;
      const p = res.data.find(x => x.name === name);
      if (!p) return;
      document.getElementById('p-cat').value    = p.category || '';
      document.getElementById('p-bag').value    = p.default_bag_size_kg || 25;
      document.getElementById('p-status').value = p.status || 'Active';
    });
  }
}

async function submitProduct() {
  const body = {
    old_name:            document.getElementById('p-old-name').value,
    name:                document.getElementById('p-name').value.trim(),
    category:            document.getElementById('p-cat').value.trim(),
    default_bag_size_kg: parseFloat(document.getElementById('p-bag').value) || 25,
    status:              document.getElementById('p-status').value,
  };
  if (!body.name) { document.getElementById('prod-err').textContent = 'Name required'; document.getElementById('prod-err').classList.remove('hidden'); return; }
  const res = await api.upsertProduct(body);
  if (res?.ok) { closeModal(); toast('Product saved', 'success'); await loadProductsTable(); }
  else { document.getElementById('prod-err').textContent = res?.error; document.getElementById('prod-err').classList.remove('hidden'); }
}

async function deleteProduct(name) {
  if (!confirm(`Delete product "${name}"? This will also remove its formula.`)) return;
  const res = await api.deleteProduct(name);
  if (res?.ok) { toast('Product deleted', 'success'); await loadProductsTable(); }
  else toast(res?.error, 'error');
}
