const { test, expect } = require('@playwright/test');
const fs = require('node:fs/promises');
const path = require('node:path');

async function getRepoRoot() {
  return path.resolve(__dirname, '../..');
}

async function findDmContentUrls(repoRoot) {
  const siteRoot = path.join(repoRoot, '_site-ui');
  const candidates = [];

  async function walk(dir, relBase) {
    const entries = await fs.readdir(dir, { withFileTypes: true });
    for (const e of entries) {
      const abs = path.join(dir, e.name);
      const rel = path.join(relBase, e.name);
      if (e.isDirectory()) {
        // Avoid extremely deep walks.
        if (rel.split(path.sep).length > 6) continue;
        await walk(abs, rel);
      } else if (e.isFile() && e.name === 'index.html') {
        // Convert rel path into a URL.
        const urlPath = `/${rel.replace(/\\/g, '/').replace(/index\.html$/, '')}`;
        // Only keep DM content sections.
        if (
          urlPath.startsWith('/chapters/') ||
          urlPath.startsWith('/locations/') ||
          urlPath.startsWith('/monsters/') ||
          urlPath.startsWith('/encounters/') ||
          urlPath.startsWith('/npcs/') ||
          urlPath.startsWith('/rewards/')
        ) {
          candidates.push(urlPath);
        }
      }
    }
  }

  // Walk a few known content roots (keeps it fast).
  for (const root of ['chapters', 'locations', 'monsters', 'encounters', 'npcs', 'rewards']) {
    const abs = path.join(siteRoot, root);
    await fs
      .stat(abs)
      .then(() => walk(abs, root))
      .catch(() => undefined);
  }

  // De-dup and keep stable ordering.
  const uniq = Array.from(new Set(candidates)).sort();
  return uniq;
}

test('Global chatbot shows on DM pages and hides on excluded pages', async ({ page }) => {
  await page.goto('/', { waitUntil: 'domcontentloaded' });
  await page.evaluate(() => localStorage.clear());
  await page.reload({ waitUntil: 'domcontentloaded' });
  await expect(page.locator('#global-chatbot')).toHaveCount(0);

  await page.goto('/tools/chat/', { waitUntil: 'domcontentloaded' });
  await expect(page.locator('#global-chatbot')).toHaveCount(0);

  await page.goto('/toc/', { waitUntil: 'domcontentloaded' });
  await expect(page.locator('#global-chatbot')).toHaveCount(0);

  await page.goto('/search-results.html', { waitUntil: 'domcontentloaded' });
  await expect(page.locator('#global-chatbot')).toHaveCount(0);

  const repoRoot = await getRepoRoot();
  const urls = await findDmContentUrls(repoRoot);
  expect(urls.length).toBeGreaterThan(0);

  await page.goto(urls[0], { waitUntil: 'domcontentloaded' });
  await expect(page.locator('#global-chatbot')).toHaveCount(1);
  await expect(page.locator('#global-chatbot .chatbot__panel')).toBeVisible();
});

test('Global chatbot collapse state persists across DM pages', async ({ page }) => {
  const repoRoot = await getRepoRoot();
  const urls = await findDmContentUrls(repoRoot);
  expect(urls.length).toBeGreaterThan(1);

  await page.goto(urls[0], { waitUntil: 'domcontentloaded' });
  await page.evaluate(() => localStorage.clear());
  await page.reload({ waitUntil: 'domcontentloaded' });
  await expect(page.locator('#global-chatbot')).toHaveCount(1);

  // Collapse.
  await page.click('#chatbotToggle');
  await expect(page.locator('html')).toHaveClass(/chatbot-collapsed/);

  // Navigate to another DM page; the pre-render script should reapply the class.
  await page.goto(urls[1], { waitUntil: 'domcontentloaded' });
  await expect(page.locator('#global-chatbot')).toHaveCount(1);
  await expect(page.locator('html')).toHaveClass(/chatbot-collapsed/);

  // Expand from floating toggle.
  await page.click('#chatbotFloatingToggle');
  await expect(page.locator('html')).not.toHaveClass(/chatbot-collapsed/);
});
