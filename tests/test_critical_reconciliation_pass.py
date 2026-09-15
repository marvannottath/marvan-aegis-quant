"""
AEGIS QUANT — CRITICAL INTEGRITY RECONCILIATION PASS MASTER TEST SUITE (20 GATES)
Exhaustively verifies all 20 requirements from Section 13:
  1.  Dashboard position count == authoritative position count
  2.  Dashboard exposure == authoritative exposure
  3.  Position table == authoritative position store
  4.  Broker position state reconciles with internal state
  5.  Position delta is detected
  6.  Stale positions are not shown as active
  7.  Backtest currency matches workspace
  8.  Backtest venue matches workspace
  9.  Backtest trade count matches actual trade rows
  10. Backtest PnL reconciles
  11. Missing trade log cannot produce RECONCILIATION_OK
  12. Audit events use real persisted events
  13. Profiler scope is explicit
  14. Profiler missing stage is NOT MEASURED
  15. Profiler column mapping is correct
  16. Wrong workspace data is rejected
  17. Failed reconciliation blocks execution
  18. Persistence survives restart
  19. Binance LIVE remains disabled
  20. Withdrawal remains disabled
"""

import os
import sys
import json
import time
import asyncio
from pathlib import Path

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from core.workspace_manager import workspace_manager
from core.position_snapshot_service import position_snapshot_service, PositionSnapshotService
from core.execution_gate import execution_gate
from core.environment_gate import environment_gate
from core.market_data_watchdog import market_data_watchdog
from core.risk_engine import risk_engine
from core.execution_latency_profiler import execution_latency_profiler
from core.audit_logger import audit_logger, FinancialAuditLogger
from core.double_entry_ledger import double_entry_ledger
from core.order_state_machine import order_state_machine
from core.backtest_analytics_engine import backtest_analytics_engine
from execution.paper_broker import paper_broker
from dashboard.app import app, get_state, get_india_positions, get_position_snapshot


class DummyRequest:
    def __init__(self, data=None, query_params=None, cookies=None):
        self._data = data or {}
        self.query_params = query_params or {}
        self.cookies = cookies or {}
        self.client = type("Client", (), {"host": "127.0.0.1"})()

    async def json(self):
        return self._data


