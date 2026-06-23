/* ── AI Chat ─────────────────────────────────────────────────────────────── */
let chatHistory = [];

const QUICK_PROMPTS = [
  'What are my current stock alerts?',
  'How many open orders do I have?',
  'Which materials need reordering?',
  'Show me critical priority orders',
  'What products can I manufacture today?',
  'Run a feasibility check for 500 bags',
];

function renderChat(el) {
  el.innerHTML = `
    <div class="page-header">
      <div class="page-title-group">
        <div class="page-title">💬 AI Factory Assistant</div>
        <div class="page-sub">Ask anything about your factory in plain English</div>
      </div>
      <div class="page-actions">
        <button class="btn btn-secondary btn-sm" onclick="chatHistory=[];renderChat(document.getElementById('page-container'))">Clear chat</button>
        <button class="btn btn-ghost btn-sm" onclick="App.navigate('settings')">⚙ Settings</button>
      </div>
    </div>
    <div class="chat-shell">
      <div class="chat-quick-actions" id="quick-actions">
        ${QUICK_PROMPTS.map(p => `<button class="quick-chip" onclick="sendChat('${p.replace(/'/g, "\\'")}')">${p}</button>`).join('')}
      </div>
      <div class="chat-messages" id="chat-messages">
        <div class="chat-msg assistant">
          <div class="chat-avatar">🤖</div>
          <div class="chat-bubble">
            Hey! I'm your JDK Factory AI assistant. Ask me anything about inventory, orders, MRP, or just say what you want to do and I'll help you get there. 🏭
          </div>
        </div>
      </div>
      <div class="chat-input-row">
        <textarea class="chat-input" id="chat-input" placeholder="Ask me anything… e.g. 'Which raw materials are critically low?'" rows="1"></textarea>
        <button class="chat-send" id="chat-send-btn" onclick="sendChat()">
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
            <path d="M16 2L2 8l5 3 3 5 6-14z" fill="currentColor"/>
          </svg>
        </button>
      </div>
    </div>`;

  const input = document.getElementById('chat-input');
  input.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendChat(); }
  });
  input.addEventListener('input', () => {
    input.style.height = 'auto';
    input.style.height = Math.min(input.scrollHeight, 120) + 'px';
  });

  // Restore history
  chatHistory.forEach(m => appendMsg(m.role, m.content));
}

function appendMsg(role, content, action = null) {
  const msgs = document.getElementById('chat-messages');
  if (!msgs) return;

  const isUser = role === 'user';
  const avatar = isUser ? (App.user?.display_name?.[0] || 'U') : '🤖';

  let extra = '';
  if (action?.action === 'navigate' && action.page) {
    extra = `<div><button class="chat-action-pill" onclick="App.navigate('${action.page}')">→ Open ${action.page}</button></div>`;
  } else if (action?.action === 'run_mrp') {
    extra = `<div><button class="chat-action-pill" onclick="App.navigate('mrp')">→ Run MRP Now</button></div>`;
  }

  const div = document.createElement('div');
  div.className = `chat-msg ${role}`;
  div.innerHTML = `
    <div class="chat-avatar">${avatar}</div>
    <div>
      <div class="chat-bubble">${content.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>').replace(/\n/g, '<br>')}</div>
      ${extra}
    </div>`;
  msgs.appendChild(div);
  msgs.scrollTop = msgs.scrollHeight;
}

async function sendChat(preset) {
  const input = document.getElementById('chat-input');
  const message = preset || input?.value?.trim();
  if (!message) return;

  const btn = document.getElementById('chat-send-btn');
  if (input) { input.value = ''; input.style.height = 'auto'; }
  if (btn) btn.disabled = true;

  // Hide quick actions after first message
  const qa = document.getElementById('quick-actions');
  if (qa && chatHistory.length === 0) qa.style.display = 'none';

  appendMsg('user', message);
  chatHistory.push({ role: 'user', content: message });

  // Typing indicator
  const msgs = document.getElementById('chat-messages');
  const typing = document.createElement('div');
  typing.className = 'chat-msg assistant';
  typing.id = 'typing-indicator';
  typing.innerHTML = `<div class="chat-avatar">🤖</div><div class="chat-bubble" style="color:var(--text-muted)"><div class="spinner" style="width:14px;height:14px;display:inline-block;margin-right:6px"></div>thinking…</div>`;
  msgs?.appendChild(typing);
  msgs && (msgs.scrollTop = msgs.scrollHeight);

  const res = await api.chat(message, chatHistory.slice(-10));

  document.getElementById('typing-indicator')?.remove();
  if (btn) btn.disabled = false;

  if (res?.ok) {
    const reply  = res.data.reply;
    const action = res.data.action;
    appendMsg('assistant', reply, action);
    chatHistory.push({ role: 'assistant', content: reply });
  } else {
    appendMsg('assistant', `⚠️ ${res?.error || 'Something went wrong. Check your DeepSeek API key in Settings.'}`);
  }
}
