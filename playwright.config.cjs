const { defineConfig } = require('@playwright/test');

module.exports = defineConfig({
  testDir: './tests/ui',
  timeout: 180_000,
  expect: {
    timeout: 20_000,
  },
  webServer: {
    // Serve the already-built `_site/` without live reload to avoid flakiness
    // from Jekyll auto-regeneration during UI automation.
    command: 'python3 -m http.server 4100 --directory _site-ui',
    port: 4100,
    reuseExistingServer: true,
    timeout: 120_000,
  },
  use: {
    baseURL: process.env.UI_BASE_URL || 'http://localhost:4100',
    headless: process.env.HEADED ? false : true,
    viewport: { width: 1280, height: 720 },
  },
});
