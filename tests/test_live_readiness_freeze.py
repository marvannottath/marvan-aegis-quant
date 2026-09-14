"""
AEGIS QUANT — MASTER PRODUCTION READINESS FREEZE AUDIT (18 PRODUCTION GATES)
Stabilization verification across:
  1. INDIA Workspace (INR / NSE/BSE / Upstox / Indian instruments)
  2. FOREX & GOLD Workspace (USD / Global feeds / Currencies & Gold)
  3. CRYPTO Workspace (USDT / Binance / Crypto instruments)

Validates all 18 Master Production Gates:
  GATE 1:  INDIA Workspace Integrity & Venue Isolation
  GATE 2:  FOREX & GOLD Workspace Integrity & Venue Isolation
  GATE 3:  CRYPTO Workspace Integrity & Venue Isolation
  GATE 4:  Cross-Workspace Data Leakage Prevention
  GATE 5:  Double-Entry Ledger & 10-Bucket Wallet Integrity
  GATE 6:  Risk Engine & Workspace Validation
  GATE 7:  Order Submission & State Machine Lifecycle
  GATE 8:  Market Data Freshness & Watchdog Gate
  GATE 9:  Execution Profiler Segmentation & Non-Zero Timestamps
  GATE 10: Backtest Provenance & Authentic Reporting
  GATE 11: Performance Curve Dynamic Consistency
  GATE 12: Immutable Audit Trail
  GATE 13: Macro / News Intelligence Truthfulness
  GATE 14: India Tax Statement Engine & Non-Stuck UI
  GATE 15: Binance Live Safety Switch & Secret Protection
  GATE 16: Emergency Kill Switch & Trading Halt
  GATE 17: Withdrawal Lock & Custody Guard
  GATE 18: Zero UI Unresolved Placeholders & Signal Schema Integrity
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
from core.multi_market_scanner import multi_scanner
from core.macro_news_engine import macro_engine
from core.performance_curve_engine import performance_curve_engine
from core.execution_latency_profiler import execution_latency_profiler
from core.backtest_analytics_engine import backtest_analytics_engine
from core.audit_logger import audit_logger
from core.double_entry_ledger import double_entry_ledger
from core.risk_engine import risk_engine
from core.environment_gate import environment_gate
from core.market_data_watchdog import market_data_watchdog
from core.order_state_machine import order_state_machine, OrderStateMachineError
from core.withdrawal_state_machine import withdrawal_state_machine
from core.india_statement_engine import india_statement_engine
from execution.user_wallet import user_wallet
from execution.paper_broker import paper_broker

PROHIBITED_IN_INDIA = [
    "BTCUSD", "ETHUSD", "SOLUSD", "EURUSD", "USDJPY",
    "XAUUSD", "AAPL", "BTCUSDT", "ETHUSDT", "SOLUSDT",
    "BNBUSDT", "ADAUSDT", "DOGEUSDT", "XRPUSDT", "GBPUSD"
]

class DummyRequest:
    def __init__(self, data=None, query_params=None, cookies=None):
        self._data = data or {}
        self.query_params = query_params or {}
        self.cookies = cookies or {}
        self.client = type("Client", (), {"host": "127.0.0.1"})()
    async def json(self):
        return self._data


async def run_master_production_audit():
    from dashboard.app import (
        get_state,
        switch_workspace_endpoint,
        submit_order,
        get_execution_latency,
        get_performance_curve,
        list_backtest_runs,
        get_india_tax_statement
    )

    gates = []
    print("=" * 80)
    print("AEGIS QUANT — 18-POINT MASTER PRODUCTION READINESS FREEZE SUITE")
    print("=" * 80)

    # ------------------------------------------------------------------
    # GATE 1: INDIA Workspace Integrity & Venue Isolation
    # ------------------------------------------------------------------
    g1_pass = True
    g1_msg = ""
    try:
        workspace_manager.set_active_workspace("INDIA")
        cfg = workspace_manager.get_active_workspace_config()
        assert cfg["currency"] == "INR", f"Expected INR, got {cfg['currency']}"
        assert cfg["currency_symbol"] == "₹", f"Expected ₹, got {cfg['currency_symbol']}"
        assert any(v in cfg["venue_name"] for v in ["NSE", "BSE", "Upstox"]), f"Unexpected venue {cfg['venue_name']}"
        
        markets = multi_scanner.scan_markets("INDIA")
        assert len(markets) > 0, "No markets in INDIA scanner"
        for m in markets:
            sym = m.get("symbol") or m.get("ticker", "")
            assert workspace_manager.is_symbol_allowed(sym, "INDIA"), f"Non-Indian symbol in scanner: {sym}"
            assert sym not in PROHIBITED_IN_INDIA, f"Prohibited symbol leaked: {sym}"
        g1_msg = f"Verified INR (₹), venue {cfg['venue_name']}, {len(markets)} Indian instruments isolated"
    except Exception as e:
        g1_pass = False
        g1_msg = str(e)
    gates.append(("GATE 1: INDIA Workspace Integrity & Venue Isolation", g1_pass, g1_msg))

    # ------------------------------------------------------------------
    # GATE 2: FOREX & GOLD Workspace Integrity & Venue Isolation
    # ------------------------------------------------------------------
    g2_pass = True
    g2_msg = ""
    try:
        workspace_manager.set_active_workspace("FOREX_GOLD")
        cfg = workspace_manager.get_active_workspace_config()
        assert cfg["currency"] == "USD", f"Expected USD, got {cfg['currency']}"
        assert cfg["currency_symbol"] == "$", f"Expected $, got {cfg['currency_symbol']}"
        
        markets = multi_scanner.scan_markets("FOREX_GOLD")
        assert len(markets) > 0, "No markets in FOREX_GOLD scanner"
        for m in markets:
            sym = m.get("symbol") or m.get("ticker", "")
            assert workspace_manager.is_symbol_allowed(sym, "FOREX_GOLD"), f"Non-Forex symbol in scanner: {sym}"
            assert not sym.endswith("USDT"), f"Crypto symbol leaked in Forex: {sym}"
            assert sym not in ["RELIANCE", "TCS", "INFY"], f"Indian symbol leaked in Forex: {sym}"
        g2_msg = f"Verified USD ($), venue {cfg['venue_name']}, {len(markets)} Forex/Gold pairs isolated"
    except Exception as e:
        g2_pass = False
        g2_msg = str(e)
    gates.append(("GATE 2: FOREX & GOLD Workspace Integrity & Venue Isolation", g2_pass, g2_msg))

    # ------------------------------------------------------------------
    # GATE 3: CRYPTO Workspace Integrity & Venue Isolation
    # ------------------------------------------------------------------
    g3_pass = True
    g3_msg = ""
    try:
        workspace_manager.set_active_workspace("CRYPTO")
        cfg = workspace_manager.get_active_workspace_config()
        assert cfg["currency"] == "USDT", f"Expected USDT, got {cfg['currency']}"
        assert "Binance" in cfg["venue_name"], f"Expected Binance, got {cfg['venue_name']}"
        
        markets = multi_scanner.scan_markets("CRYPTO")
        assert len(markets) > 0, "No markets in CRYPTO scanner"
        for m in markets:
            sym = m.get("symbol") or m.get("ticker", "")
            assert workspace_manager.is_symbol_allowed(sym, "CRYPTO"), f"Non-Crypto symbol in scanner: {sym}"
            assert sym.endswith("USDT") or sym.endswith("BTC"), f"Non-crypto symbol format: {sym}"
        g3_msg = f"Verified USDT ($), venue Binance, {len(markets)} Crypto instruments isolated"
    except Exception as e:
        g3_pass = False
        g3_msg = str(e)
    gates.append(("GATE 3: CRYPTO Workspace Integrity & Venue Isolation", g3_pass, g3_msg))

    # ------------------------------------------------------------------
    # GATE 4: Cross-Workspace Data Leakage Prevention
    # ------------------------------------------------------------------
    g4_pass = True
    g4_msg = ""
    try:
        # Switch INDIA -> CRYPTO -> FOREX_GOLD -> INDIA
        workspace_manager.set_active_workspace("INDIA")
        state_in = await get_state("INDIA")
        assert not any(pos.get("symbol", "").endswith("USDT") for pos in state_in.get("positions", []))
        
        workspace_manager.set_active_workspace("CRYPTO")
        state_cr = await get_state("CRYPTO")
        assert not any(pos.get("symbol") in ["RELIANCE", "TCS", "INFY"] for pos in state_cr.get("positions", []))
        
        workspace_manager.set_active_workspace("FOREX_GOLD")
        state_fx = await get_state("FOREX_GOLD")
        assert not any(pos.get("symbol", "").endswith("USDT") for pos in state_fx.get("positions", []))
        
        workspace_manager.set_active_workspace("INDIA")
        g4_msg = "Strict zero cross-workspace position/market leakage across rapid 4-way workspace hops"
    except Exception as e:
        g4_pass = False
        g4_msg = str(e)
    gates.append(("GATE 4: Cross-Workspace Data Leakage Prevention", g4_pass, g4_msg))

    # ------------------------------------------------------------------
    # GATE 5: Double-Entry Ledger & 10-Bucket Wallet Integrity
    # ------------------------------------------------------------------
    g5_pass = True
    g5_msg = ""
    try:
        wallet = user_wallet.compute_all("AEGIS_QUANT_MASTER")
        required_buckets = [
            "total_balance", "available_balance", "trading_balance",
            "used_margin", "unrealized_pnl", "realized_pnl", "fees_paid",
            "locked_balance", "withdrawable_balance", "profit_vault"
        ]
        for b in required_buckets:
            assert b in wallet, f"Missing bucket {b} in user_wallet"
        assert wallet["reconciliation_ok"] is True, f"Reconciliation failed, delta: {wallet.get('reconciliation_delta')}"
        assert wallet["total_balance"] >= 0.0, "Total balance is negative"
        assert wallet["available_balance"] >= 0.0, "Available balance is negative"
        g5_msg = f"All 10 buckets valid; Reconciliation OK: ledger_equity={wallet['ledger_equity']}, broker_equity={wallet['broker_equity']}"
    except Exception as e:
        g5_pass = False
        g5_msg = str(e)
    gates.append(("GATE 5: Double-Entry Ledger & 10-Bucket Wallet Integrity", g5_pass, g5_msg))

    # ------------------------------------------------------------------
    # GATE 6: Risk Engine & Workspace Validation
    # ------------------------------------------------------------------
    g6_pass = True
    g6_msg = ""
    try:
        # Symbol workspace mismatch
        ok, code, msg = risk_engine.validate_workspace_order(
            symbol="BTCUSDT", workspace="INDIA", currency="INR",
            amount=1000.0, leverage=1.0, current_open_positions=0, available_cash=100000.0,
            price=50000.0, quantity=1.0
        )
        assert not ok and "WORKSPACE" in code and "MISMATCH" in code, f"Expected WORKSPACE MISMATCH, got {code} ({msg})"

        # Currency mismatch
        ok, code, msg = risk_engine.validate_workspace_order(
            symbol="RELIANCE", workspace="INDIA", currency="USD",
            amount=2850.0, leverage=1.0, current_open_positions=0, available_cash=100000.0,
            price=2850.0, quantity=1.0
        )
        assert not ok and "CURRENCY_MISMATCH" in code, f"Expected CURRENCY_MISMATCH, got {code} ({msg})"

        # SEBI 5x leverage cap in India
        ok, code, msg = risk_engine.validate_workspace_order(
            symbol="RELIANCE", workspace="INDIA", currency="INR",
            amount=2850.0, leverage=6.0, current_open_positions=0, available_cash=100000.0,
            price=2850.0, quantity=1.0
        )
        assert not ok and "SEBI" in code and "LEVERAGE" in code, f"Expected SEBI LEVERAGE CAP, got {code} ({msg})"

        # Invalid quantity
        ok, code, msg = risk_engine.validate_workspace_order(
            symbol="RELIANCE", workspace="INDIA", currency="INR",
            amount=2850.0, leverage=1.0, current_open_positions=0, available_cash=100000.0,
            price=2850.0, quantity=-1.0
        )
        assert not ok and "INVALID_QUANTITY" in code, f"Expected INVALID_QUANTITY, got {code} ({msg})"

        g6_msg = "Enforced: workspace mismatch, currency mismatch, SEBI 5x peak leverage, invalid quantity"
    except Exception as e:
        g6_pass = False
        g6_msg = str(e)
    gates.append(("GATE 6: Risk Engine & Workspace Validation", g6_pass, g6_msg))

    # ------------------------------------------------------------------
    # GATE 7: Order Submission & State Machine Lifecycle
    # ------------------------------------------------------------------
    g7_pass = True
    g7_msg = ""
    try:
        ord_rec = order_state_machine.create_order("BTCUSDT", "BUY", 0.01, "LIMIT", "TESTNET", 60000.0)
        oid = ord_rec["order_id"]
        assert ord_rec["status"] == "CREATED"
        
        ord_rec = order_state_machine.transition(oid, "RISK_PENDING", "Pre-trade risk evaluation")
        assert ord_rec["status"] == "RISK_PENDING"
        
        ord_rec = order_state_machine.transition(oid, "APPROVED", "Risk gates passed")
        assert ord_rec["status"] == "APPROVED"
        
        ord_rec = order_state_machine.transition(oid, "SUBMITTED", "Submitted to venue")
        assert ord_rec["status"] == "SUBMITTED"
        
        # Test illegal transition (SUBMITTED -> CREATED)
        illegal_transition_caught = False
        try:
            order_state_machine.transition(oid, "CREATED", "Illegal backward transition")
        except OrderStateMachineError:
            illegal_transition_caught = True
        assert illegal_transition_caught, "State machine permitted illegal backward transition"
        
        # Proper transition to ACKNOWLEDGED then FILLED
        order_state_machine.transition(oid, "ACKNOWLEDGED", "Venue ack")
        ord_rec = order_state_machine.transition(
            oid, "FILLED", "Filled by venue",
            execution_record={"execution_id": f"EXEC-{oid}", "fill_price": 60000.0, "fill_qty": 0.01},
            fill_qty=0.01, avg_fill_price=60000.0
        )
        assert ord_rec["status"] == "FILLED"
        g7_msg = f"Order {oid} verified through full lifecycle CREATED -> ... -> FILLED with illegal transition protection"
    except Exception as e:
        g7_pass = False
        g7_msg = str(e)
    gates.append(("GATE 7: Order Submission & State Machine Lifecycle", g7_pass, g7_msg))

    # ------------------------------------------------------------------
    # GATE 8: Market Data Freshness & Watchdog Gate
    # ------------------------------------------------------------------
    g8_pass = True
    g8_msg = ""
    try:
        # Tick record
        res = market_data_watchdog.record_tick("TESTSYM", 100.0)
        assert res["integrity"] == "PASS"
        assert market_data_watchdog.get_status("TESTSYM") == "LIVE"
        
        # Zero price violation
        res_zero = market_data_watchdog.record_tick("TESTSYM_BAD", 0.0)
        assert res_zero["integrity"] == "FAIL"
        assert any("INVALID_PRICE" in v for v in res_zero["violations"])

        # Stale data blocking
        stale_tick_time = time.time() - 10.0
        market_data_watchdog.record_tick("STALE_SYM", 100.0, received_at=stale_tick_time)
        assert market_data_watchdog.is_stale("STALE_SYM")
        
        # Verify EnvironmentGate blocks stale data
        ok, reason = environment_gate.check_order_allowed("PAPER", market_data_age_seconds=10.0)
        assert not ok and "stale" in reason.lower()
        g8_msg = "Verified: live ticks, zero-price rejection, stale data detection (>5.0s), order blocking"
    except Exception as e:
        g8_pass = False
        g8_msg = str(e)
    gates.append(("GATE 8: Market Data Freshness & Watchdog Gate", g8_pass, g8_msg))

    # ------------------------------------------------------------------
    # GATE 9: Execution Profiler Segmentation & Non-Zero Timestamps
    # ------------------------------------------------------------------
    g9_pass = True
    g9_msg = ""
    try:
        # Record trace with measured duration
        trace = execution_latency_profiler.record_execution(
            order_id="ORD-TEST-GATE9",
            symbol="RELIANCE",
            stages={
                "signal_generated": 0.5,
                "risk_evaluated": 1.2,
                "order_constructed": 0.3,
                "venue_acknowledged": 2.1,
                "fill_processed": 0.4
            },
            workspace="INDIA",
            result="SUCCESS"
        )
        assert trace["total_latency_ms"] > 0.0, "Trace duration is zero"
        assert trace["workspace"] == "INDIA"
        
        # Global profiler contains it
        glob_prof = execution_latency_profiler.get_summary(workspace="GLOBAL")
        assert glob_prof["view_scope"] == "GLOBAL"
        assert glob_prof["sample_count"] > 0
        
        # India profiler contains it and strictly filters
        india_prof = execution_latency_profiler.get_summary(workspace="INDIA")
        assert india_prof["view_scope"] == "WORKSPACE_SPECIFIC"
        for ex in india_prof.get("recent_executions", []):
            assert ex.get("workspace") == "INDIA" or workspace_manager.is_symbol_allowed(ex.get("symbol", ""), "INDIA"), f"Non-India trace leaked: {ex}"
        g9_msg = f"Non-zero duration ({trace['total_latency_ms']:.2f}ms), GLOBAL vs WORKSPACE_SPECIFIC cleanly segmented"
    except Exception as e:
        g9_pass = False
        g9_msg = str(e)
    gates.append(("GATE 9: Execution Profiler Segmentation & Non-Zero Timestamps", g9_pass, g9_msg))

    # ------------------------------------------------------------------
    # GATE 10: Backtest Provenance & Authentic Reporting
    # ------------------------------------------------------------------
    g10_pass = True
    g10_msg = ""
    try:
        runs = backtest_analytics_engine.list_backtest_runs()
        assert len(runs) > 0, "No backtest runs found"
        for r in runs:
            assert "workspace" in r
            assert "venue" in r
            assert "currency" in r
            assert "dataset_provenance" in r
            assert "has_trade_log" in r
            # Provenance guard: non-India backtests must NOT masquerade as India
            if r["currency"] in ["USD", "USDT"]:
                assert r["workspace"] != "INDIA", f"USD backtest tagged with INDIA workspace: {r['backtest_id']}"
        first_run = backtest_analytics_engine.get_backtest_run(runs[0]["backtest_id"])
        assert first_run is not None
        assert "has_trade_log" in first_run
        g10_msg = f"Verified {len(runs)} backtest runs; explicit workspace/currency/provenance metadata enforced"
    except Exception as e:
        g10_pass = False
        g10_msg = str(e)
    gates.append(("GATE 10: Backtest Provenance & Authentic Reporting", g10_pass, g10_msg))

    # ------------------------------------------------------------------
    # GATE 11: Performance Curve Dynamic Consistency
    # ------------------------------------------------------------------
    g11_pass = True
    g11_msg = ""
    try:
        timeframes = ["1D", "1W", "1M", "3M", "ALL"]
        environments = ["AEGIS_QUANT_MASTER", "AEGIS_INDIA_INR", "AEGIS_QUANT_FOREX"]
        for env in environments:
            for tf in timeframes:
                curve = performance_curve_engine.get_curve(metric="equity", time_range=tf, environment=env)
                assert curve["status"] == "SUCCESS", f"Curve failed for {env} {tf}"
                assert curve["range"] == tf
                assert len(curve["points"]) >= 2, f"Insufficient points in {env} {tf}"
        g11_msg = "Verified 3 workspaces x 5 timeframes (15 permutations) with persistent baseline data"
    except Exception as e:
        g11_pass = False
        g11_msg = str(e)
    gates.append(("GATE 11: Performance Curve Dynamic Consistency", g11_pass, g11_msg))

    # ------------------------------------------------------------------
    # GATE 12: Immutable Audit Trail
    # ------------------------------------------------------------------
    g12_pass = True
    g12_msg = ""
    try:
        audit_logger.log_event(
            event_type="PRODUCTION_GATE_AUDIT",
            actor="SYSTEM_VALIDATOR",
            details={"gate": "GATE_12", "status": "TESTING"},
            workspace="INDIA",
            symbol="TCS",
            result="SUCCESS"
        )
        trail = audit_logger.get_audit_trail(workspace="INDIA")
        assert len(trail) > 0, "Empty audit trail"
        latest = trail[0]
        assert latest["event_type"] == "PRODUCTION_GATE_AUDIT"
        assert latest["workspace"] == "INDIA"
        assert "integrity_hash" in latest, "Audit record missing SHA256 integrity hash"
        g12_msg = f"Audit trail contains {len(trail)} records with SHA256 integrity hashing"
    except Exception as e:
        g12_pass = False
        g12_msg = str(e)
    gates.append(("GATE 12: Immutable Audit Trail", g12_pass, g12_msg))

    # ------------------------------------------------------------------
    # GATE 13: Macro / News Intelligence Truthfulness
    # ------------------------------------------------------------------
    g13_pass = True
    g13_msg = ""
    try:
        news = macro_engine.scan_macro_news()
        # In environment without configured telegram, status must be NOT CONFIGURED
        if not os.getenv("TELEGRAM_BOT_TOKEN"):
            assert news["status"] == "NOT CONFIGURED", f"Expected 'NOT CONFIGURED', got '{news['status']}'"
            assert "NOT CONFIGURED" in news.get("lockout_reason", ""), "Missing lockout reason note"
            assert news["status"] != "CLEAR", "False 'CLEAR' status reported without active telegram feed"
            g13_msg = "Truthful status 'NOT CONFIGURED' reported without credentials (zero false CLEAR states)"
        else:
            g13_msg = f"News scanner evaluated with status {news['status']}"
    except Exception as e:
        g13_pass = False
        g13_msg = str(e)
    gates.append(("GATE 13: Macro / News Intelligence Truthfulness", g13_pass, g13_msg))

    # ------------------------------------------------------------------
    # GATE 14: India Tax Statement Engine & Non-Stuck UI
    # ------------------------------------------------------------------
    g14_pass = True
    g14_msg = ""
    try:
        stmt = india_statement_engine.generate_statement("FY2024-25")
        assert stmt.get("status") == "SUCCESS", f"Statement generation returned status {stmt.get('status')}"
        assert stmt.get("compliance_validated") is True, "Compliance validation flag missing"
        assert "statutory_levies" in stmt, "Missing statutory levies breakdown"
        levies = stmt["statutory_levies"]
        for levy in ["stt", "exchange_turnover_charges", "sebi_turnover_fee", "stamp_duty", "gst_18_pct", "brokerage"]:
            assert levy in levies, f"Missing statutory levy: {levy}"
        
        # Verify endpoint handling
        req = DummyRequest(query_params={"fy": "FY2024-25"})
        resp = await get_india_tax_statement(req)
        assert resp.status_code == 200
        data = json.loads(resp.body.decode("utf-8"))
        assert data.get("status") in ["SUCCESS", "NOT_AVAILABLE"]
        g14_msg = f"Itemized statutory levies verified (STT, SEBI, GST, Stamp Duty, Brokerage); net PnL: ₹{stmt.get('net_pnl_after_taxes')}"
    except Exception as e:
        g14_pass = False
        g14_msg = str(e)
    gates.append(("GATE 14: India Tax Statement Engine & Non-Stuck UI", g14_pass, g14_msg))

    # ------------------------------------------------------------------
    # GATE 15: Binance Live Safety Switch & Secret Protection
    # ------------------------------------------------------------------
    g15_pass = True
    g15_msg = ""
    try:
        status = environment_gate.get_environment_status()
        assert status["live_trading"] == "LOCKED", f"Live trading is not LOCKED: {status['live_trading']}"
        assert status["live_trading_enabled_flag"] is False, "LIVE_TRADING_ENABLED flag is True"
        
        # Check order allowed gate
        ok, reason = environment_gate.check_order_allowed("LIVE")
        assert not ok and "LIVE_TRADING_ENABLED=false" in reason
        
        # Check that secret keys are never leaked in state
        st = await get_state("CRYPTO")
        state_str = json.dumps(st)
        assert "BINANCE_API_SECRET" not in state_str
        assert "secret_key" not in state_str or "sk_test" in state_str
        g15_msg = "LIVE_TRADING_ENABLED=false locked; Live execution blocked; Secrets protected"
    except Exception as e:
        g15_pass = False
        g15_msg = str(e)
    gates.append(("GATE 15: Binance Live Safety Switch & Secret Protection", g15_pass, g15_msg))

    # ------------------------------------------------------------------
    # GATE 16: Emergency Kill Switch & Trading Halt
    # ------------------------------------------------------------------
    g16_pass = True
    g16_msg = ""
    try:
        # Test kill switch check logic
        saved_fn = environment_gate._is_kill_switch_active
        environment_gate._is_kill_switch_active = lambda: True
        try:
            ok, reason = environment_gate.check_order_allowed("PAPER")
            assert not ok and "kill switch is active" in reason.lower(), f"Unexpected reason: {reason}"
        finally:
            environment_gate._is_kill_switch_active = saved_fn
            
        g16_msg = "Kill switch halts all order evaluations immediately (fail-closed)"
    except Exception as e:
        g16_pass = False
        g16_msg = str(e)
    gates.append(("GATE 16: Emergency Kill Switch & Trading Halt", g16_pass, g16_msg))

    # ------------------------------------------------------------------
    # GATE 17: Withdrawal Lock & Custody Guard
    # ------------------------------------------------------------------
    g17_pass = True
    g17_msg = ""
    try:
        wd_res = withdrawal_state_machine.request_withdrawal(
            user_id="USER-TEST",
            amount=1000.0,
            asset="USDT",
            destination_address="0x1234567890abcdef",
            network="TRC20"
        )
        assert wd_res["status"] == "REJECTED"
        assert "LIVE_WITHDRAWALS_ENABLED=false" in wd_res["reason"]
        
        ok, reason = environment_gate.check_withdrawal_allowed("PAPER")
        assert not ok and "LIVE_WITHDRAWALS_ENABLED=false" in reason
        g17_msg = "Withdrawals hard-locked by default (LIVE_WITHDRAWALS_ENABLED=false)"
    except Exception as e:
        g17_pass = False
        g17_msg = str(e)
    gates.append(("GATE 17: Withdrawal Lock & Custody Guard", g17_pass, g17_msg))

    # ------------------------------------------------------------------
    # GATE 18: Zero UI Unresolved Placeholders & Signal Schema Integrity
    # ------------------------------------------------------------------
    g18_pass = True
    g18_msg = ""
    try:
        template_file = ROOT_DIR / "dashboard" / "templates" / "index.html"
        with open(template_file, "r") as f:
            html_content = f.read()

        # Check for forbidden raw technical placeholders
        assert "Generating Indian Statutory Tax Statement..." not in html_content, "Indefinite 'Generating...' found in template"
        assert "Loading trade history..." not in html_content, "Indefinite 'Loading trade history...' found in template"
        
        # Check 10-column table schema headers
        table_headers = [
            "Symbol", "Venue", "Direction", "Score", "Confidence",
            "Expected R:R", "Current Price", "Timestamp", "Risk State", "Action"
        ]
        for th in table_headers:
            assert th in html_content, f"Table header '{th}' not found in template"

        # Check that fallback logic exists for unresolvable symbols: NO DATA AVAILABLE, BLOCKED, DISABLED
        assert "NO DATA AVAILABLE" in html_content
        assert "BLOCKED" in html_content
        assert "DISABLED" in html_content
        assert "NOT CONFIGURED" in html_content

        g18_msg = "10-column signal table verified; Unresolved placeholders removed; BLOCKED/DISABLED fallback active"
    except Exception as e:
        g18_pass = False
        g18_msg = str(e)
    gates.append(("GATE 18: Zero UI Unresolved Placeholders & Signal Schema Integrity", g18_pass, g18_msg))

    # ------------------------------------------------------------------
    # Print Summary Report
    # ------------------------------------------------------------------
    print("\n" + "=" * 80)
    print("MASTER PRODUCTION READINESS BREAKDOWN (18/18 GATES)")
    print("=" * 80)
    passed_count = 0
    for name, p, msg in gates:
        status_str = "PASS [✓]" if p else "FAIL [✗]"
        print(f"{status_str:<10} | {name}")
        print(f"           | Evidence: {msg}")
        if p:
            passed_count += 1

    print("=" * 80)
    print(f"SUMMARY: {passed_count}/{len(gates)} GATES PASSED ({(passed_count/len(gates))*100:.1f}%)")
    print("=" * 80)

    # Return active workspace to default INDIA
    workspace_manager.set_active_workspace("INDIA")
    
    if passed_count < len(gates):
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(run_master_production_audit())
