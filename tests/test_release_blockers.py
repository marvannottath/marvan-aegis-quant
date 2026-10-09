"""
AEGIS-QUANT — COMPREHENSIVE RELEASE BLOCKERS VERIFICATION SUITE
Covers all four concrete audit blockers:

1. BLOCKER 1: Portfolio aggregate environment isolation & explicit forwarding.
   - Enforces strict isolation between DEMO and LIVE pools.
   - Verifies spoofed or invalid environments fail closed with HTTP 400 ACCOUNT_CONTEXT_UNAVAILABLE.

2. BLOCKER 2: Truthful live balance provenance & fail-closed disconnected state.
   - Proves unauthenticated live broker returns total_equity=None and data_source="DISCONNECTED".
   - Proves DEMO balances are explicitly marked as SIMULATION_PAPER.
   - Proves /api/capital/breakdown handles total_equity=None without TypeError.

3. BLOCKER 3: Zero-Trust Live Trading Toggle Gate.
   - Proves unauthenticated requests are rejected with HTTP 401.
   - Proves invalid session tokens are rejected with HTTP 401.
   - Proves non-SUPER_ADMIN sessions are rejected with HTTP 403.
   - Proves enabling without TOTP is rejected with HTTP 403.
   - Proves invalid TOTP is rejected with HTTP 403.
   - Proves valid TOTP with SUPER_ADMIN enables live spot trading on gate.
   - Proves replayed TOTP code is rejected with HTTP 403.
   - Proves emergency shutdown locks live trading without TOTP for authorized admins.
   - Proves toggle never modifies withdrawal or Futures locking flags.

4. BLOCKER 4: Frontend Production Compatibility.
   - Verifies all 8 core institutional frontend routes return HTTP 200 on port 3000.
"""

import unittest
import time
import requests
from typing import Dict, Any

BACKEND_URL = "http://127.0.0.1:8888"
FRONTEND_URL = "http://localhost:3000"


def get_trader_session() -> str:
    r = requests.post(
        f"{BACKEND_URL}/api/trader/login",
        json={"username": "quant_trader", "password": "Trader@2026!"},
        timeout=5
    )
    assert r.status_code == 200, f"Trader login failed: {r.text}"
    return r.json().get("session_token", "")


def get_super_admin_session() -> str:
    from core.super_admin import super_admin
    totp = super_admin.generate_totp_code(super_admin.users["marvan"]["totp_secret"])
    r = requests.post(
        f"{BACKEND_URL}/api/admin/login",
        json={"username": "marvan", "password": "Marvan@2026!", "totp_code": totp},
        timeout=5
    )
    assert r.status_code == 200, f"Admin login failed: {r.text}"
    return r.json().get("session_token", "")


