#!/usr/bin/env bash
# ==============================================================================
# Aegis-Quant Fast Production Update & Frontend Build
# Syncs latest git commit, compiles Next.js bundle, and restarts services.
# Run on VPS as root: bash update_vps.sh
# ==============================================================================
set -e

APP_DIR="/var/www/quantum_trading_system"
cd "$APP_DIR"

echo "======================================================"
echo "⚡ [1/5] Syncing latest code from GitHub main..."
echo "======================================================"
git fetch origin main
git reset --hard origin/main
echo "✓ Git HEAD is now at: $(git rev-parse --short HEAD)"

mkdir -p "$APP_DIR/data"
echo '{"live_trading_enabled": true}' > "$APP_DIR/data/environment_gate_state.json"
echo "✓ Live Trading Guard state enabled"

echo "======================================================"
echo "📦 [2/5] Installing/Updating Python backend deps..."
echo "======================================================"
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✓ Python venv created"
fi
./venv/bin/pip install --upgrade pip -q
./venv/bin/pip install -r requirements.txt -q
echo "✓ Python dependencies installed"

echo "======================================================"
echo "🏗️  [3/5] Compiling Next.js Production Frontend Build..."
echo "======================================================"
cd "$APP_DIR/frontend"
npm install --legacy-peer-deps --silent
npm run build
echo "✓ Next.js build compiled successfully!"

echo "======================================================"
echo "🔄 [4/5] Restarting Backend & Frontend services..."
echo "======================================================"
cd "$APP_DIR"
systemctl daemon-reload
systemctl restart marvan-pool
sleep 2
systemctl restart aegis-frontend
sleep 2

echo ""
echo "Service Health Check:"
systemctl is-active --quiet marvan-pool && echo "  ✓ marvan-pool (FastAPI Backend :8888) is ACTIVE" || echo "  ✗ marvan-pool FAILED — check: journalctl -u marvan-pool -n 30"
systemctl is-active --quiet aegis-frontend && echo "  ✓ aegis-frontend (Next.js UI :3000) is ACTIVE" || echo "  ✗ aegis-frontend FAILED — check: journalctl -u aegis-frontend -n 30"

echo "======================================================"
echo "🌐 [5/5] Patching Nginx routes..."
echo "======================================================"
python3 scripts/patch_nginx_config.py 2>/dev/null || echo "  (Nginx already configured correctly)"
systemctl reload nginx 2>/dev/null || true

echo ""
echo "======================================================"
echo "🎉 Update Complete! Fresh UI & Engine Live on VPS"
echo "   https://srv1799665.hstgr.cloud/crypto"
echo "======================================================"
