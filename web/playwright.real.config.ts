import { defineConfig } from '@playwright/test';

// Runs the same journey against a real server (default 127.0.0.1:8765, started with --fake-teammates).
// E2E_BASE_URL: use an already-running web app (e.g. the server serving the build). Otherwise Vite is
// started on 5176 and proxies /api, /ws and /portraits to OL_API.
const external = process.env.E2E_BASE_URL;

export default defineConfig({
  testDir: 'e2e-real',
  outputDir: 'test-results/pw-real',
  timeout: 360_000,
  workers: 1,
  fullyParallel: false,
  reporter: [['list']],
  use: {
    baseURL: external ?? 'http://127.0.0.1:5176',
    headless: true,
    viewport: { width: 1280, height: 800 },
    launchOptions: { args: ['--no-sandbox'] },
  },
  webServer: external
    ? undefined
    : {
        command: 'pnpm exec vite --port 5176 --host 127.0.0.1',
        url: 'http://127.0.0.1:5176',
        reuseExistingServer: true,
        env: { OL_API: process.env.OL_API ?? 'http://127.0.0.1:8765' },
      },
});
