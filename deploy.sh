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

echo "[3/3] Restarting Aegis-Quant background service..."
if systemctl is-active --quiet aegis-quant; then
    systemctl restart aegis-quant
    echo "✓ Service 'aegis-quant' restarted successfully!"
elif systemctl is-active --quiet quantum_trading; then
    systemctl restart quantum_trading
    echo "✓ Service 'quantum_trading' restarted successfully!"
elif systemctl is-active --quiet uvicorn; then
    systemctl restart uvicorn
    echo "✓ Service 'uvicorn' restarted successfully!"
else
    echo "Killing existing main.py processes..."
    pkill -f "python.*main.py" || true
    sleep 1
    nohup ./venv/bin/python3 main.py --mode run > server.log 2>&1 &
    echo "✓ Process restarted with nohup in background!"
fi

echo "=========================================="
echo " UPDATE COMPLETE — Dashboard is Live!     "
echo "=========================================="
