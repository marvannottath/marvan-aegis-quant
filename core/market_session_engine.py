"""
AEGIS QUANT — Market Session Engine
=====================================
Authoritative per-workspace market session state machine.

States:
    PRE_MARKET    — session not yet open, pre-market window
    OPEN          — trading active
    CLOSING_SOON  — within closing warning window (last 5 minutes)
    CLOSED        — session ended for the day
    HOLIDAY       — exchange / public holiday
    HALTED        — trading halted (circuit breaker or manual)
    UNKNOWN       — unable to determine state

Rules:
    - MARKET CLOSED does NOT mean POSITION CLOSED.
    - MARKET CLOSED blocks new AI entries and autonomous signals.
    - Frontend must NEVER hardcode market state — always read from this engine.
    - All state transitions emit an immutable SHA-256-chained audit event.
    - State overrides (HALTED, HOLIDAY) persist in data/market_session_state.json.
"""

import json
import threading
from datetime import datetime, timezone, timedelta, date
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

IST = timezone(timedelta(hours=5, minutes=30))
UTC = timezone.utc

# State constants
PRE_MARKET   = "PRE_MARKET"
OPEN         = "OPEN"
CLOSING_SOON = "CLOSING_SOON"
CLOSED       = "CLOSED"
HOLIDAY      = "HOLIDAY"
HALTED       = "HALTED"
UNKNOWN      = "UNKNOWN"

WORKSPACES = ("INDIA", "FOREX_GOLD", "CRYPTO")

# NSE/BSE 2026 holiday list (trading holidays — markets closed)
# Source: NSE India official calendar
NSE_HOLIDAYS_2026 = {
    date(2026, 1, 26),   # Republic Day
    date(2026, 3, 25),   # Holi
    date(2026, 4, 2),    # Ram Navami
    date(2026, 4, 3),    # Good Friday
    date(2026, 4, 14),   # Dr. Ambedkar Jayanti
    date(2026, 5, 1),    # Maharashtra Day / Labour Day
    date(2026, 8, 15),   # Independence Day
    date(2026, 10, 2),   # Mahatma Gandhi Jayanti
    date(2026, 11, 4),   # Diwali Laxmi Pujan
    date(2026, 11, 5),   # Diwali Balipratipada
    date(2026, 12, 25),  # Christmas
}

FOREX_HOLIDAYS_2026 = {
    date(2026, 1, 1),    # New Year's Day
    date(2026, 12, 25),  # Christmas
}

STATE_FILE = Path("data/market_session_state.json")


