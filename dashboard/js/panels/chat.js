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

function renderMarkdown(text) {
  if (!text) return '';
  return text
    // Code blocks
    .replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>')
    // Inline code
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    // Bold
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    // Links
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>')
    // Lists
    .replace(/^- (.+)$/gm, '<li>$1</li>')
    .replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>')
    // Line breaks
    .replace(/\n/g, '<br>');
}

function renderMessages(container) {
  const messagesEl = container.querySelector('.chat-messages');
  if (!messagesEl) return;

  let html = '';
  if (chatState.messages.length === 0) {
    html = `
      <div class="chat-welcome">
        <div class="chat-welcome-icon">&#128172;</div>
        <div class="chat-welcome-text">Start a conversation with the Sigil runtime. Type a message or use /commands.</div>
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
        if (msg.text) {
          html += renderMarkdown(msg.text);
        }
        if (msg.toolCalls && msg.toolCalls.length > 0) {
          for (const tc of msg.toolCalls) {
            const tcId = 'tc-' + Math.random().toString(36).slice(2, 8);
            html += `
              <div class="tool-call">
                <div class="tool-call-header" data-tc="${tcId}">
                  <span class="tool-call-icon" id="icon-${tcId}">&#9654;</span>
                  <span>${tc.name || 'tool_call'}</span>
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
      <div class="typing-indicator">
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
      </div>`;
  }

  messagesEl.innerHTML = html;

  // Wire tool call toggles
  messagesEl.querySelectorAll('.tool-call-header').forEach(header => {
    header.addEventListener('click', () => {
      const tcId = header.dataset.tc;
      const body = document.getElementById(`body-${tcId}`);
      const icon = document.getElementById(`icon-${tcId}`);
      if (body) body.classList.toggle('open');
      if (icon) icon.classList.toggle('open');
    });
  });

  // Auto-scroll
  if (!chatState.userScrolledUp) {
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }
}

function escapeHtml(str) {
  if (!str) return '';
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

export function initChat(container, api, config) {
  if (!container) return;
  chatState.sessionId = generateSessionId();

  container.innerHTML = `
    <div class="chat-container">
      <div class="chat-header">
        <div class="chat-header-left">
          <span class="chat-header-title">Chat</span>
          <span class="chat-session-id">${chatState.sessionId}</span>
        </div>
        <div class="chat-header-actions">
          <button class="btn btn-ghost btn-sm" id="chat-new-session">New</button>
        </div>
      </div>
      <div class="chat-messages"></div>
      <div class="chat-input-area">
        <div class="chat-context-bar">
          <span id="chat-turn-count">Turns: 0</span>
          <span id="chat-char-count">0</span>
        </div>
        <div class="chat-input-row">
          <textarea class="chat-textarea" placeholder="Type a message... (/ for commands)" rows="1" id="chat-input"></textarea>
          <button class="chat-send-btn" id="chat-send" title="Send">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m22 2-7 20-4-9-9-4z"/><path d="M22 2 11 13"/></svg>
          </button>
        </div>
      </div>
    </div>`;

  renderMessages(container);

  const input = container.querySelector('#chat-input');
  const sendBtn = container.querySelector('#chat-send');
  const charCount = container.querySelector('#chat-char-count');
  const turnCount = container.querySelector('#chat-turn-count');
  const messagesArea = container.querySelector('.chat-messages');

  // Auto-grow textarea
  input.addEventListener('input', () => {
    input.style.height = 'auto';
    input.style.height = Math.min(input.scrollHeight, 120) + 'px';
    charCount.textContent = input.value.length;
  });

  // Scroll detection
  messagesArea.addEventListener('scroll', () => {
    const atBottom = messagesArea.scrollHeight - messagesArea.scrollTop - messagesArea.clientHeight < 50;
    chatState.userScrolledUp = !atBottom;
  });

  // Send message
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
      if (result.assistant && result.assistant.text) {
        agentMsg.text = result.assistant.text;
      } else if (result.response) {
        agentMsg.text = result.response;
      } else if (typeof result === 'string') {
        agentMsg.text = result;
      } else {
        agentMsg.text = JSON.stringify(result, null, 2);
      }

      if (result.tool_calls) {
        agentMsg.toolCalls = result.tool_calls;
      }
      if (result.assistant && result.assistant.tool_calls) {
        agentMsg.toolCalls = result.assistant.tool_calls;
      }

      chatState.messages.push(agentMsg);
    } catch (err) {
      chatState.messages.push({
        role: 'agent',
        text: `Error: ${err.message}`,
        toolCalls: [],
      });
    }

    chatState.sending = false;
    turnCount.textContent = `Turns: ${Math.floor(chatState.messages.length / 2)}`;
    renderMessages(container);
  }

  sendBtn.addEventListener('click', sendMessage);
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  // New session
  container.querySelector('#chat-new-session')?.addEventListener('click', () => {
    chatState.sessionId = generateSessionId();
    chatState.messages = [];
    chatState.sending = false;
    container.querySelector('.chat-session-id').textContent = chatState.sessionId;
    turnCount.textContent = 'Turns: 0';
    renderMessages(container);
  });
}
