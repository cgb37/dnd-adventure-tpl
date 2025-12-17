(() => {
  const baseUrl = (window.LLM_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '');

  const LS_OPEN_KEY = 'dnd_global_chatbot_open';
  const LS_PROVIDER_KEY = 'dnd_global_chatbot_provider';
  const LS_KIND_KEY = 'dnd_global_chatbot_kind';

  const elPanel = document.querySelector('#global-chatbot .chatbot__panel');
  const elToggle = document.getElementById('chatbotToggle');
  const elFloatingToggle = document.getElementById('chatbotFloatingToggle');
  const elProvider = document.getElementById('chatbotProvider');
  const elKind = document.getElementById('chatbotKind');
  const elMessages = document.getElementById('chatbotMessages');
  const elInput = document.getElementById('chatbotInput');
  const elSend = document.getElementById('chatbotSend');

  if (!elPanel || !elToggle || !elFloatingToggle || !elProvider || !elKind || !elMessages || !elInput || !elSend) {
    return;
  }

  function isCollapsed() {
    return document.documentElement.classList.contains('chatbot-collapsed');
  }

  function setCollapsed(collapsed) {
    if (collapsed) {
      document.documentElement.classList.add('chatbot-collapsed');
      try {
        localStorage.setItem(LS_OPEN_KEY, 'false');
      } catch (_) {
        // ignore
      }
    } else {
      document.documentElement.classList.remove('chatbot-collapsed');
      try {
        localStorage.setItem(LS_OPEN_KEY, 'true');
      } catch (_) {
        // ignore
      }
    }
  }

  function appendMessage({ role, text, meta }) {
    const wrap = document.createElement('div');
    wrap.className = `chatbot__msg chatbot__msg--${role}`;

    const bubble = document.createElement('div');
    bubble.className = 'chatbot__bubble';
    bubble.textContent = text;

    wrap.appendChild(bubble);

    if (meta) {
      const m = document.createElement('div');
      m.className = 'chatbot__meta';
      m.textContent = meta;
      bubble.appendChild(m);
    }

    elMessages.appendChild(wrap);
    elMessages.scrollTop = elMessages.scrollHeight;
  }

  function appendThinking() {
    const wrap = document.createElement('div');
    wrap.className = 'chatbot__msg chatbot__msg--ai';
    wrap.dataset.thinking = 'true';

    const bubble = document.createElement('div');
    bubble.className = 'chatbot__bubble';
    bubble.textContent = 'Thinking…';

    wrap.appendChild(bubble);
    elMessages.appendChild(wrap);
    elMessages.scrollTop = elMessages.scrollHeight;

    return () => {
      wrap.remove();
    };
  }

  function normalizeKind(kind) {
    return (kind || '')
      .trim()
      .toLowerCase()
      .replaceAll('_', '-')
      .replaceAll(' ', '-')
      .replace(/-+/g, '-');
  }

  async function httpJson(path, opts = {}) {
    const headers = {
      'Content-Type': 'application/json',
      ...(opts.headers || {}),
    };

    const res = await fetch(`${baseUrl}${path}`, {
      ...opts,
      headers,
    });

    const text = await res.text();
    let body = null;
    try {
      body = text ? JSON.parse(text) : null;
    } catch {
      // ignore
    }

    if (!res.ok) {
      const detail = body?.error?.message || body?.detail || text || `${res.status}`;
      throw new Error(detail);
    }

    return body;
  }

  function autosizeTextarea() {
    elInput.style.height = 'auto';
    const maxLines = 5;
    const lineHeight = 24; // close enough for Bootstrap default
    const maxHeight = maxLines * lineHeight + 16;
    elInput.style.height = `${Math.min(elInput.scrollHeight, maxHeight)}px`;
  }

  function getSelectedProvider() {
    return (elProvider.value || '').trim();
  }

  function getSelectedKind() {
    return normalizeKind(elKind.value || 'npc');
  }

  function setProviderFromStorage() {
    try {
      const saved = localStorage.getItem(LS_PROVIDER_KEY);
      if (saved) elProvider.value = saved;
    } catch (_) {
      // ignore
    }
  }

  function setKindFromStorage() {
    try {
      const saved = localStorage.getItem(LS_KIND_KEY);
      if (saved) elKind.value = saved;
    } catch (_) {
      // ignore
    }
  }

  async function loadMeta() {
    const providersRes = await httpJson('/v1/meta/providers');
    const providers = providersRes?.data?.providers || [];
    const defaultProvider = providersRes?.data?.default_provider || '';

    elProvider.innerHTML = '';
    for (const p of providers) {
      const opt = document.createElement('option');
      opt.value = p;
      opt.textContent = p;
      elProvider.appendChild(opt);
    }

    setProviderFromStorage();
    if (!elProvider.value && defaultProvider && providers.includes(defaultProvider)) {
      elProvider.value = defaultProvider;
    }
    if (!elProvider.value && providers.length) {
      elProvider.value = providers[0];
    }

    elProvider.addEventListener('change', () => {
      try {
        localStorage.setItem(LS_PROVIDER_KEY, elProvider.value);
      } catch (_) {
        // ignore
      }
    });

    const gensRes = await httpJson('/v1/meta/generators');
    const gens = gensRes?.data?.generators || [];

    elKind.innerHTML = '';
    for (const k of gens) {
      const opt = document.createElement('option');
      opt.value = k;
      opt.textContent = k;
      elKind.appendChild(opt);
    }

    // Prefer a DM-oriented default.
    if (gens.includes('npc')) elKind.value = 'npc';

    setKindFromStorage();
    if (!elKind.value && gens.length) {
      elKind.value = gens[0];
    }

    elKind.addEventListener('change', () => {
      try {
        localStorage.setItem(LS_KIND_KEY, elKind.value);
      } catch (_) {
        // ignore
      }
    });

    appendMessage({
      role: 'ai',
      text: 'Hi! Select a generator and tell me what you want to create.',
      meta: 'Tip: include details like level, class, alignment, or leave it open-ended.',
    });
  }

  async function handleSend() {
    const text = (elInput.value || '').trim();
    if (!text) return;

    const kind = getSelectedKind();
    const provider = getSelectedProvider();

    appendMessage({ role: 'user', text });
    elInput.value = '';
    autosizeTextarea();

    const stopThinking = appendThinking();

    try {
      const res = await httpJson(`/v1/generate/${encodeURIComponent(kind)}`, {
        method: 'POST',
        headers: {
          'X-LLM-Provider': provider,
        },
        body: JSON.stringify({ prompt: text }),
      });

      const data = res?.data || {};
      const slug = data.slug || '';
      const draftPath = data.draft_path || '';

      stopThinking();

      let msg = `Created ${kind} draft.`;
      if (draftPath) msg += `\nDraft: ${draftPath}`;
      if (slug) msg += `\nSlug: ${slug}`;

      appendMessage({ role: 'ai', text: msg });

      if (slug) {
        const promoteText = `Promote ${kind}/${slug}`;
        const wrap = document.createElement('div');
        wrap.className = 'chatbot__msg chatbot__msg--ai';

        const bubble = document.createElement('div');
        bubble.className = 'chatbot__bubble';

        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'btn btn-sm btn-success';
        btn.textContent = promoteText;

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
        elMessages.appendChild(wrap);
        elMessages.scrollTop = elMessages.scrollHeight;
      }
    } catch (e) {
      stopThinking();
      appendMessage({ role: 'ai', text: `Error: ${e.message}` });
    }
  }

  function wireToggle() {
    const onToggle = () => setCollapsed(!isCollapsed());
    elToggle.addEventListener('click', onToggle);
    elFloatingToggle.addEventListener('click', () => setCollapsed(false));

    // Reflect direction in the header icon.
    const icon = elToggle.querySelector('.chatbot__toggleIcon');
    const updateIcon = () => {
      if (!icon) return;
      icon.textContent = isCollapsed() ? '‹' : '›';
    };

    updateIcon();

    const obs = new MutationObserver(updateIcon);
    obs.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });
  }

  elInput.addEventListener('input', autosizeTextarea);
  elInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  });

  elSend.addEventListener('click', handleSend);

  wireToggle();
  autosizeTextarea();

  loadMeta().catch((e) => {
    appendMessage({ role: 'ai', text: `Failed to load metadata: ${e.message}` });
  });
})();
