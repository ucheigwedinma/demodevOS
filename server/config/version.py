"""
Single source of truth for the developerOS server release.

Bumping process:
    1. Update VERSION + CODENAME here
    2. Update VERSION in client/src/lib/version.ts to match
    3. Update `version` in client/package.json to match
    4. Tag the commit `v<VERSION>` on git

Codenames are picked alphabetically, one per minor release.
"""

VERSION = "1.0.0"
CODENAME = "Eleanor"
RELEASE_DATE = "2026-05-08"


def version_info() -> dict[str, str]:
    """Structured version info for the /api/version/ endpoint."""
    return {
        "version": VERSION,
        "codename": CODENAME,
        "release_date": RELEASE_DATE,
    }
