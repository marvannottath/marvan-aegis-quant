#!/usr/bin/env bash
# ==============================================================================
# Setup Free Let's Encrypt SSL (HTTPS) on Hostinger VPS
# Enables WebAuthn / Touch ID / Face ID hardware biometrics support
# ==============================================================================
set -e

echo "🔒 [1/3] Installing Certbot for Nginx..."
apt-get update -y
apt-get install -y certbot python3-certbot-nginx

echo "🔒 [2/3] Generating Free Let's Encrypt SSL Certificate..."
certbot --nginx -d srv1799665.hstgr.cloud --register-unsafely-without-email --agree-tos --redirect --non-interactive

echo "🔒 [3/3] Reloading Nginx..."
systemctl reload nginx

echo "======================================================"
echo "🎉 SUCCESS: HTTPS is now ACTIVE!"
echo "🌐 You can now open: https://srv1799665.hstgr.cloud"
echo "🔐 WebAuthn Touch ID / Face ID is now fully enabled!"
echo "======================================================"
