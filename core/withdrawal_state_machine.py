"""
Aegis-Quant Withdrawal State Machine.
All withdrawals locked by default (LIVE_WITHDRAWALS_ENABLED=false).
Immutable state transitions with ledger-linked fund locking.

Allowed transitions:
  REQUESTED       -> RISK_CHECK | REJECTED
  RISK_CHECK      -> COMPLIANCE_CHECK | REJECTED
  COMPLIANCE_CHECK-> APPROVED | REJECTED
  APPROVED        -> PROCESSING
  PROCESSING      -> COMPLETED | FAILED
"""

import uuid
import time
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta

IST_TZ = timezone(timedelta(hours=5, minutes=30))
WITHDRAWALS_DB = Path(__file__).resolve().parent.parent / "data" / "withdrawals_state_machine.json"


class WithdrawalStateMachineError(Exception):
    pass


WITHDRAWAL_TRANSITIONS: Dict[str, List[str]] = {
    "REQUESTED":        ["RISK_CHECK", "REJECTED"],
    "RISK_CHECK":       ["COMPLIANCE_CHECK", "REJECTED"],
    "COMPLIANCE_CHECK": ["APPROVED", "REJECTED"],
    "APPROVED":         ["PROCESSING"],
    "PROCESSING":       ["COMPLETED", "FAILED"],
    # Terminal
    "COMPLETED": [],
    "REJECTED":  [],
    "FAILED":    [],
}


def _now_str() -> str:
    return datetime.now(timezone.utc).astimezone(IST_TZ).strftime("%Y-%m-%d %H:%M:%S IST")


class WithdrawalStateMachine:
    def __init__(self):
        self.withdrawals: Dict[str, Dict[str, Any]] = {}
        self._load()
        self._save()

    def _load(self):
        WITHDRAWALS_DB.parent.mkdir(parents=True, exist_ok=True)
        if WITHDRAWALS_DB.exists():
            try:
                with open(WITHDRAWALS_DB, "r") as f:
                    self.withdrawals = json.load(f)
            except Exception as e:
                print(f"[WITHDRAWAL_SM] Load error: {e}")

    def _save(self):
        try:
            tmp = WITHDRAWALS_DB.with_suffix(".tmp")
            with open(tmp, "w") as f:
                json.dump(self.withdrawals, f, indent=2)
            tmp.replace(WITHDRAWALS_DB)
        except Exception as e:
            print(f"[WITHDRAWAL_SM] Save error: {e}")

    def request_withdrawal(
        self,
        user_id: str,
        amount: float,
        asset: str,
        destination_address: str,
        network: str,
        environment: str = "PAPER",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create withdrawal in REQUESTED state. Fails immediately if withdrawals are locked."""
        import os
        if os.getenv("LIVE_WITHDRAWALS_ENABLED", "false").lower() != "true":
            return {
                "status": "REJECTED",
                "reason": "LIVE_WITHDRAWALS_ENABLED=false — withdrawals are locked",
                "withdrawal_id": None,
            }
        if amount <= 0:
            return {"status": "REJECTED", "reason": "Amount must be positive", "withdrawal_id": None}

        wid = f"WD-{environment[:3]}-{int(time.time()*1000)}-{uuid.uuid4().hex[:6].upper()}"
        record = {
            "withdrawal_id":      wid,
            "user_id":            user_id,
            "amount":             round(amount, 2),
            "asset":              asset,
            "destination_address":destination_address,
            "network":            network,
            "environment":        environment,
            "status":             "REQUESTED",
            "funds_locked":       False,
            "provider_tx_id":     None,
            "created_at":         _now_str(),
            "updated_at":         _now_str(),
            "transitions": [{"from": None, "to": "REQUESTED", "at": _now_str(), "reason": "Withdrawal requested"}],
            "metadata":           metadata or {},
        }
        self.withdrawals[wid] = record
        self._save()
        return {"status": "REQUESTED", "withdrawal_id": wid, "record": record}

    def transition(
        self,
        withdrawal_id: str,
        new_state: str,
        reason: str = "",
        provider_tx_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Transition withdrawal to new state."""
        if withdrawal_id not in self.withdrawals:
            raise WithdrawalStateMachineError(f"Withdrawal '{withdrawal_id}' not found")

        wd = self.withdrawals[withdrawal_id]
        current = wd["status"]
        allowed = WITHDRAWAL_TRANSITIONS.get(current, [])

        if new_state not in allowed:
            raise WithdrawalStateMachineError(
                f"Invalid transition {current} -> {new_state}. Allowed: {allowed}"
            )

        wd["status"]     = new_state
        wd["updated_at"] = _now_str()

        # Lock funds on APPROVED
        if new_state == "APPROVED":
            wd["funds_locked"] = True

        # Release lock on FAILED
        if new_state == "FAILED":
            wd["funds_locked"] = False

        if provider_tx_id:
            wd["provider_tx_id"] = provider_tx_id

        wd["transitions"].append({"from": current, "to": new_state, "at": _now_str(), "reason": reason})
        self._save()
        return wd

    def get_withdrawal(self, withdrawal_id: str) -> Optional[Dict[str, Any]]:
        return self.withdrawals.get(withdrawal_id)

    def get_pending_withdrawals(self) -> List[Dict[str, Any]]:
        pending_states = {"REQUESTED", "RISK_CHECK", "COMPLIANCE_CHECK", "APPROVED", "PROCESSING"}
        return [w for w in self.withdrawals.values() if w["status"] in pending_states]


# Global singleton
withdrawal_state_machine = WithdrawalStateMachine()
