import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright configuration for NH Mission Control E2E tests.
 * See https://playwright.dev/docs/test-configuration
 *
 * Tests cover:
 * - Authentication flows (login, register, logout)
 * - Pipeline management (CRUD, Kanban board)
 * - Dashboard functionality (metrics, stats)
 */
export default defineConfig({
  testDir: './e2e',
  fullyParallel: false, // Run tests serially to avoid auth conflicts
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 1,
  workers: 1, // Single worker to prevent test isolation issues
  reporter: [
    ['html', { open: 'never' }],
    ['list'],
  ],
  timeout: 60000, // 60s per test
  expect: {
    timeout: 10000, // 10s for assertions
  },
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    // Viewport for consistent testing
    viewport: { width: 1280, height: 720 },
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: [
    {
      // Backend API server (FastAPI)
      // Run from backend directory to ensure correct module resolution
      command: 'python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000',
      url: 'http://localhost:8000/health',
      cwd: '../backend',
      reuseExistingServer: !process.env.CI,
      timeout: 60000,
      env: {
        DATABASE_URL: 'sqlite+aiosqlite:///./test_e2e.db',
        SECRET_KEY: 'e2e-test-secret-key-for-jwt-tokens-12345',
        ENVIRONMENT: 'testing',
      },
    },
    {
      // Frontend dev server (Vite)
      command: 'npm run dev',
      url: 'http://localhost:3000',
      reuseExistingServer: !process.env.CI,
      timeout: 60000,
    },
  ],
});
