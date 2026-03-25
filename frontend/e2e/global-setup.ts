import { expect, test as setup } from "@playwright/test";

/**
 * Global setup — verifies the app is reachable before running the test suite.
 * Runs once before all test projects.
 */
setup("verify app is reachable", async ({ page }) => {
  const response = await page.goto("/api/health");
  expect(response?.status()).toBeLessThan(500);
});
