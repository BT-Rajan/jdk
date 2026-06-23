/* ── App Controller ─────────────────────────────────────────────────────── */
const App = window.App = {
  user: null,
  currentPage: null,

  async init() {
    // Try to restore existing session cookie — show auth screen on any failure
    try {
      const res = await api.me();
      if (res?.ok && res.data) {
        App.boot(res.data);
      } else {
        App.showAuth();
      }
    } catch (e) {
      App.showAuth();
    }
  },

  showAuth() {
    document.getElementById('auth-screen').classList.remove('hidden');
    document.getElementById('app-shell').classList.add('hidden');
  },

  boot(user) {
    App.user = user;
    document.getElementById('auth-screen').classList.add('hidden');
    document.getElementById('app-shell').classList.remove('hidden');

    // Set user info in sidebar
    document.getElementById('user-display').textContent = user.display_name || user.username;
    document.getElementById('user-role-badge').textContent = user.role || '';
    document.getElementById('user-avatar').textContent = (user.display_name || user.username || 'U')[0].toUpperCase();

    App.setupNav();
    App.navigate('dashboard');
  },

  setupNav() {
    // Nav items
    document.querySelectorAll('.nav-item[data-page]').forEach(btn => {
      btn.addEventListener('click', () => {
        App.navigate(btn.dataset.page);
        // Mobile: close sidebar
        document.getElementById('sidebar').classList.remove('mobile-open');
      });
    });

    // Sidebar toggle
    document.getElementById('sidebar-toggle').addEventListener('click', () => {
      document.getElementById('sidebar').classList.toggle('collapsed');
    });

    // Sign out
    document.getElementById('btn-signout').addEventListener('click', async () => {
      await api.logout();
      App.user = null;
      document.getElementById('app-shell').classList.add('hidden');
      document.getElementById('auth-screen').classList.remove('hidden');
      showAuthView('login');
      document.getElementById('page-container').innerHTML = '';
      sessionStorage.clear();
    });
  },

  navigate(page) {
    App.currentPage = page;

    // Update active nav
    document.querySelectorAll('.nav-item[data-page]').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.page === page);
    });

    // Render page
    const container = document.getElementById('page-container');
    const renderer = App.pages[page];
    if (renderer) {
      renderer(container);
    } else {
      container.innerHTML = `<div class="empty-state"><div class="empty-state-icon">🚧</div><div class="empty-state-title">Page not found</div></div>`;
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
    mrp:         renderMRP,
    backup:      renderBackup,
    settings:    renderSettings,
  },
};

// Start
App.init();
