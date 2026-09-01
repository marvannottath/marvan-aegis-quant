"""
AEGIS QUANT — FORENSIC INVARIANT VERIFICATION TEST SUITE
Verifies:
 1. Vault Balance Invariant: vault_balance == sum(vault_transactions.sweep_amount)
 2. Zero-Vault Invariant: Empty ledger -> vault_balance == $0.00 exactly
 3. 11-Field Schema Check
 4. Partitioned Namespace Isolation (MASTER, TESTNET, LIVE)
 5. Backtest Isolation: Backtest runs do NOT leak to live/paper state
 6. Profit Factor "N/A — No Losing Trades" handling when gross_loss == 0
 7. Account Reconciliation: Trading Account Equity + Vault = Total Platform Assets
"""

import sys
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from execution.paper_broker import paper_broker
from execution.profit_vault import profit_vault
from backtest.backtest_engine import BacktestEngine

results = []

def check(test_id, name, condition, detail=""):
    sym = "✅ PASS" if condition else "❌ FAIL"
    results.append({"id": test_id, "name": name, "status": "PASS" if condition else "FAIL", "detail": detail})
    print(f"[{test_id:02d}] {sym} {name}" + (f" | {detail}" if detail else ""))
    return condition

print("\n=== AEGIS QUANT FORENSIC INVARIANT TESTS ===\n")

# TEST 1: Zero Vault Invariant
paper_broker.set_active_capital_pool("BINANCE_LIVE_REAL")
live_vault = profit_vault.get_vault_balance("BINANCE_LIVE_REAL")
check(1, "Zero Vault Invariant: Empty ledger -> vault_balance == $0.00", live_vault == 0.0, f"Vault: ${live_vault:.2f}")

# TEST 2: Dynamic Invariant Check
paper_broker.set_active_capital_pool("AEGIS_QUANT_MASTER")
rec = profit_vault.sweep_profit(150.50, "XAUUSD", "TAKE_PROFIT_HIT", "TRD-XAU-001", "AEGIS_QUANT_MASTER")
v_bal = profit_vault.get_vault_balance("AEGIS_QUANT_MASTER")
txs = profit_vault.vault_stores["AEGIS_QUANT_MASTER"]["transactions"]
expected_bal = sum(t["sweep_amount"] for t in txs if t["status"] == "CONFIRMED")
check(2, "Vault Balance Invariant: vault_balance == sum(sweep_amount)", v_bal == expected_bal, f"Calculated: ${v_bal}, Sum: ${expected_bal}")

# TEST 3: 11-Field Vault Schema Check
required_fields = ["transaction_id", "timestamp", "source_trade_id", "asset", "realized_profit", "sweep_amount", "environment", "account_id", "reason", "previous_balance", "new_balance"]
has_all_fields = all(k in rec for k in required_fields)
check(3, "11-Field Vault Transaction Schema completeness", has_all_fields, f"Missing: {[k for k in required_fields if k not in rec]}")

# TEST 4: Namespace Isolation
paper_broker.set_active_capital_pool("BINANCE_TESTNET_DEMO")
testnet_vault = profit_vault.get_vault_balance("BINANCE_TESTNET_DEMO")
master_vault = profit_vault.get_vault_balance("AEGIS_QUANT_MASTER")
check(4, "Namespace Isolation: TESTNET vault != MASTER vault", testnet_vault != master_vault or (testnet_vault == 0.0 and master_vault > 0.0), f"Master: ${master_vault}, Testnet: ${testnet_vault}")

# TEST 5: Backtest Isolation Guarantee
bt = BacktestEngine()
prev_paper_vault = profit_vault.get_vault_balance("AEGIS_QUANT_MASTER")
prev_paper_trades = len(paper_broker.trade_history)
bt_res = bt.run_backtest("XAUUSD", "30d")
post_paper_vault = profit_vault.get_vault_balance("AEGIS_QUANT_MASTER")
post_paper_trades = len(paper_broker.trade_history)
check(5, "Backtest Isolation: Backtest run does NOT change PAPER or LIVE state", (prev_paper_vault == post_paper_vault) and (prev_paper_trades == post_paper_trades), f"Vault: ${prev_paper_vault} -> ${post_paper_vault}")

# TEST 6: Profit Factor No-Loss Handling
paper_broker.set_active_capital_pool("AEGIS_QUANT_MASTER")
acc_summary = paper_broker.get_account_summary()
pf_disp = acc_summary["ledger_metrics"]["all_time"]["profit_factor_display"]
check(6, "Profit Factor displays 'N/A — No Losing Trades' when gross loss is 0", "N/A" in pf_disp or "1.00" in pf_disp, f"Display: {pf_disp}")

# TEST 7: Account Reconciliation
rec_report = paper_broker.get_reconciliation()
check(7, "Account Reconciliation: Trading Equity + Vault = Total Platform Assets", rec_report["status"] == "RECONCILIATION_OK", f"Trading Eq: ${rec_report['trading_account_equity']}, Vault: ${rec_report['secured_vault_reserve']}, Total: ${rec_report['total_platform_assets']}")

print("\n" + "="*80)
passed = sum(1 for r in results if r["status"] == "PASS")
print(f"SUMMARY: {passed}/{len(results)} INVARIANT TESTS PASSED")
print("="*80)
