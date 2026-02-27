// Sigil Dashboard — Chat Panel

let chatState = {
  sessionId: null,
  messages: [],
  sending: false,
  userScrolledUp: false,
};

function generateSessionId() {
  return 'dash-' + Math.random().toString(36).slice(2, 10);
}

function escapeHtml(str) {
  if (!str) return '';
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function renderMarkdown(text) {
  if (!text) return '';
  return text
    .replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>')
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>')
    .replace(/^- (.+)$/gm, '<li>$1</li>')
    .replace(/(<li>[\s\S]*?<\/li>)/g, '<ul>$1</ul>')
    .replace(/\n/g, '<br>');
}

const WELCOME_SVG = `<svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" stroke-linecap="round" stroke-linejoin="round" style="opacity:0.15">
  <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
  <path d="M8 9h8M8 13h6"/>
</svg>`;

const SEND_SVG = `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m22 2-7 20-4-9-9-4z"/><path d="M22 2 11 13"/></svg>`;

function renderMessages(container) {
  const messagesEl = container.querySelector('.chat-messages');
  if (!messagesEl) return;

  let html = '';
  if (chatState.messages.length === 0) {
    html = `
      <div class="chat-welcome">
        ${WELCOME_SVG}
        <div class="chat-welcome-text">Chat with the Sigil runtime. Type a message or use /commands.</div>
      </div>`;
  } else {
    for (const msg of chatState.messages) {
      if (msg.role === 'user') {
        html += `
          <div class="chat-message user">
            <div class="chat-bubble">${escapeHtml(msg.text)}</div>
          </div>`;
      } else {
        html += `<div class="chat-message agent"><div class="chat-bubble">`;
        if (msg.text) html += renderMarkdown(msg.text);
        if (msg.toolCalls && msg.toolCalls.length > 0) {
          for (const tc of msg.toolCalls) {
            const tcId = 'tc-' + Math.random().toString(36).slice(2, 8);
            html += `
              <div class="tool-call">
                <div class="tool-call-header" data-tc="${tcId}" role="button" tabindex="0" aria-expanded="false" aria-label="Toggle tool call details">
                  <span class="tool-call-icon" id="icon-${tcId}">&#9654;</span>
                  <span>${escapeHtml(tc.name || 'tool_call')}</span>
                </div>
                <div class="tool-call-body" id="body-${tcId}">${escapeHtml(JSON.stringify(tc, null, 2))}</div>
              </div>`;
          }
        }
        html += `</div></div>`;
      }
    }
  }

  if (chatState.sending) {
    html += `
      <div class="typing-indicator" role="status" aria-label="Agent is typing">
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
      </div>`;
  }

  messagesEl.innerHTML = html;

  // Wire tool call toggles
  messagesEl.querySelectorAll('.tool-call-header').forEach(header => {
    const toggle = () => {
      const tcId = header.dataset.tc;
      const body = document.getElementById(`body-${tcId}`);
      const icon = document.getElementById(`icon-${tcId}`);
      const isOpen = body?.classList.toggle('open');
      if (icon) icon.classList.toggle('open');
      header.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
    };
    header.addEventListener('click', toggle);
    header.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggle(); }
    });
  });

  if (!chatState.userScrolledUp) {
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }
}

export function initChat(container, api, config) {
  if (!container) return;
  chatState.sessionId = generateSessionId();

  container.innerHTML = `
    <div class="chat-container" role="region" aria-label="Chat">
      <div class="chat-header">
        <div class="chat-header-left">
          <span class="chat-header-title">Chat</span>
          <span class="chat-session-id">${chatState.sessionId}</span>
        </div>
        <div class="chat-header-actions">
          <button class="btn btn-ghost btn-sm" id="chat-new-session" aria-label="Start new chat session">New</button>
        </div>
      </div>
      <div class="chat-messages" role="log" aria-label="Chat messages" aria-live="polite"></div>
      <div class="chat-input-area">
        <div class="chat-context-bar">
          <span id="chat-turn-count">0 turns</span>
          <span id="chat-char-count">0</span>
        </div>
        <div class="chat-input-row">
          <textarea class="chat-textarea" placeholder="Message... (/ for commands)" rows="1" id="chat-input" aria-label="Chat message input"></textarea>
          <button class="chat-send-btn" id="chat-send" title="Send" aria-label="Send message">${SEND_SVG}</button>
        </div>
      </div>
    </div>`;

  renderMessages(container);

  const input = container.querySelector('#chat-input');
  const sendBtn = container.querySelector('#chat-send');
  const charCount = container.querySelector('#chat-char-count');
  const turnCount = container.querySelector('#chat-turn-count');
  const messagesArea = container.querySelector('.chat-messages');

  input.addEventListener('input', () => {
    input.style.height = 'auto';
    input.style.height = Math.min(input.scrollHeight, 120) + 'px';
    charCount.textContent = input.value.length;
  });

  messagesArea.addEventListener('scroll', () => {
    const atBottom = messagesArea.scrollHeight - messagesArea.scrollTop - messagesArea.clientHeight < 50;
    chatState.userScrolledUp = !atBottom;
  });

  async function sendMessage() {
    const text = input.value.trim();
    if (!text || chatState.sending) return;

    chatState.messages.push({ role: 'user', text });
    chatState.sending = true;
    input.value = '';
    input.style.height = 'auto';
    charCount.textContent = '0';
    chatState.userScrolledUp = false;
    renderMessages(container);

    try {
      let result;
      if (text.startsWith('/')) {
        result = await api.executeCommand(chatState.sessionId, text);
      } else {
        result = await api.chat(chatState.sessionId, text);
      }

      const agentMsg = { role: 'agent', text: '', toolCalls: [] };
      if (result.assistant?.text) {
        agentMsg.text = result.assistant.text;
      } else if (result.response) {
        agentMsg.text = result.response;
      } else if (typeof result === 'string') {
        agentMsg.text = result;
      } else {
        agentMsg.text = JSON.stringify(result, null, 2);
      }

      if (result.tool_calls) agentMsg.toolCalls = result.tool_calls;
      if (result.assistant?.tool_calls) agentMsg.toolCalls = result.assistant.tool_calls;

      chatState.messages.push(agentMsg);
    } catch (err) {
      chatState.messages.push({ role: 'agent', text: `Error: ${err.message}`, toolCalls: [] });
    }

    chatState.sending = false;
    const turns = Math.floor(chatState.messages.length / 2);
    turnCount.textContent = `${turns} turn${turns !== 1 ? 's' : ''}`;
    renderMessages(container);
  }

  sendBtn.addEventListener('click', sendMessage);
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  container.querySelector('#chat-new-session')?.addEventListener('click', () => {
    chatState.sessionId = generateSessionId();
    chatState.messages = [];
    chatState.sending = false;
    container.querySelector('.chat-session-id').textContent = chatState.sessionId;
    turnCount.textContent = '0 turns';
    renderMessages(container);
  });
}
