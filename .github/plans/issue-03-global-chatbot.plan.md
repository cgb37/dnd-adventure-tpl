# Plan — Issue #3 / Iteration 4: Global Chatbot UI (Split View)

Issue: https://github.com/cgb37/dnd-adventure-tpl/issues/3
Branch: `3-feat-add-chatbot-to-all-view-ports`

## Goal
Add a **global, always-available chatbot UI** that appears on **DM-facing content pages** (chapters/locations/monsters/encounters/etc.) and is **excluded** from:

- `/tools/*` (for now)
- homepage
- 404
- search pages
- link/utility pages

The UI should follow the **dual-panel split view** described in `.github/prompts/ui-chatbot.prompt.md`, and match the site’s existing look & feel.

## UX Requirements (from prompt + clarifications)

### Desktop/tablet
- Two-panel layout:
  - Left: main site content (~70%).
  - Right: chatbot panel (~30%).
- Subtle divider between panels.
- Right panel has show/hide toggle:
  - Expanded: visible panel.
  - Collapsed: panel slides off-screen; a floating toggle remains on right edge.
- Chat UI is a **true chat experience**:
  - message bubbles
  - user messages right-aligned
  - AI messages left-aligned
  - loading indicator while waiting
- Input:
  - multi-line textarea, auto-expanding (max ~4–5 lines)
  - send button
  - action icons row (present but disabled/no-op): attach, model, MCP/tool
  - a “Generate” dropdown (NPC/Monster/Encounter/Location/Chapter)

### Mobile
- The chatbot becomes a **bottom drawer**.
- Toggle shows/hides the drawer.
- Open/closed state persists across pages.

### State persistence
Persist via `localStorage`:
- expanded/collapsed state
- selected generator kind
- selected provider (if shown)

## Backend integration (reuse Iteration 3 API)

The chat UI still calls the existing endpoints:

- `GET /v1/meta/providers` (populate provider list)
- `GET /v1/meta/generators` (populate generate dropdown)
- `GET /v1/meta/schema/{kind}` (optional for future; in Iteration 4 we can keep it minimal)
- `POST /v1/generate/{kind}` (generate content)
  - pass provider override via `X-LLM-Provider`
- `POST /v1/promote/{kind}/{slug}` (promote last generated)

Iteration 4 intent: the “Generate” dropdown **sets internal state** (current generator kind). The user’s free-form message becomes the `prompt` sent to `/v1/generate/{kind}`.

## Page inclusion/exclusion strategy

Implement a conservative allowlist.

Preferred approach:
- Render chatbot shell only when one of the following is true:
  - `page.layout` is in an allowlist (e.g. `chapter`, `episode`, `scene`, `location`, `encounter`, `monster`, `npc`, `reward`, etc.)
  - OR `page.url` starts with known DM content prefixes (e.g. `/chapters/`, `/locations/`, `/monsters/`, `/encounters/`, `/npcs/`)

And ensure it is NOT rendered when:
- `page.url` starts with `/tools/`
- `page.url` is `/` (home)
- `page.url` is `/404.html`
- `page.url` is `/search-results.html` (and any other search endpoints)

## Implementation outline

### 1) Jekyll layout changes
- Add a reusable include for the chatbot shell (HTML markup) so it’s not duplicated.
- Inject into the site layout(s) with a conditional guard.
- Wrap page content + chatbot in a layout container that supports split view.

Candidate files:
- `_layouts/default.html` (or whichever layout wraps most content)
- `_includes/...` (new include for chatbot)
- `assets/css/...` or `assets/main.scss` (prefer using existing Bootstrap utilities + minimal additional CSS)

### 2) Front-end JS
- New JS module (or refactor `assets/js/llm-chatbot.js`) to support:
  - message list + rendering
  - typing/loading indicator
  - send message -> call `/v1/generate/{kind}`
  - show last generated slug + promote CTA
  - toggle open/closed state and persist
  - responsive mode switching to bottom drawer

Important:
- Render AI output as **text**, not HTML, to avoid XSS.
- Keep Content-Type header correct: `application/json`.

### 3) Styling
- Match current theme (do not introduce new fonts/colors).
- Use existing Bootstrap styles where possible.
- Add only minimal CSS for split view, panel transitions, and drawer behavior.

### 4) Testing
Update Playwright to cover:
- A representative DM content page shows the chatbot.
- `/tools/chat/` does not show the global chatbot.
- Home page does not show it.
- Toggle persists across navigation.

Optional (if stable in CI/local):
- Generate + promote smoke flow.

## Acceptance criteria
- Chatbot visible on DM content pages; absent on excluded pages.
- Desktop split view matches prompt proportions and collapses smoothly.
- Mobile uses bottom drawer.
- Selected generator kind and open/closed state persist via localStorage.
- Chat UI displays message bubbles and loading state.
- Generates via `/v1/generate/{kind}` using the selected kind.

## Risks / notes
- Adding a split-view wrapper can interact with existing CSS/layout assumptions; prefer scoping styles to a wrapper class.
- Exclusion logic must be conservative to avoid polluting non-DM pages.
- Don’t add secrets to the browser; keep auth relaxed only for local dev.
