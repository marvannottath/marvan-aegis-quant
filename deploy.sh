#!/bin/bash
echo "=========================================="
echo " Aegis-Quant Hostinger VPS Update Script  "
echo "=========================================="

APP_DIR="/var/www/quantum_trading_system"

if [ -d "$APP_DIR" ]; then
    cd "$APP_DIR" || exit 1
fi

echo "[1/3] Pulling latest code from GitHub main..."
git pull origin main

echo "[2/3] Checking python virtual environment..."
if [ -f "./venv/bin/python3" ]; then
    ./venv/bin/python3 -c "import dashboard.app; print('✓ Python imports verified')"
fi

echo "[3/3] Restarting Aegis-Quant background service on port 8888..."
if systemctl is-active --quiet marvan_quant || [ -f /etc/systemd/system/marvan_quant.service ]; then
    systemctl restart marvan_quant
    echo "✓ Systemd service 'marvan_quant' restarted successfully on PORT 8888!"
elif systemctl is-active --quiet aegis-quant; then
    systemctl restart aegis-quant
    echo "✓ Service 'aegis-quant' restarted successfully!"
elif systemctl is-active --quiet quantum_trading; then
    systemctl restart quantum_trading
    echo "✓ Service 'quantum_trading' restarted successfully!"
else
    echo "Killing existing python processes..."
    pkill -f "python.*main.py" || true
    sleep 1
    PORT=8888 nohup ./venv/bin/python3 main.py --mode run > server.log 2>&1 &
    echo "✓ Process restarted with nohup on PORT 8888!"
fi

echo "=========================================="
echo " UPDATE COMPLETE — Dashboard is Live!     "
echo "=========================================="
