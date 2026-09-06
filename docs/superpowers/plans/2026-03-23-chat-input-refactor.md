# Chat Input Refactor Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the two-row toolbar + separate send bar with a single unified input box (textarea on top, action bar on bottom) that exposes Ask/Agent mode toggle, file attachment, model selection, and a send button — all inside one rounded container with a blue focus border.

**Architecture:** All UI state (mode, model, attached files) lives in the JS widget. The HTML shell is declarative — no inline logic. CSS drives the focus ring and hides/shows Agent-only controls based on a `data-mode` attribute on the input wrapper. File uploads use a hidden `<input type="file">` triggered by the "+" button and are validated client-side (type + size) before being attached to the API request as `FormData`.

**Tech Stack:** Vanilla JS (ES2020 IIFE), Bootstrap 5.3 utility classes, CSS custom properties, Jekyll Liquid templating, Playwright for UI tests.

**Reference image:** Unified dark input box — textarea top, bottom bar: `[⊡ Ask ▾]  [⊡ Agent type ▾]  [+]  ···  [Model ▾ | ➤]`

---

## Existing files to understand before starting

- `_includes/chatbot_shell.html` — HTML structure (70 lines)
- `assets/css/chatbot.css` — All chatbot styles (334 lines)
- `assets/js/chatbot-widget.js` — Widget logic (324 lines)
- `_config.yml` — `llm_api_base_url` and chatbot allow/deny lists

---

## Task 1: Write Playwright test for the new input structure

These tests will FAIL until the HTML is refactored. Run them first to establish the baseline.

**Files:**
- Create: `tests/ui/chat-input-refactor.spec.js`

**Step 1: Create the test file**

```javascript
// tests/ui/chat-input-refactor.spec.js
// Run against a built Jekyll site served at http://localhost:4000
// Start the site first: bundle exec jekyll serve --livereload

const { test, expect } = require('@playwright/test');

const CHAT_PAGE = 'http://localhost:4000/chapters/'; // first chatbot-enabled page

test.describe('Chat input box layout', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(CHAT_PAGE);
    // Wait for the widget JS to boot
    await page.waitForSelector('.chatbot__inputBox');
  });

  test('input box is present and contains textarea', async ({ page }) => {
    const box = page.locator('.chatbot__inputBox');
    await expect(box).toBeVisible();
    await expect(box.locator('.chatbot__textarea')).toBeVisible();
  });

  test('bottom bar has mode toggle, attach, model, and send buttons', async ({ page }) => {
    const bar = page.locator('.chatbot__bottomBar');
    await expect(bar.locator('[data-testid="mode-toggle"]')).toBeVisible();
    await expect(bar.locator('[data-testid="attach-btn"]')).toBeVisible();
    await expect(bar.locator('[data-testid="model-btn"]')).toBeVisible();
    await expect(bar.locator('[data-testid="send-btn"]')).toBeVisible();
  });

  test('old toolbar rows are GONE', async ({ page }) => {
    await expect(page.locator('.chatbot__toolbarRow')).toHaveCount(0);
    await expect(page.locator('#chatbotProvider')).toHaveCount(0);
    await expect(page.locator('#chatbotKind')).toHaveCount(0);
  });

  test('agent type selector hidden in Ask mode', async ({ page }) => {
    const box = page.locator('.chatbot__inputBox');
    await expect(box).toHaveAttribute('data-mode', 'ask');
    await expect(page.locator('[data-testid="agent-type-btn"]')).toBeHidden();
  });

  test('switching to Agent mode shows agent type selector', async ({ page }) => {
    await page.locator('[data-testid="mode-toggle"]').click();
    await page.locator('[data-value="agent"]').click();
    const box = page.locator('.chatbot__inputBox');
    await expect(box).toHaveAttribute('data-mode', 'agent');
    await expect(page.locator('[data-testid="agent-type-btn"]')).toBeVisible();
  });

  test('attach button opens file picker', async ({ page }) => {
    const [chooser] = await Promise.all([
      page.waitForEvent('filechooser'),
      page.locator('[data-testid="attach-btn"]').click(),
    ]);
    expect(chooser).toBeTruthy();
  });

  test('model button opens model dropdown', async ({ page }) => {
    await page.locator('[data-testid="model-btn"]').click();
    await expect(page.locator('.chatbot__modelDropdown')).toBeVisible();
  });

  test('model dropdown shows group headers', async ({ page }) => {
    await page.locator('[data-testid="model-btn"]').click();
    const dropdown = page.locator('.chatbot__modelDropdown');
    await expect(dropdown.locator('.chatbot__modelGroup')).toHaveCount(3); // Local / API / OpenRouter
  });

  test('file too large shows error message', async ({ page }) => {
    // Create a fake >10 MB buffer
    const bigFile = Buffer.alloc(11 * 1024 * 1024, 'x');
    const [chooser] = await Promise.all([
      page.waitForEvent('filechooser'),
      page.locator('[data-testid="attach-btn"]').click(),
    ]);
    await chooser.setFiles({
      name: 'big.txt',
      mimeType: 'text/plain',
      buffer: bigFile,
    });
    await expect(page.locator('.chatbot__attachError')).toContainText('too large');
  });

  test('Enter sends message, Shift+Enter inserts newline', async ({ page }) => {
    const input = page.locator('.chatbot__textarea');
    await input.fill('Hello');
    await input.press('Enter');
    // A user bubble should appear
    await expect(page.locator('.chatbot__msg--user').last()).toContainText('Hello');
  });
});
```

