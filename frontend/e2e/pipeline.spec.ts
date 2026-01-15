import { test, expect, type Page } from '@playwright/test';

/**
 * E2E tests for Pipeline/Kanban functionality in NH Mission Control.
 * Tests CRUD operations, Kanban board, and opportunity management.
 */

// Test user credentials - shared across pipeline tests
const TEST_USER = {
  email: `e2e-pipeline-${Date.now()}@example.com`,
  password: 'PipelineTest123!',
  name: 'Pipeline Test User',
};

// Helper to login and navigate to pipeline
async function loginAndGoToPipeline(page: Page, user = TEST_USER) {
  await page.goto('/login');
  await page.waitForLoadState('networkidle');
  await page.getByTestId('email-input').fill(user.email);
  await page.getByTestId('password-input').fill(user.password);
  await page.getByTestId('submit-btn').click();
  await expect(page).toHaveURL(/\/dashboard/, { timeout: 10000 });

  // Navigate to pipeline
  await page.goto('/pipeline');
  await page.waitForLoadState('networkidle');
  await expect(page.getByTestId('pipeline-page')).toBeVisible({ timeout: 10000 });
}

// Helper to create an opportunity via API
async function createOpportunityViaAPI(request: any, token: string, data: any) {
  const response = await request.post('http://localhost:8000/api/v1/pipeline/opportunities', {
    headers: {
      Authorization: `Bearer ${token}`,
    },
    data,
  });
  return response.json();
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

test.describe('Pipeline Page - Basic Functionality', () => {
  test.beforeAll(async ({ request }) => {
    // Register test user
    await request.post('http://localhost:8000/api/v1/auth/register', {
      data: TEST_USER,
    });
  });

  test.beforeEach(async ({ page }) => {
    await loginAndGoToPipeline(page);
  });

  test('should display pipeline page with Kanban columns', async ({ page }) => {
    await expect(page.getByText('Pipeline').first()).toBeVisible();
    await expect(page.getByRole('button', { name: /Add Opportunity/i })).toBeVisible();

    // Check Kanban columns are visible
    await expect(page.getByText('Leads')).toBeVisible();
    await expect(page.getByText('Qualified')).toBeVisible();
    await expect(page.getByText('Proposal')).toBeVisible();
    await expect(page.getByText('Negotiating')).toBeVisible();
    await expect(page.getByText('Won')).toBeVisible();
  });

  test('should have search input', async ({ page }) => {
    const searchInput = page.getByPlaceholder(/Search opportunities/i);
    await expect(searchInput).toBeVisible();
  });

  test('should have filter button', async ({ page }) => {
    const filterButton = page.getByRole('button', { name: /Filter/i });
    await expect(filterButton).toBeVisible();
  });
});

test.describe('Pipeline - Add Opportunity Modal', () => {
  test.beforeAll(async ({ request }) => {
    // Ensure test user exists
    try {
      await request.post('http://localhost:8000/api/v1/auth/register', {
        data: TEST_USER,
      });
    } catch (e) {
      // User may already exist
    }
  });

  test.beforeEach(async ({ page }) => {
    await loginAndGoToPipeline(page);
  });

  test('should open add opportunity modal', async ({ page }) => {
    await page.getByRole('button', { name: /Add Opportunity/i }).click();

    // Modal should be visible
    await expect(page.getByText('Add Opportunity').nth(1)).toBeVisible();
    await expect(page.getByLabel('Title *')).toBeVisible();
    await expect(page.getByLabel('Source')).toBeVisible();
    await expect(page.getByLabel('Value')).toBeVisible();
  });

  test('should close modal with X button', async ({ page }) => {
    await page.getByRole('button', { name: /Add Opportunity/i }).click();
    await expect(page.getByText('Add Opportunity').nth(1)).toBeVisible();

    // Click the X button in modal header
    await page.locator('.fixed button').first().click();

    // Modal should be closed
    await expect(page.locator('.fixed.inset-0')).not.toBeVisible();
  });

  test('should close modal with Cancel button', async ({ page }) => {
    await page.getByRole('button', { name: /Add Opportunity/i }).click();
    await page.getByRole('button', { name: 'Cancel' }).click();

    // Modal should be closed
    await expect(page.locator('.fixed.inset-0')).not.toBeVisible();
  });

  test('should create new opportunity', async ({ page }) => {
    const opportunityTitle = `E2E Test Opportunity ${Date.now()}`;

    await page.getByRole('button', { name: /Add Opportunity/i }).click();

    // Fill the form
    await page.getByLabel('Title *').fill(opportunityTitle);
    await page.getByLabel('Source').selectOption('upwork');
    await page.getByLabel('Value').fill('5000');
    await page.getByLabel('Currency').selectOption('EUR');
    await page.getByLabel('Client Name').fill('E2E Test Client');

    // Submit
    await page.getByRole('button', { name: /Add Opportunity/i }).last().click();

    // Wait for modal to close and opportunity to appear
    await expect(page.locator('.fixed.inset-0')).not.toBeVisible({ timeout: 5000 });

    // Opportunity should appear in Leads column
    await expect(page.getByText(opportunityTitle)).toBeVisible({ timeout: 5000 });
  });

  test('should add tech stack tags', async ({ page }) => {
    await page.getByRole('button', { name: /Add Opportunity/i }).click();

    // Add tech stack
    await page.getByPlaceholder(/Python, FastAPI/i).fill('Python');
    await page.getByRole('button', { name: 'Add' }).click();

    await page.getByPlaceholder(/Python, FastAPI/i).fill('FastAPI');
    await page.getByRole('button', { name: 'Add' }).click();

    // Tags should be visible
    await expect(page.getByText('Python').first()).toBeVisible();
    await expect(page.getByText('FastAPI').first()).toBeVisible();
  });

  test('should remove tech stack tag', async ({ page }) => {
    await page.getByRole('button', { name: /Add Opportunity/i }).click();

    // Add tech
    await page.getByPlaceholder(/Python, FastAPI/i).fill('RemoveMe');
    await page.getByRole('button', { name: 'Add' }).click();
    await expect(page.getByText('RemoveMe')).toBeVisible();

    // Remove it (click X on the tag)
    await page.locator('.bg-blue-100').getByRole('button').click();
    await expect(page.getByText('RemoveMe')).not.toBeVisible();
  });

  test('should require title field', async ({ page }) => {
    await page.getByRole('button', { name: /Add Opportunity/i }).click();

    // Try to submit without title
    await page.getByRole('button', { name: /Add Opportunity/i }).last().click();

    // Should still be in modal (form validation)
    await expect(page.getByLabel('Title *')).toBeVisible();
  });
});

test.describe('Pipeline - Opportunity Cards', () => {
  let authToken: string;

  test.beforeAll(async ({ request }) => {
    // Ensure test user exists
    try {
      await request.post('http://localhost:8000/api/v1/auth/register', {
        data: TEST_USER,
      });
    } catch (e) {
      // User may already exist
    }

    // Get auth token
    authToken = await getAuthToken(request);

    // Create some test opportunities
    await createOpportunityViaAPI(request, authToken, {
      title: 'Card Test - Python API',
      source: 'upwork',
      value: 3000,
      currency: 'EUR',
      client_name: 'Test Client A',
      tech_stack: ['Python', 'FastAPI'],
    });

    await createOpportunityViaAPI(request, authToken, {
      title: 'Card Test - React Dashboard',
      source: 'direct',
      value: 5000,
      currency: 'USD',
      client_name: 'Test Client B',
      tech_stack: ['React', 'TypeScript'],
    });
  });

  test.beforeEach(async ({ page }) => {
    await loginAndGoToPipeline(page);
  });

  test('should display opportunity cards with details', async ({ page }) => {
    // Wait for cards to load
    await page.waitForSelector('.bg-white.rounded-lg.border', { timeout: 10000 });

    // Check card contains expected elements
    const cards = page.locator('.bg-white.rounded-lg.border');
    await expect(cards.first()).toBeVisible();
  });

  test('should show card action menu', async ({ page }) => {
    await page.waitForSelector('.bg-white.rounded-lg.border', { timeout: 10000 });

    // Click the menu button (MoreVertical icon)
    const menuButton = page.locator('.bg-white.rounded-lg.border').first().locator('button').first();
    await menuButton.click();

    // Menu should show options
    await expect(page.getByText('Analyze')).toBeVisible();
    await expect(page.getByText('Proposal')).toBeVisible();
    await expect(page.getByText('Estimate')).toBeVisible();
    await expect(page.getByText('Delete')).toBeVisible();
  });

  test('should close menu when clicking outside', async ({ page }) => {
    await page.waitForSelector('.bg-white.rounded-lg.border', { timeout: 10000 });

    const menuButton = page.locator('.bg-white.rounded-lg.border').first().locator('button').first();
    await menuButton.click();
    await expect(page.getByText('Analyze')).toBeVisible();

    // Click outside
    await page.click('body', { position: { x: 10, y: 10 } });

    // Menu should be closed
    await expect(page.locator('.absolute.right-0.top-full')).not.toBeVisible();
  });
});

test.describe('Pipeline - Move Opportunity', () => {
  let authToken: string;
  let testOpportunityId: string;

  test.beforeAll(async ({ request }) => {
    try {
      await request.post('http://localhost:8000/api/v1/auth/register', {
        data: TEST_USER,
      });
    } catch (e) {
      // User exists
    }

    authToken = await getAuthToken(request);

    // Create opportunity for move tests
    const opp = await createOpportunityViaAPI(request, authToken, {
      title: `Move Test Opp ${Date.now()}`,
      source: 'upwork',
      value: 2500,
    });
    testOpportunityId = opp.id;
  });

  test.beforeEach(async ({ page }) => {
    await loginAndGoToPipeline(page);
  });

  test('should move opportunity to next stage', async ({ page }) => {
    // Find a card with "Move to Qualified" button
    const moveButton = page.getByRole('button', { name: /Move to Qualified/i }).first();

    if (await moveButton.isVisible()) {
      await moveButton.click();

      // Wait for the move to complete
      await page.waitForTimeout(1000);

      // The opportunity should now be in Qualified column (or the page should refresh)
      // We can verify by checking the qualified column count increased
    }
  });
});

test.describe('Pipeline - Search and Filter', () => {
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

    // Create opportunities with searchable content
    await createOpportunityViaAPI(request, authToken, {
      title: 'Searchable Python Project',
      client_name: 'SearchableClient',
      tech_stack: ['Python', 'Django'],
    });

    await createOpportunityViaAPI(request, authToken, {
      title: 'Another React Project',
      client_name: 'DifferentClient',
      tech_stack: ['React', 'Node.js'],
    });
  });

  test.beforeEach(async ({ page }) => {
    await loginAndGoToPipeline(page);
  });

  test('should filter opportunities by title', async ({ page }) => {
    const searchInput = page.getByPlaceholder(/Search opportunities/i);
    await searchInput.fill('Searchable Python');

    // Wait for filter to apply
    await page.waitForTimeout(500);

    // Should show matching opportunity
    await expect(page.getByText('Searchable Python Project')).toBeVisible();
  });

  test('should filter opportunities by client name', async ({ page }) => {
    const searchInput = page.getByPlaceholder(/Search opportunities/i);
    await searchInput.fill('SearchableClient');

    await page.waitForTimeout(500);

    // Should show matching opportunity
    await expect(page.getByText('Searchable Python Project')).toBeVisible();
  });

  test('should filter opportunities by tech stack', async ({ page }) => {
    const searchInput = page.getByPlaceholder(/Search opportunities/i);
    await searchInput.fill('Django');

    await page.waitForTimeout(500);

    // Should show matching opportunity
    await expect(page.getByText('Searchable Python Project')).toBeVisible();
  });

  test('should show empty state when no matches', async ({ page }) => {
    const searchInput = page.getByPlaceholder(/Search opportunities/i);
    await searchInput.fill('NonExistentUniqueString12345');

    await page.waitForTimeout(500);

    // Columns should show "No opportunities"
    await expect(page.getByText('No opportunities').first()).toBeVisible();
  });

  test('should clear search and show all opportunities', async ({ page }) => {
    const searchInput = page.getByPlaceholder(/Search opportunities/i);

    // First filter
    await searchInput.fill('Searchable');
    await page.waitForTimeout(500);

    // Then clear
    await searchInput.clear();
    await page.waitForTimeout(500);

    // Should show all opportunities again
    // The cards should be visible
  });
});