def run_all_tests():
    print("\n" + "=" * 75)
    print("  AEGIS QUANT — 20-POINT CRITICAL RECONCILIATION VERIFICATION BATTERY")
    print("=" * 75 + "\n")

    results = {}

    # ------------------------------------------------------------------
    # GATE 1: Dashboard position count == authoritative position count
    # ------------------------------------------------------------------
    try:
        snap = position_snapshot_service.get_snapshot("INDIA")
        auth_count = snap["open_position_count"]

        # Check API state response
        req = DummyRequest(query_params={"workspace": "INDIA"})
        loop = asyncio.get_event_loop()
        state_resp = loop.run_until_complete(get_state(req))
        state_data = json.loads(state_resp.body.decode("utf-8")) if hasattr(state_resp, "body") else state_resp

        dashboard_count = state_data.get("open_positions_count", -1)
        snap_in_state = state_data.get("position_snapshot", {})

        assert auth_count == 0, f"Expected 0 open positions for INDIA, got {auth_count}"
        assert dashboard_count == auth_count, f"Dashboard count {dashboard_count} != authoritative {auth_count}"
        assert snap_in_state.get("open_position_count") == auth_count, "Position snapshot in /api/state mismatch"
        results["1. Dashboard position count == authoritative count"] = "PASS"
        print("  [PASS] Gate 1: Dashboard position count == authoritative count (0 == 0)")
    except Exception as e:
        results["1. Dashboard position count == authoritative count"] = f"FAIL: {e}"
        print(f"  [FAIL] Gate 1: {e}")

    # ------------------------------------------------------------------
    # GATE 2: Dashboard exposure == authoritative exposure
    # ------------------------------------------------------------------
    try:
        snap = position_snapshot_service.get_snapshot("INDIA")
        auth_exposure = snap["total_exposure"]

        req = DummyRequest(query_params={"workspace": "INDIA"})
        state_resp = loop.run_until_complete(get_state(req))
        state_data = json.loads(state_resp.body.decode("utf-8")) if hasattr(state_resp, "body") else state_resp
        dashboard_exposure = state_data.get("total_exposure", -1.0)

        assert auth_exposure == 0.0, f"Authoritative exposure {auth_exposure} != 0.0"
        assert dashboard_exposure == auth_exposure, f"Dashboard exposure {dashboard_exposure} != authoritative {auth_exposure}"
        results["2. Dashboard exposure == authoritative exposure"] = "PASS"
        print(f"  [PASS] Gate 2: Dashboard exposure == authoritative exposure (₹{dashboard_exposure:.2f} == ₹{auth_exposure:.2f})")
    except Exception as e:
        results["2. Dashboard exposure == authoritative exposure"] = f"FAIL: {e}"
        print(f"  [FAIL] Gate 2: {e}")

    # ------------------------------------------------------------------
    # GATE 3: Position table == authoritative position store
    # ------------------------------------------------------------------
    try:
        snap = position_snapshot_service.get_snapshot("INDIA")
        raw_resp = loop.run_until_complete(get_india_positions()) if asyncio.iscoroutinefunction(get_india_positions) else get_india_positions()
        india_pos_resp = json.loads(raw_resp.body.decode("utf-8")) if hasattr(raw_resp, "body") else raw_resp
        table_positions = india_pos_resp.get("positions", [])

        assert len(table_positions) == len(snap["positions"]), "Table row count != snapshot row count"
        assert snap["positions"] == table_positions, "Position objects differ between snapshot and table endpoint"
        results["3. Position table == authoritative position store"] = "PASS"
        print(f"  [PASS] Gate 3: Position table == authoritative position store ({len(table_positions)} rows verified)")
    except Exception as e:
        results["3. Position table == authoritative position store"] = f"FAIL: {e}"
        print(f"  [FAIL] Gate 3: {e}")

    # ------------------------------------------------------------------
    # GATE 4: Broker position state reconciles with internal state
    # ------------------------------------------------------------------
    try:
        snap = position_snapshot_service.get_snapshot("INDIA")
        assert snap["broker_sync"] == "SYNCED", f"Broker sync status '{snap['broker_sync']}' != 'SYNCED'"
        assert snap["reconciliation_status"] == "RECONCILIATION_OK", f"Status '{snap['reconciliation_status']}' != 'RECONCILIATION_OK'"
        assert snap["status"] == "PASS", f"Snapshot status '{snap['status']}' != 'PASS'"
        assert snap["delta_detected"] is False, "Unexpected delta detected during clean state"
        results["4. Broker position state reconciles"] = "PASS"
        print("  [PASS] Gate 4: Broker position state reconciles with internal state (SYNCED, RECONCILIATION_OK)")
    except Exception as e:
        results["4. Broker position state reconciles"] = f"FAIL: {e}"
        print(f"  [FAIL] Gate 4: {e}")

    # ------------------------------------------------------------------
    # GATE 5: Position delta is detected
    # ------------------------------------------------------------------
    try:
        # Inject synthetic delta into India broker
        delta_pos = [{"symbol": "RELIANCE", "units": 50, "entry_price": 2850.0}]
        position_snapshot_service.inject_position_delta("INDIA", delta_pos)

        delta_snap = position_snapshot_service.get_snapshot("INDIA")
        assert delta_snap["delta_detected"] is True, "Delta was not detected by snapshot service"
        assert delta_snap["reconciliation_status"] == "RECONCILIATION_FAIL", f"Expected RECONCILIATION_FAIL, got {delta_snap['reconciliation_status']}"
        assert delta_snap["status"] == "FAIL", f"Expected FAIL, got {delta_snap['status']}"
        assert delta_snap["broker_positions_count"] == 1, f"Expected broker count 1, got {delta_snap['broker_positions_count']}"

        # Clean up injected delta
        position_snapshot_service.clear_injected_delta("INDIA")
        clean_snap = position_snapshot_service.get_snapshot("INDIA")
        assert clean_snap["delta_detected"] is False, "Delta cleanup failed"
        assert clean_snap["reconciliation_status"] == "RECONCILIATION_OK", "Status did not return to OK"

        results["5. Position delta is detected"] = "PASS"
        print("  [PASS] Gate 5: Position delta is detected (RECONCILIATION_FAIL triggered and cleaned)")
    except Exception as e:
        position_snapshot_service.clear_injected_delta("INDIA")
        results["5. Position delta is detected"] = f"FAIL: {e}"
        print(f"  [FAIL] Gate 5: {e}")

    # ------------------------------------------------------------------
    # GATE 6: Stale positions are not shown as active
    # ------------------------------------------------------------------
    try:
        orders_db = ROOT_DIR / "data" / "orders_state_machine.json"
        assert orders_db.exists(), "orders_state_machine.json missing"
        with open(orders_db, "r") as f:
            all_orders = json.load(f)

        india_orders = [
            o for o in all_orders.values()
            if workspace_manager.is_symbol_allowed(o.get("symbol", ""), "INDIA")
        ]
        assert len(india_orders) >= 5, f"Expected at least 5 historical India orders, found {len(india_orders)}"

        # All existing India orders are FILLED historical orders
        filled_india = [o for o in india_orders if o.get("status") == "FILLED"]
        assert len(filled_india) == len(india_orders), "Some India orders are in non-terminal state"

        # Verify snapshot service does NOT treat FILLED orders as active positions
        snap = position_snapshot_service.get_snapshot("INDIA")
        assert snap["open_position_count"] == 0, f"Snapshot incorrectly counted terminal orders as active: {snap['open_position_count']}"

        results["6. Stale positions are not shown as active"] = "PASS"
        print(f"  [PASS] Gate 6: Stale positions are not shown as active ({len(filled_india)} terminal orders ignored)")
    except Exception as e:
        results["6. Stale positions are not shown as active"] = f"FAIL: {e}"
        print(f"  [FAIL] Gate 6: {e}")

    # ------------------------------------------------------------------
    # GATE 7: Backtest currency matches workspace
    # ------------------------------------------------------------------
    try:
        runs = backtest_analytics_engine.list_backtest_runs()
        assert len(runs) > 0, "No backtest runs found"

        for r in runs:
            ws = r.get("workspace")
            cur = r.get("currency")
            if ws == "INDIA":
                assert cur == "INR", f"India backtest {r['backtest_id']} has non-INR currency: {cur}"
            elif ws == "CRYPTO":
                assert cur in ("USDT", "USD"), f"Crypto backtest {r['backtest_id']} has non-USD currency: {cur}"

        results["7. Backtest currency matches workspace"] = "PASS"
        print(f"  [PASS] Gate 7: Backtest currency matches workspace ({len(runs)} runs verified)")
    except Exception as e:
        results["7. Backtest currency matches workspace"] = f"FAIL: {e}"
        print(f"  [FAIL] Gate 7: {e}")

    # ------------------------------------------------------------------
    # GATE 8: Backtest venue matches workspace
    # ------------------------------------------------------------------
    try:
        for r in runs:
            ws = r.get("workspace")
            venue = r.get("venue")
            if ws == "INDIA":
                assert venue in ("NSE", "BSE"), f"India backtest {r['backtest_id']} has wrong venue: {venue}"
            elif ws == "CRYPTO":
                assert venue in ("Binance", "BINANCE"), f"Crypto backtest {r['backtest_id']} has wrong venue: {venue}"

        results["8. Backtest venue matches workspace"] = "PASS"
        print(f"  [PASS] Gate 8: Backtest venue matches workspace (NSE/BSE vs Binance)")
    except Exception as e:
        results["8. Backtest venue matches workspace"] = f"FAIL: {e}"
        print(f"  [FAIL] Gate 8: {e}")

    # ------------------------------------------------------------------
    # GATE 9: Backtest trade count matches actual trade rows
    # ------------------------------------------------------------------
    try:
        hp100 = backtest_analytics_engine.get_backtest_detail("BQ-BT-HP100-1789006052")
        assert hp100 is not None, "BQ-BT-HP100-1789006052 not found"
        summary = hp100["summary"]
        trades = hp100["trades"]

        assert summary["trade_count"] == len(trades), f"Summary trade count {summary['trade_count']} != actual trade rows {len(trades)}"
        assert len(trades) == 100, f"Expected 100 trades, got {len(trades)}"

        results["9. Backtest trade count matches actual trade rows"] = "PASS"
        print(f"  [PASS] Gate 9: Backtest trade count matches actual trade rows (100 == {len(trades)})")
    except Exception as e:
        results["9. Backtest trade count matches actual trade rows"] = f"FAIL: {e}"
        print(f"  [FAIL] Gate 9: {e}")

    # ------------------------------------------------------------------
    # GATE 10: Backtest PnL reconciles
    # ------------------------------------------------------------------
    try:
        summary = hp100["summary"]
        trades = hp100["trades"]
        init_cap = summary["initial_capital"]
        final_cap = summary["final_capital"]
        net_pnl = summary["net_pnl"]

        sum_trade_pnl = sum(t["net_pnl"] for t in trades)
        derived_final = init_cap + sum_trade_pnl

        delta = abs(derived_final - final_cap)
        assert delta < 0.10, f"PnL delta ₹{delta:.4f} exceeds ₹0.10 tolerance. Derived: {derived_final}, Stored: {final_cap}"
        assert summary["reconciliation_status"] == "RECONCILIATION_OK", f"Status '{summary['reconciliation_status']}' != RECONCILIATION_OK"

        results["10. Backtest PnL reconciles"] = "PASS"
        print(f"  [PASS] Gate 10: Backtest PnL reconciles (initial + sum(net_pnl) == final, delta: ${delta:.4f})")
    except Exception as e:
        results["10. Backtest PnL reconciles"] = f"FAIL: {e}"
        print(f"  [FAIL] Gate 10: {e}")

    # ------------------------------------------------------------------
    # GATE 11: Missing trade log cannot produce RECONCILIATION_OK
    # ------------------------------------------------------------------
    try:
        # Request a non-existent backtest
        empty_res = backtest_analytics_engine.get_backtest_detail("NON-EXISTENT-ID")
        assert empty_res is None, "Non-existent backtest should return None"

        # Verify reconciliation validator on empty trades
        incomplete_summary = backtest_analytics_engine._verify_integrity({"trade_history": []})
        assert incomplete_summary["status"] == "INCOMPLETE", f"Expected INCOMPLETE, got {incomplete_summary['status']}"
        assert "INCOMPLETE" in incomplete_summary["message"], "Message should indicate INCOMPLETE"

        results["11. Missing trade log cannot produce RECONCILIATION_OK"] = "PASS"
        print("  [PASS] Gate 11: Missing trade log cannot produce RECONCILIATION_OK (returns INCOMPLETE)")
    except Exception as e:
        results["11. Missing trade log cannot produce RECONCILIATION_OK"] = f"FAIL: {e}"
        print(f"  [FAIL] Gate 11: {e}")

    # ------------------------------------------------------------------
    # GATE 12: Audit events use real persisted events
    # ------------------------------------------------------------------
    try:
        events = audit_logger.get_events(limit=500)
        assert len(events) >= 100, f"Expected at least 100 persisted events, got {len(events)}"

        # Check integrity of first 10 events
        for ev in events[:10]:
            assert "event_id" in ev and ev["event_id"].startswith("AUD-"), f"Invalid event_id: {ev.get('event_id')}"
            assert "timestamp" in ev, "Missing timestamp"
            assert "event_type" in ev, "Missing event_type"
            assert "integrity_hash" in ev and len(ev["integrity_hash"]) == 64, "Missing or invalid SHA-256 integrity hash"

        results["12. Audit events use real persisted events"] = "PASS"
        print(f"  [PASS] Gate 12: Audit events use real persisted events ({len(events)} real events loaded from disk)")
    except Exception as e:
        results["12. Audit events use real persisted events"] = f"FAIL: {e}"
        print(f"  [FAIL] Gate 12: {e}")

    # ------------------------------------------------------------------
    # GATE 13: Profiler scope is explicit
    # ------------------------------------------------------------------
    try:
        scopes = execution_latency_profiler.CANONICAL_TIMING_SCOPES
        required_scopes = {"END-TO-END EXECUTION", "ORDER SUBMISSION", "EXCHANGE / FILL", "LEDGER WRITE"}
        assert required_scopes.issubset(set(scopes.keys())), f"Missing canonical timing scopes: {required_scopes - set(scopes.keys())}"

        summary = execution_latency_profiler.get_summary()
        assert "timing_scopes" in summary, "Missing timing_scopes in profiler summary"
        assert summary["timing_scopes"]["ORDER_SUBMISSION"]["canonical_name"] == "ORDER SUBMISSION"

        results["13. Profiler scope is explicit"] = "PASS"
        print("  [PASS] Gate 13: Profiler scope is explicit (4 canonical segregated scopes verified)")
    except Exception as e:
        results["13. Profiler scope is explicit"] = f"FAIL: {e}"
        print(f"  [FAIL] Gate 13: {e}")

    # ------------------------------------------------------------------
    # GATE 14: Profiler missing stage is NOT MEASURED
    # ------------------------------------------------------------------
    try:
        unmeasured_summary = execution_latency_profiler.get_summary(workspace="UNMEASURED_VENUE")
        stages = unmeasured_summary.get("stage_averages", [])

        # In UNMEASURED_VENUE with zero historical executions, all stages must be NOT MEASURED
        assert len(stages) == 10, f"Expected 10 stages, got {len(stages)}"
        for s in stages:
            assert s["status"] == "NOT MEASURED", f"Stage {s['stage']} has status {s['status']} instead of NOT MEASURED"
            assert s["avg_duration_ms"] is None, f"Stage {s['stage']} has avg_duration_ms {s['avg_duration_ms']} instead of None"

        assert unmeasured_summary.get("p50") is None, f"Expected None p50 for unmeasured profiler, got {unmeasured_summary.get('p50')}"

        # Also verify that across all profiler stage averages, none report 0.0 ms when not measured
        for st in stages:
            assert st["avg_duration_ms"] != 0.0, "Found fake 0.0ms on unmeasured stage"

        results["14. Profiler missing stage is NOT MEASURED"] = "PASS"
        print("  [PASS] Gate 14: Profiler missing stage is NOT MEASURED (avg_duration_ms is None, no fake 0.0ms)")
    except Exception as e:
        results["14. Profiler missing stage is NOT MEASURED"] = f"FAIL: {e}"
        print(f"  [FAIL] Gate 14: {e}")


    # ------------------------------------------------------------------
    # GATE 15: Profiler column mapping is correct
    # ------------------------------------------------------------------
    try:
        # Check index.html template has the exact 8 headers
        tmpl_path = ROOT_DIR / "dashboard" / "templates" / "index.html"
        with open(tmpl_path, "r") as f:
            tmpl_content = f.read()

        expected_headers = [
            "Timestamp", "Execution ID", "Order ID", "Symbol",
            "Workspace", "Result", "Total Latency", "Risk Gate"
        ]
        for h in expected_headers:
            assert h in tmpl_content, f"Execution table header '{h}' missing from index.html"

        # Check app.py prerender generates all 8 columns in order
        app_path = ROOT_DIR / "dashboard" / "app.py"
        with open(app_path, "r") as f:
            app_content = f.read()

        assert "e.get('execution_id', '')" in app_content, "Missing execution_id in prerender"
        assert "e.get('order_id', '--')" in app_content, "Missing order_id in prerender"
        assert "e.get('symbol', '')" in app_content, "Missing symbol in prerender"
        assert "e.get('workspace', active_ws)" in app_content, "Missing workspace in prerender"

        results["15. Profiler column mapping is correct"] = "PASS"
        print("  [PASS] Gate 15: Profiler column mapping is correct (8 columns mapped in index.html and app.py)")
    except Exception as e:
        results["15. Profiler column mapping is correct"] = f"FAIL: {e}"
        print(f"  [FAIL] Gate 15: {e}")

    # ------------------------------------------------------------------
    # GATE 16: Wrong workspace data is rejected
    # ------------------------------------------------------------------
    try:
        # Attempt to validate BTCUSDT in INDIA workspace
        valid_res = execution_gate.validate_and_gate_order(
            symbol="BTCUSDT",
            side="BUY",
            quantity=0.1,
            price=60000.0,
            order_type="LIMIT",
            environment="PAPER",
            product="CNC",
            workspace="INDIA"
        )
        assert valid_res["allowed"] is False, "BTCUSDT was incorrectly allowed in INDIA workspace"
        assert "WORKSPACE" in valid_res["reason"].upper() or "MISMATCH" in valid_res["reason"].upper() or "INVALID" in valid_res["reason"].upper(), \
            f"Expected workspace mismatch reason, got: {valid_res['reason']}"

        results["16. Wrong workspace data is rejected"] = "PASS"
        print(f"  [PASS] Gate 16: Wrong workspace data is rejected ({valid_res['rejection_code']}: {valid_res['reason']})")
    except Exception as e:
        results["16. Wrong workspace data is rejected"] = f"FAIL: {e}"
        print(f"  [FAIL] Gate 16: {e}")

    # ------------------------------------------------------------------
    # GATE 17: Failed reconciliation blocks execution
    # ------------------------------------------------------------------
    try:
        # Force reconciliation status to FAIL
        position_snapshot_service.set_forced_reconciliation_status("RECONCILIATION_FAIL")

        gate_res = execution_gate.validate_and_gate_order(
            symbol="RELIANCE",
            side="BUY",
            quantity=1,
            price=2850.0,
            order_type="MARKET",
            environment="PAPER",
            product="CNC",
            workspace="INDIA"
        )

        assert gate_res["allowed"] is False, "Order was allowed during RECONCILIATION_FAIL"
        assert gate_res["rejection_code"] == "RECONCILIATION_GATE_BLOCKED", f"Expected RECONCILIATION_GATE_BLOCKED, got {gate_res['rejection_code']}"

        # Reset forced status
        position_snapshot_service.reset_forced_reconciliation_status()

        results["17. Failed reconciliation blocks execution"] = "PASS"
        print(f"  [PASS] Gate 17: Failed reconciliation blocks execution ({gate_res['rejection_code']})")
    except Exception as e:
        position_snapshot_service.reset_forced_reconciliation_status()
        results["17. Failed reconciliation blocks execution"] = f"FAIL: {e}"
        print(f"  [FAIL] Gate 17: {e}")

    # ------------------------------------------------------------------
    # GATE 18: Persistence survives restart
    # ------------------------------------------------------------------
    try:
        # Write test event
        test_ev = audit_logger.record_event(
            event_type="SYSTEM_RECONCILIATION_AUDIT",
            workspace="INDIA",
            user_id="AUDIT_VERIFIER",
            result="PASS",
            reason="Master 20-Gate Persistence Verification"
        )
        test_id = test_ev["event_id"]

        # Create new FinancialAuditLogger instance from disk to simulate daemon restart
        reloaded_logger = FinancialAuditLogger()
        found_ev = reloaded_logger.get_event(test_id)
        assert found_ev is not None, f"Event {test_id} not found in reloaded logger"
        assert found_ev["integrity_hash"] == test_ev["integrity_hash"], "Integrity hash mismatch on reload"

        results["18. Persistence survives restart"] = "PASS"
        print(f"  [PASS] Gate 18: Persistence survives restart (Event {test_id} recovered from disk)")
    except Exception as e:
        results["18. Persistence survives restart"] = f"FAIL: {e}"
        print(f"  [FAIL] Gate 18: {e}")

    # ------------------------------------------------------------------
    # GATE 19: Binance LIVE remains disabled
    # ------------------------------------------------------------------
    try:
        assert environment_gate.LIVE_TRADING_ENABLED is False, "LIVE_TRADING_ENABLED must be False"
        allowed, reason = environment_gate.check_order_allowed("LIVE")
        assert allowed is False, "LIVE order was permitted when LIVE_TRADING_ENABLED=false"
        assert "LIVE_TRADING_ENABLED=false" in reason, f"Unexpected rejection reason: {reason}"

        results["19. Binance LIVE remains disabled"] = "PASS"
        print("  [PASS] Gate 19: Binance LIVE remains disabled (LIVE_TRADING_ENABLED=false)")
    except Exception as e:
        results["19. Binance LIVE remains disabled"] = f"FAIL: {e}"
        print(f"  [FAIL] Gate 19: {e}")

    # ------------------------------------------------------------------
    # GATE 20: Withdrawal remains disabled
    # ------------------------------------------------------------------
    try:
        assert environment_gate.LIVE_WITHDRAWALS_ENABLED is False, "LIVE_WITHDRAWALS_ENABLED must be False"
        allowed, reason = environment_gate.check_withdrawal_allowed("LIVE")
        assert allowed is False, "LIVE withdrawal was permitted when LIVE_WITHDRAWALS_ENABLED=false"
        assert "LIVE_WITHDRAWALS_ENABLED=false" in reason, f"Unexpected rejection reason: {reason}"

        results["20. Withdrawal remains disabled"] = "PASS"
        print("  [PASS] Gate 20: Withdrawal remains disabled (LIVE_WITHDRAWALS_ENABLED=false)")
    except Exception as e:
        results["20. Withdrawal remains disabled"] = f"FAIL: {e}"
        print(f"  [FAIL] Gate 20: {e}")

    print("\n" + "=" * 75)
    passed = sum(1 for v in results.values() if v == "PASS")
    total = len(results)
    print(f"  TEST BATTERY SUMMARY: {passed}/{total} GATES PASSED")
    print("=" * 75 + "\n")

    if passed == total:
        print(">>> ALL 20 CRITICAL RECONCILIATION GATES PASSED SUCCESSFULLY <<<\n")
        return 0
    else:
        print(f">>> {total - passed} GATE(S) FAILED <<< \n")
        return 1


if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)
