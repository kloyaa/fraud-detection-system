import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

/**
 * Health check E2E tests — baseline connectivity and accessibility.
 *
 * @a11y tag: included in `pnpm test:a11y` accessibility-only run.
 * axe-core violations are CI failures (WCAG 2.1 AA is mandatory per @elena).
 */

test.describe("API health endpoint", () => {
  test("GET /api/health returns a healthy or degraded status", async ({
    request,
  }) => {
    const response = await request.get("/api/health");

    // 200 (healthy) or 503 (degraded — backend unreachable in CI) are both acceptable
    // What we verify is that the Next.js server itself is running
    expect([200, 503]).toContain(response.status());

    const body = (await response.json()) as {
      status: string;
      timestamp: string;
      version: string;
    };
    expect(body).toHaveProperty("status");
    expect(body).toHaveProperty("timestamp");
    expect(body).toHaveProperty("version");
  });
});

test.describe("Login page @a11y", () => {
  test("login page is accessible (WCAG 2.1 AA)", async ({ page }) => {
    await page.goto("/login");

    const accessibilityScanResults = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
      .analyze();

    expect(accessibilityScanResults.violations).toEqual([]);
  });

  test("login page loads without JS errors", async ({ page }) => {
    const errors: string[] = [];
    page.on("pageerror", (err) => errors.push(err.message));

    await page.goto("/login");
    await page.waitForLoadState("networkidle");

    expect(errors).toEqual([]);
  });
});
