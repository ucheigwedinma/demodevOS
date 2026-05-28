#!/bin/bash
# ============================================================
# developerOS — Production Deploy Script
# Run from the repo root on your local machine
# Usage: bash deploy/deploy-production.sh
# ============================================================

set -euo pipefail

SERVER="root@187.124.113.7"
SSH_OPTS="-i $HOME/.ssh/developeros_vps"
APP_DIR="/opt/developerOS"
WEB_DIR="/var/www/developeros"
COMPOSE_FILE="docker-compose.hostinger.yml"
NGINX_CONF="deploy/nginx/production.conf"
export RSYNC_RSH="ssh $SSH_OPTS"

echo "============================================================"
echo "  Deploying developerOS to PRODUCTION"
echo "  Server: $SERVER"
echo "============================================================"
echo ""

# --- 1. Build frontends locally ---
echo "==> Building client..."
cd client
npm run build
cd ..

echo "==> Building console..."
cd console
npm run build
cd ..

# --- 2. Sync server code ---
echo "==> Syncing server to $SERVER:$APP_DIR..."
rsync -avz --delete \
    --exclude 'node_modules' \
    --exclude '.git' \
    --exclude '.env*' \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude 'client/node_modules' \
    --exclude 'client/.svelte-kit' \
    --exclude 'client/build' \
    --exclude 'console/node_modules' \
    --exclude 'console/.svelte-kit' \
    --exclude 'console/build' \
    --exclude 'secrets' \
    --exclude '.venv' \
    --exclude 'server/.venv' \
    ./ "$SERVER:$APP_DIR/"

# --- 3. Upload frontend builds ---
echo "==> Uploading client build..."
rsync -avz --delete client/build/ "$SERVER:$WEB_DIR/client/"

echo "==> Uploading console build..."
rsync -avz --delete console/build/ "$SERVER:$WEB_DIR/console/"

# --- 4. Nginx config ---
echo "==> Updating Nginx config..."
rsync -avz "$NGINX_CONF" "$SERVER:/tmp/developeros.conf"
ssh $SSH_OPTS $SERVER "\
    cp /tmp/developeros.conf /etc/nginx/sites-available/developeros && \
    ln -sf /etc/nginx/sites-available/developeros /etc/nginx/sites-enabled/developeros && \
    nginx -t && systemctl reload nginx"

# --- 5. Build and restart backend ---
echo "==> Building and starting containers..."
ssh $SSH_OPTS $SERVER "\
    cd $APP_DIR && \
    docker compose -f $COMPOSE_FILE up -d --build && \
    echo '==> Running migrations...' && \
    docker compose -f $COMPOSE_FILE exec server python manage.py migrate --noinput && \
    docker compose -f $COMPOSE_FILE exec server python manage.py collectstatic --noinput && \
    echo '==> Running seed commands...' && \
    docker compose -f $COMPOSE_FILE exec server python manage.py seed_platform_suite || true && \
    docker compose -f $COMPOSE_FILE exec server python manage.py seed_rbac || true && \
    docker compose -f $COMPOSE_FILE exec server python manage.py seed_status_badges || true && \
    docker compose -f $COMPOSE_FILE exec server python manage.py seed_master_data || true && \
    docker compose -f $COMPOSE_FILE exec server python manage.py seed_feature_flags || true && \
    docker compose -f $COMPOSE_FILE exec server python manage.py seed_project_templates || true && \
    docker compose -f $COMPOSE_FILE exec server python manage.py seed_demo_suite || true"

# --- 6. Health checks ---
echo "==> Waiting for services..."
sleep 5

echo "==> Running health checks..."
for URL in "https://api.developeros.pro/api/health/" "https://app.developeros.pro" "https://console.developeros.pro"; do
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$URL" 2>/dev/null || echo "000")
    if [ "$HTTP_CODE" = "200" ]; then
        echo "    OK  $URL"
    else
        echo "    WARN $URL (HTTP $HTTP_CODE — may still be starting)"
    fi
done

echo ""
echo "============================================================"
echo "  Deployment complete!"
echo "============================================================"
echo "  API:     https://api.developeros.pro"
echo "  App:     https://app.developeros.pro"
echo "  Console: https://console.developeros.pro"
echo "============================================================"
