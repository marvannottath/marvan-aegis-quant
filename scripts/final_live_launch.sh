#!/usr/bin/env bash
# ==============================================================================
# AEGIS QUANT — ONE-COMMAND FINAL LIVE ACTIVATION & VERIFICATION PIPELINE
# Server: srv1799665.hstgr.cloud | IPv4: 187.127.189.139 | Port: 8888
# ==============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(dirname "$SCRIPT_DIR")"
cd "$APP_DIR"

echo "================================================================================"
echo "  🚀 STARTING AEGIS QUANT FINAL LIVE LAUNCH SEQUENCE"
echo "  Working Directory: $APP_DIR"
echo "  Timestamp: $(date '+%Y-%m-%d %H:%M:%S IST')"
echo "================================================================================"

# Use virtualenv python if available
if [ -f "./venv/bin/python3" ]; then
    PYTHON_BIN="./venv/bin/python3"
else
    PYTHON_BIN="python3"
fi

# Execute 20-step verification engine
$PYTHON_BIN core/final_live_pipeline.py

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "================================================================================"
    echo "  ✅ FINAL LAUNCH SEQUENCE COMPLETED WITH PASSING SAFETY GATES"
    echo "================================================================================"
else
    echo "================================================================================"
    echo "  ⚠️  LAUNCH PIPELINE STOPPED AT SAFE BOUNDARY — CHECK GATES ABOVE"
    echo "================================================================================"
fi

exit $EXIT_CODE