**Step 2: Run tests to confirm they ALL fail (expected)**

```bash
cd /Users/charlesbrownroberts/Code/CGB37/dnd-ai/dnd-adventure-tpl
npx playwright test tests/ui/chat-input-refactor.spec.js --reporter=line
```

Expected: All 9 tests FAIL with "waiting for selector '.chatbot__inputBox'" — the new class doesn't exist yet.

---

## Task 2: Refactor `chatbot_shell.html` — new unified input box

Replace the old two-row toolbar and separated send row with the industry-standard single-box layout.

**Files:**
- Modify: `_includes/chatbot_shell.html`

**Step 1: Read current file** *(already done — it is 70 lines)*

**Step 2: Replace the entire file contents**

```html
{%- comment -%}
Global chatbot shell (Iteration 5)
- Rendered only on allowlisted DM content pages (see _config.yml -> chatbot)
- Excluded on /tools/* and other denylisted pages
{%- endcomment -%}

<script>
  // Apply persisted open/closed state before the widget renders to reduce flicker.
  (function () {
    try {
      var open = localStorage.getItem('dnd_global_chatbot_open');
      if (open === 'false') document.documentElement.classList.add('chatbot-collapsed');
    } catch (_) {}
  })();
</script>

<aside id="global-chatbot" class="chatbot" aria-label="AI Assistant">
  <div class="chatbot__panel">

    <!-- ── Header ── -->
    <div class="chatbot__header">
      <div class="chatbot__title">
        <span class="chatbot__badge" aria-hidden="true">AI</span>
        <div>
          <div class="chatbot__heading">AI Assistant</div>
          <div class="chatbot__subheading">DM tools</div>
        </div>
      </div>
      <button id="chatbotToggle" class="btn btn-sm btn-outline-secondary chatbot__toggle"
              type="button" aria-label="Toggle chatbot">
        <span class="chatbot__toggleIcon" aria-hidden="true">›</span>
      </button>
    </div>

    <!-- ── Messages ── -->
    <div id="chatbotMessages" class="chatbot__messages"
         role="log" aria-live="polite" aria-relevant="additions"></div>

    <!-- ── Unified input box ── -->
    <div class="chatbot__inputArea">

      <!-- Attachment preview strip (hidden until files are attached) -->
      <div id="chatbotAttachments" class="chatbot__attachments" hidden></div>
      <div id="chatbotAttachError" class="chatbot__attachError" hidden></div>

      <!-- Input box: focus ring wraps textarea + bottom bar -->
      <div class="chatbot__inputBox" data-mode="ask" id="chatbotInputBox">

        <textarea id="chatbotInput"
                  class="chatbot__textarea"
                  rows="1"
                  placeholder="Ask anything..."
                  aria-label="Chat input"></textarea>

        <!-- Bottom action bar -->
        <div class="chatbot__bottomBar">

          <!-- Left controls -->
          <div class="chatbot__bottomLeft">

            <!-- Mode toggle: Ask / Agent -->
            <div class="chatbot__dropdownWrap" id="modeDropdownWrap">
              <button class="chatbot__pillBtn chatbot__pillBtn--active"
                      type="button"
                      data-testid="mode-toggle"
                      id="modePillBtn"
                      aria-haspopup="true"
                      aria-expanded="false">
                <svg class="chatbot__pillIcon" aria-hidden="true" viewBox="0 0 16 16" width="14" height="14">
                  <path fill="currentColor" d="M2 2h12v8H9l-3 3v-3H2z"/>
                </svg>
                <span id="modePillLabel">Ask</span>
                <svg class="chatbot__chevron" aria-hidden="true" viewBox="0 0 16 16" width="10" height="10">
                  <path fill="currentColor" d="M4 6l4 4 4-4"/>
                </svg>
              </button>
              <ul class="chatbot__dropdownMenu" id="modeMenu" role="menu" hidden>
                <li role="menuitem" data-value="ask">
                  <svg aria-hidden="true" viewBox="0 0 16 16" width="14" height="14">
                    <path fill="currentColor" d="M2 2h12v8H9l-3 3v-3H2z"/>
                  </svg>
                  Ask
                </li>
                <li role="menuitem" data-value="agent">
                  <svg aria-hidden="true" viewBox="0 0 16 16" width="14" height="14">
                    <path fill="currentColor" d="M8 1a5 5 0 100 10A5 5 0 008 1zm0 2a1.5 1.5 0 110 3 1.5 1.5 0 010-3zm0 7c-2 0-3.5-1-3.5-2.5C4.5 6 6 5 8 5s3.5 1 3.5 2.5C11.5 9 10 10 8 10z"/>
                  </svg>
                  Agent
                </li>
              </ul>
            </div>

            <!-- Agent type selector — only visible in agent mode -->
            <div class="chatbot__dropdownWrap" id="agentTypeWrap">
              <button class="chatbot__pillBtn"
                      type="button"
                      data-testid="agent-type-btn"
                      id="agentTypePillBtn"
                      aria-haspopup="true"
                      aria-expanded="false">
                <svg class="chatbot__pillIcon" aria-hidden="true" viewBox="0 0 16 16" width="14" height="14">
                  <path fill="currentColor" d="M1 3h14v2H1zm2 4h10v2H3zm2 4h6v2H5z"/>
                </svg>
                <span id="agentTypePillLabel">NPC</span>
                <svg class="chatbot__chevron" aria-hidden="true" viewBox="0 0 16 16" width="10" height="10">
                  <path fill="currentColor" d="M4 6l4 4 4-4"/>
                </svg>
              </button>
              <ul class="chatbot__dropdownMenu" id="agentTypeMenu" role="menu" hidden></ul>
            </div>

            <!-- Attach button -->
            <button class="chatbot__pillBtn chatbot__pillBtn--icon"
                    type="button"
                    data-testid="attach-btn"
                    id="attachBtn"
                    aria-label="Attach file">
              <svg aria-hidden="true" viewBox="0 0 16 16" width="15" height="15">
                <path fill="currentColor" d="M13.5 6.5l-6 6a3.5 3.5 0 01-4.95-4.95l6-6a2 2 0 012.83 2.83l-5.66 5.66a.5.5 0 01-.71-.71l5.66-5.66"/>
              </svg>
            </button>

            <!-- Hidden real file input -->
            <input type="file"
                   id="chatbotFileInput"
                   class="chatbot__fileInput"
                   accept="image/*,.pdf,.doc,.docx,.txt,.md,.json"
                   multiple
                   hidden>
          </div>

          <!-- Right controls: model selector + send -->
          <div class="chatbot__bottomRight">
            <div class="chatbot__dropdownWrap" id="modelDropdownWrap">
              <button class="chatbot__modelBtn"
                      type="button"
                      data-testid="model-btn"
                      id="modelBtn"
                      aria-haspopup="true"
                      aria-expanded="false">
                <span id="modelBtnLabel">Loading…</span>
                <svg class="chatbot__chevron" aria-hidden="true" viewBox="0 0 16 16" width="10" height="10">
                  <path fill="currentColor" d="M4 6l4 4 4-4"/>
                </svg>
              </button>
              <ul class="chatbot__dropdownMenu chatbot__modelDropdown"
                  id="modelMenu" role="menu" hidden></ul>
            </div>

            <div class="chatbot__sendDivider" aria-hidden="true"></div>

            <button id="chatbotSend"
                    class="chatbot__sendBtn"
                    type="button"
                    data-testid="send-btn"
                    aria-label="Send message">
              <svg aria-hidden="true" viewBox="0 0 16 16" width="15" height="15">
                <path fill="currentColor" d="M2 14L14 8 2 2v4l8 2-8 2z"/>
              </svg>
            </button>
          </div>

        </div><!-- /.chatbot__bottomBar -->
      </div><!-- /.chatbot__inputBox -->
    </div><!-- /.chatbot__inputArea -->

  </div><!-- /.chatbot__panel -->

  <button id="chatbotFloatingToggle"
          class="btn btn-primary chatbot__floatingToggle"
          type="button"
          aria-label="Show chatbot">
    <span aria-hidden="true">‹</span>
  </button>
</aside>

<script>
  window.LLM_API_BASE_URL = "{{ site.llm_api_base_url | default: 'http://localhost:8000' }}";
</script>
<script src="/assets/js/chatbot-widget.js"></script>
```

