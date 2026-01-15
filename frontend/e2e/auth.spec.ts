import { test, expect, type Page } from '@playwright/test';

/**
 * E2E tests for Authentication flows in NH Mission Control.
 * Tests login, register, and logout functionality.
 */

// Test user credentials
const TEST_USER = {
  email: `e2e-test-${Date.now()}@example.com`,
  password: 'TestPass123!',
  name: 'E2E Test User',
};

// Helper to clean up test user (API call)
async function deleteTestUser(email: string, request: any) {
  try {
    // Login as the user first to get a token
    const loginResp = await request.post('http://localhost:8000/api/v1/auth/login', {
      form: {
        username: email,
        password: TEST_USER.password,
      },
    });

    if (loginResp.ok()) {
      const tokens = await loginResp.json();
      // Delete the user
      await request.delete('http://localhost:8000/api/v1/auth/me', {
        headers: {
          Authorization: `Bearer ${tokens.access_token}`,
        },
      });
    }
  } catch (e) {
    // Ignore cleanup errors
  }
}

test.describe('Authentication - Registration', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/register');
    await page.waitForLoadState('networkidle');
  });

  test('should display registration form', async ({ page }) => {
    await expect(page.getByText('NH Mission Control')).toBeVisible();
    await expect(page.getByText('Create your account')).toBeVisible();
    await expect(page.getByTestId('register-form')).toBeVisible();
    await expect(page.getByTestId('name-input')).toBeVisible();
    await expect(page.getByTestId('email-input')).toBeVisible();
    await expect(page.getByTestId('password-input')).toBeVisible();
    await expect(page.getByTestId('confirm-password-input')).toBeVisible();
    await expect(page.getByTestId('submit-btn')).toBeVisible();
  });

  test('should show error when passwords do not match', async ({ page }) => {
    await page.getByTestId('name-input').fill('Test User');
    await page.getByTestId('email-input').fill('test@example.com');
    await page.getByTestId('password-input').fill('Password123!');
    await page.getByTestId('confirm-password-input').fill('DifferentPass123!');
    await page.getByTestId('submit-btn').click();

    await expect(page.getByText('Passwords do not match')).toBeVisible();
  });

  test('should show validation for weak password', async ({ page }) => {
    await page.getByTestId('name-input').fill('Test User');
    await page.getByTestId('email-input').fill('test@example.com');
    await page.getByTestId('password-input').fill('weak');
    await page.getByTestId('confirm-password-input').fill('weak');
    await page.getByTestId('submit-btn').click();

    // Browser validation should prevent submission (minLength=8)
    // Check that we're still on the register page
    await expect(page).toHaveURL(/\/register/);
  });

  test('should successfully register a new user', async ({ page, request }) => {
    const uniqueEmail = `e2e-reg-${Date.now()}@example.com`;

    await page.getByTestId('name-input').fill('Registration Test');
    await page.getByTestId('email-input').fill(uniqueEmail);
    await page.getByTestId('password-input').fill('SecurePass123!');
    await page.getByTestId('confirm-password-input').fill('SecurePass123!');
    await page.getByTestId('submit-btn').click();

    // Should redirect to dashboard after successful registration
    await expect(page).toHaveURL(/\/dashboard/, { timeout: 10000 });

    // Clean up - logout and delete the test user
    await page.goto('/login');
  });

  test('should have link to login page', async ({ page }) => {
    await expect(page.getByText('Already have an account?')).toBeVisible();
    await page.getByRole('link', { name: 'Sign in' }).click();
    await expect(page).toHaveURL(/\/login/);
  });
});

