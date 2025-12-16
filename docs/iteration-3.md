# Iteration 3 — Jekyll UI Chatbot + API Metadata + Draft Promotion

This document explains the Iteration 3 changes: a small Jekyll-hosted “chatbot” UI that drives the existing FastAPI LLM draft generation service, plus metadata endpoints for UI discovery, a promotion workflow (API + CLI), and automated UI testing.

## Goals (what we built)

- A developer-facing UI page at `/tools/chat/` inside the Jekyll site.
- A thin JS client that:
  - Loads available providers and generators from the API.
  - Accepts slash commands like `/generate npc`.
  - Fetches a schema for the selected generator.
  - Calls `POST /v1/generate/{kind}` to write a draft into the active campaign.
  - Calls `POST /v1/promote/{kind}/{slug}` to move the draft into `_pages/...`.
  - Sends a per-request provider override via `X-LLM-Provider`.
- FastAPI endpoints to support the UI:
  - `GET /v1/meta/providers`
  - `GET /v1/meta/generators`
  - `GET /v1/meta/schema/{kind}`
  - `POST /v1/promote/{kind}/{slug}`
- A CLI helper for promotion: `scripts/promote-draft`.
- End-to-end UI smoke testing with Playwright.

## Why this approach

### Static UI + local API

Jekyll produces a static site, which is ideal for campaign content. Rather than embedding model calls into the site generator (Ruby), we keep “LLM generation” as a separate FastAPI service (Python) and let the static UI talk to it via HTTP.

This keeps responsibilities clean:

- **Jekyll/Ruby**: builds the site and renders content.
- **JS (browser)**: minimal interactive UX, no secrets.
- **FastAPI/Python**: does generation, writes drafts, enforces rules/security.

### Metadata-driven UI

Instead of hard-coding “what fields does a generator need?” in the UI, the UI asks the API for a schema. This reduces drift and makes adding new generator inputs a server-owned decision.

## Key workflows

### 1) Select generator

In the UI:

- `/generate npc`

The UI normalizes the kind to kebab-case, fetches schema, then renders inputs.

### 2) Generate

The UI submits:

- `POST /v1/generate/{kind}`
- JSON body: `{"prompt": "...", ...optional fields...}`
- Header: `X-LLM-Provider: <provider>`

The API:

- Normalizes `kind`.
- Uses the active campaign (`.active-campaign`).
- Runs the generator.
- Writes a draft under:
  - `campaigns/<active>/_drafts/<kind>/<slug>.md`

### 3) Promote

The UI (or CLI) triggers:

- `POST /v1/promote/{kind}/{slug}`

The API:

- Validates kind + slug.
- Applies the canonical mapping.
- Moves the file from `_drafts` to `_pages`.

Important: promotion changes the campaign submodule working tree. Commit promoted content in the campaign repo.

## Files and ownership

### Jekyll (Ruby) site

- `_config.yml`
  - Adds `llm_api_base_url` for the UI.
- `tools/chat/index.md`
  - Adds the `/tools/chat/` page.

Jekyll builds the page into `_site/tools/chat/index.html`.

### JavaScript (browser UI)

- `assets/js/llm-chatbot.js`
  - Renders the UI behavior.
  - Fetches metadata (`/v1/meta/*`).
  - Issues generate/promote requests.
  - Persists provider selection to `localStorage`.

Design note: header merge order matters. The client sets `Content-Type: application/json` and then overlays custom headers (like `X-LLM-Provider`) so it does not accidentally clobber the content type.

### FastAPI (Python service)

App wiring:

- `services/llm_api/src/llm_api/app.py`
  - Installs CORS middleware.
  - Registers routes:
    - `/v1/generate/...`
    - `/v1/meta/...`
    - `/v1/promote/...`

Routes:

- `services/llm_api/src/llm_api/routes/generate.py`
  - Reads header `X-LLM-Provider`.
  - Normalizes kind.
  - Dispatches to the correct generator.

- `services/llm_api/src/llm_api/routes/meta.py`
  - `GET /v1/meta/providers` returns configured providers.
  - `GET /v1/meta/generators` lists supported kinds.
  - `GET /v1/meta/schema/{kind}` returns the schema for that generator.

- `services/llm_api/src/llm_api/routes/promote.py`
  - Promotes draft → `_pages` using mapping.

Generator dispatch:

- `services/llm_api/src/llm_api/generators/dispatch.py`
  - Contains `SUPPORTED_KINDS` and dispatch function.

Generators (currently shared request model, per-generator output model):

- `services/llm_api/src/llm_api/generators/npc.py`
- `services/llm_api/src/llm_api/generators/monster.py`
- `services/llm_api/src/llm_api/generators/encounter.py`
- `services/llm_api/src/llm_api/generators/chapter.py`
- `services/llm_api/src/llm_api/generators/location.py`

Provider creation:

- `services/llm_api/src/llm_api/providers/factory.py`
  - Uses `provider_override` if provided.
  - Throws `ApiError` for unknown/unconfigured providers.

Schema & kinds:

- `services/llm_api/src/llm_api/services/kinds.py`
  - Canonicalizes kind names into kebab-case.

- `services/llm_api/src/llm_api/services/registry.py`
  - Exposes `schema_for_kind()` used by `/v1/meta/schema/{kind}`.
  - Skips `PydanticUndefined` defaults (not JSON serializable).

Promotion logic:

- `services/llm_api/src/llm_api/services/promotion_mapping.py`
  - Canonical mapping table from `kind` → target `_pages` folder.

- `services/llm_api/src/llm_api/services/promotion.py`
  - Validates slug to prevent path traversal.
  - Moves draft → promoted path.

Errors:

- `services/llm_api/src/llm_api/services/errors.py`
  - Installs exception handlers.
  - Sanitizes validation errors (e.g., byte values) into JSON-safe strings.

