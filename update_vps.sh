#!/usr/bin/env bash
# ==============================================================================
# Aegis-Quant Fast Production Update & Frontend Build
# Syncs latest git commit, compiles Next.js bundle, and restarts services.
# ==============================================================================
set -e

APP_DIR="/var/www/quantum_trading_system"
cd "$APP_DIR"

echo "======================================================"
echo "⚡ [1/3] Syncing latest code from GitHub main..."
echo "======================================================"
git fetch origin main
git reset --hard origin/main
echo "✓ Git HEAD is now at: $(git rev-parse --short HEAD)"

echo "======================================================"
echo "📦 [2/3] Compiling Next.js Production Frontend Build..."
echo "======================================================"
cd "$APP_DIR/frontend"
npm run build
echo "✓ Next.js build compiled successfully!"

echo "======================================================"
echo "🔄 [3/3] Restarting Backend & Frontend services..."
echo "======================================================"
systemctl restart marvan-pool aegis-frontend

echo ""
echo "Service Health Check:"
systemctl is-active --quiet marvan-pool && echo "  ✓ marvan-pool (FastAPI Backend :8888) is ACTIVE" || echo "  ✗ marvan-pool FAILED"
systemctl is-active --quiet aegis-frontend && echo "  ✓ aegis-frontend (Next.js UI :3000) is ACTIVE" || echo "  ✗ aegis-frontend FAILED"
echo ""
echo "======================================================"
echo "🎉 Update Complete! Fresh UI & Engine Live on VPS"
echo "======================================================"
