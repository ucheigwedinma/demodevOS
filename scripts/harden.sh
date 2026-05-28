#!/usr/bin/env bash
# ------------------------------------------------------------------------------
# developerOS — Production Server Hardening
#
# Run once on the VPS after initial setup to:
#   1. Configure UFW firewall (allow 80, 443, restricted SSH)
#   2. Harden SSH (key-only auth, no root login, rate limiting)
#   3. Install fail2ban for brute-force protection
#   4. Enable automatic security updates
#
# Usage:
#   bash scripts/harden.sh [--ssh-port 22] [--allow-ssh-from <ip>]
#
# Examples:
#   bash scripts/harden.sh                              # SSH from anywhere, rate-limited
#   bash scripts/harden.sh --allow-ssh-from 203.0.113.5 # SSH from one IP only
#   bash scripts/harden.sh --ssh-port 2222              # SSH on non-standard port
# ------------------------------------------------------------------------------
set -euo pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log()  { echo -e "${GREEN}[harden]${NC} $1"; }
warn() { echo -e "${YELLOW}[harden]${NC} $1"; }
err()  { echo -e "${RED}[harden]${NC} $1"; exit 1; }

# ── Parse arguments ──────────────────────────────────────────
SSH_PORT="22"
SSH_ALLOW_FROM=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --ssh-port)      SSH_PORT="$2"; shift 2 ;;
    --allow-ssh-from) SSH_ALLOW_FROM="$2"; shift 2 ;;
    *) err "Unknown argument: $1" ;;
  esac
done

# ── Require root ─────────────────────────────────────────────
if [[ $EUID -ne 0 ]]; then
  err "This script must be run as root."
fi

# ==============================================================================
# 1. FIREWALL (UFW)
# ==============================================================================
log "Configuring firewall (UFW)..."

apt-get install -y -qq ufw > /dev/null 2>&1

# Reset to clean state
ufw --force reset > /dev/null

# Default policies: deny all incoming, allow all outgoing
ufw default deny incoming > /dev/null
ufw default allow outgoing > /dev/null

# HTTP and HTTPS — open to the world
ufw allow 80/tcp > /dev/null
ufw allow 443/tcp > /dev/null

# SSH — restricted or rate-limited
if [[ -n "$SSH_ALLOW_FROM" ]]; then
  # Allow SSH only from specific IP(s)
  IFS=',' read -ra IPS <<< "$SSH_ALLOW_FROM"
  for ip in "${IPS[@]}"; do
    ip=$(echo "$ip" | xargs)  # trim whitespace
    ufw allow from "$ip" to any port "$SSH_PORT" proto tcp > /dev/null
    log "  SSH allowed from $ip on port $SSH_PORT"
  done
else
  # Allow SSH from anywhere but rate-limit (6 connections / 30 seconds per IP)
  ufw limit "$SSH_PORT/tcp" > /dev/null
  log "  SSH rate-limited on port $SSH_PORT (6 attempts / 30s)"
fi

# Enable firewall
ufw --force enable > /dev/null

log "Firewall active. Rules:"
ufw status numbered 2>/dev/null | while IFS= read -r line; do
  log "  $line"
done

# ==============================================================================
# 2. SSH HARDENING
# ==============================================================================
log "Hardening SSH configuration..."

SSHD_CONFIG="/etc/ssh/sshd_config"
SSHD_HARDENING="/etc/ssh/sshd_config.d/99-hardening.conf"

# Back up original
if [[ ! -f "${SSHD_CONFIG}.original" ]]; then
  cp "$SSHD_CONFIG" "${SSHD_CONFIG}.original"
  log "  Backed up original sshd_config"
fi

# Write hardening overrides as a drop-in config
cat > "$SSHD_HARDENING" << 'SSHEOF'
# developerOS — SSH hardening (managed by scripts/harden.sh)

# Disable password authentication — key-only access
PasswordAuthentication no
ChallengeResponseAuthentication no

# Disable root login (use a regular user + sudo)
PermitRootLogin no

# Limit authentication attempts per connection
MaxAuthTries 3

# Disconnect idle sessions after 5 minutes
ClientAliveInterval 300
ClientAliveCountMax 2

# Disable X11 forwarding and agent forwarding
X11Forwarding no
AllowAgentForwarding no

# Only allow SSH protocol 2
Protocol 2

# Log verbosely for audit trail
LogLevel VERBOSE
SSHEOF

# Set SSH port if non-standard
if [[ "$SSH_PORT" != "22" ]]; then
  echo "Port $SSH_PORT" >> "$SSHD_HARDENING"
  log "  SSH port set to $SSH_PORT"
fi

# Validate config before restarting
if sshd -t 2>/dev/null; then
  systemctl reload sshd 2>/dev/null || systemctl reload ssh 2>/dev/null
  log "  SSH configuration applied and reloaded"
