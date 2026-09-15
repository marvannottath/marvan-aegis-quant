"""
Aegis-Quant Secure Credential & Provider State Manager.
First priority security architecture for Phase 4.
Enforces:
  1. Credentials stored ONLY server-side (env vars or local 0600 secure store).
  2. Forbidden from frontend, HTML, JS, git, logs, audit payloads, exceptions.
  3. Explicit provider configuration states:
       - NOT CONFIGURED
       - CONFIGURED
       - AUTHENTICATION FAILED
       - AUTHENTICATED
       - READ-ONLY VERIFIED
       - TESTNET VERIFIED
       - LIVE LOCKED
  4. Strict environment boundaries:
       - Testnet credentials cannot hit LIVE endpoints.
       - LIVE credentials cannot be used in Testnet.
       - Upstox Read-Only workflow cannot place orders.
"""

import os
import json
import time
import base64
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime, timezone, timedelta

IST_TZ = timezone(timedelta(hours=5, minutes=30))

# Explicit 7 Provider Configuration States
STATE_NOT_CONFIGURED        = "NOT CONFIGURED"
STATE_CONFIGURED            = "CONFIGURED"
STATE_AUTHENTICATION_FAILED = "AUTHENTICATION FAILED"
STATE_AUTHENTICATED         = "AUTHENTICATED"
STATE_READ_ONLY_VERIFIED    = "READ-ONLY VERIFIED"
STATE_TESTNET_VERIFIED      = "TESTNET VERIFIED"
STATE_LIVE_LOCKED           = "LIVE LOCKED"

VALID_PROVIDER_STATES = {
    STATE_NOT_CONFIGURED,
    STATE_CONFIGURED,
    STATE_AUTHENTICATION_FAILED,
    STATE_AUTHENTICATED,
    STATE_READ_ONLY_VERIFIED,
    STATE_TESTNET_VERIFIED,
    STATE_LIVE_LOCKED,
}

SECURE_STORE_PATH = Path(__file__).resolve().parent.parent / "data" / ".secure_credentials.json"


