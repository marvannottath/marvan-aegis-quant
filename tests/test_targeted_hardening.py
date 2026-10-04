"""
Targeted tests for Aegis-Quant Hardening Pass:
1. TOTP Deactivation security (/api/auth/totp-deactivate)
   - unauthenticated rejected (401)
   - non-admin trader rejected (403)
   - username-only rejected (400)
   - wrong password / wrong OTP rejected (400)
   - valid authorized request succeeds (200)
   - audit trail logged
2. Local SVG QR generation without external network call
3. Kotak Neo Broker Adapter paper/mock safety gate
"""

import os
import sys
import json
import base64
import asyncio
from pathlib import Path

# Setup paths
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.super_admin import super_admin
from execution.kotak_neo_broker import kotak_neo_broker
from dashboard.app import universal_totp_deactivate

PASSED_COUNT = 0
FAILED_COUNT = 0


def test(name: str, condition: bool, msg: str = ""):
    global PASSED_COUNT, FAILED_COUNT
    if condition:
        PASSED_COUNT += 1
        print(f"  [PASS] {name} - {msg}")
    else:
        FAILED_COUNT += 1
        print(f"  [FAIL] {name} - {msg}")


class MockClient:
    def __init__(self, host: str = "127.0.0.1"):
        self.host = host

    async def invoke_deactivate(self, headers: dict, data: dict):
        class MockRequest:
            def __init__(self, hdrs, client_ip):
                self.headers = hdrs
                self.client = type("Client", (), {"host": client_ip})()

        req = MockRequest(headers, self.host)
        resp = await universal_totp_deactivate(req, data)
        return resp.status_code, json.loads(resp.body.decode("utf-8"))


