// Sigil Dashboard — Chat Autocomplete Engine
// Provides "/" command and "@" mention completion in the chat input.

/**
 * @typedef {Object} AutocompleteItem
 * @property {string} type      - 'command' | 'mention'
 * @property {string} value     - The text to insert (e.g. '/help', '@analyst')
 * @property {string} label     - Display label (e.g. '/help', '@analyst')
 * @property {string} description - Short description
 * @property {string} [icon]    - Optional icon hint ('command'|'skill'|'sister'|'session')
 */

const ICON_SVG = {
  command: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="4 17 10 11 4 5"/><line x1="12" y1="19" x2="20" y2="19"/></svg>`,
  skill: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/></svg>`,
  sister: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>`,
  session: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="18" height="18" x="3" y="3" rx="2"/><path d="M3 9h18"/><path d="M9 21V9"/></svg>`,
};

export class ChatAutocomplete {
  /**
   * @param {HTMLTextAreaElement} inputEl  - The chat textarea element
   * @param {Object} opts
   * @param {function(): AutocompleteItem[]} opts.getCommands - Returns current command list
   * @param {function(): AutocompleteItem[]} opts.getMentions - Returns current mention list
   * @param {function(string): void} opts.onAccept - Called when user selects an item
   */
  constructor(inputEl, opts) {
    this._input = inputEl;
    this._getCommands = opts.getCommands;
    this._getMentions = opts.getMentions;
    this._onAccept = opts.onAccept;

    this._popup = null;
    this._items = [];
    this._selectedIndex = 0;
    this._active = false;
    this._triggerType = null; // 'command' | 'mention'
    this._triggerPos = -1;    // Caret position of trigger char

    this._createPopup();
    this._bindEvents();
  }

  // ── DOM creation ──

  _createPopup() {
    this._popup = document.createElement('div');
    this._popup.className = 'autocomplete-popup';
    this._popup.setAttribute('role', 'listbox');
    this._popup.setAttribute('aria-label', 'Autocomplete suggestions');
    this._popup.style.display = 'none';

    // Insert popup as a sibling of the input area, inside chat-input-area
    const inputArea = this._input.closest('.chat-input-area');
    if (inputArea) {
      inputArea.style.position = 'relative';
      inputArea.insertBefore(this._popup, inputArea.firstChild);
    } else {
      // Fallback: append to parent
      this._input.parentElement.appendChild(this._popup);
    }
  }

  // ── Event binding ──

  _bindEvents() {
    this._input.addEventListener('input', () => this._onInput());
    this._input.addEventListener('keydown', (e) => this._onKeyDown(e));
    this._input.addEventListener('blur', () => {
      // Delay to allow click on popup item
      setTimeout(() => this.dismiss(), 150);
    });

    this._popup.addEventListener('mousedown', (e) => {
      // Prevent blur from firing before click registers
      e.preventDefault();
    });

    this._popup.addEventListener('click', (e) => {
      const item = e.target.closest('[data-ac-index]');
      if (item) {
        const idx = parseInt(item.dataset.acIndex, 10);
        if (!isNaN(idx) && idx >= 0 && idx < this._items.length) {
          this._selectedIndex = idx;
          this._accept();
        }
      }
    });
  }

  // ── Core logic ──

  _onInput() {
    const value = this._input.value;
    const caret = this._input.selectionStart;

    // Check for "/" at start of input
    if (value.startsWith('/')) {
      this._triggerType = 'command';
      this._triggerPos = 0;
      const query = value.slice(1, caret);
      // Don't show if there's a space after the command (user is typing args)
      if (query.includes(' ')) {
        this.dismiss();
        return;
      }
      this._showResults(query);
      return;
    }

    // Check for "@" — look backwards from caret for nearest unescaped @
    const textBeforeCaret = value.slice(0, caret);
    const atIndex = textBeforeCaret.lastIndexOf('@');
    if (atIndex >= 0) {
      // Ensure @ is at start or preceded by whitespace
      if (atIndex === 0 || /\s/.test(value[atIndex - 1])) {
        const query = textBeforeCaret.slice(atIndex + 1);
        // Don't show if there's a space in the mention query
        if (query.includes(' ')) {
          this.dismiss();
          return;
        }
        this._triggerType = 'mention';
        this._triggerPos = atIndex;
        this._showResults(query);
        return;
      }
    }

    this.dismiss();
  }

