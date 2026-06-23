/* ── Backup & Restore ────────────────────────────────────────────────────── */
function renderBackup(el) {
  el.innerHTML = `
    <div class="page-header">
      <div class="page-title-group">
        <div class="page-title">Backup & Restore</div>
        <div class="page-sub">Export and import factory data</div>
      </div>
    </div>

    <div class="two-col">
      <div>
        <div class="settings-section">
          <div class="settings-section-title">⬇ Download Backups</div>

          <div style="display:flex;flex-direction:column;gap:.75rem;">
            <div style="display:flex;align-items:center;justify-content:space-between;padding:.75rem;background:var(--bg-elevated);border-radius:var(--r-md);border:1px solid var(--border);">
              <div>
                <div style="font-size:.85rem;font-weight:600;color:var(--text-primary)">Master Data</div>
                <div style="font-size:.72rem;color:var(--text-muted)">Products, formulas, inventory, suppliers</div>
              </div>
              <button class="btn btn-secondary btn-sm" onclick="downloadBackup('master')">⬇ Download</button>
            </div>

            <div style="display:flex;align-items:center;justify-content:space-between;padding:.75rem;background:var(--bg-elevated);border-radius:var(--r-md);border:1px solid var(--border);">
              <div>
                <div style="font-size:.85rem;font-weight:600;color:var(--text-primary)">Customer Orders</div>
                <div style="font-size:.72rem;color:var(--text-muted)">All order records</div>
              </div>
              <button class="btn btn-secondary btn-sm" onclick="downloadBackup('orders')">⬇ Download</button>
            </div>

            <div style="display:flex;align-items:center;justify-content:space-between;padding:.75rem;background:var(--bg-elevated);border-radius:var(--r-md);border:1px solid var(--border);">
              <div>
                <div style="font-size:.85rem;font-weight:600;color:var(--text-primary)">Customers</div>
                <div style="font-size:.72rem;color:var(--text-muted)">Customer directory</div>
              </div>
              <button class="btn btn-secondary btn-sm" onclick="downloadBackup('customers')">⬇ Download</button>
            </div>
          </div>
        </div>
      </div>

      <div>
        <div class="settings-section">
          <div class="settings-section-title">⬆ Restore Master Data</div>
          <div class="alert alert-warn" style="margin-bottom:1rem;">
            ⚠️ Restoring will <strong>overwrite</strong> current master data (products, formulas, inventory, suppliers). Orders and customers are not affected.
          </div>

          <div class="drop-zone" id="restore-drop"
            onclick="document.getElementById('restore-file').click()"
            ondragover="event.preventDefault();this.classList.add('over')"
            ondragleave="this.classList.remove('over')"
            ondrop="handleRestoreDrop(event)">
            <div style="font-size:2rem;margin-bottom:.5rem;">📂</div>
            <div style="font-weight:600;color:var(--text-secondary)">Drop master_data.json here</div>
            <div style="font-size:.75rem;margin-top:.25rem;">or click to browse</div>
          </div>
          <input type="file" id="restore-file" accept=".json" style="display:none" onchange="handleRestoreFile(this.files[0])"/>

          <div id="restore-status" style="margin-top:.75rem;"></div>
        </div>
      </div>
    </div>`;
}

async function downloadBackup(type) {
  const endpoints = {
    master:    ['/api/backup/master',    'master_data_backup.json'],
    orders:    ['/api/backup/orders',    'customer_orders_backup.json'],
    customers: ['/api/backup/customers', 'customers_backup.json'],
  };
  const [path, filename] = endpoints[type];
  const res = await fetch(`${API_BASE}${path}`, { credentials: 'include' });
  if (!res.ok) { toast('Download failed', 'error'); return; }
  const blob = await res.blob();
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement('a');
  a.href = url; a.download = filename; a.click();
  URL.revokeObjectURL(url);
  toast(`${type} backup downloaded`, 'success');
}

function handleRestoreDrop(e) {
  e.preventDefault();
  document.getElementById('restore-drop').classList.remove('over');
  const file = e.dataTransfer.files[0];
  if (file) handleRestoreFile(file);
}

async function handleRestoreFile(file) {
  if (!file) return;
  const statusEl = document.getElementById('restore-status');
  if (!file.name.endsWith('.json')) {
    statusEl.innerHTML = '<div class="alert alert-danger">Only .json files are accepted</div>';
    return;
  }
  if (!confirm(`Restore master data from "${file.name}"? This will overwrite current data.`)) return;

  statusEl.innerHTML = loading('Restoring…');
  const form = new FormData();
  form.append('file', file);
  const res = await api.restoreMaster(form);
  if (res?.ok) {
    statusEl.innerHTML = '<div class="alert alert-success">✓ Master data restored successfully</div>';
    toast('Master data restored', 'success');
  } else {
    statusEl.innerHTML = `<div class="alert alert-danger">${res?.error || 'Restore failed'}</div>`;
  }
}
