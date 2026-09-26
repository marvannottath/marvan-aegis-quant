#!/bin/bash
echo "=========================================="
echo " Aegis-Quant Hostinger VPS Update Script  "
echo "=========================================="

APP_DIR="/var/www/quantum_trading_system"

if [ -d "$APP_DIR" ]; then
    cd "$APP_DIR" || exit 1
else
    echo "ERROR: Directory $APP_DIR not found!"
    exit 1
fi

echo "[1/4] Pulling latest code from GitHub main..."
git fetch origin main
git reset --hard origin/main
echo "Git HEAD is now: $(git rev-parse --short HEAD)"

echo "[2/4] Clearing cache and state files..."
rm -f execution/profit_vault_state.json

echo "[3/4] Restarting Aegis-Quant background service..."
pkill -9 -f "python.*main.py" 2>/dev/null || true
sleep 1

RESTARTED=0
if systemctl is-active --quiet marvan-pool || [ -f /etc/systemd/system/marvan-pool.service ]; then
    systemctl restart marvan-pool
    echo "✓ Systemd service 'marvan-pool' restarted successfully!"
    RESTARTED=1
fi
if systemctl is-active --quiet marvan_quant || [ -f /etc/systemd/system/marvan_quant.service ]; then
    systemctl restart marvan_quant
    echo "✓ Systemd service 'marvan_quant' restarted successfully!"
    RESTARTED=1
fi
if [ $RESTARTED -eq 0 ]; then
    echo "Starting process via nohup on PORT 8888..."
    PORT=8888 nohup ./venv/bin/python main.py --mode run > server.log 2>&1 &
    echo "✓ Process started with nohup on PORT 8888!"
fi

echo "[4/4] Running live Binance Broker verification..."
./venv/bin/python -c "
from execution.binance_broker import binance_broker
acc = binance_broker.get_account_info('BINANCE_LIVE', force_refresh=True)
fut = binance_broker.get_futures_account_summary('BINANCE_LIVE')
pos = binance_broker.get_open_positions('BINANCE_LIVE')
print('----------------------------------------')
print('LIVE DIAGNOSTIC REPORT:')
print('Total Equity          :', acc.get('total_equity'))
print('Total Available Bal   :', acc.get('available_balance'))
print('Futures Wallet Balance:', fut.get('total_wallet_balance'))
print('Futures Available Bal :', fut.get('available_balance'))
print('Futures API Status    :', getattr(binance_broker, '_last_futures_status', 200))
print('Futures API Error     :', getattr(binance_broker, '_last_futures_error', 'NONE'))
print('Active Open Positions :', len(pos), [p.get('symbol') for p in pos])
print('----------------------------------------')
"

echo "=========================================="
echo " UPDATE COMPLETE — Dashboard is Live!     "
echo "=========================================="
