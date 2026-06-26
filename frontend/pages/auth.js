/* ── Auth ────────────────────────────────────────────────────────────────── */

function showAuthView(view) {
  document.querySelectorAll('.auth-view').forEach(v => v.classList.remove('active'));
  const target = document.getElementById('view-' + view);
  if (target) target.classList.add('active');
  // Clear all error/success messages
  ['login-error','signup-error','signup-success','forgot-error','forgot-success','reset-error','reset-success'].forEach(id => {
    const el = document.getElementById(id);
    if (el) { el.textContent = ''; el.classList.add('hidden'); }
  });
  // Hide reset section when leaving forgot view
  const resetSection = document.getElementById('forgot-reset-section');
  if (resetSection) resetSection.classList.add('hidden');
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
  if (!ident) { _setFormErr('forgot-error', 'Enter your username'); return; }
  btn.disabled = true; btn.textContent = 'Please wait…';
  const res = await api.forgotPw({ username: ident });
  btn.disabled = false; btn.textContent = 'Get Reset Token →';
  if (res && res.ok) {
    const token = res.data?.reset_token;
    if (token) {
      // Auto-fill the token and reveal the reset section
      document.getElementById('reset-token-input').value = token;
      _setFormOk('forgot-success', 'Token generated — enter a new password below.');
      document.getElementById('forgot-reset-section').classList.remove('hidden');
    } else {
      _setFormOk('forgot-success', res.data?.message || 'Check your email for the reset link.');
    }
  } else {
    _setFormErr('forgot-error', res?.error || 'Account not found');
  }
});

// ── Reset Password ─────────────────────────────────────────────────────────
document.getElementById('btn-reset-pw').addEventListener('click', async () => {
  const btn     = document.getElementById('btn-reset-pw');
  const token   = document.getElementById('reset-token-input').value.trim();
  const pw      = document.getElementById('reset-new-pw').value;
  const confirm = document.getElementById('reset-confirm-pw').value;

  if (!token)          { _setFormErr('reset-error', 'Token is required'); return; }
  if (pw.length < 6)   { _setFormErr('reset-error', 'Password must be at least 6 characters'); return; }
  if (pw !== confirm)  { _setFormErr('reset-error', 'Passwords do not match'); return; }

  btn.disabled = true; btn.textContent = 'Resetting…';
  const res = await api.resetPw({ token, password: pw });
  btn.disabled = false; btn.textContent = 'Reset Password →';

  if (res && res.ok) {
    _setFormOk('reset-success', 'Password updated! Redirecting to sign in…');
    document.getElementById('reset-error').classList.add('hidden');
    setTimeout(() => showAuthView('login'), 1800);
  } else {
    _setFormErr('reset-error', res?.error || 'Reset failed — token may have expired');
  }
});
