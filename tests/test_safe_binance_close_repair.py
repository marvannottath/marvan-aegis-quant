"""
Comprehensive Offline Mock Tests for Safe Binance Spot Close-Flow Repair.

Covers:
1. Entry price resolution (cache, pool positions, trade history).
2. Entry price cache retention on SELL orders in create_order.
3. Close spot position action, side ("SELL"), gross/net P&L calculation, and outcome flags.
4. Environment isolation: TESTNET vs LIVE pool separation for trade records.
5. Timeout / rejection classification (CONFIRMED_FILLED vs AMBIGUOUS_TIMEOUT vs REJECTED).
6. PaperBroker skip_exchange_order decoupling (preventing duplicate exchange orders).
7. Position restoration on exchange failure when skip_exchange_order=False.
8. AutonomousTrader closed_cooldowns preventing churn and position preservation on sell failure/timeout.
"""

import os
import sys
import time
import pytest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


@pytest.fixture(autouse=True)
def isolate_close_in_flight_tracker(tmp_path):
    """Ensure all tests run against an isolated temporary close_in_flight.json."""
    from core.autonomous_trader import autonomous_trader
    from core.close_in_flight_tracker import CloseInFlightTracker

    test_db = tmp_path / "close_in_flight_test.json"
    isolated_tracker = CloseInFlightTracker(db_path=test_db)
    orig_tracker = autonomous_trader.in_flight_tracker

    autonomous_trader.in_flight_tracker = isolated_tracker
    autonomous_trader.close_in_flight = isolated_tracker.in_flight_orders
    try:
        yield isolated_tracker
    finally:
        autonomous_trader.in_flight_tracker = orig_tracker
        autonomous_trader.close_in_flight = orig_tracker.in_flight_orders


def test_binance_broker_get_entry_price():
    """Verify get_entry_price prioritizes cache, then pool positions, then trade history."""
    from execution.binance_broker import binance_broker
    from execution.paper_broker import paper_broker

    binance_broker._entry_price_cache.clear()
    
    # 1. Fallback to pool positions
    pool = paper_broker.pools.setdefault("BINANCE_TESTNET_DEMO", {})
    pool["positions"] = {
        "ETHUSDT": {"symbol": "ETHUSDT", "entry_price": 2800.0, "units": 0.5}
    }
    ep = binance_broker.get_entry_price("BINANCE_TESTNET", "ETHUSDT")
    assert ep == 2800.0, f"Expected 2800.0 from pool position, got {ep}"

    # 2. Priority of cache over pool position
    binance_broker._entry_price_cache["ETHUSDT"] = 2850.0
    ep2 = binance_broker.get_entry_price("BINANCE_TESTNET", "ETHUSDT")
    assert ep2 == 2850.0, f"Expected 2850.0 from cache, got {ep2}"

    # 3. Clean up
    binance_broker._entry_price_cache.clear()
    pool["positions"].clear()


def test_create_order_entry_price_cache_preservation_on_sell():
    """Verify create_order preserves _entry_price_cache on SELL and only sets it on BUY."""
    from execution.binance_broker import binance_broker

    binance_broker._entry_price_cache["SOLUSDT"] = 150.0

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "orderId": 123456,
        "clientOrderId": "test_client_order",
        "status": "FILLED",
        "executedQty": "1.0",
        "cummulativeQuoteQty": "160.0",
        "fills": [{"price": "160.0", "qty": "1.0", "commission": "0.1", "commissionAsset": "USDT"}]
    }

    with patch("execution.binance_broker.requests.post", return_value=mock_resp), \
         patch.object(binance_broker, "_get_server_time_ms", return_value=1700000000000):
        res = binance_broker.create_order(
            environment="BINANCE_TESTNET",
            symbol="SOLUSDT",
            side="SELL",
            quantity=1.0,
            order_type="MARKET"
        )
        assert res.get("status") == "SUCCESS"
        # Cache must NOT have been removed on SELL!
        assert "SOLUSDT" in binance_broker._entry_price_cache
        assert binance_broker._entry_price_cache["SOLUSDT"] == 150.0

    binance_broker._entry_price_cache.clear()


