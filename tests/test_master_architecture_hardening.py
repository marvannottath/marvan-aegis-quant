"""
AEGIS-QUANT — MASTER ARCHITECTURE HARDENING VERIFICATION TEST SUITE
Deterministic verification across all core architecture modules:
1. Account Context & Fail-Closed Isolation
2. Account Scoped Cache Isolation
3. Authoritative Trade Economics & Cost PnL Engine
4. Capital Availability & Residual/Dust Classification
5. Dynamic Risk Policy Versioning, Impact Preview & 1-Click Rollback
6. Standardized Broker Adapter Contract
7. Order State Machine & Partial Fills / Idempotency
8. Market Regime Awareness & Dynamic Capital-Scaled Sizing
9. System Safety Enforcements (Fail-Closed, Live Locked, Withdrawals Locked)
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
from core.cost_pnl_engine import cost_pnl_engine, TradeEconomics
from core.capital_availability_engine import (
    capital_availability_engine,
    STATUS_TRADEABLE,
    STATUS_RESIDUAL,
    STATUS_LOCKED,
    STATUS_PENDING_SETTLEMENT
)
from core.risk_policy_versioning import risk_policy_manager
from core.risk_engine import risk_engine
from core.broker_adapter import BrokerAdapter
from core.order_state_machine import order_state_machine
from core.market_regime_sizer import market_regime_sizer
from core.environment_gate import environment_gate
from core.continuous_learner import continuous_learner


class TestMasterArchitectureHardening(unittest.TestCase):

    # ==================================================================
    # 1. ACCOUNT CONTEXT — SINGLE SOURCE OF TRUTH & FAIL-CLOSED
    # ==================================================================
    def test_01_account_context_resolution(self):
        """Account context resolves correctly for all native venues."""
        ctx_crypto = account_context_manager.resolve(workspace="CRYPTO", environment="PAPER")
        self.assertEqual(ctx_crypto.currency, "USDT")
        self.assertEqual(ctx_crypto.broker, "BINANCE")
        self.assertEqual(ctx_crypto.workspace, "CRYPTO")

        ctx_india = account_context_manager.resolve(workspace="INDIA")
        self.assertEqual(ctx_india.currency, "INR")
        self.assertEqual(ctx_india.broker, "UPSTOX")
        self.assertEqual(ctx_india.currency_symbol, "₹")

        ctx_forex = account_context_manager.resolve(workspace="FOREX_GOLD")
        self.assertEqual(ctx_forex.currency, "USD")
        self.assertIn("FOREX", ctx_forex.instruments)

    def test_02_account_context_fail_closed_on_unresolved(self):
        """Account context FAILS CLOSED with AccountContextUnavailableError when unknown."""
        with self.assertRaises(AccountContextUnavailableError):
            account_context_manager.resolve(account_id="NON_EXISTENT_UNKNOWN_ACCOUNT")

        with self.assertRaises(AccountContextUnavailableError):
            account_context_manager.resolve(workspace="INVALID_WORKSPACE_NAME")

        with self.assertRaises(AccountContextUnavailableError):
            # Mismatched account_id and workspace must fail closed
            account_context_manager.resolve(account_id="BINANCE_SPOT_DEMO", workspace="INDIA")

    def test_03_account_context_no_silent_crypto_default(self):
        """Resolving without parameters or invalid inputs never silently returns CRYPTO."""
        with self.assertRaises(AccountContextUnavailableError):
            account_context_manager.resolve(workspace="UNKNOWN_MARKET")

    # ==================================================================
    # 2. CACHE ISOLATION & ZERO DATA MIXING
    # ==================================================================
    def test_04_account_cache_isolation(self):
        """Caches are strictly scoped to account_id with zero cross-account bleeding."""
        acc1 = "BINANCE_SPOT_DEMO"
        acc2 = "AEGIS_INDIA_INR"

        account_cache.set(acc1, "positions", [{"symbol": "BTCUSDT", "qty": 0.5}])
        account_cache.set(acc2, "positions", [{"symbol": "RELIANCE", "qty": 10}])

        pos1 = account_cache.get(acc1, "positions")
        pos2 = account_cache.get(acc2, "positions")

        self.assertEqual(len(pos1), 1)
        self.assertEqual(pos1[0]["symbol"], "BTCUSDT")
        self.assertEqual(len(pos2), 1)
        self.assertEqual(pos2[0]["symbol"], "RELIANCE")

        # Switching account invalidates previous active view cache safely
        account_cache.switch_account(acc1, acc2)
        # Account 2 cache remains intact
        self.assertIsNotNone(account_cache.get(acc2, "positions"))

    # ==================================================================
    # 3. COST + PNL ENGINE & AUTHORITATIVE TRADE ECONOMICS
    # ==================================================================
    def test_05_trade_economics_crypto_calculation(self):
        """Binance trade economics deducts maker/taker fee, slippage, and spread."""
        econ = cost_pnl_engine.calculate_trade_economics(
            symbol="BTCUSDT",
            side="BUY",
            quantity=0.1,
            entry_price=60000.0,
            exit_price=61000.0,
            currency="USDT",
            instrument="SPOT",
            broker="BINANCE"
        )
        self.assertIsInstance(econ, TradeEconomics)
        self.assertEqual(econ.gross_pnl, 100.0)  # (61000 - 60000) * 0.1 = 100.0
        self.assertGreater(econ.total_costs, 0.0)
        # Net PnL must equal gross minus total costs
        self.assertEqual(econ.net_pnl, round(econ.gross_pnl - econ.total_costs, 2))
        self.assertTrue(econ.is_profit)

    def test_06_trade_economics_india_statutory_taxes(self):
        """Upstox India trade economics includes brokerage, STT, turnover, and GST."""
        econ = cost_pnl_engine.calculate_trade_economics(
            symbol="RELIANCE",
            side="BUY",
            quantity=10,
            entry_price=2500.0,
            exit_price=2600.0,
            currency="INR",
            instrument="EQUITY",
            broker="UPSTOX"
        )
        self.assertEqual(econ.gross_pnl, 1000.0)
        self.assertGreater(econ.taxes_charges, 0.0)  # STT + GST + turnover
        self.assertEqual(econ.net_pnl, round(1000.0 - econ.total_costs, 2))

    # ==================================================================
    # 4. CAPITAL AVAILABILITY & RESIDUAL/DUST ENGINE
    # ==================================================================
    def test_07_capital_availability_9_bucket_breakdown(self):
        """9-bucket capital availability breakdown correctly computes deployable capital."""
        breakdown = capital_availability_engine.compute_breakdown(
            account_id="BINANCE_TEST",
            total_equity=10000.0,
            broker_balance=10000.0,
            available_cash=5000.0,
            used_margin=2000.0,
            reserved_cash=1000.0,
            open_orders_reserved=500.0,
            residual_dust_capital=50.0,
            safety_buffer_pct=2.0,  # 2% of 10000 = 200
            currency="USDT",
            broker="BINANCE"
        )
        # Deductions = reserved (1000) + orders (500) + dust (50) + buffer (200) = 1750
        # Tradeable = 5000 - 1750 = 3250
        self.assertEqual(breakdown.tradeable_capital, 3250.0)
        self.assertTrue(breakdown.can_open_new_trades)

    def test_08_residual_dust_classification(self):
        """Dust assets below min notional are classified RESIDUAL without blocking engine."""
        # 0.00001 BTC at $60000 = $0.60 notional (below Binance $5.00 min)
        dust = capital_availability_engine.classify_asset("BTCUSDT", 0.00001, 60000.0, broker="BINANCE")
        self.assertEqual(dust["status"], STATUS_RESIDUAL)

        # 0.001 BTC at $60000 = $60.00 notional (above Binance $5.00 min)
        tradeable = capital_availability_engine.classify_asset("BTCUSDT", 0.001, 60000.0, broker="BINANCE")
        self.assertEqual(tradeable["status"], STATUS_TRADEABLE)

        # Locked collateral
        locked = capital_availability_engine.classify_asset("BTCUSDT", 0.1, 60000.0, is_locked=True)
        self.assertEqual(locked["status"], STATUS_LOCKED)

    # ==================================================================
    # 5. DYNAMIC RISK POLICY VERSIONING & 1-CLICK ROLLBACK
    # ==================================================================
    def test_09_risk_policy_preview_and_apply(self):
        """Two-phase risk change: preview -> impact calculation -> apply -> rollback."""
        current = risk_engine.get_profile_summary()
        proposed = {"max_leverage": 5.0, "max_risk_per_trade_pct": 2.0}

        preview = risk_policy_manager.preview_risk_change(
            account_id="CRYPTO_MAIN",
            workspace="CRYPTO",
            current_state=current,
            proposed_state=proposed,
            account_equity=10000.0,
            current_exposure=1000.0,
            open_positions_count=2,
            tradeable_capital=8000.0
        )
        self.assertIn(preview.risk_level, ["LOW", "MEDIUM", "HIGH", "CRITICAL"])
        self.assertEqual(preview.status, "PENDING_CONFIRMATION")

        # Apply confirmed change
        res = risk_policy_manager.apply_confirmed_change(preview.preview_id, confirmed=True, user_actor="ADMIN")
        self.assertEqual(res["status"], "APPLIED")
        self.assertTrue(res["version"].startswith("v"))

        # 1-Click Rollback
        rollback_res = risk_policy_manager.rollback_to_previous_policy(user_actor="ADMIN")
        self.assertEqual(rollback_res["status"], "ROLLED_BACK")

    # ==================================================================
    # 6. STANDARDIZED BROKER ADAPTER CONTRACT
    # ==================================================================
    def test_10_broker_adapter_truthful_contract(self):
        """BrokerAdapter contract returns UNKNOWN rather than inventing status."""
        class MockUnconfiguredAdapter(BrokerAdapter):
            @property
            def broker_name(self): return "MOCK"
            @property
            def status(self): return "NOT_CONFIGURED"
            def connect(self): return False
            def get_account(self): return {"status": "UNCONFIGURED"}
            def get_balance(self): return {}
            def get_available_balance(self, asset="USDT"): return 0.0
            def get_positions(self): return []
            def get_orders(self): return []
            def place_order(self, symbol, side, order_type, quantity, price=None, params=None): return {}
            def cancel_order(self, order_id, symbol=None): return False
            def close_position(self, symbol): return False
            def get_market_data(self, symbol): return {}

        adapter = MockUnconfiguredAdapter()
        status = adapter.get_market_status()
        self.assertEqual(status, "UNKNOWN")
        rules = adapter.get_trading_rules("BTCUSDT")
        self.assertEqual(rules.get("session"), "UNKNOWN")
        constraints = adapter.get_symbol_constraints("BTCUSDT")
        self.assertEqual(constraints.get("min_notional"), "UNKNOWN")

    # ==================================================================
    # 7. ORDER STATE MACHINE & PARTIAL FILLS / IDEMPOTENCY
    # ==================================================================
    def test_11_order_state_machine_lifecycle_and_partial_fills(self):
        """Order state machine tracks requested vs executed vs remaining quantities."""
        order = order_state_machine.create_order(
            symbol="BTCUSDT",
            side="BUY",
            quantity=1.0,
            order_type="LIMIT",
            environment="PAPER",
            price=60000.0,
            metadata={"instrument": "SPOT"}
        )
        self.assertEqual(order["status"], "CREATED")
        order_id = order["order_id"]

        # Transition to RISK_PENDING -> APPROVED -> SUBMITTED -> ACKNOWLEDGED
        order_state_machine.transition(order_id, "RISK_PENDING", reason="Risk evaluation")
        order_state_machine.transition(order_id, "APPROVED", reason="Approved by risk engine")
        order_state_machine.transition(order_id, "SUBMITTED", reason="Sent to broker")
        order_state_machine.transition(order_id, "ACKNOWLEDGED", reason="Broker accepted")

        # Partial Fill: 0.4 BTC filled
        p_order = order_state_machine.transition(
            order_id, "PARTIALLY_FILLED",
            fill_qty=0.4,
            avg_fill_price=60000.0,
            reason="Partial fill 40%"
        )
        self.assertEqual(p_order["executed_quantity"], 0.4)
        self.assertEqual(p_order["remaining_quantity"], 0.6)

        # Full Fill: remaining 0.6 BTC filled with execution record
        exec_record = {"broker_tx_id": "TX-12345", "fill_time": "2026-10-08"}
        f_order = order_state_machine.transition(
            order_id, "FILLED",
            fill_qty=1.0,
            avg_fill_price=60010.0,
            execution_record=exec_record,
            reason="Completed"
        )
        self.assertEqual(f_order["status"], "FILLED")
        self.assertEqual(f_order["executed_quantity"], 1.0)
        self.assertEqual(f_order["remaining_quantity"], 0.0)

    # ==================================================================
    # 8. MARKET REGIME AWARENESS & DYNAMIC POSITION SIZING
    # ==================================================================
    def test_12_market_regime_and_position_sizing(self):
        """Position sizing scales dynamically with tradeable capital and regime scalar."""
        market_regime_sizer.update_sentiment(score=65, vix=14.0, condition="TRENDING")
        regime = market_regime_sizer.determine_regime(workspace="CRYPTO")
        self.assertEqual(regime["regime"], "TRENDING")
        self.assertGreater(regime["sizing_multiplier"], 0.5)

        # Position sizing is a function of tradeable capital
        size_low_cap = risk_engine.calculate_capital_scaled_position_size(
            tradeable_capital=20.0,
            volatility=0.01,
            confidence_score=80.0,
            regime_scalar=regime["sizing_multiplier"],
            broker_min_notional=5.0
        )
        size_high_cap = risk_engine.calculate_capital_scaled_position_size(
            tradeable_capital=10000.0,
            volatility=0.01,
            confidence_score=80.0,
            regime_scalar=regime["sizing_multiplier"],
            broker_min_notional=5.0
        )
        self.assertGreater(size_high_cap, size_low_cap)
        # Must not exceed tradeable capital
        self.assertLessEqual(size_low_cap, 20.0)

    # ==================================================================
    # 9. FAIL-CLOSED SAFETY ENFORCEMENTS
    # ==================================================================
    def test_13_fail_closed_environment_gate(self):
        """Live trading and withdrawals remain permanently locked by default."""
        allowed, reason = environment_gate.check_order_allowed(environment="LIVE")
        self.assertFalse(allowed)
        self.assertIn("LIVE_TRADING_ENABLED=false", reason)

        wd_allowed, wd_reason = environment_gate.check_withdrawal_allowed(environment="LIVE")
        self.assertFalse(wd_allowed)
        self.assertIn("LIVE_WITHDRAWALS_ENABLED=false", wd_reason)

    # ==================================================================
    # 10. CONTINUOUS LEARNER MODEL VERSIONING & SWITCHING
    # ==================================================================
    def test_14_ai_model_catalog_and_version_switching(self):
        """Model catalog returns validated models and switches champions safely for NEW TRADES ONLY."""
        continuous_learner.state["champion_version"] = "v2.0.0-BREAKOUT"
        catalog = continuous_learner.get_model_catalog()
        self.assertIn("active_version", catalog)
        self.assertEqual(len(catalog["models"]), 3)
        self.assertEqual(catalog["scope"], "NEW_TRADES_ONLY")

        # Test switching to Model v3
        res = continuous_learner.switch_model("v3.0.0-CONSENSUS", user_actor="TEST_RUNNER", reason="Higher Sharpe")
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["active_version"], "v3.0.0-CONSENSUS")
        self.assertEqual(res["scope"], "NEW_TRADES_ONLY")

        # Verify active catalog reflects switch
        new_catalog = continuous_learner.get_model_catalog()
        self.assertEqual(new_catalog["active_version"], "v3.0.0-CONSENSUS")
        self.assertGreater(len(new_catalog["version_history"]), 0)

        # Invalid model must fail gracefully
        err = continuous_learner.switch_model("INVALID_VERSION_99")
        self.assertEqual(err["status"], "ERROR")

    def test_15_ai_model_compare_and_rollback(self):
        """Model comparison computes parameter deltas and rollback restores previous version."""
        cmp = continuous_learner.compare_models("v1.0.0-CONSERVATIVE", "v3.0.0-CONSENSUS")
        self.assertEqual(cmp["status"], "SUCCESS")
        self.assertGreater(cmp["delta_win_rate"], 0)
        self.assertGreater(cmp["delta_sharpe"], 0)

        # Switch to v1 then rollback to v3
        continuous_learner.switch_model("v1.0.0-CONSERVATIVE", user_actor="TEST_RUNNER", reason="Test switch")
        self.assertEqual(continuous_learner.get_model_catalog()["active_version"], "v1.0.0-CONSERVATIVE")

        rb = continuous_learner.rollback_model(user_actor="TEST_RUNNER")
        self.assertEqual(rb["status"], "SUCCESS")
        self.assertEqual(rb["active_version"], "v3.0.0-CONSENSUS")


if __name__ == "__main__":
    unittest.main()
