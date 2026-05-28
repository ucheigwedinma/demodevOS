/**
 * Single source of truth for the developerOS client release.
 *
 * Bumping process:
 *   1. Update VERSION + CODENAME here
 *   2. Update `version` in client/package.json to match VERSION
 *   3. Update server/config/version.py to match
 *   4. Tag the commit `v<VERSION>` on git
 *
 * Codenames are picked alphabetically, one per minor release.
 */

export const VERSION = "1.0.0";
export const CODENAME = "Eleanor";
export const RELEASE_DATE = "2026-05-08";

export interface VersionInfo {
  version: string;
  codename: string;
  releaseDate: string;
}

export const versionInfo: VersionInfo = {
  version: VERSION,
  codename: CODENAME,
  releaseDate: RELEASE_DATE,
};

/** Short label for footers / sidebars: "v1.0.0 · Eleanor" */
export function versionLabel(): string {
  return `v${VERSION} · ${CODENAME}`;
}
