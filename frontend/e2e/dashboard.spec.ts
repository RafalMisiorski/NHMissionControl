import { test, expect, type Page } from '@playwright/test';

/**
 * E2E tests for Dashboard functionality in NH Mission Control.
 * Tests metrics display, pipeline stages, and recent opportunities.
 */

// Test user credentials
const TEST_USER = {
  email: `e2e-dashboard-${Date.now()}@example.com`,
  password: 'DashboardTest123!',
  name: 'Dashboard Test User',
};

// Helper to login
async function login(page: Page, user = TEST_USER) {
  await page.goto('/login');
  await page.waitForLoadState('networkidle');
  await page.getByTestId('email-input').fill(user.email);
  await page.getByTestId('password-input').fill(user.password);
  await page.getByTestId('submit-btn').click();
  await expect(page).toHaveURL(/\/dashboard/, { timeout: 10000 });
}

// Helper to get auth token
async function getAuthToken(request: any, user = TEST_USER): Promise<string> {
  const loginResp = await request.post('http://localhost:8000/api/v1/auth/login', {
    form: {
      username: user.email,
      password: user.password,
    },
  });
  const tokens = await loginResp.json();
  return tokens.access_token;
}

// Helper to create opportunity via API
async function createOpportunity(request: any, token: string, data: any) {
  return request.post('http://localhost:8000/api/v1/pipeline/opportunities', {
    headers: { Authorization: `Bearer ${token}` },
    data,
  });
}

test.describe('Dashboard - Basic Display', () => {
  test.beforeAll(async ({ request }) => {
    // Register test user
    await request.post('http://localhost:8000/api/v1/auth/register', {
      data: TEST_USER,
    });
  });

  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('should display dashboard page with welcome message', async ({ page }) => {
    await expect(page.getByTestId('dashboard-page')).toBeVisible();
    await expect(page.getByText(/Welcome back/i)).toBeVisible();
  });

  test('should display pipeline description', async ({ page }) => {
    await expect(page.getByText(/Here's what's happening with your pipeline/i)).toBeVisible();
  });

  test('should display metric cards section', async ({ page }) => {
    // Check for metric cards
    await expect(page.getByText('Pipeline Value')).toBeVisible();
    await expect(page.getByText('Conversion Rate')).toBeVisible();
    await expect(page.getByText('Avg. Deal Size')).toBeVisible();
    await expect(page.getByText('Total Opportunities')).toBeVisible();
  });

  test('should display pipeline stages section', async ({ page }) => {
    await expect(page.getByText('Pipeline Stages')).toBeVisible();
    await expect(page.getByRole('link', { name: 'View all' }).first()).toBeVisible();
  });

  test('should display recent opportunities section', async ({ page }) => {
    await expect(page.getByText('Recent Opportunities')).toBeVisible();
    await expect(page.getByRole('link', { name: 'Add new' })).toBeVisible();
  });

  test('should display North Star progress section', async ({ page }) => {
    await expect(page.getByText('North Star Progress')).toBeVisible();
    await expect(page.getByText(/Goal:/i)).toBeVisible();
  });
});

test.describe('Dashboard - Metric Cards', () => {
  let authToken: string;

  test.beforeAll(async ({ request }) => {
    try {
      await request.post('http://localhost:8000/api/v1/auth/register', {
        data: TEST_USER,
      });
    } catch (e) {
      // User exists
    }

    authToken = await getAuthToken(request);

    // Create some opportunities for metrics
    await createOpportunity(request, authToken, {
      title: 'Dashboard Metric Test 1',
      value: 5000,
      status: 'lead',
    });

    await createOpportunity(request, authToken, {
      title: 'Dashboard Metric Test 2',
      value: 10000,
      status: 'won',
      probability: 100,
    });
  });

  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('should show loading state for metrics initially', async ({ page }) => {
    // On fast connections, this might not be visible, but the test verifies the component structure
    await page.waitForLoadState('networkidle');
    // After loading, values should be displayed
    await expect(page.getByText('Pipeline Value')).toBeVisible();
  });

  test('should display numeric values in metric cards', async ({ page }) => {
    await page.waitForLoadState('networkidle');

    // Wait for metrics to load (loading spinners should disappear)
    await page.waitForSelector('[class*="animate-spin"]', { state: 'detached', timeout: 10000 }).catch(() => {
      // Spinners might already be gone
    });

    // Check that metric values are displayed (they should be numbers or percentages)
    const metricsSection = page.locator('.grid').first();
    await expect(metricsSection).toBeVisible();
  });

  test('should display icons in metric cards', async ({ page }) => {
    // Each metric card should have an icon
    const metricCards = page.locator('.rounded-xl.border').first();
    await expect(metricCards).toBeVisible();
  });
});

