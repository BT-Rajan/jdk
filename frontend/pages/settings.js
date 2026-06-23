/* ── Settings ────────────────────────────────────────────────────────────── */
async function renderSettings(el) {
  el.innerHTML = `
    <div class="page-header">
      <div class="page-title-group">
        <div class="page-title">Settings</div>
        <div class="page-sub">AI configuration, production parameters, and user management</div>
      </div>
    </div>
    <div id="settings-content">${loading()}</div>`;
  await loadSettingsContent();
}

async function loadSettingsContent() {
  const el = document.getElementById('settings-content');
  if (!el) return;

  const res = await api.getSettings();
  const s = res?.ok ? res.data : {};

  el.innerHTML = tabs([
    {
      id: 'ai',
      label: '🤖 AI / DeepSeek',
      content: `
        <div class="settings-section" style="margin-top:.75rem;max-width:600px;">
          <div class="settings-section-title">💬 DeepSeek AI Configuration</div>
          <div class="alert alert-info" style="margin-bottom:1rem;">
            DeepSeek powers the AI Chat assistant. Get your API key at <a href="https://platform.deepseek.com" target="_blank" style="color:var(--info-text)">platform.deepseek.com</a>
          </div>
          <div class="input-group">
            <label>DeepSeek API Key</label>
            <div style="position:relative;">
              <input id="s-apikey" type="password" value="${s.deepseek_api_key || ''}" placeholder="sk-..." autocomplete="new-password"/>
              <button onclick="toggleApiKeyVisibility()" style="position:absolute;right:.6rem;top:50%;transform:translateY(-50%);background:none;border:none;color:var(--text-muted);cursor:pointer;font-size:.8rem;">👁</button>
            </div>
          </div>
          ${formRow(
            `<div class="input-group">
              <label>Model</label>
              <select id="s-model">
                <option value="deepseek-chat" ${(s.deepseek_model||'deepseek-chat')==='deepseek-chat'?'selected':''}>deepseek-chat</option>
                <option value="deepseek-reasoner" ${s.deepseek_model==='deepseek-reasoner'?'selected':''}>deepseek-reasoner</option>
              </select>
            </div>`,
            `<div class="input-group">
              <label>Base URL</label>
              <input id="s-baseurl" type="text" value="${s.deepseek_base_url || 'https://api.deepseek.com'}" placeholder="https://api.deepseek.com"/>
            </div>`
          )}
          <div id="ai-err" class="form-error hidden"></div>
          <div id="ai-ok"  class="form-success hidden"></div>
          <button class="btn btn-primary" onclick="saveAISettings()">Save AI Settings</button>
        </div>`
    },
    {
      id: 'production',
      label: '🏭 Production',
      content: `
        <div class="settings-section" style="margin-top:.75rem;max-width:600px;">
          <div class="settings-section-title">⚙ Production Parameters</div>
          ${formRow(
            inputGroup('s-batch',    'Batch Size (kg)',           'number', `min="1" value="${s.batch_size_kg || 1000}"`),
            inputGroup('s-capacity', 'Daily Capacity (kg)',       'number', `min="1" value="${s.daily_capacity_kg || 20000}"`)
          )}
          ${inputGroup('s-horizon', 'Planning Horizon (days)', 'number', `min="1" value="${s.planning_horizon_days || 30}"`)}
          ${inputGroup('s-appname', 'App Name',                'text',   `value="${s.app_name || 'JDK Smart Factory'}"`)}
          <div id="prod-set-err" class="form-error hidden"></div>
          <div id="prod-set-ok"  class="form-success hidden"></div>
          <button class="btn btn-primary" onclick="saveProdSettings()">Save Production Settings</button>
        </div>`
    },
    {
      id: 'users',
      label: '👥 User Management',
      content: `
        <div class="settings-section" style="margin-top:.75rem;">
          <div class="settings-section-title">Role Permissions</div>
          <div class="table-wrap">
            <table>
              <thead><tr>
                <th>Role</th><th>Read</th><th>Write</th><th>Orders</th><th>Inventory</th><th>Admin</th>
              </tr></thead>
              <tbody>
                ${[
                  ['Super Admin',        '✓','✓','✓','✓','✓'],
                  ['Production Planner', '✓','✓','✓','✗','✗'],
                  ['Warehouse User',     '✓','✗','✗','✓','✗'],
                  ['Purchasing User',    '✓','✓','✗','✗','✗'],
                  ['Management Viewer',  '✓','✗','✗','✗','✗'],
                ].map(([role,...perms]) => `<tr>
                  <td><strong>${role}</strong></td>
                  ${perms.map(p => `<td style="color:${p==='✓'?'var(--success-text)':'var(--text-muted)'}">${p}</td>`).join('')}
                </tr>`).join('')}
              </tbody>
            </table>
          </div>
          <div class="alert alert-info" style="margin-top:1rem;">
            New accounts created via sign-up get <strong>Management Viewer</strong> role. An admin must update roles directly in <code style="font-family:var(--font-mono);font-size:.8rem;">config/auth.json</code>.
          </div>
        </div>`
    },
    {
      id: 'about',
      label: 'ℹ About',
      content: `
        <div class="settings-section" style="margin-top:.75rem;max-width:500px;">
          <div class="settings-section-title">ℹ Platform Info</div>
          <div style="display:flex;flex-direction:column;gap:.6rem;font-size:.85rem;">
            ${[
              ['Platform', 'JDK Smart Factory'],
              ['Version',  '2.0.0'],
              ['Backend',  'Flask + Python'],
              ['Frontend', 'Vanilla JS SPA'],
              ['AI Engine','DeepSeek Chat API'],
              ['Storage',  'JSON flat-file (upgradeable to DB)'],
            ].map(([k,v]) => `<div style="display:flex;gap:1rem;padding:.5rem;border-radius:var(--r-sm);background:var(--bg-elevated);">
              <span style="color:var(--text-muted);min-width:100px;">${k}</span>
              <span style="color:var(--text-primary);font-weight:500;">${v}</span>
            </div>`).join('')}
          </div>
        </div>`
    },
  ]);
}

