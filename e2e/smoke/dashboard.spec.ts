import { expect, test } from "@playwright/test";

test.describe("smoke: authed shell", () => {
  test("root loads without redirecting to /login", async ({ page }) => {
    const responses: number[] = [];
    page.on("response", (res) => {
      if (res.url().includes("/api/")) responses.push(res.status());
    });

    await page.goto("/");
    await page.waitForLoadState("networkidle");

    expect(page.url()).not.toContain("/login");

    const unauthorized = responses.filter((s) => s === 401 || s === 403);
    expect(
      unauthorized,
      `Expected no auth failures from /api. Got statuses: ${responses.join(", ")}`,
    ).toHaveLength(0);
  });

  test("projects route renders", async ({ page }) => {
    await page.goto("/projects");
    await page.waitForLoadState("networkidle");
    expect(page.url()).not.toContain("/login");
    await expect(page.locator("body")).toBeVisible();
  });
});