test.describe('Authentication - Login', () => {
  let registeredUser: typeof TEST_USER;

  test.beforeAll(async ({ request }) => {
    // Register a test user for login tests
    registeredUser = {
      ...TEST_USER,
      email: `e2e-login-${Date.now()}@example.com`,
    };

    await request.post('http://localhost:8000/api/v1/auth/register', {
      data: {
        email: registeredUser.email,
        password: registeredUser.password,
        name: registeredUser.name,
      },
    });
  });

  test.beforeEach(async ({ page }) => {
    // Clear any existing auth state
    await page.context().clearCookies();
    await page.goto('/login');
    await page.evaluate(() => localStorage.clear());
    await page.reload();
    await page.waitForLoadState('networkidle');
  });

  test('should display login form', async ({ page }) => {
    await expect(page.getByText('NH Mission Control')).toBeVisible();
    await expect(page.getByText('Sign in to your account')).toBeVisible();
    await expect(page.getByTestId('login-form')).toBeVisible();
    await expect(page.getByTestId('email-input')).toBeVisible();
    await expect(page.getByTestId('password-input')).toBeVisible();
    await expect(page.getByTestId('submit-btn')).toBeVisible();
  });

  test('should show error for invalid credentials', async ({ page }) => {
    await page.getByTestId('email-input').fill('wrong@example.com');
    await page.getByTestId('password-input').fill('wrongpassword');
    await page.getByTestId('submit-btn').click();

    // Should show error message
    await expect(page.getByText(/invalid|incorrect|failed/i)).toBeVisible({ timeout: 5000 });
    // Should stay on login page
    await expect(page).toHaveURL(/\/login/);
  });

  test('should successfully login with valid credentials', async ({ page }) => {
    await page.getByTestId('email-input').fill(registeredUser.email);
    await page.getByTestId('password-input').fill(registeredUser.password);
    await page.getByTestId('submit-btn').click();

    // Should redirect to dashboard
    await expect(page).toHaveURL(/\/dashboard/, { timeout: 10000 });

    // Should show user's name in the UI (welcome message)
    await expect(page.getByText(/Welcome back/i)).toBeVisible();
  });

  test('should persist login state after page refresh', async ({ page }) => {
    // Login first
    await page.getByTestId('email-input').fill(registeredUser.email);
    await page.getByTestId('password-input').fill(registeredUser.password);
    await page.getByTestId('submit-btn').click();
    await expect(page).toHaveURL(/\/dashboard/, { timeout: 10000 });

    // Refresh the page
    await page.reload();
    await page.waitForLoadState('networkidle');

    // Should still be on dashboard (not redirected to login)
    await expect(page).toHaveURL(/\/dashboard/);
  });

  test('should have link to registration page', async ({ page }) => {
    await expect(page.getByText("Don't have an account?")).toBeVisible();
    await page.getByRole('link', { name: 'Sign up' }).click();
    await expect(page).toHaveURL(/\/register/);
  });
});

test.describe('Authentication - Logout', () => {
  let testUser: typeof TEST_USER;

  test.beforeAll(async ({ request }) => {
    // Register a test user
    testUser = {
      ...TEST_USER,
      email: `e2e-logout-${Date.now()}@example.com`,
    };

    await request.post('http://localhost:8000/api/v1/auth/register', {
      data: {
        email: testUser.email,
        password: testUser.password,
        name: testUser.name,
      },
    });
  });

  test('should successfully logout user', async ({ page }) => {
    // Login first
    await page.goto('/login');
    await page.waitForLoadState('networkidle');
    await page.getByTestId('email-input').fill(testUser.email);
    await page.getByTestId('password-input').fill(testUser.password);
    await page.getByTestId('submit-btn').click();
    await expect(page).toHaveURL(/\/dashboard/, { timeout: 10000 });

    // Find and click logout button (typically in header/nav)
    const logoutButton = page.getByRole('button', { name: /logout|sign out/i });
    if (await logoutButton.isVisible()) {
      await logoutButton.click();
    } else {
      // Try clicking user menu first if logout is in dropdown
      const userMenu = page.locator('header').getByRole('button').last();
      await userMenu.click();
      await page.getByText(/logout|sign out/i).click();
    }

    // Should redirect to login page
    await expect(page).toHaveURL(/\/login/, { timeout: 10000 });
  });

  test('should clear auth tokens on logout', async ({ page }) => {
    // Login
    await page.goto('/login');
    await page.waitForLoadState('networkidle');
    await page.getByTestId('email-input').fill(testUser.email);
    await page.getByTestId('password-input').fill(testUser.password);
    await page.getByTestId('submit-btn').click();
    await expect(page).toHaveURL(/\/dashboard/, { timeout: 10000 });

    // Check tokens exist
    const tokensBefore = await page.evaluate(() => ({
      access: localStorage.getItem('nh-access-token'),
      refresh: localStorage.getItem('nh-refresh-token'),
    }));
    expect(tokensBefore.access).toBeTruthy();

    // Logout
    const logoutButton = page.getByRole('button', { name: /logout|sign out/i });
    if (await logoutButton.isVisible()) {
      await logoutButton.click();
    } else {
      const userMenu = page.locator('header').getByRole('button').last();
      await userMenu.click();
      await page.getByText(/logout|sign out/i).click();
    }

    await expect(page).toHaveURL(/\/login/, { timeout: 10000 });

    // Check tokens are cleared
    const tokensAfter = await page.evaluate(() => ({
      access: localStorage.getItem('nh-access-token'),
      refresh: localStorage.getItem('nh-refresh-token'),
    }));
    expect(tokensAfter.access).toBeNull();
    expect(tokensAfter.refresh).toBeNull();
  });
});

