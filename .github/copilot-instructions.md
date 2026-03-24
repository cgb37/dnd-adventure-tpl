<!-- Copilot instructions for dnd-adventure-tpl -->

# Quick orientation

- **Big picture:** this repo is a Jekyll-based D&D adventure template (UI/site) plus a small FastAPI LLM service (`services/llm_api`) used to generate draft campaign content. The UI is static Jekyll files (`_layouts`, `_includes`, `_posts`, `_pages`, `_data`) and the LLM service produces Markdown drafts into the `campaigns/<active>/_drafts/...` tree.

- **Primary integration points:**
  - `services/llm_api` — FastAPI that consumes prompts and writes draft Markdown.
  - Jekyll site — static UI served locally (see `jekyll-serve.sh` and `index.html`).
  - `campaigns/` — where generated drafts are persisted.
  - `docker-compose.yml` / `Dockerfile` — dev container orchestration for the API and optional services.

# What to know before editing code

- The LLM API is opinionated about where content lands: see `services/llm_api/README.md` and the `campaigns/<active>/_drafts/<kind>/<slug>.md` pattern. Changes to generation output shape must keep that file placement consistent.
- Stable IDs are generated (UUIDv5) from `{kind}:{campaign}:{slug}`; do not change the namespace constant without migration.
- Prompts and templates live in `_prompts/` — check these when adjusting generated content.

# Developer workflows (commands you will need)

- Run the LLM API locally:

  - Create a venv, install, and run:

    python -m venv .venv && source .venv/bin/activate
    pip install -e services/llm_api[dev]
    uvicorn llm_api.app:app --reload --port 8000

  - Env and settings are documented in `services/llm_api/README.md` and implemented in `services/llm_api/src/llm_api/services/config.py`.

- Run UI tests (Playwright):

  - `npm run test:ui` (see `playwright.config.cjs` and `package.json`).
  - If tests fail due to CORS/auth, ensure the API dev compose and `UI_ORIGIN` match (see `services/llm_api/README.md`).

- Run via Docker (dev compose):

  - `docker compose up --build api` (see `services/llm_api/Dockerfile` and `docker-compose.yml`).

# Security, envs, and auth quirks

- API requires `X-API-Key` on `/v1/*` endpoints. For local convenience the API supports `RELAX_AUTH_ON_LOCALHOST=true` (see `Settings.relax_auth_on_localhost`).
- Key envs and providers are enumerated in `services/llm_api/README.md` and `services/llm_api/src/llm_api/services/config.py` (e.g., `LLM_PROVIDER`, `OLLAMA_BASE_URL`, `OPENAI_API_KEY`, `DEBUG_PROMPTS`).
- By default CORS allows `http://localhost:4000`. Update `UI_ORIGIN` or `CORS_ALLOW_ORIGINS` in `.env` when testing different origins.

# Code patterns and conventions to follow

- Site content: Jekyll conventions — use `_layouts`, `_includes`, `_posts`, `_data`, and the `_plugins` scripts (`_plugins/*.rb`) which generate site JSON/search data. Keep front-matter YAML consistent with existing templates in `_frontmattertpls/`.
- LLM service: Pydantic/Pydantic-Settings `Settings` is the single place for configuration defaults — reference it for env names and types (`services/llm_api/src/llm_api/services/config.py`).
- Generated content: the LLM service writes draft Markdown files directly to `campaigns/`. When changing generation outputs, update any code that consumes the draft files (site build or downstream scripts).

# Useful examples

- Example API call (local):

  curl -X POST 'http://localhost:8000/v1/generate/npc' \
    -H 'X-API-Key: your_key' \
    -H 'Content-Type: application/json' \
    -d '{"campaign":"my-campaign","slug":"mysterious-bard","fields":{}}'

- Where to inspect prompts: `_prompts/ai-rpg-npc-generator.txt` (and other similar files).

# Files you will read first

- [services/llm_api/README.md](services/llm_api/README.md) — API behaviour, envs, run steps
- [services/llm_api/src/llm_api/services/config.py](services/llm_api/src/llm_api/services/config.py) — all env var names and defaults
- `_prompts/` — prompt templates used by the LLM service
- `campaigns/` — target location for generated drafts
- `playwright.config.cjs` and `package.json` — UI test configuration and scripts
- `docker-compose.yml`, `Dockerfile`, and `services/llm_api/Dockerfile` — docker/dev-compose setup

# When to ask for human review

- Any change that modifies where drafts are written in `campaigns/`.
- Any change to authentication logic (header names, relax_auth behaviour).
- Any change to prompt templates that materially alters structure of generated Markdown used by the site.

# Feedback

If anything here is unclear or you want more examples (e.g., typical request/response bodies, prompt structure, or a walk-through of a generation -> file flow), tell me which area and I'll expand.
