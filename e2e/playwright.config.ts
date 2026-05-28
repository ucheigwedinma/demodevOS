import { defineConfig, devices } from "@playwright/test";

const BASE_URL = process.env.UAT_BASE_URL ?? "http://localhost:5176";

export default defineConfig({
  testDir: ".",
  testMatch: ["**/*.spec.ts"],
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 2 : undefined,
  reporter: process.env.CI ? [["html"], ["github"]] : [["list"], ["html"]],
  globalSetup: "./global-setup.ts",
  use: {
    baseURL: BASE_URL,
    storageState: ".auth/storageState.json",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
    actionTimeout: 10_000,
    navigationTimeout: 15_000,
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
    // Add firefox / webkit projects once the chromium suite is stable.
  ],
});
