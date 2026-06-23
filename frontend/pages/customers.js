/* ── Customers ───────────────────────────────────────────────────────────── */
async function renderCustomers(el) {
  el.innerHTML = `
    <div class="page-header">
      <div class="page-title-group">
        <div class="page-title">Customers</div>
        <div class="page-sub">Manage customer accounts</div>
      </div>
      <div class="page-actions">
        <button class="btn btn-primary btn-sm" onclick="showAddCustomerModal()">+ Add Customer</button>
      </div>
    </div>
    <div id="customers-content">${loading()}</div>`;

  await loadCustomersTable();
}

async function loadCustomersTable() {
  const el = document.getElementById('customers-content');
  if (!el) return;
  el.innerHTML = loading();
  const res = await api.getCustomers();
  if (!res?.ok) { el.innerHTML = `<div class="alert alert-danger">${res?.error}</div>`; return; }

  const t = table([
    { key: 'customer', label: 'Customer' },
    { key: 'customer_type', label: 'Type', render: r => badge(r.customer_type || '—', 'muted') },
    { key: 'delivery_location', label: 'Location', muted: true },
    { key: 'terms', label: 'Payment Terms', muted: true },
    { key: '_actions', label: '', render: r => `<button class="btn btn-danger btn-sm" onclick="deleteCustomer('${r.customer.replace(/'/g,"\\'")}')">Remove</button>` },
  ], res.data, { emptyIcon: '👥', emptyTitle: 'No customers yet', emptySub: 'Add your first customer to get started' });

  el.innerHTML = `<div class="card">${t}</div>`;
}

function showAddCustomerModal() {
  openModal(`
    <h3 style="margin-bottom:1.25rem;font-size:1rem;font-weight:700;">Add Customer</h3>
    ${inputGroup('c-name', 'Customer Name *', 'text', 'placeholder="Acme Corp"')}
    ${selectGroup('c-type', 'Type', ['Construction Company','Material Shop','Government Project','Developer','Other'])}
    ${inputGroup('c-loc', 'Delivery Location', 'text', 'placeholder="Chennai"')}
    ${inputGroup('c-terms', 'Payment Terms', 'text', 'placeholder="Net 30"')}
    <div id="cust-err" class="form-error hidden"></div>
    <div style="display:flex;gap:.5rem;margin-top:1rem;">
      <button class="btn btn-primary" style="flex:1" onclick="submitAddCustomer()">Add Customer</button>
      <button class="btn btn-secondary" onclick="closeModal()">Cancel</button>
    </div>`);
}

async function submitAddCustomer() {
  const body = {
    customer:          document.getElementById('c-name').value.trim(),
    customer_type:     document.getElementById('c-type').value,
    delivery_location: document.getElementById('c-loc').value.trim(),
    terms:             document.getElementById('c-terms').value.trim(),
  };
  if (!body.customer) { document.getElementById('cust-err').textContent = 'Name required'; document.getElementById('cust-err').classList.remove('hidden'); return; }
  const res = await api.addCustomer(body);
  if (res?.ok) { closeModal(); toast('Customer added', 'success'); await loadCustomersTable(); }
  else { document.getElementById('cust-err').textContent = res?.error; document.getElementById('cust-err').classList.remove('hidden'); }
}

async function deleteCustomer(name) {
  if (!confirm(`Remove customer "${name}"?`)) return;
  const res = await api.deleteCustomer(name);
  if (res?.ok) { toast('Customer removed', 'success'); await loadCustomersTable(); }
  else toast(res?.error, 'error');
}