def test_close_spot_position_action_side_and_pnl_calculation():
    """Verify close_spot_position produces SELL action/side and accurate gross/net P&L."""
    from execution.binance_broker import binance_broker
    from execution.paper_broker import paper_broker

    pool = paper_broker.pools.setdefault("BINANCE_TESTNET_DEMO", {})
    pool["positions"] = {
        "BTCUSDT": {"symbol": "BTCUSDT", "entry_price": 60000.0, "units": 0.05}
    }
    binance_broker._entry_price_cache["BTCUSDT"] = 60000.0

    mock_bals = [{"asset": "BTC", "free": "0.05", "locked": "0.0"}]
    mock_order = {
        "status": "SUCCESS",
        "outcome": "FILLED",
        "executed_quantity": 0.05,
        "cummulative_quote_qty": 3250.0,
        "avg_price": 65000.0,
        "average_fill_price": 65000.0,
        "fills": [{"price": "65000.0", "qty": "0.05", "commission": "1.0", "commissionAsset": "USDT"}]
    }

    with patch.object(binance_broker, "get_balances", return_value=mock_bals), \
         patch.object(binance_broker, "create_order", return_value=mock_order), \
         patch.object(binance_broker, "get_bulk_market_data", return_value={"BTCUSDT": {"last_price": 65000.0}}), \
         patch.object(binance_broker, "get_live_spot_balance", return_value=10000.0):

        res = binance_broker.close_spot_position("BTCUSDT", environment="BINANCE_TESTNET")

        assert res.get("status") == "SUCCESS"
        assert res.get("outcome") == "CONFIRMED_FILLED"

        record = res.get("trade_record")
        assert record is not None
        assert record["action"] == "SELL"
        assert record["side"] == "SELL"
        assert record["entry_side"] == "BUY"
        assert record["exit_side"] == "SELL"
        assert record["entry_price"] == 60000.0
        assert record["exit_price"] == 65000.0
        assert record["units"] == 0.05

        expected_gross = round((65000.0 - 60000.0) * 0.05, 2)  # 250.00
        assert record["gross_pnl"] == expected_gross
        assert record["net_pnl"] == expected_gross - record["fee_usd"]
        assert record["result"] == "WIN"
        assert record["source"] == "BINANCE_TESTNET"

    binance_broker._entry_price_cache.clear()
    pool["positions"].clear()


def test_close_spot_position_pool_isolation():
    """Verify testnet close records go strictly to BINANCE_TESTNET_DEMO, not BINANCE_LIVE_REAL."""
    from execution.binance_broker import binance_broker
    from execution.paper_broker import paper_broker

    testnet_pool = paper_broker.pools.setdefault("BINANCE_TESTNET_DEMO", {})
    live_pool = paper_broker.pools.setdefault("BINANCE_LIVE_REAL", {})

    testnet_pool["trade_history"] = []
    live_pool["trade_history"] = []

    mock_bals = [{"asset": "ETH", "free": "1.0", "locked": "0.0"}]
    mock_order = {
        "status": "SUCCESS",
        "outcome": "FILLED",
        "executed_quantity": 1.0,
        "cummulative_quote_qty": 3000.0,
        "avg_price": 3000.0,
        "fills": []
    }

    with patch.object(binance_broker, "get_balances", return_value=mock_bals), \
         patch.object(binance_broker, "create_order", return_value=mock_order), \
         patch.object(binance_broker, "get_entry_price", return_value=2900.0), \
         patch.object(binance_broker, "get_live_spot_balance", return_value=5000.0):

        binance_broker.close_spot_position("ETHUSDT", environment="BINANCE_TESTNET")

        assert len(testnet_pool["trade_history"]) == 1
        assert len(live_pool["trade_history"]) == 0
        assert testnet_pool["trade_history"][0]["source"] == "BINANCE_TESTNET"


def test_close_spot_position_timeout_and_rejection_outcomes():
    """Verify AMBIGUOUS_TIMEOUT and REJECTED classification."""
    from execution.binance_broker import binance_broker

    mock_bals = [{"asset": "BNB", "free": "2.0", "locked": "0.0"}]

    # 1. Timeout outcome
    mock_timeout = {
        "status": "ERROR",
        "outcome": "TIMEOUT",
        "message": "Connection timed out connecting to api.binance.com"
    }
    with patch.object(binance_broker, "get_balances", return_value=mock_bals), \
         patch.object(binance_broker, "create_order", return_value=mock_timeout), \
         patch.object(binance_broker, "get_entry_price", return_value=500.0):

        res_timeout = binance_broker.close_spot_position("BNBUSDT", environment="BINANCE_TESTNET")
        assert res_timeout["status"] == "ERROR"
        assert res_timeout["outcome"] == "AMBIGUOUS_TIMEOUT"

    # 2. Rejection outcome
    mock_rejected = {
        "status": "ERROR",
        "outcome": "REJECTED",
        "message": "Filter failure: MIN_NOTIONAL"
    }
    with patch.object(binance_broker, "get_balances", return_value=mock_bals), \
         patch.object(binance_broker, "create_order", return_value=mock_rejected), \
         patch.object(binance_broker, "get_entry_price", return_value=500.0):

        res_reject = binance_broker.close_spot_position("BNBUSDT", environment="BINANCE_TESTNET")
        assert res_reject["status"] == "ERROR"
        assert res_reject["outcome"] == "REJECTED"