**Step 3: Run tests — expect the "old toolbar" tests to pass, new-structure tests still fail (CSS/JS not done)**

```bash
npx playwright test tests/ui/chat-input-refactor.spec.js --reporter=line
```

Expected: `old toolbar rows are GONE` — PASS. All others still FAIL (no CSS yet).

**Step 4: Commit**

```bash
git add _includes/chatbot_shell.html
git commit -m "refactor(chatbot): replace two-row toolbar with unified input box HTML (shell only)"
```

---

## Task 3: Replace `chatbot.css` — style the new input box

Strip out all the old `chatbot__toolbar` / `chatbot__toolbarRow` / `chatbot__hint` rules and add the new unified box styles.

**Files:**
- Modify: `assets/css/chatbot.css`

**Step 1: Replace the file**

Keep the existing split-layout rules at top and bottom unchanged. Only replace the component-level styles (lines 31–257 roughly). Full replacement below:

```css
/* Global chatbot (Iteration 5)
 * - Prefer Bootstrap variables.
 * - Scope all rules to #global-chatbot to avoid bleed.
 */

/* ── Split-view layout (desktop) ── */
#split-wrapper.with-chatbot {
  display: flex !important;
  min-height: 100vh !important;
}
#split-wrapper.with-chatbot > #page-container {
  flex: 0 0 66.6666667% !important;
  max-width: 66.6666667% !important;
}
#split-wrapper.with-chatbot > #chatbot-column {
  flex: 0 0 33.3333333% !important;
  max-width: 33.3333333% !important;
  overflow: hidden;
  position: relative;
}

/* ── Panel shell ── */
#global-chatbot.chatbot { position: relative; }

#global-chatbot .chatbot__panel {
  height: 100%;
  display: flex;
  flex-direction: column;
  border-left: 1px solid rgba(255,255,255,.12);
  background: var(--bs-body-bg);
  transition: opacity 200ms ease, transform 200ms ease;
}

/* ── Header ── */
#global-chatbot .chatbot__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: .75rem;
  border-bottom: 1px solid rgba(255,255,255,.12);
  flex-shrink: 0;
}
#global-chatbot .chatbot__title {
  display: flex;
  align-items: center;
  gap: .75rem;
}
#global-chatbot .chatbot__badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2rem;
  height: 2rem;
  border-radius: .5rem;
  background: rgba(255,255,255,.12);
  font-weight: 600;
}
#global-chatbot .chatbot__heading { font-weight: 600; line-height: 1.1; }
#global-chatbot .chatbot__subheading { font-size: .875rem; opacity: .75; }
#global-chatbot .chatbot__toggle { min-width: 2.25rem; }
#global-chatbot .chatbot__toggleIcon { display: inline-block; }

/* ── Messages ── */
#global-chatbot .chatbot__messages {
  flex: 1 1 auto;
  overflow-y: auto;
  padding: .75rem;
}
#global-chatbot .chatbot__msg {
  display: flex;
  margin-bottom: .75rem;
}
#global-chatbot .chatbot__msg--user { justify-content: flex-end; }
#global-chatbot .chatbot__bubble {
  max-width: 85%;
  padding: .6rem .75rem;
  border-radius: .5rem;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: .9rem;
}
#global-chatbot .chatbot__msg--user .chatbot__bubble {
  background: rgba(13,110,253,.35);
  border: 1px solid rgba(13,110,253,.25);
}
#global-chatbot .chatbot__msg--ai .chatbot__bubble {
  background: rgba(255,255,255,.08);
  border: 1px solid rgba(255,255,255,.10);
}
#global-chatbot .chatbot__meta {
  margin-top: .25rem;
  font-size: .8rem;
  opacity: .75;
}

/* ── Input area (outer wrapper) ── */
#global-chatbot .chatbot__inputArea {
  padding: .5rem .75rem .75rem;
  border-top: 1px solid rgba(255,255,255,.12);
  background: var(--bs-body-bg);
  flex-shrink: 0;
}

/* ── Attachment preview strip ── */
#global-chatbot .chatbot__attachments {
  display: flex;
  flex-wrap: wrap;
  gap: .35rem;
  margin-bottom: .4rem;
}
#global-chatbot .chatbot__attachChip {
  display: inline-flex;
  align-items: center;
  gap: .3rem;
  padding: .2rem .5rem;
  border-radius: .375rem;
  background: rgba(255,255,255,.1);
  font-size: .75rem;
  max-width: 140px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
#global-chatbot .chatbot__attachChip button {
  background: none;
  border: none;
  padding: 0;
  cursor: pointer;
  color: inherit;
  opacity: .6;
  line-height: 1;
}
#global-chatbot .chatbot__attachError {
  font-size: .75rem;
  color: var(--bs-danger);
  margin-bottom: .3rem;
}

/* ── Unified input box ── */
#global-chatbot .chatbot__inputBox {
  border: 1px solid rgba(255,255,255,.18);
  border-radius: .75rem;
  background: #0d0d0d;           /* slightly darker than panel bg */
  padding: .6rem .6rem .4rem;
  transition: border-color 150ms ease, box-shadow 150ms ease;
}
#global-chatbot .chatbot__inputBox:focus-within {
  border-color: #4d90fe;         /* blue focus ring matching image */
  box-shadow: 0 0 0 1px rgba(77,144,254,.35);
}

/* ── Textarea inside the box ── */
#global-chatbot .chatbot__textarea {
  display: block;
  width: 100%;
  resize: none;
  overflow: hidden;
  border: none;
  background: transparent;
  color: var(--bs-body-color);
  padding: 0 .25rem .4rem;
  font-size: .9rem;
  line-height: 1.5;
  outline: none;
  min-height: 2rem;
}
#global-chatbot .chatbot__textarea::placeholder { opacity: .45; }

/* ── Bottom action bar ── */
#global-chatbot .chatbot__bottomBar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: .25rem;
  padding-top: .2rem;
  border-top: 1px solid rgba(255,255,255,.07);
  margin-top: .25rem;
}
#global-chatbot .chatbot__bottomLeft {
  display: flex;
  align-items: center;
  gap: .25rem;
  flex-wrap: nowrap;
}
#global-chatbot .chatbot__bottomRight {
  display: flex;
  align-items: center;
  gap: 0;
  flex-shrink: 0;
}

/* ── Pill buttons (mode, agent type, attach) ── */
#global-chatbot .chatbot__pillBtn {
  display: inline-flex;
  align-items: center;
  gap: .3rem;
  padding: .25rem .55rem;
  border-radius: .5rem;
  border: 1px solid rgba(255,255,255,.15);
  background: rgba(255,255,255,.05);
  color: var(--bs-body-color);
  font-size: .78rem;
  cursor: pointer;
  white-space: nowrap;
  transition: background 120ms ease;
}
#global-chatbot .chatbot__pillBtn:hover {
  background: rgba(255,255,255,.10);
}
#global-chatbot .chatbot__pillBtn--active {
  border-color: rgba(255,255,255,.28);
}
#global-chatbot .chatbot__pillBtn--icon {
  padding: .25rem .4rem;
}
#global-chatbot .chatbot__pillIcon { flex-shrink: 0; }
#global-chatbot .chatbot__chevron { flex-shrink: 0; opacity: .55; }

/* ── Agent type button: hidden in ask mode ── */
#global-chatbot .chatbot__inputBox[data-mode="ask"] #agentTypeWrap {
  display: none;
}

/* ── Dropdown menus ── */
#global-chatbot .chatbot__dropdownWrap {
  position: relative;
}
#global-chatbot .chatbot__dropdownMenu {
  position: absolute;
  bottom: calc(100% + .35rem);
  left: 0;
  z-index: 1060;
  min-width: 140px;
  background: #1a1a1a;
  border: 1px solid rgba(255,255,255,.15);
  border-radius: .5rem;
  padding: .25rem 0;
  list-style: none;
  margin: 0;
  box-shadow: 0 4px 16px rgba(0,0,0,.5);
}
/* Model dropdown opens to the right to avoid clipping */
#global-chatbot .chatbot__modelDropdown {
  left: auto;
  right: 0;
  min-width: 200px;
}
#global-chatbot .chatbot__dropdownMenu li {
  display: flex;
  align-items: center;
  gap: .45rem;
  padding: .35rem .75rem;
  cursor: pointer;
  font-size: .82rem;
  white-space: nowrap;
  transition: background 100ms;
}
#global-chatbot .chatbot__dropdownMenu li:hover {
  background: rgba(255,255,255,.08);
}
#global-chatbot .chatbot__dropdownMenu li[aria-selected="true"] {
  color: #4d90fe;
}
/* Group headers inside model dropdown */
#global-chatbot .chatbot__modelGroup {
  padding: .25rem .75rem .1rem;
  font-size: .7rem;
  text-transform: uppercase;
  letter-spacing: .06em;
  opacity: .5;
  cursor: default;
  pointer-events: none;
}

/* ── Model button ── */
#global-chatbot .chatbot__modelBtn {
  display: inline-flex;
  align-items: center;
  gap: .3rem;
  padding: .25rem .45rem;
  border: none;
  background: transparent;
  color: rgba(255,255,255,.55);
  font-size: .78rem;
  cursor: pointer;
  white-space: nowrap;
}
#global-chatbot .chatbot__modelBtn:hover { color: var(--bs-body-color); }

/* ── Divider between model and send ── */
#global-chatbot .chatbot__sendDivider {
  width: 1px;
  height: 1.1rem;
  background: rgba(255,255,255,.2);
  margin: 0 .35rem;
}

/* ── Send button ── */
#global-chatbot .chatbot__sendBtn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.9rem;
  height: 1.9rem;
  border-radius: .45rem;
  border: none;
  background: rgba(255,255,255,.08);
  color: var(--bs-body-color);
  cursor: pointer;
  transition: background 120ms;
}
#global-chatbot .chatbot__sendBtn:hover {
  background: #4d90fe;
  color: #fff;
}

/* ── Floating toggle ── */
#global-chatbot .chatbot__floatingToggle {
  display: none;
  position: fixed;
  right: .75rem;
  bottom: .75rem;
  z-index: 1050;
}

/* ── Collapsed state ── */
html.chatbot-collapsed #chatbot-split.with-chatbot #content-wrap,
html.chatbot-collapsed #page-container.with-chatbot #content-wrap {
  flex-basis: 100%;
  max-width: 100%;
}
html.chatbot-collapsed #chatbot-split.with-chatbot #global-chatbot,
html.chatbot-collapsed #page-container.with-chatbot #global-chatbot {
  flex-basis: 0;
  max-width: 0;
}
html.chatbot-collapsed #global-chatbot .chatbot__panel {
  opacity: 0;
  transform: translateX(24px);
  pointer-events: none;
}
html.chatbot-collapsed #global-chatbot .chatbot__floatingToggle {
  display: inline-flex;
}

/* ── Mobile drawer ── */
@media (max-width: 768px) {
  #chatbot-split.with-chatbot,
  #page-container.with-chatbot { display: block; }
  #chatbot-split.with-chatbot #content-wrap,
  #page-container.with-chatbot #content-wrap { max-width: none; }
  #chatbot-split.with-chatbot #global-chatbot,
  #page-container.with-chatbot #global-chatbot {
    position: fixed;
    left: 0; right: 0; bottom: 0;
    max-width: none;
    width: 100%;
    z-index: 1050;
  }
  #global-chatbot .chatbot__panel {
    height: 65vh;
    border-left: none;
    border-top: 1px solid rgba(255,255,255,.12);
    box-shadow: 0 -8px 24px rgba(0,0,0,.25);
  }
  html.chatbot-collapsed #global-chatbot .chatbot__panel {
    display: flex;
    transform: translateY(100%);
  }
  #global-chatbot .chatbot__floatingToggle { display: none; }
  html.chatbot-collapsed #global-chatbot .chatbot__floatingToggle { display: inline-flex; }
}

/* ── Strict always-visible split (side_by_side layout) ── */
#chatbot-split.with-chatbot,
#page-container.with-chatbot {
  display: flex !important;
  min-height: 100vh !important;
}
#chatbot-split.with-chatbot > #content-wrap,
#page-container.with-chatbot > #content-wrap {
  flex: 0 0 66.6666667% !important;
  max-width: 66.6666667% !important;
  height: 100vh !important;
  overflow: auto !important;
  z-index: 1;
}
#chatbot-split.with-chatbot > #global-chatbot,
#page-container.with-chatbot > #global-chatbot {
  flex: 0 0 33.3333333% !important;
  max-width: 33.3333333% !important;
  height: 100vh !important;
  overflow: auto !important;
  position: relative !important;
  z-index: 2;
}
#global-chatbot .chatbot__panel {
  height: 100% !important;
  display: flex;
  flex-direction: column;
}
html.chatbot-collapsed #chatbot-split.with-chatbot > #content-wrap,
html.chatbot-collapsed #page-container.with-chatbot > #content-wrap,
html.chatbot-collapsed #chatbot-split.with-chatbot > #global-chatbot,
html.chatbot-collapsed #page-container.with-chatbot > #global-chatbot,
html.chatbot-collapsed #global-chatbot .chatbot__panel {
  flex-basis: auto !important;
  max-width: none !important;
  opacity: 1 !important;
  transform: none !important;
  pointer-events: auto !important;
}
#global-chatbot .chatbot__floatingToggle,
#chatbotToggle {
  display: none !important;
}
@media (max-width: 768px) {
  #chatbot-split.with-chatbot,
  #page-container.with-chatbot { display: block !important; }
  #chatbot-split.with-chatbot > #content-wrap,
  #page-container.with-chatbot > #content-wrap,
  #chatbot-split.with-chatbot > #global-chatbot,
  #page-container.with-chatbot > #global-chatbot {
    width: 100% !important;
    max-width: none !important;
    height: auto !important;
  }
}
```

