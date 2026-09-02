#!/usr/bin/env python3
"""
AEGIS-QUANT — Complete Money Flow Architecture Test Suite.
Tests all 21 subsystems: environment gates, payment providers, wallet,
ledger, order lifecycle, withdrawal locks, reconciliation, persistence.
"""

import sys
import json
import time
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PASS = "PASS"
FAIL = "FAIL"
UNVERIFIED = "UNVERIFIED"

results = []

def test(name, condition, detail=""):
    status = PASS if condition else FAIL
    results.append({"name": name, "status": status, "detail": detail})
    marker = "✅" if status == PASS else "❌"
    print(f"  {marker} [{status}] {name}" + (f" — {detail}" if detail else ""))


print("=" * 75)
print("AEGIS-QUANT — MONEY FLOW ARCHITECTURE TEST SUITE")
print("=" * 75)

# ==========================================================================
# 1. ENVIRONMENT GATE
# ==========================================================================
print("\n[1. ENVIRONMENT GATE]")
from core.environment_gate import environment_gate, EnvironmentGate

allowed, msg = environment_gate.check_order_allowed("PAPER", market_data_age_seconds=0.1)
test("PAPER order allowed with fresh data", allowed, msg)

allowed, msg = environment_gate.check_order_allowed("LIVE", market_data_age_seconds=0.1)
test("LIVE order blocked (LIVE_TRADING_ENABLED=false)", not allowed, msg)

allowed, msg = environment_gate.check_order_allowed("PAPER", market_data_age_seconds=10.0)
test("Stale data (10s) blocks PAPER order", not allowed, msg)

allowed, msg = environment_gate.check_withdrawal_allowed("PAPER")
test("Withdrawals locked by default", not allowed, msg)

allowed, msg = environment_gate.check_order_allowed("INVALID_ENV")
test("Invalid environment rejected", not allowed, msg)

status = environment_gate.get_environment_status()
test("Environment status returns all keys", all(k in status for k in [
    "paper_trading", "live_trading", "live_withdrawals", "kill_switch_active"
]), str(list(status.keys())))

# ==========================================================================
# 2. MARKET DATA WATCHDOG
# ==========================================================================
print("\n[2. MARKET DATA WATCHDOG]")
from core.market_data_watchdog import market_data_watchdog, STATUS_LIVE, STATUS_DISCONNECTED

s = market_data_watchdog.get_status("NEVER_SEEN_SYMBOL_XYZ")
test("Unknown symbol is DISCONNECTED", s == STATUS_DISCONNECTED, s)

market_data_watchdog.record_tick("BTCUSD", 79050.0)
s = market_data_watchdog.get_status("BTCUSD")
test("Fresh tick → LIVE status", s == STATUS_LIVE, s)

result = market_data_watchdog.record_tick("BTCUSD", -1.0)
test("Negative price flagged INVALID", result["integrity"] == "FAIL", str(result["violations"]))

result = market_data_watchdog.record_tick("ETHUSD", 0.0)
test("Zero price flagged INVALID", result["integrity"] == "FAIL", str(result["violations"]))

for ms in [1.0, 2.0, 3.0, 4.0, 5.0]:
    market_data_watchdog.record_latency(ms)
pcts = market_data_watchdog.get_latency_percentiles()
test("Latency percentiles computed", pcts["p50"] > 0, str(pcts))

# ==========================================================================
# 3. ORDER STATE MACHINE
# ==========================================================================
print("\n[3. ORDER STATE MACHINE]")
from core.order_state_machine import order_state_machine, OrderStateMachineError

order = order_state_machine.create_order("BTCUSD", "BUY", 0.01, "MARKET", "PAPER")
oid = order["order_id"]
test("Order created in CREATED state", order["status"] == "CREATED", oid)

order_state_machine.transition(oid, "RISK_PENDING")
order_state_machine.transition(oid, "APPROVED")
order_state_machine.transition(oid, "SUBMITTED")
order_state_machine.transition(oid, "ACKNOWLEDGED")
exec_rec = {"fill_price": 79050.0, "environment": "PAPER"}
order_state_machine.transition(oid, "FILLED", execution_record=exec_rec, fill_qty=0.01, avg_fill_price=79050.0)
order = order_state_machine.get_order(oid)
test("Order reached FILLED with exec_record", order["status"] == "FILLED" and order["execution_record"] is not None)

