"""
REST API Endpoint Diagnostic Audit Script for Marvan's Aegis-Quant Trading System.
Tests all FastAPI REST endpoints over HTTP to verify 200 OK responses.
"""

import urllib.request
import json

BASE_URL = "http://localhost:8005"

endpoints = [
    ("/", "GET", None),
    ("/api/state", "GET", None),
    ("/api/binance-status", "GET", None),
    ("/api/run-sync", "GET", None),
    ("/api/set-risk-profile", "POST", {"profile": "MODERATE"}),
    ("/api/set-max-trade-cap", "POST", {"cap_usd": 5000.0}),
    ("/api/deposit-cash", "POST", {"amount": 100.0}),
]

print("=== STARTING REST API ENDPOINT AUDIT ===")

all_passed = True
for path, method, data in endpoints:
    url = f"{BASE_URL}{path}"
    try:
        if method == "GET":
            req = urllib.request.Request(url, headers={"User-Agent": "AuditScript/1.0"})
        else:
            json_data = json.dumps(data).encode("utf-8")
            req = urllib.request.Request(url, data=json_data, headers={"Content-Type": "application/json", "User-Agent": "AuditScript/1.0"}, method="POST")

        with urllib.request.urlopen(req, timeout=5) as response:
            status = response.status
            if status == 200:
                print(f"[PASS] {method} {path} -> HTTP {status} OK")
            else:
                print(f"[FAIL] {method} {path} -> HTTP {status}")
                all_passed = False
    except Exception as e:
        print(f"[FAIL] {method} {path} -> Error: {e}")
        all_passed = False

print("=== API AUDIT RESULT ===")
if all_passed:
    print("ALL REST API ENDPOINTS RETURNED HTTP 200 OK (0 FAILS)!")
else:
    print("SOME API ENDPOINTS FAILED.")
