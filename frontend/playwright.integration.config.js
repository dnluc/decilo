import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests/integration',
  workers: 1,
  use: {
    baseURL: 'http://127.0.0.1:5174',
    launchOptions: process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {},
  },
  webServer: [
    {
      command: 'python -m uvicorn browser_backend:app --app-dir tests/integration --host 127.0.0.1 --port 18764',
      url: 'http://127.0.0.1:18764/health',
      env: { PYTHONPATH: '../src', DECILO_DEMO_SESSIONS: '0', DECILO_PARTIALS: '0' },
    },
    {
      command: 'npm run dev -- --port 5174',
      url: 'http://127.0.0.1:5174',
      env: { DECILO_BACKEND_URL: 'http://127.0.0.1:18764' },
    },
  ],
});