class MarketSessionEngine:
    """
    Authoritative market session state machine for all workspaces.
    Thread-safe. State persisted to disk for manual overrides (HALTED, HOLIDAY).
    """

    def __init__(self):
        self._lock = threading.RLock()
        self._overrides: Dict[str, Dict[str, Any]] = {}  # workspace → override
        self._last_states: Dict[str, str] = {ws: UNKNOWN for ws in WORKSPACES}
        self._last_transition: Dict[str, str] = {}
        self._load_overrides()

    # ─── Persistence ─────────────────────────────────────────────────────────

    def _load_overrides(self):
        """Load manual overrides (HALTED, HOLIDAY) from disk."""
        try:
            if STATE_FILE.exists():
                raw = json.loads(STATE_FILE.read_text())
                self._overrides = raw.get("overrides", {})
        except Exception:
            self._overrides = {}

    def _save_overrides(self):
        """Persist manual overrides to disk."""
        try:
            STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "overrides": self._overrides,
                "saved_at": datetime.now(UTC).isoformat(),
            }
            tmp = STATE_FILE.with_suffix(".tmp")
            tmp.write_text(json.dumps(payload, indent=2))
            tmp.replace(STATE_FILE)
        except Exception:
            pass

    # ─── India Session ────────────────────────────────────────────────────────

    def _india_session_state(self, now_ist: datetime) -> str:
        """Return NSE/BSE session state for the given IST datetime."""
        d = now_ist.date()
        # Weekend
        if now_ist.weekday() >= 5:  # Sat=5, Sun=6
            return CLOSED
        # Holiday
        if d in NSE_HOLIDAYS_2026:
            return HOLIDAY

        h = now_ist.hour
        m = now_ist.minute

        # PRE_MARKET: 09:00–09:14
        if (h == 9 and m < 15):
            return PRE_MARKET
        # OPEN: 09:15–15:24
        if (h == 9 and m >= 15) or (10 <= h <= 14) or (h == 15 and m < 25):
            return OPEN
        # CLOSING_SOON: 15:25–15:29
        if h == 15 and 25 <= m <= 29:
            return CLOSING_SOON
        # CLOSED: 15:30 onwards
        if (h == 15 and m >= 30) or h > 15:
            return CLOSED
        # Before 09:00
        return CLOSED

    # ─── Forex/Gold Session ───────────────────────────────────────────────────

    def _forex_session_state(self, now_utc: datetime) -> str:
        """Return Forex/Gold session state for the given UTC datetime."""
        d = now_utc.date()
        if d in FOREX_HOLIDAYS_2026:
            return HOLIDAY

        weekday = now_utc.weekday()  # Mon=0 … Sun=6
        h = now_utc.hour

        # Weekend close: Fri 22:00 UTC → Sun 22:00 UTC
        if weekday == 4 and h >= 22:    # Friday after 22:00 UTC
            return CLOSED
        if weekday == 5:                # Saturday
            return CLOSED
        if weekday == 6 and h < 22:     # Sunday before 22:00 UTC
            return CLOSED

        return OPEN

    # ─── Crypto Session ───────────────────────────────────────────────────────

    def _crypto_session_state(self) -> str:
        """Crypto markets are 24/7. Always OPEN unless manually HALTED."""
        return OPEN

    # ─── Main State Resolver ──────────────────────────────────────────────────

    def get_state(self, workspace: str) -> str:
        """
        Return authoritative session state for the given workspace.
        Manual overrides (HALTED, HOLIDAY) take precedence over computed state.
        """
        with self._lock:
            ws = workspace.upper()
            # Check manual override first
            override = self._overrides.get(ws, {})
            if override.get("active"):
                state = override.get("state", UNKNOWN)
                return state

            now_utc = datetime.now(UTC)
            now_ist = now_utc.astimezone(IST)

            if ws == "INDIA":
                state = self._india_session_state(now_ist)
            elif ws == "FOREX_GOLD":
                state = self._forex_session_state(now_utc)
            elif ws == "CRYPTO":
                state = self._crypto_session_state()
            else:
                state = UNKNOWN

            # Detect transitions for audit logging
            prev = self._last_states.get(ws, UNKNOWN)
            if prev != state:
                self._last_states[ws] = state
                self._emit_transition_audit(ws, prev, state)

            return state

    def get_all_states(self) -> Dict[str, Dict[str, Any]]:
        """Return session states for all workspaces with metadata."""
        result = {}
        now_ist = datetime.now(UTC).astimezone(IST)
        for ws in WORKSPACES:
            state = self.get_state(ws)
            override_active = bool(self._overrides.get(ws, {}).get("active"))
            result[ws] = {
                "workspace": ws,
                "state": state,
                "is_trading_allowed": state in (OPEN, CLOSING_SOON),
                "is_new_entry_allowed": state == OPEN,
                "is_ai_blocked": state not in (OPEN,),
                "evaluated_at_ist": now_ist.strftime("%Y-%m-%d %H:%M:%S IST"),
                "evaluated_timestamp": now_ist.strftime("%Y-%m-%d %H:%M:%S IST"),
                "manual_override_active": override_active,
                "manual_override_status": "ACTIVE" if override_active else "INACTIVE",
                "override_reason": self._overrides.get(ws, {}).get("reason", ""),
            }
        return result

    def get_state_detail(self, workspace: str) -> Dict[str, Any]:
        """Full state detail for a single workspace."""
        ws = workspace.upper()
        state = self.get_state(ws)
        now_ist = datetime.now(UTC).astimezone(IST)
        override = self._overrides.get(ws, {})

        # Next session open estimate for India
        next_open = None
        if ws == "INDIA" and state in (CLOSED, HOLIDAY):
            tomorrow = now_ist.date() + timedelta(days=1)
            days_ahead = 0
            for i in range(1, 8):
                candidate = now_ist.date() + timedelta(days=i)
                if candidate.weekday() < 5 and candidate not in NSE_HOLIDAYS_2026:
                    next_open = f"{candidate} 09:15:00 IST"
                    break

        return {
            "workspace": ws,
            "state": state,
            "is_trading_allowed": state in (OPEN, CLOSING_SOON),
            "is_new_entry_allowed": state == OPEN,
            "is_ai_blocked": state not in (OPEN,),
            "evaluated_at_ist": now_ist.strftime("%Y-%m-%d %H:%M:%S IST"),
            "evaluated_timestamp": now_ist.strftime("%Y-%m-%d %H:%M:%S IST"),
            "manual_override_active": bool(override.get("active")),
            "manual_override_status": "ACTIVE" if bool(override.get("active")) else "INACTIVE",
            "override_state": override.get("state"),
            "override_reason": override.get("reason", ""),
            "override_by": override.get("by", ""),
            "override_at": override.get("at", ""),
            "next_session_open": next_open,
        }

    # ─── Manual Overrides ─────────────────────────────────────────────────────

    def set_halted(self, workspace: str, reason: str, by: str) -> Dict[str, Any]:
        """Manually HALT a workspace session (circuit breaker or admin decision)."""
        with self._lock:
            ws = workspace.upper()
            if ws not in WORKSPACES:
                return {"ok": False, "error": f"Unknown workspace: {workspace}"}
            prev = self.get_state(ws)
            self._overrides[ws] = {
                "active": True,
                "state": HALTED,
                "reason": reason,
                "by": by,
                "at": datetime.now(UTC).isoformat(),
            }
            self._save_overrides()
            self._emit_halt_audit(ws, prev, HALTED, reason, by)
            return {"ok": True, "workspace": ws, "state": HALTED, "reason": reason}

    def clear_halt(self, workspace: str, by: str) -> Dict[str, Any]:
        """Clear manual HALT override, returning to computed state."""
        with self._lock:
            ws = workspace.upper()
            if ws not in WORKSPACES:
                return {"ok": False, "error": f"Unknown workspace: {workspace}"}
            prev_override = self._overrides.pop(ws, {})
            self._save_overrides()
            new_state = self.get_state(ws)
            self._emit_halt_audit(ws, prev_override.get("state", HALTED), new_state, "Halt cleared", by)
            return {"ok": True, "workspace": ws, "state": new_state, "message": "Manual HALT cleared"}

    def set_holiday(self, workspace: str, reason: str, by: str) -> Dict[str, Any]:
        """Manually mark a workspace as HOLIDAY."""
        with self._lock:
            ws = workspace.upper()
            if ws not in WORKSPACES:
                return {"ok": False, "error": f"Unknown workspace: {workspace}"}
            prev = self.get_state(ws)
            self._overrides[ws] = {
                "active": True,
                "state": HOLIDAY,
                "reason": reason,
                "by": by,
                "at": datetime.now(UTC).isoformat(),
            }
            self._save_overrides()
            self._emit_halt_audit(ws, prev, HOLIDAY, reason, by)
            return {"ok": True, "workspace": ws, "state": HOLIDAY, "reason": reason}

    # ─── Audit Emission ───────────────────────────────────────────────────────

    def _emit_transition_audit(self, workspace: str, prev: str, new: str):
        """Emit audit event for session state transition."""
        try:
            from core.audit_logger import audit_logger
            event_type = "MARKET_OPEN" if new in (OPEN, PRE_MARKET) else "MARKET_CLOSE"
            audit_logger.log_event(
                event_type=event_type,
                workspace=workspace,
                amount=0.0,
                symbol="MARKET_SESSION",
                order_id="SYSTEM",
                user="MARKET_SESSION_ENGINE",
                execution_id=f"MKT-{workspace}-{new}",
                ip_address="SYSTEM",
                environment="ALL",
                previous_state=prev,
                new_state=new,
                session_engine="MarketSessionEngine",
            )
        except Exception:
            pass  # Audit failure must never break session engine

    def _emit_halt_audit(self, workspace: str, prev: str, new: str, reason: str, by: str):
        """Emit audit event for manual HALT/HOLIDAY override."""
        try:
            from core.audit_logger import audit_logger
            audit_logger.log_event(
                event_type="MARKET_HALTED" if new == HALTED else "MARKET_HOLIDAY_SET",
                workspace=workspace,
                amount=0.0,
                symbol="MARKET_SESSION",
                order_id="SYSTEM",
                user=by,
                execution_id=f"MKT-HALT-{workspace}",
                ip_address="SYSTEM",
                environment="ALL",
                previous_state=prev,
                new_state=new,
                reason=reason,
            )
        except Exception:
            pass


# Global singleton
market_session_engine = MarketSessionEngine()
