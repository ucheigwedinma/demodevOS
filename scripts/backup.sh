#!/usr/bin/env bash
# ------------------------------------------------------------------------------
# developerOS — Automated database backup with retention
#
# Usage:
#   bash scripts/backup.sh              # local backup only
#   bash scripts/backup.sh --offsite    # local + upload to offsite (S3/B2)
#
# Cron example (daily at 3 AM):
#   0 3 * * * cd ~/developeros && bash scripts/backup.sh --offsite >> ~/backups/backup.log 2>&1
#
# Environment variables (for offsite upload):
#   BACKUP_S3_BUCKET    — s3://bucket-name/path  (AWS S3 or any S3-compatible)
#   BACKUP_B2_BUCKET    — b2://bucket-name/path  (Backblaze B2 via b2 CLI)
#
# Expects: docker compose with service "db" running PostgreSQL.
# Compose file: docker-compose.hostinger.yml
# ------------------------------------------------------------------------------
set -euo pipefail

COMPOSE_FILE="docker-compose.hostinger.yml"
BACKUP_DIR="${HOME}/backups"
RETENTION_DAYS=30          # keep local backups for 30 days
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
BACKUP_FILE="$BACKUP_DIR/developeros-${TIMESTAMP}.sql.gz"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log()  { echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] ${GREEN}[backup]${NC} $1"; }
warn() { echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] ${YELLOW}[backup]${NC} $1"; }
err()  { echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] ${RED}[backup]${NC} $1"; }

mkdir -p "$BACKUP_DIR"

# ------------------------------------------------------------------------------
# 1. Check database is running
# ------------------------------------------------------------------------------
if ! docker compose -f "$COMPOSE_FILE" exec -T db pg_isready -U postgres > /dev/null 2>&1; then
  err "Database is not running. Aborting backup."
  exit 1
fi

# ------------------------------------------------------------------------------
# 2. Dump database
# ------------------------------------------------------------------------------
log "Starting database backup..."
docker compose -f "$COMPOSE_FILE" exec -T db \
  pg_dump -U postgres --no-owner --no-acl developerOS | gzip > "$BACKUP_FILE"

FILESIZE=$(du -h "$BACKUP_FILE" | cut -f1)
log "Backup saved: $BACKUP_FILE ($FILESIZE)"

# ------------------------------------------------------------------------------
# 3. Verify backup integrity (quick check: can gunzip read it?)
# ------------------------------------------------------------------------------
if ! gzip -t "$BACKUP_FILE" 2>/dev/null; then
  err "Backup file is corrupted! Aborting."
  rm -f "$BACKUP_FILE"
  exit 1
fi
log "Backup integrity verified."

# ------------------------------------------------------------------------------
# 4. Offsite upload (if --offsite flag passed)
# ------------------------------------------------------------------------------
if [[ "${1:-}" == "--offsite" ]]; then
  UPLOADED=false

  # AWS S3 (or S3-compatible like DigitalOcean Spaces, MinIO)
  if [[ -n "${BACKUP_S3_BUCKET:-}" ]]; then
    log "Uploading to S3: $BACKUP_S3_BUCKET"
    if aws s3 cp "$BACKUP_FILE" "${BACKUP_S3_BUCKET}/$(basename "$BACKUP_FILE")" --quiet; then
      log "S3 upload complete."
      UPLOADED=true
    else
      err "S3 upload failed."
    fi
  fi

  # Backblaze B2
  if [[ -n "${BACKUP_B2_BUCKET:-}" ]]; then
    log "Uploading to Backblaze B2: $BACKUP_B2_BUCKET"
    if b2 upload-file "${BACKUP_B2_BUCKET}" "$BACKUP_FILE" "backups/$(basename "$BACKUP_FILE")" --quiet; then
      log "B2 upload complete."
      UPLOADED=true
    else
      err "B2 upload failed."
    fi
  fi

  if [[ "$UPLOADED" == false ]]; then
    warn "No offsite storage configured. Set BACKUP_S3_BUCKET or BACKUP_B2_BUCKET."
  fi
fi

# ------------------------------------------------------------------------------
# 5. Cleanup old backups (local retention)
# ------------------------------------------------------------------------------
DELETED=$(find "$BACKUP_DIR" -name "developeros-*.sql.gz" -mtime +${RETENTION_DAYS} -delete -print | wc -l)
if [[ "$DELETED" -gt 0 ]]; then
  log "Cleaned up $DELETED backup(s) older than ${RETENTION_DAYS} days."
fi

# ------------------------------------------------------------------------------
# 6. Summary
# ------------------------------------------------------------------------------
TOTAL=$(find "$BACKUP_DIR" -name "developeros-*.sql.gz" | wc -l)
TOTAL_SIZE=$(du -sh "$BACKUP_DIR" 2>/dev/null | cut -f1)
log "Done. $TOTAL backup(s) on disk ($TOTAL_SIZE total)."
