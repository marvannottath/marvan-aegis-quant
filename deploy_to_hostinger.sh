#!/bin/bash
# Marvan's Pool - Automated 1-Click Deployment Script to Hostinger VPS (187.127.189.139)

SERVER_IP="187.127.189.139"
SERVER_USER="root"
REMOTE_DIR="/var/www/quantum_trading_system"

echo "============================================================"
echo "   Deploying Marvan's Pool AI Quant Engine to Hostinger VPS"
echo "   Target Server IP: $SERVER_IP"
echo "============================================================"

# 1. Create Remote Directory on Hostinger VPS
ssh -o StrictHostKeyChecking=no $SERVER_USER@$SERVER_IP "mkdir -p $REMOTE_DIR"

# 2. Sync Code Files via rsync
rsync -avz --exclude='venv' --exclude='__pycache__' --exclude='.git' ./ $SERVER_USER@$SERVER_IP:$REMOTE_DIR/

# 3. Setup Remote Python Environment & Systemd Daemon Service
ssh $SERVER_USER@$SERVER_IP "bash -s" << 'EOF'
cd /var/www/quantum_trading_system
apt-get update && apt-get install -y python3-pip python3-venv nginx

if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

./venv/bin/pip install --upgrade pip
./venv/bin/pip install fastapi uvicorn requests jinja2 numpy pandas torch urllib3

cat << 'SERVICE' > /etc/systemd/system/marvan_quant.service
[Unit]
Description=Marvan Aegis-Quant AI Autonomous Trader
After=network.target

[Service]
User=root
WorkingDirectory=/var/www/quantum_trading_system
ExecStart=/var/www/quantum_trading_system/venv/bin/python main.py --mode run
Restart=always
RestartSec=5
Environment=PORT=8888

[Install]
WantedBy=multi-user.target
SERVICE

systemctl daemon-reload
systemctl enable marvan_quant
systemctl restart marvan_quant
EOF

echo "============================================================"
echo "   DEPLOYMENT SUCCESSFUL!"
echo "   Your Live Dashboard is now running 24/7 on Hostinger VPS:"
echo "   👉 http://187.127.189.139:8888"
echo "============================================================"
