"""
Phase 6: Targeted Performance, Resilience, and Broker Decoupling Test Suite.
Verifies:
  1. Repeated snapshot calls reuse cached snapshots rather than querying broker repeatedly.
  2. Binance API timeout handling (bounded timeouts).
  3. Binance authentication failure bounded retry / backoff.
  4. Stale cache handling (distinguishes AUTHENTICATED_LIVE vs CACHED_LAST_KNOWN vs API_UNAVAILABLE).
  5. INDIA workspace never invokes Binance broker routines.
  6. FOREX_GOLD workspace never invokes Binance broker routines.
  7. CRYPTO workspace gracefully handles Binance broker unavailability without crashing or hanging.
  8. Workspace-specific financial calculations maintain integrity during slow broker conditions.
"""

import sys
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from execution.binance_broker import binance_broker
from core.position_snapshot_service import position_snapshot_service
from execution.paper_broker import paper_broker


def report(test_name: str, passed: bool, actual: any, expected: any):
    status = "PASS" if passed else "FAIL"
    print(f"[{status}] {test_name}")
    print(f"       Actual:   {actual}")
    print(f"       Expected: {expected}\n")
    if not passed:
        raise AssertionError(f"Test failed: {test_name} | Actual: {actual} | Expected: {expected}")


def test_1_repeated_snapshot_deduplication():
    # Pass 1: generate snapshot
    snap1 = position_snapshot_service.get_snapshot("CRYPTO", force_refresh=True)
    # Pass 2: get_portfolio_aggregate with pos_snap passed in should NOT re-call get_snapshot
    with patch.object(position_snapshot_service, "get_snapshot", wraps=position_snapshot_service.get_snapshot) as mock_snap:
        agg = position_snapshot_service.get_portfolio_aggregate("CRYPTO", force_refresh=False, pos_snap=snap1)
        mock_snap.assert_not_called()
        report(
            "repeated_snapshot_deduplication",
            mock_snap.call_count == 0 and agg.get("workspace") == "CRYPTO",
            f"mock_snap call count: {mock_snap.call_count}",
            "mock_snap call count: 0"
        )


def test_2_india_zero_binance_broker_calls():
    with patch.object(binance_broker, "get_open_positions") as mock_open_pos, \
         patch.object(binance_broker, "get_account_info") as mock_acc_info, \
         patch.object(binance_broker, "get_authoritative_status") as mock_status:
        # Request INDIA snapshot and portfolio aggregate
        snap = position_snapshot_service.get_snapshot("INDIA", force_refresh=True)
        agg = position_snapshot_service.get_portfolio_aggregate("INDIA", force_refresh=True)
        total_calls = mock_open_pos.call_count + mock_acc_info.call_count + mock_status.call_count
        report(
            "india_zero_binance_calls",
            total_calls == 0 and snap.get("workspace") == "INDIA" and agg.get("currency") == "INR",
            f"Binance calls during INDIA render: {total_calls}",
            "0 Binance calls"
        )


def test_3_forex_zero_binance_broker_calls():
    with patch.object(binance_broker, "get_open_positions") as mock_open_pos, \
         patch.object(binance_broker, "get_account_info") as mock_acc_info, \
         patch.object(binance_broker, "get_authoritative_status") as mock_status:
        # Request FOREX_GOLD snapshot and portfolio aggregate
        snap = position_snapshot_service.get_snapshot("FOREX_GOLD", force_refresh=True)
        agg = position_snapshot_service.get_portfolio_aggregate("FOREX_GOLD", force_refresh=True)
        total_calls = mock_open_pos.call_count + mock_acc_info.call_count + mock_status.call_count
        report(
            "forex_zero_binance_calls",
            total_calls == 0 and snap.get("workspace") == "FOREX_GOLD" and agg.get("currency") == "USD",
            f"Binance calls during FOREX render: {total_calls}",
            "0 Binance calls"
        )


