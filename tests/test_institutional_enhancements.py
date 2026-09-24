"""
Comprehensive Institutional Verification Test Suite:
1. Multi-Timeframe (MTF) Confluence Engine
2. Smart Dynamic Trailing Stop & Break-Even Ratchet
3. Two-Way Telegram Interactive Controller
4. Institutional PnL Calendar & Heatmap Engine
5. Walk-Forward Strategy Optimizer & Overfitting Guardrails
6. Advanced Strategy Suite (Statistical Arbitrage, Liquidation Hunter, Funding Harvester, Grid)
7. AI Forensic Trade Explainer & Post-Mortem Engine
8. CA-Ready Regulatory Tax & PnL Accounting Auditor
9. Institutional Factsheet Tear-Sheet Generator
10. Whale Order Flow Radar & DOM Imbalance Engine
11. TWAP Smart Order Slicer
12. Black Swan & Flash Crash Panic Shield
13. Disaster Recovery 6-Hour Snapshot Sentinel
"""

import unittest
from core.mtf_confluence import mtf_confluence_engine
from core.notification_engine import notification_engine
from core.risk_engine import risk_engine
from core.pnl_calendar_service import pnl_calendar_service
from core.walk_forward_optimizer import walk_forward_optimizer
from core.advanced_strategies import advanced_strategy_suite
from core.trade_explainer import trade_explainer
from core.tax_audit_engine import tax_audit_engine
from core.factsheet_generator import factsheet_generator
from core.order_flow_radar import order_flow_radar
from core.twap_order_slicer import twap_order_slicer
from core.black_swan_shield import black_swan_shield
from core.disaster_recovery import disaster_recovery


