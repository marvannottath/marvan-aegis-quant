"""
AEGIS-QUANT Telegram Alerting & Notification Engine.
Provides outbound dispatching for critical system events:
  - Orders (Submitted, Filled, Rejected)
  - Positions (Opened, Closed, Stop-Loss, Take-Profit)
  - Risk & Safety (Circuit Breakers, Kill Switch, Reconciliation Failure)
  - Security Events
Never exposes raw bot tokens in API responses.
Truthfully reports NOT_CONFIGURED when environment variables are unset.
"""

import os
import json
import time
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime, timezone, timedelta

IST_TZ = timezone(timedelta(hours=5, minutes=30))

CONFIG_FILE = Path(__file__).resolve().parent.parent / "data" / "notification_config.json"


def get_ist_now() -> str:
    return datetime.now(timezone.utc).astimezone(IST_TZ).strftime("%Y-%m-%d %H:%M:%S IST")


class TelegramAlerts:
    def __init__(self):
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
        self.enabled = bool(self.bot_token and self.chat_id)
        self.last_delivery_status: str = "NOT_SENT"
        self.last_delivery_time: Optional[str] = None
        self.delivery_log: list = []
        self._load_config()

    def _load_config(self):
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r") as f:
                    cfg = json.load(f)
                    if not self.bot_token:
                        self.bot_token = cfg.get("telegram_bot_token", "")
                    if not self.chat_id:
                        self.chat_id = cfg.get("telegram_chat_id", "")
                    self.enabled = bool(self.bot_token and self.chat_id)
            except Exception as e:
                print(f"[TELEGRAM] Config load notice: {e}")

    def get_status(self) -> Dict[str, Any]:
        """Return truthful configuration and connection status without exposing bot token."""
        return {
            "configured": self.enabled,
            "status": "CONFIGURED" if self.enabled else "NOT_CONFIGURED",
            "chat_id_configured": bool(self.chat_id),
            "bot_token_set": bool(self.bot_token),
            "last_delivery_status": self.last_delivery_status,
            "last_delivery_time": self.last_delivery_time,
            "recent_deliveries_count": len(self.delivery_log)
        }

    def send_alert(self, title: str, message: str, event_type: str = "SYSTEM_ALERT") -> Dict[str, Any]:
        """Dispatch message to Telegram if configured."""
        now = get_ist_now()
        if not self.enabled:
            record = {
                "timestamp": now,
                "event_type": event_type,
                "title": title,
                "status": "SKIPPED_NOT_CONFIGURED",
                "detail": "TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not configured."
            }
            self.delivery_log.insert(0, record)
            return {"success": False, "status": "NOT_CONFIGURED", "detail": record["detail"]}

        formatted_text = f"🚨 *AEGIS QUANT — {title}*\n\n{message}\n\n🕒 _{now}_"
        try:
            import requests
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            resp = requests.post(url, json={
                "chat_id": self.chat_id,
                "text": formatted_text,
                "parse_mode": "Markdown"
            }, timeout=5.0)

            if resp.status_code == 200:
                self.last_delivery_status = "DELIVERED"
                self.last_delivery_time = now
                record = {"timestamp": now, "event_type": event_type, "title": title, "status": "DELIVERED"}
                self.delivery_log.insert(0, record)
                return {"success": True, "status": "DELIVERED", "timestamp": now}
            else:
                self.last_delivery_status = f"FAILED_HTTP_{resp.status_code}"
                self.last_delivery_time = now
                record = {"timestamp": now, "event_type": event_type, "title": title, "status": self.last_delivery_status}
                self.delivery_log.insert(0, record)
                return {"success": False, "status": self.last_delivery_status, "detail": resp.text}
        except Exception as ex:
            self.last_delivery_status = f"FAILED_EXCEPTION_{type(ex).__name__}"
            self.last_delivery_time = now
            record = {"timestamp": now, "event_type": event_type, "title": title, "status": self.last_delivery_status, "error": str(ex)}
            self.delivery_log.insert(0, record)
            return {"success": False, "status": self.last_delivery_status, "error": str(ex)}

    def send_test_alert(self) -> Dict[str, Any]:
        """Send a test heartbeat notification."""
        if not self.enabled:
            return {
                "success": False,
                "status": "NOT_CONFIGURED",
                "message": "Telegram notifications are NOT configured. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID environment variables."
            }
        return self.send_alert("Heartbeat Test", "Test alert delivery from AEGIS QUANT console.", "TEST_HEARTBEAT")


# Global singleton
telegram_alerts = TelegramAlerts()