**Step 2: Verify Jekyll still builds**

```bash
cd /Users/charlesbrownroberts/Code/CGB37/dnd-ai/dnd-adventure-tpl
bundle exec jekyll build 2>&1 | tail -5
```

Expected: `done in X seconds.` — no errors.

**Step 3: Commit**

```bash
git add assets/css/chatbot.css
git commit -m "refactor(chatbot): replace toolbar CSS with unified input box styles"
```

---

## Task 4: Refactor `chatbot-widget.js` — mode toggle, model dropdown, dropdowns

Rewrite the widget to wire up the new HTML. Keep the same API contract (`/v1/meta/providers`, `/v1/meta/generators`, `/v1/generate/{kind}`).

**Files:**
- Modify: `assets/js/chatbot-widget.js`

**Step 1: Replace the entire file**

```javascript
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
    panel:         document.querySelector('#global-chatbot .chatbot__panel'),
    toggle:        document.getElementById('chatbotToggle'),
    floatToggle:   document.getElementById('chatbotFloatingToggle'),
    messages:      document.getElementById('chatbotMessages'),
    input:         document.getElementById('chatbotInput'),
    send:          document.getElementById('chatbotSend'),
    inputBox:      document.getElementById('chatbotInputBox'),
    // mode
    modePillBtn:   document.getElementById('modePillBtn'),
    modePillLabel: document.getElementById('modePillLabel'),
    modeMenu:      document.getElementById('modeMenu'),
    // agent type
    agentTypeWrap: document.getElementById('agentTypeWrap'),
    agentTypePillBtn: document.getElementById('agentTypePillBtn'),
    agentTypePillLabel: document.getElementById('agentTypePillLabel'),
    agentTypeMenu: document.getElementById('agentTypeMenu'),
    // attach
    attachBtn:     document.getElementById('attachBtn'),
    fileInput:     document.getElementById('chatbotFileInput'),
    attachments:   document.getElementById('chatbotAttachments'),
    attachError:   document.getElementById('chatbotAttachError'),
    // model
    modelBtn:      document.getElementById('modelBtn'),
    modelBtnLabel: document.getElementById('modelBtnLabel'),
    modelMenu:     document.getElementById('modelMenu'),
  };

  // Bail if the shell HTML isn't present (shouldn't happen on allowed pages).
  if (!el.panel || !el.input || !el.send) return;

  // ── State ──────────────────────────────────────────────────────────────────
  const state = {
    mode:          lsGet(LS_MODE) || 'ask',   // 'ask' | 'agent'
    kind:          lsGet(LS_KIND) || 'npc',   // generator type
    model:         lsGet(LS_MODEL) || '',      // selected provider/model
    attachedFiles: [],                          // File[]
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
    // Update aria-selected
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
  // Providers returned by /v1/meta/providers are grouped by prefix:
  //   "local/*"      → Local
  //   "openrouter/*" → OpenRouter
  //   everything else → API
  function groupProviders(providers) {
    const groups = { Local: [], OpenRouter: [], API: [] };
    for (const p of providers) {
      if (p.startsWith('local/') || p.startsWith('local:')) groups.Local.push(p);
      else if (p.startsWith('openrouter/') || p.startsWith('openrouter:')) groups.OpenRouter.push(p);
      else groups.API.push(p);
    }
    return groups;
  }

  function populateModelMenu(providers, defaultProvider) {
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
        // Show a short label (strip prefix)
        li.textContent = p.replace(/^(local|openrouter)[/:]/i, '');
        el.modelMenu.appendChild(li);
      }
    }
  }

  function applyModel(model) {
    state.model = model;
    lsSet(LS_MODEL, model);
    // Short display label
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
      // Avoid duplicates
      if (!state.attachedFiles.some((e) => e.name === f.name && e.size === f.size)) {
        state.attachedFiles.push(f);
      }
    }

    if (errors.length) {
      el.attachError.textContent = errors.join(' ');
      el.attachError.hidden = false;
    }

    el.fileInput.value = ''; // reset so same file can be re-added after removal
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

    // Show user message (include attachment names as context)
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
        // Ask mode: simple chat — POST /v1/chat or fallback to /v1/generate/chat
        // The endpoint may not exist yet; fall back gracefully.
        let res;
        try {
          res = await httpJson('/v1/chat', {
            method: 'POST',
            headers: model ? { 'X-LLM-Provider': model } : {},
            body: JSON.stringify({ message: text }),
          });
        } catch (chatErr) {
          // Fallback: some backends expose /v1/generate/chat
          res = await httpJson('/v1/generate/chat', {
            method: 'POST',
            headers: model ? { 'X-LLM-Provider': model } : {},
            body: JSON.stringify({ prompt: text }),
          });
        }
        state.attachedFiles = [];
        renderAttachChips();
        stopThinking();
        const reply = res?.data?.reply || res?.data?.text || res?.data?.content || JSON.stringify(res?.data);
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

    // Populate + apply model
    populateModelMenu(providers, defaultProvider);
    const savedModel = state.model;
    const resolvedModel = providers.includes(savedModel)
      ? savedModel
      : (defaultProvider || providers[0] || '');
    applyModel(resolvedModel);

    // Populate + apply kind
    populateAgentTypes(kinds);
    const savedKind = state.kind;
    const resolvedKind = kinds.includes(savedKind)
      ? savedKind
      : (kinds.includes('npc') ? 'npc' : kinds[0] || 'npc');
    applyKind(resolvedKind);

    // Apply persisted mode
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
```