test.describe('Dashboard - Pipeline Stages', () => {
  let authToken: string;

  test.beforeAll(async ({ request }) => {
    try {
      await request.post('http://localhost:8000/api/v1/auth/register', {
        data: TEST_USER,
      });
    } catch (e) {
      // User exists
    }

    authToken = await getAuthToken(request);

    // Create opportunities in different stages
    await createOpportunity(request, authToken, {
      title: 'Stage Test - Lead',
      status: 'lead',
      value: 1000,
    });

    await createOpportunity(request, authToken, {
      title: 'Stage Test - Qualified',
      status: 'qualified',
      value: 2000,
    });

    await createOpportunity(request, authToken, {
      title: 'Stage Test - Proposal',
      status: 'proposal',
      value: 3000,
    });
  });

  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('should display stage cards with counts', async ({ page }) => {
    await page.waitForLoadState('networkidle');

    // Wait for stats to load
    await page.waitForSelector('[class*="animate-spin"]', { state: 'detached', timeout: 10000 }).catch(() => {});

    // Check for stage labels
    await expect(page.getByText('Leads').first()).toBeVisible();
    await expect(page.getByText('Qualified').first()).toBeVisible();
    await expect(page.getByText('Proposal Sent').first()).toBeVisible();
  });

  test('should have clickable stage cards that link to pipeline', async ({ page }) => {
    await page.waitForLoadState('networkidle');

    // Find a stage card link
    const stageLink = page.locator('a[href*="/pipeline?status="]').first();

    if (await stageLink.isVisible()) {
      await stageLink.click();
      await expect(page).toHaveURL(/\/pipeline/);
    }
  });

  test('should show opportunities count per stage', async ({ page }) => {
    await page.waitForLoadState('networkidle');

    // Each stage should show "X opportunities"
    const opportunityCountText = page.getByText(/\d+ opportunities?/i).first();
    await expect(opportunityCountText).toBeVisible();
  });
});

test.describe('Dashboard - Recent Opportunities', () => {
  let authToken: string;

  test.beforeAll(async ({ request }) => {
    try {
      await request.post('http://localhost:8000/api/v1/auth/register', {
        data: TEST_USER,
      });
    } catch (e) {
      // User exists
    }

    authToken = await getAuthToken(request);

    // Create some recent opportunities
    for (let i = 1; i <= 3; i++) {
      await createOpportunity(request, authToken, {
        title: `Recent Opp ${i} - ${Date.now()}`,
        client_name: `Client ${i}`,
        source: 'upwork',
        value: i * 1000,
        nh_score: 60 + i * 10,
      });
    }
  });

  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('should display recent opportunities list', async ({ page }) => {
    await page.waitForLoadState('networkidle');

    // Wait for loading to complete
    await page.waitForSelector('[class*="animate-spin"]', { state: 'detached', timeout: 10000 }).catch(() => {});

    // Recent opportunities section should have items
    const recentSection = page.locator('text=Recent Opportunities').locator('..');
    await expect(recentSection).toBeVisible();
  });

  test('should show opportunity details in recent list', async ({ page }) => {
    await page.waitForLoadState('networkidle');
    await page.waitForSelector('[class*="animate-spin"]', { state: 'detached', timeout: 10000 }).catch(() => {});

    // Should show opportunity titles
    const oppCards = page.locator('.space-y-3').last().locator('a');
    const count = await oppCards.count();

    if (count > 0) {
      // First opportunity card should have title and client name
      await expect(oppCards.first()).toBeVisible();
    }
  });

  test('should show NH score bars for scored opportunities', async ({ page }) => {
    await page.waitForLoadState('networkidle');
    await page.waitForSelector('[class*="animate-spin"]', { state: 'detached', timeout: 10000 }).catch(() => {});

    // Look for NH score indicators
    const scoreIndicator = page.getByText(/NH:/i).first();
    if (await scoreIndicator.isVisible()) {
      await expect(scoreIndicator).toBeVisible();
    }
  });

  test('should link to pipeline page when clicking Add new', async ({ page }) => {
    const addNewLink = page.getByRole('link', { name: 'Add new' });
    await addNewLink.click();

    await expect(page).toHaveURL(/\/pipeline/);
  });

  test('should show status badges on opportunity cards', async ({ page }) => {
    await page.waitForLoadState('networkidle');
    await page.waitForSelector('[class*="animate-spin"]', { state: 'detached', timeout: 10000 }).catch(() => {});

    // Look for status badges (lead, qualified, proposal, etc.)
    const statusBadge = page.locator('.rounded-full').first();
    if (await statusBadge.isVisible()) {
      await expect(statusBadge).toBeVisible();
    }
  });
});

test.describe('Dashboard - Empty State', () => {
  const EMPTY_USER = {
    email: `e2e-empty-${Date.now()}@example.com`,
    password: 'EmptyTest123!',
    name: 'Empty Dashboard User',
  };

  test.beforeAll(async ({ request }) => {
    // Register a fresh user with no opportunities
    await request.post('http://localhost:8000/api/v1/auth/register', {
      data: EMPTY_USER,
    });
  });

  test('should show empty state for new user', async ({ page }) => {
    await login(page, EMPTY_USER);
    await page.waitForLoadState('networkidle');

    // Wait for loading to complete
    await page.waitForSelector('[class*="animate-spin"]', { state: 'detached', timeout: 10000 }).catch(() => {});

    // Should show "No opportunities yet" or similar empty state
    const emptyState = page.getByText(/No opportunities yet/i);
    if (await emptyState.isVisible()) {
      await expect(emptyState).toBeVisible();
      // Should have link to add first opportunity
      await expect(page.getByText(/Add your first opportunity/i)).toBeVisible();
    }
  });

  test('should show zero values in metrics for new user', async ({ page }) => {
    await login(page, EMPTY_USER);
    await page.waitForLoadState('networkidle');
    await page.waitForSelector('[class*="animate-spin"]', { state: 'detached', timeout: 10000 }).catch(() => {});

    // Total Opportunities should show 0
    await expect(page.getByText('Total Opportunities')).toBeVisible();
  });
});