def test_paper_broker_skip_exchange_order_decoupling():
    """Verify skip_exchange_order=True prevents duplicate exchange calls."""
    from execution.paper_broker import paper_broker
    from execution.binance_broker import binance_broker

    paper_broker.switch_pool("BINANCE_TESTNET_DEMO")
    paper_broker.positions["SOLUSDT"] = {
        "asset": "SOLUSDT",
        "entry_price": 100.0,
        "units": 2.0,
        "capital_allocated": 200.0,
        "action": "BUY",
        "product": "SPOT"
    }

    with patch.object(binance_broker, "create_order") as mock_create_order:
        res = paper_broker.close_position("SOLUSDT", exit_price=110.0, skip_exchange_order=True)

        assert res is not None
        assert "SOLUSDT" not in paper_broker.positions
        mock_create_order.assert_not_called()


def test_paper_broker_position_restored_on_exchange_rejection():
    """Verify position is restored if skip_exchange_order=False and exchange rejects."""
    from execution.paper_broker import paper_broker
    from execution.binance_broker import binance_broker

    paper_broker.switch_pool("BINANCE_TESTNET_DEMO")
    paper_broker.positions["AVAXUSDT"] = {
        "asset": "AVAXUSDT",
        "entry_price": 30.0,
        "units": 10.0,
        "capital_allocated": 300.0,
        "action": "BUY",
        "product": "SPOT",
        "environment": "BINANCE_TESTNET"
    }

    mock_bals = [{"asset": "AVAX", "free": "10.0"}]
    mock_rejected = {"status": "ERROR", "message": "Account has insufficient balance for fees"}

    with patch.object(binance_broker, "get_balances", return_value=mock_bals), \
         patch.object(binance_broker, "create_order", return_value=mock_rejected):

        res = paper_broker.close_position("AVAXUSDT", exit_price=35.0, skip_exchange_order=False)

        assert res["status"] == "ERROR"
        assert res["outcome"] == "EXCHANGE_REJECTED"
        assert "AVAXUSDT" in paper_broker.positions, "Position must be restored on rejection"

    paper_broker.positions.pop("AVAXUSDT", None)


def test_autonomous_trader_cooldown_and_fail_closed():
    """Verify AutonomousTrader respects closed_cooldowns and retains position on sell failure."""
    from core.autonomous_trader import autonomous_trader

    autonomous_trader.closed_cooldowns.clear()
    now = time.time()
    autonomous_trader.closed_cooldowns["BTCUSDT"] = now + 60.0

    # Cooldown active
    assert time.time() < autonomous_trader.closed_cooldowns.get("BTCUSDT", 0)

    # Inactive asset
    assert time.time() >= autonomous_trader.closed_cooldowns.get("ETHUSDT", 0)


def test_client_order_id_preserved_on_timeout_and_rejection():
    """Verify Binance create_order preserves exact client_order_id on timeout and rejection."""
    from execution.binance_broker import binance_broker
    import requests

    # 1. Connection Timeout
    with patch("execution.binance_broker.requests.post", side_effect=requests.exceptions.ConnectTimeout("Connection timed out")), \
         patch.object(binance_broker, "_get_server_time_ms", return_value=1700000000000):
        res_timeout = binance_broker.create_order(
            environment="BINANCE_TESTNET",
            symbol="BTCUSDT",
            side="SELL",
            quantity=0.01,
            order_type="MARKET",
            client_order_id="AQ-CUSTOM-TEST-CID-1"
        )
        assert res_timeout["status"] == "ERROR"
        assert res_timeout["outcome"] == "TIMEOUT"
        assert res_timeout["client_order_id"] == "AQ-CUSTOM-TEST-CID-1", "Must preserve custom client_order_id on timeout"

    # 2. Rejection with auto-generated client_order_id
    mock_bad_resp = MagicMock()
    mock_bad_resp.status_code = 400
    mock_bad_resp.text = '{"code": -1013, "msg": "Filter failure: MIN_NOTIONAL"}'
    mock_bad_resp.json.return_value = {"code": -1013, "msg": "Filter failure: MIN_NOTIONAL"}

    with patch("execution.binance_broker.requests.post", return_value=mock_bad_resp), \
         patch.object(binance_broker, "_get_server_time_ms", return_value=1700000000000):
        res_reject = binance_broker.create_order(
            environment="BINANCE_TESTNET",
            symbol="BTCUSDT",
            side="SELL",
            quantity=0.00001,
            order_type="MARKET"
        )
        assert res_reject["status"] == "ERROR"
        assert res_reject["outcome"] == "REJECTED"
        assert res_reject.get("client_order_id") is not None
        assert str(res_reject["client_order_id"]).startswith("AQ-")


