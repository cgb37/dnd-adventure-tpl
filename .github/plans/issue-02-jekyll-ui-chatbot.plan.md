````markdown
# Iteration 3 — Jekyll UI Chatbot + Metadata + Promotion

## Goal
Add a **Jekyll-based UI chatbot** that can drive the existing LLM draft-generation API, including:
- Selecting an LLM **provider** from a dropdown (based on `.env` / server config)
- Using slash commands like `/generate npc` to select a generator
- Prompting for required/optional generator fields (derived from FastAPI Pydantic request models)
- Generating a draft Markdown file into the active campaign’s `_drafts` folder
- Promoting drafts into the appropriate `_pages` folder using a defined mapping (via API and CLI)

## Context / Decisions (from clarifications)
- Jekyll runs at `http://localhost:4000`.
- FastAPI runs at `http://localhost:8000`.
- Ollama runs locally on the host:
  - Host access: `http://localhost:11434`
  - Docker access: `http://host.docker.internal:11434`
- Campaign content is a separate repo as a submodule under `campaigns/<campaign>/`.
- Generation writes **drafts only**:
  - `campaigns/<active>/_drafts/<kind>/<slug>.md`
- Promotion moves draft -> `_pages/...` following a canonical mapping table.
- Canonical `kind` identifier is **kebab-case** everywhere (API routes, folders, frontmatter).
  - Python module filenames remain **snake_case**.
- UI provider selection persists **until changed** (localStorage).
- Model selection stays fixed in `.env` (no model picker in UI).
- Required/optional input fields come from **FastAPI Pydantic models** (API is source of truth).
- Security (dev): relax auth on localhost (UI can call API without `X-API-Key`).
  - Keep strict auth available via env for future hardening.
- Provider selection is passed per-request using header: `X-LLM-Provider`.

## Non-goals
- Production-grade secret handling inside a static client.
- Full “chat” conversation persistence across sessions.
- Auto-PR creation or CI-driven publish workflows.

## API Additions
### Metadata endpoints (UI discovery)
- `GET /v1/meta/generators`
  - Returns the list of supported generator `kind`s (kebab-case).
- `GET /v1/meta/schema/{kind}`
  - Returns a minimal schema derived from the generator’s Pydantic request model:
    - required fields
    - optional fields
    - property annotations/defaults
- `GET /v1/meta/providers`
  - Returns the list of configured providers based on the server environment.

### Promotion endpoint
- `POST /v1/promote/{kind}/{slug}`
  - Moves `campaigns/<active>/_drafts/<kind>/<slug>.md` to the mapped `_pages` location.
  - Prevents overwrites by default (409 if target exists).

## Jekyll UI Additions
- A template-owned page at `/tools/chat/`.
- A small JS client that:
  - Fetches providers and generator kinds from metadata endpoints
  - Persists selected provider to localStorage
  - Parses commands:
    - `/generate <kind>` (accepts spaces/underscores; normalizes to kebab-case)
  - Submits generation requests with:
    - JSON body containing prompt + schema fields
    - Header `X-LLM-Provider: <provider>`
  - Shows draft path and a Promote button
  - Displays a CLI fallback command if promotion fails

## Canonical Promotion Mapping Table
Drafts remain:
- `_drafts/<kind>/<slug>.md`

Promotion targets:
- `encounter` -> `_pages/encounters/<slug>.md`
- `encounter-table` -> `_pages/encounter-tables/<slug>.md`
- `location` -> `_pages/locations/<slug>.md`
- `monster` -> `_pages/monsters/<slug>.md`
- `npc` -> `_pages/npcs/<slug>.md`
- `character` -> `_pages/characters/<slug>.md`

## Acceptance Criteria
- UI page loads at `/tools/chat/` and successfully:
  - lists providers + generators (from API metadata)
  - supports `/generate npc` and `/generate encounter table`
  - submits generation requests and writes drafts to `_drafts/<kind>/...`
  - can promote via API endpoint and via CLI script
- Kind normalization is consistent across UI and API.
- Provider override is sent using `X-LLM-Provider` and reflected in API logs.

## Risks / Notes
- Static JS cannot securely store secrets; localhost relaxed auth is dev-only.
- Promotion modifies the campaign submodule working tree; users should commit changes in the campaign repo separately.

````
