/* ── Raw Materials ───────────────────────────────────────────────────────── */
async function renderMaterials(el) {
  el.innerHTML = `
    <div class="page-header">
      <div class="page-title-group">
        <div class="page-title">Raw Materials</div>
        <div class="page-sub">Stock levels, reorder settings, and lead times</div>
      </div>
      <div class="page-actions">
        <button class="btn btn-primary btn-sm" onclick="showMaterialModal()">+ Add Material</button>
      </div>
    </div>
    <div id="materials-content">${loading()}</div>`;
  await loadMaterialsTable();
}

async function loadMaterialsTable() {
  const el = document.getElementById('materials-content');
  if (!el) return;
  el.innerHTML = loading();
  const res = await api.getRawMaterials();
  if (!res?.ok) { el.innerHTML = `<div class="alert alert-danger">${res?.error}</div>`; return; }

  const t = table([
    { key: 'material', label: 'Material' },
    { key: 'current_stock', label: 'Current Stock', render: r => fmt(r.current_stock, 0) },
    { key: 'minimum_stock', label: 'Min Stock', render: r => fmt(r.minimum_stock, 0), muted: true },
    { key: 'reorder_point', label: 'Reorder At', render: r => fmt(r.reorder_point, 0), muted: true },
    { key: 'lead_time_days', label: 'Lead (days)', render: r => `${r.lead_time_days}d`, muted: true },
    { key: 'status', label: 'Status', render: r => statusBadge(r.status) },
    { key: '_actions', label: '', render: r => `
      <div style="display:flex;gap:.4rem;">
        <button class="btn btn-secondary btn-sm" onclick="showMaterialModal('${r.material.replace(/'/g,"\\'")}', ${JSON.stringify(r).replace(/"/g,'&quot;')})">Edit</button>
        <button class="btn btn-danger btn-sm" onclick="deleteMaterial('${r.material.replace(/'/g,"\\'")}')">✕</button>
      </div>` },
  ], res.data, { emptyIcon: '🪨', emptyTitle: 'No raw materials', emptySub: 'Add materials to manage inventory and run MRP' });

  el.innerHTML = `<div class="card">${t}</div>`;
}

function showMaterialModal(name = null, existing = null) {
  openModal(`
    <h3 style="margin-bottom:1.25rem;font-size:1rem;font-weight:700;">${name ? 'Edit' : 'Add'} Raw Material</h3>
    <input type="hidden" id="rm-orig-name" value="${name || ''}"/>
    ${formRow(
      inputGroup('rm-name', 'Material Name *', 'text', `placeholder="Limestone" value="${name || ''}"`),
      selectGroup('rm-unit', 'Unit', ['kg','pcs','liter','ton'], existing?.unit || 'kg')
    )}
    ${formRow(
      inputGroup('rm-stock', 'Current Stock', 'number', `min="0" step="0.1" value="${existing?.current_stock ?? 0}"`),
      inputGroup('rm-min',   'Minimum Stock', 'number', `min="0" step="0.1" value="${existing?.minimum_stock ?? 0}"`)
    )}
    ${formRow(
      inputGroup('rm-reorder',  'Reorder Point',    'number', `min="0" step="0.1" value="${existing?.reorder_point ?? 0}"`),
      inputGroup('rm-lead',     'Lead Time (days)', 'number', `min="0" step="1" value="${existing?.lead_time_days ?? 0}"`)
    )}
    <div id="rm-err" class="form-error hidden"></div>
    <div style="display:flex;gap:.5rem;margin-top:1rem;">
      <button class="btn btn-primary" style="flex:1" onclick="submitMaterial()">Save Material</button>
      <button class="btn btn-secondary" onclick="closeModal()">Cancel</button>
    </div>`);
}

async function submitMaterial() {
  const body = {
    name:          document.getElementById('rm-name').value.trim(),
    unit:          document.getElementById('rm-unit').value,
    current_stock: parseFloat(document.getElementById('rm-stock').value) || 0,
    minimum_stock: parseFloat(document.getElementById('rm-min').value)   || 0,
    reorder_point: parseFloat(document.getElementById('rm-reorder').value) || 0,
    lead_time_days:parseFloat(document.getElementById('rm-lead').value)  || 0,
  };
  if (!body.name) { document.getElementById('rm-err').textContent = 'Name required'; document.getElementById('rm-err').classList.remove('hidden'); return; }
  const res = await api.upsertMaterial(body);
  if (res?.ok) { closeModal(); toast('Material saved', 'success'); await loadMaterialsTable(); }
  else { document.getElementById('rm-err').textContent = res?.error; document.getElementById('rm-err').classList.remove('hidden'); }
}

async function deleteMaterial(name) {
  if (!confirm(`Delete material "${name}"? This will also remove its inventory data.`)) return;
  const res = await api.deleteMaterial(name);
  if (res?.ok) { toast('Material deleted', 'success'); await loadMaterialsTable(); }
  else toast(res?.error, 'error');
}