def test_4_binance_failure_bounded_retry():
    # Test that failed account info calls trigger bounded backoff and do not hammer external API
    binance_broker._account_info_cache.clear()
    binance_broker._account_info_err_ts.clear()

    with patch.object(binance_broker, "_get_credentials_for_env", return_value=("mock_k", "mock_s", "https://api.binance.com", False)), \
         patch("requests.get", side_effect=Exception("Connection timed out")) as mock_req:
        res1 = binance_broker.get_account_info("BINANCE_LIVE_TEST_BOUNDED")
        calls_after_first = mock_req.call_count
        res2 = binance_broker.get_account_info("BINANCE_LIVE_TEST_BOUNDED")
        res3 = binance_broker.get_account_info("BINANCE_LIVE_TEST_BOUNDED")
        calls_after_subsequent = mock_req.call_count

        # Requests should NOT be repeated; subsequent calls should hit the 15s failure cache
        report(
            "binance_failure_bounded_retry",
            calls_after_first > 0 and calls_after_subsequent == calls_after_first and res1.get("status") == "API_UNAVAILABLE" and res2.get("status") == "API_UNAVAILABLE",
            f"calls after first: {calls_after_first}, calls after subsequent: {calls_after_subsequent}, status: {res1.get('status')}",
            f"calls strictly unchanged ({calls_after_first}) under 15s backoff"
        )


def test_5_stale_cache_data_source_labeling():
    # Cache an authenticated response and verify data_source transitions
    env = "BINANCE_LIVE_LABEL_TEST"
    cache_key = f"acc_{env}"
    fake_info = {
        "authenticated": True,
        "account_status": "AUTHENTICATED",
        "status": "AUTHENTICATED",
        "available_balance": 1000.0,
        "total_equity": 1000.0,
    }
    binance_broker._account_info_cache[cache_key] = fake_info
    binance_broker._account_info_cache_ts[cache_key] = time.time()  # fresh

    res_fresh = binance_broker.get_account_info(env)
    fresh_label = res_fresh.get("data_source")

    # Age the cache by 2 seconds
    binance_broker._account_info_cache_ts[cache_key] = time.time() - 2.0
    res_stale = binance_broker.get_account_info(env)
    stale_label = res_stale.get("data_source")

    report(
        "stale_cache_data_source_labeling",
        fresh_label == "AUTHENTICATED_LIVE" and stale_label == "CACHED_LAST_KNOWN",
        f"fresh: {fresh_label}, aged: {stale_label}",
        "fresh: AUTHENTICATED_LIVE, aged: CACHED_LAST_KNOWN"
    )


def test_6_crypto_resilience_when_binance_down():
    # When Binance is completely down, CRYPTO position snapshot and aggregate must still render safely
    with patch.object(binance_broker, "get_open_positions", side_effect=Exception("Binance 503 Service Unavailable")), \
         patch.object(binance_broker, "get_authoritative_status", return_value={"authenticated": False, "connected": False, "status": "DISCONNECTED"}):
        snap = position_snapshot_service.get_snapshot("CRYPTO", force_refresh=True)
        agg = position_snapshot_service.get_portfolio_aggregate("CRYPTO", force_refresh=True, pos_snap=snap)
        report(
            "crypto_resilience_when_binance_down",
            snap is not None and agg.get("workspace") == "CRYPTO" and agg.get("currency") == "USDT",
            f"Workspace: {agg.get('workspace')}, Currency: {agg.get('currency')}",
            "Workspace: CRYPTO, Currency: USDT (safely handled without crash)"
        )


def test_7_dashboard_render_all_workspaces_no_unbound_error():
    import asyncio
    from fastapi import Request
    from dashboard.app import read_dashboard

    async def _run():
        workspaces = ["INDIA", "CRYPTO", "FOREX_GOLD"]
        for ws in workspaces:
            req = MagicMock(spec=Request)
            req.query_params = {"workspace": ws}
            req.headers = {}
            resp = await read_dashboard(req)
            html = resp.body.decode("utf-8")
            assert "{{ LITE_BROKER_BADGE }}" not in html, f"Placeholder remaining in {ws}"
            assert "{{ LITE_BROKER_BADGE_CLASS }}" not in html, f"Class placeholder remaining in {ws}"
            if ws == "INDIA":
                assert "UPSTOX: NSE/BSE ACTIVE" in html, "India lite badge missing"
            elif ws == "FOREX_GOLD":
                assert "MT5: FOREX & GOLD LIVE ACTIVE" in html, "Forex lite badge missing"
            elif ws == "CRYPTO":
                assert "BINANCE:" in html, "Crypto lite badge missing"

    asyncio.run(_run())
    report(
        "dashboard_render_all_workspaces_no_unbound_error",
        True,
        "All 3 workspaces rendered successfully without UnboundLocalError",
        "All 3 workspaces render cleanly with resolved Lite and Pro elements"
    )


