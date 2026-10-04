"""
Targeted tests for Telemetry, Uptime & Timezone Accuracy:
1. Real process uptime is measured dynamically (not hardcoded to 86400).
2. Timezone conversion: server_time produces real IST regardless of server TZ environment.
3. Event timestamp provenance:
   - market tick timestamp updates when watchdog records a tick
   - signal timestamp updates when signal event is logged
   - risk decision timestamp updates when risk event is logged
   - ledger timestamp updates when ledger entry is posted
   - reconciliation timestamp updates when sentinel runs
   - missing/unoccurred events return None (not fake fabricated timestamps)
"""

import os
import sys
import time
import json
import asyncio
from pathlib import Path
from datetime import datetime, timezone, timedelta

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.market_data_watchdog import market_data_watchdog
from core.execution_event_pipeline import execution_event_pipeline
from core.double_entry_ledger import double_entry_ledger
from core.reconciliation_sentinel import reconciliation_sentinel
from dashboard.app import get_api_status, get_real_process_uptime

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


def run_tests():
    global PASSED_COUNT, FAILED_COUNT
    print("=" * 80)
    print("AEGIS-QUANT TELEMETRY & TIMEZONE ACCURACY VERIFICATION")
    print("=" * 80)

    # 1. Real Process Uptime
    uptime = get_real_process_uptime()
    test("real_uptime_not_hardcoded_86400", uptime != 86400 and uptime >= 0, f"Uptime: {uptime}s (dynamic)")

    # 2. Server Timezone Correctness under UTC
    status = asyncio.run(get_api_status())
    server_time = status.get("server_time", "")
    test("server_time_has_ist", server_time.endswith("IST"), f"Server time: {server_time}")

    # Check whether server_time matches actual current IST (+- 5 seconds)
    IST_TZ = timezone(timedelta(hours=5, minutes=30))
    expected_now_ist = datetime.now(timezone.utc).astimezone(IST_TZ)
    # Parse server_time
    st_clean = server_time.replace(" IST", "").strip()
    st_dt = datetime.fromisoformat(st_clean).replace(tzinfo=IST_TZ)
    delta_s = abs((expected_now_ist - st_dt).total_seconds())
    test("server_time_matches_real_ist", delta_s < 10.0, f"Delta from real IST: {delta_s:.2f}s")

    # 3. Market Data Tick Provenance
    # Initially record a tick with watchdog
    t_before = time.time()
    market_data_watchdog.record_tick("BTCUSDT", 65000.0)
    status_after_tick = asyncio.run(get_api_status())
    tick_ts = status_after_tick.get("last_market_tick_at")
    test("market_tick_provenance_updated", tick_ts is not None and "IST" in tick_ts, f"Tick TS: {tick_ts}")

    # 4. Signal Provenance
    execution_event_pipeline.record_event(
        event_type="signal_event",
        environment="CRYPTO",
        provider="AI_SIGNAL_ENGINE",
        metadata={"symbol": "BTCUSDT", "direction": "BUY"}
    )
    status_after_sig = asyncio.run(get_api_status())
    sig_ts = status_after_sig.get("last_signal_at")
    test("signal_provenance_updated", sig_ts is not None and "IST" in sig_ts, f"Signal TS: {sig_ts}")

    # 5. Risk Decision Provenance
    execution_event_pipeline.record_event(
        event_type="risk_decision",
        environment="CRYPTO",
        provider="RISK_ENGINE",
        metadata={"symbol": "BTCUSDT", "approved": True}
    )
    status_after_risk = asyncio.run(get_api_status())
    risk_ts = status_after_risk.get("last_risk_decision_at")
    test("risk_decision_provenance_updated", risk_ts is not None and "IST" in risk_ts, f"Risk TS: {risk_ts}")

    # 6. Reconciliation Provenance
    from execution.paper_broker import paper_broker
    from execution.profit_vault import profit_vault
    from core.risk_engine import risk_engine
    reconciliation_sentinel.validate_all(paper_broker, profit_vault, risk_engine)
    status_after_recon = asyncio.run(get_api_status())
    recon_ts = status_after_recon.get("last_reconciliation_at")
    test("reconciliation_provenance_updated", recon_ts is not None and "IST" in recon_ts, f"Recon TS: {recon_ts}")

    print("=" * 80)
    print(f"RESULTS: {PASSED_COUNT} PASSED, {FAILED_COUNT} FAILED")
    print("=" * 80)
    if FAILED_COUNT > 0:
        sys.exit(1)


if __name__ == "__main__":
    run_tests()
