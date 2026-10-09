"""
Aegis-Quant Google Authenticator (RFC 6238 TOTP 2FA) Engine.
Pure Python standard library implementation — zero external dependencies.
Protects critical operations:
  - Switching to LIVE trading
  - Disarming or clearing Emergency Lockdown
  - Modifying live API keys
  - Requesting fund withdrawals
"""

import hmac
import hashlib
import struct
import time
import base64
import secrets
import json
from pathlib import Path
from typing import Dict, Any, Tuple
from urllib.parse import quote

STATE_FILE = Path(__file__).resolve().parent.parent / "data" / "totp_2fa_state.json"

class TOTPAuthenticator:
    def __init__(self, issuer: str = "AegisQuant", account_name: str = "admin"):
        self.issuer = issuer
        self.account_name = account_name
        self.time_step = 30
        self._load_state()

    def _load_state(self):
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        if STATE_FILE.exists():
            try:
                with open(STATE_FILE, "r") as f:
                    data = json.load(f)
                    self.secret = data.get("secret", "")
                    self.is_enabled = data.get("is_enabled", False)
                    self.backup_codes = data.get("backup_codes", [])
                    return
            except Exception:
                pass
        
        # Provision a default 160-bit (20-byte base32) secret if none exists
        raw_bytes = secrets.token_bytes(20)
        self.secret = base64.b32encode(raw_bytes).decode("ascii").strip("=")
        # Default enabled for security demo, but ready to verify
        self.is_enabled = True
        self.backup_codes = [secrets.token_hex(4).upper() for _ in range(5)]
        self._save_state()

    def _save_state(self):
        try:
            with open(STATE_FILE, "w") as f:
                json.dump({
                    "secret": self.secret,
                    "is_enabled": self.is_enabled,
                    "backup_codes": self.backup_codes
                }, f, indent=2)
        except Exception:
            pass

    def get_provisioning_uri(self) -> str:
        """Returns standard otpauth:// URI for scanning into Google Authenticator / 1Password."""
        label = quote(f"{self.issuer}:{self.account_name}")
        issuer_q = quote(self.issuer)
        return f"otpauth://totp/{label}?secret={self.secret}&issuer={issuer_q}&algorithm=SHA1&digits=6&period=30"

    def generate_current_code(self, offset_steps: int = 0) -> str:
        """Computes current 6-digit TOTP code (RFC 6238 HMAC-SHA1)."""
        counter = int(time.time() // self.time_step) + offset_steps
        # Pad base32 string if needed
        padding = (8 - len(self.secret) % 8) % 8
        padded_secret = self.secret + ("=" * padding)
        key = base64.b32decode(padded_secret, casefold=True)
        
        msg = struct.pack(">Q", counter)
        h = hmac.new(key, msg, hashlib.sha1).digest()
        offset = h[19] & 0x0F
        code_int = (struct.unpack(">I", h[offset:offset+4])[0] & 0x7FFFFFFF) % 1000000
        return f"{code_int:06d}"

    def verify_code(self, candidate_code: str) -> Tuple[bool, str]:
        """
        Verifies a 6-digit code or 8-char backup code.
        Supports ±1 time step (±30s) window for clock skew tolerance.
        """
        cleaned = candidate_code.strip().replace(" ", "").replace("-", "")
        if not cleaned:
            return False, "EMPTY_CODE"

        # Check backup codes first
        if cleaned.upper() in self.backup_codes:
            self.backup_codes.remove(cleaned.upper())
            self._save_state()
            return True, "BACKUP_CODE_ACCEPTED"

        # Verify TOTP code for t-1, t, t+1
        for step in [0, -1, 1]:
            expected = self.generate_current_code(offset_steps=step)
            if hmac.compare_digest(cleaned, expected):
                return True, "TOTP_ACCEPTED"

        return False, "INVALID_CODE"

    def verify_and_consume_code(self, candidate_code: str, identifier: str = "system_admin") -> Tuple[bool, str]:
        """
        Verifies code and atomically records time_counter into SQLite DB with PRIMARY KEY constraint.
        Survives process restarts and concurrent multi-worker requests.
        """
        cleaned = candidate_code.strip().replace(" ", "").replace("-", "")
        if not cleaned:
            return False, "EMPTY_CODE"

        # Check backup codes first
        if cleaned.upper() in self.backup_codes:
            self.backup_codes.remove(cleaned.upper())
            self._save_state()
            return True, "BACKUP_CODE_ACCEPTED"

        if not cleaned.isdigit() or len(cleaned) != 6:
            return False, "INVALID_CODE"

        current_counter = int(time.time() // self.time_step)
        matched_counter = None
        for step in [0, -1, 1]:
            expected = self.generate_current_code(offset_steps=step)
            if hmac.compare_digest(cleaned, expected):
                matched_counter = current_counter + step
                break

        if matched_counter is None:
            return False, "INVALID_CODE"

        # Durable atomic SQLite anti-replay
        try:
            db_path = STATE_FILE.parent / "aegis_quant.db"
            import sqlite3
            with sqlite3.connect(str(db_path), timeout=30.0) as conn:
                conn.execute("PRAGMA journal_mode=WAL;")
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS totp_consumed_steps (
                        admin_username TEXT NOT NULL,
                        time_counter INTEGER NOT NULL,
                        consumed_at TEXT NOT NULL,
                        PRIMARY KEY (admin_username, time_counter)
                    );
                """)
                conn.execute(
                    "INSERT INTO totp_consumed_steps (admin_username, time_counter, consumed_at) VALUES (?, ?, ?)",
                    (identifier.lower().strip(), matched_counter, str(time.time()))
                )
            return True, "TOTP_ACCEPTED"
        except sqlite3.IntegrityError:
            return False, "TOTP_REPLAY_DETECTED"
        except Exception as e:
            return False, f"PERSISTENCE_ERROR: {e}"

    def get_status(self) -> Dict[str, Any]:
        """Returns public 2FA status snapshot strictly without exposing secrets."""
        return {
            "is_enabled": self.is_enabled,
            "status": "ACTIVE" if self.is_enabled else "NOT_ENABLED",
            "issuer": self.issuer,
            "account_name": self.account_name,
            "backup_codes_remaining": len(self.backup_codes)
        }

    def get_one_time_provisioning(self) -> Dict[str, Any]:
        """Returns one-time setup details ONLY during explicit 2FA enrollment."""
        return {
            "provisioning_uri": self.get_provisioning_uri(),
            "issuer": self.issuer,
            "account_name": self.account_name
        }

totp_authenticator = TOTPAuthenticator()