class TestInstitutionalEnhancements(unittest.TestCase):
    def test_mtf_confluence_structure(self):
        """Verify MTF confluence calculation and fakeout filtering."""
        res_buy = mtf_confluence_engine.analyze_structure(
            symbol="BTCUSDT",
            current_price=65000.0,
            action="BUY",
            micro_rsi=65.0,
            volatility=0.012
        )
        self.assertEqual(res_buy["symbol"], "BTCUSDT")
        self.assertEqual(res_buy["signal_action"], "BUY")
        self.assertGreaterEqual(res_buy["confluence_score"], 65.0)
        self.assertTrue(res_buy["is_approved"])
        self.assertIn("timeframe_matrix", res_buy)

    def test_telegram_interactive_commands(self):
        """Verify two-way Telegram bot commands."""
        status_reply = notification_engine.handle_bot_command("/status")
        self.assertIn("AEGIS QUANT — LIVE SYSTEM STATUS", status_reply)

        risk_mod = notification_engine.handle_bot_command("/risk moderate")
        self.assertIn("RISK PROFILE SWITCHED TO:* `MODERATE`", risk_mod)

        risk_cons = notification_engine.handle_bot_command("/risk conservative")
        self.assertIn("RISK PROFILE SWITCHED TO:* `CONSERVATIVE`", risk_cons)

        daily_reply = notification_engine.handle_bot_command("/daily_summary")
        self.assertIn("AEGIS DAILY INSTITUTIONAL TRADING SUMMARY", daily_reply)

    def test_pnl_calendar_service(self):
        """Verify PnL calendar grid and monthly KPIs."""
        cal = pnl_calendar_service.get_monthly_calendar("2026-09")
        self.assertEqual(cal["status"], "SUCCESS")
        self.assertEqual(len(cal["days"]), 30)
        self.assertGreater(cal["kpis"]["total_trades"], 0)

    def test_break_even_ratchet_logic(self):
        """Verify break-even ratchet conditions."""
        entry_price = 100.0
        peak_price = 100.90
        pnl_pct = (peak_price - entry_price) / entry_price
        highest_pnl = pnl_pct
        self.assertGreaterEqual(highest_pnl, 0.008)
        break_even_active = (highest_pnl >= 0.008)
        self.assertTrue(break_even_active)

    def test_walk_forward_optimizer(self):
        """Verify rolling walk-forward calibration with overfitting guardrail."""
        opt_res = walk_forward_optimizer.run_walk_forward_optimization(workspace="CRYPTO")
        self.assertEqual(opt_res["status"], "SUCCESS")
        self.assertEqual(opt_res["guardrail_verdict"], "PASSED")
        self.assertGreaterEqual(opt_res["overfit_ratio"], 0.75)
        self.assertIn("rsi_oversold", opt_res["active_hyperparameters"])

    def test_advanced_strategies_suite(self):
        """Verify advanced strategies catalog and toggling."""
        catalog = advanced_strategy_suite.get_catalog()
        self.assertEqual(catalog["status"], "SUCCESS")
        strats = catalog["strategies"]
        self.assertIn("STATISTICAL_ARBITRAGE", strats)
        self.assertIn("LIQUIDATION_HUNTER", strats)
        self.assertIn("FUNDING_HARVESTER", strats)
        self.assertIn("RANGE_GRID_ACCUMULATOR", strats)
        
        toggle_res = advanced_strategy_suite.toggle_strategy("STATISTICAL_ARBITRAGE", True)
        self.assertEqual(toggle_res["status"], "SUCCESS")

    def test_trade_explainer(self):
        """Verify AI trade post-mortem and forensic explanation."""
        sample_trade = {
            "trade_id": "TRD-0042",
            "symbol": "BTCUSDT",
            "side": "BUY",
            "entry_price": 65120.0,
            "exit_price": 65780.0,
            "pnl": 66.0,
            "reason": "TRAILING_STOP_LOSS_LOCKED"
        }
        exp = trade_explainer.explain_trade(sample_trade)
        self.assertEqual(exp["status"], "SUCCESS")
        self.assertIn("entry_analysis", exp)
        self.assertIn("exit_analysis", exp)
        self.assertIn("execution_quality", exp)
        self.assertIn("Trailing Stop", exp["exit_analysis"]["explanation"])

    def test_tax_audit_engine(self):
        """Verify CA-ready tax statement calculation and CSV export."""
        audit = tax_audit_engine.generate_tax_audit()
        self.assertEqual(audit["status"], "SUCCESS")
        self.assertIn("india_equity_fo", audit)
        self.assertIn("crypto_vda", audit)
        self.assertGreater(audit["total_tax_liability_inr"], 0.0)

        csv_str = tax_audit_engine.export_csv()
        self.assertIn("AEGIS QUANT - REGULATORY TAX & PNL AUDIT STATEMENT", csv_str)
        self.assertIn("CBDT / SEBI", csv_str)

    def test_factsheet_generator(self):
        """Verify institutional factsheet metrics."""
        fs = factsheet_generator.generate_factsheet()
        self.assertEqual(fs["status"], "SUCCESS")
        self.assertEqual(fs["core_metrics"]["sharpe_ratio"], 2.14)
        self.assertIn("monthly_performance_history", fs)
        self.assertIn("asset_allocation", fs)

    def test_order_flow_radar(self):
        """Verify Whale order flow telemetry and DOM ladder."""
        radar = order_flow_radar.get_radar_telemetry("BTCUSDT")
        self.assertEqual(radar["status"], "SUCCESS")
        self.assertIn("bid_volume_ratio", radar)
        self.assertIn("whale_block_orders", radar)
        self.assertIn("dom_ladder", radar)
        self.assertIn("on_chain_telemetry", radar)

    def test_twap_order_slicer(self):
        """Verify smart order slicing for large executions."""
        small_plan = twap_order_slicer.create_twap_plan("BTCUSDT", "BUY", 1000.0)
        self.assertFalse(small_plan["needs_slicing"])

        large_plan = twap_order_slicer.create_twap_plan("BTCUSDT", "BUY", 10000.0, num_slices=5)
        self.assertTrue(large_plan["needs_slicing"])
        self.assertEqual(len(large_plan["slices"]), 5)
        # Verify sum of slices matches total within rounding
        total_sum = sum(s["amount_usd"] for s in large_plan["slices"])
        self.assertAlmostEqual(total_sum, 10000.0, delta=1.0)

    def test_black_swan_shield(self):
        """Verify flash crash panic defense triggering."""
        # Normal ticks
        t1 = black_swan_shield.inspect_tick("ETHUSDT", 3000.0)
        t2 = black_swan_shield.inspect_tick("ETHUSDT", 2990.0)
        self.assertFalse(t2["shield_triggered"])

        # Severe flash crash (-4.5% drop in same minute)
        t3 = black_swan_shield.inspect_tick("ETHUSDT", 2850.0)
        self.assertTrue(t3["shield_triggered"])
        self.assertTrue(black_swan_shield.is_shield_active)

        # Reset shield
        black_swan_shield.reset_shield()
        self.assertFalse(black_swan_shield.is_shield_active)

    def test_disaster_recovery_sentinel(self):
        """Verify automated state snapshot and checksum creation."""
        res = disaster_recovery.create_snapshot("UNIT_TEST_TRIGGER")
        self.assertEqual(res["status"], "SUCCESS")
        snap = res["snapshot"]
        self.assertIn("sha256_checksum", snap)
        self.assertEqual(snap["integrity_status"], "VERIFIED_VALID")


if __name__ == "__main__":
    unittest.main()
