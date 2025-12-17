# Iteration 4 — Global Chatbot UI (Split View) + DM-Page Gating + Stable UI Test Builds

This document explains the Iteration 4 changes: a **global, always-available chatbot UI** that is injected into DM-facing content pages (chapters/locations/monsters/encounters/npcs/rewards/etc.) and excluded from site utility pages (home, search, tools, quick links/toc). It also covers the supporting **Jekyll gating configuration**, **front-end widget implementation**, and **Playwright UI test stabilization**.

This iteration intentionally reuses the existing Iteration 3 FastAPI endpoints for metadata, generation, and promotion.

## Goals (what we built)

- A **global chatbot shell** rendered on DM content pages via the shared layout.
- **Desktop/tablet split view**:
  - Left: main content (~70%).
  - Right: chatbot panel (~30%).
- **Mobile bottom drawer** behavior.
- A **true chat UX** (message bubbles, loading indicator, multi-line textarea, Enter-to-send).
- **State persistence** across navigation via `localStorage`:
  - open/collapsed state
  - selected provider
  - selected generator kind
- Conservative **page inclusion/exclusion** so the widget does not appear on tools, toc, home, search.
- A dedicated Jekyll build destination for UI tests (`_site-ui/`) to avoid flakiness when `jekyll serve` is running.

## Why this approach

### Make the assistant feel “built in”

Iteration 3 provided a `/tools/chat/` page. Iteration 4 makes the assistant feel like a **first-class part of the DM reading experience** by rendering it alongside the content.

### Keep model calls out of Jekyll

As in Iteration 3, the Jekyll site remains static and does not call LLMs during build time. The global widget is just a front-end client that calls the existing API.

### Conservative gating

The primary risk of a global widget is “polluting” non-DM pages. Iteration 4 implements an allowlist+denylist strategy so the chatbot only appears where intended.

## Page inclusion/exclusion (gating)

Gating is driven by configuration in `_config.yml` under the `chatbot:` key.

### Allow rules

The chatbot is enabled when either:

- `page.layout` matches one of `chatbot.enabled_layouts`, OR
- `page.url` starts with one of `chatbot.enabled_url_prefixes`.

### Deny rules

If enabled by allow rules, it can still be disabled when:

- `page.url` starts with one of `chatbot.disabled_url_prefixes`, OR
- `page.url` equals one of `chatbot.disabled_urls`.

### Implementation details (Liquid)

The gating logic lives in `_layouts/default.html` and computes a `chatbot_enabled` flag.

Important implementation note:

- Liquid does not reliably support `p.size` for strings. Prefix slicing uses `p | size`.

This was a key fix: without it, the prefix checks could silently fail and the chatbot would not render on expected DM pages.

## Jekyll layout + include structure

### `_layouts/default.html`

Changes:

- Computes `chatbot_enabled` using the allowlist/denylist rules described above.
- Adds a `with-chatbot` class to `#page-container` when enabled.
- Conditionally renders the global shell with:
  - `{% include chatbot_shell.html %}`

### `_includes/styles.html`

Adds the global stylesheet:

- `assets/css/chatbot.css`

### `_includes/chatbot_shell.html`

Defines the global widget markup.

Responsibilities:

- Adds a tiny inline script that applies the persisted collapsed state early (to reduce layout flicker).
- Renders the chatbot panel DOM (`#global-chatbot`).
- Sets `window.LLM_API_BASE_URL` from `site.llm_api_base_url`.
- Loads the widget script:
  - `assets/js/chatbot-widget.js`

## Front-end widget behavior

### `assets/js/chatbot-widget.js`

This is a small, self-contained script that attaches behavior to the `chatbot_shell.html` DOM.

Key behaviors:

- Fetch metadata:
  - `GET /v1/meta/providers` (provider dropdown)
  - `GET /v1/meta/generators` (kind dropdown)
- Persist selections:
  - `dnd_global_chatbot_provider`
  - `dnd_global_chatbot_kind`
- Persist open/collapsed state:
  - `dnd_global_chatbot_open`
- Chat UX:
  - user messages right aligned
  - AI messages left aligned
  - “Thinking…” placeholder while waiting
  - Enter sends, Shift+Enter inserts newline
  - textarea autosizes up to ~5 lines
- Generate flow:
  - `POST /v1/generate/{kind}`
  - JSON body: `{ "prompt": "..." }`
  - provider override header: `X-LLM-Provider`
- Promote flow:
  - shows a button after generation
  - `POST /v1/promote/{kind}/{slug}`

Security note:

- Responses are rendered with `textContent` (not `innerHTML`) to reduce XSS risk.

### `assets/css/chatbot.css`

This file provides the split view and drawer layout.

Behavior summary:

- Desktop/tablet:
  - `#page-container.with-chatbot` becomes a flex container.
  - content uses ~70% width, chatbot uses ~30%.
  - collapsing adds `html.chatbot-collapsed` which:
    - expands content to 100%
    - collapses chatbot panel to width 0
    - shows a floating button to reopen
- Mobile (`max-width: 992px`):
  - chatbot becomes a fixed bottom drawer.
  - collapse translates the drawer off-screen.

Styling constraints adhered to:

- Uses Bootstrap variables and existing typography.
- Avoids introducing new font families or hard-coded theme systems.

## UI testing (Playwright)

Iteration 4 includes new tests that validate:

- The global chatbot appears on DM pages.
- The global chatbot does not appear on excluded pages (`/`, `/tools/chat/`, `/toc/`, `/search-results.html`).
- Collapsed state persists across DM page navigation.

### Key stability change: `_site-ui/`

Previously, UI tests built into `_site/` and served `_site/`.

This can become flaky when a long-running `jekyll serve` is running in parallel, because it can regenerate `_site/` while tests are reading it.

Iteration 4 makes UI tests build to a dedicated directory:

- Jekyll build destination for UI tests: `_site-ui/`
- Playwright serves `_site-ui/` (port 4100)

### Files involved

- `package.json`
  - `npm run test:ui` runs `jekyll build --destination _site-ui` then Playwright
- `playwright.config.cjs`
  - webServer serves `_site-ui/`
- `tests/ui/global-chatbot.spec.cjs`
  - discovers DM URLs by scanning `_site-ui/` for content roots

### Running UI tests

From the template repo root:

- `npm run test:ui`

Notes:

- The UI tests expect the API to be reachable at `http://localhost:8000`.
- The API should allow browser-origin requests from the test server’s origin (`http://localhost:4100`).

## Operational notes / best practices

- The global chatbot is intentionally front-end only; it does not embed secrets.
- Promotion moves files inside the campaign submodule working tree; commit promoted content in the campaign repo.
- If you add new DM content sections or layouts, update the allowlist/denylist under `chatbot:` in `_config.yml`.

## Troubleshooting

- Chatbot missing on expected pages:
  - Confirm the page uses `layout: default` (directly or indirectly).
  - Confirm `_config.yml` `chatbot.enabled_layouts` includes the page layout name.
  - Confirm `_config.yml` prefix matching lists include the section’s URL prefix.

- UI tests flaky / chatbot appears/disappears:
  - Ensure tests are serving from `_site-ui/` (not `_site/`).
  - Avoid running `jekyll serve` that targets the same destination as UI tests.

- Browser console shows metadata load failures:
  - Verify the API is running (`docker compose up api`), and that CORS allows the origin.
  - Check `site.llm_api_base_url` in `_config.yml` (defaults to `http://localhost:8000`).
