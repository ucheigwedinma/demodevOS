#!/bin/bash
# ============================================================
# developerOS Server Setup Script
# Run ONCE on a fresh Ubuntu 22.04+ VPS
#
# Usage (production):
#   ssh root@<IP> 'bash -s' < deploy/setup-server.sh production
#
# Usage (staging):
#   ssh root@<IP> 'bash -s' < deploy/setup-server.sh staging
# ============================================================

set -euo pipefail

ENV="${1:-production}"

if [ "$ENV" = "production" ]; then
    DOMAIN_API="api.developeros.pro"
    DOMAIN_APP="app.developeros.pro"
    DOMAIN_CONSOLE="console.developeros.pro"
elif [ "$ENV" = "staging" ]; then
    DOMAIN_API="api-staging.developeros.pro"
    DOMAIN_APP="staging.developeros.pro"
    DOMAIN_CONSOLE="console-staging.developeros.pro"
else
    echo "Usage: $0 [production|staging]"
    exit 1
fi

EMAIL="admin@developeros.pro"
APP_DIR="/opt/developerOS"

echo "==> Setting up developerOS ($ENV) server..."
echo "    API:     $DOMAIN_API"
echo "    App:     $DOMAIN_APP"
echo "    Console: $DOMAIN_CONSOLE"
echo ""

# --- System packages ---
echo "==> Updating system..."
apt-get update && apt-get upgrade -y

echo "==> Installing prerequisites..."
apt-get install -y \
    ca-certificates curl gnupg lsb-release \
    nginx certbot python3-certbot-nginx \
    git ufw fail2ban

# --- Docker ---
echo "==> Installing Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
    systemctl start docker
fi

if ! docker compose version &> /dev/null; then
    apt-get install -y docker-compose-plugin
fi

# --- Firewall ---
echo "==> Configuring firewall..."
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow 80/tcp
ufw allow 443/tcp
echo "y" | ufw enable

# --- Directories ---
echo "==> Creating directories..."
mkdir -p $APP_DIR
mkdir -p $APP_DIR/secrets
mkdir -p /var/www/developeros/client
mkdir -p /var/www/developeros/console
mkdir -p /var/www/certbot

# --- Nginx temp config for Certbot ---
echo "==> Setting up Nginx for SSL provisioning..."
cat > /etc/nginx/sites-available/developeros-temp <<NGINX_TEMP
server {
    listen 80;
    server_name $DOMAIN_API $DOMAIN_APP $DOMAIN_CONSOLE;

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        return 200 'developerOS - Setting up SSL...';
        add_header Content-Type text/plain;
    }
}
NGINX_TEMP

ln -sf /etc/nginx/sites-available/developeros-temp /etc/nginx/sites-enabled/developeros-temp
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

# --- SSL Certificates ---
echo "==> Obtaining SSL certificates..."
for DOMAIN in $DOMAIN_API $DOMAIN_APP $DOMAIN_CONSOLE; do
    if [ ! -d "/etc/letsencrypt/live/$DOMAIN" ]; then
        certbot certonly --webroot -w /var/www/certbot \
            -d "$DOMAIN" \
            --non-interactive --agree-tos --email "$EMAIL"
    else
        echo "    Certificate for $DOMAIN already exists, skipping."
    fi
done

# --- Switch to production nginx ---
echo "==> Cleaning up temp nginx config..."
rm -f /etc/nginx/sites-enabled/developeros-temp
rm -f /etc/nginx/sites-available/developeros-temp

# Certbot auto-renewal
echo "0 0,12 * * * root certbot renew --quiet --post-hook 'systemctl reload nginx'" > /etc/cron.d/certbot-renew

# --- Create deploy user ---
echo "==> Creating deploy user..."
if ! id "deploy" &>/dev/null; then
    useradd -m -s /bin/bash -G docker deploy
    mkdir -p /home/deploy/.ssh
    cp /root/.ssh/authorized_keys /home/deploy/.ssh/ 2>/dev/null || true
    chown -R deploy:deploy /home/deploy/.ssh
    chmod 700 /home/deploy/.ssh
fi
chown -R deploy:deploy $APP_DIR
chown -R deploy:deploy /var/www/developeros

echo ""
echo "============================================================"
echo "  Server setup complete! ($ENV)"
echo "============================================================"
echo ""
echo "  Next steps:"
echo "  1. Create secrets:"
echo "     echo 'your-secret-key' > $APP_DIR/secrets/django_secret_key"
echo "     echo 'your-db-password' > $APP_DIR/secrets/db_password"
echo "  2. Create $APP_DIR/.env.$ENV with app settings"
echo "  3. Run: bash deploy/deploy-$ENV.sh"
echo ""
echo "============================================================"