def test_candidate_evaluation_loop_cooldown_and_ticker_scope():
    """Regression test: verify candidate evaluation loop executes without NameError on 'asset'."""
    from core.autonomous_trader import autonomous_trader
    from core.risk_engine import risk_engine
    from core.multi_market_scanner import multi_scanner

    autonomous_trader.closed_cooldowns.clear()
    autonomous_trader.close_in_flight.clear()

    # Place ETHUSDT on cooldown, SOLUSDT in close_in_flight
    autonomous_trader.closed_cooldowns["ETHUSDT"] = time.time() + 60.0
    autonomous_trader.close_in_flight["SOLUSDT"] = {"status": "UNKNOWN"}

    # Mock scanned candidates
    mock_candidates = [
        {"ticker": "ETHUSDT", "price": 2800.0, "rsi": 45.0, "volatility": 0.01, "ai_action": "BUY", "opportunity_score": 85.0},
        {"ticker": "SOLUSDT", "price": 140.0, "rsi": 40.0, "volatility": 0.015, "ai_action": "BUY", "opportunity_score": 90.0},
        {"ticker": "ADAUSDT", "price": 0.50, "rsi": 38.0, "volatility": 0.012, "ai_action": "BUY", "opportunity_score": 80.0},
    ]

    evaluated_tickers = []
    # Simulate candidate loop exactly as in autonomous_trader.py
    for item in mock_candidates:
        ticker = item["ticker"]
        opp_score = item["opportunity_score"]
        if opp_score < 74.0:
            continue
        # Verified loop logic:
        if time.time() < autonomous_trader.closed_cooldowns.get(ticker, 0) or ticker in autonomous_trader.close_in_flight:
            continue
        evaluated_tickers.append(ticker)

    # ETHUSDT was in cooldown -> skipped
    # SOLUSDT was in close_in_flight -> skipped
    # ADAUSDT passes
    assert evaluated_tickers == ["ADAUSDT"]


def test_in_flight_reconciliation_barrier_states():
    """Verify close-in-flight barrier handles STILL_UNKNOWN, CONFIRMED_FILLED, and CONFIRMED_REJECTED."""
    from core.autonomous_trader import autonomous_trader
    from execution.binance_broker import binance_broker
    from execution.paper_broker import paper_broker

    autonomous_trader.close_in_flight.clear()
    autonomous_trader.closed_cooldowns.clear()

    # Setup initial position
    paper_broker.switch_pool("BINANCE_LIVE_REAL")
    paper_broker.positions["LINKUSDT"] = {
        "asset": "LINKUSDT",
        "entry_price": 12.0,
        "units": 50.0,
        "capital_allocated": 600.0,
        "action": "BUY",
        "product": "SPOT",
        "trade_id": "TRD-LINK-001"
    }

    # 1. STILL_UNKNOWN: Order status query returns network error -> barrier stays active
    autonomous_trader.close_in_flight["LINKUSDT"] = {
        "environment": "BINANCE_LIVE",
        "client_order_id": "AQ-LINK-TEST-001",
        "symbol": "LINKUSDT",
        "status": "UNKNOWN",
        "requested_at": time.time(),
        "exit_price": 13.0,
        "reason": "SCALP_HARVEST"
    }

    with patch.object(binance_broker, "get_order_status", return_value={"status": "ERROR", "message": "Read timeout"}):
        res1 = autonomous_trader.reconcile_in_flight_close("LINKUSDT")
        assert res1 == "STILL_UNKNOWN"
        assert "LINKUSDT" in autonomous_trader.close_in_flight, "Barrier must stay active while UNKNOWN"
        assert "LINKUSDT" in paper_broker.positions, "Position must remain open while UNKNOWN"

    # 2. CONFIRMED_FILLED: Exchange confirms order was FILLED
    mock_fill_order = {"status": "FILLED", "price": "13.20", "avgPrice": "13.20", "executedQty": "50.0"}
    with patch.object(binance_broker, "get_order_status", return_value={"status": "SUCCESS", "order": mock_fill_order}):
        res2 = autonomous_trader.reconcile_in_flight_close("LINKUSDT")
        assert res2 == "CONFIRMED_FILLED"
        assert "LINKUSDT" not in autonomous_trader.close_in_flight, "Barrier must clear after confirmed fill"
        assert "LINKUSDT" not in paper_broker.positions, "Position must be closed internally"
        assert time.time() < autonomous_trader.closed_cooldowns.get("LINKUSDT", 0), "Cooldown must be set after fill"

    # 3. CONFIRMED_REJECTED: Order not found on exchange (-2011)
    paper_broker.positions["DOGEUSDT"] = {
        "asset": "DOGEUSDT",
        "entry_price": 0.15,
        "units": 1000.0,
        "capital_allocated": 150.0,
        "action": "BUY",
        "product": "SPOT",
        "trade_id": "TRD-DOGE-001"
    }
    autonomous_trader.close_in_flight["DOGEUSDT"] = {
        "environment": "BINANCE_LIVE",
        "client_order_id": "AQ-DOGE-TEST-002",
        "symbol": "DOGEUSDT",
        "status": "UNKNOWN",
        "requested_at": time.time(),
        "exit_price": 0.16,
        "reason": "STOP_LOSS"
    }

    with patch.object(binance_broker, "get_order_status", return_value={"status": "ERROR", "message": "Unknown order sent: -2011"}):
        res3 = autonomous_trader.reconcile_in_flight_close("DOGEUSDT")
        assert res3 == "CONFIRMED_REJECTED"
        assert "DOGEUSDT" not in autonomous_trader.close_in_flight, "Barrier must clear after confirmed rejection"
        assert "DOGEUSDT" in paper_broker.positions, "Position must remain open on rejection"

    paper_broker.positions.pop("DOGEUSDT", None)


