#!/usr/bin/env bash
# ==============================================================================
# Hostinger VPS Performance Optimization & Zombie Process Purge
# ==============================================================================

set -e

echo "===================================================================="
echo "⚡ Starting Hostinger VPS Lag Cleanup & Memory Optimization"
echo "===================================================================="

APP_DIR="/var/www/quantum_trading_system"

cd "$APP_DIR"

# 1. Terminate orphaned / rogue Python processes not managed by systemd
echo "[1/5] Purging orphaned / zombie Python and Node processes..."
systemctl stop marvan-pool aegis-frontend 2>/dev/null || true
sleep 1

# Kill any lingering unmanaged background loops
pkill -9 -f "uvicorn dashboard.app" 2>/dev/null || true
pkill -9 -f "python main.py" 2>/dev/null || true
pkill -9 -f "next-server" 2>/dev/null || true

# 2. Clear old build cache and temporary logs
echo "[2/5] Cleaning disk cache and temporary files..."
rm -rf "$APP_DIR/frontend/.next/cache" 2>/dev/null || true
rm -rf /tmp/pip-* /tmp/*.tmp 2>/dev/null || true

# 3. Pull latest code and re-patch Nginx
echo "[3/5] Syncing latest Git code and applying high-speed Nginx cache..."
git fetch origin main
git reset --hard origin/main

python3 scripts/patch_nginx_config.py

# 4. Build Next.js Production Bundle
echo "[4/5] Building optimized Next.js production bundle..."
cd "$APP_DIR/frontend"
npm install --legacy-peer-deps
npm run build

# 5. Restart services with clean memory footprint
echo "[5/5] Starting optimized background services..."
systemctl daemon-reload
systemctl restart marvan-pool
systemctl restart aegis-frontend
systemctl reload nginx

# Drop Linux kernel pagecache to maximize free RAM
sync
if [ -w /proc/sys/vm/drop_caches ]; then
    echo 3 > /proc/sys/vm/drop_caches 2>/dev/null || true
fi

echo "===================================================================="
echo "✅ OPTIMIZATION COMPLETE!"
echo "Current Server Memory & Uptime:"
free -h
uptime
echo "===================================================================="
