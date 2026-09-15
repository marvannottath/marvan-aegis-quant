"""
AEGIS QUANT — THREE-WORKSPACE FINAL FORENSIC AUDIT & RECONCILIATION TEST SUITE
Exhaustively verifies all 31 categories from Section 23:
  1.  Workspace isolation
  2.  Currency isolation
  3.  Position isolation
  4.  Order isolation
  5.  PnL isolation
  6.  Ledger isolation
  7.  AI signal isolation
  8.  Scanner isolation
  9.  Risk isolation
  10. Backtest isolation
  11. Trade log consistency
  12. Broker reconciliation
  13. Portfolio reconciliation
  14. Dashboard aggregation
  15. Execution schema mapping
  16. Profiler integrity
  17. Audit event generation
  18. Persistence after reload
  19. Persistence after restart
  20. Unresolved symbol blocks order
  21. Stale market data blocks order
  22. Wrong workspace blocks order
  23. Wrong currency blocks order
  24. Wrong instrument blocks order
  25. Excessive exposure blocks order
  26. Loss-limit breach blocks order
  27. Drawdown breach blocks order
  28. Kill switch blocks order
  29. News-policy unresolved state follows fail-safe rule
  30. Binance LIVE remains disabled
  31. Withdrawals remain disabled
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
from core.kill_switch import emergency_kill_switch
from core.execution_latency_profiler import execution_latency_profiler
from core.audit_logger import audit_logger, FinancialAuditLogger
from core.double_entry_ledger import double_entry_ledger, DoubleEntryLedger
from core.order_state_machine import order_state_machine, OrderStateMachine
from core.withdrawal_state_machine import withdrawal_state_machine
from core.backtest_analytics_engine import backtest_analytics_engine
from core.multi_market_scanner import multi_scanner
from core.macro_news_engine import macro_engine
from execution.paper_broker import paper_broker
from dashboard.app import (
    app,
    get_state,
    get_position_snapshot,
    get_portfolio_aggregate_endpoint
)


def run_31_point_audit():
    print("\n" + "=" * 80)
    print("  AEGIS QUANT — THREE-WORKSPACE FINAL FORENSIC AUDIT (31 CATEGORIES)")
    print("=" * 80 + "\n")

    results = {}

    # ------------------------------------------------------------------
    # 1. WORKSPACE ISOLATION
    # ------------------------------------------------------------------
    try:
        india_symbols = workspace_manager.get_workspace_meta("INDIA")["instruments"]
        forex_symbols = workspace_manager.get_workspace_meta("FOREX_GOLD")["instruments"]
        crypto_symbols = workspace_manager.get_workspace_meta("CRYPTO")["instruments"]

        # Zero symbol overlap across all three workspaces
        india_forex_overlap = set(india_symbols) & set(forex_symbols)
        india_crypto_overlap = set(india_symbols) & set(crypto_symbols)
        forex_crypto_overlap = set(forex_symbols) & set(crypto_symbols)

        assert len(india_forex_overlap) == 0, f"India-Forex overlap detected: {india_forex_overlap}"
        assert len(india_crypto_overlap) == 0, f"India-Crypto overlap detected: {india_crypto_overlap}"
        assert len(forex_crypto_overlap) == 0, f"Forex-Crypto overlap detected: {forex_crypto_overlap}"

        # Switching workspace switches paper broker pool deterministically
        paper_broker.switch_pool("AEGIS_INDIA_INR")
        assert paper_broker.active_pool_name == "AEGIS_INDIA_INR"
        paper_broker.switch_pool("AEGIS_QUANT_MASTER")
        assert paper_broker.active_pool_name == "AEGIS_QUANT_MASTER"
        paper_broker.switch_pool("BINANCE_TESTNET_DEMO")
        assert paper_broker.active_pool_name == "BINANCE_TESTNET_DEMO"

        results["1. Workspace isolation"] = "PASS"
        print("  [PASS] 1. Workspace isolation (0 symbol overlap, pool switches strictly verified)")
    except Exception as e:
        results["1. Workspace isolation"] = f"FAIL: {e}"
        print(f"  [FAIL] 1. Workspace isolation: {e}")

    # ------------------------------------------------------------------
    # 2. CURRENCY ISOLATION
    # ------------------------------------------------------------------
    try:
        m_india = workspace_manager.get_workspace_meta("INDIA")
        m_forex = workspace_manager.get_workspace_meta("FOREX_GOLD")
        m_crypto = workspace_manager.get_workspace_meta("CRYPTO")

        assert m_india["currency"] == "INR" and m_india["currency_symbol"] == "₹"
        assert m_forex["currency"] == "USD" and m_forex["currency_symbol"] == "$"
        assert m_crypto["currency"] == "USDT" and m_crypto["currency_symbol"] == "$"

        # Mismatched currency rejected by execution gate
        ok_inr_in_fx, code, _, _ = execution_gate.validate_order(
            symbol="EURUSD", side="BUY", quantity=1000, price=1.08,
            workspace="FOREX_GOLD", currency="INR", data_age_seconds=0.1
        )
        assert not ok_inr_in_fx and code == "CURRENCY_MISMATCH"

        ok_usd_in_in, code2, _, _ = execution_gate.validate_order(
            symbol="RELIANCE", side="BUY", quantity=10, price=2850.0,
            workspace="INDIA", currency="USD", data_age_seconds=0.1
        )
        assert not ok_usd_in_in and code2 == "CURRENCY_MISMATCH"

        results["2. Currency isolation"] = "PASS"
        print("  [PASS] 2. Currency isolation (INR ₹ vs USD $ vs USDT $, cross-currency rejected)")
    except Exception as e:
        results["2. Currency isolation"] = f"FAIL: {e}"
        print(f"  [FAIL] 2. Currency isolation: {e}")

    # ------------------------------------------------------------------
    # 3. POSITION ISOLATION
    # ------------------------------------------------------------------
    try:
        snap_in = position_snapshot_service.get_snapshot("INDIA")
        snap_fx = position_snapshot_service.get_snapshot("FOREX_GOLD")
        snap_cr = position_snapshot_service.get_snapshot("CRYPTO")

        # Verify no cross-workspace positions contaminated
        for p in snap_in.get("positions", []):
            assert workspace_manager.is_symbol_allowed(p["symbol"], "INDIA"), f"Non-India symbol in India positions: {p['symbol']}"
        for p in snap_fx.get("positions", []):
            assert workspace_manager.is_symbol_allowed(p["symbol"], "FOREX_GOLD"), f"Non-Forex symbol in Forex positions: {p['symbol']}"
        for p in snap_cr.get("positions", []):
            assert workspace_manager.is_symbol_allowed(p["symbol"], "CRYPTO"), f"Non-Crypto symbol in Crypto positions: {p['symbol']}"

        results["3. Position isolation"] = "PASS"
        print("  [PASS] 3. Position isolation (0 cross-workspace position contamination)")
    except Exception as e:
        results["3. Position isolation"] = f"FAIL: {e}"
        print(f"  [FAIL] 3. Position isolation: {e}")

    # ------------------------------------------------------------------
    # 4. ORDER ISOLATION
    # ------------------------------------------------------------------
    try:
        orders = list(order_state_machine.orders.values())
        india_orders = [o for o in orders if workspace_manager.is_symbol_allowed(o.get("symbol", ""), "INDIA")]
        forex_orders = [o for o in orders if workspace_manager.is_symbol_allowed(o.get("symbol", ""), "FOREX_GOLD")]
        crypto_orders = [o for o in orders if workspace_manager.is_symbol_allowed(o.get("symbol", ""), "CRYPTO")]

        # Ensure order scoping strictly matches workspace symbol registries
        for o in india_orders:
            assert not workspace_manager.is_symbol_allowed(o["symbol"], "CRYPTO")
            assert not workspace_manager.is_symbol_allowed(o["symbol"], "FOREX_GOLD")

        results["4. Order isolation"] = "PASS"
        print(f"  [PASS] 4. Order isolation ({len(india_orders)} IN, {len(forex_orders)} FX, {len(crypto_orders)} CR orders segregated)")
    except Exception as e:
        results["4. Order isolation"] = f"FAIL: {e}"
        print(f"  [FAIL] 4. Order isolation: {e}")

    # ------------------------------------------------------------------
    # 5. PNL ISOLATION
    # ------------------------------------------------------------------
    try:
        p_in = position_snapshot_service.get_portfolio_aggregate("INDIA")
        p_fx = position_snapshot_service.get_portfolio_aggregate("FOREX_GOLD")
        p_cr = position_snapshot_service.get_portfolio_aggregate("CRYPTO")

        assert p_in["currency"] == "INR"
        assert p_fx["currency"] == "USD"
        assert p_cr["currency"] == "USDT"

        # Unrealized PnL is computed strictly from active workspace positions
        assert p_in["unrealized_pnl"] == sum(p.get("unrealized_pnl", 0.0) for p in snap_in.get("positions", []))
        assert p_fx["unrealized_pnl"] == sum(p.get("unrealized_pnl", 0.0) for p in snap_fx.get("positions", []))
        assert p_cr["unrealized_pnl"] == sum(p.get("unrealized_pnl", 0.0) for p in snap_cr.get("positions", []))

        results["5. PnL isolation"] = "PASS"
        print("  [PASS] 5. PnL isolation (Realized and unrealized PnL isolated per pool and currency)")
    except Exception as e:
        results["5. PnL isolation"] = f"FAIL: {e}"
        print(f"  [FAIL] 5. PnL isolation: {e}")

    # ------------------------------------------------------------------
    # 6. LEDGER ISOLATION
    # ------------------------------------------------------------------
    try:
        # Check double-entry equality across all environments
        ledger_res = double_entry_ledger.verify_ledger_integrity()
        assert ledger_res.get("is_balanced") is True, f"Double-entry ledger unbalanced: {ledger_res}"
        assert ledger_res.get("total_debits") == ledger_res.get("total_credits"), "Debits != Credits"

        # Check per-pool currency tagging
        for entry in double_entry_ledger.entries:
            env = entry.get("environment", "")
            asset = entry.get("asset", "")
            if "INDIA" in env or env == "AEGIS_INDIA_INR":
                assert asset == "INR", f"Non-INR asset in India ledger entry: {entry}"
            elif "BINANCE" in env or env == "BINANCE_TESTNET_DEMO":
                assert asset in ["USDT", "BTC", "ETH", "SOL", "BNB"], f"Unexpected asset in Crypto ledger entry: {entry}"

        results["6. Ledger isolation"] = "PASS"
        print(f"  [PASS] 6. Ledger isolation ({len(double_entry_ledger.entries)} entries balanced: Debits == Credits)")
    except Exception as e:
        results["6. Ledger isolation"] = f"FAIL: {e}"
        print(f"  [FAIL] 6. Ledger isolation: {e}")

    # ------------------------------------------------------------------
    # 7. AI SIGNAL ISOLATION
    # ------------------------------------------------------------------
    try:
        loop = asyncio.get_event_loop()
        state_in = loop.run_until_complete(get_state("INDIA"))
        state_cr = loop.run_until_complete(get_state("CRYPTO"))

        opps_in = state_in.get("ai_opportunities", [])
        opps_cr = state_cr.get("ai_opportunities", [])

        # India opportunities must only contain allowable India symbols
        for opp in opps_in:
            sym = opp.get("symbol")
            if sym not in ("DATA UNAVAILABLE", "NO DATA AVAILABLE", "UNKNOWN"):
                assert workspace_manager.is_symbol_allowed(sym, "INDIA"), f"Non-India symbol in India AI signals: {sym}"
                assert opp.get("instrument_id", "").startswith("NSE"), f"Invalid instrument ID for India: {opp.get('instrument_id')}"
                assert opp.get("exchange") == "NSE"

        # Crypto opportunities must only contain allowable Crypto symbols
        for opp in opps_cr:
            sym = opp.get("symbol")
            if sym not in ("DATA UNAVAILABLE", "NO DATA AVAILABLE", "UNKNOWN"):
                assert workspace_manager.is_symbol_allowed(sym, "CRYPTO"), f"Non-Crypto symbol in Crypto AI signals: {sym}"
                assert opp.get("instrument_id", "").startswith("BINANCE"), f"Invalid instrument ID for Crypto: {opp.get('instrument_id')}"
                assert opp.get("exchange") == "BINANCE"

        results["7. AI signal isolation"] = "PASS"
        print("  [PASS] 7. AI signal isolation (All signals carry valid symbol, instrument_id, and exchange)")
    except Exception as e:
        results["7. AI signal isolation"] = f"FAIL: {e}"
        print(f"  [FAIL] 7. AI signal isolation: {e}")

    # ------------------------------------------------------------------
    # 8. SCANNER ISOLATION
    # ------------------------------------------------------------------
    try:
        scanner_in = multi_scanner.scan_markets("INDIA")
        scanner_cr = multi_scanner.scan_markets("CRYPTO")
        scanner_fx = multi_scanner.scan_markets("FOREX_GOLD")

        for item in scanner_in:
            sym = item.get("symbol") or item.get("ticker", "")
            assert workspace_manager.is_symbol_allowed(sym, "INDIA"), f"Non-India symbol in India scanner: {sym}"
        for item in scanner_cr:
            sym = item.get("symbol") or item.get("ticker", "")
            assert workspace_manager.is_symbol_allowed(sym, "CRYPTO"), f"Non-Crypto symbol in Crypto scanner: {sym}"
        for item in scanner_fx:
            sym = item.get("symbol") or item.get("ticker", "")
            assert workspace_manager.is_symbol_allowed(sym, "FOREX_GOLD"), f"Non-Forex symbol in Forex scanner: {sym}"

        results["8. Scanner isolation"] = "PASS"
        print("  [PASS] 8. Scanner isolation (100% strict symbol containment per workspace)")
    except Exception as e:
        results["8. Scanner isolation"] = f"FAIL: {e}"
        print(f"  [FAIL] 8. Scanner isolation: {e}")

    # ------------------------------------------------------------------
    # 9. RISK ISOLATION
    # ------------------------------------------------------------------
    try:
        # SEBI 5x leverage cap check for Indian Equities
        ok_sebi, code_sebi, _, _ = execution_gate.validate_order(
            symbol="RELIANCE", side="BUY", quantity=10, price=2500.0,
            workspace="INDIA", currency="INR", leverage=10.0, data_age_seconds=0.1
        )
        assert not ok_sebi and ("LEVERAGE" in code_sebi or "SEBI" in code_sebi), f"Expected SEBI leverage rejection, got {code_sebi}"

        # 5x intraday peak leverage is legally permissible under SEBI rules
        orig_prof = risk_engine.active_profile_name
        risk_engine.set_risk_profile("AGGRESSIVE")
        ok_5x, code_5x, reason_5x, _ = execution_gate.validate_order(
            symbol="RELIANCE", side="BUY", quantity=1, price=2500.0,
            workspace="INDIA", currency="INR", leverage=5.0, data_age_seconds=0.1
        )
        risk_engine.set_risk_profile(orig_prof)
        assert ok_5x, f"SEBI 5x legal leverage was rejected: {code_5x} - {reason_5x}"

        results["9. Risk isolation"] = "PASS"
        print("  [PASS] 9. Risk isolation (SEBI 5x cap enforced for India; >5x rejected with SEBI/LEVERAGE)")
    except Exception as e:
        results["9. Risk isolation"] = f"FAIL: {e}"
        print(f"  [FAIL] 9. Risk isolation: {e}")

    # ------------------------------------------------------------------
    # 10. BACKTEST ISOLATION
    # ------------------------------------------------------------------
    try:
        runs = backtest_analytics_engine.list_backtest_runs()
        assert len(runs) > 0, "No backtest runs found"

        for r in runs:
            ws = r.get("workspace")
            cur = r.get("currency")
            venue = r.get("venue")
            if ws == "INDIA":
                assert cur == "INR", f"India backtest currency mismatch: {cur}"
                assert "NSE" in venue or "BSE" in venue, f"India backtest venue mismatch: {venue}"
            elif ws == "CRYPTO":
                assert cur in ["USDT", "USD"], f"Crypto backtest currency mismatch: {cur}"
                assert "BINANCE" in venue.upper(), f"Crypto backtest venue mismatch: {venue}"
            elif ws == "FOREX_GOLD":
                assert cur == "USD", f"Forex backtest currency mismatch: {cur}"

        results["10. Backtest isolation"] = "PASS"
        print(f"  [PASS] 10. Backtest isolation ({len(runs)} backtest runs segregated with matching venue/currency)")
    except Exception as e:
        results["10. Backtest isolation"] = f"FAIL: {e}"
        print(f"  [FAIL] 10. Backtest isolation: {e}")

    # ------------------------------------------------------------------
    # 11. TRADE LOG CONSISTENCY
    # ------------------------------------------------------------------
    try:
        bt_path = ROOT_DIR / "data" / "backtest_latest_run.json"
        assert bt_path.exists(), "backtest_latest_run.json missing"
        with open(bt_path, "r") as f:
            bt_data = json.load(f)

        trades = bt_data.get("trade_history") or bt_data.get("trades", [])
        tot_trades = int(bt_data.get("total_trades", len(trades)))
        assert tot_trades == len(trades), f"Reported total_trades ({tot_trades}) != actual trades length ({len(trades)})"

        init_cap = float(bt_data.get("initial_capital", 100000.0))
        final_cap = float(bt_data.get("final_capital") or bt_data.get("final_equity", init_cap))
        sum_pnl = sum(float(t.get("net_pnl", 0.0)) for t in trades)
        assert abs(init_cap + sum_pnl - final_cap) < 1.0, f"PnL sum mismatch: {init_cap} + {sum_pnl} != {final_cap}"

        # Missing trade log cannot return RECONCILIATION_OK
        incomplete_res = backtest_analytics_engine._verify_integrity({"trade_history": []})
        assert incomplete_res["status"] == "INCOMPLETE"

        results["11. Trade log consistency"] = "PASS"
        print(f"  [PASS] 11. Trade log consistency (All {len(trades)} trades sum mathematically to final capital)")
    except Exception as e:
        results["11. Trade log consistency"] = f"FAIL: {e}"
        print(f"  [FAIL] 11. Trade log consistency: {e}")

    # ------------------------------------------------------------------
    # 12. BROKER RECONCILIATION
    # ------------------------------------------------------------------
    try:
        for ws in ["INDIA", "FOREX_GOLD", "CRYPTO"]:
            snap = position_snapshot_service.get_snapshot(ws)
            assert snap["broker_sync"] == "SYNCED", f"{ws} broker_sync not SYNCED"
            assert snap["reconciliation_status"] == "RECONCILIATION_OK", f"{ws} reconciliation_status not OK"
            assert snap["delta_detected"] is False

        # Injected delta triggers fail-closed response
        position_snapshot_service.inject_position_delta("INDIA", [{"symbol": "TCS", "units": 10, "entry_price": 4200.0}])
        snap_delta = position_snapshot_service.get_snapshot("INDIA")
        assert snap_delta["delta_detected"] is True
        assert snap_delta["reconciliation_status"] == "RECONCILIATION_FAIL"
        position_snapshot_service.clear_injected_delta("INDIA")

        results["12. Broker reconciliation"] = "PASS"
        print("  [PASS] 12. Broker reconciliation (SYNCED across all 3; delta detection verified)")
    except Exception as e:
        position_snapshot_service.clear_injected_delta("INDIA")
        results["12. Broker reconciliation"] = f"FAIL: {e}"
        print(f"  [FAIL] 12. Broker reconciliation: {e}")

    # ------------------------------------------------------------------
    # 13. PORTFOLIO RECONCILIATION
    # ------------------------------------------------------------------
    try:
        for ws in ["INDIA", "FOREX_GOLD", "CRYPTO"]:
            agg = position_snapshot_service.get_portfolio_aggregate(ws)
            # Cash + Used Margin + Unrealized PnL + Vault Balance == Total Equity
            computed_eq = round(agg["free_cash"] + agg["used_margin"] + agg["unrealized_pnl"] + agg.get("vault_balance", 0.0), 2)
            assert abs(computed_eq - agg["total_equity"]) < 0.05, f"{ws} equity equation mismatch: {computed_eq} vs {agg['total_equity']}"
            assert agg["available_margin"] == max(0.0, agg["free_cash"])

        results["13. Portfolio reconciliation"] = "PASS"
        print("  [PASS] 13. Portfolio reconciliation (Cash + Margin + PnL + Vault == Total Equity across all 3)")
    except Exception as e:
        results["13. Portfolio reconciliation"] = f"FAIL: {e}"
        print(f"  [FAIL] 13. Portfolio reconciliation: {e}")

    # ------------------------------------------------------------------
    # 14. DASHBOARD AGGREGATION
    # ------------------------------------------------------------------
    try:
        loop = asyncio.get_event_loop()
        state_data = loop.run_until_complete(get_state("INDIA"))

        agg = position_snapshot_service.get_portfolio_aggregate("INDIA")
        assert state_data["portfolio_equity"] == agg["total_equity"]
        assert state_data["virtual_cash"] == agg["free_cash"]
        assert state_data["open_positions_count"] == agg["open_positions"]
        assert state_data["total_exposure"] == agg["total_exposure"]

        # Check explicit /api/portfolio endpoint
        port_resp = loop.run_until_complete(get_portfolio_aggregate_endpoint("INDIA"))
        port_data = json.loads(port_resp.body.decode("utf-8"))
        assert port_data["total_equity"] == agg["total_equity"]

        results["14. Dashboard aggregation"] = "PASS"
        print("  [PASS] 14. Dashboard aggregation (Top cards derive directly from authoritative aggregate)")
    except Exception as e:
        results["14. Dashboard aggregation"] = f"FAIL: {e}"
        print(f"  [FAIL] 14. Dashboard aggregation: {e}")

    # ------------------------------------------------------------------
    # 15. EXECUTION SCHEMA MAPPING
    # ------------------------------------------------------------------
    try:
        template_file = ROOT_DIR / "dashboard" / "templates" / "index.html"
        content = template_file.read_text(encoding="utf-8")

        expected_headers = [
            "Timestamp", "Execution ID", "Order ID", "Symbol",
            "Workspace", "Result", "Total Latency", "Risk Gate"
        ]
        for h in expected_headers:
            assert h in content, f"Execution table header '{h}' missing from index.html"

        results["15. Execution schema mapping"] = "PASS"
        print("  [PASS] 15. Execution schema mapping (All 8 columns mapped and verified)")
    except Exception as e:
        results["15. Execution schema mapping"] = f"FAIL: {e}"
        print(f"  [FAIL] 15. Execution schema mapping: {e}")

    # ------------------------------------------------------------------
    # 16. PROFILER INTEGRITY
    # ------------------------------------------------------------------
    try:
        # Check that unmeasured stages report NOT MEASURED with avg_duration_ms=None
        unmeasured = execution_latency_profiler.get_summary(workspace="UNMEASURED_TEST_VENUE")
        for stage in unmeasured.get("stage_averages", []):
            if stage["status"] == "NOT MEASURED":
                assert stage["avg_duration_ms"] is None, f"Fake duration found in unmeasured stage: {stage}"

        # Check 4 canonical segregated scopes
        scopes = execution_latency_profiler.CANONICAL_TIMING_SCOPES
        assert "END-TO-END EXECUTION" in scopes
        assert "ORDER SUBMISSION" in scopes
        assert "EXCHANGE / FILL" in scopes
        assert "LEDGER WRITE" in scopes

        results["16. Profiler integrity"] = "PASS"
        print("  [PASS] 16. Profiler integrity (4 canonical scopes; unmeasured stages report None, 0 fake 0.0ms)")
    except Exception as e:
        results["16. Profiler integrity"] = f"FAIL: {e}"
        print(f"  [FAIL] 16. Profiler integrity: {e}")

    # ------------------------------------------------------------------
    # 17. AUDIT EVENT GENERATION
    # ------------------------------------------------------------------
    try:
        evt = audit_logger.log_event(
            event_type="FORENSIC_AUDIT_CHECK",
            symbol="RELIANCE",
            workspace="INDIA",
            environment="AEGIS_INDIA_INR",
            result="PASS",
            reason="31-point forensic audit test execution"
        )
        assert evt.get("integrity_hash"), "Audit event missing SHA-256 integrity hash"
        assert len(evt["integrity_hash"]) == 64, "Invalid SHA-256 hash length"

        results["17. Audit event generation"] = "PASS"
        print("  [PASS] 17. Audit event generation (SHA-256 integrity hash generated and verified)")
    except Exception as e:
        results["17. Audit event generation"] = f"FAIL: {e}"
        print(f"  [FAIL] 17. Audit event generation: {e}")

    # ------------------------------------------------------------------
    # 18. PERSISTENCE AFTER RELOAD
    # ------------------------------------------------------------------
    try:
        count_before = len(order_state_machine.orders)
        order_state_machine._load()
        count_after = len(order_state_machine.orders)
        assert count_before == count_after, f"Order reload mismatch: {count_before} vs {count_after}"

        audit_before = len(audit_logger.logs)
        audit_logger._load_logs()
        audit_after = len(audit_logger.logs)
        assert audit_before == audit_after, f"Audit reload mismatch: {audit_before} vs {audit_after}"

        results["18. Persistence after reload"] = "PASS"
        print(f"  [PASS] 18. Persistence after reload ({count_after} orders and {audit_after} audit records restored)")
    except Exception as e:
        results["18. Persistence after reload"] = f"FAIL: {e}"
        print(f"  [FAIL] 18. Persistence after reload: {e}")

    # ------------------------------------------------------------------
    # 19. PERSISTENCE AFTER RESTART
    # ------------------------------------------------------------------
    try:
        fresh_osm = OrderStateMachine()
        fresh_audit = FinancialAuditLogger()
        fresh_ledger = DoubleEntryLedger()

        assert len(fresh_osm.orders) == len(order_state_machine.orders)
        assert len(fresh_audit.logs) == len(audit_logger.logs)
        assert len(fresh_ledger.entries) == len(double_entry_ledger.entries)

        results["19. Persistence after restart"] = "PASS"
        print("  [PASS] 19. Persistence after restart (Fresh class instances reload identical data from disk)")
    except Exception as e:
        results["19. Persistence after restart"] = f"FAIL: {e}"
        print(f"  [FAIL] 19. Persistence after restart: {e}")

    # ------------------------------------------------------------------
    # 20. UNRESOLVED SYMBOL BLOCKS ORDER
    # ------------------------------------------------------------------
    try:
        ok, code, reason, _ = execution_gate.validate_order(
            symbol="DATA UNAVAILABLE", side="BUY", quantity=10, price=100.0, workspace="INDIA", data_age_seconds=0.1
        )
        assert not ok and code == "SYMBOL_UNRESOLVED", f"Expected SYMBOL_UNRESOLVED, got {code}"

        results["20. Unresolved symbol blocks order"] = "PASS"
        print("  [PASS] 20. Unresolved symbol blocks order (Rejects unresolvable symbols with SYMBOL_UNRESOLVED)")
    except Exception as e:
        results["20. Unresolved symbol blocks order"] = f"FAIL: {e}"
        print(f"  [FAIL] 20. Unresolved symbol blocks order: {e}")

    # ------------------------------------------------------------------
    # 21. STALE MARKET DATA BLOCKS ORDER
    # ------------------------------------------------------------------
    try:
        ok, code, reason, _ = execution_gate.validate_order(
            symbol="RELIANCE", side="BUY", quantity=1, price=2500.0,
            data_age_seconds=12.5, workspace="INDIA"
        )
        assert not ok and code == "STALE_MARKET_DATA", f"Expected STALE_MARKET_DATA, got {code}"

        results["21. Stale market data blocks order"] = "PASS"
        print("  [PASS] 21. Stale market data blocks order (Rejects data age > 5.0s with STALE_MARKET_DATA)")
    except Exception as e:
        results["21. Stale market data blocks order"] = f"FAIL: {e}"
        print(f"  [FAIL] 21. Stale market data blocks order: {e}")

    # ------------------------------------------------------------------
    # 22. WRONG WORKSPACE BLOCKS ORDER
    # ------------------------------------------------------------------
    try:
        # BTCUSDT in INDIA workspace
        ok_cr, code_cr, _, _ = execution_gate.validate_order(
            symbol="BTCUSDT", side="BUY", quantity=0.1, price=60000.0, workspace="INDIA", data_age_seconds=0.1
        )
        assert not ok_cr and code_cr == "WORKSPACE_ASSET_MISMATCH"

        # RELIANCE in CRYPTO workspace
        ok_in, code_in, _, _ = execution_gate.validate_order(
            symbol="RELIANCE", side="BUY", quantity=10, price=2500.0, workspace="CRYPTO", data_age_seconds=0.1
        )
        assert not ok_in and code_in == "WORKSPACE_ASSET_MISMATCH"

        results["22. Wrong workspace blocks order"] = "PASS"
        print("  [PASS] 22. Wrong workspace blocks order (Cross-workspace orders rejected with WORKSPACE_ASSET_MISMATCH)")
    except Exception as e:
        results["22. Wrong workspace blocks order"] = f"FAIL: {e}"
        print(f"  [FAIL] 22. Wrong workspace blocks order: {e}")

    # ------------------------------------------------------------------
    # 23. WRONG CURRENCY BLOCKS ORDER
    # ------------------------------------------------------------------
    try:
        ok, code, reason, _ = execution_gate.validate_order(
            symbol="RELIANCE", side="BUY", quantity=5, price=2500.0,
            currency="USD", workspace="INDIA", data_age_seconds=0.1
        )
        assert not ok and code == "CURRENCY_MISMATCH"

        results["23. Wrong currency blocks order"] = "PASS"
        print("  [PASS] 23. Wrong currency blocks order (USD in INDIA rejected with CURRENCY_MISMATCH)")
    except Exception as e:
        results["23. Wrong currency blocks order"] = f"FAIL: {e}"
        print(f"  [FAIL] 23. Wrong currency blocks order: {e}")

    # ------------------------------------------------------------------
    # 24. WRONG INSTRUMENT BLOCKS ORDER
    # ------------------------------------------------------------------
    try:
        ok, code, reason, _ = execution_gate.validate_order(
            symbol="", side="BUY", quantity=5, price=100.0, workspace="INDIA", data_age_seconds=0.1
        )
        assert not ok and code in ["SYMBOL_UNRESOLVED", "MISSING_INSTRUMENT_ID"]

        results["24. Wrong instrument blocks order"] = "PASS"
        print("  [PASS] 24. Wrong instrument blocks order (Empty or invalid instrument blocked fail-closed)")
    except Exception as e:
        results["24. Wrong instrument blocks order"] = f"FAIL: {e}"
        print(f"  [FAIL] 24. Wrong instrument blocks order: {e}")

    # ------------------------------------------------------------------
    # 25. EXCESSIVE EXPOSURE BLOCKS ORDER
    # ------------------------------------------------------------------
    try:
        ok_exp, code_exp, reason_exp, _ = execution_gate.validate_order(
            symbol="RELIANCE", side="BUY", quantity=1000000, price=2500.0,
            workspace="INDIA", currency="INR", data_age_seconds=0.1
        )
        assert not ok_exp and ("EXPOSURE" in code_exp or "CAP" in code_exp or "RISK" in code_exp or "LEVERAGE" in code_exp)

        results["25. Excessive exposure blocks order"] = "PASS"
        print("  [PASS] 25. Excessive exposure blocks order (Massive exposure rejected by risk gate)")
    except Exception as e:
        results["25. Excessive exposure blocks order"] = f"FAIL: {e}"
        print(f"  [FAIL] 25. Excessive exposure blocks order: {e}")

    # ------------------------------------------------------------------
    # 26. LOSS-LIMIT BREACH BLOCKS ORDER
    # ------------------------------------------------------------------
    try:
        orig_loss = risk_engine.daily_realized_loss
        risk_engine.daily_realized_loss = 6000.0  # limit is 2000.0
        passed, code, msg = risk_engine.validate_order_pipeline(
            amount_usd=100.0, leverage=1.0, current_open_positions=0, available_cash=10000.0
        )
        risk_engine.daily_realized_loss = orig_loss
        assert not passed and "DAILY_LOSS" in code

        results["26. Loss-limit breach blocks order"] = "PASS"
        print(f"  [PASS] 26. Loss-limit breach blocks order (Daily loss limit breach triggers {code})")
    except Exception as e:
        risk_engine.daily_realized_loss = 0.0
        results["26. Loss-limit breach blocks order"] = f"FAIL: {e}"
        print(f"  [FAIL] 26. Loss-limit breach blocks order: {e}")

    # ------------------------------------------------------------------
    # 27. DRAWDOWN BREACH BLOCKS ORDER
    # ------------------------------------------------------------------
    try:
        risk_engine.circuit_tripped = True
        risk_engine.trip_reason = "15% portfolio drawdown circuit breaker tripped"
        passed, code, msg = risk_engine.validate_order_pipeline(
            amount_usd=100.0, leverage=1.0, current_open_positions=0, available_cash=10000.0
        )
        risk_engine.circuit_tripped = False
        risk_engine.trip_reason = ""
        assert not passed and "DRAWDOWN" in code

        results["27. Drawdown breach blocks order"] = "PASS"
        print(f"  [PASS] 27. Drawdown breach blocks order (Drawdown circuit breaker trips with {code})")
    except Exception as e:
        risk_engine.circuit_tripped = False
        risk_engine.trip_reason = ""
        results["27. Drawdown breach blocks order"] = f"FAIL: {e}"
        print(f"  [FAIL] 27. Drawdown breach blocks order: {e}")

    # ------------------------------------------------------------------
    # 28. KILL SWITCH BLOCKS ORDER
    # ------------------------------------------------------------------
    try:
        emergency_kill_switch.activate(reason="Forensic Audit Test Trigger", initiated_by="AUDIT_TEST")

        ok, code, reason, _ = execution_gate.validate_order(
            symbol="RELIANCE", side="BUY", quantity=1, price=2500.0, workspace="INDIA", data_age_seconds=0.1
        )
        assert not ok and code == "KILL_SWITCH_ACTIVE", f"Expected KILL_SWITCH_ACTIVE, got {code}"

        emergency_kill_switch.deactivate(deactivated_by="AUDIT_TEST")
        assert not emergency_kill_switch.is_activated

        results["28. Kill switch blocks order"] = "PASS"
        print("  [PASS] 28. Kill switch blocks order (KILL_SWITCH_ACTIVE blocks orders fail-closed)")
    except Exception as e:
        emergency_kill_switch.deactivate(deactivated_by="Cleanup")
        results["28. Kill switch blocks order"] = f"FAIL: {e}"
        print(f"  [FAIL] 28. Kill switch blocks order: {e}")

    # ------------------------------------------------------------------
    # 29. NEWS-POLICY UNRESOLVED STATE FOLLOWS FAIL-SAFE RULE
    # ------------------------------------------------------------------
    try:
        news = macro_engine.get_workspace_news("INDIA")
        assert news["status"] == "NOT_CONFIGURED"
        assert "NOT CONFIGURED" in news["display_banner"]
        # Zero fake "CLEAR" status
        assert news["status"] != "CLEAR"

        results["29. News-policy unresolved state follows fail-safe rule"] = "PASS"
        print("  [PASS] 29. News-policy unresolved state follows fail-safe rule (Truthfully reports NOT_CONFIGURED)")
    except Exception as e:
        results["29. News-policy unresolved state follows fail-safe rule"] = f"FAIL: {e}"
        print(f"  [FAIL] 29. News-policy unresolved state follows fail-safe rule: {e}")

    # ------------------------------------------------------------------
    # 30. BINANCE LIVE REMAINS DISABLED
    # ------------------------------------------------------------------
    try:
        assert os.getenv("LIVE_TRADING_ENABLED", "false").lower() != "true"
        ok_live, code_live, reason_live, _ = execution_gate.validate_order(
            symbol="BTCUSDT", side="BUY", quantity=0.01, price=60000.0,
            environment="LIVE", workspace="CRYPTO", data_age_seconds=0.1
        )
        assert not ok_live and code_live in ["LIVE_TRADING_LOCKED", "LIVE_TRADING_DISABLED"]

        results["30. Binance LIVE remains disabled"] = "PASS"
        print("  [PASS] 30. Binance LIVE remains disabled (LIVE_TRADING_ENABLED=false strictly enforced)")
    except Exception as e:
        results["30. Binance LIVE remains disabled"] = f"FAIL: {e}"
        print(f"  [FAIL] 30. Binance LIVE remains disabled: {e}")

    # ------------------------------------------------------------------
    # 31. WITHDRAWALS REMAIN DISABLED
    # ------------------------------------------------------------------
    try:
        assert os.getenv("LIVE_WITHDRAWALS_ENABLED", "false").lower() != "true"
        wd_res = withdrawal_state_machine.request_withdrawal(
            user_id="USER-AUDIT", amount=100.0, asset="USDT",
            destination_address="0x1234567890abcdef1234567890abcdef12345678",
            network="TRC20", environment="LIVE"
        )
        assert wd_res["status"] == "REJECTED"
        assert "LIVE_WITHDRAWALS_ENABLED=false" in wd_res["reason"]

        results["31. Withdrawals remain disabled"] = "PASS"
        print("  [PASS] 31. Withdrawals remain disabled (LIVE_WITHDRAWALS_ENABLED=false strictly enforced)")
    except Exception as e:
        results["31. Withdrawals remain disabled"] = f"FAIL: {e}"
        print(f"  [FAIL] 31. Withdrawals remain disabled: {e}")

    # ------------------------------------------------------------------
    # SUMMARY
    # ------------------------------------------------------------------
    print("\n" + "=" * 80)
    passed_count = sum(1 for v in results.values() if v == "PASS")
    total_count = len(results)
    print(f"  TEST MATRIX SUMMARY: {passed_count}/{total_count} CATEGORIES PASSED ({(passed_count/total_count)*100:.1f}%)")
    print("=" * 80 + "\n")

    if passed_count == total_count:
        print(">>> ALL 31 FORENSIC AUDIT CATEGORIES PASSED SUCCESSFULLY <<<\n")
        return True
    else:
        failed = [k for k, v in results.items() if v != "PASS"]
        print(f">>> {len(failed)} CATEGORIES FAILED: {failed} <<<\n")
        return False


if __name__ == "__main__":
    success = run_31_point_audit()
    sys.exit(0 if success else 1)
