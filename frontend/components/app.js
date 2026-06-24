/* ── App Controller ─────────────────────────────────────────────────────── */
const App = window.App = {
  user: null,
  currentPage: null,

  // ── Screens ──────────────────────────────────────────────────────────────
  _splash()  { 
    document.getElementById('splash-screen').classList.remove('hidden');
    document.getElementById('auth-screen').classList.add('hidden');
    document.getElementById('app-shell').classList.add('hidden');
  },
  _showAuth() {
    document.getElementById('splash-screen').classList.add('hidden');
    document.getElementById('auth-screen').classList.remove('hidden');
    document.getElementById('app-shell').classList.add('hidden');
  },
  _showApp()  {
    document.getElementById('splash-screen').classList.add('hidden');
    document.getElementById('auth-screen').classList.add('hidden');
    document.getElementById('app-shell').classList.remove('hidden');
  },

  // ── Init (called once on page load) ──────────────────────────────────────
  async init() {
    App._splash();
    try {
      const res = await api.me();
      if (res && res.ok && res.data && res.data.username) {
        App.boot(res.data);
      } else {
        App._showAuth();
      }
    } catch (e) {
      // Network error or server not ready — show auth, don't reload
      App._showAuth();
    }
  },

  // ── Boot (called after successful login or valid session) ─────────────────
  boot(user) {
    App.user = user;
    App._showApp();

    document.getElementById('user-display').textContent   = user.display_name || user.username;
    document.getElementById('user-role-badge').textContent = user.role || '';
    document.getElementById('user-avatar').textContent    = (user.display_name || user.username || 'U')[0].toUpperCase();

    App._setupNav();
    App.navigate('dashboard');
  },

  // ── Nav ───────────────────────────────────────────────────────────────────
  _setupNav() {
    document.querySelectorAll('.nav-item[data-page]').forEach(btn => {
      // Remove old listeners by cloning
      const fresh = btn.cloneNode(true);
      btn.parentNode.replaceChild(fresh, btn);
      fresh.addEventListener('click', () => {
        App.navigate(fresh.dataset.page);
        document.getElementById('sidebar').classList.remove('mobile-open');
      });
    });

    document.getElementById('sidebar-toggle').onclick = () => {
      document.getElementById('sidebar').classList.toggle('collapsed');
    };

    document.getElementById('btn-signout').onclick = async () => {
      try { await api.logout(); } catch(e) {}
      App.user = null;
      App._showAuth();
      showAuthView('login');
      document.getElementById('page-container').innerHTML = '';
    };
  },

  navigate(page) {
    App.currentPage = page;
    document.querySelectorAll('.nav-item[data-page]').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.page === page);
    });
    const container = document.getElementById('page-container');
    const renderer  = App.pages[page];
    if (renderer) {
      renderer(container);
    } else {
      container.innerHTML = `<div class="empty-state">
        <div class="empty-state-icon">🚧</div>
        <div class="empty-state-title">Page not found: ${page}</div>
      </div>`;
    }
  },

  pages: {
    dashboard:   renderDashboard,
    chat:        renderChat,
    customers:   renderCustomers,
    products:    renderProducts,
    formulas:    renderFormulas,
    materials:   renderMaterials,
    suppliers:   renderSuppliers,
    inventory:   renderInventory,
    feasibility: renderFeasibility,
    orders:      renderOrders,
    schedule:    renderSchedule,
    mrp:         renderMRP,
    backup:      renderBackup,
    settings:    renderSettings,
  },
};

// ── Start ─────────────────────────────────────────────────────────────────
App.init();