  _showResults(query) {
    const source = this._triggerType === 'command'
      ? this._getCommands()
      : this._getMentions();

    const lowerQuery = query.toLowerCase();
    this._items = lowerQuery.length === 0
      ? source.slice(0, 12)
      : this._filterItems(source, lowerQuery).slice(0, 12);

    if (this._items.length === 0) {
      this.dismiss();
      return;
    }

    this._selectedIndex = 0;
    this._active = true;
    this._render();
    this._popup.style.display = '';
  }

  _filterItems(items, query) {
    // Score-based filtering: prefix match scores higher than substring match
    const scored = [];
    for (const item of items) {
      const target = item.label.toLowerCase();
      // Strip trigger char for matching
      const cleanTarget = target.replace(/^[/@]/, '');
      if (cleanTarget.startsWith(query)) {
        scored.push({ item, score: 2 });
      } else if (cleanTarget.includes(query)) {
        scored.push({ item, score: 1 });
      } else if (item.description && item.description.toLowerCase().includes(query)) {
        scored.push({ item, score: 0 });
      }
    }
    scored.sort((a, b) => b.score - a.score);
    return scored.map(s => s.item);
  }

  _onKeyDown(e) {
    if (!this._active) return;

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        this._selectedIndex = (this._selectedIndex + 1) % this._items.length;
        this._render();
        break;

      case 'ArrowUp':
        e.preventDefault();
        this._selectedIndex = (this._selectedIndex - 1 + this._items.length) % this._items.length;
        this._render();
        break;

      case 'Tab':
      case 'Enter':
        e.preventDefault();
        e.stopPropagation();
        this._accept();
        break;

      case 'Escape':
        e.preventDefault();
        this.dismiss();
        break;
    }
  }

  _accept() {
    if (!this._active || this._items.length === 0) return;

    const item = this._items[this._selectedIndex];
    const value = this._input.value;

    // Replace from trigger position to current caret
    const before = value.slice(0, this._triggerPos);
    const after = value.slice(this._input.selectionStart);
    const insertText = item.value + (this._triggerType === 'mention' ? ' ' : '');

    this._input.value = before + insertText + after;

    // Position caret after inserted text
    const newCaret = before.length + insertText.length;
    this._input.selectionStart = newCaret;
    this._input.selectionEnd = newCaret;

    // If it is a command with no further typing needed, leave cursor after
    // Trigger input event so textarea auto-resize works
    this._input.dispatchEvent(new Event('input', { bubbles: true }));

    this.dismiss();

    if (this._onAccept) {
      this._onAccept(item.value);
    }
  }

  dismiss() {
    this._active = false;
    this._items = [];
    this._triggerType = null;
    this._triggerPos = -1;
    this._popup.style.display = 'none';
    this._popup.innerHTML = '';
  }

  // ── Rendering ──

  _render() {
    let html = '';
    const triggerLabel = this._triggerType === 'command' ? 'Commands' : 'Mentions';
    html += `<div class="autocomplete-header">${triggerLabel}</div>`;

    for (let i = 0; i < this._items.length; i++) {
      const item = this._items[i];
      const selected = i === this._selectedIndex;
      const iconHtml = ICON_SVG[item.icon] || ICON_SVG.command;
      html += `
        <div class="autocomplete-item${selected ? ' selected' : ''}"
             data-ac-index="${i}"
             role="option"
             aria-selected="${selected}">
          <span class="autocomplete-icon">${iconHtml}</span>
          <span class="autocomplete-label">${this._escapeHtml(item.label)}</span>
          <span class="autocomplete-desc">${this._escapeHtml(item.description)}</span>
        </div>`;
    }

    this._popup.innerHTML = html;

    // Scroll selected item into view
    const selectedEl = this._popup.querySelector('.autocomplete-item.selected');
    if (selectedEl) {
      selectedEl.scrollIntoView({ block: 'nearest' });
    }
  }

  _escapeHtml(str) {
    if (!str) return '';
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  // ── Public API ──

  /** Returns true if autocomplete popup is currently active. */
  get isActive() {
    return this._active;
  }

  /** Force-refresh the items (e.g. after new data is fetched). */
  refresh() {
    if (this._active) {
      this._onInput();
    }
  }

  /** Clean up event listeners and DOM. */
  destroy() {
    this._popup.remove();
  }
}
