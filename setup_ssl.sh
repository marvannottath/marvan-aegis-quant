#!/usr/bin/env bash
# ==============================================================================
# Setup Free Let's Encrypt SSL (HTTPS) on Hostinger VPS
# Enables WebAuthn / Touch ID / Face ID hardware biometrics support
# ==============================================================================
set -e

echo "🔒 [1/4] Resolving Python OpenSSL & Cryptography dependencies..."
# Fix Ubuntu 24.04 / Debian pyOpenSSL vs cryptography mismatch
python3 -m pip install --break-system-packages --upgrade pyOpenSSL cryptography 2>/dev/null || true

# If system certbot still fails due to conflicting distro packages, install isolated certbot
if ! certbot --version >/dev/null 2>&1; then
    echo "⚙️ Setting up isolated Certbot environment..."
    apt-get update -y
    apt-get install -y python3-venv python3-pip libaugeas-dev
    python3 -m venv /opt/certbot/
    /opt/certbot/bin/pip install --upgrade pip
    /opt/certbot/bin/pip install certbot certbot-nginx
    ln -sf /opt/certbot/bin/certbot /usr/bin/certbot
fi

echo "🔒 [2/4] Testing Certbot..."
certbot --version

echo "🔒 [3/4] Generating Free Let's Encrypt SSL Certificate..."
certbot --nginx -d srv1799665.hstgr.cloud --register-unsafely-without-email --agree-tos --redirect --non-interactive

echo "🔒 [4/4] Reloading Nginx..."
systemctl reload nginx

echo "======================================================"
echo "🎉 SUCCESS: HTTPS is now ACTIVE!"
echo "🌐 You can now open: https://srv1799665.hstgr.cloud"
echo "🔐 WebAuthn Touch ID / Face ID is now fully enabled!"
echo "======================================================"

