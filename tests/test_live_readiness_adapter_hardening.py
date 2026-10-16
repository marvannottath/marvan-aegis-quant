"""
Regression and Hardening Tests for Aegis-Quant Live-Readiness.
Covers:
1. MultiMarketScanner initialization, cache attributes, and isolated workspace scans.
2. PaperBroker thread-safe atomic state save under high concurrency (zero rename collision).
3. Kotak Neo fail-closed behavior for LIVE environment orders without credentials.
4. Upstox fail-closed behavior for LIVE environment orders without access token.
5. MT5 live server connection fail-closed when bridge and native library unavailable.
6. EnvironmentGate and ExecutionGate strict LIVE lockout enforcement.
"""

import os
import sys
import pytest
import threading
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def test_multi_scanner_init_and_cache_attributes():
    """Verify MultiMarketScanner initializes cleanly and exposes all caches without errors."""
    from core.multi_market_scanner import MultiMarketScanner, multi_scanner

    scanner = MultiMarketScanner()
    assert hasattr(scanner, "_scan_cache"), "_scan_cache must exist on scanner"
    assert hasattr(scanner, "_scan_cache_ts"), "_scan_cache_ts must exist on scanner"
    assert hasattr(scanner, "_binance_24h_cache"), "_binance_24h_cache must exist on scanner"
    assert hasattr(scanner, "_binance_24h_cache_ts"), "_binance_24h_cache_ts must exist on scanner"

    # Verify isolated scan across all 3 workspaces
    for ws in ["CRYPTO", "INDIA", "FOREX_GOLD"]:
        res = scanner.scan_workspace(ws)
        assert isinstance(res, list), f"scan_workspace({ws}) must return a list"
        assert len(res) > 0, f"scan_workspace({ws}) must return assets"
        # Verify ticker presence and expected fields
        first = res[0]
        assert "ticker" in first
        assert "price" in first
        assert "opportunity_score" in first


def test_paper_broker_concurrent_atomic_save():
    """Verify PaperBroker._save_state() is thread-safe and never encounters temp-file rename errors."""
    from execution.paper_broker import paper_broker

    errors = []

    def worker(worker_id):
        for i in range(15):
            try:
                paper_broker.virtual_cash += 0.01
                paper_broker._save_state()
            except Exception as e:
                errors.append(f"Worker {worker_id} iteration {i} failed: {e}")

    threads = [threading.Thread(target=worker, args=(t,)) for t in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(errors) == 0, f"Concurrent saves resulted in errors: {errors}"


def test_kotak_neo_live_order_fail_closed_no_silent_fallback():
    """Verify Kotak Neo rejects LIVE order when unconfigured without falling back to paper."""
    from execution.kotak_neo_broker import KotakNeoBrokerAdapter

    adapter = KotakNeoBrokerAdapter()
    adapter._consumer_key = ""
    adapter._session_token = ""
    adapter._paper_mode = False

    order_req = {
        "symbol": "RELIANCE",
        "side": "BUY",
        "quantity": 10,
        "price": 2900.0,
        "environment": "LIVE",
    }

    # Even if LIVE_TRADING_ENABLED was True, unconfigured credentials must reject
    res = adapter.place_order(order_req)
    assert res["status"] in ("REJECTED", "REQUIRES_AUTH"), f"Expected rejection, got: {res}"
    assert res.get("order_id") is None, "LIVE rejected order must not generate an order_id"
    assert "mock" not in str(res).lower(), "LIVE order must not route to mock"


def test_upstox_live_order_fail_closed_no_silent_fallback():
    """Verify Upstox rejects LIVE order when access token is missing without falling back to paper."""
    from execution.upstox_broker import UpstoxBrokerAdapter

    adapter = UpstoxBrokerAdapter()
    adapter._access_token = ""
    adapter._paper_mode = False

    order_req = {
        "symbol": "TCS",
        "side": "BUY",
        "quantity": 5,
        "price": 3800.0,
        "environment": "LIVE",
    }

    res = adapter.place_order(order_req)
    assert res["status"] == "REJECTED", f"Expected REJECTED, got: {res}"
    assert res.get("code") in ("LIVE_TRADING_LOCKED", "AUTH_REQUIRED"), f"Unexpected code: {res}"
    assert res.get("broker") != "UPSTOX_PAPER", "LIVE order must never route to UPSTOX_PAPER"


def test_mt5_live_server_connection_fail_closed():
    """Verify MT5 connect() fails closed for real server when bridge is unavailable."""
    from execution.mt5_broker import MT5BrokerAdapter

    adapter = MT5BrokerAdapter()
    adapter.login = 98765432
    adapter.password = "Secr3tPassword!"
    adapter.server = "ICMarkets-Live01"  # Real live server
    adapter.bridge_url = "http://127.0.0.1:9999"  # Non-existent bridge

    res = adapter.connect()
    assert res["status"] == "ERROR", f"Expected ERROR, got: {res}"
    assert adapter.is_connected is False, "is_connected must remain False"
    assert adapter.status in ("BRIDGE_UNAVAILABLE", "CONNECTION_FAILED"), f"Unexpected status: {adapter.status}"


def test_environment_gate_strict_lockouts():
    """Verify EnvironmentGate strictly locks live trading and withdrawals by default."""
    from core.environment_gate import environment_gate

    assert environment_gate.LIVE_TRADING_ENABLED is False, "LIVE_TRADING_ENABLED must be False by default"
    assert environment_gate.LIVE_WITHDRAWALS_ENABLED is False, "LIVE_WITHDRAWALS_ENABLED must be False by default"

    allowed, reason = environment_gate.check_order_allowed("LIVE")
    assert allowed is False, "LIVE order must be blocked"
    assert "LIVE_TRADING_ENABLED=false" in reason

    w_allowed, w_reason = environment_gate.check_withdrawal_allowed("LIVE")
    assert w_allowed is False, "LIVE withdrawal must be blocked"
    assert "LIVE_WITHDRAWALS_ENABLED=false" in w_reason


def test_execution_gate_blocks_live_order_and_cross_workspace():
    """Verify ExecutionGate enforces all safety checklist gates."""
    from core.execution_gate import execution_gate

    # 1. LIVE order locked
    allowed, code, reason, _ = execution_gate.validate_order(
        symbol="BTCUSDT",
        side="BUY",
        quantity=0.1,
        price=60000.0,
        workspace="CRYPTO",
        environment="LIVE",
        data_age_seconds=1.0
    )
    assert allowed is False
    assert code == "LIVE_TRADING_LOCKED"

    # 2. Cross-workspace asset mismatch
    allowed_cw, code_cw, reason_cw, _ = execution_gate.validate_order(
        symbol="RELIANCE",
        side="BUY",
        quantity=10,
        price=2900.0,
        workspace="CRYPTO",
        environment="PAPER"
    )
    assert allowed_cw is False
    assert code_cw == "WORKSPACE_ASSET_MISMATCH"
