#!/usr/bin/env bash
# ==============================================================================
# MARVAN'S POOL - 24/7/365 HOSTINGER VPS AUTOMATED CLOUD DEPLOYMENT SCRIPT
# Server Hostname: srv1799665.hstgr.cloud | Server IPv4: 187.127.189.139
# Port: 8888 (Coexists alongside MG Clearance Hub on 80/443)
# ==============================================================================

set -e

VPS_HOST="187.127.189.139"
VPS_USER="root"
REMOTE_DIR="/var/www/quantum_trading_system"

echo "================================================================================"
echo "   🚀 Deploying Marvan Aegis-Quant AI Pool to Hostinger VPS (24/7/365)          "
echo "================================================================================"

echo "[1/4] Syncing codebase to Hostinger VPS (${VPS_HOST})..."
rsync -avz --exclude '.git' --exclude 'venv' --exclude '__pycache__' ./ ${VPS_USER}@${VPS_HOST}:${REMOTE_DIR}

echo "[2/4] Installing Python 3 dependencies on VPS..."
ssh ${VPS_USER}@${VPS_HOST} "bash -s" << 'EOF'
cd /var/www/quantum_trading_system
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt
EOF

echo "[3/4] Registering and enabling systemd 24/7 background daemon..."
ssh ${VPS_USER}@${VPS_HOST} "bash -s" << 'EOF'
cp /var/www/quantum_trading_system/scripts/marvan-pool.service /etc/systemd/system/marvan-pool.service
systemctl daemon-reload
systemctl enable marvan-pool.service
systemctl restart marvan-pool.service
EOF

echo "[4/4] Verifying live daemon health check on port 8888..."
sleep 3
ssh ${VPS_USER}@${VPS_HOST} "systemctl status marvan-pool.service --no-pager"

echo "================================================================================"
echo "   ✅ DEPLOYMENT COMPLETE! Marvan's Pool is running 24/7/365 on Cloud VPS!      "
echo "   🌐 Trader Terminal:  http://${VPS_HOST}:8888/                               "
echo "   🔐 Super Admin SIEM: http://${VPS_HOST}:8888/admin                          "
echo "================================================================================"
