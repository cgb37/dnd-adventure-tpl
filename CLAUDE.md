# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Jekyll (UI)
```bash
bundle exec jekyll build              # Build to _site/
bundle exec jekyll serve              # Dev server at localhost:4000
bundle exec jekyll build --destination _site-ui   # Build for Playwright
./jekyll-serve.sh                     # Local serve wrapper
```

### Playwright tests
```bash
npm run test:ui                       # Full run (Docker API + Jekyll build + Playwright)
npm run test:ui:headed                # Same, with visible browser
npx playwright test tests/ui/chatbot.spec.cjs        # Single test file
npx playwright test tests/ui/chatbot.spec.cjs --debug
HEADED=1 npx playwright test tests/ui/chatbot.spec.cjs
```

Tests require the Jekyll site built to `_site-ui` and the LLM API running. Playwright serves `_site-ui` via Python's `http.server` on port 4100. Test timeout: 180s; assertion timeout: 20s.

### LLM API (Python)
```bash
cd services/llm_api
pip install -e ".[dev]"
uvicorn llm_api.app:create_app --factory --reload --port 8000
pytest                                # API unit tests
```

### Docker
```bash
npm run start:docker:dub              # docker compose up --build
```

### Campaign management
```bash
./scripts/use-campaign <name>         # Activate campaign (symlinks _pages/_posts)
./scripts/use-campaign <name> --bootstrap --force
./scripts/promote-draft               # Move draft → published
./scripts/smoke-api                   # Smoke-test LLM API endpoints
```

## Architecture

### Overview
Static Jekyll UI + FastAPI LLM service. Jekyll renders DM campaign content; the LLM API generates Markdown drafts that are written to `campaigns/<name>/_drafts/` and later promoted to `campaigns/<name>/_pages/` via a promote endpoint.

### Campaign system
`.active-campaign` holds the current campaign name. `scripts/use-campaign` symlinks `_pages` and `_posts` from `campaigns/<name>/` into the repo root so Jekyll picks them up. Drafts live at `campaigns/<name>/_drafts/<kind>/<slug>.md`.

### Chatbot integration
The global chatbot widget (`_includes/chatbot_shell.html` + `assets/js/chatbot-widget.js`) is injected only on gated pages. Gating logic runs in `_layouts/default.html`:
1. Allow if `page.layout` is in `site.chatbot.enabled_layouts`
2. Allow if `page.url` matches `site.chatbot.enabled_url_prefixes`
3. Deny if `page.url` matches `disabled_url_prefixes` or `disabled_urls`

The widget (Iteration 5) stores mode (`ask`/`agent`), kind, and model in `localStorage`. It hits:
- `GET /v1/meta/providers` — populate model selector (grouped by `local/`, `openrouter/` prefix)
- `GET /v1/meta/generators` — populate agent-type selector
- `POST /v1/chat` (Ask mode) — plain chat; falls back to `/v1/generate/chat`
- `POST /v1/generate/{kind}` (Agent mode) — draft generation; supports `FormData` when files are attached
- `POST /v1/promote/{kind}/{slug}` — move draft to published

CSS drives agent-type visibility: `.chatbot__inputBox[data-mode="ask"] #agentTypeWrap { display:none }`.

### LLM API (`services/llm_api/`)
FastAPI app. Key modules:
- `routes/` — `generate.py`, `meta.py`, `promote.py`, `health.py`
- `generators/` — one file per kind (`npc.py`, `monster.py`, etc.); each returns YAML front-matter + Markdown body
- `services/` — `config.py` (Pydantic Settings, reads env vars), `active_campaign.py`, `drafts.py`, `security.py`

Auth: `X-API-Key` header required on `/v1/*`. Set `RELAX_AUTH_ON_LOCALHOST=true` to skip auth for `localhost` origins during local dev.

LLM providers (set via env): `mock` (default, no API key), `ollama`, `openai`, `anthropic`, `gemini`.

### Layout hierarchy
- `default.html` — base HTML shell, chatbot gating, injects `chatbot_shell.html` when enabled
- `split.html` — 66/33 flex layout (content left, chatbot right)
- Content layouts (`chapter.html`, `npc.html`, `monster.html`, etc.) extend `split.html` or `default.html`

### CSS / JS
- `assets/css/chatbot.css` — All chatbot styles, scoped to `#global-chatbot`. Contains both the base component styles and the strict always-visible split-layout overrides at the bottom.
- `assets/js/chatbot-widget.js` — Single IIFE, no build step required.
- No transpilation. Vanilla ES2020, Bootstrap 5.3 utility classes.

### Chatbot gating config (`_config.yml`)
```yaml
chatbot:
  enabled_layouts: [chapter, episode, scene, location, encounter, monster, npc, reward, dmnote, sessionprep, sessionrecap]
  enabled_url_prefixes: [/chapters/, /encounters/, /locations/, /monsters/, /npcs/, /rewards/]
  disabled_url_prefixes: [/tools/, /toc/]
  disabled_urls: [/, /404.html, /search-results.html, /search.json]
llm_api_base_url: "http://localhost:8000"
```