function toggleApiKeyVisibility() {
  const input = document.getElementById('s-apikey');
  input.type = input.type === 'password' ? 'text' : 'password';
}

async function saveAISettings() {
  const body = {
    deepseek_api_key:  document.getElementById('s-apikey').value.trim(),
    deepseek_model:    document.getElementById('s-model').value,
    deepseek_base_url: document.getElementById('s-baseurl').value.trim(),
  };
  const res = await api.saveSettings(body);
  const errEl = document.getElementById('ai-err');
  const okEl  = document.getElementById('ai-ok');
  if (res?.ok) {
    okEl.textContent = '✓ AI settings saved';
    okEl.classList.remove('hidden');
    errEl.classList.add('hidden');
    toast('AI settings saved', 'success');
    setTimeout(() => okEl.classList.add('hidden'), 3000);
  } else {
    errEl.textContent = res?.error || 'Save failed';
    errEl.classList.remove('hidden');
    okEl.classList.add('hidden');
  }
}

async function saveProdSettings() {
  const body = {
    batch_size_kg:        parseFloat(document.getElementById('s-batch').value)    || 1000,
    daily_capacity_kg:    parseFloat(document.getElementById('s-capacity').value) || 20000,
    planning_horizon_days:parseInt(document.getElementById('s-horizon').value)    || 30,
    app_name:             document.getElementById('s-appname').value.trim(),
  };
  const res = await api.saveSettings(body);
  const errEl = document.getElementById('prod-set-err');
  const okEl  = document.getElementById('prod-set-ok');
  if (res?.ok) {
    okEl.textContent = '✓ Production settings saved';
    okEl.classList.remove('hidden');
    errEl.classList.add('hidden');
    toast('Production settings saved', 'success');
    setTimeout(() => okEl.classList.add('hidden'), 3000);
  } else {
    errEl.textContent = res?.error || 'Save failed';
    errEl.classList.remove('hidden');
    okEl.classList.add('hidden');
  }
}