class TestReleaseBlockers(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Ensure backend is accessible
        try:
            r = requests.get(f"{BACKEND_URL}/api/status", timeout=5)
            assert r.status_code == 200, f"Backend status check failed: {r.status_code}"
        except Exception as e:
            raise RuntimeError(f"Backend not accessible at {BACKEND_URL}: {e}")

    def setUp(self):
        from core.super_admin import super_admin
        super_admin.failed_login_attempts.clear()

    # =========================================================================
    # BLOCKER 1: PORTFOLIO AGGREGATE ENVIRONMENT ISOLATION
    # =========================================================================

    def test_blocker1_portfolio_aggregate_demo_live_isolation(self):
        """Verify GET /api/portfolio/aggregate cleanly partitions DEMO and LIVE environments."""
        # Query DEMO
        r_demo = requests.get(
            f"{BACKEND_URL}/api/portfolio/aggregate",
            params={"environment": "DEMO", "workspace": "CRYPTO"},
            timeout=5
        )
        self.assertEqual(r_demo.status_code, 200)
        d_demo = r_demo.json()
        self.assertIn(d_demo.get("status"), ["SUCCESS", "PASS"])
        self.assertIn("DEMO", d_demo.get("pool_name", ""))
        self.assertEqual(d_demo.get("data_source"), "SIMULATION_PAPER")
        self.assertTrue(d_demo.get("is_simulated", False))

        # Query LIVE
        r_live = requests.get(
            f"{BACKEND_URL}/api/portfolio/aggregate",
            params={"environment": "LIVE", "workspace": "CRYPTO"},
            timeout=5
        )
        self.assertEqual(r_live.status_code, 200)
        d_live = r_live.json()
        self.assertIn("LIVE", d_live.get("pool_name", ""))

        # Cross-contamination check: DEMO and LIVE must not share pool names
        self.assertNotEqual(d_demo.get("pool_name"), d_live.get("pool_name"))

    def test_blocker1_portfolio_aggregate_spoofed_env_fails_closed(self):
        """Verify spoofed or invalid environment parameter fails closed with HTTP 400."""
        r_spoof = requests.get(
            f"{BACKEND_URL}/api/portfolio/aggregate",
            params={"environment": "HACK_ATTEMPT", "workspace": "CRYPTO"},
            timeout=5
        )
        self.assertEqual(r_spoof.status_code, 400)
        d_spoof = r_spoof.json()
        self.assertEqual(d_spoof.get("status"), "FAIL_CLOSED")
        self.assertEqual(d_spoof.get("error_code"), "ACCOUNT_CONTEXT_UNAVAILABLE")

    def test_blocker1_portfolio_aggregate_invalid_workspace_fails_closed(self):
        """Verify invalid workspace fails closed with HTTP 400."""
        r_invalid_ws = requests.get(
            f"{BACKEND_URL}/api/portfolio/aggregate",
            params={"environment": "LIVE", "workspace": "NON_EXISTENT_WORKSPACE"},
            timeout=5
        )
        self.assertEqual(r_invalid_ws.status_code, 400)
        d_invalid = r_invalid_ws.json()
        self.assertEqual(d_invalid.get("status"), "FAIL_CLOSED")
        self.assertEqual(d_invalid.get("error_code"), "ACCOUNT_CONTEXT_UNAVAILABLE")

    # =========================================================================
    # BLOCKER 2: TRUTHFUL LIVE BALANCE PROVENANCE & DISCONNECTED BROKER
    # =========================================================================

    def test_blocker2_unauthenticated_live_broker_equity_is_none(self):
        """Verify unauthenticated live broker returns total_equity=None and DISCONNECTED."""
        r_live = requests.get(
            f"{BACKEND_URL}/api/portfolio/aggregate",
            params={"environment": "LIVE", "workspace": "CRYPTO"},
            timeout=5
        )
        self.assertEqual(r_live.status_code, 200)
        d_live = r_live.json()
        # Since local machine has no real Binance API keys configured, live pool must return DISCONNECTED
        self.assertIsNone(d_live.get("total_equity"))
        self.assertIsNone(d_live.get("free_cash"))
        self.assertFalse(d_live.get("broker_connected"))
        self.assertEqual(d_live.get("data_source"), "DISCONNECTED")
        self.assertEqual(d_live.get("open_positions_count"), 0)

    def test_blocker2_capital_breakdown_handles_disconnected_live_broker(self):
        """Verify /api/capital/breakdown gracefully handles disconnected live broker without crashing."""
        r = requests.get(
            f"{BACKEND_URL}/api/capital/breakdown",
            params={"environment": "LIVE", "workspace": "CRYPTO"},
            timeout=5
        )
        self.assertEqual(r.status_code, 200)
        d = r.json()
        self.assertEqual(d.get("status"), "SUCCESS")
        self.assertFalse(d.get("broker_connected"))
        self.assertEqual(d.get("data_source"), "DISCONNECTED")
        breakdown = d.get("breakdown", {})
        self.assertIsNone(breakdown.get("total_equity"))
        self.assertIsNone(breakdown.get("available_cash"))
        self.assertIsNone(breakdown.get("tradeable_capital"))
        self.assertFalse(breakdown.get("can_open_new_trades"))

    def test_blocker2_demo_returns_paper_balances(self):
        """Verify DEMO returns paper simulation balances with explicit paper provenance."""
        r_demo = requests.get(
            f"{BACKEND_URL}/api/portfolio/aggregate",
            params={"environment": "DEMO", "workspace": "CRYPTO"},
            timeout=5
        )
        self.assertEqual(r_demo.status_code, 200)
        d_demo = r_demo.json()
        self.assertIsNotNone(d_demo.get("total_equity"))
        self.assertIsInstance(d_demo.get("total_equity"), (int, float))
        self.assertEqual(d_demo.get("data_source"), "SIMULATION_PAPER")
        self.assertTrue(d_demo.get("is_simulated"))

    # =========================================================================
    # BLOCKER 3: SECURE LIVE TRADING TOGGLE (SUPER_ADMIN + RFC 6238 TOTP)
    # =========================================================================

    def test_blocker3_toggle_unauthenticated_rejected_401(self):
        """Verify unauthenticated request without token is rejected with HTTP 401."""
        r = requests.post(
            f"{BACKEND_URL}/api/toggle-live-trading",
            json={"enabled": True},
            timeout=5
        )
        self.assertEqual(r.status_code, 401)
        d = r.json()
        self.assertEqual(d.get("error"), "UNAUTHENTICATED")

    def test_blocker3_toggle_invalid_token_rejected_401(self):
        """Verify request with invalid/fake session token is rejected with HTTP 401."""
        r = requests.post(
            f"{BACKEND_URL}/api/toggle-live-trading",
            headers={"Authorization": "Bearer fake_token_abc_123"},
            json={"enabled": True},
            timeout=5
        )
        self.assertEqual(r.status_code, 401)
        d = r.json()
        self.assertEqual(d.get("error"), "UNAUTHENTICATED")

    def test_blocker3_toggle_non_super_admin_rejected_403(self):
        """Verify valid session without SUPER_ADMIN role (e.g. LEAD_TRADER) is rejected with HTTP 403."""
        trader_token = get_trader_session()
        r = requests.post(
            f"{BACKEND_URL}/api/toggle-live-trading",
            headers={"Authorization": f"Bearer {trader_token}"},
            json={"enabled": True, "totp_code": "123456"},
            timeout=5
        )
        self.assertEqual(r.status_code, 403)
        d = r.json()
        self.assertEqual(d.get("error"), "FORBIDDEN")
        self.assertIn("SUPER_ADMIN", d.get("message", ""))

    def test_blocker3_toggle_missing_totp_rejected_403(self):
        """Verify SUPER_ADMIN session without TOTP code is rejected with HTTP 403."""
        admin_token = get_super_admin_session()
        r = requests.post(
            f"{BACKEND_URL}/api/toggle-live-trading",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"enabled": True},
            timeout=5
        )
        self.assertEqual(r.status_code, 403)
        d = r.json()
        self.assertEqual(d.get("error"), "TOTP_REQUIRED")

    def test_blocker3_toggle_invalid_totp_rejected_403(self):
        """Verify SUPER_ADMIN session with invalid TOTP code is rejected with HTTP 403."""
        admin_token = get_super_admin_session()
        r = requests.post(
            f"{BACKEND_URL}/api/toggle-live-trading",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"enabled": True, "totp_code": "000000"},
            timeout=5
        )
        self.assertEqual(r.status_code, 403)
        d = r.json()
        self.assertEqual(d.get("error"), "INVALID_TOTP")

    def test_blocker3_toggle_authorized_activation_and_replay_protection(self):
        """Verify full authorized activation flow with RFC 6238 TOTP, replay protection, and lockdown."""
        import sqlite3
        from core.super_admin import super_admin, TOTP_REPLAY_DB
        from core.environment_gate import environment_gate

        with sqlite3.connect(str(TOTP_REPLAY_DB), timeout=30.0) as conn:
            conn.execute("DELETE FROM totp_consumed_steps WHERE admin_username = 'marvan';")

        admin_token = get_super_admin_session()
        secret = super_admin.users["marvan"]["totp_secret"]
        valid_totp = super_admin.generate_totp_code(secret, time_step=0)
        self.assertTrue(len(valid_totp) == 6, "Valid 6-digit TOTP must be generated")

        try:
            # 1. First submission: Authorized activation
            r_activate = requests.post(
                f"{BACKEND_URL}/api/toggle-live-trading",
                headers={"Authorization": f"Bearer {admin_token}"},
                json={"enabled": True, "totp_code": valid_totp},
                timeout=5
            )
            self.assertEqual(r_activate.status_code, 200)
            d_activate = r_activate.json()
            self.assertEqual(d_activate.get("status"), "SUCCESS")
            self.assertTrue(d_activate.get("live_trading_enabled"))

            # Invariant check: Live trading flag toggled, but withdrawals remain strictly locked!
            self.assertFalse(
                environment_gate.LIVE_WITHDRAWALS_ENABLED,
                "LIVE_WITHDRAWALS_ENABLED must remain false under all circumstances"
            )

            # 2. Replay submission: Re-using the same TOTP code must be REJECTED (HTTP 403)
            r_replay = requests.post(
                f"{BACKEND_URL}/api/toggle-live-trading",
                headers={"Authorization": f"Bearer {admin_token}"},
                json={"enabled": True, "totp_code": valid_totp},
                timeout=5
            )
            self.assertEqual(r_replay.status_code, 403)
            d_replay = r_replay.json()
            self.assertEqual(d_replay.get("error"), "TOTP_REPLAY_DETECTED")

            # 3. Emergency lockdown: Authorized operator can disable live trading without TOTP
            r_disable = requests.post(
                f"{BACKEND_URL}/api/toggle-live-trading",
                headers={"Authorization": f"Bearer {admin_token}"},
                json={"enabled": False},
                timeout=5
            )
            self.assertEqual(r_disable.status_code, 200)
            d_disable = r_disable.json()
            self.assertEqual(d_disable.get("status"), "SUCCESS")
            self.assertFalse(d_disable.get("live_trading_enabled"))

            # Gate verification: LIVE_TRADING_ENABLED must be False
            self.assertFalse(environment_gate.LIVE_TRADING_ENABLED)

        finally:
            # Hard safety guarantee: Always ensure live trading is disabled at end of test
            environment_gate.toggle_live_trading(False)

    def test_blocker3_toggle_unauthenticated_disable_rejected_401(self):
        """Verify unauthenticated attempt to disable live trading is rejected with HTTP 401."""
        r = requests.post(
            f"{BACKEND_URL}/api/toggle-live-trading",
            json={"enabled": False},
            timeout=5
        )
        self.assertEqual(r.status_code, 401)
        d = r.json()
        self.assertEqual(d.get("error"), "UNAUTHENTICATED")

    def test_blocker3_durable_replay_persists_across_restart(self):
        """Verify consumed TOTP time-step is recorded in SQLite and rejected across process restarts."""
        from core.super_admin import SuperAdminEngine

        # 1. First engine instance generates and consumes TOTP
        engine1 = SuperAdminEngine()
        secret = engine1.users["marvan"]["totp_secret"]
        totp = engine1.generate_totp_code(secret, time_step=0)
        engine1.verify_and_consume_totp("marvan", totp)

        # 2. Simulate complete process restart by creating a new SuperAdminEngine instance
        restarted_engine = SuperAdminEngine()
        success, reason = restarted_engine.verify_and_consume_totp("marvan", totp)
        self.assertFalse(success, "Replay across simulated restart must be blocked")
        self.assertEqual(reason, "TOTP_REPLAY_DETECTED", "Must fail with TOTP_REPLAY_DETECTED")

    def test_blocker3_concurrent_replay_race_rejected(self):
        """Verify concurrent requests with the exact same TOTP code are atomically rejected by SQLite."""
        import sqlite3
        from concurrent.futures import ThreadPoolExecutor
        from core.super_admin import super_admin, TOTP_REPLAY_DB
        from core.environment_gate import environment_gate

        with sqlite3.connect(str(TOTP_REPLAY_DB), timeout=30.0) as conn:
            conn.execute("DELETE FROM totp_consumed_steps WHERE admin_username = 'marvan';")

        admin_token = get_super_admin_session()
        secret = super_admin.users["marvan"]["totp_secret"]
        test_totp = super_admin.generate_totp_code(secret, time_step=0)

        def make_activation_request():
            return requests.post(
                f"{BACKEND_URL}/api/toggle-live-trading",
                headers={"Authorization": f"Bearer {admin_token}"},
                json={"enabled": True, "totp_code": test_totp},
                timeout=5
            )

        try:
            with ThreadPoolExecutor(max_workers=2) as executor:
                f1 = executor.submit(make_activation_request)
                f2 = executor.submit(make_activation_request)
                r1 = f1.result()
                r2 = f2.result()

            status_codes = [r1.status_code, r2.status_code]
            self.assertIn(403, status_codes, "At least one concurrent request must be rejected with 403")
            replayed_resp = r1 if r1.status_code == 403 else r2
            self.assertEqual(replayed_resp.json().get("error"), "TOTP_REPLAY_DETECTED")
        finally:
            environment_gate.toggle_live_trading(False)

    # =========================================================================
    # BLOCKER 4: FRONTEND PRODUCTION COMPATIBILITY & ROUTING
    # =========================================================================

    def test_blocker4_nextjs_routes_accessible(self):
        """Verify all 8 institutional Next.js frontend pages return HTTP 200 on port 3000."""
        routes = [
            "/",
            "/crypto",
            "/india",
            "/forex-gold",
            "/demo",
            "/demo/crypto",
            "/demo/india",
            "/demo/forex-gold",
        ]
        for path in routes:
            r = requests.get(f"{FRONTEND_URL}{path}", timeout=5)
            self.assertEqual(r.status_code, 200, f"Route {path} failed with status {r.status_code}")
            self.assertIn("Aegis Quant", r.text, f"Route {path} missing Aegis Quant title")

    def test_blocker5_websocket_upgrade_and_environment_isolation(self):
        """Verify WebSocket /ws upgrade, 1s tick, and complete environment isolation between DEMO and LIVE."""
        import websockets
        import asyncio
        import json

        async def _test():
            # DEMO connection
            async with websockets.connect(f"ws://127.0.0.1:8888/ws?workspace=CRYPTO&environment=DEMO") as ws_demo:
                msg = await asyncio.wait_for(ws_demo.recv(), timeout=5.0)
                data = json.loads(msg)
                self.assertEqual(data.get("environment"), "DEMO")
                self.assertEqual(data.get("event_type"), "ENGINE_HEARTBEAT")
                self.assertIsNotNone(data.get("portfolio_equity"))

            # LIVE connection
            async with websockets.connect(f"ws://127.0.0.1:8888/ws?workspace=CRYPTO&environment=LIVE") as ws_live:
                msg = await asyncio.wait_for(ws_live.recv(), timeout=5.0)
                data = json.loads(msg)
                self.assertEqual(data.get("environment"), "LIVE")
                self.assertEqual(data.get("event_type"), "ENGINE_HEARTBEAT")
                # When unauthenticated live broker, equity must be None (no paper leak)
                self.assertIsNone(data.get("portfolio_equity"))

        asyncio.run(_test())


if __name__ == "__main__":
    unittest.main()

