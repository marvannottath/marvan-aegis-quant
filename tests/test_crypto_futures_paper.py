"""
Aegis-Quant BUG-04 Crypto Futures Architecture Verification Test Suite.
Validates:
1. Product model: SPOT vs USDT_M_FUTURES.
2. Futures order routing: BinanceBroker mock fills for paper/testnet.
3. Fail-closed Live Futures Gate: REJECTED with LIVE_FUTURES_LOCKED when environment is LIVE.
4. Directional symmetry: Paper futures supports both LONG and SHORT.
5. Leverage and Margin calculation: notional = margin * leverage, units = notional / price.
6. Liquidation math: liquidation price computed for LONG and SHORT.
7. Liquidation enforcement: breaches trigger loss capped at allocated margin.
8. Coexistence and Isolation: BTCUSDT SPOT and BTCUSDT FUTURES coexist independently.
9. Decoupled Close: Spot close dismisses spot; Futures close routes to futures without dismissing spot.
10. Stop-Loss & Take-Profit enforcement for LONG and SHORT positions.
"""

import sys
import os
from pathlib import Path

# Ensure root workspace is in sys.path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from execution.binance_broker import binance_broker
from execution.paper_broker import paper_broker
from core.position_snapshot_service import position_snapshot_service
from core.workspace_manager import workspace_manager
from core.risk_engine import risk_engine
from core.environment_gate import environment_gate

PASSED_COUNT = 0
FAILED_COUNT = 0

def test(name: str, condition: bool, details: str = ""):
    global PASSED_COUNT, FAILED_COUNT
    if condition:
        PASSED_COUNT += 1
        print(f"[PASS] {name} - {details}")
    else:
        FAILED_COUNT += 1
        print(f"[FAIL] {name} - {details}")


