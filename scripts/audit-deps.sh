#!/usr/bin/env bash
# ------------------------------------------------------------------------------
# developerOS — Dependency Security Audit
#
# Scans Python and Node.js dependencies for known vulnerabilities.
# Run before every deploy and periodically (e.g., weekly cron).
#
# Usage:
#   bash scripts/audit-deps.sh            # audit both Python + Node
#   bash scripts/audit-deps.sh --python   # Python only
#   bash scripts/audit-deps.sh --node     # Node only
#
# Exit codes:
#   0  — no vulnerabilities found
#   1  — vulnerabilities detected (details printed)
# ------------------------------------------------------------------------------
set -euo pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log()  { echo -e "${GREEN}[audit]${NC} $1"; }
warn() { echo -e "${YELLOW}[audit]${NC} $1"; }
err()  { echo -e "${RED}[audit]${NC} $1"; }

# Resolve project root (works from any subdirectory)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

RUN_PYTHON=true
RUN_NODE=true
EXIT_CODE=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --python) RUN_NODE=false; shift ;;
    --node)   RUN_PYTHON=false; shift ;;
    *)        err "Unknown argument: $1"; exit 1 ;;
  esac
done

# ==============================================================================
# Python — pip-audit
# ==============================================================================
if $RUN_PYTHON; then
  log "Auditing Python dependencies..."

  if ! command -v pip-audit &> /dev/null; then
    warn "pip-audit not installed. Installing..."
    pip install pip-audit --quiet
  fi

  if pip-audit -r "$PROJECT_DIR/server/requirements.txt" 2>&1; then
    log "  Python: no known vulnerabilities"
  else
    err "  Python: vulnerabilities found (see above)"
    EXIT_CODE=1
  fi
  echo ""
fi

# ==============================================================================
# Node.js — npm audit
# ==============================================================================
if $RUN_NODE; then
  log "Auditing Node.js dependencies..."

  if [ -d "$PROJECT_DIR/client/node_modules" ]; then
    # --omit=dev: only audit production dependencies
    if cd "$PROJECT_DIR/client" && npm audit --omit=dev 2>&1; then
      log "  Node.js: no known vulnerabilities"
    else
      err "  Node.js: vulnerabilities found (see above)"
      EXIT_CODE=1
    fi
  else
    warn "  client/node_modules not found — run npm install first"
  fi
  echo ""
fi

# ==============================================================================
# Summary
# ==============================================================================
if [ $EXIT_CODE -eq 0 ]; then
  log "All dependency audits passed."
else
  err "Vulnerabilities detected — review and update before deploying."
fi

exit $EXIT_CODE