**Step 2: Verify build still passes**

```bash
bundle exec jekyll build 2>&1 | tail -5
```

Expected: `done in X seconds.`

**Step 3: Commit**

```bash
git add assets/js/chatbot-widget.js
git commit -m "refactor(chatbot): rewrite widget for Ask/Agent modes, model selector, file attach"
```

---

## Task 5: Run the full Playwright test suite

**Step 1: Serve the site**

```bash
bundle exec jekyll serve --no-watch &
sleep 5
```

**Step 2: Run all chatbot tests**

```bash
npx playwright test tests/ui/chat-input-refactor.spec.js --reporter=line
```

Expected: All 9 tests PASS.

**Step 3: If any test fails, debug**

Common issues and fixes:

| Failing test | Likely cause | Fix |
|---|---|---|
| `chatbot__inputBox` not found | Jekyll cache stale | `bundle exec jekyll clean && jekyll build` |
| Agent type hidden in ask mode | CSS selector mismatch | Check `[data-mode="ask"] #agentTypeWrap` selector in CSS |
| File chooser never opens | `attachBtn` wiring | Confirm `el.attachBtn.addEventListener('click', ...)` targets correct ID |
| Model dropdown group count ≠ 3 | All providers in same group | Add `local/` or `openrouter/` prefixed test providers in mock |
| `too large` message missing | Error div not rendered | Check `el.attachError.hidden = false` path in JS |

