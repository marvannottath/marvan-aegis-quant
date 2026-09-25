"""
Comprehensive Unit Test Suite for the 14 Institutional Add-ons.
Verifies:
  1. RFC 6238 TOTP 2FA Engine
  2. Zero-Withdrawal API Permission Sentinel
  3. Threat Mitigation, IP Pinning & Canary Honeypot
  4. Self-Healing Thread Supervisor
  5. Microsecond Priority Event Bus
  6. TradingView Webhook Gateway
  7. Portfolio Correlation & Exposure Risk Shield
  8. Transaction Cost Analysis (TCA) Engine
  9. Daily E-Statement Engine & SHA-256 Seal
 10. Market Regime & Fear/Greed Dynamic Sizer
 11. Dashboard API Route Integration
"""

import unittest
import time
import asyncio
from unittest.mock import MagicMock

class TestInstitutionalPlatformSuite(unittest.TestCase):

    def test_01_totp_authenticator(self):
        from core.totp_authenticator import totp_authenticator
        status = totp_authenticator.get_status()
        self.assertTrue(status["is_enabled"])
        self.assertIn("otpauth://totp", status["provisioning_uri"])

        # Generate current code and verify
        current_code = totp_authenticator.generate_current_code()
        self.assertEqual(len(current_code), 6)
        ok, reason = totp_authenticator.verify_code(current_code)
        self.assertTrue(ok)
        self.assertEqual(reason, "TOTP_ACCEPTED")

        # Bogus code rejection
        bad_ok, bad_reason = totp_authenticator.verify_code("000000" if current_code != "000000" else "111111")
        self.assertFalse(bad_ok)

    def test_02_api_permission_sentinel(self):
        from core.api_permission_sentinel import api_permission_sentinel
        
        # Danger Key (Withdrawals = True) must be REJECTED
        danger_key = {
            "enableWithdrawals": True,
            "enableSpotAndMarginTrading": True,
            "enableReading": True
        }
        ok, msg, audit = api_permission_sentinel.inspect_permissions("vmPU123456788c90", danger_key)
        self.assertFalse(ok)
        self.assertIn("CRITICAL_REJECTION", msg)
        self.assertEqual(audit["result"], "REJECTED_DANGER_WITHDRAWAL_ENABLED")

        # Spot-Only Safe Key must PASS
        safe_key = {
            "enableWithdrawals": False,
            "enableSpotAndMarginTrading": True,
            "enableReading": True
        }
        ok_safe, msg_safe, audit_safe = api_permission_sentinel.inspect_permissions("vmPU123456788c90", safe_key)
        self.assertTrue(ok_safe)
        self.assertEqual(audit_safe["result"], "AUTHORIZED_SPOT_ONLY")

    def test_03_threat_mitigation_and_honeypot(self):
        from core.threat_mitigation_engine import threat_mitigation_engine
        
        test_ip = "198.51.100.99"
        threat_mitigation_engine.blacklisted_ips.pop(test_ip, None)
        self.assertFalse(threat_mitigation_engine.is_blacklisted(test_ip))

        # Attacker hits honeypot route
        incident = threat_mitigation_engine.record_honeypot_hit(test_ip, "/wp-admin", "sqlmap/1.4")
        self.assertEqual(incident["severity"], "CRITICAL")
        self.assertTrue(threat_mitigation_engine.is_blacklisted(test_ip))

        # Session pinning check
        sess_ok, _ = threat_mitigation_engine.check_session_pinning("SESS-001", "187.127.189.139", "Mozilla")
        self.assertTrue(sess_ok)
        # Shifted IP
        shift_ok, shift_msg = threat_mitigation_engine.check_session_pinning("SESS-001", "203.0.113.5", "Mozilla")
        self.assertFalse(shift_ok)
        self.assertIn("ANOMALOUS_IP_SHIFT", shift_msg)

    def test_04_thread_supervisor_self_healing(self):
        from core.thread_supervisor import thread_supervisor

        executed = {"count": 0}
        def dummy_worker():
            executed["count"] += 1

        thread_supervisor.register_task("TEST_DAEMON", dummy_worker)
        time.sleep(0.05)
        self.assertIn("TEST_DAEMON", thread_supervisor.tasks)
        self.assertGreaterEqual(executed["count"], 1)

        # Heartbeat recording
        thread_supervisor.record_heartbeat("TEST_DAEMON")
        status = thread_supervisor.get_status()
        self.assertEqual(status["status"], "SUPERVISOR_ACTIVE")

    def test_05_priority_event_bus(self):
        from core.event_bus import event_bus

        received = []
        def handler(payload):
            received.append(payload.get("data"))

        event_bus.subscribe("TEST_TOPIC", handler)
        event_bus.publish("TEST_TOPIC", {"data": "HIGH_PRIORITY_ORDER"}, priority=event_bus.PRIORITY_ORDER)
        time.sleep(0.15)
        self.assertIn("HIGH_PRIORITY_ORDER", received)
        self.assertGreater(event_bus.stats["dispatched_total"], 0)

    def test_06_tradingview_gateway(self):
        from core.tradingview_gateway import tradingview_gateway

        # Unauthorized alert rejected
        unauth_ok, unauth_msg, _ = tradingview_gateway.process_webhook({
            "passphrase": "WRONG_SECRET",
            "symbol": "BTCUSDT",
            "action": "BUY"
        }, "10.0.0.1")
        self.assertFalse(unauth_ok)
        self.assertIn("UNAUTHORIZED", unauth_msg)

        # Authenticated alert processed
        auth_ok, auth_msg, rec = tradingview_gateway.process_webhook({
            "passphrase": "AEGIS_QUANT_SECURE_WEBHOOK_2026",
            "symbol": "BTCUSDT",
            "action": "BUY",
            "price": 68500.0,
            "quantity": 0.05
        }, "10.0.0.1")
        self.assertTrue(auth_ok)
        self.assertEqual(rec["status"], "ORDER_SUBMITTED")

    def test_07_portfolio_correlation_shield(self):
        from core.correlation_shield import correlation_shield

        # High crypto cluster
        positions = [
            {"symbol": "BTCUSDT"},
            {"symbol": "ETHUSDT"},
            {"symbol": "SOLUSDT"}
        ]
        res = correlation_shield.evaluate_portfolio_risk(positions)
        self.assertGreater(res["mean_correlation"], 0.80)
        self.assertTrue(res["is_danger_cluster"])
        self.assertEqual(res["cluster_risk_level"], "CRITICAL_CLUSTER")

        # Diversified multi-asset
        div_positions = [
            {"symbol": "BTCUSDT"},
            {"symbol": "XAUUSD"},
            {"symbol": "NSE:RELIANCE"}
        ]
        div_res = correlation_shield.evaluate_portfolio_risk(div_positions)
        self.assertFalse(div_res["is_danger_cluster"])

    def test_08_transaction_cost_analysis(self):
        from core.tca_analyzer import tca_analyzer

        # Order cost calculation
        cost = tca_analyzer.analyze_order_cost(
            decision_price=65000.0,
            executed_price=65012.0,
            quantity=0.1,
            side="BUY",
            fee_paid=6.50
        )
        self.assertGreater(cost["slippage_bps"], 0.0)
        self.assertGreater(cost["fee_bps"], 0.0)
        self.assertIn("execution_rating", cost)

        # Aggregate report
        agg = tca_analyzer.aggregate_tca_report([])
        self.assertIn("avg_slippage_bps", agg)
        self.assertIn("execution_efficiency_score", agg)

    def test_09_daily_statement_engine(self):
        from core.daily_statement_engine import daily_statement_engine

        stmt = daily_statement_engine.generate_statement()
        self.assertIn("statement_id", stmt)
        self.assertIn("net_pnl_usd", stmt)
        self.assertIn("ledger_sha256", stmt)
        self.assertEqual(len(stmt["ledger_sha256"]), 64)

        html = daily_statement_engine.generate_html_document(stmt)
        self.assertIn("AEGIS QUANTITATIVE CAPITAL", html)
        self.assertIn(stmt["statement_id"], html)

    def test_10_market_regime_sizer(self):
        from core.market_regime_sizer import market_regime_sizer

        # Extreme Fear / High VIX => 0.50x
        market_regime_sizer.update_sentiment(score=18, vix=28.5)
        res_fear = market_regime_sizer.get_sizing_multiplier()
        self.assertEqual(res_fear["sizing_multiplier"], 0.50)
        self.assertEqual(res_fear["sentiment_label"], "EXTREME_FEAR")

        # Steady Bull => 1.00x
        market_regime_sizer.update_sentiment(score=65, vix=13.2)
        res_bull = market_regime_sizer.get_sizing_multiplier()
        self.assertEqual(res_bull["sizing_multiplier"], 1.00)

    def test_11_dashboard_api_routes(self):
        from dashboard.app import (
            get_2fa_status, verify_2fa, get_threat_status,
            get_supervisor_status, receive_tradingview_alert,
            get_portfolio_correlation, get_tca_report,
            get_daily_statement, get_market_regime_sizing,
            honeypot_trap
        )

        # 1. 2FA Status
        r1 = asyncio.run(get_2fa_status())
        self.assertEqual(r1.status_code, 200)

        # 2. 2FA Verify
        class MockReq:
            async def json(self):
                return {"code": "000000"}
        r2 = asyncio.run(verify_2fa(MockReq()))
        self.assertEqual(r2.status_code, 200)

        # 3. Threats Status
        r3 = asyncio.run(get_threat_status())
        self.assertEqual(r3.status_code, 200)

        # 4. Supervisor Status
        r4 = asyncio.run(get_supervisor_status())
        self.assertEqual(r4.status_code, 200)

        # 5. TradingView Webhook
        class MockTvReq:
            def __init__(self):
                self.client = MagicMock()
                self.client.host = "127.0.0.1"
            async def json(self):
                return {
                    "passphrase": "AEGIS_QUANT_SECURE_WEBHOOK_2026",
                    "symbol": "BTCUSDT",
                    "action": "BUY",
                    "price": 68000.0,
                    "quantity": 0.01
                }
        r5 = asyncio.run(receive_tradingview_alert(MockTvReq()))
        self.assertEqual(r5.status_code, 200)

        # 6. Portfolio Correlation
        r6 = asyncio.run(get_portfolio_correlation())
        self.assertEqual(r6.status_code, 200)

        # 7. TCA Report
        r7 = asyncio.run(get_tca_report())
        self.assertEqual(r7.status_code, 200)

        # 8. Daily Statement JSON & HTML
        r8_json = asyncio.run(get_daily_statement(format="json"))
        self.assertEqual(r8_json.status_code, 200)
        r8_html = asyncio.run(get_daily_statement(format="html"))
        self.assertEqual(r8_html.status_code, 200)
        self.assertIn(b"AEGIS QUANTITATIVE CAPITAL", r8_html.body)

        # 9. Market Regime Sizing
        r9 = asyncio.run(get_market_regime_sizing())
        self.assertEqual(r9.status_code, 200)

        # 10. Canary Honeypot Route
        class MockHoneyReq:
            def __init__(self):
                self.client = MagicMock()
                self.client.host = "192.0.2.1"
                self.headers = {"User-Agent": "Scanner/2.0"}
                self.url = MagicMock()
                self.url.path = "/wp-admin"
        r10 = asyncio.run(honeypot_trap(MockHoneyReq()))
        self.assertEqual(r10.status_code, 404)

if __name__ == "__main__":
    unittest.main()
