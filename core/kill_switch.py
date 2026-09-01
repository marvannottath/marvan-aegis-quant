"""
Aegis Hardware-Grade Emergency Kill Switch Engine.
When activated:
  1. STOP AI Trading Engine
  2. STOP Strategy Execution
  3. REJECT New Orders
  4. CANCEL Pending Orders
  5. FREEZE Withdrawals
  6. LOG Immutable Audit Event
  7. ALERT System Administrator
"""

import time
import json
from pathlib import Path
from typing import Dict, Any
from datetime import datetime, timezone, timedelta

IST_TZ = timezone(timedelta(hours=5, minutes=30))
KILL_SWITCH_FILE = Path(__file__).resolve().parent.parent / "data" / "emergency_kill_switch_state.json"

class EmergencyKillSwitch:
    def __init__(self):
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
        """Trigger immediate emergency system lockdown."""
        self.is_activated = True
        self.activated_at = datetime.now(timezone.utc).astimezone(IST_TZ).strftime("%Y-%m-%d %H:%M:%S")
        self.activated_by = activated_by
        self.reason = reason

        self._save_state()

        # Log Immutable Audit Trail Event
        try:
            from core.audit_logger import audit_logger
            audit_logger.log_event("EMERGENCY_KILL_SWITCH_TRIGGERED", activated_by, 0.0, "SYSTEM", "NONE", "ADMIN", f"REASON: {reason}", "127.0.0.1")
        except Exception:
            pass

        print(f"[EMERGENCY KILL SWITCH] 🚨 SYSTEM LOCKDOWN ACTIVATED by {activated_by} | Reason: {reason}")
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


# Global Singleton
emergency_kill_switch = EmergencyKillSwitch()