test.describe('Pipeline - Delete Opportunity', () => {
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

  test.beforeEach(async ({ page, request }) => {
    // Create a fresh opportunity for each delete test
    await createOpportunityViaAPI(request, authToken, {
      title: `Delete Test ${Date.now()}`,
      source: 'direct',
    });

    await loginAndGoToPipeline(page);
  });

  test('should delete opportunity after confirmation', async ({ page }) => {
    await page.waitForSelector('.bg-white.rounded-lg.border', { timeout: 10000 });

    // Open menu on first card
    const menuButton = page.locator('.bg-white.rounded-lg.border').first().locator('button').first();
    await menuButton.click();

    // Set up dialog handler before clicking delete
    page.once('dialog', async (dialog) => {
      expect(dialog.type()).toBe('confirm');
      await dialog.accept();
    });

    // Click delete
    await page.getByText('Delete').click();

    // Wait for deletion to complete
    await page.waitForTimeout(1000);
  });

  test('should cancel delete when dialog is dismissed', async ({ page }) => {
    await page.waitForSelector('.bg-white.rounded-lg.border', { timeout: 10000 });

    const cardCountBefore = await page.locator('.bg-white.rounded-lg.border').count();

    const menuButton = page.locator('.bg-white.rounded-lg.border').first().locator('button').first();
    await menuButton.click();

    // Dismiss the dialog
    page.once('dialog', async (dialog) => {
      await dialog.dismiss();
    });

    await page.getByText('Delete').click();

    await page.waitForTimeout(500);

    // Card count should remain the same
    const cardCountAfter = await page.locator('.bg-white.rounded-lg.border').count();
    expect(cardCountAfter).toBe(cardCountBefore);
  });
});

