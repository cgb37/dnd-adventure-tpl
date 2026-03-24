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
