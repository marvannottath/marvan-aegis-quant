#!/usr/bin/env bash
# ==============================================================================
# Marvan Aegis-Quant: Automated Hostinger VPS Deployment Script
# Target: https://srv1799665.hstgr.cloud/ (IP: 187.127.189.139)
# Deploys Next.js (port 3000) + FastAPI Backend (port 8888) with Nginx Proxy
# ==============================================================================

set -e

APP_DIR="/var/www/quantum_trading_system"
FRONTEND_DIR="$APP_DIR/frontend"

echo "===================================================================="
echo "🚀 Starting Full Deployment on Hostinger VPS (srv1799665.hstgr.cloud)"
echo "===================================================================="

# Step 1: Ensure directory and pull latest code from GitHub
if [ ! -d "$APP_DIR" ]; then
    echo "Creating directory $APP_DIR..."
    mkdir -p "$APP_DIR"
    git clone https://github.com/marvannottath/marvan-aegis-quant.git "$APP_DIR"
fi

cd "$APP_DIR"
echo "[1/6] Fetching and syncing latest code from GitHub main..."
git fetch origin main
git reset --hard origin/main
echo "✓ Git HEAD is now at: $(git rev-parse --short HEAD)"

# Step 2: Setup / Update Python Virtual Environment for FastAPI Backend
echo "[2/6] Updating Python backend dependencies..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt

# Step 3: Ensure Node.js (>= 18) and npm are installed
echo "[3/6] Verifying Node.js & npm runtime..."
if ! command -v node >/dev/null 2>&1 || [ "$(node -v | cut -d'.' -f1 | tr -d 'v')" -lt 18 ]; then
    echo "Installing Node.js 20 LTS..."
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
    apt-get install -y nodejs build-essential
fi
echo "✓ Node.js version: $(node -v), npm version: $(npm -v)"

# Step 4: Build Next.js Production Application
echo "[4/6] Installing Next.js dependencies and building production bundle..."
cd "$FRONTEND_DIR"
npm install --legacy-peer-deps
npm run build
echo "✓ Next.js build completed successfully!"

# Step 5: Configure and start systemd services
echo "[5/6] Registering Systemd services for Backend & Frontend..."

# 5a. Backend Service (port 8888)
cat << 'EOF' > /etc/systemd/system/marvan-pool.service
[Unit]
Description=Marvan Aegis-Quant AI Autonomous Trading Backend
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/var/www/quantum_trading_system
ExecStart=/var/www/quantum_trading_system/venv/bin/python main.py --mode run
Restart=always
RestartSec=3
Environment=PORT=8888
Environment=PYTHONUNBUFFERED=1
Environment=LIVE_TRADING_ENABLED=false
Environment=LIVE_WITHDRAWALS_ENABLED=false
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
EOF

# 5b. Frontend Next.js Service (port 3000)
cat << 'EOF' > /etc/systemd/system/aegis-frontend.service
[Unit]
Description=Marvan Aegis-Quant Next.js Production UI
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/var/www/quantum_trading_system/frontend
ExecStart=/usr/bin/npm run start -- -p 3000
Restart=always
RestartSec=3
Environment=NODE_ENV=production
Environment=PORT=3000
Environment=BACKEND_URL=http://127.0.0.1:8888

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable marvan-pool.service
systemctl restart marvan-pool.service
echo "✓ marvan-pool.service (FastAPI port 8888) restarted."

systemctl enable aegis-frontend.service
systemctl restart aegis-frontend.service
echo "✓ aegis-frontend.service (Next.js port 3000) restarted."

# Step 6: Configure Nginx to reverse proxy Next.js (port 3000) and API (port 8888)
echo "[6/6] Updating Nginx reverse proxy configuration across all ports (80 & 443 SSL)..."

# Run authoritative Python patcher to update all active Nginx files (including SSL 443)
cd "$APP_DIR"
python3 scripts/patch_nginx_config.py

echo "===================================================================="
echo "🎉 DEPLOYMENT COMPLETE!"
echo "   Next.js UI is now LIVE on: https://srv1799665.hstgr.cloud/"
echo "   Super Admin Portal:        https://srv1799665.hstgr.cloud/admin"
echo "   Profile & 2FA Center:      https://srv1799665.hstgr.cloud/profile"
echo "   Backend API Gateway:       http://127.0.0.1:8888/api/health"
echo "===================================================================="