try:
    order_state_machine.transition(oid, "APPROVED")
    test("Terminal state re-transition blocked", False)
except OrderStateMachineError as e:
    test("Terminal state re-transition blocked", True, str(e)[:60])

# FILLED without exec record blocked
order2 = order_state_machine.create_order("ETHUSD", "SELL", 0.1, "MARKET", "PAPER")
oid2 = order2["order_id"]
for st in ["RISK_PENDING", "APPROVED", "SUBMITTED", "ACKNOWLEDGED"]:
    order_state_machine.transition(oid2, st)
try:
    order_state_machine.transition(oid2, "FILLED")
    test("FILLED without execution_record blocked", False)
except OrderStateMachineError as e:
    test("FILLED without execution_record blocked", True, str(e)[:60])

test("Orders persisted to disk", (ROOT / "data" / "orders_state_machine.json").exists())

# ==========================================================================
# 4. WITHDRAWAL STATE MACHINE
# ==========================================================================
print("\n[4. WITHDRAWAL STATE MACHINE]")
from core.withdrawal_state_machine import withdrawal_state_machine

result = withdrawal_state_machine.request_withdrawal("USER-1", 100.0, "USDT", "TAddr123", "TRC20")
test("Withdrawal locked (LIVE_WITHDRAWALS_ENABLED=false)", result["status"] == "REJECTED", result.get("reason","")[:60])

result = withdrawal_state_machine.request_withdrawal("USER-1", -50.0, "USDT", "TAddr123", "TRC20")
test("Negative withdrawal amount rejected", result["status"] == "REJECTED")

# ==========================================================================
# 5. BINANCE PAY ENGINE
# ==========================================================================
print("\n[5. BINANCE PAY ENGINE]")
from execution.binance_pay_engine import binance_pay_engine

result = binance_pay_engine.create_payment_order(100.0)
test("Binance Pay returns NOT_CONFIGURED without credentials", result["status"] == "NOT_CONFIGURED")

status = binance_pay_engine.get_provider_status()
test("Binance Pay provider status: NOT_CONFIGURED", status["status"] == "NOT_CONFIGURED")

binance_pay_engine.processed_trade_nos.add("TEST-IDEM-001")
result = binance_pay_engine.process_webhook_event({"merchantTradeNo": "TEST-IDEM-001", "bizStatus": "PAY_SUCCESS"})
test("Duplicate webhook idempotent", result["status"] == "ALREADY_PROCESSED")

result2 = binance_pay_engine.process_webhook_event({"merchantTradeNo": "UNKNOWN-999", "bizStatus": "PAY_SUCCESS"})
test("Unknown merchantTradeNo returns NOT_FOUND", result2["status"] == "NOT_FOUND")

# ==========================================================================
# 6. PAYMENT PROVIDER ROUTER
# ==========================================================================
print("\n[6. PAYMENT PROVIDER ROUTER]")
from execution.payment_provider_router import payment_provider_router

statuses = payment_provider_router.get_provider_statuses()
test("Router returns both provider statuses", "BINANCE_PAY" in statuses and "STRIPE" in statuses)
test("Binance Pay shows NOT_CONFIGURED", statuses["BINANCE_PAY"]["status"] == "NOT_CONFIGURED")
test("Stripe shows TEST_MODE", statuses["STRIPE"]["status"] == "TEST_MODE")

# ==========================================================================
# 7. USER WALLET
# ==========================================================================
print("\n[7. USER WALLET]")
from execution.user_wallet import user_wallet

try:
    balances = user_wallet.compute_all()
    test("UserWallet returns all 10 buckets", all(k in balances for k in [
        "total_balance", "available_balance", "trading_balance", "used_margin",
        "unrealized_pnl", "realized_pnl", "fees_paid", "locked_balance",
        "withdrawable_balance", "profit_vault"
    ]))
    test("Reconciliation flag present", "reconciliation_ok" in balances)
    test("Total balance non-negative", balances["total_balance"] >= 0)
except Exception as e:
    test("UserWallet compute_all runs without error", False, str(e))

# ==========================================================================
# 8. DOUBLE-ENTRY LEDGER INTEGRITY & FINANCIAL ASSERTIONS
# ==========================================================================
print("\n[8. DOUBLE-ENTRY LEDGER INTEGRITY & RECONCILIATION]")
from core.double_entry_ledger import double_entry_ledger