else
  rm -f "$SSHD_HARDENING"
  warn "  SSH config validation failed — reverted changes"
  warn "  Check sshd_config manually: sshd -t"
fi

# ==============================================================================
# 3. FAIL2BAN (brute-force protection)
# ==============================================================================
log "Installing fail2ban..."

apt-get install -y -qq fail2ban > /dev/null 2>&1

# Configure jail for SSH
cat > /etc/fail2ban/jail.d/developeros.conf << JAILEOF
# developerOS — fail2ban configuration

[sshd]
enabled  = true
port     = $SSH_PORT
filter   = sshd
logpath  = /var/log/auth.log
maxretry = 5
findtime = 600
bantime  = 3600

# Repeat offenders get banned for 24 hours
[sshd-aggressive]
enabled  = true
port     = $SSH_PORT
filter   = sshd[mode=aggressive]
logpath  = /var/log/auth.log
maxretry = 3
findtime = 86400
bantime  = 86400
JAILEOF

systemctl enable fail2ban > /dev/null 2>&1
systemctl restart fail2ban > /dev/null 2>&1
log "  fail2ban active — 5 failed attempts = 1 hour ban, repeat = 24 hour ban"

# ==============================================================================
# 4. AUTOMATIC SECURITY UPDATES
# ==============================================================================
log "Configuring automatic security updates..."

apt-get install -y -qq unattended-upgrades > /dev/null 2>&1

cat > /etc/apt/apt.conf.d/20auto-upgrades << 'AUTOEOF'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
APT::Periodic::AutocleanInterval "7";
AUTOEOF

# Only apply security updates, not all updates
cat > /etc/apt/apt.conf.d/50unattended-upgrades << 'UPGRADEEOF'
Unattended-Upgrade::Allowed-Origins {
    "${distro_id}:${distro_codename}-security";
};
Unattended-Upgrade::AutoFixInterruptedDpkg "true";
Unattended-Upgrade::Remove-Unused-Dependencies "true";
Unattended-Upgrade::Automatic-Reboot "false";
UPGRADEEOF

systemctl enable unattended-upgrades > /dev/null 2>&1
log "  Automatic security updates enabled (security patches only, no auto-reboot)"

# ==============================================================================
# 5. KERNEL NETWORK HARDENING
# ==============================================================================
log "Applying kernel network hardening..."

SYSCTL_HARDENING="/etc/sysctl.d/99-hardening.conf"
cat > "$SYSCTL_HARDENING" << 'SYSCTLEOF'
# developerOS — kernel network hardening

# Prevent IP spoofing
net.ipv4.conf.all.rp_filter = 1
net.ipv4.conf.default.rp_filter = 1

# Ignore ICMP redirects (prevent MITM)
net.ipv4.conf.all.accept_redirects = 0
net.ipv4.conf.default.accept_redirects = 0
net.ipv4.conf.all.send_redirects = 0
net.ipv4.conf.default.send_redirects = 0

# Disable source routing
net.ipv4.conf.all.accept_source_route = 0
net.ipv4.conf.default.accept_source_route = 0

# SYN flood protection
net.ipv4.tcp_syncookies = 1
net.ipv4.tcp_max_syn_backlog = 2048
net.ipv4.tcp_synack_retries = 2

# Ignore ICMP broadcast requests
net.ipv4.icmp_echo_ignore_broadcasts = 1

# Log suspicious packets (spoofed, source-routed, redirects)
net.ipv4.conf.all.log_martians = 1
net.ipv4.conf.default.log_martians = 1

# Disable IPv6 if not used
net.ipv6.conf.all.disable_ipv6 = 1
net.ipv6.conf.default.disable_ipv6 = 1
SYSCTLEOF

sysctl --system > /dev/null 2>&1
log "  Kernel parameters applied"

# ==============================================================================
# SUMMARY
# ==============================================================================
echo ""
log "============================================"
log "  Server hardening complete!"
log "============================================"
echo ""
log "What was configured:"
log "  [1] UFW firewall — ports 80, 443 open; SSH on $SSH_PORT (restricted)"
log "  [2] SSH hardened  — key-only auth, no root login, max 3 attempts"
log "  [3] fail2ban     — 5 failed SSH = 1h ban, repeat offenders = 24h ban"
log "  [4] Auto-updates — security patches applied daily (no auto-reboot)"
log "  [5] Kernel       — SYN flood protection, IP spoofing prevention"
echo ""
warn "IMPORTANT: Before disconnecting, verify SSH access in a NEW terminal:"
warn "  ssh -p $SSH_PORT your-user@this-server"
warn ""
warn "If locked out, use your hosting provider's console/VNC access to fix."
echo ""