class SecureCredentialManager:
    """
    Authoritative server-side credential and provider state manager.
    Protects secrets from exposure in frontend, audit logs, and git.
    """

    def __init__(self):
        self._credentials: Dict[str, Dict[str, Any]] = {
            "UPSTOX": {
                "api_key": "",
                "api_secret": "",
                "access_token": "",
                "redirect_uri": "",
                "mode": "READ_ONLY",
                "state": STATE_NOT_CONFIGURED,
                "last_auth_attempt": None,
                "last_error": ""
            },
            "BINANCE_TESTNET": {
                "api_key": "",
                "secret_key": "",
                "mode": "TESTNET",
                "state": STATE_NOT_CONFIGURED,
                "last_auth_attempt": None,
                "last_error": ""
            },
            "FOREX": {
                "provider_name": "None",
                "state": STATE_NOT_CONFIGURED,
                "mode": "SIMULATED",
                "last_error": "No external provider configured"
            }
        }
        self._load_credentials()

    # ------------------------------------------------------------------ #
    # Secure Loading & Masking
    # ------------------------------------------------------------------ #

    def _load_credentials(self):
        """Load credentials from environment variables or secure file store."""
        # 1. Upstox from env
        u_key = os.getenv("UPSTOX_API_KEY", "").strip()
        u_sec = os.getenv("UPSTOX_API_SECRET", "").strip()
        u_tok = os.getenv("UPSTOX_ACCESS_TOKEN", "").strip()
        u_uri = os.getenv("UPSTOX_REDIRECT_URI", "http://localhost:8888/api/upstox/callback").strip()

        # 2. Binance Testnet from env
        b_key = os.getenv("BINANCE_TESTNET_API_KEY", os.getenv("BINANCE_TEST_API_KEY", "")).strip()
        b_sec = os.getenv("BINANCE_TESTNET_SECRET_KEY", os.getenv("BINANCE_TEST_SECRET_KEY", "")).strip()

        # 3. Check local secure store if env is empty
        if not (u_key and u_tok) or not (b_key and b_sec):
            if SECURE_STORE_PATH.exists():
                try:
                    with open(SECURE_STORE_PATH, "r") as f:
                        data = json.load(f)
                    u_store = data.get("UPSTOX", {})
                    b_store = data.get("BINANCE_TESTNET", {})
                    u_key = u_key or u_store.get("api_key", "")
                    u_sec = u_sec or u_store.get("api_secret", "")
                    u_tok = u_tok or u_store.get("access_token", "")
                    b_key = b_key or b_store.get("api_key", "")
                    b_sec = b_sec or b_store.get("secret_key", "")
                except Exception as e:
                    pass

        # Update Upstox state
        self._credentials["UPSTOX"]["api_key"] = u_key
        self._credentials["UPSTOX"]["api_secret"] = u_sec
        self._credentials["UPSTOX"]["access_token"] = u_tok
        self._credentials["UPSTOX"]["redirect_uri"] = u_uri

        if u_tok and u_key:
            self._credentials["UPSTOX"]["state"] = STATE_CONFIGURED
        else:
            self._credentials["UPSTOX"]["state"] = STATE_NOT_CONFIGURED

        # Update Binance Testnet state
        self._credentials["BINANCE_TESTNET"]["api_key"] = b_key
        self._credentials["BINANCE_TESTNET"]["secret_key"] = b_sec
        if b_key and b_sec:
            self._credentials["BINANCE_TESTNET"]["state"] = STATE_CONFIGURED
        else:
            self._credentials["BINANCE_TESTNET"]["state"] = STATE_NOT_CONFIGURED

    def mask_secret(self, secret: Optional[str]) -> str:
        """Mask a secret value safely for UI display. Never expose plaintext."""
        if not secret:
            return ""
        s = str(secret).strip()
        if len(s) <= 8:
            return "••••••••"
        return f"{s[:4]}••••••••{s[-4:]}"

    def get_masked_status(self) -> Dict[str, Any]:
        """Return provider statuses with zero raw secrets."""
        return {
            "UPSTOX": {
                "state": self._credentials["UPSTOX"]["state"],
                "mode": self._credentials["UPSTOX"]["mode"],
                "masked_api_key": self.mask_secret(self._credentials["UPSTOX"]["api_key"]),
                "has_token": bool(self._credentials["UPSTOX"]["access_token"]),
                "last_auth_attempt": self._credentials["UPSTOX"]["last_auth_attempt"],
                "last_error": self._credentials["UPSTOX"]["last_error"]
            },
            "BINANCE_TESTNET": {
                "state": self._credentials["BINANCE_TESTNET"]["state"],
                "mode": self._credentials["BINANCE_TESTNET"]["mode"],
                "masked_api_key": self.mask_secret(self._credentials["BINANCE_TESTNET"]["api_key"]),
                "last_auth_attempt": self._credentials["BINANCE_TESTNET"]["last_auth_attempt"],
                "last_error": self._credentials["BINANCE_TESTNET"]["last_error"]
            },
            "FOREX": {
                "state": STATE_NOT_CONFIGURED,
                "mode": "SIMULATED",
                "provider": "None (Interbank Simulation Engine)",
                "note": "FOREX LIVE BROKER = NOT CONFIGURED"
            }
        }

    # ------------------------------------------------------------------ #
    # State Management & Verification
    # ------------------------------------------------------------------ #

    def set_provider_state(self, provider: str, state: str, error_msg: str = ""):
        """Set explicit provider state with validation."""
        p = provider.upper()
        if p in self._credentials:
            if state in VALID_PROVIDER_STATES:
                self._credentials[p]["state"] = state
                self._credentials[p]["last_error"] = error_msg
                self._credentials[p]["last_auth_attempt"] = datetime.now(timezone.utc).astimezone(IST_TZ).strftime("%Y-%m-%d %H:%M:%S IST")

    def get_provider_state(self, provider: str) -> str:
        """Return the authoritative explicit state for provider."""
        p = provider.upper()
        if p in self._credentials:
            return self._credentials[p]["state"]
        return STATE_NOT_CONFIGURED

    # ------------------------------------------------------------------ #
    # Token Expiry Checking (Safe JWT inspection without exposing secret)
    # ------------------------------------------------------------------ #

    def is_upstox_token_expired(self) -> Tuple[bool, Optional[str]]:
        """
        Check if Upstox JWT token is expired without logging or exposing token.
        Returns (is_expired: bool, expiry_iso_or_reason: str).
        """
        token = self._credentials["UPSTOX"]["access_token"]
        if not token:
            return True, "NO_TOKEN_CONFIGURED"

        try:
            parts = token.split(".")
            if len(parts) != 3:
                return False, "OPAQUE_TOKEN_FORMAT"

            # Decode payload
            payload_b64 = parts[1]
            rem = len(payload_b64) % 4
            if rem > 0:
                payload_b64 += "=" * (4 - rem)
            payload_json = base64.urlsafe_b64decode(payload_b64).decode("utf-8")
            data = json.loads(payload_json)

            exp = data.get("exp")
            if not exp:
                return False, "NO_EXP_CLAIM"

            now_epoch = time.time()
            if now_epoch >= exp:
                exp_dt = datetime.fromtimestamp(exp, tz=timezone.utc).astimezone(IST_TZ).strftime("%Y-%m-%d %H:%M:%S IST")
                return True, f"EXPIRED_AT_{exp_dt}"

            rem_hours = round((exp - now_epoch) / 3600.0, 1)
            return False, f"VALID_{rem_hours}_HOURS_REMAINING"
        except Exception as e:
            return False, f"EXPIRY_PARSE_ERROR_{type(e).__name__}"

    # ------------------------------------------------------------------ #
    # Environment Hard Boundary
    # ------------------------------------------------------------------ #

    def validate_environment_boundary(
        self,
        provider: str,
        target_environment: str,
        action: str = "READ_ONLY"
    ) -> Tuple[bool, str]:
        """
        Hard Environment Boundary Invariants:
          1. BINANCE TESTNET credentials cannot be used against LIVE endpoints.
          2. LIVE Binance credentials cannot be silently used by TESTNET workflows.
          3. UPSTOX READ-ONLY workflow cannot submit orders.
          4. LIVE trading cannot be triggered without explicit LIVE_TRADING_ENABLED=true.
        """
        prov = provider.upper()
        env = target_environment.upper()
        act = action.upper()

        # Rule 1 & 2: Binance Environment Isolation
        if "BINANCE" in prov:
            if "LIVE" in env:
                from core.environment_gate import environment_gate
                if not environment_gate.LIVE_TRADING_ENABLED:
                    return False, "LIVE_LOCKED: Binance LIVE execution strictly locked by server safety gate"
                if "TESTNET" in prov:
                    return False, "ENVIRONMENT_MISMATCH: Binance TESTNET credentials forbidden on LIVE endpoint"

            if "TESTNET" in env and "LIVE" in prov:
                return False, "ENVIRONMENT_MISMATCH: Binance LIVE credentials forbidden on TESTNET endpoint"

        # Rule 3: Upstox Read-Only Safety
        if "UPSTOX" in prov:
            if act in ("ORDER", "TRADE", "SUBMIT_ORDER", "EXECUTE"):
                if self._credentials["UPSTOX"].get("mode") == "READ_ONLY":
                    return False, "READ_ONLY_VIOLATION: Upstox is in READ-ONLY mode. Order placement is strictly forbidden."

        # Rule 4: Live order check
        if "LIVE" in env and act in ("ORDER", "EXECUTE", "WITHDRAWAL"):
            from core.environment_gate import environment_gate
            if act == "WITHDRAWAL" and not environment_gate.LIVE_WITHDRAWALS_ENABLED:
                return False, "WITHDRAWAL_LOCKED: Live withdrawals are strictly disabled"
            if act in ("ORDER", "EXECUTE") and not environment_gate.LIVE_TRADING_ENABLED:
                return False, "LIVE_TRADING_LOCKED: Live order execution is strictly locked"

        return True, "ENVIRONMENT_BOUNDARY_VERIFIED"


# Global singleton
secure_credential_manager = SecureCredentialManager()
