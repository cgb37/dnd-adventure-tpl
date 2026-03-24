// assets/js/chatbot-widget.js
// Chatbot widget (Iteration 5) — unified input box
(() => {
  const baseUrl = (window.LLM_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '');

  // ── localStorage keys ──────────────────────────────────────────────────────
  const LS_OPEN    = 'dnd_global_chatbot_open';
  const LS_MODE    = 'dnd_global_chatbot_mode';     // 'ask' | 'agent'
  const LS_KIND    = 'dnd_global_chatbot_kind';     // 'npc', 'location', …
  const LS_MODEL   = 'dnd_global_chatbot_model';    // provider string

  // ── Element references ─────────────────────────────────────────────────────
  const el = {
    panel:              document.querySelector('#global-chatbot .chatbot__panel'),
    toggle:             document.getElementById('chatbotToggle'),
    floatToggle:        document.getElementById('chatbotFloatingToggle'),
    messages:           document.getElementById('chatbotMessages'),
    input:              document.getElementById('chatbotInput'),
    send:               document.getElementById('chatbotSend'),
    inputBox:           document.getElementById('chatbotInputBox'),
    // mode
    modePillBtn:        document.getElementById('modePillBtn'),
    modePillLabel:      document.getElementById('modePillLabel'),
    modeMenu:           document.getElementById('modeMenu'),
    // agent type
    agentTypePillBtn:   document.getElementById('agentTypePillBtn'),
    agentTypePillLabel: document.getElementById('agentTypePillLabel'),
    agentTypeMenu:      document.getElementById('agentTypeMenu'),
    // attach
    attachBtn:          document.getElementById('attachBtn'),
    fileInput:          document.getElementById('chatbotFileInput'),
    attachments:        document.getElementById('chatbotAttachments'),
    attachError:        document.getElementById('chatbotAttachError'),
    // model
    modelBtn:           document.getElementById('modelBtn'),
    modelBtnLabel:      document.getElementById('modelBtnLabel'),
    modelMenu:          document.getElementById('modelMenu'),
  };

  // Bail if the shell HTML isn't present (shouldn't happen on allowed pages).
  if (!el.panel || !el.input || !el.send) return;

  // ── State ──────────────────────────────────────────────────────────────────
  const state = {
    mode:          lsGet(LS_MODE) || 'ask',
    kind:          lsGet(LS_KIND) || 'npc',
    model:         lsGet(LS_MODEL) || '',
    attachedFiles: [],
  };

  // ── LocalStorage helpers ───────────────────────────────────────────────────
  function lsGet(key) {
    try { return localStorage.getItem(key); } catch { return null; }
  }
  function lsSet(key, val) {
    try { localStorage.setItem(key, val); } catch { /* ignore */ }
  }

  // ── HTTP helper ────────────────────────────────────────────────────────────
  async function httpJson(path, opts = {}) {
    const headers = { 'Content-Type': 'application/json', ...(opts.headers || {}) };
    const res = await fetch(`${baseUrl}${path}`, { ...opts, headers });
    const text = await res.text();
    let body = null;
    try { body = text ? JSON.parse(text) : null; } catch { /* ignore */ }
    if (!res.ok) {
      const detail = body?.error?.message || body?.detail || text || `${res.status}`;
      throw new Error(detail);
    }
    return body;
  }

  // ── Textarea auto-resize ───────────────────────────────────────────────────
  function autosizeTextarea() {
    el.input.style.height = 'auto';
    const max = 5 * 24 + 16;
    el.input.style.height = `${Math.min(el.input.scrollHeight, max)}px`;
  }

  // ── Messages ───────────────────────────────────────────────────────────────
  function appendMessage({ role, text, meta }) {
    const wrap = document.createElement('div');
    wrap.className = `chatbot__msg chatbot__msg--${role}`;
    const bubble = document.createElement('div');
    bubble.className = 'chatbot__bubble';
    bubble.textContent = text;
    if (meta) {
      const m = document.createElement('div');
      m.className = 'chatbot__meta';
      m.textContent = meta;
      bubble.appendChild(m);
    }
    wrap.appendChild(bubble);
    el.messages.appendChild(wrap);
    el.messages.scrollTop = el.messages.scrollHeight;
  }

  function appendThinking() {
    const wrap = document.createElement('div');
    wrap.className = 'chatbot__msg chatbot__msg--ai';
    wrap.dataset.thinking = 'true';
    const bubble = document.createElement('div');
    bubble.className = 'chatbot__bubble';
    bubble.textContent = 'Thinking…';
    wrap.appendChild(bubble);
    el.messages.appendChild(wrap);
    el.messages.scrollTop = el.messages.scrollHeight;
    return () => wrap.remove();
  }

  // ── Dropdown helpers ───────────────────────────────────────────────────────
  function openMenu(menu, btn) {
    menu.hidden = false;
    btn.setAttribute('aria-expanded', 'true');
  }
  function closeMenu(menu, btn) {
    menu.hidden = true;
    btn.setAttribute('aria-expanded', 'false');
  }
  function toggleMenu(menu, btn) {
    menu.hidden ? openMenu(menu, btn) : closeMenu(menu, btn);
  }

  // Close all menus when clicking outside
  document.addEventListener('click', (e) => {
    const menus = [
      [el.modeMenu, el.modePillBtn],
      [el.agentTypeMenu, el.agentTypePillBtn],
      [el.modelMenu, el.modelBtn],
    ];
    for (const [menu, btn] of menus) {
      if (menu && btn && !btn.contains(e.target) && !menu.contains(e.target)) {
        closeMenu(menu, btn);
      }
    }
  });

  // ── Mode toggle (Ask / Agent) ──────────────────────────────────────────────
  function applyMode(mode) {
    state.mode = mode;
    lsSet(LS_MODE, mode);
    el.inputBox.dataset.mode = mode;
    el.modePillLabel.textContent = mode === 'ask' ? 'Ask' : 'Agent';
    el.input.placeholder = mode === 'ask' ? 'Ask anything...' : 'Describe what to generate…';
  }

  el.modePillBtn.addEventListener('click', () => toggleMenu(el.modeMenu, el.modePillBtn));

  el.modeMenu.addEventListener('click', (e) => {
    const item = e.target.closest('[data-value]');
    if (!item) return;
    applyMode(item.dataset.value);
    closeMenu(el.modeMenu, el.modePillBtn);
  });

  // ── Agent type selector ────────────────────────────────────────────────────
  function populateAgentTypes(kinds) {
    el.agentTypeMenu.innerHTML = '';
    for (const k of kinds) {
      const li = document.createElement('li');
      li.role = 'menuitem';
      li.dataset.value = k;
      li.textContent = k.charAt(0).toUpperCase() + k.slice(1);
      if (k === state.kind) li.setAttribute('aria-selected', 'true');
      el.agentTypeMenu.appendChild(li);
    }
  }

  function applyKind(kind) {
    state.kind = kind;
    lsSet(LS_KIND, kind);
    el.agentTypePillLabel.textContent = kind.charAt(0).toUpperCase() + kind.slice(1);
    el.agentTypeMenu.querySelectorAll('[data-value]').forEach((li) => {
      li.setAttribute('aria-selected', li.dataset.value === kind ? 'true' : 'false');
    });
  }

  el.agentTypePillBtn.addEventListener('click', () =>
    toggleMenu(el.agentTypeMenu, el.agentTypePillBtn)
  );

  el.agentTypeMenu.addEventListener('click', (e) => {
    const item = e.target.closest('[data-value]');
    if (!item) return;
    applyKind(item.dataset.value);
    closeMenu(el.agentTypeMenu, el.agentTypePillBtn);
  });

  // ── Model selector ─────────────────────────────────────────────────────────
  // Providers grouped by prefix: "local/*" → Local, "openrouter/*" → OpenRouter, else → API
  function groupProviders(providers) {
    const groups = { Local: [], OpenRouter: [], API: [] };
    for (const p of providers) {
      if (p.startsWith('local/') || p.startsWith('local:')) groups.Local.push(p);
      else if (p.startsWith('openrouter/') || p.startsWith('openrouter:')) groups.OpenRouter.push(p);
      else groups.API.push(p);
    }
    return groups;
  }

  function populateModelMenu(providers) {
    el.modelMenu.innerHTML = '';
    const groups = groupProviders(providers);
    const ORDER = ['Local', 'API', 'OpenRouter'];

    for (const groupName of ORDER) {
      const list = groups[groupName];
      if (!list.length) continue;

      const header = document.createElement('li');
      header.className = 'chatbot__modelGroup';
      header.textContent = groupName;
      el.modelMenu.appendChild(header);

      for (const p of list) {
        const li = document.createElement('li');
        li.role = 'menuitem';
        li.dataset.value = p;
        li.textContent = p.replace(/^(local|openrouter)[/:]/i, '');
        el.modelMenu.appendChild(li);
      }
    }
  }

  function applyModel(model) {
    state.model = model;
    lsSet(LS_MODEL, model);
    const label = model.replace(/^(local|openrouter)[/:]/i, '') || model;
    el.modelBtnLabel.textContent = label || 'Model';
    el.modelMenu.querySelectorAll('[data-value]').forEach((li) => {
      li.setAttribute('aria-selected', li.dataset.value === model ? 'true' : 'false');
    });
  }

  el.modelBtn.addEventListener('click', () => toggleMenu(el.modelMenu, el.modelBtn));

  el.modelMenu.addEventListener('click', (e) => {
    const item = e.target.closest('[data-value]');
    if (!item) return;
    applyModel(item.dataset.value);
    closeMenu(el.modelMenu, el.modelBtn);
  });

  // ── File attachment ────────────────────────────────────────────────────────
  const MAX_FILE_BYTES = 10 * 1024 * 1024; // 10 MB
  const ALLOWED_TYPES = new Set([
    'image/jpeg', 'image/png', 'image/gif', 'image/webp',
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'text/plain', 'text/markdown', 'text/x-markdown',
    'application/json', 'text/json',
  ]);

  el.attachBtn.addEventListener('click', () => el.fileInput.click());

  el.fileInput.addEventListener('change', () => {
    el.attachError.hidden = true;
    const files = Array.from(el.fileInput.files || []);
    const errors = [];

    for (const f of files) {
      if (f.size > MAX_FILE_BYTES) {
        errors.push(`"${f.name}" is too large (max 10 MB).`);
        continue;
      }
      if (!ALLOWED_TYPES.has(f.type) && !f.name.endsWith('.json') && !f.name.endsWith('.md')) {
        errors.push(`"${f.name}" is not a supported file type.`);
        continue;
      }
      if (!state.attachedFiles.some((a) => a.name === f.name && a.size === f.size)) {
        state.attachedFiles.push(f);
      }
    }

    if (errors.length) {
      el.attachError.textContent = errors.join(' ');
      el.attachError.hidden = false;
    }

    el.fileInput.value = '';
    renderAttachChips();
  });

  function renderAttachChips() {
    el.attachments.innerHTML = '';
    if (!state.attachedFiles.length) {
      el.attachments.hidden = true;
      return;
    }
    el.attachments.hidden = false;
    for (let i = 0; i < state.attachedFiles.length; i++) {
      const f = state.attachedFiles[i];
      const chip = document.createElement('div');
      chip.className = 'chatbot__attachChip';
      chip.title = f.name;

      const name = document.createElement('span');
      name.textContent = f.name.length > 18 ? f.name.slice(0, 15) + '…' : f.name;

      const removeBtn = document.createElement('button');
      removeBtn.type = 'button';
      removeBtn.setAttribute('aria-label', `Remove ${f.name}`);
      removeBtn.textContent = '×';
      removeBtn.addEventListener('click', () => {
        state.attachedFiles.splice(i, 1);
        renderAttachChips();
      });

      chip.appendChild(name);
      chip.appendChild(removeBtn);
      el.attachments.appendChild(chip);
    }
  }

  // ── Send ───────────────────────────────────────────────────────────────────
  async function handleSend() {
    const text = (el.input.value || '').trim();
    if (!text) return;

    const isAgent = state.mode === 'agent';
    const kind    = state.kind;
    const model   = state.model;

    const fileNames = state.attachedFiles.map((f) => f.name).join(', ');
    appendMessage({
      role: 'user',
      text: fileNames ? `${text}\n[Attached: ${fileNames}]` : text,
    });

    el.input.value = '';
    autosizeTextarea();

    const stopThinking = appendThinking();

    try {
      if (isAgent) {
        // Agent mode: POST /v1/generate/{kind}
        // If files are attached, use FormData; otherwise JSON.
        let res;
        if (state.attachedFiles.length) {
          const form = new FormData();
          form.append('prompt', text);
          for (const f of state.attachedFiles) form.append('files', f);
          const headers = {};
          if (model) headers['X-LLM-Provider'] = model;
          const raw = await fetch(`${baseUrl}/v1/generate/${encodeURIComponent(kind)}`, {
            method: 'POST',
            headers,
            body: form,
          });
          const rawText = await raw.text();
          res = rawText ? JSON.parse(rawText) : null;
          if (!raw.ok) throw new Error(res?.detail || rawText || `${raw.status}`);
        } else {
          res = await httpJson(`/v1/generate/${encodeURIComponent(kind)}`, {
            method: 'POST',
            headers: model ? { 'X-LLM-Provider': model } : {},
            body: JSON.stringify({ prompt: text }),
          });
        }

        state.attachedFiles = [];
        renderAttachChips();

        const data = res?.data || {};
        const slug = data.slug || '';
        const draftPath = data.draft_path || '';
        stopThinking();

        let msg = `Created ${kind} draft.`;
        if (draftPath) msg += `\nDraft: ${draftPath}`;
        if (slug) msg += `\nSlug: ${slug}`;
        appendMessage({ role: 'ai', text: msg });

        if (slug) {
          appendPromoteButton(kind, slug);
        }
      } else {
        // Ask mode: POST /v1/chat
        const res = await httpJson('/v1/chat', {
          method: 'POST',
          headers: model ? { 'X-LLM-Provider': model } : {},
          body: JSON.stringify({ messages: [{ role: 'user', content: text }] }),
        });
        state.attachedFiles = [];
        renderAttachChips();
        stopThinking();
        const reply = res?.data?.message?.content || JSON.stringify(res?.data);
        appendMessage({ role: 'ai', text: reply });
      }
    } catch (e) {
      stopThinking();
      appendMessage({ role: 'ai', text: `Error: ${e.message}` });
    }
  }

  function appendPromoteButton(kind, slug) {
    const wrap = document.createElement('div');
    wrap.className = 'chatbot__msg chatbot__msg--ai';
    const bubble = document.createElement('div');
    bubble.className = 'chatbot__bubble';
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'btn btn-sm btn-success';
    btn.textContent = `Promote ${kind}/${slug}`;
    btn.onclick = async () => {
      btn.disabled = true;
      try {
        const promoted = await httpJson(
          `/v1/promote/${encodeURIComponent(kind)}/${encodeURIComponent(slug)}`,
          { method: 'POST' }
        );
        const to = promoted?.data?.to || '';
        appendMessage({ role: 'ai', text: to ? `Promoted to: ${to}` : 'Promoted.' });
      } catch (e) {
        appendMessage({ role: 'ai', text: `Promote failed: ${e.message}` });
      } finally {
        btn.disabled = false;
      }
    };
    bubble.appendChild(btn);
    wrap.appendChild(bubble);
    el.messages.appendChild(wrap);
    el.messages.scrollTop = el.messages.scrollHeight;
  }

  // ── Panel collapse / expand ────────────────────────────────────────────────
  function isCollapsed() {
    return document.documentElement.classList.contains('chatbot-collapsed');
  }
  function setCollapsed(collapsed) {
    document.documentElement.classList.toggle('chatbot-collapsed', collapsed);
    lsSet(LS_OPEN, collapsed ? 'false' : 'true');
  }

  function wireToggle() {
    if (el.toggle) el.toggle.addEventListener('click', () => setCollapsed(!isCollapsed()));
    if (el.floatToggle) el.floatToggle.addEventListener('click', () => setCollapsed(false));

    const icon = el.toggle?.querySelector('.chatbot__toggleIcon');
    const updateIcon = () => {
      if (icon) icon.textContent = isCollapsed() ? '‹' : '›';
    };
    updateIcon();
    new MutationObserver(updateIcon).observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['class'],
    });
  }

  // ── Bootstrap ─────────────────────────────────────────────────────────────
  async function loadMeta() {
    const [providersRes, gensRes] = await Promise.all([
      httpJson('/v1/meta/providers'),
      httpJson('/v1/meta/generators'),
    ]);

    const providers       = providersRes?.data?.providers || [];
    const defaultProvider = providersRes?.data?.default_provider || '';
    const kinds           = gensRes?.data?.generators || [];

    populateModelMenu(providers);
    const resolvedModel = providers.includes(state.model)
      ? state.model
      : (defaultProvider || providers[0] || '');
    applyModel(resolvedModel);

    populateAgentTypes(kinds);
    const resolvedKind = kinds.includes(state.kind)
      ? state.kind
      : (kinds.includes('npc') ? 'npc' : kinds[0] || 'npc');
    applyKind(resolvedKind);

    applyMode(state.mode);

    appendMessage({
      role: 'ai',
      text: 'Hi! Use Ask for questions or switch to Agent to generate NPCs, locations and more.',
    });
  }

  // ── Wire up inputs ─────────────────────────────────────────────────────────
  el.input.addEventListener('input', autosizeTextarea);
  el.input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  });
  el.send.addEventListener('click', handleSend);

  wireToggle();
  autosizeTextarea();

  loadMeta().catch((e) => {
    appendMessage({ role: 'ai', text: `Failed to connect: ${e.message}` });
    el.modelBtnLabel.textContent = 'Offline';
  });
})();