entry = double_entry_ledger.post_entry(
    "BINANCE_PAY_DEPOSIT", "BINANCE_PAY_INFLOW", "CUSTOMER_TRADING_ACCOUNT",
    500.0, "USDT", reference_id="TEST-ARCH-001", environment="TEST_ENV"
)
test("Ledger entry posted successfully", entry["status"] == "POSTED", entry["entry_id"])

try:
    double_entry_ledger.post_entry("DEPOSIT", "DR", "CR", 0.0, environment="TEST_ENV")
    test("Zero-amount ledger entry blocked", False)
except ValueError as e:
    test("Zero-amount ledger entry blocked", True, str(e)[:60])

try:
    double_entry_ledger.post_entry("DEPOSIT", "DR", "CR", -100.0, environment="TEST_ENV")
    test("Negative-amount ledger entry blocked", False)
except ValueError as e:
    test("Negative-amount ledger entry blocked", True, str(e)[:60])

bal = double_entry_ledger.get_account_balance("CUSTOMER_TRADING_ACCOUNT", "AEGIS_QUANT_MASTER")
test("Ledger account balance computable", isinstance(bal, float), f"Balance: {bal}")

# Strict Financial Assertions for AEGIS_QUANT_MASTER
opening_entry = double_entry_ledger.ensure_opening_balance("AEGIS_QUANT_MASTER", 100000.0)
test("Opening balance ledger entry exists", opening_entry is not None and opening_entry["amount"] == 100000.0)

from execution.paper_broker import paper_broker
broker_eq = round(float(paper_broker.equity), 2)
ledger_eq = round(double_entry_ledger.get_account_balance("CUSTOMER_TRADING_ACCOUNT", "AEGIS_QUANT_MASTER"), 2)
delta = round(abs(broker_eq - ledger_eq), 2)

test("Ledger Equity == Broker Equity (Delta == $0.00)", delta == 0.0, f"Ledger: ${ledger_eq}, Broker: ${broker_eq}, Delta: ${delta}")

# ==========================================================================
# 9. FAIL-CLOSED INTEGRATION: stale data + LIVE lock
# ==========================================================================
print("\n[9. FAIL-CLOSED INTEGRATION]")

allowed, msg = environment_gate.check_order_allowed("PAPER", market_data_age_seconds=6.0)
test("6s stale data blocks PAPER order", not allowed, msg[:60])

allowed, msg = environment_gate.check_order_allowed("LIVE", market_data_age_seconds=0.1)
test("LIVE order always blocked (no flag)", not allowed, msg[:60])

allowed, msg = environment_gate.check_withdrawal_allowed("AEGIS_QUANT_MASTER")
test("Withdrawal always blocked (no flag)", not allowed, msg[:60])

# ==========================================================================
# 10. PERSISTENCE
# ==========================================================================
print("\n[10. PERSISTENCE]")
test("orders_state_machine.json persisted", (ROOT / "data" / "orders_state_machine.json").exists())
test("binance_pay_payments.json persisted", (ROOT / "data" / "binance_pay_payments.json").exists())
test("withdrawals_state_machine.json persisted", (ROOT / "data" / "withdrawals_state_machine.json").exists())
test("processed_binance_pay_events.json persisted", (ROOT / "data" / "processed_binance_pay_events.json").exists())

# ==========================================================================
# FINAL REPORT
# ==========================================================================
total   = len(results)
passed  = sum(1 for r in results if r["status"] == PASS)
failed  = sum(1 for r in results if r["status"] == FAIL)

print("\n" + "=" * 75)
print(f"MONEY FLOW ARCHITECTURE TEST RESULTS: {passed}/{total} PASS")
print(f"  ✅ PASS: {passed}  ❌ FAIL: {failed}")
print("=" * 75)

if failed > 0:
    print("\nFAILED TESTS:")
    for r in results:
        if r["status"] == FAIL:
            print(f"  ❌ {r['name']}: {r.get('detail', '')}")

final = "INFRASTRUCTURE READY" if failed == 0 else "INFRASTRUCTURE NOT READY"
print(f"\nFINAL STATUS: {final}")
print("=" * 75 + "\n")
sys.exit(0 if failed == 0 else 1)