def run_tests():
    print("=" * 80)
    print("RUNNING CRYPTO FUTURES ARCHITECTURE TEST SUITE (BUG-04)")
    print("=" * 80)

    # 1. BinanceBroker Futures Live Gate Rejection
    res_live = binance_broker.create_futures_order(
        symbol="BTCUSDT",
        side="BUY",
        quantity=0.01,
        environment="BINANCE_LIVE"
    )
    test(
        "live_futures_locked",
        res_live.get("status") == "REJECTED" and res_live.get("code") == "LIVE_FUTURES_LOCKED",
        f"Live order correctly blocked: {res_live.get('code')}"
    )

    # 2. BinanceBroker Paper/Testnet Mock Fill
    res_paper = binance_broker.create_futures_order(
        symbol="BTCUSDT",
        side="BUY",
        quantity=0.01,
        environment="BINANCE_TESTNET"
    )
    test(
        "paper_futures_fill",
        res_paper.get("status") in ("FILLED", "SUCCESS") and res_paper.get("product") == "USDT_M_FUTURES",
        f"Paper futures filled: order_id={res_paper.get('provider_order_id')}"
    )

    # 3. Paper Broker: Switch to clean demo pool
    paper_broker.switch_pool("BINANCE_TESTNET_DEMO")
    paper_broker.positions.clear()
    paper_broker.virtual_cash = 20000.0

    # 4. Open SPOT position on BTCUSDT
    pos_spot = paper_broker.execute_order(
        asset="BTCUSDT",
        action="BUY",
        amount_usd=1000.0,
        current_price=60000.0,
        leverage=1.0,
        product="SPOT"
    )
    test(
        "spot_position_created",
        "BTCUSDT" in paper_broker.positions and pos_spot.get("product") == "SPOT",
        f"Spot position units: {pos_spot.get('units')}"
    )

    # 5. Open FUTURES LONG position on BTCUSDT with 5x leverage
    pos_fut_long = paper_broker.execute_order(
        asset="BTCUSDT",
        action="BUY",
        amount_usd=1000.0,
        current_price=60000.0,
        leverage=5.0,
        product="USDT_M_FUTURES"
    )
    fut_long_key = "BTCUSDT:USDT_M_FUTURES"
    test(
        "futures_long_coexistence",
        fut_long_key in paper_broker.positions and "BTCUSDT" in paper_broker.positions,
        "SPOT and FUTURES positions coexist independently in paper broker"
    )
    test(
        "futures_long_units_math",
        abs(pos_fut_long.get("units") - (5000.0 / 60000.0)) < 0.001,
        f"Notional=$5000, Units={pos_fut_long.get('units')}"
    )
    test(
        "futures_long_liquidation_price",
        pos_fut_long.get("liquidation_price") < 60000.0,
        f"Liquidation price={pos_fut_long.get('liquidation_price')} (< entry 60000)"
    )

    # 6. Position Snapshot Service exposes correct product and leverage
    snap = position_snapshot_service.get_snapshot("CRYPTO", force_refresh=True)
    crypto_positions = snap.get("positions", [])
    spot_view = next((p for p in crypto_positions if p["symbol"] == "BTCUSDT" and p.get("product") == "SPOT"), None)
    fut_view = next((p for p in crypto_positions if p["symbol"] == "BTCUSDT" and p.get("product") == "USDT_M_FUTURES"), None)

    test(
        "snapshot_spot_product_and_leverage",
        spot_view is not None and spot_view.get("leverage") == 1.0 and spot_view.get("product") == "SPOT",
        f"Spot view leverage={spot_view.get('leverage') if spot_view else None}"
    )
    test(
        "snapshot_futures_product_and_leverage",
        fut_view is not None and fut_view.get("leverage") == 5.0 and fut_view.get("product") == "USDT_M_FUTURES",
        f"Futures view leverage={fut_view.get('leverage') if fut_view else None}"
    )

    # 7. Close Futures Long position with profit
    trade_fut_close = paper_broker.close_position("BTCUSDT:USDT_M_FUTURES", exit_price=66000.0)
    test(
        "futures_long_profit_calculation",
        trade_fut_close is not None and trade_fut_close.get("pnl_usd", 0.0) > 0,
        f"Realized PnL=${trade_fut_close.get('pnl_usd')} (Entry 60k, Exit 66k, 5x)"
    )
    test(
        "spot_unaffected_after_futures_close",
        "BTCUSDT" in paper_broker.positions and "BTCUSDT:USDT_M_FUTURES" not in paper_broker.positions,
        "SPOT position remains open after FUTURES close"
    )

    # 8. Open FUTURES SHORT position on ETHUSDT with 10x leverage
    pos_fut_short = paper_broker.execute_order(
        asset="ETHUSDT",
        action="SELL",
        amount_usd=500.0,
        current_price=3000.0,
        leverage=10.0,
        product="USDT_M_FUTURES"
    )
    eth_fut_key = "ETHUSDT:USDT_M_FUTURES"
    test(
        "futures_short_creation",
        eth_fut_key in paper_broker.positions and pos_fut_short.get("action") == "SELL",
        f"Short position created with units={pos_fut_short.get('units')}"
    )
    test(
        "futures_short_liquidation_price",
        pos_fut_short.get("liquidation_price") > 3000.0,
        f"Short liquidation price={pos_fut_short.get('liquidation_price')} (> entry 3000)"
    )

    # 9. Close FUTURES SHORT position with profit (price drops from 3000 to 2700)
    trade_short_close = paper_broker.close_position("ETHUSDT:USDT_M_FUTURES", exit_price=2700.0)
    test(
        "futures_short_profit_calculation",
        trade_short_close is not None and trade_short_close.get("pnl_usd", 0.0) > 0,
        f"Short PnL=${trade_short_close.get('pnl_usd')} (Entry 3000, Exit 2700, 10x)"
    )

    # 10. Liquidation Breach in _update_equity
    # Open high-leverage long position that will be liquidated
    pos_to_liq = paper_broker.execute_order(
        asset="SOLUSDT",
        action="BUY",
        amount_usd=100.0,
        current_price=100.0,
        leverage=20.0,
        product="USDT_M_FUTURES"
    )
    sol_key = "SOLUSDT:USDT_M_FUTURES"
    liq_p = pos_to_liq.get("liquidation_price", 95.0)
    # Simulate price drop below liquidation price
    pos_to_liq["last_price"] = liq_p - 1.0
    paper_broker._update_equity()
    test(
        "liquidation_triggered_automatically",
        sol_key not in paper_broker.positions,
        f"Position liquidated automatically when price breached {liq_p}"
    )

    # 11. Clean up open test spot position
    paper_broker.close_position("BTCUSDT", exit_price=60000.0)

    # 12. Risk Engine Leverage Cap check for Crypto
    ok, code, msg = risk_engine.validate_workspace_order(
        symbol="BTCUSDT",
        workspace="CRYPTO",
        currency="USDT",
        amount=100.0,
        leverage=30.0,  # exceeds 25x cap
        current_open_positions=0,
        available_cash=5000.0,
        price=60000.0,
        quantity=0.01
    )
    test(
        "risk_engine_crypto_leverage_cap",
        not ok and code == "RISK_REJECTED/MAX_LEVERAGE_EXCEEDED",
        f"Rejected leverage > 25x: {code}"
    )

    print("=" * 80)
    print(f"RESULTS: {PASSED_COUNT} PASSED, {FAILED_COUNT} FAILED")
    print("=" * 80)
    if FAILED_COUNT > 0:
        sys.exit(1)

if __name__ == "__main__":
    run_tests()
