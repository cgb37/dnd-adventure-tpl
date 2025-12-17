# Issue #7 — Chatbot Desktop Split-View UI Fixes
Issue: https://github.com/cgb37/dnd-adventure-tpl/issues/7
Branch: `7-fix-ui-fixes`

## Overview
Fix the desktop split-view layout so the AI Assistant panel behaves like a stable right-side column. Specifically, the chatbot column stays viewport-sticky while the main page scrolls, and the split begins below the navbar so the navbar remains full-width and is never covered by the chatbot.

## Goals (what we built)
- Make the chatbot column viewport-sticky on desktop split-view.
- Ensure the desktop split layout starts below the navbar (navbar stays full-width).
- Ensure the chatbot does not overlap/cover the navbar or other top-of-page chrome on desktop.

## Non-goals
- Change mobile behavior (mobile drawer overlay stays as-is).
- Introduce new UI controls, animations, or layout modes.
- Redesign the chatbot UI or change prompt/AI behavior.

## Why this approach
- Keeping the navbar outside the split container preserves existing Bootstrap navbar behavior and avoids “70% width navbar” regressions.
- `position: sticky` provides “fixed-in-viewport” behavior without removing the chatbot from layout flow, which helps prevent overlaps.
- Scoping the flex split to the content area reduces unintended layout interactions with site-wide header/nav/hero.

## Implementation details
- **Jekyll / Layout**
  - Introduce an explicit “split container” that begins *after* the navbar include and wraps only the content area + chatbot.
  - Move/insert the chatbot shell include into that split container (desktop) so it participates in the two-column layout while leaving the navbar above it.
  - Ensure existing gating/toggles that currently apply `.with-chatbot` are applied to the new split container (or a similar, content-only wrapper) rather than the entire `#page-container`.

- **CSS (desktop split-view)**
  - Update `assets/css/chatbot.css` to apply the desktop flex split rules to the new content-only wrapper (instead of `#page-container`).
  - Make the chatbot panel sticky on desktop:
    - Prefer `position: sticky` on the chatbot column (or `.chatbot__panel`) with `top: 0`.
    - If the navbar ever becomes `fixed`/`sticky` in future, be prepared to set `top` via a CSS variable (e.g., `--chatbot-sticky-top`) so the panel always stays below top chrome.
  - Keep `min-width: 0` / overflow rules consistent so the left content column behaves correctly with long code blocks/tables.

- **CSS (mobile)**
  - Keep the current mobile drawer behavior unchanged (`position: fixed; bottom: 0; z-index: 1050;`).

- **JS**
  - No behavior change required beyond ensuring any class toggles that enable split-view target the correct wrapper.

## How to validate
- Local build/serve (Docker):
  - `docker compose up --build`
  - Visit `http://localhost:4000` and open any long page.

- Expected results (desktop widths):
  - The navbar remains full-width across the top.
  - The content area below the navbar is split into left content + right chatbot.
  - Scrolling the page keeps the chatbot column stationary (viewport-sticky) while the left content scrolls.
  - The chatbot column never covers the navbar.

- Regression check (mobile widths):
  - The chatbot still behaves like a bottom drawer and may overlay content (unchanged).

## TODO list (execution plan)
- [ ] Identify the exact point in `_layouts/default.html` (or equivalent) where the split container should start (immediately after the navbar include).
- [ ] Add a content-only split wrapper and place the chatbot shell inside it.
- [ ] Update CSS selectors so the desktop split-view is applied to the new wrapper.
- [ ] Add sticky positioning for the chatbot column on desktop.
- [ ] Verify no navbar overlap and no “navbar shrinks to 70% width” regressions.
- [ ] Validate on a long page at desktop + mobile breakpoints.

## Security considerations
- No auth changes.
- No secret handling changes.
- No new CORS/origin behavior.
- No new user-controlled HTML injection; changes are layout/CSS only.

## .env / environment variables added
None.

## Diagram (optional but encouraged)
```mermaid
flowchart TB
  Nav[Navbar (full width)] --> Split[Content-only split container]
  Split --> Main[Main content (left column)]
  Split --> Chat[Chatbot (right column, sticky)]
```

## Diff summary (files changed)
```diff
+ docs/issue-7-fix-ui-fixes.md
```
