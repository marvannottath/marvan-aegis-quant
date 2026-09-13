"""
Immutable Financial Audit Logger for Aegis Quant.
Records all financial events (deposit_created, deposit_credited, withdrawal_requested, etc.) with IP & session metadata.
"""

import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
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
        user_id: str = "USER-MAIN",
        amount: float = 0.0,
        asset: str = "INR",
        network: str = "NSE",
        provider: str = "UPSTOX",
        reference_id: str = "",
        ip_address: str = "127.0.0.1",
        environment: str = "AEGIS_INDIA_INR",
        workspace: Optional[str] = None,
        venue: Optional[str] = None,
        symbol: Optional[str] = None,
        result: str = "SUCCESS",
        correlation_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        event_id = f"AUD-{int(time.time()*1000)}-{event_type[:4].upper()}"
        now_str = datetime.now(timezone.utc).astimezone(IST_TZ).strftime("%Y-%m-%d %H:%M:%S")
        corr_id = correlation_id or reference_id or event_id

        # Determine workspace & venue intelligently if not explicitly provided
        ws = workspace
        if not ws:
            if "INDIA" in environment or asset == "INR" or network in ["NSE", "BSE"] or provider == "UPSTOX":
                ws = "INDIA"
            elif "BINANCE" in environment or asset in ["USDT", "BTC", "ETH", "SOL"] or provider == "BINANCE":
                ws = "CRYPTO"
            else:
                ws = "FOREX_GOLD"

        vn = venue
        if not vn:
            vn = "NSE/BSE" if ws == "INDIA" else ("BINANCE" if ws == "CRYPTO" else "GLOBAL_FX")

        sym = symbol or asset

        record = {
            "event_id": event_id,
            "timestamp": now_str,
            "event_type": event_type,
            "user_id": user_id,
            "environment": environment,
            "workspace": ws,
            "venue": vn,
            "symbol": sym,
            "result": result,
            "amount": round(float(amount or 0.0), 2),
            "asset": asset,
            "network": network,
            "provider": provider,
            "reference_id": reference_id or corr_id,
            "correlation_id": corr_id,
            "ip_address": ip_address
        }
        for k, v in kwargs.items():
            if k not in record:
                record[k] = v

        self.logs.insert(0, record)
        self._save_logs()
        try:
            from core.unified_database import unified_db
            unified_db.log_audit_action(
                actor=user_id,
                action=event_type,
                category=provider,
                details=record
            )
        except Exception:
            pass
        return record

    def get_audit_trail(self, environment: Optional[str] = None, workspace: Optional[str] = None) -> List[Dict[str, Any]]:
        logs = self.logs
        if workspace and workspace not in ["ALL", ""]:
            ws_norm = "INDIA" if "IND" in workspace.upper() else ("CRYPTO" if "CRYP" in workspace.upper() or "BINANCE" in workspace.upper() else "FOREX_GOLD")
            matched = [l for l in logs if l.get("workspace") == ws_norm or (ws_norm == "INDIA" and l.get("asset") == "INR")]
            return matched
        if environment and environment not in ["ALL", ""]:
            matched = [l for l in logs if l.get("environment") == environment]
            if matched:
                return matched
        return logs


# Global Singleton
audit_logger = FinancialAuditLogger()
