/* ── Auth ────────────────────────────────────────────────────────────────── */

function showAuthView(view) {
  document.querySelectorAll('.auth-view').forEach(v => v.classList.remove('active'));
  const target = document.getElementById('view-' + view);
  if (target) target.classList.add('active');
  // Clear all error/success messages
  ['login-error','signup-error','signup-success','forgot-error','forgot-success'].forEach(id => {
    const el = document.getElementById(id);
    if (el) { el.textContent = ''; el.classList.add('hidden'); }
  });
}

function _setFormErr(id, msg) {
  const el = document.getElementById(id);
  if (el) { el.textContent = msg; el.classList.remove('hidden'); }
}

function _setFormOk(id, msg) {
  const el = document.getElementById(id);
  if (el) { el.textContent = msg; el.classList.remove('hidden'); }
}

// ── Login ────────────────────────────────────────────────────────────────
document.getElementById('btn-login').addEventListener('click', async () => {
  const btn = document.getElementById('btn-login');
  const u   = document.getElementById('login-user').value.trim();
  const p   = document.getElementById('login-pw').value;

  if (!u || !p) { _setFormErr('login-error', 'Username and password required'); return; }

  btn.disabled    = true;
  btn.textContent = 'Signing in…';

  const res = await api.login(u, p);

  btn.disabled    = false;
  btn.textContent = 'Sign in →';

  if (res && res.ok && res.data) {
    App.boot(res.data);
  } else {
    _setFormErr('login-error', res?.error || 'Login failed. Check credentials.');
  }
});

// Enter key on login fields
['login-user','login-pw'].forEach(id => {
  document.getElementById(id).addEventListener('keydown', e => {
    if (e.key === 'Enter') document.getElementById('btn-login').click();
  });
});

// ── Signup ───────────────────────────────────────────────────────────────
document.getElementById('btn-signup').addEventListener('click', async () => {
  const btn = document.getElementById('btn-signup');
  const body = {
    display_name: document.getElementById('signup-name').value.trim(),
    username:     document.getElementById('signup-user').value.trim(),
    email:        document.getElementById('signup-email').value.trim(),
    password:     document.getElementById('signup-pw').value,
  };
  if (!body.username || !body.password) {
    _setFormErr('signup-error', 'Username and password required'); return;
  }
  btn.disabled = true; btn.textContent = 'Creating…';
  const res = await api.signup(body);
  btn.disabled = false; btn.textContent = 'Create Account →';
  if (res && res.ok) {
    _setFormOk('signup-success', '✓ Account created! Please sign in.');
    setTimeout(() => showAuthView('login'), 1500);
  } else {
    _setFormErr('signup-error', res?.error || 'Signup failed');
  }
});

// ── Forgot Password ───────────────────────────────────────────────────────
document.getElementById('btn-forgot').addEventListener('click', async () => {
  const btn   = document.getElementById('btn-forgot');
  const ident = document.getElementById('forgot-ident').value.trim();
  if (!ident) { _setFormErr('forgot-error', 'Enter your username or email'); return; }
  btn.disabled = true; btn.textContent = 'Sending…';
  const body = ident.includes('@') ? { email: ident } : { username: ident };
  const res  = await api.forgotPw(body);
  btn.disabled = false; btn.textContent = 'Send Reset Link →';
  if (res && res.ok) {
    const token = res.data?.reset_token;
    const msg   = token
      ? 'Reset token (dev mode): ' + token
      : res.data?.message || 'Reset link sent.';
    _setFormOk('forgot-success', msg);
  } else {
    _setFormErr('forgot-error', res?.error || 'Account not found');
  }
});
