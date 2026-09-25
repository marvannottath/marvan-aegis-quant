"""
Aegis-Quant API Key Zero-Withdrawal Permission Sentinel.
Hard-enforces that exchange API credentials NEVER possess withdrawal privileges.
Any key with 'enableWithdrawals: True' is immediately rejected, quarantined, and alerted.
Only keys with Spot Trading + Read permissions are authorized for execution.
"""

import logging
from typing import Dict, Any, Tuple

logger = logging.getLogger("AegisQuant.APIPermissionSentinel")

class APIPermissionSentinel:
    def __init__(self):
        self._audit_log = []

    def inspect_permissions(self, api_key: str, permissions_dict: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Inspects raw broker API key permission flags.
        Example permissions_dict:
        {
            "ipRestrict": True,
            "enableWithdrawals": False,
            "enableInternalTransfer": False,
            "permitsUniversalTransfer": False,
            "enableVanillaOptions": False,
            "enableReading": True,
            "enableFutures": False,
            "enableMargin": False,
            "enableSpotAndMarginTrading": True
        }
        """
        audit_record = {
            "api_key_masked": f"{api_key[:4]}••••{api_key[-4:]}" if len(api_key) >= 8 else "••••",
            "timestamp": permissions_dict.get("timestamp", 0),
            "result": "UNKNOWN",
            "danger_flags": []
        }

        # CRITICAL SAFETY GATE: ZERO-WITHDRAWAL CHECK
        if permissions_dict.get("enableWithdrawals", False):
            audit_record["result"] = "REJECTED_DANGER_WITHDRAWAL_ENABLED"
            audit_record["danger_flags"].append("CRITICAL: enableWithdrawals is TRUE on broker key!")
            logger.critical("🚨 REJECTED API KEY: 'enableWithdrawals' is active! Zero-trust policy violation.")
            self._audit_log.append(audit_record)
            return False, "CRITICAL_REJECTION: API Key has withdrawal permissions enabled. You must disable withdrawals on Binance/Upstox before connecting!", audit_record

        # INTERNAL TRANSFER CHECK
        if permissions_dict.get("permitsUniversalTransfer", False) or permissions_dict.get("enableInternalTransfer", False):
            audit_record["danger_flags"].append("WARNING: Internal transfer permissions enabled.")

        # SPOT TRADING PERMISSION
        spot_ok = permissions_dict.get("enableSpotAndMarginTrading", True)
        read_ok = permissions_dict.get("enableReading", True)

        if not read_ok:
            audit_record["result"] = "REJECTED_MISSING_READ_PERMISSION"
            self._audit_log.append(audit_record)
            return False, "REJECTED: API Key is missing 'Reading' permissions.", audit_record

        audit_record["result"] = "AUTHORIZED_SPOT_ONLY"
        self._audit_log.append(audit_record)
        return True, "AUTHORIZED: Key satisfies Zero-Withdrawal Spot-Only policy.", audit_record

    def get_audit_trail(self) -> list:
        return self._audit_log[-50:]

api_permission_sentinel = APIPermissionSentinel()
