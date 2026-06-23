/* ── Auth ─────────────────────────────────────────────────────────────────── */

function showAuthView(view) {
  document.querySelectorAll('.auth-view').forEach(v => v.classList.remove('active'));
  document.getElementById(`view-${view}`)?.classList.add('active');
  ['login-error','signup-error','signup-success','forgot-error','forgot-success'].forEach(id => {
    const el = document.getElementById(id);
    if (el) { el.classList.add('hidden'); el.textContent = ''; }
  });
}

function showFormError(id, msg) {
  const el = document.getElementById(id);
  if (el) { el.textContent = msg; el.classList.remove('hidden'); }
}

function showFormSuccess(id, msg) {
  const el = document.getElementById(id);
  if (el) { el.textContent = msg; el.classList.remove('hidden'); }
}

// Login
document.getElementById('btn-login').addEventListener('click', async () => {
  const btn = document.getElementById('btn-login');
  btn.disabled = true;
  btn.textContent = 'Signing in…';
  const u = document.getElementById('login-user').value.trim();
  const p = document.getElementById('login-pw').value;
  const res = await api.login(u, p);
  btn.disabled = false;
  btn.textContent = 'Sign in →';
  if (res?.ok) {
    sessionStorage.setItem('jdk_user', JSON.stringify(res.data));
    window.App?.boot(res.data);
  } else {
    showFormError('login-error', res?.error || 'Login failed');
  }
});

['login-user', 'login-pw'].forEach(id => {
  document.getElementById(id)?.addEventListener('keydown', e => {
    if (e.key === 'Enter') document.getElementById('btn-login').click();
  });
});

// Signup
document.getElementById('btn-signup').addEventListener('click', async () => {
  const btn = document.getElementById('btn-signup');
  btn.disabled = true;
  btn.textContent = 'Creating…';
  const body = {
    display_name: document.getElementById('signup-name').value.trim(),
    username:     document.getElementById('signup-user').value.trim(),
    email:        document.getElementById('signup-email').value.trim(),
    password:     document.getElementById('signup-pw').value,
  };
  const res = await api.signup(body);
  btn.disabled = false;
  btn.textContent = 'Create Account →';
  if (res?.ok) {
    showFormSuccess('signup-success', 'Account created! Please sign in.');
    setTimeout(() => showAuthView('login'), 1500);
  } else {
    showFormError('signup-error', res?.error || 'Signup failed');
  }
});

// Forgot password
document.getElementById('btn-forgot').addEventListener('click', async () => {
  const btn = document.getElementById('btn-forgot');
  btn.disabled = true;
  btn.textContent = 'Sending…';
  const ident = document.getElementById('forgot-ident').value.trim();
  const body = ident.includes('@') ? { email: ident } : { username: ident };
  const res = await api.forgotPw(body);
  btn.disabled = false;
  btn.textContent = 'Send Reset Link →';
  if (res?.ok) {
    const token = res.data?.reset_token;
    const msg = token
      ? `Reset token (dev mode): ${token}`
      : res.data?.message || 'Reset link sent.';
    showFormSuccess('forgot-success', msg);
  } else {
    showFormError('forgot-error', res?.error || 'Account not found');
  }
});
