(() => {
  const baseUrl = (window.LLM_API_BASE_URL || "http://localhost:8000").replace(/\/$/, "");

  const output = document.getElementById("output");
  const input = document.getElementById("chatInput");
  const sendBtn = document.getElementById("sendBtn");
  const clearBtn = document.getElementById("clearBtn");
  const providerSelect = document.getElementById("llmProvider");
  const schemaPanel = document.getElementById("schemaPanel");

  const LS_PROVIDER_KEY = "dnd_llm_provider";

  let currentKind = null;
  let currentSchema = null;
  let lastGenerated = null;

  function log(msg) {
    output.textContent += `${msg}\n`;
  }

  function clearLog() {
    output.textContent = "";
  }

  function normalizeKind(kind) {
    return (kind || "")
      .trim()
      .toLowerCase()
      .replaceAll("_", "-")
      .replaceAll(" ", "-")
      .replace(/-+/g, "-");
  }

  async function httpJson(path, opts = {}) {
    // IMPORTANT: Spread order matters. If `opts.headers` is provided, it must not
    // clobber the default Content-Type header (otherwise FastAPI will treat the
    // body as raw bytes and validation will fail).
    const headers = {
      "Content-Type": "application/json",
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

  function renderSchema(kind, schema) {
    schemaPanel.innerHTML = "";

    if (!schema) return;

    const title = document.createElement("div");
    title.className = "mb-2";
    title.innerHTML = `<strong>Generator:</strong> <code>${kind}</code>`;
    schemaPanel.appendChild(title);

    const required = (schema.required || []).filter((f) => f !== "prompt");
    const optional = (schema.optional || []).filter((f) => f !== "prompt");
    const props = schema.properties || {};

    const field = (name) => {
      const wrap = document.createElement("div");
      wrap.className = "mb-2";

      const label = document.createElement("label");
      label.className = "form-label";
      label.textContent = name;

      let input;

      if (name === "constraints") {
        input = document.createElement("textarea");
        input.className = "form-control";
        input.rows = 3;
        input.placeholder = '{"key": "value"}';
      } else {
        input = document.createElement("input");
        input.className = "form-control";
        input.type = name === "seed" ? "number" : "text";
      }

      input.dataset.field = name;

      const defv = props[name]?.default;
      if (defv !== null && defv !== undefined) {
        input.value = String(defv);
      }

      wrap.appendChild(label);
      wrap.appendChild(input);

      const desc = props[name]?.description;
      if (desc) {
        const help = document.createElement("div");
        help.className = "form-text";
        help.textContent = desc;
        wrap.appendChild(help);
      }

      return wrap;
    };

    if (required.length) {
      const reqTitle = document.createElement("div");
      reqTitle.className = "form-text mb-1";
      reqTitle.textContent = "Required";
      schemaPanel.appendChild(reqTitle);
      for (const f of required) schemaPanel.appendChild(field(f));
    }

    if (optional.length) {
      const details = document.createElement("details");
      details.className = "mt-2";

      const sum = document.createElement("summary");
      sum.textContent = "Optional";

      details.appendChild(sum);
      for (const f of optional) details.appendChild(field(f));

      schemaPanel.appendChild(details);
    }

    const promoteWrap = document.createElement("div");
    promoteWrap.id = "promoteWrap";
    promoteWrap.className = "mt-3";
    schemaPanel.appendChild(promoteWrap);
  }

  function collectSchemaValues() {
    const values = {};
    const inputs = schemaPanel.querySelectorAll("[data-field]");

    for (const el of inputs) {
      const name = el.dataset.field;
      const raw = (el.value || "").trim();
      if (!raw) continue;

      if (name === "seed") {
        const n = Number(raw);
        if (!Number.isFinite(n)) throw new Error("seed must be a number");
        values.seed = n;
        continue;
      }

      if (name === "constraints") {
        try {
          const obj = JSON.parse(raw);
          if (obj && typeof obj === "object" && !Array.isArray(obj)) {
            values.constraints = obj;
          } else {
            throw new Error("constraints must be a JSON object");
          }
        } catch (e) {
          throw new Error(`constraints must be valid JSON: ${e.message}`);
        }
        continue;
      }

      values[name] = raw;
    }

    return values;
  }

  function renderPromoteControls(kind, slug) {
    const wrap = document.getElementById("promoteWrap");
    if (!wrap) return;

    wrap.innerHTML = "";

    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "btn btn-success";
    btn.textContent = `Promote ${kind}/${slug}`;

    btn.onclick = async () => {
      btn.disabled = true;
      try {
        const res = await httpJson(`/v1/promote/${encodeURIComponent(kind)}/${encodeURIComponent(slug)}`, {
          method: "POST",
        });
        log(`Promoted to: ${res?.data?.to || "(unknown)"}`);
      } catch (e) {
        log(`Promote failed: ${e.message}`);
        log(`CLI fallback: ./scripts/promote-draft "${kind}" "${slug}"`);
      } finally {
        btn.disabled = false;
      }
    };

    const cli = document.createElement("div");
    cli.className = "form-text mt-2";
    cli.textContent = `CLI fallback: ./scripts/promote-draft "${kind}" "${slug}"`;

    wrap.appendChild(btn);
    wrap.appendChild(cli);
  }

  async function loadMeta() {
    const providersRes = await httpJson("/v1/meta/providers");
    const providers = providersRes?.data?.providers || [];
    const defaultProvider = providersRes?.data?.default_provider || "";

    providerSelect.innerHTML = "";
    for (const p of providers) {
      const opt = document.createElement("option");
      opt.value = p;
      opt.textContent = p;
      providerSelect.appendChild(opt);
    }

    const saved = localStorage.getItem(LS_PROVIDER_KEY);
    if (saved && providers.includes(saved)) {
      providerSelect.value = saved;
    } else if (defaultProvider && providers.includes(defaultProvider)) {
      providerSelect.value = defaultProvider;
    }

    providerSelect.addEventListener("change", () => {
      localStorage.setItem(LS_PROVIDER_KEY, providerSelect.value);
    });

    const gensRes = await httpJson("/v1/meta/generators");
    const gens = gensRes?.data?.generators || [];
    log(`Generators: ${gens.join(", ")}`);
  }

  async function setGenerator(kindRaw) {
    const kind = normalizeKind(kindRaw);
    if (!kind) throw new Error("Usage: /generate <kind>");

    const schemaRes = await httpJson(`/v1/meta/schema/${encodeURIComponent(kind)}`);
    currentKind = schemaRes?.data?.kind || kind;
    currentSchema = schemaRes?.data?.schema || null;

    renderSchema(currentKind, currentSchema);
    log(`Selected generator: ${currentKind}`);
  }

  async function doGenerate(prompt) {
    if (!currentKind) throw new Error('Select a generator first (e.g. "/generate npc")');

    const provider = providerSelect.value;
    const extras = collectSchemaValues();

    const payload = {
      prompt,
      ...extras,
    };

    const res = await httpJson(`/v1/generate/${encodeURIComponent(currentKind)}`, {
      method: "POST",
      headers: {
        "X-LLM-Provider": provider,
      },
      body: JSON.stringify(payload),
    });

    const data = res?.data || {};
    lastGenerated = data;

    log(`draft_path=${data.draft_path || ""}`);
    log(`slug=${data.slug || ""} id=${data.id || ""}`);

    if (data.slug) {
      renderPromoteControls(currentKind, data.slug);
    }
  }

  async function handleInput(text) {
    const t = (text || "").trim();
    if (!t) return;

    if (t.startsWith("/generate")) {
      const rest = t.slice("/generate".length).trim();
      await setGenerator(rest);
      return;
    }

    if (t.startsWith("/")) {
      throw new Error('Unknown command. Try: /generate npc');
    }

    await doGenerate(t);
  }

  async function onSend() {
    const text = input.value;
    input.value = "";

    try {
      await handleInput(text);
    } catch (e) {
      log(`Error: ${e.message}`);
    }
  }

  sendBtn.addEventListener("click", onSend);
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") onSend();
  });

  clearBtn.addEventListener("click", clearLog);

  loadMeta().catch((e) => log(`Failed to load metadata: ${e.message}`));
})();
