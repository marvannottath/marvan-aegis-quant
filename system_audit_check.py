"""
Deep System-Wide Audit Script for Marvan's Aegis-Quant Trading System.
Checks all modules, data structures, persistence files, risk rules, and API consistency.
"""

import sys
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

results = []

def audit_log(section, status, detail):
    results.append({"section": section, "status": status, "detail": detail})
    print(f"[{status}] {section}: {detail}")

print("=== STARTING FULL SYSTEM-WIDE AUDIT ===")

# 1. Audit Persistence Files
vault_file = PROJECT_ROOT / "execution" / "profit_vault_state.json"
broker_file = PROJECT_ROOT / "execution" / "paper_broker_state.json"

if vault_file.exists():
    try:
        with open(vault_file, "r") as f:
            v_data = json.load(f)
            bal = v_data.get("vault_balance", 0)
            sweeps = v_data.get("total_sweeps_count", 0)
            audit_log("Profit Vault State", "PASS", f"Vault file intact. Balance: ${bal:,.2f}, Sweeps Count: {sweeps}")
    except Exception as e:
        audit_log("Profit Vault State", "FAIL", f"Error reading vault JSON: {e}")
else:
    audit_log("Profit Vault State", "WARN", "profit_vault_state.json file does not exist yet.")

if broker_file.exists():
    try:
        with open(broker_file, "r") as f:
            b_data = json.load(f)
            cash = b_data.get("virtual_cash", 0)
            equity = b_data.get("equity", 0)
            pos_count = len(b_data.get("positions", {}))
            audit_log("Paper Broker State", "PASS", f"Broker file intact. Virtual Cash: ${cash:,.2f}, Equity: ${equity:,.2f}, Open Positions: {pos_count}")
    except Exception as e:
        audit_log("Paper Broker State", "FAIL", f"Error reading paper broker JSON: {e}")
else:
    audit_log("Paper Broker State", "WARN", "paper_broker_state.json file does not exist yet.")

# 2. Audit Core Python Modules Importability
try:
    from execution.paper_broker import PaperBroker
    from execution.profit_vault import profit_vault, ProfitVault
    from core.risk_engine import RiskEngine
    from core.autonomous_trader import AutonomousTrader
    from core.multi_market_scanner import multi_scanner
    from sync.daily_sync import daily_sync
    from execution.binance_broker import binance_broker
    audit_log("Core Python Imports", "PASS", "All core execution, risk, sync, and broker modules imported successfully.")
except Exception as e:
    audit_log("Core Python Imports", "FAIL", f"Module import error: {e}")

# 3. Audit Risk Engine Rules
try:
    re = RiskEngine()
    prof = re.get_profile_summary()
    audit_log("Risk Engine Rules", "PASS", f"Active profile: {prof['active_profile']} ({prof['default_leverage']}x lev), Max Cap: ${prof['max_trade_cap_usd']:,.2f}")
except Exception as e:
    audit_log("Risk Engine Rules", "FAIL", f"Risk Engine error: {e}")

# 4. Audit Account Summary Data Consistency
try:
    pb = PaperBroker()
    summary = pb.get_account_summary()
    req_keys = ["virtual_cash", "portfolio_equity", "initial_capital", "total_pnl_usd", "total_pnl_pct", "profit_vault", "open_positions_count", "open_positions"]
    missing = [k for k in req_keys if k not in summary]
    if not missing:
        audit_log("Account Summary Schema", "PASS", f"All required keys present in account summary. Open positions: {summary['open_positions_count']}")
    else:
        audit_log("Account Summary Schema", "FAIL", f"Missing keys in account summary: {missing}")
except Exception as e:
    audit_log("Account Summary Schema", "FAIL", f"Account summary error: {e}")

# 5. Audit Open Position Field Completeness
try:
    pb = PaperBroker()
    summary = pb.get_account_summary()
    pos_list = summary["open_positions"]
    if len(pos_list) > 0:
        p0 = pos_list[0]
        pos_keys = ["asset", "action", "entry_price", "capital_allocated", "leverage", "live_price", "unrealized_pnl_usd", "unrealized_pnl_pct"]
        missing_p = [k for k in pos_keys if k not in p0]
        if not missing_p:
            audit_log("Position Schema Integrity", "PASS", f"All required position fields present (live_price, unrealized_pnl_usd, etc.). Sample asset: {p0['asset']}")
        else:
            audit_log("Position Schema Integrity", "FAIL", f"Missing position keys: {missing_p}")
    else:
        audit_log("Position Schema Integrity", "INFO", "No active open positions to validate schema.")
except Exception as e:
    audit_log("Position Schema Integrity", "FAIL", f"Position schema error: {e}")

print("=== AUDIT SUMMARY RESULT ===")
fail_count = sum(1 for r in results if r["status"] == "FAIL")
if fail_count == 0:
    print("ALL CORE SYSTEM CHECKS PASSED SUCCESSFULLY (0 FAILS)!")
else:
    print(f"ATTENTION: {fail_count} CHECKS FAILED.")