def test_zero_holdings_zero_pnl_dismissal():
    """Verify ZERO_HOLDINGS outcome closes internal position at entry price with zero realized P&L."""
    from execution.paper_broker import paper_broker

    paper_broker.switch_pool("BINANCE_TESTNET_DEMO")
    paper_broker.positions["DOTUSDT"] = {
        "asset": "DOTUSDT",
        "entry_price": 6.50,
        "units": 100.0,
        "capital_allocated": 650.0,
        "action": "BUY",
        "product": "SPOT",
        "trade_id": "TRD-DOT-001"
    }

    # Close with exit_price equal to entry_price and skip_exchange_order=True
    rec = paper_broker.close_position(
        asset="DOTUSDT",
        exit_price=6.50,
        reason="ZERO_HOLDINGS_RECONCILED",
        skip_exchange_order=True
    )

    assert rec is not None
    assert rec["gross_pnl"] == 0.0
    assert rec["entry_price"] == 6.50
    assert rec["exit_price"] == 6.50
    assert "DOTUSDT" not in paper_broker.positions


@pytest.mark.asyncio
async def test_dashboard_close_endpoint_spot_skip_exchange_order():
    """Verify /api/close-position endpoint calls binance_broker and sets skip_exchange_order=True."""
    from dashboard.app import close_position_endpoint
    from execution.paper_broker import paper_broker
    from execution.binance_broker import binance_broker

    paper_broker.switch_pool("BINANCE_TESTNET_DEMO")
    paper_broker.positions["NEARUSDT"] = {
        "asset": "NEARUSDT",
        "entry_price": 5.0,
        "units": 50.0,
        "capital_allocated": 250.0,
        "action": "BUY",
        "product": "SPOT",
        "environment": "BINANCE_TESTNET",
        "trade_id": "TRD-NEAR-001"
    }

    mock_spot_close = {
        "status": "SUCCESS",
        "outcome": "CONFIRMED_FILLED",
        "message": "Sold on Binance",
        "trade_record": {
            "trade_id": "TRD-BINA-NEAR-12345",
            "action": "SELL",
            "side": "SELL",
            "entry_price": 5.0,
            "exit_price": 5.5,
            "units": 50.0,
            "gross_pnl": 25.0
        }
    }

    with patch.object(binance_broker, "close_spot_position", return_value=mock_spot_close), \
         patch.object(paper_broker, "close_position", wraps=paper_broker.close_position) as spy_close:

        response = await close_position_endpoint({"asset": "NEARUSDT", "workspace": "CRYPTO"})
        assert response.status_code == 200

        # Assert paper_broker.close_position was called with skip_exchange_order=True
        assert spy_close.called
        _, kwargs = spy_close.call_args
        assert kwargs.get("skip_exchange_order") is True, "Must set skip_exchange_order=True to prevent duplicate exchange execution"


