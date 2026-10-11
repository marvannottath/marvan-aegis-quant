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

# 1. Terminate orphaned / rogue Python and Node processes
echo "[1/5] Purging orphaned / zombie Python and Node processes..."
systemctl stop marvan-pool aegis-frontend 2>/dev/null || true
pm2 stop all 2>/dev/null || true
sleep 1

# Kill any lingering unmanaged background loops and free port 3000 & 8888
fuser -k 3000/tcp 2>/dev/null || true
fuser -k 8888/tcp 2>/dev/null || true
pkill -9 -f "uvicorn dashboard.app" 2>/dev/null || true
pkill -9 -f "python main.py" 2>/dev/null || true
pkill -9 -f "next" 2>/dev/null || true

# 2. Clear entire old build directory, caches, and temporary logs
echo "[2/5] Cleaning disk cache and purging stale build artifacts..."
rm -rf "$APP_DIR/frontend/.next" 2>/dev/null || true
rm -rf /tmp/pip-* /tmp/*.tmp 2>/dev/null || true

# 3. Pull latest code and re-patch Nginx
echo "[3/5] Syncing latest Git code and applying high-speed Nginx cache..."
git fetch origin main
git reset --hard origin/main

python3 scripts/patch_nginx_config.py

# 4. Build Next.js Production Bundle cleanly
echo "[4/5] Building optimized Next.js production bundle..."
cd "$APP_DIR/frontend"
rm -rf .next
npm install --legacy-peer-deps
npm run build

# 5. Restart services with clean memory footprint
echo "[5/5] Starting optimized background services..."
systemctl daemon-reload
systemctl restart marvan-pool 2>/dev/null || true
systemctl restart aegis-frontend 2>/dev/null || true
pm2 restart all 2>/dev/null || true
systemctl reload nginx 2>/dev/null || true

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
