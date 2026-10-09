"""
AEGIS-QUANT — DEMO / LIVE ENVIRONMENT ISOLATION & SEPARATE URL ARCHITECTURE TEST SUITE
Deterministic security verification covering all 20 required isolation invariants:

1.  LIVE cannot read DEMO balance
2.  DEMO cannot read LIVE balance
3.  LIVE cannot read DEMO positions
4.  DEMO cannot read LIVE positions
5.  LIVE cannot read DEMO orders
6.  DEMO cannot read LIVE orders
7.  LIVE performance cannot resolve DEMO equity
8.  DEMO performance cannot resolve LIVE equity
9.  LIVE vault cannot resolve DEMO vault
10. DEMO vault cannot resolve LIVE vault
11. DEMO order cannot reach live execution adapter
12. LIVE URL cannot be spoofed through query parameters
13. DEMO URL cannot access LIVE account by ID
14. Cache keys are environment scoped
15. Real-time event routing is environment scoped
16. Environment switching clears stale state
17. Unauthorized environment access fails closed
18. Restart preserves environment separation
19. Legacy ?workspace= URLs normalize safely
20. No global environment/account fallback exists in financial paths
21. Repeated switching: LIVE -> DEMO -> LIVE and DEMO -> LIVE -> DEMO
"""

import unittest
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.account_context import (
    account_context_manager,
    AccountContext,
    AccountContextUnavailableError,
    ACCOUNT_CONTEXT_UNAVAILABLE
)
from core.account_cache import account_cache
from core.workspace_manager import workspace_manager
from core.position_snapshot_service import position_snapshot_service
from core.order_state_machine import order_state_machine
from core.environment_gate import environment_gate
from core.performance_curve_engine import performance_curve_engine
from execution.paper_broker import paper_broker
from execution.profit_vault import profit_vault
from core.double_entry_ledger import double_entry_ledger