test.describe('Authentication - Protected Routes', () => {
  test('should redirect unauthenticated users to login', async ({ page }) => {
    // Clear any existing auth
    await page.context().clearCookies();
    await page.goto('/dashboard');
    await page.evaluate(() => localStorage.clear());

    // Try to access dashboard without login
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');

    // Should be redirected to login
    await expect(page).toHaveURL(/\/login/, { timeout: 10000 });
  });

  test('should redirect unauthenticated users from pipeline page', async ({ page }) => {
    await page.context().clearCookies();
    await page.goto('/pipeline');
    await page.evaluate(() => localStorage.clear());

    await page.goto('/pipeline');
    await page.waitForLoadState('networkidle');

    await expect(page).toHaveURL(/\/login/, { timeout: 10000 });
  });
});

test.describe('Authentication - API Integration', () => {
  test('backend auth endpoints should be accessible', async ({ request }) => {
    // Test health endpoint
    const healthResp = await request.get('http://localhost:8000/health');
    expect(healthResp.ok()).toBeTruthy();
  });

  test('should return 401 for protected endpoints without token', async ({ request }) => {
    const meResp = await request.get('http://localhost:8000/api/v1/auth/me');
    expect(meResp.status()).toBe(401);
  });

  test('should successfully register via API', async ({ request }) => {
    const uniqueEmail = `api-test-${Date.now()}@example.com`;

    const response = await request.post('http://localhost:8000/api/v1/auth/register', {
      data: {
        email: uniqueEmail,
        password: 'ApiTestPass123!',
        name: 'API Test User',
      },
    });

    expect(response.ok()).toBeTruthy();
    const user = await response.json();
    expect(user).toHaveProperty('id');
    expect(user).toHaveProperty('email', uniqueEmail);
  });

  test('should return tokens on successful login via API', async ({ request }) => {
    // First register
    const email = `api-login-${Date.now()}@example.com`;
    await request.post('http://localhost:8000/api/v1/auth/register', {
      data: {
        email,
        password: 'ApiTestPass123!',
        name: 'API Login Test',
      },
    });

    // Then login (OAuth2 form format)
    const loginResp = await request.post('http://localhost:8000/api/v1/auth/login', {
      form: {
        username: email,
        password: 'ApiTestPass123!',
      },
    });

    expect(loginResp.ok()).toBeTruthy();
    const tokens = await loginResp.json();
    expect(tokens).toHaveProperty('access_token');
    expect(tokens).toHaveProperty('refresh_token');
    expect(tokens).toHaveProperty('token_type', 'bearer');
  });

  test('should access protected endpoint with valid token', async ({ request }) => {
    // Register and login
    const email = `api-protected-${Date.now()}@example.com`;
    await request.post('http://localhost:8000/api/v1/auth/register', {
      data: {
        email,
        password: 'ApiTestPass123!',
        name: 'API Protected Test',
      },
    });

    const loginResp = await request.post('http://localhost:8000/api/v1/auth/login', {
      form: {
        username: email,
        password: 'ApiTestPass123!',
      },
    });
    const tokens = await loginResp.json();

    // Access protected /me endpoint
    const meResp = await request.get('http://localhost:8000/api/v1/auth/me', {
      headers: {
        Authorization: `Bearer ${tokens.access_token}`,
      },
    });

    expect(meResp.ok()).toBeTruthy();
    const user = await meResp.json();
    expect(user.email).toBe(email);
  });
});
