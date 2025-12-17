const { test, expect } = require('@playwright/test');
const fs = require('node:fs/promises');
const path = require('node:path');

async function getRepoRoot() {
  // tests/ui -> tests -> repo
  return path.resolve(__dirname, '../..');
}

async function getActiveCampaign(repoRoot) {
  try {
    const raw = await fs.readFile(path.join(repoRoot, '.active-campaign'), 'utf8');
    const name = (raw || '').trim();
    return name || null;
  } catch {
    return null;
  }
}

async function waitForLlmApiReady({ baseUrl = 'http://localhost:8000', timeoutMs = 60_000 } = {}) {
  const start = Date.now();
  const url = `${baseUrl.replace(/\/$/, '')}/v1/meta/generators`;

  // The API relaxes auth for localhost origins; mirror what the browser will send.
  const headers = { Origin: 'http://localhost:4100' };

  // Poll quickly; container startup can be a bit slow on first run.
  while (Date.now() - start < timeoutMs) {
    try {
      const res = await fetch(url, { headers });
      if (res.ok) return;
    } catch {
      // ignore and retry
    }
    // eslint-disable-next-line no-await-in-loop
    await new Promise((r) => setTimeout(r, 1_000));
  }

  throw new Error(`LLM API not ready after ${timeoutMs}ms: ${url}`);
}

test('UI chatbot: select generator, generate draft, promote', async ({ page }) => {
  const repoRoot = await getRepoRoot();
  const campaign = (await getActiveCampaign(repoRoot)) || 'rpg-theForsakenCrown';

  const slug = `ui-test-npc-${Date.now()}`;
  const promotedPath = path.join(repoRoot, 'campaigns', campaign, '_pages', 'npcs', `${slug}.md`);

  // Ensure prior run doesn't collide.
  await fs.unlink(promotedPath).catch(() => undefined);

  page.on('console', (msg) => {
    // Helpful when debugging headless failures.
    // eslint-disable-next-line no-console
    console.log(`[browser:${msg.type()}] ${msg.text()}`);
  });

  await waitForLlmApiReady();

  await page.goto('/tools/chat/', { waitUntil: 'domcontentloaded' });

  await expect(page.locator('#llmProvider')).toBeVisible({ timeout: 20_000 });
  await expect(page.locator('#output')).toContainText('Generators:', { timeout: 30_000 });

  // Select the generator.
  await page.fill('#chatInput', '/generate npc');
  await page.keyboard.press('Enter');

  await expect(page.locator('#output')).toContainText('Selected generator: npc', { timeout: 30_000 });

  // Wait until the schema panel has loaded.
  await expect(page.locator('#schemaPanel')).toContainText('Generator:', { timeout: 30_000 });
  await expect(page.locator('#schemaPanel')).toContainText('npc', { timeout: 30_000 });

  // Fill optional fields (slug + title) so we don't overwrite anything.
  const optionalSummary = page.locator('#schemaPanel details summary');
  if (await optionalSummary.count()) {
    await optionalSummary.first().click();
  }

  const slugInput = page.locator('#schemaPanel [data-field="slug"]');
  if (await slugInput.count()) {
    await slugInput.fill(slug);
  }

  // Generate.
  await page.fill('#chatInput', 'Create a very short NPC for UI automation testing.');
  const genResponse = page.waitForResponse(
    (resp) => resp.url().includes('/v1/generate/npc') && resp.status() === 201,
    { timeout: 180_000 }
  );

  await page.click('#sendBtn');

  const gen = await genResponse;
  const genJson = await gen.json();
  const actualSlug = genJson?.data?.slug;
  expect(actualSlug).toBeTruthy();

  await expect(page.locator('#output')).toContainText('draft_path=', { timeout: 60_000 });
  await expect(page.locator('#output')).toContainText(`slug=${actualSlug}`, { timeout: 60_000 });

  // Promote.
  const promoteBtn = page.locator('#schemaPanel #promoteWrap button');
  await expect(promoteBtn).toBeVisible({ timeout: 20_000 });

  const promoteResponse = page.waitForResponse(
    (resp) => resp.url().includes(`/v1/promote/npc/${encodeURIComponent(actualSlug)}`) && resp.status() === 200,
    { timeout: 60_000 }
  );
  await promoteBtn.click();

  await promoteResponse;

  await expect(page.locator('#output')).toContainText('Promoted to:', { timeout: 60_000 });

  // Cleanup to avoid leaving generated files behind.
  const promotedActual = path.join(repoRoot, 'campaigns', campaign, '_pages', 'npcs', `${actualSlug}.md`);
  await fs.unlink(promotedActual).catch(() => undefined);
});