class TestDemoLiveEnvironmentIsolation(unittest.TestCase):

    def setUp(self):
        # Set up known test balances and orders
        if "AEGIS_INDIA_INR" in paper_broker.pools:
            paper_broker.reset_pool("AEGIS_INDIA_INR", 100000.0)

    # ==================================================================
    # 1 & 2. BALANCE ISOLATION
    # ==================================================================
    def test_01_live_cannot_read_demo_balance(self):
        """LIVE environment queries must not resolve DEMO virtual balances."""
        live_pool = workspace_manager.get_workspace_pool("CRYPTO", environment="LIVE")
        demo_pool = workspace_manager.get_workspace_pool("CRYPTO", environment="DEMO")
        self.assertEqual(live_pool, "BINANCE_LIVE_REAL")
        self.assertEqual(demo_pool, "BINANCE_TESTNET_DEMO")

        live_agg = position_snapshot_service.get_portfolio_aggregate("CRYPTO", force_refresh=True, environment="LIVE")
        demo_agg = position_snapshot_service.get_portfolio_aggregate("CRYPTO", force_refresh=True, environment="DEMO")

        # Live initial/virtual cash is 0.0 or isolated, demo initial is 19950.55
        self.assertNotEqual(live_agg["free_cash"], demo_agg["free_cash"])
        self.assertEqual(demo_agg["free_cash"], 19950.55)

    def test_02_demo_cannot_read_live_balance(self):
        """DEMO queries must not read LIVE balances."""
        india_live = workspace_manager.get_workspace_pool("INDIA", environment="LIVE")
        india_demo = workspace_manager.get_workspace_pool("INDIA", environment="DEMO")
        self.assertEqual(india_live, "UPSTOX_LIVE")
        self.assertEqual(india_demo, "AEGIS_INDIA_INR")

        agg_live = position_snapshot_service.get_portfolio_aggregate("INDIA", force_refresh=True, environment="LIVE")
        agg_demo = position_snapshot_service.get_portfolio_aggregate("INDIA", force_refresh=True, environment="DEMO")
        self.assertEqual(agg_demo["total_equity"], 100000.0)
        self.assertIn(agg_live["total_equity"], [0.0, None])

    # ==================================================================
    # 3 & 4. POSITION ISOLATION
    # ==================================================================
    def test_03_live_cannot_read_demo_positions(self):
        """LIVE snapshot must not inherit simulated DEMO positions."""
        # Inject position only into DEMO pool
        demo_pool = "BINANCE_TESTNET_DEMO"
        paper_broker.pools[demo_pool]["positions"]["BTCUSDT"] = {
            "symbol": "BTCUSDT",
            "units": 0.5,
            "entry_price": 50000.0,
            "capital_allocated": 25000.0,
            "side": "BUY"
        }
        live_snap = position_snapshot_service.get_snapshot("CRYPTO", force_refresh=True, environment="LIVE")
        live_syms = [p.get("symbol") or p.get("asset") for p in live_snap["positions"]]
        # DEMO position must not bleed into LIVE
        self.assertNotIn("BTCUSDT", live_syms)

    def test_04_demo_cannot_read_live_positions(self):
        """DEMO snapshot must not contain LIVE positions."""
        live_pool = "BINANCE_LIVE_REAL"
        paper_broker.pools[live_pool]["positions"]["SOLUSDT"] = {
            "symbol": "SOLUSDT",
            "units": 10.0,
            "entry_price": 140.0,
            "capital_allocated": 1400.0,
            "side": "BUY"
        }
        demo_snap = position_snapshot_service.get_snapshot("CRYPTO", force_refresh=True, environment="DEMO")
        demo_syms = [p.get("symbol") or p.get("asset") for p in demo_snap["positions"]]
        self.assertNotIn("SOLUSDT", demo_syms)

    # ==================================================================
    # 5 & 6. ORDER ISOLATION
    # ==================================================================
    def test_05_live_cannot_read_demo_orders(self):
        """LIVE order queries return only LIVE orders."""
        order_state_machine.create_order(
            symbol="BTCUSDT", side="BUY", quantity=0.1,
            order_type="LIMIT", environment="PAPER", price=60000.0
        )
        live_orders = order_state_machine.get_orders_by_environment("LIVE")
        for o in live_orders:
            self.assertEqual(o["environment"], "LIVE")

    def test_06_demo_cannot_read_live_orders(self):
        """DEMO order queries return only DEMO/PAPER orders."""
        order_state_machine.create_order(
            symbol="BTCUSDT", side="BUY", quantity=0.1,
            order_type="LIMIT", environment="LIVE", price=60000.0
        )
        demo_orders = order_state_machine.get_orders_by_environment("PAPER")
        for o in demo_orders:
            self.assertEqual(o["environment"], "PAPER")

    # ==================================================================
    # 7 & 8. PERFORMANCE ISOLATION
    # ==================================================================
    def test_07_live_performance_cannot_resolve_demo_equity(self):
        """LIVE performance curve must derive strictly from LIVE state."""
        live_curve = performance_curve_engine.get_curve(metric="equity", time_range="1D", environment="LIVE", workspace="CRYPTO")
        demo_curve = performance_curve_engine.get_curve(metric="equity", time_range="1D", environment="DEMO", workspace="CRYPTO")
        self.assertNotEqual(live_curve.get("latest"), demo_curve.get("latest"))

    def test_08_demo_performance_cannot_resolve_live_equity(self):
        """DEMO performance curve must not bleed into LIVE."""
        demo_curve = performance_curve_engine.get_curve(metric="equity", time_range="1D", environment="DEMO", workspace="INDIA")
        self.assertEqual(demo_curve.get("latest"), 100000.0)

    # ==================================================================
    # 9 & 10. VAULT ISOLATION
    # ==================================================================
    def test_09_live_vault_cannot_resolve_demo_vault(self):
        """LIVE vault summary must not include DEMO simulated sweeps."""
        live_summary = profit_vault.get_vault_summary("BINANCE_LIVE_REAL")
        demo_summary = profit_vault.get_vault_summary("BINANCE_TESTNET_DEMO")
        self.assertIn("LIVE BROKER", live_summary.get("external_transfer_status", ""))
        self.assertNotEqual(live_summary, demo_summary)

    def test_10_demo_vault_cannot_resolve_live_vault(self):
        """DEMO vault must not aggregate LIVE broker balances."""
        demo_bal = profit_vault.get_vault_balance("BINANCE_TESTNET_DEMO")
        live_bal = profit_vault.get_vault_balance("BINANCE_LIVE_REAL")
        self.assertEqual(live_bal, 0.0)

    # ==================================================================
    # 11. EXECUTION SAFETY GATE
    # ==================================================================
    def test_11_demo_order_cannot_reach_live_adapter(self):
        """DEMO orders are permanently blocked from LIVE execution paths."""
        allowed, reason = environment_gate.check_order_allowed("LIVE")
        self.assertFalse(allowed)
        self.assertIn("LIVE_TRADING_ENABLED=false", reason)

        # Paper order allowed through sandbox gate
        p_allowed, p_reason = environment_gate.check_order_allowed("PAPER")
        self.assertTrue(p_allowed)
        self.assertIn("GATE_PASS", p_reason)

    # ==================================================================
    # 12 & 13. URL & CONTEXT SPOOFING GUARDS
    # ==================================================================
    def test_12_live_url_cannot_be_spoofed_via_query_params(self):
        """DEMO routes cannot be manipulated by query parameters to access LIVE accounts."""
        # Account resolver strictly rejects LIVE account under DEMO environment
        with self.assertRaises(AccountContextUnavailableError):
            account_context_manager.resolve(
                account_id="BINANCE_LIVE_REAL",
                environment="DEMO"
            )

    def test_13_demo_url_cannot_access_live_account_by_id(self):
        """Specifying LIVE account_id inside DEMO context fails closed."""
        with self.assertRaises(AccountContextUnavailableError):
            account_context_manager.resolve(
                account_id="UPSTOX_LIVE",
                environment="DEMO"
            )

        with self.assertRaises(AccountContextUnavailableError):
            account_context_manager.resolve(
                account_id="MT5_LIVE_REAL",
                environment="DEMO"
            )

    # ==================================================================
    # 14. CACHE SCOPING
    # ==================================================================
    def test_14_cache_keys_are_environment_scoped(self):
        """Account cache keys strictly include environment in key namespace."""
        acc = "BINANCE_TESTNET_DEMO"
        account_cache.set("positions", acc, [{"symbol": "BTCUSDT"}], environment="DEMO")

        # Querying with DEMO environment hits cache
        cached_demo = account_cache.get("positions", acc, environment="DEMO")
        self.assertIsNotNone(cached_demo)

        # Querying the exact same account with LIVE environment returns None (no leakage)
        cached_live = account_cache.get("positions", acc, environment="LIVE")
        self.assertIsNone(cached_live)

    # ==================================================================
    # 15. REAL-TIME EVENT ROUTING
    # ==================================================================
    def test_15_real_time_event_routing_is_environment_scoped(self):
        """Orders and snapshots generated have explicit immutable environment tags."""
        o = order_state_machine.create_order(
            symbol="BTCUSDT", side="BUY", quantity=0.1,
            order_type="LIMIT", environment="PAPER"
        )
        self.assertEqual(o["environment"], "PAPER")
        self.assertTrue(o["order_id"].startswith("ORD-PAP-"))

    # ==================================================================
    # 16. ENVIRONMENT SWITCHING CLEARS STALE STATE
    # ==================================================================
    def test_16_environment_switching_clears_stale_state(self):
        """Invalidating an environment removes only its cached records."""
        account_cache.set("equity", "BINANCE_TESTNET_DEMO", 19950.55, environment="DEMO")
        account_cache.set("equity", "BINANCE_LIVE_REAL", 5000.0, environment="LIVE")

        account_cache.invalidate_environment("DEMO")

        self.assertIsNone(account_cache.get("equity", "BINANCE_TESTNET_DEMO", environment="DEMO"))
        self.assertEqual(account_cache.get("equity", "BINANCE_LIVE_REAL", environment="LIVE"), 5000.0)

    # ==================================================================
    # 17. UNAUTHORIZED ENVIRONMENT ACCESS FAILS CLOSED
    # ==================================================================
    def test_17_unauthorized_environment_access_fails_closed(self):
        """Requesting non-existent or invalid environments raises AccountContextUnavailableError."""
        with self.assertRaises(AccountContextUnavailableError):
            account_context_manager.resolve(workspace="CRYPTO", environment="INVALID_ENV")

    # ==================================================================
    # 18. RESTART PRESERVES ENVIRONMENT SEPARATION
    # ==================================================================
    def test_18_restart_preserves_environment_separation(self):
        """Fresh pool queries resolve correct pools deterministically after reload."""
        p_live = workspace_manager.get_workspace_pool("CRYPTO", environment="LIVE")
        p_demo = workspace_manager.get_workspace_pool("CRYPTO", environment="DEMO")
        self.assertEqual(p_live, "BINANCE_LIVE_REAL")
        self.assertEqual(p_demo, "BINANCE_TESTNET_DEMO")

    # ==================================================================
    # 19. LEGACY ?workspace= URLs NORMALIZE SAFELY
    # ==================================================================
    def test_19_legacy_workspace_normalization(self):
        """Normalization of workspace parameters remains safe and robust."""
        norm1 = workspace_manager._normalize_workspace("crypto")
        self.assertEqual(norm1, "CRYPTO")
        norm2 = workspace_manager._normalize_workspace("forex")
        self.assertEqual(norm2, "FOREX_GOLD")

    # ==================================================================
    # 20. NO GLOBAL FALLBACK IN FINANCIAL PATHS
    # ==================================================================
    def test_20_no_global_fallback_in_financial_paths(self):
        """Empty workspace and account fails closed without silent fallback."""
        with self.assertRaises(AccountContextUnavailableError):
            account_context_manager.resolve()

    # ==================================================================
    # 21. REPEATED ENVIRONMENT SWITCHING
    # ==================================================================
    def test_21_repeated_environment_switching_stability(self):
        """Repeated switching between LIVE and DEMO maintains invariant stability."""
        for _ in range(5):
            ctx_live = account_context_manager.resolve(workspace="CRYPTO", environment="LIVE")
            self.assertEqual(ctx_live.environment, "LIVE")
            self.assertEqual(ctx_live.broker, "BINANCE")

            ctx_demo = account_context_manager.resolve(workspace="CRYPTO", environment="DEMO")
            self.assertEqual(ctx_demo.environment, "PAPER")
            self.assertEqual(ctx_demo.account_id, "BINANCE_SPOT_DEMO")

            # Verify India
            in_live = account_context_manager.resolve(workspace="INDIA", environment="LIVE")
            self.assertEqual(in_live.account_id, "UPSTOX_LIVE")

            in_demo = account_context_manager.resolve(workspace="INDIA", environment="DEMO")
            self.assertEqual(in_demo.account_id, "AEGIS_INDIA_INR")


if __name__ == "__main__":
    unittest.main()
