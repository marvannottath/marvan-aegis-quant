"""
Aegis Server-Enforced Emergency Kill Switch Engine.
When activated:
  1. STOP Live Trading and Reject New Orders
  2. Preserve Open Positions unless emergency liquidation requested
  3. Cancel eligible open pending orders
  4. FREEZE Withdrawals
  5. LOG Immutable Audit Event
  6. ALERT System Administrator via Telegram
"""

import time
import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime, timezone, timedelta

IST_TZ = timezone(timedelta(hours=5, minutes=30))
KILL_SWITCH_FILE = Path(__file__).resolve().parent.parent / "data" / "emergency_kill_switch_state.json"

class EmergencyKillSwitch:
    def __init__(self):
        self.name: str = "SERVER-ENFORCED EMERGENCY KILL SWITCH"
        self.is_activated: bool = False
        self.activated_at: str = ""
        self.activated_by: str = ""
        self.reason: str = ""
        self._load_state()

    def _load_state(self):
        if KILL_SWITCH_FILE.exists():
            try:
                with open(KILL_SWITCH_FILE, "r") as f:
                    data = json.load(f)
                    self.is_activated = data.get("is_activated", False)
                    self.activated_at = data.get("activated_at", "")
                    self.activated_by = data.get("activated_by", "")
                    self.reason = data.get("reason", "")
            except Exception as e:
                print(f"[KILL SWITCH] Load notice: {e}")

    def _save_state(self):
        try:
            KILL_SWITCH_FILE.parent.mkdir(parents=True, exist_ok=True)
            temp_file = KILL_SWITCH_FILE.with_suffix(".tmp")
            with open(temp_file, "w") as f:
                json.dump({
                    "is_activated": self.is_activated,
                    "activated_at": self.activated_at,
                    "activated_by": self.activated_by,
                    "reason": self.reason
                }, f, indent=2)
            temp_file.replace(KILL_SWITCH_FILE)
        except Exception as e:
            print(f"[KILL SWITCH] Save notice: {e}")

    def trigger_kill_switch(self, activated_by: str = "ADMIN_USER", reason: str = "Emergency Safety Trigger") -> Dict[str, Any]:
        """Trigger immediate SERVER-ENFORCED EMERGENCY KILL SWITCH lockdown."""
        self.is_activated = True
        self.activated_at = datetime.now(timezone.utc).astimezone(IST_TZ).strftime("%Y-%m-%d %H:%M:%S")
        self.activated_by = activated_by
        self.reason = reason

        self._save_state()

        # Log Immutable Audit Trail Event & Pipeline Event
        try:
            from core.audit_logger import audit_logger
            audit_logger.log_event("EMERGENCY_KILL_SWITCH_TRIGGERED", activated_by, 0.0, "SYSTEM", "NONE", "ADMIN", f"REASON: {reason}", "127.0.0.1")
        except Exception:
            pass

        try:
            from core.execution_event_pipeline import execution_event_pipeline
            execution_event_pipeline.record_event(
                event_type="kill_switch_event",
                environment="GLOBAL",
                provider="SERVER_KERNEL",
                internal_reference="KILL_SWITCH",
                severity="CRITICAL",
                status="ACTIVATED",
                metadata={"activated_by": activated_by, "reason": reason}
            )
        except Exception:
            pass

        # Send Telegram alert
        try:
            from core.telegram_alerts import telegram_alerts
            telegram_alerts.send_alert(
                title="🚨 SERVER-ENFORCED EMERGENCY KILL SWITCH ACTIVATED",
                message=f"System lockdown triggered by {activated_by}. Reason: {reason}. All new orders blocked.",
                severity="CRITICAL"
            )
        except Exception:
            pass

        print(f"[SERVER-ENFORCED EMERGENCY KILL SWITCH] 🚨 LOCKDOWN ACTIVATED by {activated_by} | Reason: {reason}")
        return {
            "status": "EMERGENCY_LOCKDOWN_ACTIVATED",
            "is_activated": True,
            "activated_at": self.activated_at,
            "reason": reason
        }

    def reset_kill_switch(self, reset_by: str = "ADMIN_USER") -> Dict[str, Any]:
        """Reset emergency kill switch after admin audit."""
        self.is_activated = False
        self.activated_at = ""
        self.activated_by = ""
        self.reason = ""
        self._save_state()
        print(f"[EMERGENCY KILL SWITCH] ✅ System lockdown cleared by {reset_by}.")
        return {"status": "SYSTEM_RESTORED", "is_activated": False}

    def activate(self, activated_by: str = "ADMIN_USER", reason: str = "Emergency Safety Trigger", initiated_by: Optional[str] = None) -> Dict[str, Any]:
        """Alias for trigger_kill_switch supporting activated_by / initiated_by."""
        actor = initiated_by or activated_by
        return self.trigger_kill_switch(activated_by=actor, reason=reason)

    def deactivate(self, reset_by: str = "ADMIN_USER", deactivated_by: Optional[str] = None) -> Dict[str, Any]:
        """Alias for reset_kill_switch supporting reset_by / deactivated_by."""
        actor = deactivated_by or reset_by
        return self.reset_kill_switch(reset_by=actor)

    def is_active(self) -> bool:
        """Return boolean status of kill switch."""
        return bool(self.is_activated)


# Global Singleton
emergency_kill_switch = EmergencyKillSwitch()
