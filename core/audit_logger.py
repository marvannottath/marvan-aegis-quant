"""
Immutable Financial Audit Logger for Aegis Quant.
Records all financial events (deposit_created, deposit_credited, withdrawal_requested, etc.) with IP & session metadata.
"""

import json
import time
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime, timezone, timedelta

IST_TZ = timezone(timedelta(hours=5, minutes=30))
AUDIT_LOG_FILE = Path(__file__).resolve().parent.parent / "data" / "financial_audit_log.json"

class FinancialAuditLogger:
    def __init__(self):
        self.logs: List[Dict[str, Any]] = []
        self._load_logs()

    def _load_logs(self):
        if AUDIT_LOG_FILE.exists():
            try:
                with open(AUDIT_LOG_FILE, "r") as f:
                    data = json.load(f)
                    self.logs = data.get("logs", [])
            except Exception as e:
                print(f"[AUDIT LOG] Load error: {e}")

    def _save_logs(self):
        try:
            AUDIT_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
            temp_file = AUDIT_LOG_FILE.with_suffix(".tmp")
            with open(temp_file, "w") as f:
                json.dump({"logs": self.logs}, f, indent=2)
            temp_file.replace(AUDIT_LOG_FILE)
        except Exception as e:
            print(f"[AUDIT LOG] Save error: {e}")

    def log_event(
        self,
        event_type: str,
        user_id: str,
        amount: float,
        asset: str = "USDT",
        network: str = "TRC20",
        provider: str = "BINANCE",
        reference_id: str = "",
        ip_address: str = "127.0.0.1",
        environment: str = "AEGIS_QUANT_MASTER"
    ) -> Dict[str, Any]:
        event_id = f"AUD-{int(time.time()*1000)}-{event_type[:4].upper()}"
        record = {
            "event_id": event_id,
            "timestamp": datetime.now(timezone.utc).astimezone(IST_TZ).strftime("%Y-%m-%d %H:%M:%S"),
            "event_type": event_type,
            "user_id": user_id,
            "environment": environment,
            "amount": round(amount, 2),
            "asset": asset,
            "network": network,
            "provider": provider,
            "reference_id": reference_id,
            "ip_address": ip_address
        }
        self.logs.insert(0, record)
        self._save_logs()
        return record

    def get_audit_trail(self, environment: str = "AEGIS_QUANT_MASTER") -> List[Dict[str, Any]]:
        return [l for l in self.logs if l["environment"] == environment]


# Global Singleton
audit_logger = FinancialAuditLogger()