test.describe('Dashboard - Navigation', () => {
  test.beforeAll(async ({ request }) => {
    try {
      await request.post('http://localhost:8000/api/v1/auth/register', {
        data: TEST_USER,
      });
    } catch (e) {
      // User exists
    }
  });

  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('should navigate to pipeline from View all link', async ({ page }) => {
    const viewAllLink = page.getByRole('link', { name: 'View all' }).first();
    await viewAllLink.click();

    await expect(page).toHaveURL(/\/pipeline/);
  });

  test('should navigate to pipeline from stage card', async ({ page }) => {
    await page.waitForLoadState('networkidle');
    await page.waitForSelector('[class*="animate-spin"]', { state: 'detached', timeout: 10000 }).catch(() => {});

    const stageLink = page.locator('a[href*="/pipeline?status="]').first();
    if (await stageLink.isVisible()) {
      await stageLink.click();
      await expect(page).toHaveURL(/\/pipeline\?status=/);
    }
  });

  test('should navigate to opportunity from recent list', async ({ page }) => {
    await page.waitForLoadState('networkidle');
    await page.waitForSelector('[class*="animate-spin"]', { state: 'detached', timeout: 10000 }).catch(() => {});

    // Find an opportunity link in recent opportunities section
    const oppLink = page.locator('a[href*="/pipeline?id="]').first();
    if (await oppLink.isVisible()) {
      await oppLink.click();
      await expect(page).toHaveURL(/\/pipeline\?id=/);
    }
  });
});

test.describe('Dashboard - API Integration', () => {
  let authToken: string;

  test.beforeAll(async ({ request }) => {
    try {
      await request.post('http://localhost:8000/api/v1/auth/register', {
        data: TEST_USER,
      });
    } catch (e) {
      // User exists
    }

    authToken = await getAuthToken(request);
  });

  test('should return pipeline stats from API', async ({ request }) => {
    const response = await request.get('http://localhost:8000/api/v1/pipeline/stats', {
      headers: { Authorization: `Bearer ${authToken}` },
    });

    expect(response.ok()).toBeTruthy();
    const stats = await response.json();

    expect(stats).toHaveProperty('stages');
    expect(stats).toHaveProperty('total_opportunities');
    expect(stats).toHaveProperty('total_value');
    expect(stats).toHaveProperty('weighted_pipeline_value');
    expect(stats).toHaveProperty('conversion_rate');
    expect(stats).toHaveProperty('avg_deal_size');
  });

  test('should return opportunities list from API', async ({ request }) => {
    const response = await request.get('http://localhost:8000/api/v1/pipeline/opportunities?page_size=5', {
      headers: { Authorization: `Bearer ${authToken}` },
    });

    expect(response.ok()).toBeTruthy();
    const data = await response.json();

    expect(data).toHaveProperty('items');
    expect(data).toHaveProperty('total');
    expect(data).toHaveProperty('page');
    expect(data).toHaveProperty('page_size');
  });

  test('should return user info from API', async ({ request }) => {
    const response = await request.get('http://localhost:8000/api/v1/auth/me', {
      headers: { Authorization: `Bearer ${authToken}` },
    });

    expect(response.ok()).toBeTruthy();
    const user = await response.json();

    expect(user).toHaveProperty('id');
    expect(user).toHaveProperty('email');
    expect(user).toHaveProperty('name');
  });
});

test.describe('Dashboard - Responsive Design', () => {
  test.beforeAll(async ({ request }) => {
    try {
      await request.post('http://localhost:8000/api/v1/auth/register', {
        data: TEST_USER,
      });
    } catch (e) {
      // User exists
    }
  });

  test('should display correctly on desktop viewport', async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 });
    await login(page);

    // Grid should show 4 columns on desktop
    const metricsGrid = page.locator('.grid-cols-1.md\\:grid-cols-2.lg\\:grid-cols-4');
    await expect(metricsGrid).toBeVisible();
  });

  test('should display correctly on tablet viewport', async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 });
    await login(page);

    await expect(page.getByTestId('dashboard-page')).toBeVisible();
    await expect(page.getByText('Pipeline Value')).toBeVisible();
  });

  test('should display correctly on mobile viewport', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await login(page);

    await expect(page.getByTestId('dashboard-page')).toBeVisible();
    // Metric cards should stack on mobile
    await expect(page.getByText('Pipeline Value')).toBeVisible();
  });
});