Security gate:

- `services/llm_api/src/llm_api/services/security.py`
  - Enforces `X-API-Key` by default.
  - Supports local-dev relaxation (see Security section).

### CLI promotion helper

- `scripts/promote-draft`
  - Runs `python3 -m llm_api.scripts.promote_draft <kind> <slug>`

- `services/llm_api/src/llm_api/scripts/promote_draft.py`
  - Promotes without needing the web UI.

### UI testing (Node + Playwright)

- `package.json`, `package-lock.json`
- `playwright.config.cjs`
- `tests/ui/chatbot.spec.cjs`

The UI test serves the built `_site/` directory on port 4100 to avoid Jekyll live-reload flakiness.

## How to add a new generator kind (end-to-end)

A “kind” is the canonical identifier used by:

- API route: `/v1/generate/{kind}`
- Draft directory: `_drafts/<kind>/...`
- Promotion mapping key
- UI command: `/generate <kind>`

### Step 1 — Create the generator module

Create a new generator file:

- `services/llm_api/src/llm_api/generators/<kind>.py`

Follow the existing pattern:

- Define an output Pydantic model.
- Create a `GeneratedDraft` subclass.
- Implement `async def generate_<kind>(..., provider_override: str | None = None)`.

### Step 2 — Register it in dispatch

Update:

- `services/llm_api/src/llm_api/generators/dispatch.py`

Add the kind to `SUPPORTED_KINDS` and route to the generator.

### Step 3 — Update promotion mapping (if promotable)

If you want `/v1/promote/...` to work for this kind, update:

- `services/llm_api/src/llm_api/services/promotion_mapping.py`

Add a `PromotionRule` mapping for the new kind.

### Step 4 — Update the UI “Commands” list (optional)

The UI can discover generator kinds from the API, but the command help text is static.

Update:

- `tools/chat/index.md`

### Step 5 — Decide on request model changes

Right now all generators share the same request model (see `llm_api.models.requests.GenerateRequest`).

If a new kind needs custom fields, the intended future direction is:

- Create a per-kind request model.
- Update `registry.get_request_model_for_kind()` to return it.
- Ensure `/v1/meta/schema/{kind}` reflects the new fields.

This keeps the UI in sync without hard-coding.

## How to add a new provider

Providers are selected in two ways:

- Default provider comes from server env (`LLM_PROVIDER`).
- Per-request provider override comes from `X-LLM-Provider`.

Add provider support by:

1) Updating `services/llm_api/src/llm_api/providers/factory.py` to construct the correct PydanticAI model/provider.
2) Updating `services/llm_api/src/llm_api/routes/meta.py` so `/v1/meta/providers` lists the provider only when its required env vars are set.

## Configuration

### Jekyll

- `_config.yml` sets `llm_api_base_url` (defaults to `http://localhost:8000`).

### API env vars

See:

- `services/llm_api/.env.example`

Important knobs:

- `LLM_API_KEY` (required unless relax mode allows bypass)
- `LLM_PROVIDER` (default provider)
- `RELAX_AUTH_ON_LOCALHOST` (developer convenience)
- `CORS_ALLOW_ORIGINS` (used only when relax mode is off)

## Security

### What we enforce

- API key auth via `X-API-Key` (FastAPI dependency `require_api_key`).
- Per-request provider override via `X-LLM-Provider` is treated as a *selection* input; it does not grant access.
- Slug validation in promotion to prevent path traversal:
  - no `/` or `\\`
  - no `..`
- CORS:
  - In strict mode: allowlist configured via `CORS_ALLOW_ORIGINS`.
  - In relaxed local dev mode: CORS restrictions are disabled to avoid localhost-port friction.

### Local dev relax mode (tradeoffs)

When `RELAX_AUTH_ON_LOCALHOST=true`:

- Requests from localhost are allowed without `X-API-Key`.
- CORS is set permissively to allow browser tooling from any local port.

This is intentionally developer-friendly but should be considered unsafe outside local development.

Recommended production stance:

- `RELAX_AUTH_ON_LOCALHOST=false`
- Set a narrow `CORS_ALLOW_ORIGINS`
- Use a real `LLM_API_KEY`

### Client-side constraints

The Jekyll UI is static JS and should not embed secrets.

Even in strict mode, if you ever choose to add API keys to the browser, assume they are publicly accessible to any user who can load the page.

## Testing

### Backend tests (pytest)

Run backend tests inside the API container:

- `docker compose exec -T api pytest -q`

### UI tests (Playwright)

- `npm install`
- `npx playwright install chromium` (first time)
- `npm run test:ui`

`test:ui` rebuilds Jekyll via Docker then runs Playwright.

Notes:

- Playwright serves `_site/` from a static server during tests to avoid Jekyll live-reload flakiness.
- The UI test generates content and then cleans up its promoted file to avoid leaving artifacts.

## Operational notes / best practices

- Keep generated `_data/*.yml` treated as build artifacts.
- Draft generation writes into the active campaign submodule; promotion moves files inside that repo.
  - Commit generated/published content in the campaign repo as a separate commit.
- Prefer adding new generator fields server-side (Pydantic model) so the UI schema endpoint remains the source of truth.
- When changing CORS/auth behavior, validate with a browser preflight (OPTIONS) from the UI origin.

## Troubleshooting

- UI shows “Failed to load metadata”:
  - Ensure the API is running and reachable at the configured base URL.
  - If the UI is served from a non-4000 port, either enable relax mode for local dev or configure CORS allowlist.

- API returns 422 validation errors:
  - Check that the browser request includes `Content-Type: application/json`.
  - Inspect the UI console logs and network tab for request payload.

- Promote fails with 409:
  - The target already exists; pick a new slug or delete the existing file.