def run_tests():
    global PASSED_COUNT, FAILED_COUNT
    client = MockClient()

    print("=" * 80)
    print("AEGIS-QUANT TARGETED HARDENING VERIFICATION")
    print("=" * 80)

    # ---------------------------------------------------------
    # ITEM 1: CRITICAL SECURITY - TOTP DEACTIVATION
    # ---------------------------------------------------------
    print("\n--- 1. TOTP DEACTIVATION SECURITY ---")

    # 1.1 Unauthenticated request must be rejected with 401
    status_code, res = asyncio.run(client.invoke_deactivate(
        headers={},
        data={"username": "marvan", "password": "WrongPassword"}
    ))
    test(
        "totp_deactivate_unauthenticated_rejected",
        status_code == 401 and res.get("status") == "FAILED",
        f"Status: {status_code}, Resp: {res}"
    )

    # 1.2 Non-admin trader session must be rejected with 403
    trader_token = super_admin.create_session("quant_trader")
    status_code, res = asyncio.run(client.invoke_deactivate(
        headers={"Authorization": f"Bearer {trader_token}"},
        data={"username": "quant_trader", "password": "Trader@2026!"}
    ))
    test(
        "totp_deactivate_non_admin_rejected",
        status_code == 403 and res.get("status") == "FAILED",
        f"Status: {status_code}, Resp: {res}"
    )

    # 1.3 Request with valid admin token but only username (missing password & otp) must fail with 400
    admin_token = super_admin.create_session("marvan")
    status_code, res = asyncio.run(client.invoke_deactivate(
        headers={"Authorization": f"Bearer {admin_token}"},
        data={"username": "marvan"}
    ))
    test(
        "totp_deactivate_username_only_rejected",
        status_code == 400 and res.get("status") == "FAILED",
        f"Status: {status_code}, Resp: {res}"
    )

    # 1.4 Admin token with wrong password and wrong OTP must fail with 400
    status_code, res = asyncio.run(client.invoke_deactivate(
        headers={"Authorization": f"Bearer {admin_token}"},
        data={
            "username": "marvan",
            "password": "incorrect_password_12345",
            "totp_code": "000000"
        }
    ))
    test(
        "totp_deactivate_wrong_credentials_rejected",
        status_code == 400 and res.get("status") == "FAILED",
        f"Status: {status_code}, Resp: {res}"
    )

    # 1.5 Valid authorized request succeeds and logs to audit trail
    super_admin.users["marvan"]["totp_enabled"] = True
    super_admin._save_users()
    test("super_admin_totp_precondition_enabled", super_admin.users["marvan"]["totp_enabled"] is True, "TOTP is enabled")

    status_code, res = asyncio.run(client.invoke_deactivate(
        headers={"Authorization": f"Bearer {admin_token}"},
        data={
            "username": "marvan",
            "password": "Marvan@2026!"
        }
    ))
    test(
        "totp_deactivate_valid_admin_password_succeeds",
        status_code == 200 and res.get("status") == "SUCCESS" and super_admin.users["marvan"]["totp_enabled"] is False,
        f"Status: {status_code}, TOTP enabled now: {super_admin.users['marvan']['totp_enabled']}"
    )

    # 1.6 Verify audit log entry
    audit_file = ROOT / "data" / "user_audit_trail.json"
    audit_logged = False
    if audit_file.exists():
        with open(audit_file, "r") as f:
            trail = json.load(f)
        actions = [e.get("action") for e in trail]
        audit_logged = "TOTP_DEACTIVATED" in actions
    test("totp_deactivate_audit_trail_recorded", audit_logged, f"Found TOTP_DEACTIVATED in audit trail")

    # ---------------------------------------------------------
    # ITEM 2: REMOVE EXTERNAL QR DEPENDENCY
    # ---------------------------------------------------------
    print("\n--- 2. LOCAL OFFLINE SVG QR GENERATION ---")
    qr_res = super_admin.get_totp_provisioning_uri("marvan")
    qr_uri = qr_res.get("qr_image_url", "")
    
    is_svg_data_uri = qr_uri.startswith("data:image/svg+xml;base64,")
    b64_part = qr_uri.split(",", 1)[1] if is_svg_data_uri else ""
    try:
        svg_xml = base64.b64decode(b64_part).decode("utf-8")
        valid_svg = "<svg" in svg_xml and "</svg>" in svg_xml and "quickchart.io" not in svg_xml
    except Exception:
        valid_svg = False

    test(
        "local_svg_qr_offline_generation",
        is_svg_data_uri and valid_svg,
        f"SVG length: {len(svg_xml)} bytes, zero external HTTP dependencies"
    )

    # ---------------------------------------------------------
    # ITEM 10: KOTAK NEO BROKER ADAPTER PAPER/MOCK SCAFFOLDING
    # ---------------------------------------------------------
    print("\n--- 3. KOTAK NEO BROKER ADAPTER SCAFFOLDING & ISOLATION ---")
    test("kotak_neo_broker_name", kotak_neo_broker.broker_name == "KOTAK_NEO", "Broker name is KOTAK_NEO")

    auth_res = kotak_neo_broker.authenticate({"consumer_key": "MOCK_KEY", "consumer_secret": "MOCK_SECRET"})
    test("kotak_neo_paper_authenticate", auth_res.get("authenticated") is True and auth_res.get("paper_mode") is True, "Authenticated in paper mode")

    funds = kotak_neo_broker.get_funds()
    test("kotak_neo_funds_inr", funds.get("currency") == "INR" and funds.get("cash") == 50000.0, f"Cash: {funds.get('cash')} INR")

    # Paper order with NSE tick 0.05
    acc_order = kotak_neo_broker.place_order({
        "symbol": "RELIANCE",
        "side": "BUY",
        "quantity": 10,
        "price": 2500.05,
        "product": "MIS"
    })
    test("kotak_neo_nse_tick_accepted", acc_order.get("status") == "ACCEPTED", f"Accepted NSE valid tick order: {acc_order.get('order_id')}")

    # Rejection on invalid tick
    rej_order = kotak_neo_broker.place_order({
        "symbol": "TCS",
        "side": "BUY",
        "quantity": 5,
        "price": 3450.03,  # Invalid tick
        "product": "MIS"
    })
    test("kotak_neo_invalid_tick_rejected", rej_order.get("status") == "REJECTED", f"Rejected non-0.05 tick: {rej_order.get('message')}")

    # Rejection of LIVE orders when LIVE_TRADING_ENABLED=false
    live_rej = kotak_neo_broker.place_order({
        "symbol": "INFY",
        "side": "BUY",
        "quantity": 5,
        "price": 1800.00,
        "environment": "LIVE"
    })
    test("kotak_neo_fail_closed_live_locked", live_rej.get("status") == "REJECTED" and "LIVE_TRADING_ENABLED is false" in live_rej.get("message", ""), "Blocked live execution via fail-closed policy")

    print("\n" + "=" * 80)
    print(f"RESULTS: {PASSED_COUNT} PASSED, {FAILED_COUNT} FAILED")
    print("=" * 80)
    if FAILED_COUNT > 0:
        sys.exit(1)


if __name__ == "__main__":
    run_tests()
