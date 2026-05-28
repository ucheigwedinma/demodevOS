#!/usr/bin/env bash
# ============================================================
#  developerOS — Hostinger VPS deploy script
#  Usage:  ssh root@<vps-ip> 'bash -s' < deploy.sh
#  Or:     scp deploy.sh root@<vps-ip>: && ssh root@<vps-ip> bash deploy.sh
# ============================================================
set -euo pipefail

DOMAIN="app.developeros.pro"
REPO_URL="git@github.com:YOUR_ORG/developerOS.git"   # ← update this
APP_DIR="/opt/developerOS"
BRANCH="main"

# ── Colors ───────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

# ── 1. System packages ──────────────────────────────────────
info "Updating system packages..."
apt-get update -qq
apt-get install -y -qq git curl ufw

# ── 2. Docker (if missing) ──────────────────────────────────
if ! command -v docker &>/dev/null; then
  info "Installing Docker..."
  curl -fsSL https://get.docker.com | sh
  systemctl enable --now docker
else
  info "Docker already installed: $(docker --version)"
fi

# Docker Compose plugin (v2)
if ! docker compose version &>/dev/null; then
  info "Installing Docker Compose plugin..."
  apt-get install -y -qq docker-compose-plugin
else
  info "Docker Compose already installed: $(docker compose version)"
fi

# ── 3. Firewall ─────────────────────────────────────────────
info "Configuring firewall..."
ufw --force reset >/dev/null
ufw default deny incoming
ufw default allow outgoing
ufw limit ssh/tcp          # rate-limit SSH: 6 connections / 30s per IP
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable
info "Firewall active (SSH rate-limited). For full hardening run: bash scripts/harden.sh"

# ── 4. Clone / pull repo ────────────────────────────────────
if [ -d "$APP_DIR/.git" ]; then
  info "Pulling latest code..."
  cd "$APP_DIR"
  git fetch origin
  git reset --hard "origin/$BRANCH"
else
  info "Cloning repository..."
  git clone -b "$BRANCH" "$REPO_URL" "$APP_DIR"
  cd "$APP_DIR"
fi

# ── 5. Check .env.prod exists ───────────────────────────────
if [ ! -f server/.env.prod ]; then
  error "server/.env.prod not found. Copy server/.env.prod.example and fill in real values."
fi

# Symlink so docker-compose can interpolate variables (e.g. POSTGRES_PASSWORD)
ln -sf server/.env.prod .env

# ── 6. Generate DB password if still placeholder ────────────
if grep -q "CHANGE-ME-strong-password" server/.env.prod; then
  DB_PASS=$(openssl rand -base64 32 | tr -d '/+=' | head -c 40)
  info "Generating secure database password..."
  sed -i "s/CHANGE-ME-strong-password/$DB_PASS/g" server/.env.prod
  warn "DB password set. It's stored in server/.env.prod — keep this file safe."
fi

# ── 7. Build client SPA ─────────────────────────────────────
info "Building client SPA..."
if command -v node &>/dev/null && [ "$(node -v | cut -d. -f1 | tr -d v)" -ge 20 ]; then
  cd "$APP_DIR/client"
  npm ci --silent
  npm run build
  cd "$APP_DIR"
else
  # Build inside a temporary Docker container
  info "Node not found on host — building in Docker..."
  docker run --rm \
    -v "$APP_DIR/client:/app" \
    -w /app \
    node:22-alpine \
    sh -c "npm ci --silent && npm run build"
fi

# ── 8. SSL certificates ─────────────────────────────────────
SSL_DIR="$APP_DIR/nginx/ssl"
mkdir -p "$SSL_DIR"

if [ ! -f "$SSL_DIR/fullchain.pem" ]; then
  info "Generating temporary self-signed certificate (for initial startup)..."
  openssl req -x509 -nodes -days 7 \
    -newkey rsa:2048 \
    -keyout "$SSL_DIR/privkey.pem" \
    -out    "$SSL_DIR/fullchain.pem" \
    -subj   "/CN=$DOMAIN" 2>/dev/null
  warn "Self-signed cert created. Run certbot after first startup (see below)."
fi

# ── 9. Start services ───────────────────────────────────────
info "Starting Docker services..."
cd "$APP_DIR"
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

# Wait for the server to be healthy
info "Waiting for server to become healthy..."
for i in $(seq 1 30); do
  if docker compose -f docker-compose.yml -f docker-compose.prod.yml ps server | grep -q "healthy"; then
    break
  fi
  sleep 2
done

# ── 10. Run migrations ──────────────────────────────────────
info "Running Django migrations..."
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec -T server \
  python manage.py migrate --noinput

# ── 11. Create superuser (if none exists) ────────────────────
info "Checking for superuser..."
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec -T server \
  python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(is_superuser=True).exists():
    print('No superuser found. Create one with:')
    print('  docker compose -f docker-compose.yml -f docker-compose.prod.yml exec server python manage.py createsuperuser')
else:
    print('Superuser already exists.')
"

# ── 12. Certbot (Let's Encrypt) ─────────────────────────────
info ""
info "============================================"
info "  Services are running!"
info "============================================"
info ""
info "Next steps:"
info ""
info "1. Point DNS: $DOMAIN → $(curl -s ifconfig.me || echo '<this-server-ip>')"
info ""
info "2. Once DNS propagates, get a real SSL certificate:"
info "   docker run --rm -v ${APP_DIR}/nginx/ssl:/etc/letsencrypt/live/$DOMAIN \\"
info "     -v ${APP_DIR}/certbot-webroot:/var/www/certbot \\"
info "     certbot/certbot certonly --webroot \\"
info "     -w /var/www/certbot -d $DOMAIN --agree-tos -m your@email.com"
info ""
info "   Then restart nginx:"
info "   docker compose -f docker-compose.yml -f docker-compose.prod.yml restart nginx"
info ""
info "3. Create a superuser (if not already done):"
info "   docker compose -f docker-compose.yml -f docker-compose.prod.yml exec server python manage.py createsuperuser"
info ""
info "4. Seed demo data (optional):"
info "   docker compose -f docker-compose.yml -f docker-compose.prod.yml exec server python manage.py seed_support_desk"
info "   docker compose -f docker-compose.yml -f docker-compose.prod.yml exec server python manage.py seed_knowledge_base"
info ""
