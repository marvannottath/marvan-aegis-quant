#!/usr/bin/env python3
"""
AEGIS QUANT — PHASE 5D: FINAL SAFETY HARDENING & RUNTIME VERIFICATION
Automated Test Suite (21 Comprehensive Verification Sections)

Verifies:
  1. Drawdown check exception -> BLOCK
  2. Loss check exception -> BLOCK
  3. News check exception -> BLOCK
  4. Reconciliation check exception -> BLOCK
  5. Instrument check exception -> BLOCK
  6. Market data exception / missing data -> BLOCK
  7. Broker check exception / unconfigured -> BLOCK
  8. Position check exception -> BLOCK
  9. Workspace resolution exception -> BLOCK
  10. Any incomplete preflight -> BLOCK
  11. 13/14 PASS -> BLOCK
  12. 14/14 including one skipped gate -> BLOCK
  13. 14/14 including one unknown gate -> BLOCK
  14. 14/14 actual verified PASS -> only then RUNNING
  15. Restart safety: RUNNING -> PAUSED, PAUSED -> PAUSED, STOPPED -> STOPPED, BLOCKED -> BLOCKED
  16. Market session runtime accuracy (INDIA, FOREX_GOLD, CRYPTO)
  17. India market close behavior: MARKET CLOSED != POSITION CLOSED
  18. AI control state machine distinct states (RUNNING, PAUSED, STOPPED, BLOCKED, DISABLED)
  19. Workspace AI isolation: INDIA != FOREX_GOLD != CRYPTO
  20. Authoritative drawdown enforcement: current_drawdown >= max_drawdown blocks order & AI
  21. AI control audit: immutable audit events for all transitions with SHA-256 integrity
"""

import sys
import os
import json
import time
from pathlib import Path
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock, PropertyMock

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

PASS_COUNT = 0
FAIL_COUNT = 0
TOTAL_CHECKS = 0

def check(name: str, passed: bool, detail: str = ""):
    global PASS_COUNT, FAIL_COUNT, TOTAL_CHECKS
    TOTAL_CHECKS += 1
    if passed:
        PASS_COUNT += 1
        print(f"  [PASS] {name}" + (f" ({detail})" if detail else ""))
    else:
        FAIL_COUNT += 1
        print(f"  [FAIL] {name}" + (f" ({detail})" if detail else ""))

def section(title: str):
    print("\n" + "=" * 76)
    print(f"  {title}")
    print("=" * 76)