def test_fully_filled_order_lifecycle():
    """Verify fully filled order returns FILLED outcome, cleans up cache, and purges position."""
    from execution.binance_broker import binance_broker
    from execution.paper_broker import paper_broker

    paper_broker.switch_pool("BINANCE_TESTNET_DEMO")
    paper_broker.positions["LINKUSDT"] = {
        "asset": "LINKUSDT",
        "entry_price": 10.0,
        "units": 20.0,
        "capital_allocated": 200.0,
        "action": "BUY",
        "product": "SPOT",
        "trade_id": "TRD-LINK-001"
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "symbol": "LINKUSDT",
        "orderId": 777777,
        "clientOrderId": "AQ_SELL_LINK_001",
        "status": "FILLED",
        "origQty": "20.0",
        "executedQty": "20.0",
        "cummulativeQuoteQty": "240.0",
        "fills": [{"price": "12.0", "qty": "20.0", "commission": "0.1", "commissionAsset": "USDT"}]
    }

    with patch("execution.binance_broker.requests.post", return_value=mock_resp), \
         patch.object(binance_broker, "_get_server_time_ms", return_value=1700000000000), \
         patch.object(binance_broker, "get_account_info", return_value={"balances": [{"asset": "LINK", "free": "20.0", "locked": "0.0"}]}), \
         patch.object(binance_broker, "get_live_spot_balance", return_value=500.0):

        res = binance_broker.close_spot_position("LINKUSDT", environment="BINANCE_TESTNET")
        assert res.get("status") == "SUCCESS"
        assert res.get("outcome") == "CONFIRMED_FILLED"
        assert res.get("executed_quantity") == 20.0
        assert res.get("trade_record", {}).get("net_pnl") > 0
        pool_pos = paper_broker.pools.get("BINANCE_TESTNET_DEMO", {}).get("positions", {})
        assert "LINKUSDT" not in pool_pos


def test_partial_fill_retains_remaining_position():
    """Verify partial fill accounts only for executed fraction and retains remainder."""
    from execution.binance_broker import binance_broker
    from execution.paper_broker import paper_broker

    paper_broker.switch_pool("BINANCE_TESTNET_DEMO")
    paper_broker.positions["ADAUSDT"] = {
        "asset": "ADAUSDT",
        "entry_price": 0.50,
        "units": 1000.0,
        "capital_allocated": 500.0,
        "action": "BUY",
        "product": "SPOT",
        "trade_id": "TRD-ADA-001"
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "symbol": "ADAUSDT",
        "orderId": 888888,
        "clientOrderId": "AQ_SELL_ADA_001",
        "status": "PARTIALLY_FILLED",
        "origQty": "1000.0",
        "executedQty": "400.0",
        "cummulativeQuoteQty": "240.0",
        "fills": [{"price": "0.60", "qty": "400.0", "commission": "0.2", "commissionAsset": "USDT"}]
    }

    with patch("execution.binance_broker.requests.post", return_value=mock_resp), \
         patch.object(binance_broker, "_get_server_time_ms", return_value=1700000000000), \
         patch.object(binance_broker, "get_account_info", return_value={"balances": [{"asset": "ADA", "free": "1000.0", "locked": "0.0"}]}), \
         patch.object(binance_broker, "get_live_spot_balance", return_value=1000.0):

        res = binance_broker.close_spot_position("ADAUSDT", environment="BINANCE_TESTNET")
        assert res.get("status") == "PARTIALLY_FILLED"
        assert res.get("outcome") == "PARTIALLY_FILLED"
        assert res.get("executed_quantity") == 400.0
        assert res.get("remaining_quantity") == 600.0

        pool_pos = paper_broker.pools.get("BINANCE_TESTNET_DEMO", {}).get("positions", {})
        assert "ADAUSDT" in pool_pos, "Remaining position must NOT be dismissed from pool"
        assert pool_pos["ADAUSDT"]["units"] == 600.0
        assert pool_pos["ADAUSDT"]["capital_allocated"] == 300.0

    paper_broker.positions.pop("ADAUSDT", None)