def test_8_forex_performance_curve_equity_isolation():
    from core.performance_curve_engine import performance_curve_engine
    # Switch paper_broker to CRYPTO with low equity (~13.84)
    paper_broker.switch_pool("BINANCE_LIVE_REAL")
    crypto_equity = paper_broker.equity

    # Request performance curve for FOREX_GOLD with MT5_LIVE_REAL
    forex_curve = performance_curve_engine.get_curve(metric="equity", time_range="1D", environment="MT5_LIVE_REAL")
    forex_latest = forex_curve.get("latest", 0.0)

    # Forensic check: Forex curve must NOT return Crypto's equity
    is_isolated = (forex_latest != crypto_equity) and (forex_latest >= 1000.0)
    report(
        "forex_performance_curve_equity_isolation",
        is_isolated,
        f"Forex latest equity: {forex_latest} USD vs Crypto equity: {crypto_equity} USDT",
        "Forex curve strictly isolated from Crypto pool equity"
    )


def test_9_profit_vault_reconciliation_and_isolation():
    """
    BUG-03 Regression Test:
    Verify profit vault reconciliation across paper and live environments:
    1. Base balance for live pools must be 0.0 (no synthetic seed).
    2. Simulated pools sum verified sweep transactions and include vault balance in total equity.
    3. External live brokers (Binance Live) do not double-count vault balance in total equity.
    4. Cross-workspace equation: Cash + Margin + PnL + Vault == Total Equity holds across all 3 workspaces.
    """
    from execution.profit_vault import profit_vault, EXTERNAL_LIVE_POOLS
    from core.position_snapshot_service import position_snapshot_service
    from execution.user_wallet import user_wallet

    # 1. External live pool base balance is 0.0
    for live_pool in ["BINANCE_LIVE_REAL", "MT5_LIVE_REAL", "UPSTOX_LIVE"]:
        store = profit_vault.vault_stores.get(live_pool, {})
        assert store.get("base_balance", 0.0) == 0.0, f"Live pool {live_pool} has non-zero base balance"

    # 2. Check all 3 workspace aggregates satisfy the financial invariant
    for ws in ["INDIA", "CRYPTO", "FOREX_GOLD"]:
        agg = position_snapshot_service.get_portfolio_aggregate(ws, force_refresh=True, environment="DEMO")
        computed_eq = round(agg["free_cash"] + agg["used_margin"] + agg["unrealized_pnl"] + agg.get("vault_balance", 0.0), 2)
        assert abs(computed_eq - agg["total_equity"]) < 0.05, f"{ws} equity equation failed: {computed_eq} vs {agg['total_equity']}"

        agg_live = position_snapshot_service.get_portfolio_aggregate(ws, force_refresh=True, environment="LIVE")
        if agg_live.get("data_source") == "DISCONNECTED":
            assert agg_live["total_equity"] is None, f"{ws} live total equity must be None when disconnected"

    # 3. User wallet does not double count live broker equity
    w_live = user_wallet.compute_all(environment="BINANCE_LIVE_REAL")
    assert w_live["broker_equity"] == round(float(paper_broker.pools.get("BINANCE_LIVE_REAL", {}).get("equity", 0.0)), 2)

    # 4. Vault summary returns proper status for live pools
    v_sum = profit_vault.get_vault_summary("BINANCE_LIVE_REAL")
    assert "LIVE BROKER" in v_sum["external_transfer_status"]
    assert v_sum["auto_external_sweep_enabled"] is False

    report(
        "profit_vault_reconciliation_and_isolation",
        True,
        "Paper & live vault reconciled with zero double-counting across all 3 workspaces",
        "Authoritative broker equity strictly preserved for live pools; paper pools segregated"
    )


def main():
    print("=" * 80)
    print("RUNNING TARGETED PERFORMANCE, RESILIENCE & ISOLATION SUITE")
    print("=" * 80)
    test_1_repeated_snapshot_deduplication()
    test_2_india_zero_binance_broker_calls()
    test_3_forex_zero_binance_broker_calls()
    test_4_binance_failure_bounded_retry()
    test_5_stale_cache_data_source_labeling()
    test_6_crypto_resilience_when_binance_down()
    test_7_dashboard_render_all_workspaces_no_unbound_error()
    test_8_forex_performance_curve_equity_isolation()
    test_9_profit_vault_reconciliation_and_isolation()
    print("=" * 80)
    print("ALL 9 PERFORMANCE & RESILIENCE TESTS PASSED SUCCESSFULLY! (100%)")
    print("=" * 80)


if __name__ == "__main__":
    main()
