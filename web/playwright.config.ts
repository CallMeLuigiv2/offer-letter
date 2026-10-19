import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: 'e2e',
  outputDir: 'test-results/pw',
  timeout: 90_000,
  fullyParallel: false,
  workers: 1,
  reporter: [['list']],
  use: {
    baseURL: 'http://127.0.0.1:5174',
    headless: true,
    viewport: { width: 1280, height: 800 },
    launchOptions: { args: ['--no-sandbox'] },
  },
  webServer: {
    command: 'pnpm exec vite --port 5174 --host 127.0.0.1',
    url: 'http://127.0.0.1:5174',
    reuseExistingServer: false,
    env: { VITE_MOCK: '1', VITE_MOCK_FAST: '1' },
  },
});