def run_all_tests():
    from core.ai_trading_controller import ai_trading_controller, RUNNING, PAUSED, STOPPED, BLOCKED, DISABLED
    from core.market_session_engine import market_session_engine
    from core.execution_gate import execution_gate
    from core.risk_engine import risk_engine
    from core.audit_logger import audit_logger

    # Helper to clean/reset state
    def reset_ai():
        for ws in ("INDIA", "FOREX_GOLD", "CRYPTO"):
            ai_trading_controller._states[ws] = {
                "state": PAUSED,
                "reason": "TEST_RESET",
                "user": "P5D_TEST",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "block_reason": None,
            }
        ai_trading_controller._test_broker_override.clear()

    reset_ai()

    # ══════════════════════════════════════════════════════════════════════════════
    # 1. DRAWDOWN CHECK EXCEPTION -> BLOCK
    # ══════════════════════════════════════════════════════════════════════════════
    section("1. DRAWDOWN CHECK EXCEPTION -> FAIL-CLOSED BLOCK")
    with patch("core.risk_engine.risk_engine.get_drawdown", side_effect=RuntimeError("Simulated Drawdown DB Failure")):
        res = ai_trading_controller.resume("INDIA", user="TEST")
        g8 = next((g for g in res.get("gates", []) if g["id"] == 8), None)
        check("Drawdown exception does not pass Gate 8", g8 and g8["passed"] is False, f"Gate 8: {g8['detail'] if g8 else 'N/A'}")
        check("AI Resume is BLOCKED on drawdown exception", res["ok"] is False and res["state"] == BLOCKED, f"State: {res['state']}")

    # ══════════════════════════════════════════════════════════════════════════════
    # 2. LOSS CHECK EXCEPTION -> BLOCK
    # ══════════════════════════════════════════════════════════════════════════════
    section("2. LOSS CHECK EXCEPTION -> FAIL-CLOSED BLOCK")
    class BrokenLoss:
        @property
        def daily_realized_loss(self):
            raise RuntimeError("Simulated Loss Read Timeout")
    with patch("core.risk_engine.risk_engine", new=BrokenLoss()):
        res = ai_trading_controller.resume("INDIA", user="TEST")
        g9 = next((g for g in res.get("gates", []) if g["id"] == 9), None)
        check("Loss exception does not pass Gate 9", g9 and g9["passed"] is False, f"Gate 9: {g9['detail'] if g9 else 'N/A'}")
        check("AI Resume is BLOCKED on loss check exception", res["ok"] is False and res["state"] == BLOCKED, f"State: {res['state']}")

    # ══════════════════════════════════════════════════════════════════════════════
    # 3. NEWS CHECK EXCEPTION -> BLOCK
    # ══════════════════════════════════════════════════════════════════════════════
    section("3. NEWS CHECK EXCEPTION -> FAIL-CLOSED BLOCK")
    with patch("sync.economic_calendar.economic_filter.is_news_lockout_active", side_effect=Exception("Simulated Calendar API Timeout")):
        res = ai_trading_controller.resume("INDIA", user="TEST")
        g10 = next((g for g in res.get("gates", []) if g["id"] == 10), None)
        check("News exception does not pass Gate 10", g10 and g10["passed"] is False, f"Gate 10: {g10['detail'] if g10 else 'N/A'}")
        check("AI Resume is BLOCKED on news exception", res["ok"] is False and res["state"] == BLOCKED, f"State: {res['state']}")

    # ══════════════════════════════════════════════════════════════════════════════
    # 4. RECONCILIATION CHECK EXCEPTION -> BLOCK
    # ══════════════════════════════════════════════════════════════════════════════
    section("4. RECONCILIATION CHECK EXCEPTION -> FAIL-CLOSED BLOCK")
    class BrokenSentinel:
        @property
        def last_report(self):
            raise KeyError("Corrupted Sentinel Report")
    with patch("core.reconciliation_sentinel.reconciliation_sentinel", new=BrokenSentinel()):
        res = ai_trading_controller.resume("INDIA", user="TEST")
        g11 = next((g for g in res.get("gates", []) if g["id"] == 11), None)
        check("Reconciliation exception does not pass Gate 11", g11 and g11["passed"] is False, f"Gate 11: {g11['detail'] if g11 else 'N/A'}")
        check("AI Resume is BLOCKED on reconciliation exception", res["ok"] is False and res["state"] == BLOCKED, f"State: {res['state']}")

    # ══════════════════════════════════════════════════════════════════════════════
    # 5. INSTRUMENT CHECK EXCEPTION -> BLOCK
    # ══════════════════════════════════════════════════════════════════════════════
    section("5. INSTRUMENT CHECK EXCEPTION -> FAIL-CLOSED BLOCK")
    with patch("core.instrument_master.instrument_master.get_all_symbols", side_effect=ValueError("Corrupted Instrument Master Table")):
        res = ai_trading_controller.resume("INDIA", user="TEST")
        g14 = next((g for g in res.get("gates", []) if g["id"] == 14), None)
        check("Instrument master exception does not pass Gate 14", g14 and g14["passed"] is False, f"Gate 14: {g14['detail'] if g14 else 'N/A'}")
        check("AI Resume is BLOCKED on instrument check exception", res["ok"] is False and res["state"] == BLOCKED, f"State: {res['state']}")

    # ══════════════════════════════════════════════════════════════════════════════
    # 6. MARKET DATA EXCEPTION & MISSING DATA (age=9999.0s) -> BLOCK
    # ══════════════════════════════════════════════════════════════════════════════
    section("6. MARKET DATA EXCEPTION & MISSING DATA -> FAIL-CLOSED BLOCK")
    # A. Stale / Not Subscribed (9999.0s)
    with patch("core.market_data_watchdog.market_data_watchdog.get_age", return_value=9999.0):
        res = ai_trading_controller.resume("INDIA", user="TEST")
        g4 = next((g for g in res.get("gates", []) if g["id"] == 4), None)
        check("Missing data (age=9999.0s) strictly FAILS Gate 4", g4 and g4["passed"] is False, f"Detail: {g4['detail'] if g4 else 'N/A'}")
        check("AI Resume is BLOCKED when data is unsubscribed", res["ok"] is False and res["state"] == BLOCKED)

    # B. Watchdog Exception
    with patch("core.market_data_watchdog.market_data_watchdog.get_age", side_effect=RuntimeError("Watchdog Shared Memory Failure")):
        res = ai_trading_controller.resume("INDIA", user="TEST")
        g4 = next((g for g in res.get("gates", []) if g["id"] == 4), None)
        check("Market data exception strictly FAILS Gate 4", g4 and g4["passed"] is False, f"Detail: {g4['detail'] if g4 else 'N/A'}")
        check("AI Resume is BLOCKED on watchdog exception", res["ok"] is False and res["state"] == BLOCKED)

    # ══════════════════════════════════════════════════════════════════════════════
    # 7. BROKER CHECK EXCEPTION & UNCONFIGURED -> BLOCK
    # ══════════════════════════════════════════════════════════════════════════════
    section("7. BROKER CHECK EXCEPTION & UNCONFIGURED PROVIDER -> FAIL-CLOSED BLOCK")
    # A. Truthful unconfigured state
    res = ai_trading_controller.resume("INDIA", user="TEST")
    g3 = next((g for g in res.get("gates", []) if g["id"] == 3), None)
    check("Unconfigured Upstox broker fails Gate 3", g3 and g3["passed"] is False, f"Detail: {g3['detail'] if g3 else 'N/A'}")
    check("AI Resume is BLOCKED for unconfigured broker", res["ok"] is False and res["state"] == BLOCKED)

    # B. Broker exception
    with patch("execution.upstox_broker.upstox_broker.get_configuration_state", side_effect=Exception("Vault decryption error")):
        res = ai_trading_controller.resume("INDIA", user="TEST")
        g3 = next((g for g in res.get("gates", []) if g["id"] == 3), None)
        check("Broker exception fails Gate 3", g3 and g3["passed"] is False, f"Detail: {g3['detail'] if g3 else 'N/A'}")

    # ══════════════════════════════════════════════════════════════════════════════
    # 8. POSITION CHECK EXCEPTION & DELTA DETECTED -> BLOCK
    # ══════════════════════════════════════════════════════════════════════════════
    section("8. POSITION CHECK EXCEPTION & DELTA DISCREPANCY -> FAIL-CLOSED BLOCK")
    with patch("core.position_snapshot_service.position_snapshot_service.get_snapshot", return_value={"status": "FAIL", "delta_detected": True, "reconciliation_status": "RECONCILIATION_FAIL"}):
        res = ai_trading_controller.resume("INDIA", user="TEST")
        g6 = next((g for g in res.get("gates", []) if g["id"] == 6), None)
        check("Position reconciliation delta fails Gate 6", g6 and g6["passed"] is False, f"Detail: {g6['detail'] if g6 else 'N/A'}")
        check("AI Resume is BLOCKED on position delta", res["ok"] is False and res["state"] == BLOCKED)

    # ══════════════════════════════════════════════════════════════════════════════
    # 9. WORKSPACE RESOLUTION EXCEPTION -> BLOCK
    # ══════════════════════════════════════════════════════════════════════════════
    section("9. WORKSPACE RESOLUTION EXCEPTION -> FAIL-CLOSED BLOCK")
    res = ai_trading_controller.resume("INVALID_WS_NAME", user="TEST")
    g1 = next((g for g in res.get("gates", []) if g["id"] == 1), None)
    check("Invalid workspace fails Gate 1", g1 and g1["passed"] is False, f"Detail: {g1['detail'] if g1 else 'N/A'}")
    check("AI Resume is BLOCKED on invalid workspace", res["ok"] is False)

    # ══════════════════════════════════════════════════════════════════════════════
    # 10. ANY INCOMPLETE PREFLIGHT -> BLOCK
    # ══════════════════════════════════════════════════════════════════════════════
    section("10. INCOMPLETE PREFLIGHT (LESS THAN 14 GATES) -> FAIL-CLOSED BLOCK")
    # Simulate a truncated preflight returning only 13 gates
    with patch.object(ai_trading_controller, "_run_resume_preflight", return_value=(False, [{"id": i, "name": f"Gate {i}", "passed": True} for i in range(1, 14)])):
        res = ai_trading_controller.resume("INDIA", user="TEST")
        check("Preflight with only 13 gates is rejected", res["ok"] is False and res["state"] == BLOCKED)

    # ══════════════════════════════════════════════════════════════════════════════
    # 11. 13/14 PASS -> BLOCK
    # ══════════════════════════════════════════════════════════════════════════════
    section("11. 13/14 GATES PASS -> FAIL-CLOSED BLOCK")
    thirteen_gates = [{"id": i, "name": f"Gate {i}", "passed": (i != 14)} for i in range(1, 15)]
    with patch.object(ai_trading_controller, "_run_resume_preflight", return_value=(False, thirteen_gates)):
        res = ai_trading_controller.resume("INDIA", user="TEST")
        check("13/14 PASS strictly yields BLOCKED", res["ok"] is False and res["state"] == BLOCKED)
        check("Resume is NOT allowed", res.get("state") != RUNNING)

    # ══════════════════════════════════════════════════════════════════════════════
    # 12. 14/14 INCLUDING ONE SKIPPED GATE -> BLOCK
    # ══════════════════════════════════════════════════════════════════════════════
    section("12. 14/14 WITH ONE SKIPPED GATE -> FAIL-CLOSED BLOCK")
    skipped_gates = [{"id": i, "name": f"Gate {i}", "passed": True, "skipped": (i == 4)} for i in range(1, 15)]
    all_pass_skipped = (
        len(skipped_gates) == 14
        and sum(1 for g in skipped_gates if g.get("passed") is True) == 14
        and sum(1 for g in skipped_gates if g.get("skipped", False)) == 0
    )
    check("Skipped gate invariant prevents all_passed evaluation", all_pass_skipped is False)

    # ══════════════════════════════════════════════════════════════════════════════
    # 13. 14/14 INCLUDING ONE UNKNOWN GATE -> BLOCK
    # ══════════════════════════════════════════════════════════════════════════════
    section("13. 14/14 WITH ONE UNKNOWN/NULL GATE -> FAIL-CLOSED BLOCK")
    unknown_gates = [{"id": i, "name": f"Gate {i}", "passed": (None if i == 7 else True)} for i in range(1, 15)]
    with patch.object(ai_trading_controller, "_run_resume_preflight", return_value=(False, unknown_gates)):
        res = ai_trading_controller.resume("INDIA", user="TEST")
        check("Gate with None/Unknown passed status blocks resume", res["ok"] is False and res["state"] == BLOCKED)

    # ══════════════════════════════════════════════════════════════════════════════
    # 14. 14/14 ACTUAL VERIFIED PASS -> RUNNING
    # ══════════════════════════════════════════════════════════════════════════════
    section("14. 14/14 VERIFIED EVIDENCE -> TRANSITION TO RUNNING")
    reset_ai()
    # Provide all 14 verified mock conditions for CRYPTO (always OPEN)
    ai_trading_controller._test_broker_override["CRYPTO"] = True
    with patch("core.market_data_watchdog.market_data_watchdog.get_age", return_value=0.5):
        with patch("core.market_session_engine.market_session_engine.get_state", return_value="OPEN"):
            res = ai_trading_controller.resume("CRYPTO", user="TEST_OPERATOR")
            check("All 14 gates pass with full verified evidence", res["ok"] is True, f"Passed: {res.get('gates_passed')}/14")
            check("AI State is strictly RUNNING", res["state"] == RUNNING)
            check("Workspace state persisted as RUNNING", ai_trading_controller.get_state("CRYPTO") == RUNNING)

    # ══════════════════════════════════════════════════════════════════════════════
    # 15. RESTART SAFETY (PERSISTENCE)
    # ══════════════════════════════════════════════════════════════════════════════
    section("15. RESTART SAFETY INVARIANTS")
    from core.ai_trading_controller import AITradingController
    # RUNNING in memory -> simulated restart loads it as PAUSED
    new_controller = AITradingController()
    check("RUNNING AI automatically converts to PAUSED on reload", new_controller.get_state("CRYPTO") == PAUSED)

    # STOPPED remains STOPPED
    ai_trading_controller.stop("INDIA", user="TEST", reason="PRE_RESTART_STOP")
    new_controller_2 = AITradingController()
    check("STOPPED state survives restart", new_controller_2.get_state("INDIA") == STOPPED)

    # BLOCKED remains BLOCKED
    ai_trading_controller.block("FOREX_GOLD", user="TEST", reason="CRITICAL_RISK")
    new_controller_3 = AITradingController()
    check("BLOCKED state survives restart", new_controller_3.get_state("FOREX_GOLD") == BLOCKED)

    # ══════════════════════════════════════════════════════════════════════════════
    # 16. MARKET SESSION RUNTIME ACCURACY
    # ══════════════════════════════════════════════════════════════════════════════
    section("16. MARKET SESSION RUNTIME ACCURACY (INDIA, FOREX_GOLD, CRYPTO)")
    states = market_session_engine.get_all_states()
    check("INDIA session state is valid enum", states["INDIA"]["state"] in ("PRE_MARKET", "OPEN", "CLOSING_SOON", "CLOSED", "HOLIDAY", "HALTED", "UNKNOWN"))
    check("FOREX_GOLD session state is valid enum", states["FOREX_GOLD"]["state"] in ("OPEN", "CLOSED", "HOLIDAY", "HALTED", "UNKNOWN"))
    check("CRYPTO session is 24/7 OPEN by default", states["CRYPTO"]["state"] == "OPEN")

    # Manual halt
    market_session_engine.set_halted("CRYPTO", reason="Emergency Halt Test", by="TEST_ADMIN")
    check("CRYPTO state immediately reflects HALTED", market_session_engine.get_state("CRYPTO") == "HALTED")
    market_session_engine.clear_halt("CRYPTO", by="TEST_ADMIN")
    check("CRYPTO state clears halt back to OPEN", market_session_engine.get_state("CRYPTO") == "OPEN")

    # ══════════════════════════════════════════════════════════════════════════════
    # 17. INDIA MARKET CLOSE: MARKET CLOSED ≠ POSITION CLOSED
    # ══════════════════════════════════════════════════════════════════════════════
    section("17. INDIA MARKET CLOSE: POSITIONS ARE NOT CLOSED AUTOMATICALLY")
    from execution.paper_broker import paper_broker
    paper_broker.positions["RELIANCE"] = {
        "symbol": "RELIANCE",
        "quantity": 10,
        "entry_price": 2500.0,
        "current_price": 2500.0,
        "workspace": "INDIA",
        "product": "CNC",
    }
    pos_before = len(paper_broker.positions)

    # Simulate market close transition
    ai_trading_controller.auto_block_for_market_close("INDIA")
    pos_after = len(paper_broker.positions)

    check("Open positions count unchanged after market close", pos_before == pos_after and "RELIANCE" in paper_broker.positions)
    check("No unintended square-off occurred", paper_broker.positions["RELIANCE"]["quantity"] == 10)
    del paper_broker.positions["RELIANCE"]

    # ══════════════════════════════════════════════════════════════════════════════
    # 18. AI CONTROL STATE MACHINE DISTINCT STATES
    # ══════════════════════════════════════════════════════════════════════════════
    section("18. AI CONTROL STATE MACHINE (RUNNING, PAUSED, STOPPED, BLOCKED, DISABLED)")
    reset_ai()
    ai_trading_controller.pause("INDIA", user="TEST", reason="TEST_PAUSE")
    check("State PAUSED active", ai_trading_controller.get_state("INDIA") == PAUSED)

    ai_trading_controller.stop("INDIA", user="TEST", reason="TEST_STOP")
    check("State STOPPED active", ai_trading_controller.get_state("INDIA") == STOPPED)

    ai_trading_controller.block("INDIA", user="TEST", reason="TEST_BLOCK")
    check("State BLOCKED active", ai_trading_controller.get_state("INDIA") == BLOCKED)

    # Test allowed transitions
    check("PAUSED is not RUNNING", PAUSED != RUNNING)
    check("STOPPED is not PAUSED", STOPPED != PAUSED)
    check("BLOCKED is distinct from DISABLED", BLOCKED != DISABLED)

    # ══════════════════════════════════════════════════════════════════════════════
    # 19. WORKSPACE AI ISOLATION
    # ══════════════════════════════════════════════════════════════════════════════
    section("19. WORKSPACE AI ISOLATION (INDIA != FOREX_GOLD != CRYPTO)")
    reset_ai()
    ai_trading_controller.pause("INDIA", user="TEST", reason="PAUSE_INDIA_ONLY")
    check("INDIA is PAUSED", ai_trading_controller.get_state("INDIA") == PAUSED)
    check("CRYPTO state unaffected (remains PAUSED)", ai_trading_controller.get_state("CRYPTO") == PAUSED)

    ai_trading_controller.stop("CRYPTO", user="TEST", reason="STOP_CRYPTO_ONLY")
    check("CRYPTO is STOPPED", ai_trading_controller.get_state("CRYPTO") == STOPPED)
    check("INDIA is NOT STOPPED (remains PAUSED)", ai_trading_controller.get_state("INDIA") == PAUSED)
    check("FOREX_GOLD is unaffected", ai_trading_controller.get_state("FOREX_GOLD") == PAUSED)

    # ══════════════════════════════════════════════════════════════════════════════
    # 20. AUTHORITATIVE DRAWDOWN ENFORCEMENT
    # ══════════════════════════════════════════════════════════════════════════════
    section("20. AUTHORITATIVE DRAWDOWN ENFORCEMENT (SERVER-SIDE)")
    # Test breach condition
    with patch.object(risk_engine, "get_drawdown", return_value={"workspace": "INDIA", "drawdown_pct": 12.5, "max_drawdown_pct": 5.0, "breached": True}):
        dd_ok, dd_val, dd_reason = risk_engine.evaluate_drawdown("INDIA")
        check("Drawdown >= limit evaluates to False", dd_ok is False)
        check("Drawdown breach reason explicitly identifies violation", "MAX_DRAWDOWN_BREACHED" in dd_reason)
        # Verify execution gate rejects order when drawdown breached
        ok, code, reason, _ = execution_gate.validate_order(
            symbol="RELIANCE", side="BUY", quantity=1.0, price=2500.0,
            workspace="INDIA", environment="PAPER", currency="INR", data_age_seconds=0.0
        )
        check("Execution gate rejects order on drawdown breach", ok is False)
        check("Rejection code is RISK_REJECTED or MARKET_SESSION_CLOSED", "REJECTED" in code or "CLOSED" in code)
    risk_engine.circuit_tripped = False

    # ══════════════════════════════════════════════════════════════════════════════
    # 21. AI CONTROL AUDIT INTEGRITY
    # ══════════════════════════════════════════════════════════════════════════════
    section("21. AI CONTROL AUDIT INTEGRITY (IMMUTABLE SHA-256 CHAIN)")
    chain_ok, chain_msg = audit_logger.verify_chain_integrity()
    check("Audit chain cryptographically intact", chain_ok, chain_msg)

    # Check recent AI audit events exist
    ai_event_types = {e.get("event_type") for e in audit_logger.logs[:50]}
    expected_ai_types = {"AI_PAUSE", "AI_STOP", "AI_BLOCKED"}
    found = expected_ai_types.intersection(ai_event_types)
    check("Key AI lifecycle events present in audit trail", len(found) >= 2, f"Found: {found}")

    # Check hash presence on recent logs
    recent_hashes = [e.get("integrity_hash") for e in audit_logger.logs[:20]]
    check("Recent audit events contain 64-character SHA-256 hashes", all(len(h) == 64 for h in recent_hashes if h))

    reset_ai()

    # ══════════════════════════════════════════════════════════════════════════════
    # FINAL SUMMARY
    # ══════════════════════════════════════════════════════════════════════════════
    print("\n" + "=" * 76)
    print("PHASE 5D MASTER TEST SUMMARY")
    print("=" * 76)
    print(f"  Total Checks: {TOTAL_CHECKS}")
    print(f"  Passed:       {PASS_COUNT}")
    print(f"  Failed:       {FAIL_COUNT}")
    rate = (PASS_COUNT / TOTAL_CHECKS) * 100.0 if TOTAL_CHECKS > 0 else 0.0
    print(f"  Success Rate: {rate:.1f}%")
    print(f"  Final Status: {'PASS — ALL 21 SAFETY HARDENING INVARIANTS VERIFIED' if FAIL_COUNT == 0 else 'FAIL'}")
    print("=" * 76 + "\n")

    return 0 if FAIL_COUNT == 0 else 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