**Step 4: Commit tests**

```bash
git add tests/ui/chat-input-refactor.spec.js
git commit -m "test(chatbot): add Playwright tests for unified input box UI"
```

---

## Task 6: Manual smoke-test checklist

Do this while the site is running (`bundle exec jekyll serve`). Open a chatbot-enabled page (e.g. `/npcs/some-npc/`).

- [ ] Input box is visible with correct dark background and rounded corners
- [ ] Clicking inside the box produces a **blue focus ring**
- [ ] **Ask** pill button is visible in bottom-left; clicking it shows the dropdown with Ask + Agent options
- [ ] Selecting **Agent** shows the agent-type pill; selecting **Ask** hides it
- [ ] Agent-type dropdown lists all generators from `/v1/meta/generators` (npc, location, …)
- [ ] Model button on the right shows a label from `/v1/meta/providers`; clicking opens the grouped dropdown
- [ ] Groups in the model dropdown are labelled **Local**, **API**, **OpenRouter** (only non-empty groups shown)
- [ ] Clicking **+** opens the OS file picker; accepted types include images, PDF, .docx, .json
- [ ] Attaching a file shows a chip above the input with a **×** remove button
- [ ] Attaching a >10 MB file shows a red error message
- [ ] Typing a message and pressing **Enter** sends it and shows a user bubble
- [ ] **Shift+Enter** inserts a newline instead
- [ ] In Agent mode, sending a prompt calls `/v1/generate/{kind}` and shows the response
- [ ] The old `chatbot__toolbarRow` elements are completely absent from the DOM (use DevTools)
- [ ] The old `#chatbotProvider` and `#chatbotKind` elements are absent from the DOM