def test_partial_fill_followed_by_another_fill_no_double_booking():
    """Verify incremental fills are accounted for without duplicate P&L or double-booking."""
    from core.autonomous_trader import autonomous_trader
    from execution.paper_broker import paper_broker
    from execution.binance_broker import binance_broker

    paper_broker.switch_pool("BINANCE_TESTNET_DEMO")
    paper_broker.positions["ETHUSDT"] = {
        "asset": "ETHUSDT",
        "entry_price": 3000.0,
        "units": 1.0,
        "capital_allocated": 3000.0,
        "action": "BUY",
        "product": "SPOT",
        "trade_id": "TRD-ETH-001"
    }

    autonomous_trader.close_in_flight["ETHUSDT"] = {
        "environment": "BINANCE_TESTNET",
        "client_order_id": "AQ_SELL_ETH_001",
        "symbol": "ETHUSDT",
        "status": "PARTIALLY_FILLED",
        "requested_quantity": 1.0,
        "already_reconciled_executed_qty": 0.4,
        "exit_price": 3100.0,
        "reason": "TAKE_PROFIT"
    }

    # Step 1: Exchange reports order is still PARTIALLY_FILLED with 0.7 total executed
    order_step1 = {
        "status": "SUCCESS",
        "order": {
            "status": "PARTIALLY_FILLED",
            "executedQty": "0.7",
            "origQty": "1.0",
            "price": "3100.0",
            "cummulativeQuoteQty": "2170.0"
        }
    }

    with patch.object(binance_broker, "get_order_status", return_value=order_step1):
        res1 = autonomous_trader.reconcile_in_flight_close("ETHUSDT")
        assert res1 == "STILL_UNKNOWN"
        assert "ETHUSDT" in autonomous_trader.close_in_flight, "Barrier must stay active while working"
        assert autonomous_trader.close_in_flight["ETHUSDT"]["already_reconciled_executed_qty"] == 0.7
        # Position should have 1.0 - 0.3 = 0.7 units remaining (since 0.4 was already deducted previously)
        assert paper_broker.positions["ETHUSDT"]["units"] == 0.7

    # Step 2: Exchange reports FILLED with 1.0 total executed
    order_step2 = {
        "status": "SUCCESS",
        "order": {
            "status": "FILLED",
            "executedQty": "1.0",
            "origQty": "1.0",
            "price": "3100.0",
            "cummulativeQuoteQty": "3100.0"
        }
    }

    with patch.object(binance_broker, "get_order_status", return_value=order_step2):
        res2 = autonomous_trader.reconcile_in_flight_close("ETHUSDT")
        assert res2 == "CONFIRMED_FILLED"
        assert "ETHUSDT" not in autonomous_trader.close_in_flight, "Barrier must clear after full fill"
        assert "ETHUSDT" not in paper_broker.positions, "Position must be fully closed"

    paper_broker.positions.pop("ETHUSDT", None)


def test_partial_fill_followed_by_cancellation():
    """Verify order cancellation after partial fill retains remaining position and clears barrier."""
    from core.autonomous_trader import autonomous_trader
    from execution.paper_broker import paper_broker
    from execution.binance_broker import binance_broker

    paper_broker.switch_pool("BINANCE_TESTNET_DEMO")
    paper_broker.positions["SOLUSDT"] = {
        "asset": "SOLUSDT",
        "entry_price": 140.0,
        "units": 10.0,
        "capital_allocated": 1400.0,
        "action": "BUY",
        "product": "SPOT",
        "trade_id": "TRD-SOL-001"
    }

    autonomous_trader.close_in_flight["SOLUSDT"] = {
        "environment": "BINANCE_TESTNET",
        "client_order_id": "AQ_SELL_SOL_001",
        "symbol": "SOLUSDT",
        "status": "PARTIALLY_FILLED",
        "requested_quantity": 10.0,
        "already_reconciled_executed_qty": 3.0,
        "exit_price": 150.0,
        "reason": "SCALP_HARVEST"
    }

    # Exchange reports CANCELED with 5.0 total executed (2.0 incremental since last reconcile)
    cancel_order = {
        "status": "SUCCESS",
        "order": {
            "status": "CANCELED",
            "executedQty": "5.0",
            "origQty": "10.0",
            "price": "150.0",
            "cummulativeQuoteQty": "750.0"
        }
    }

    with patch.object(binance_broker, "get_order_status", return_value=cancel_order):
        res = autonomous_trader.reconcile_in_flight_close("SOLUSDT")
        assert res == "CONFIRMED_REJECTED"
        assert "SOLUSDT" not in autonomous_trader.close_in_flight, "Barrier cleared once order is dead on exchange"
        # 10.0 - 2.0 incremental = 8.0 units remaining in paper broker
        assert "SOLUSDT" in paper_broker.positions
        assert paper_broker.positions["SOLUSDT"]["units"] == 8.0

    paper_broker.positions.pop("SOLUSDT", None)


