"""
Post-deployment verification script for commit 93253f9f on srv1799665.hstgr.cloud.
Checks:
  1. /api/status == HTTP 200
  2. git_commit starts with 93253f9f
  3. CRYPTO dashboard == HTTP 200 and renders full HTML
  4. INDIA dashboard == HTTP 200 and renders full HTML (no UnboundLocalError)
  5. FOREX_GOLD dashboard == HTTP 200 and renders full HTML
  6. zero occurrences of UnboundLocalError in response payloads
  7. LIVE_TRADING_ENABLED remains false
  8. LIVE_WITHDRAWALS_ENABLED remains false
"""

import sys
import json
import urllib.request
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

BASE_URL = "https://srv1799665.hstgr.cloud"

def check():
    results = {}

    # 1 & 2. /api/status
    try:
        req = urllib.request.Request(f"{BASE_URL}/api/status", headers={"User-Agent": "AegisDeployVerify/1.0"})
        with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
            code = resp.status
            body = json.loads(resp.read().decode())
            commit = body.get("git_commit", "")
            results["api_status_200"] = (code == 200)
            results["git_commit"] = commit
            results["git_commit_match"] = commit.startswith("93253f9")
    except Exception as e:
        results["api_status_200"] = False
        results["git_commit"] = str(e)
        results["git_commit_match"] = False

    # 3, 4, 5, 6. Workspaces
    for ws in ["CRYPTO", "INDIA", "FOREX_GOLD"]:
        try:
            req = urllib.request.Request(f"{BASE_URL}/?workspace={ws}", headers={"User-Agent": "AegisDeployVerify/1.0"})
            with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
                code = resp.status
                html = resp.read().decode("utf-8")
                has_error = "UnboundLocalError" in html or "cannot access local variable 'lite_broker_badge'" in html
                is_full_doc = "<!DOCTYPE html>" in html or "<html" in html
                results[f"{ws}_code_200"] = (code == 200)
                results[f"{ws}_no_unbound_error"] = not has_error
                results[f"{ws}_full_html"] = is_full_doc and not has_error
        except Exception as e:
            results[f"{ws}_code_200"] = False
            results[f"{ws}_no_unbound_error"] = False
            results[f"{ws}_full_html"] = False
            results[f"{ws}_error"] = str(e)

    # 7 & 8. Environment status gates
    try:
        req = urllib.request.Request(f"{BASE_URL}/api/environment/status", headers={"User-Agent": "AegisDeployVerify/1.0"})
        with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
            body = json.loads(resp.read().decode()).get("data", {})
            results["live_trading_enabled"] = body.get("live_trading_enabled_flag")
            results["live_withdrawals_enabled"] = body.get("live_withdrawals_enabled_flag")
            results["gates_locked"] = (body.get("live_trading_enabled_flag") is False and 
                                       body.get("live_withdrawals_enabled_flag") is False)
    except Exception as e:
        results["gates_locked"] = False
        results["gates_error"] = str(e)

    print(json.dumps(results, indent=2))
    return results

if __name__ == "__main__":
    check()