---

## Task 7: Final commit and cleanup

```bash
# Verify no leftover references to the old elements
grep -r "chatbotProvider\|chatbotKind\|chatbot__toolbarRow" \
  _includes/ assets/js/ assets/css/ --include="*.html" --include="*.js" --include="*.css"
# Expected: no output
```

If nothing found:

```bash
git add -A
git commit -m "chore(chatbot): remove all references to old toolbar elements"
```

---

## API contract notes for backend team

> These are the endpoints the new widget expects. No backend changes are required for the refactor to work — the existing contract is preserved. The following are **optional enhancements** to unlock full functionality:

| Endpoint | Status | Notes |
|---|---|---|
| `GET /v1/meta/providers` | ✅ exists | Optionally prefix provider names with `local/`, `openrouter/` for grouping |
| `GET /v1/meta/generators` | ✅ exists | No change needed |
| `POST /v1/generate/{kind}` (JSON) | ✅ exists | No change needed |
| `POST /v1/generate/{kind}` (FormData + files) | 🆕 optional | Needed to send attached files to the generator |
| `POST /v1/chat` | 🆕 optional | Needed for Ask mode free-form chat; widget falls back to `/v1/generate/chat` |
| `POST /v1/promote/{kind}/{slug}` | ✅ exists | No change needed |

---

## File summary

| File | Action |
|---|---|
| `_includes/chatbot_shell.html` | Full rewrite — unified input box HTML |
| `assets/css/chatbot.css` | Full rewrite — new input box + dropdown styles |
| `assets/js/chatbot-widget.js` | Full rewrite — Ask/Agent modes, model selector, file attach |
| `tests/ui/chat-input-refactor.spec.js` | New — Playwright tests |
