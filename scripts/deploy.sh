#!/usr/bin/env bash
# ------------------------------------------------------------------------------
# developerOS — Deploy with health checks and rollback
#
# Usage:
#   bash scripts/deploy.sh                    # deploy all services
#   bash scripts/deploy.sh server client      # deploy specific services
#
# Expects to be run from the project root (~/developeros on VPS).
# Compose file: docker-compose.hostinger.yml
# ------------------------------------------------------------------------------
set -euo pipefail

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.hostinger.yml}"
HEALTH_TIMEOUT=120        # seconds to wait for health checks
HEALTH_INTERVAL=5         # seconds between health check polls
SERVICES=("server" "client" "console" "celery" "celery-beat" "db" "redis")

# If specific services passed as args, use those
if [[ $# -gt 0 ]]; then
  SERVICES=("$@")
fi

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log()  { echo -e "${GREEN}[deploy]${NC} $1"; }
warn() { echo -e "${YELLOW}[deploy]${NC} $1"; }
err()  { echo -e "${RED}[deploy]${NC} $1"; }

# ------------------------------------------------------------------------------
# 0. Pre-deploy dependency audit (warn only, don't block)
# ------------------------------------------------------------------------------
AUDIT_SCRIPT="$(dirname "$0")/audit-deps.sh"
if [[ -f "$AUDIT_SCRIPT" ]]; then
  log "Running dependency security audit..."
  if bash "$AUDIT_SCRIPT" --python 2>&1; then
    log "  Dependency audit passed."
  else
    warn "  Vulnerabilities detected — review after deploy."
  fi
fi

# ------------------------------------------------------------------------------
# 1. Snapshot current image tags for rollback
# ------------------------------------------------------------------------------
log "Saving current image tags for rollback..."

declare -A ROLLBACK_IMAGES
for svc in server client console celery celery-beat; do
  img=$(docker compose -f "$COMPOSE_FILE" images "$svc" --format json 2>/dev/null | python3 -c "
import sys, json
data = json.load(sys.stdin)
if isinstance(data, list) and len(data) > 0:
    print(data[0].get('Repository','') + ':' + data[0].get('Tag',''))
" 2>/dev/null || echo "")
  if [[ -n "$img" && "$img" != ":" ]]; then
    ROLLBACK_IMAGES[$svc]="$img"
    log "  $svc → $img"
  fi
done

# ------------------------------------------------------------------------------
# 2. Pre-deploy backup (quick pg_dump)
# ------------------------------------------------------------------------------
log "Running pre-deploy database backup..."
if docker compose -f "$COMPOSE_FILE" exec -T db pg_isready -U postgres > /dev/null 2>&1; then
  BACKUP_DIR="${HOME}/backups"
  mkdir -p "$BACKUP_DIR"
  BACKUP_FILE="$BACKUP_DIR/pre-deploy-$(date +%Y%m%d-%H%M%S).sql.gz"
  docker compose -f "$COMPOSE_FILE" exec -T db \
    pg_dump -U postgres developerOS | gzip > "$BACKUP_FILE"
  log "  Backup saved: $BACKUP_FILE ($(du -h "$BACKUP_FILE" | cut -f1))"
else
  warn "  Database not running, skipping pre-deploy backup"
fi

# ------------------------------------------------------------------------------
# 3. Pull new images
# ------------------------------------------------------------------------------
log "Pulling latest images..."
docker compose -f "$COMPOSE_FILE" pull

# ------------------------------------------------------------------------------
# 4. Rolling update — bring up new containers
# ------------------------------------------------------------------------------
log "Starting updated containers..."
docker compose -f "$COMPOSE_FILE" up -d --remove-orphans

# ------------------------------------------------------------------------------
# 4b. Run migrations & collect static files
# ------------------------------------------------------------------------------
log "Running database migrations..."
docker compose -f "$COMPOSE_FILE" exec -T server python manage.py migrate --noinput 2>&1 || warn "Migrations failed — check server logs"

log "Collecting static files..."
docker compose -f "$COMPOSE_FILE" exec -T server python manage.py collectstatic --noinput 2>&1 || warn "Collectstatic failed — check server logs"

# ------------------------------------------------------------------------------
# 5. Health checks
# ------------------------------------------------------------------------------
log "Running health checks (timeout: ${HEALTH_TIMEOUT}s)..."

check_health() {
  local svc="$1"
  local elapsed=0

  while [[ $elapsed -lt $HEALTH_TIMEOUT ]]; do
    local status
    status=$(docker compose -f "$COMPOSE_FILE" ps "$svc" --format json 2>/dev/null | python3 -c "
import sys, json
data = json.load(sys.stdin)
if isinstance(data, list):
    data = data[0] if data else {}
state = data.get('State', '')
health = data.get('Health', '')
if health:
    print(health)
elif state == 'running':
    print('running')
else:
    print(state)
" 2>/dev/null || echo "unknown")

    case "$status" in
      healthy|running)
        log "  $svc: ${GREEN}$status${NC}"
        return 0
        ;;
      unhealthy)
        err "  $svc: unhealthy"
        return 1
        ;;
      *)
        # Still starting up
        sleep "$HEALTH_INTERVAL"
        elapsed=$((elapsed + HEALTH_INTERVAL))
        ;;
    esac
  done

  err "  $svc: timed out after ${HEALTH_TIMEOUT}s"
  return 1
}

# Check the API health endpoint directly
check_api_health() {
  local elapsed=0
  while [[ $elapsed -lt $HEALTH_TIMEOUT ]]; do
    if curl -sf http://localhost:8000/api/health/ > /dev/null 2>&1; then
      log "  API /api/health/: ${GREEN}ok${NC}"
      return 0
    fi
    sleep "$HEALTH_INTERVAL"
    elapsed=$((elapsed + HEALTH_INTERVAL))
  done
  err "  API /api/health/: not responding after ${HEALTH_TIMEOUT}s"
  return 1
}

FAILED=0

# Check each container's Docker health status
for svc in "${SERVICES[@]}"; do
  if ! check_health "$svc"; then
    FAILED=1
  fi
done

# Also hit the API health endpoint
if ! check_api_health; then
  FAILED=1
fi

# ------------------------------------------------------------------------------
# 6. Rollback on failure
# ------------------------------------------------------------------------------
if [[ $FAILED -ne 0 ]]; then
  err "Health checks failed — rolling back!"

  # Show recent logs for debugging
  err "Recent server logs:"
  docker compose -f "$COMPOSE_FILE" logs --tail=30 server 2>/dev/null || true

  # Rollback to previous images
  if [[ ${#ROLLBACK_IMAGES[@]} -gt 0 ]]; then
    warn "Restoring previous images..."
    for svc in "${!ROLLBACK_IMAGES[@]}"; do
      warn "  Pulling $svc → ${ROLLBACK_IMAGES[$svc]}"
      docker pull "${ROLLBACK_IMAGES[$svc]}" 2>/dev/null || true
    done
    docker compose -f "$COMPOSE_FILE" up -d --remove-orphans
    warn "Rollback complete. Previous version restored."
  else
    err "No rollback images recorded — manual intervention required."
  fi

  exit 1
fi

# ------------------------------------------------------------------------------
# 7. Cleanup
# ------------------------------------------------------------------------------
log "Cleaning up old images..."
docker image prune -f > /dev/null 2>&1 || true

log "Deploy complete!"
docker compose -f "$COMPOSE_FILE" ps