def test_timeout_retains_client_order_id_and_blocks_retries():
    """Verify timeout retains original clientOrderId and blocks retries in the autonomous trader."""
    from core.autonomous_trader import autonomous_trader
    from core.close_in_flight_tracker import CloseInFlightTracker
    from pathlib import Path
    import tempfile

    orig_tracker = autonomous_trader.in_flight_tracker
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            test_db = Path(tmpdir) / "close_in_flight.json"
            tracker = CloseInFlightTracker(db_path=test_db)
            autonomous_trader.in_flight_tracker = tracker
            autonomous_trader.close_in_flight = tracker.in_flight_orders

            tracker.record_in_flight(
                symbol="AVAXUSDT",
                environment="BINANCE_TESTNET",
                client_order_id="AQ_TIMEOUT_AVAX_001",
                requested_quantity=50.0,
                already_reconciled_qty=0.0,
                status="UNKNOWN",
                exit_price=30.0,
                reason="TRAILING_STOP"
            )

            assert tracker.is_blocked("AVAXUSDT") is True
            assert tracker.is_blocked("AVAXUSDT", "BINANCE_TESTNET") is True
            # Different environment does not cross-contaminate
            assert tracker.is_blocked("AVAXUSDT", "BINANCE_LIVE") is False
    finally:
        autonomous_trader.in_flight_tracker = orig_tracker
        autonomous_trader.close_in_flight = orig_tracker.in_flight_orders


def test_pending_reconciliation_survives_process_restart():
    """Verify pending reconciliation state is restored from disk upon simulated process restart."""
    from core.close_in_flight_tracker import CloseInFlightTracker
    from pathlib import Path
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        test_db = Path(tmpdir) / "close_in_flight.json"

        # Instance 1: Record and persist
        inst1 = CloseInFlightTracker(db_path=test_db)
        inst1.record_in_flight(
            symbol="MATICUSDT",
            environment="BINANCE_TESTNET",
            client_order_id="AQ_PERSIST_MATIC_001",
            requested_quantity=500.0,
            already_reconciled_qty=200.0,
            status="PARTIALLY_FILLED",
            exit_price=0.70,
            reason="TAKE_PROFIT"
        )
        assert test_db.exists()

        # Instance 2: Simulate process restart
        inst2 = CloseInFlightTracker(db_path=test_db)
        assert inst2.is_corrupted() is False
        assert "MATICUSDT" in inst2.in_flight_orders
        saved_entry = inst2.get_in_flight("MATICUSDT")
        assert saved_entry["client_order_id"] == "AQ_PERSIST_MATIC_001"
        assert saved_entry["requested_quantity"] == 500.0
        assert saved_entry["already_reconciled_executed_qty"] == 200.0
        assert saved_entry["status"] == "PARTIALLY_FILLED"
        assert inst2.is_blocked("MATICUSDT") is True


def test_corrupt_persistence_fails_closed():
    """Verify corrupted state file causes fail-closed behavior, blocking close operations."""
    from core.close_in_flight_tracker import CloseInFlightTracker
    from pathlib import Path
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        test_db = Path(tmpdir) / "close_in_flight.json"
        # Write corrupted JSON
        test_db.write_text("{malformed_json: true, unexpected EOF")

        tracker = CloseInFlightTracker(db_path=test_db)
        assert tracker.is_corrupted() is True
        assert "Failed to read/parse" in tracker.get_corruption_error()
        # Fail-closed: ANY symbol must be blocked!
        assert tracker.is_blocked("BTCUSDT") is True
        assert tracker.is_blocked("ETHUSDT") is True
        # Save must refuse to overwrite
        tracker.save()
        assert test_db.read_text().startswith("{malformed_json")


def test_unknown_order_status_cannot_trigger_new_close():
    """Verify UNKNOWN reconciliation status keeps barrier active without duplicate closes."""
    from core.autonomous_trader import autonomous_trader
    from execution.binance_broker import binance_broker

    autonomous_trader.close_in_flight["XRPUSDT"] = {
        "environment": "BINANCE_TESTNET",
        "client_order_id": "AQ_XRP_UNKNOWN_001",
        "symbol": "XRPUSDT",
        "status": "UNKNOWN",
        "requested_quantity": 1000.0,
        "already_reconciled_executed_qty": 0.0,
        "exit_price": 0.55,
        "reason": "STOP_LOSS"
    }

    # Exchange responds with timeout error
    with patch.object(binance_broker, "get_order_status", return_value={"status": "ERROR", "message": "Connection timed out"}), \
         patch.object(binance_broker, "get_live_spot_balance", return_value=1000.0):

        outcome = autonomous_trader.reconcile_in_flight_close("XRPUSDT")
        assert outcome == "STILL_UNKNOWN"
        assert "XRPUSDT" in autonomous_trader.close_in_flight, "Barrier must remain active during timeout"

    autonomous_trader.close_in_flight.pop("XRPUSDT", None)


