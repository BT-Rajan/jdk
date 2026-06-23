/* ── Formulas ────────────────────────────────────────────────────────────── */
async function renderFormulas(el) {
  el.innerHTML = `
    <div class="page-header">
      <div class="page-title-group">
        <div class="page-title">Formula Management</div>
        <div class="page-sub">Bill of materials per product</div>
      </div>
    </div>
    <div id="formula-select-row" style="margin-bottom:1rem;max-width:340px;">
      ${loading('Loading products…')}
    </div>
    <div id="formula-content"></div>`;

  const prodRes = await api.getProducts();
  if (!prodRes?.ok) { document.getElementById('formula-select-row').innerHTML = `<div class="alert alert-danger">${prodRes?.error}</div>`; return; }
  const products = prodRes.data.map(p => p.name);
  if (!products.length) { document.getElementById('formula-select-row').innerHTML = `<div class="alert alert-info">No products defined. Add products first.</div>`; return; }

  // Pre-select if coming from Products page
  const defaultProd = window._formulaProduct && products.includes(window._formulaProduct)
    ? window._formulaProduct : products[0];
  window._formulaProduct = null;

  document.getElementById('formula-select-row').innerHTML = `
    <div class="input-group" style="margin:0;">
      <label>Select Product</label>
      <select id="formula-product-select" onchange="loadFormula(this.value)">
        ${products.map(p => `<option value="${p}"${p === defaultProd ? ' selected' : ''}>${p}</option>`).join('')}
      </select>
    </div>`;

  loadFormula(defaultProd);
}

async function loadFormula(product) {
  const el = document.getElementById('formula-content');
  el.innerHTML = loading();

  const [formulaRes, matRes] = await Promise.all([api.getFormula(product), api.getRawMaterials()]);
  if (!formulaRes?.ok) { el.innerHTML = `<div class="alert alert-danger">${formulaRes?.error}</div>`; return; }

  const { formula, total, balanced } = formulaRes.data;
  const materials = (matRes?.data || []).map(m => m.material);

  const totalColor = balanced ? 'var(--success)' : total > 0 ? 'var(--warn)' : 'var(--danger)';

  const formulaTable = table([
    { key: 'material', label: 'Raw Material' },
    { key: 'percentage', label: 'Percentage (%)', render: r => {
      const pct = parseFloat(r.percentage);
      return `<div>${pct.toFixed(2)}%
        <div class="progress-bar" style="width:120px;display:inline-block;margin-left:8px;vertical-align:middle;">
          <div class="progress-fill" style="width:${Math.min(pct,100)}%;background:var(--accent)"></div>
        </div></div>`;
    }},
    { key: '_del', label: '', render: r => `<button class="btn btn-danger btn-sm" onclick="deleteFormulaLine('${product.replace(/'/g,"\\'")}','${r.material.replace(/'/g,"\\'")}')">Remove</button>` },
  ], formula, { emptyIcon: '🧪', emptyTitle: 'No formula lines', emptySub: 'Add raw materials below' });

  const addForm = materials.length ? `
    <div class="card" style="margin-top:1rem;">
      <div class="card-title">Add / Edit Formula Line</div>
      <div class="form-row">
        <div class="input-group">
          <label>Raw Material</label>
          <select id="fm-mat">${materials.map(m => `<option>${m}</option>`).join('')}</select>
        </div>
        ${inputGroup('fm-pct', 'Percentage (%)', 'number', 'min="0.01" max="200" step="0.1" placeholder="25.0"')}
      </div>
      <div id="fm-err" class="form-error hidden"></div>
      <button class="btn btn-primary" onclick="submitFormulaLine('${product.replace(/'/g,"\\'")}')">Save Line</button>
    </div>` : `<div class="alert alert-warn" style="margin-top:1rem;">Add raw materials first before configuring formulas.</div>`;

  el.innerHTML = `
    <div class="two-col" style="align-items:start;">
      <div class="card">
        <div class="section-header">
          <span class="section-title">Formula Lines</span>
          <div class="kpi-card" style="padding:.5rem .85rem;min-width:120px;text-align:center;">
            <div class="kpi-bar" style="background:${totalColor}"></div>
            <div class="kpi-label">Total</div>
            <div class="kpi-value" style="font-size:1.3rem;color:${totalColor}">${total.toFixed(2)}%</div>
            <div class="kpi-sub">${balanced ? '✓ Balanced' : '⚠ Check total'}</div>
          </div>
        </div>
        ${formulaTable}
      </div>
      <div>${addForm}</div>
    </div>`;
}

async function submitFormulaLine(product) {
  const mat = document.getElementById('fm-mat').value;
  const pct = parseFloat(document.getElementById('fm-pct').value);
  const errEl = document.getElementById('fm-err');
  if (!pct || pct <= 0) { errEl.textContent = 'Percentage must be > 0'; errEl.classList.remove('hidden'); return; }
  errEl.classList.add('hidden');
  const res = await api.upsertFormulaLine(product, { material: mat, percentage: pct });
  if (res?.ok) { toast('Formula line saved', 'success'); loadFormula(product); }
  else { errEl.textContent = res?.error; errEl.classList.remove('hidden'); }
}

async function deleteFormulaLine(product, material) {
  if (!confirm(`Remove ${material} from ${product} formula?`)) return;
  const res = await api.deleteFormulaLine(product, material);
  if (res?.ok) { toast('Line removed', 'success'); loadFormula(product); }
  else toast(res?.error, 'error');
}
