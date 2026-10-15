"""
AEGIS-QUANT — LIVE/DEMO ENVIRONMENT ROUTING & EXECUTION SAFETY REGRESSION TEST SUITE

Explicitly verifies:
  1. LIVE order request with LIVE_TRADING_ENABLED=false is strictly REJECTED and NEVER silently routed to DEMO.
  2. LIVE order execution cannot use Demo credentials, and DEMO orders never hit LIVE endpoints.
  3. PerformanceCurveEngine does not crash on NoneType PnL or total_equity when live brokers are disconnected.
  4. Disconnected live brokers fast-fail in < 500ms without blocking or timing out.
  5. Default workspace alignment between frontend and backend is CRYPTO.
  6. High-concurrency workspace switching (multithreaded) produces ZERO state bleeding across symbols, currencies, and pools.
  7. Workspace asset boundaries strictly isolate positions and orders.
"""

import os
import sys
import time
import unittest
import threading
from pathlib import Path

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from core.execution_gate import execution_gate
from core.environment_gate import environment_gate
from core.workspace_manager import workspace_manager
from core.position_snapshot_service import position_snapshot_service
from core.performance_curve_engine import performance_curve_engine
from execution.binance_broker import binance_broker


class TestLiveDemoRoutingSafety(unittest.TestCase):

    def setUp(self):
        # Guarantee safety invariant baseline
        os.environ["LIVE_TRADING_ENABLED"] = "false"
        environment_gate.LIVE_TRADING_ENABLED = False

    def test_01_live_order_rejected_when_live_trading_disabled(self):
        """Verify that LIVE order submission is strictly blocked and NOT silently routed to DEMO."""
        self.assertFalse(environment_gate.LIVE_TRADING_ENABLED)

        allowed, gate_code, reason, details = execution_gate.validate_order(
            symbol="BTCUSDT",
            side="BUY",
            quantity=0.01,
            price=60000.0,
            workspace="CRYPTO",
            environment="LIVE",
            currency="USDT",
            leverage=1.0,
            data_age_seconds=0.1
        )

        self.assertFalse(allowed, "LIVE order must be rejected when LIVE_TRADING_ENABLED is false")
        self.assertIn("LIVE_TRADING_LOCKED", gate_code, "Gate code must reflect live trading lock")
        self.assertIn("LIVE_TRADING_ENABLED=false", reason)

    def test_02_binance_broker_create_order_blocks_live_buy(self):
        """Verify binance_broker.create_order blocks LIVE order opening when live trading is locked."""
        res = binance_broker.create_order(
            environment="BINANCE_LIVE",
            symbol="BTCUSDT",
            side="BUY",
            quantity=0.001,
            price=60000.0,
            order_type="MARKET"
        )
        self.assertEqual(res.get("status"), "REJECTED")
        self.assertEqual(res.get("code"), "LIVE_TRADING_LOCKED")

    def test_03_credential_pairing_strict_isolation(self):
        """Verify that live credentials cannot leak into testnet and vice-versa."""
        api_k_live, sec_k_live, base_url_live, is_testnet_live = binance_broker._get_credentials_for_env("BINANCE_LIVE")
        self.assertFalse(is_testnet_live)
        self.assertEqual(base_url_live, "https://api.binance.com")

        api_k_demo, sec_k_demo, base_url_demo, is_testnet_demo = binance_broker._get_credentials_for_env("BINANCE_TESTNET_DEMO")
        self.assertTrue(is_testnet_demo)
        self.assertEqual(base_url_demo, "https://testnet.binance.vision")

    def test_04_performance_curve_engine_nonetype_safety(self):
        """Verify performance_curve_engine does not crash when live broker returns NoneType PnL."""
        for ws in ["CRYPTO", "INDIA", "FOREX_GOLD"]:
            for env in ["DEMO", "LIVE"]:
                try:
                    curve = performance_curve_engine.get_curve(
                        workspace=ws,
                        environment=env,
                        metric="equity",
                        time_range="1M"
                    )
                    self.assertIsInstance(curve, dict)
                    self.assertIn("points", curve)
                    self.assertTrue(len(curve["points"]) > 0)
                except TypeError as e:
                    self.fail(f"Performance curve engine crashed with TypeError for {ws} on {env}: {e}")

    def test_05_disconnected_broker_fast_fail_latency(self):
        """Verify get_portfolio_aggregate for disconnected LIVE broker fast-fails in < 500ms."""
        t0 = time.time()
        res = position_snapshot_service.get_portfolio_aggregate("CRYPTO", environment="LIVE", force_refresh=True)
        elapsed_ms = (time.time() - t0) * 1000.0

        self.assertLess(elapsed_ms, 500.0, f"Live probe took {elapsed_ms:.1f}ms, exceeding 500ms SLA")
        self.assertEqual(res.get("data_source"), "DISCONNECTED")
        self.assertFalse(res.get("broker_connected"))
        self.assertIsNone(res.get("total_equity"))
        self.assertIsNone(res.get("free_cash"))

    def test_06_default_workspace_alignment(self):
        """Verify default workspace across backend is CRYPTO (aligning with frontend root)."""
        norm_empty = workspace_manager._normalize_workspace(None)
        norm_blank = workspace_manager._normalize_workspace("")
        self.assertEqual(norm_empty, "CRYPTO")
        self.assertEqual(norm_blank, "CRYPTO")
        self.assertEqual(workspace_manager.get_active_workspace(), "CRYPTO")

    def test_07_concurrent_workspace_switching_zero_contamination(self):
        """Run concurrent multi-threaded requests across CRYPTO, INDIA, and FOREX_GOLD. Zero state bleeding."""
        results = {"CRYPTO": [], "INDIA": [], "FOREX_GOLD": []}
        errors = []

        def worker(ws: str):
            for _ in range(15):
                try:
                    snap = position_snapshot_service.get_snapshot(ws)
                    curr = snap.get("currency")
                    positions = snap.get("positions", [])
                    # Verify currency match
                    expected_curr = "INR" if ws == "INDIA" else ("USD" if ws == "FOREX_GOLD" else "USDT")
                    if curr != expected_curr:
                        errors.append(f"Currency mismatch for {ws}: got {curr}, expected {expected_curr}")
                    # Verify positions allowed in workspace
                    for p in positions:
                        sym = p.get("symbol")
                        if not workspace_manager.is_symbol_allowed(sym, ws):
                            errors.append(f"Contaminated position '{sym}' found in {ws}")
                    results[ws].append(True)
                except Exception as ex:
                    errors.append(f"Worker exception for {ws}: {ex}")

        threads = []
        for _ in range(3):
            for ws in ["CRYPTO", "INDIA", "FOREX_GOLD"]:
                t = threading.Thread(target=worker, args=(ws,))
                threads.append(t)
                t.start()

        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0, f"Concurrent workspace switching produced errors: {errors}")
        for ws in ["CRYPTO", "INDIA", "FOREX_GOLD"]:
            self.assertGreater(len(results[ws]), 0, f"No results recorded for {ws}")

    def test_08_cross_workspace_order_rejection(self):
        """Verify that ordering an Indian stock in Crypto or Crypto in Forex is strictly blocked."""
        # 1. Order Reliance (India) in Crypto workspace
        ok_cr, code_cr, _, _ = execution_gate.validate_order(
            symbol="RELIANCE",
            side="BUY",
            quantity=10,
            price=2500.0,
            workspace="CRYPTO",
            environment="PAPER",
            currency="USDT"
        )
        self.assertFalse(ok_cr)
        self.assertEqual(code_cr, "WORKSPACE_ASSET_MISMATCH")

        # 2. Order BTCUSDT (Crypto) in Forex workspace
        ok_fx, code_fx, _, _ = execution_gate.validate_order(
            symbol="BTCUSDT",
            side="BUY",
            quantity=0.1,
            price=60000.0,
            workspace="FOREX_GOLD",
            environment="PAPER",
            currency="USD"
        )
        self.assertFalse(ok_fx)
        self.assertEqual(code_fx, "WORKSPACE_ASSET_MISMATCH")


if __name__ == "__main__":
    unittest.main()
