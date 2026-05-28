import { execSync } from "node:child_process";
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";

const REPO_ROOT = resolve(__dirname, "..");
const CREDS_PATH = resolve(REPO_ROOT, "e2e/.auth/credentials.json");
const STORAGE_PATH = resolve(REPO_ROOT, "e2e/.auth/storageState.json");
const BASE_URL = process.env.UAT_BASE_URL ?? "http://localhost:5176";

const SEED_CMD =
  process.env.UAT_SEED_CMD ??
  `cd "${resolve(REPO_ROOT, "server")}" && .venv/bin/python manage.py seed_test_org --output "${CREDS_PATH}"`;

async function ensureBackendReachable(baseUrl: string) {
  const url = `${baseUrl}/api/health/`;
  try {
    const res = await fetch(url, { method: "GET" });
    if (!res.ok && res.status >= 500) {
      throw new Error(`backend returned ${res.status}`);
    }
  } catch (err) {
    console.warn(
      `[uat] Skipping reachability check for ${url}: ${(err as Error).message}. ` +
        `(Make sure 'make dev' is running.)`,
    );
  }
}

export default async function globalSetup() {
  mkdirSync(dirname(CREDS_PATH), { recursive: true });

  console.log("[uat] Seeding test org + minting JWT...");
  execSync(SEED_CMD, { cwd: REPO_ROOT, stdio: "inherit" });

  const creds = JSON.parse(readFileSync(CREDS_PATH, "utf-8")) as {
    access_token: string;
    refresh_token: string;
  };

  const origin = new URL(BASE_URL).origin;
  const storageState = {
    cookies: [],
    origins: [
      {
        origin,
        localStorage: [
          { name: "access_token", value: creds.access_token },
          { name: "refresh_token", value: creds.refresh_token },
        ],
      },
    ],
  };

  writeFileSync(STORAGE_PATH, JSON.stringify(storageState, null, 2));
  console.log(`[uat] Wrote authed storage state -> ${STORAGE_PATH}`);

  await ensureBackendReachable(BASE_URL);
}
