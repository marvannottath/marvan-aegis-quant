#!/usr/bin/env python3
"""
Test Suite: Market Session API Endpoint Verification.
Verifies:
  1. Route registration on FastAPI app: /api/market-session, /api/market/session
  2. Workspace routes: /api/market-session/{workspace}, /api/market/session/{workspace}
  3. Response status_code == 200
  4. Response contains top-level keys: INDIA, FOREX_GOLD, CRYPTO, sessions, status
  5. Each workspace contains: state, is_trading_allowed, is_new_entry_allowed, evaluated_timestamp, manual_override_status
  6. Workspace-specific handlers return detail with HTTP 200
  7. /api/operational-status and /api/ai/status handlers
"""

import sys
import json
import asyncio
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from dashboard.app import (
    app,
    get_all_market_sessions,
    get_workspace_market_session,
    get_operational_status,
    get_ai_status,
)


class TestMarketSessionAPI(unittest.TestCase):
    def test_01_routes_registered_on_app(self):
        """Verify both /api/market-session and /api/market/session are registered on FastAPI app."""
        route_paths = [getattr(r, "path", None) for r in app.routes]
        self.assertIn("/api/market-session", route_paths, "Route /api/market-session missing from app")
        self.assertIn("/api/market/session", route_paths, "Route /api/market/session missing from app")
        self.assertIn("/api/market-session/{workspace}", route_paths, "Route /api/market-session/{workspace} missing")
        self.assertIn("/api/market/session/{workspace}", route_paths, "Route /api/market/session/{workspace} missing")
        self.assertIn("/api/operational-status", route_paths, "Route /api/operational-status missing")
        self.assertIn("/api/ai/status", route_paths, "Route /api/ai/status missing")

    def test_02_get_all_market_sessions_handler(self):
        """Verify get_all_market_sessions() returns 200 and required fields."""
        resp = asyncio.run(get_all_market_sessions())
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.body.decode("utf-8"))
        self.assertEqual(data.get("status"), "SUCCESS")
        self.assertIn("sessions", data)

        # Must contain all three workspaces at top level and within sessions
        for ws in ["INDIA", "FOREX_GOLD", "CRYPTO"]:
            self.assertIn(ws, data, f"Missing top-level workspace '{ws}'")
            self.assertIn(ws, data["sessions"], f"Missing workspace '{ws}' in sessions")
            ws_data = data[ws]
            self.assertIn("state", ws_data)
            self.assertIn("is_trading_allowed", ws_data)
            self.assertIn("is_new_entry_allowed", ws_data)
            self.assertIn("evaluated_timestamp", ws_data)
            self.assertIn("manual_override_status", ws_data)
            self.assertIn("evaluated_at_ist", ws_data)
            self.assertIn("manual_override_active", ws_data)

    def test_03_get_workspace_market_session_handler(self):
        """Verify get_workspace_market_session(ws) returns 200 with workspace detail."""
        for ws in ["INDIA", "FOREX_GOLD", "CRYPTO"]:
            resp = asyncio.run(get_workspace_market_session(ws))
            self.assertEqual(resp.status_code, 200)
            data = json.loads(resp.body.decode("utf-8"))
            self.assertEqual(data.get("status"), "SUCCESS")
            self.assertEqual(data.get("workspace"), ws)
            self.assertIn("state", data)
            self.assertIn("is_trading_allowed", data)
            self.assertIn("is_new_entry_allowed", data)
            self.assertIn("manual_override_status", data)
            self.assertIn("evaluated_timestamp", data)
            self.assertIn("evaluated_at_ist", data)

    def test_04_operational_status_handler(self):
        """Verify get_operational_status() returns 200 with unified snapshot."""
        resp = asyncio.run(get_operational_status())
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.body.decode("utf-8"))
        self.assertEqual(data.get("status"), "SUCCESS")
        self.assertIn("market", data)
        self.assertIn("ai", data)
        self.assertIn("execution", data)
        self.assertIn("session_detail", data)

    def test_05_ai_status_handler(self):
        """Verify get_ai_status() returns 200."""
        resp = asyncio.run(get_ai_status())
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.body.decode("utf-8"))
        self.assertEqual(data.get("status"), "SUCCESS")
        self.assertIn("ai_states", data)


if __name__ == "__main__":
    unittest.main(verbosity=2)
