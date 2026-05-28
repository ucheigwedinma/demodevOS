#!/usr/bin/env bash
# ------------------------------------------------------------------------------
# developerOS — VPS setup script
#
# Run once on the VPS to:
#   1. Set up the project directory structure
#   2. Install the daily backup cron job
#   3. Verify Docker and docker compose are available
#
# Usage:
#   bash scripts/setup-vps.sh
# ------------------------------------------------------------------------------
set -euo pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log()  { echo -e "${GREEN}[setup]${NC} $1"; }
warn() { echo -e "${YELLOW}[setup]${NC} $1"; }
err()  { echo -e "${RED}[setup]${NC} $1"; }

PROJECT_DIR="${HOME}/developeros"

# ------------------------------------------------------------------------------
# 1. Check prerequisites
# ------------------------------------------------------------------------------
log "Checking prerequisites..."

if ! command -v docker &> /dev/null; then
  err "Docker is not installed. Install Docker first."
  exit 1
fi
log "  Docker: $(docker --version | head -1)"

if ! docker compose version &> /dev/null; then
  err "Docker Compose plugin is not installed."
  exit 1
fi
log "  Compose: $(docker compose version | head -1)"

# ------------------------------------------------------------------------------
# 2. Create directories
# ------------------------------------------------------------------------------
log "Creating directories..."
mkdir -p "$PROJECT_DIR/scripts"
mkdir -p "${HOME}/backups"
log "  $PROJECT_DIR"
log "  ${HOME}/backups"

# ------------------------------------------------------------------------------
# 3. Install backup cron job (daily at 3 AM)
# ------------------------------------------------------------------------------
CRON_CMD="0 3 * * * cd ${PROJECT_DIR} && bash scripts/backup.sh --offsite >> ${HOME}/backups/backup.log 2>&1"

if crontab -l 2>/dev/null | grep -qF "scripts/backup.sh"; then
  warn "Backup cron job already exists. Skipping."
else
  log "Installing daily backup cron job (3 AM)..."
  (crontab -l 2>/dev/null || true; echo "$CRON_CMD") | crontab -
  log "  Cron job installed."
fi

log "Current crontab:"
crontab -l 2>/dev/null | while read -r line; do
  log "  $line"
done

# ------------------------------------------------------------------------------
# 4. Create npm_shared network if it doesn't exist
# ------------------------------------------------------------------------------
if ! docker network inspect npm_shared &> /dev/null; then
  log "Creating npm_shared Docker network..."
  docker network create npm_shared
else
  log "npm_shared network already exists."
fi

# ------------------------------------------------------------------------------
# 5. Summary
# ------------------------------------------------------------------------------
echo ""
log "Setup complete! Next steps:"
log "  1. Copy .env file to ${PROJECT_DIR}/.env"
log "  2. Copy docker-compose.hostinger.yml to ${PROJECT_DIR}/"
log "  3. Copy scripts/ directory to ${PROJECT_DIR}/scripts/"
log "  4. Login to GHCR: echo \$GHCR_PAT | docker login ghcr.io -u ucheigwedinma --password-stdin"
log "  5. Deploy: cd ${PROJECT_DIR} && bash scripts/deploy.sh"
echo ""
log "For offsite backups, set these in your .env or export them:"
log "  export BACKUP_S3_BUCKET=s3://your-bucket/developeros-backups"
log "  export BACKUP_B2_BUCKET=your-b2-bucket-name"
