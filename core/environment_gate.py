"""
Aegis-Quant Environment Gate.
Single authoritative safety gate that must be passed before any order submission.
Enforces strict isolation between PAPER / TESTNET / LIVE environments.
Default: LIVE_TRADING_ENABLED=false, LIVE_WITHDRAWALS_ENABLED=false.
"""

import os
import time
import json
from pathlib import Path
from typing import Tuple, Dict, Any
from datetime import datetime, timezone, timedelta

IST_TZ = timezone(timedelta(hours=5, minutes=30))

class EnvironmentGateError(Exception):
    pass

class EnvironmentGate:
    """
    Hard safety gate for all order submissions.
    Checks (in order):
      1. Environment validity
      2. LIVE_TRADING_ENABLED flag (must be explicitly true for LIVE)
      3. Market data freshness
      4. Emergency kill switch
      5. Reconciliation health
    """
    PAPER   = "PAPER"
    DEMO    = "DEMO"
    TESTNET = "TESTNET"
    LIVE    = "LIVE"

    VALID_ENVIRONMENTS = {PAPER, DEMO, TESTNET, LIVE}

    # Dynamic Live Trading ON/OFF toggle state
    LIVE_TRADING_ENABLED     = os.getenv("LIVE_TRADING_ENABLED",    "false").lower() == "true"
    LIVE_WITHDRAWALS_ENABLED = os.getenv("LIVE_WITHDRAWALS_ENABLED","false").lower() == "true"

    STALE_THRESHOLD_SECONDS = float(os.getenv("MARKET_DATA_STALE_THRESHOLD_SECONDS", "5.0"))

    KILL_SWITCH_FILE = Path(__file__).resolve().parent.parent / "data" / "emergency_kill_switch_state.json"

    def __init__(self):
        self._decision_log: list = []

    def toggle_live_trading(self, enabled: bool) -> bool:
        """Toggle Live Trading ON or OFF dynamically."""
        self.LIVE_TRADING_ENABLED = bool(enabled)
        return self.LIVE_TRADING_ENABLED

    def _is_kill_switch_active(self) -> bool:
        try:
            if self.KILL_SWITCH_FILE.exists():
                with open(self.KILL_SWITCH_FILE, "r") as f:
                    return json.load(f).get("is_activated", False)
        except Exception:
            return True  # fail closed on read error
        return False


    def _get_reconciliation_status(self) -> str:
        """Import lazily to avoid circular deps."""
        try:
            from core.reconciliation_sentinel import reconciliation_sentinel
            return reconciliation_sentinel.last_report.get("status", "UNKNOWN")
        except Exception:
            return "UNKNOWN"

    def check_order_allowed(
        self,
        environment: str,
        market_data_age_seconds: float = 0.0,
        skip_reconciliation_check: bool = False
    ) -> Tuple[bool, str]:
        """
        Returns (allowed: bool, reason: str).
        ALL gates must pass for an order to be allowed.
        """
        now = datetime.now(timezone.utc).astimezone(IST_TZ).strftime("%Y-%m-%d %H:%M:%S IST")

        # Gate 1: Valid environment
        if environment not in self.VALID_ENVIRONMENTS:
            return False, f"GATE_FAIL: Unknown environment '{environment}'"

        # Gate 2: LIVE requires explicit flag
        if environment == self.LIVE and not self.LIVE_TRADING_ENABLED:
            return False, "GATE_FAIL: LIVE_TRADING_ENABLED=false — live trading is locked"

        # Gate 3: Market data freshness
        if market_data_age_seconds > self.STALE_THRESHOLD_SECONDS:
            return False, f"GATE_FAIL: Market data stale ({market_data_age_seconds:.1f}s > {self.STALE_THRESHOLD_SECONDS}s threshold)"

        # Gate 4: Emergency kill switch
        if self._is_kill_switch_active():
            return False, "GATE_FAIL: Emergency kill switch is ACTIVE — all orders blocked"

        # Gate 5: Reconciliation health
        if not skip_reconciliation_check:
            recon_status = self._get_reconciliation_status()
            if recon_status == "CRITICAL":
                return False, "GATE_FAIL: Reconciliation status is CRITICAL — trading frozen"

        return True, f"GATE_PASS: {environment} order allowed at {now}"

    def check_withdrawal_allowed(self, environment: str) -> Tuple[bool, str]:
        """Withdrawal gate — always locked unless LIVE_WITHDRAWALS_ENABLED=true."""
        if not self.LIVE_WITHDRAWALS_ENABLED:
            return False, "WITHDRAWAL_LOCKED: LIVE_WITHDRAWALS_ENABLED=false — withdrawals are locked"
        if self._is_kill_switch_active():
            return False, "WITHDRAWAL_LOCKED: Emergency kill switch is ACTIVE"
        return True, "WITHDRAWAL_GATE_PASS"

    def get_environment_status(self) -> Dict[str, Any]:
        """Full status snapshot for the /api/environment/status endpoint."""
        recon_status = self._get_reconciliation_status()
        kill_active  = self._is_kill_switch_active()
        return {
            "paper_trading":             "ACTIVE",
            "binance_testnet":           "AVAILABLE_FOR_VALIDATION",
            "live_trading":              "ACTIVE" if self.LIVE_TRADING_ENABLED else "LOCKED",
            "live_withdrawals":          "ACTIVE" if self.LIVE_WITHDRAWALS_ENABLED else "LOCKED",
            "stripe_live":               "LOCKED_UNTIL_ACCOUNT_APPROVAL",
            "live_trading_enabled_flag": self.LIVE_TRADING_ENABLED,
            "live_withdrawals_enabled_flag": self.LIVE_WITHDRAWALS_ENABLED,
            "kill_switch_active":         kill_active,
            "reconciliation_status":      recon_status,
            "stale_threshold_seconds":    self.STALE_THRESHOLD_SECONDS,
        }


# Global singleton
environment_gate = EnvironmentGate()
