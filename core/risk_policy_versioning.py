"""
Aegis-Quant Dynamic Risk Management & Policy Versioning Engine.
Enforces:
1. Two-Phase Risk Changes:
   CURRENT STATE -> PROPOSED STATE -> FULL ENGINE CALCULATION -> RISK IMPACT PREVIEW -> CONFIRMATION -> APPLY
2. Impact Classification: LOW | MEDIUM | HIGH | CRITICAL
3. Guard against silent modification: Default to NEW TRADES ONLY.
4. Policy Versioning with 1-Click Rollback.
"""

import json
import time
import uuid
from pathlib import Path
from dataclasses import dataclass, asdict, field
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta

IST_TZ = timezone(timedelta(hours=5, minutes=30))
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
RISK_VERSIONS_FILE = DATA_DIR / "risk_policy_versions.json"
PENDING_RISK_CHANGES_FILE = DATA_DIR / "pending_risk_changes.json"


@dataclass
class RiskImpactPreview:
    preview_id: str
    account_id: str
    workspace: str
    timestamp: str
    current_settings: Dict[str, Any]
    proposed_settings: Dict[str, Any]
    risk_level: str                 # LOW | MEDIUM | HIGH | CRITICAL
    requires_strong_confirmation: bool
    summary: str
    metrics: Dict[str, Any]         # equity, exposure, worst_case_loss, margin_impact, etc.
    affects_existing_positions: bool = False
    status: str = "PENDING_CONFIRMATION"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class RiskPolicyManager:
    """Manages risk proposal calculations, previews, approvals, versioning, and rollback."""

    def __init__(self):
        self._history: List[Dict[str, Any]] = []
        self._pending_previews: Dict[str, RiskImpactPreview] = {}
        self._load()

    def _load(self):
        if RISK_VERSIONS_FILE.exists():
            try:
                with open(RISK_VERSIONS_FILE, "r") as f:
                    self._history = json.load(f)
            except Exception:
                self._history = []

    def _save(self):
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            with open(RISK_VERSIONS_FILE, "w") as f:
                json.dump(self._history, f, indent=2)
        except Exception as e:
            print(f"[RISK POLICY] Save error: {e}")

    def preview_risk_change(
        self,
        account_id: str,
        workspace: str,
        current_state: Dict[str, Any],
        proposed_state: Dict[str, Any],
        account_equity: float,
        current_exposure: float,
        open_positions_count: int,
        tradeable_capital: float
    ) -> RiskImpactPreview:
        """
        Evaluate full engine calculation for proposed risk setting change.
        Classifies risk level: LOW, MEDIUM, HIGH, CRITICAL.
        """
        preview_id = f"RPREV-{int(time.time()*1000)}-{uuid.uuid4().hex[:6].upper()}"
        ts = datetime.now(timezone.utc).astimezone(IST_TZ).strftime("%Y-%m-%d %H:%M:%S IST")

        # 1. Detect Critical Safety Deactivations
        curr_sl = float(current_state.get("stop_loss_pct", 1.0))
        prop_sl = float(proposed_state.get("stop_loss_pct", curr_sl))

        curr_lev = float(current_state.get("max_leverage", 2.0))
        prop_lev = float(proposed_state.get("max_leverage", curr_lev))

        curr_risk_pct = float(current_state.get("max_risk_per_trade_pct", 1.0))
        prop_risk_pct = float(proposed_state.get("max_risk_per_trade_pct", curr_risk_pct))

        curr_daily_loss = float(current_state.get("daily_loss_limit", 1000.0))
        prop_daily_loss = float(proposed_state.get("daily_loss_limit", curr_daily_loss))

        # Worst-case loss calculation on tradeable capital
        worst_case_loss_curr = round(account_equity * (curr_risk_pct / 100.0), 2)
        worst_case_loss_prop = round(account_equity * (prop_risk_pct / 100.0), 2)
        loss_diff = round(worst_case_loss_prop - worst_case_loss_curr, 2)

        # 2. Risk Level Classification
        risk_level = "LOW"
        reasons = []
        requires_strong = False

        if prop_sl <= 0.0 or prop_sl > 10.0:
            risk_level = "CRITICAL"
            reasons.append("Stop-Loss disabled or excessively wide (>10%)")
            requires_strong = True
        elif prop_lev > 25.0:
            risk_level = "CRITICAL"
            reasons.append(f"Extreme leverage requested ({prop_lev}x > 25x)")
            requires_strong = True
        elif prop_daily_loss <= 0:
            risk_level = "CRITICAL"
            reasons.append("Daily loss protection disabled")
            requires_strong = True
        elif prop_risk_pct >= 5.0 or prop_lev >= 15.0:
            risk_level = "HIGH"
            reasons.append(f"High risk per trade ({prop_risk_pct}%) or elevated leverage ({prop_lev}x)")
        elif prop_risk_pct > curr_risk_pct or prop_lev > curr_lev:
            risk_level = "MEDIUM"
            reasons.append("Risk or leverage increased above current baseline")
        else:
            risk_level = "LOW"
            reasons.append("Conservative adjustment or risk reduction")

        summary_msg = "; ".join(reasons)

        metrics = {
            "current_equity": round(account_equity, 2),
            "current_exposure_pct": round(current_exposure, 2),
            "open_positions_count": open_positions_count,
            "tradeable_capital": round(tradeable_capital, 2),
            "current_risk_per_trade_pct": curr_risk_pct,
            "proposed_risk_per_trade_pct": prop_risk_pct,
            "current_worst_case_loss": worst_case_loss_curr,
            "proposed_worst_case_loss": worst_case_loss_prop,
            "worst_case_loss_delta": loss_diff,
            "current_max_leverage": curr_lev,
            "proposed_max_leverage": prop_lev,
            "current_daily_loss_limit": curr_daily_loss,
            "proposed_daily_loss_limit": prop_daily_loss
        }

        preview = RiskImpactPreview(
            preview_id=preview_id,
            account_id=account_id,
            workspace=workspace,
            timestamp=ts,
            current_settings=current_state,
            proposed_settings=proposed_state,
            risk_level=risk_level,
            requires_strong_confirmation=requires_strong,
            summary=summary_msg,
            metrics=metrics,
            affects_existing_positions=False,    # Default NEW TRADES ONLY
            status="PENDING_CONFIRMATION"
        )

        self._pending_previews[preview_id] = preview
        return preview

    def apply_confirmed_risk_change(
        self,
        preview_id: str,
        user_actor: str = "TRADER",
        confirmation_code: Optional[str] = None,
        confirmed: bool = True
    ) -> Dict[str, Any]:
        """
        Apply risk change ONLY AFTER explicit user confirmation.
        Persists immutable version record with full audit trail.
        """
        if not confirmed:
            return {"status": "ERROR", "message": "Confirmation flag is false"}

        if preview_id not in self._pending_previews:
            return {"status": "ERROR", "message": f"Preview ID '{preview_id}' not found or expired"}

        prev = self._pending_previews[preview_id]
        if prev.requires_strong_confirmation and not confirmation_code:
            return {
                "status": "REQUIRES_STRONG_CONFIRMATION",
                "message": "Critical risk policy change requires explicit confirmation confirmation_code='CONFIRM_CRITICAL_RISK'"
            }
        if prev.requires_strong_confirmation and confirmation_code != "CONFIRM_CRITICAL_RISK":
            return {
                "status": "CONFIRMATION_REJECTED",
                "message": "Invalid confirmation code for critical risk change"
            }

        version_num = len(self._history) + 1
        record = {
            "version": f"v{version_num}.0",
            "preview_id": preview_id,
            "account_id": prev.account_id,
            "workspace": prev.workspace,
            "old_settings": prev.current_settings,
            "new_settings": prev.proposed_settings,
            "calculated_impact": prev.metrics,
            "risk_level": prev.risk_level,
            "timestamp": datetime.now(timezone.utc).astimezone(IST_TZ).strftime("%Y-%m-%d %H:%M:%S IST"),
            "actor": user_actor,
            "affects_existing_positions": prev.affects_existing_positions,
            "status": "APPLIED"
        }

        self._history.insert(0, record)
        self._save()
        del self._pending_previews[preview_id]

        return {
            "status": "APPLIED",
            "version": record["version"],
            "new_settings": prev.proposed_settings,
            "message": f"Risk policy version {record['version']} applied successfully"
        }

    def rollback_to_previous_policy(self, user_actor: str = "SUPER_ADMIN") -> Dict[str, Any]:
        """Roll back to the previous known-good policy."""
        if len(self._history) < 1:
            return {"status": "ERROR", "message": "No historical policy versions available for rollback"}

        current_active = self._history[0]
        # Target is the old_settings of current active
        previous_settings = current_active.get("old_settings")
        if not previous_settings:
            return {"status": "ERROR", "message": "No previous settings recorded in active policy"}

        rollback_record = {
            "version": f"v{len(self._history) + 1}.0-ROLLBACK",
            "account_id": current_active.get("account_id"),
            "workspace": current_active.get("workspace"),
            "old_settings": current_active.get("new_settings"),
            "new_settings": previous_settings,
            "calculated_impact": {"action": "ROLLBACK_TO_KNOWN_GOOD"},
            "risk_level": "LOW",
            "timestamp": datetime.now(timezone.utc).astimezone(IST_TZ).strftime("%Y-%m-%d %H:%M:%S IST"),
            "actor": user_actor,
            "status": "ROLLED_BACK"
        }

        self._history.insert(0, rollback_record)
        self._save()

        return {
            "status": "ROLLED_BACK",
            "restored_settings": previous_settings,
            "version": rollback_record["version"],
            "message": f"Rolled back to previous risk policy: {rollback_record['version']}"
        }

    def get_version_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        return self._history[:limit]

    apply_confirmed_change = apply_confirmed_risk_change
    get_history = get_version_history


# Global singleton
risk_policy_manager = RiskPolicyManager()
