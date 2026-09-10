"""
Aegis-Quant Real-Time Execution & Audit Event Pipeline.
Propagates all trading, risk, lifecycle, and reconciliation state changes through
an immutable audit event stream.

Pipeline Flow:
  Market Data -> AEGIS Signal -> Risk Engine -> Order Router -> Provider API
  -> Provider Ack -> Execution Event -> Position Engine -> PnL Engine -> Wallet
  -> Double-Entry Ledger -> Analytics -> Audit Stream -> UI / Telegram.

Schema per event:
  event_id, timestamp, environment, provider, internal_reference,
  provider_reference, severity, event_type, status, metadata.
"""

import os
import time
import json
import uuid
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta

IST_TZ = timezone(timedelta(hours=5, minutes=30))
AUDIT_STREAM_FILE = Path(__file__).resolve().parent.parent / "data" / "execution_audit_stream.json"


def _now_str() -> str:
    return datetime.now(timezone.utc).astimezone(IST_TZ).strftime("%Y-%m-%d %H:%M:%S IST")


def _scrub_sensitive(data: Any) -> Any:
    """Recursively scrub any API keys, secrets, or bearer tokens from metadata."""
    if isinstance(data, dict):
        scrubbed = {}
        for k, v in data.items():
            k_lower = str(k).lower()
            if any(term in k_lower for term in ["secret", "api_key", "token", "password", "auth", "private_key"]):
                scrubbed[k] = "[REDACTED]" if v else ""
            else:
                scrubbed[k] = _scrub_sensitive(v)
        return scrubbed
    elif isinstance(data, list):
        return [_scrub_sensitive(i) for i in data]
    return data


class ExecutionEventPipeline:
    """
    Dedicated Execution & Audit Event Stream Engine.
    Emits structured events, writes to file and SQLite, and provides queries.
    """

    # Valid event types
    EVENT_TYPES = {
        "market_event",
        "signal_event",
        "risk_decision",
        "order_created",
        "order_submitted",
        "provider_acknowledged",
        "partial_fill",
        "complete_fill",
        "order_cancelled",
        "order_rejected",
        "position_updated",
        "pnl_updated",
        "wallet_updated",
        "ledger_entry",
        "reconciliation_result",
        "provider_disconnected",
        "websocket_reconnected",
        "api_error",
        "rate_limit_event",
        "kill_switch_event",
    }

    def __init__(self):
        self.events: List[Dict[str, Any]] = []
        self._max_in_memory: int = 1000
        self._load_stream()

    def _load_stream(self):
        AUDIT_STREAM_FILE.parent.mkdir(parents=True, exist_ok=True)
        if AUDIT_STREAM_FILE.exists():
            try:
                with open(AUDIT_STREAM_FILE, "r") as f:
                    data = json.load(f)
                    self.events = data.get("events", [])[-self._max_in_memory:]
            except Exception as e:
                print(f"[EVENT_PIPELINE] Stream load notice: {e}")

    def _save_stream(self):
        try:
            tmp = AUDIT_STREAM_FILE.with_suffix(".tmp")
            with open(tmp, "w") as f:
                json.dump({"events": self.events[-self._max_in_memory:]}, f, indent=2)
            tmp.replace(AUDIT_STREAM_FILE)
        except Exception as e:
            print(f"[EVENT_PIPELINE] Stream save error: {e}")

    def record_event(
        self,
        event_type: str,
        environment: str,
        provider: str = "BINANCE",
        internal_reference: str = "",
        provider_reference: str = "",
        severity: str = "INFO",
        status: str = "COMPLETED",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Record an immutable execution or audit event into the stream.
        Appends to memory, persists to JSON mirror, and writes to SQLite.
        """
        now_ts = _now_str()
        tag = event_type.replace("_", "")[:4].upper()
        event_id = f"EVT-{environment[:3].upper()}-{int(time.time()*1000)}-{tag}-{uuid.uuid4().hex[:4].upper()}"

        scrubbed_meta = _scrub_sensitive(metadata or {})

        event = {
            "event_id":           event_id,
            "timestamp":          now_ts,
            "environment":        environment,
            "provider":           provider.upper(),
            "internal_reference": internal_reference,
            "provider_reference": provider_reference,
            "severity":           severity.upper(),
            "event_type":         event_type,
            "status":             status.upper(),
            "metadata":           scrubbed_meta,
        }

        self.events.insert(0, event)
        if len(self.events) > self._max_in_memory:
            self.events = self.events[:self._max_in_memory]

        self._save_stream()

        # Synchronize to SQLite unified database
        try:
            from core.unified_database import unified_db
            unified_db.log_audit_action(
                actor=f"{provider.upper()}_PIPELINE",
                action=event_type,
                category=severity.upper(),
                details=event
            )
        except Exception:
            pass

        return event

    def get_events(
        self,
        limit: int = 50,
        environment: Optional[str] = None,
        event_type: Optional[str] = None,
        severity: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve recent events filtered by environment, type, or severity."""
        filtered = self.events
        if environment:
            filtered = [e for e in filtered if e.get("environment") == environment]
        if event_type:
            filtered = [e for e in filtered if e.get("event_type") == event_type]
        if severity:
            filtered = [e for e in filtered if e.get("severity") == severity.upper()]
        return filtered[:limit]


# Global singleton
execution_event_pipeline = ExecutionEventPipeline()
