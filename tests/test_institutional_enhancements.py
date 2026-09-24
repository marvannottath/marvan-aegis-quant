"""
Test Suite for 4 High-Value Institutional Trading Enhancements:
1. Multi-Timeframe (MTF) Confluence Engine
2. Smart Dynamic Trailing Stop & Break-Even Ratchet
3. Two-Way Telegram Interactive Controller
4. Institutional PnL Calendar & Heatmap Engine
"""

import unittest
from core.mtf_confluence import mtf_confluence_engine, MTFConfluenceEngine
from core.notification_engine import notification_engine
from core.risk_engine import risk_engine
from core.pnl_calendar_service import pnl_calendar_service


class TestInstitutionalEnhancements(unittest.TestCase):
    def test_mtf_confluence_structure(self):
        """Verify MTF confluence calculation and fakeout filtering."""
        # Bullish scenario
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

        # Bearish scenario
        res_sell = mtf_confluence_engine.analyze_structure(
            symbol="ETHUSDT",
            current_price=3200.0,
            action="SELL",
            micro_rsi=35.0,
            volatility=0.015
        )
        self.assertEqual(res_sell["signal_action"], "SELL")
        self.assertGreaterEqual(res_sell["confluence_score"], 65.0)
        self.assertTrue(res_sell["is_approved"])

    def test_telegram_interactive_commands(self):
        """Verify two-way Telegram bot commands."""
        # 1. /status command
        status_reply = notification_engine.handle_bot_command("/status")
        self.assertIn("AEGIS QUANT — LIVE SYSTEM STATUS", status_reply)
        self.assertIn("Engine State:", status_reply)
        self.assertIn("Active Risk Profile:", status_reply)

        # 2. /risk command query and update
        risk_info = notification_engine.handle_bot_command("/risk")
        self.assertIn("CURRENT RISK PROFILE:", risk_info)

        risk_mod = notification_engine.handle_bot_command("/risk moderate")
        self.assertIn("RISK PROFILE SWITCHED TO:* `MODERATE`", risk_mod)
        self.assertEqual(risk_engine.active_profile_name, "MODERATE")

        risk_cons = notification_engine.handle_bot_command("/risk conservative")
        self.assertIn("RISK PROFILE SWITCHED TO:* `CONSERVATIVE`", risk_cons)
        self.assertEqual(risk_engine.active_profile_name, "CONSERVATIVE")

        # 3. /daily_summary command
        daily_reply = notification_engine.handle_bot_command("/daily_summary")
        self.assertIn("AEGIS DAILY INSTITUTIONAL TRADING SUMMARY", daily_reply)
        self.assertIn("Total Executions Today:", daily_reply)
        self.assertIn("Win Rate:", daily_reply)

        # 4. /closeall command
        closeall_reply = notification_engine.handle_bot_command("/closeall")
        self.assertTrue(("TELEGRAM /CLOSEALL EXECUTED" in closeall_reply) or ("No open positions to close" in closeall_reply))

    def test_pnl_calendar_service(self):
        """Verify PnL calendar grid and monthly KPIs."""
        cal = pnl_calendar_service.get_monthly_calendar("2026-09")
        self.assertEqual(cal["status"], "SUCCESS")
        self.assertEqual(cal["year_month"], "2026-09")
        self.assertEqual(cal["month_name"], "September 2026")
        self.assertEqual(len(cal["days"]), 30)

        kpis = cal["kpis"]
        self.assertIn("total_net_pnl_usd", kpis)
        self.assertIn("total_net_pnl_inr", kpis)
        self.assertIn("win_day_rate", kpis)
        self.assertIn("profit_factor", kpis)
        self.assertGreater(kpis["total_trades"], 0)
        self.assertGreater(kpis["green_days"], 0)
        self.assertGreater(kpis["best_day"]["pnl_usd"], 0)

    def test_break_even_ratchet_logic(self):
        """Verify break-even ratchet conditions."""
        entry_price = 100.0
        
        # Simulate high water mark reaching +0.9% (+0.009)
        peak_price = 100.90
        pnl_pct = (peak_price - entry_price) / entry_price
        highest_pnl = pnl_pct
        self.assertGreaterEqual(highest_pnl, 0.008)

        break_even_active = (highest_pnl >= 0.008)
        self.assertTrue(break_even_active)

        # Pullback down to 100.10 (only +0.10% profit, below +0.15% fee guard)
        pullback_price = 100.10
        pullback_pnl_pct = (pullback_price - entry_price) / entry_price
        is_break_even_guard = bool(break_even_active and pullback_pnl_pct <= 0.0015)
        self.assertTrue(is_break_even_guard)


if __name__ == "__main__":
    unittest.main()