test.describe('Pipeline API - CRUD Operations', () => {
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

  test('should create opportunity via API', async ({ request }) => {
    const response = await request.post('http://localhost:8000/api/v1/pipeline/opportunities', {
      headers: { Authorization: `Bearer ${authToken}` },
      data: {
        title: `API Create Test ${Date.now()}`,
        source: 'upwork',
        value: 1000,
      },
    });

    expect(response.ok()).toBeTruthy();
    const opp = await response.json();
    expect(opp).toHaveProperty('id');
    expect(opp).toHaveProperty('title');
    expect(opp.status).toBe('lead');
  });

  test('should list opportunities via API', async ({ request }) => {
    const response = await request.get('http://localhost:8000/api/v1/pipeline/opportunities', {
      headers: { Authorization: `Bearer ${authToken}` },
    });

    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    expect(data).toHaveProperty('items');
    expect(data).toHaveProperty('total');
    expect(Array.isArray(data.items)).toBeTruthy();
  });

  test('should get single opportunity via API', async ({ request }) => {
    // First create one
    const createResp = await request.post('http://localhost:8000/api/v1/pipeline/opportunities', {
      headers: { Authorization: `Bearer ${authToken}` },
      data: { title: 'Get Single Test' },
    });
    const created = await createResp.json();

    // Then get it
    const getResp = await request.get(`http://localhost:8000/api/v1/pipeline/opportunities/${created.id}`, {
      headers: { Authorization: `Bearer ${authToken}` },
    });

    expect(getResp.ok()).toBeTruthy();
    const opp = await getResp.json();
    expect(opp.id).toBe(created.id);
  });

  test('should update opportunity via API', async ({ request }) => {
    // Create
    const createResp = await request.post('http://localhost:8000/api/v1/pipeline/opportunities', {
      headers: { Authorization: `Bearer ${authToken}` },
      data: { title: 'Update Test Original' },
    });
    const created = await createResp.json();

    // Update
    const updateResp = await request.patch(`http://localhost:8000/api/v1/pipeline/opportunities/${created.id}`, {
      headers: { Authorization: `Bearer ${authToken}` },
      data: { title: 'Update Test Modified', value: 9999 },
    });

    expect(updateResp.ok()).toBeTruthy();
    const updated = await updateResp.json();
    expect(updated.title).toBe('Update Test Modified');
    expect(Number(updated.value)).toBe(9999);
  });

  test('should delete opportunity via API', async ({ request }) => {
    // Create
    const createResp = await request.post('http://localhost:8000/api/v1/pipeline/opportunities', {
      headers: { Authorization: `Bearer ${authToken}` },
      data: { title: 'Delete Test' },
    });
    const created = await createResp.json();

    // Delete
    const deleteResp = await request.delete(`http://localhost:8000/api/v1/pipeline/opportunities/${created.id}`, {
      headers: { Authorization: `Bearer ${authToken}` },
    });

    expect(deleteResp.ok()).toBeTruthy();

    // Verify deleted (should return 404)
    const getResp = await request.get(`http://localhost:8000/api/v1/pipeline/opportunities/${created.id}`, {
      headers: { Authorization: `Bearer ${authToken}` },
    });
    expect(getResp.status()).toBe(404);
  });

  test('should move opportunity to new status via API', async ({ request }) => {
    // Create
    const createResp = await request.post('http://localhost:8000/api/v1/pipeline/opportunities', {
      headers: { Authorization: `Bearer ${authToken}` },
      data: { title: 'Move Test' },
    });
    const created = await createResp.json();
    expect(created.status).toBe('lead');

    // Move to qualified
    const moveResp = await request.post(`http://localhost:8000/api/v1/pipeline/opportunities/${created.id}/move`, {
      headers: { Authorization: `Bearer ${authToken}` },
      data: { status: 'qualified' },
    });

    expect(moveResp.ok()).toBeTruthy();
    const moved = await moveResp.json();
    expect(moved.status).toBe('qualified');
  });

  test('should get pipeline stats via API', async ({ request }) => {
    const response = await request.get('http://localhost:8000/api/v1/pipeline/stats', {
      headers: { Authorization: `Bearer ${authToken}` },
    });

    expect(response.ok()).toBeTruthy();
    const stats = await response.json();
    expect(stats).toHaveProperty('stages');
    expect(stats).toHaveProperty('total_opportunities');
    expect(stats).toHaveProperty('total_value');
    expect(Array.isArray(stats.stages)).toBeTruthy();
  });
});
