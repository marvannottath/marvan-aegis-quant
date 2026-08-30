"""
Mobile Push Notification & Alert Engine for Marvan's Pool.
Supports:
1. Real-time Telegram Bot API push alerts to Marvan's personal phone.
2. Webhook / Discord alerts.
3. Automated triggers on Realized Profit Sweeps, High-Impact News, and Security SIEM events.
"""

import json
import time
import urllib.request
import urllib.parse
from pathlib import Path
from typing import Dict, Any, List

CONFIG_FILE = Path(__file__).resolve().parent.parent / "data" / "notification_config.json"

class NotificationEngine:
    def __init__(self):
        self.config: Dict[str, Any] = {
            "telegram_enabled": True,
            "telegram_bot_token": "",
            "telegram_chat_id": "",
            "alert_on_profit_sweep": True,
            "min_sweep_usd_for_alert": 25.0,
            "alert_on_security_event": True,
            "alert_on_macro_news": True,
            "discord_webhook_url": ""
        }
        self.recent_alerts: List[Dict[str, Any]] = []
        self._load_config()

    def _load_config(self):
        """Load notification preferences from disk."""
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r") as f:
                    saved = json.load(f)
                    self.config.update(saved)
            except Exception as e:
                print(f"[NOTIFICATION] Load config error: {e}")
        else:
            self._save_config()

    def _save_config(self):
        """Save notification preferences to disk."""
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            print(f"[NOTIFICATION] Save config error: {e}")

    def update_config(self, new_config: Dict[str, Any]) -> Dict[str, Any]:
        """Update notification settings."""
        self.config.update(new_config)
        self._save_config()
        return self.config

    def send_telegram_message(self, text: str) -> bool:
        """Send message via Telegram Bot API."""
        bot_token = self.config.get("telegram_bot_token", "").strip()
        chat_id = self.config.get("telegram_chat_id", "").strip()

        # Record into recent alerts feed
        alert_item = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "channel": "Telegram Bot Push",
            "message": text,
            "status": "DISPATCHED" if (bot_token and chat_id) else "SIMULATED_LOCAL"
        }
        self.recent_alerts.insert(0, alert_item)
        if len(self.recent_alerts) > 50:
            self.recent_alerts.pop()

        if not bot_token or not chat_id:
            # If no live token configured yet, logged in memory stream
            return True

        try:
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "Markdown"
            }
            data = urllib.parse.urlencode(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data, method="POST")
            with urllib.request.urlopen(req, timeout=5) as response:
                return response.status == 200
        except Exception as e:
            print(f"[NOTIFICATION] Telegram dispatch error: {e}")
            return False

    def notify_profit_sweep(self, asset: str, profit_usd: float, vault_total: float, reason: str):
        """Triggered automatically when trading profits are swept into the vault."""
        if not self.config.get("alert_on_profit_sweep", True):
            return

        min_amt = self.config.get("min_sweep_usd_for_alert", 25.0)
        if profit_usd < min_amt:
            return

        msg = (
            f"🎉 *MARVAN'S POOL - PROFIT HARVEST ALERT* 💎\n\n"
            f"💰 *Profit Swept:* `+${profit_usd:,.2f} USD`\n"
            f"📊 *Asset Ticker:* `{asset}`\n"
            f"🛡️ *Total Vault Reserve:* `${vault_total:,.2f} USD`\n"
            f"📌 *Exit Reason:* `{reason}`\n"
            f"⏰ *Time (IST):* `{time.strftime('%I:%M:%S %p')}`\n\n"
            f"🔒 _100% Realized & Safe in Untouchable Reserve Vault._"
        )
        self.send_telegram_message(msg)

    def notify_security_event(self, event_title: str, details: str, severity: str = "HIGH"):
        """Triggered when SIEM or Super Admin auth events occur."""
        if not self.config.get("alert_on_security_event", True):
            return

        icon = "🚨" if severity == "HIGH" else "🛡️"
        msg = (
            f"{icon} *MARVAN'S POOL - SECURITY ALERT* [{severity}]\n\n"
            f"🔐 *Event:* `{event_title}`\n"
            f"📝 *Details:* `{details}`\n"
            f"⏰ *Time (IST):* `{time.strftime('%I:%M:%S %p')}`\n"
            f"🛡️ _Zero-Trust SIEM Sentinel Active._"
        )
        self.send_telegram_message(msg)

    def notify_macro_lockout(self, event_name: str, impact: str = "HIGH IMPACT"):
        """Triggered when US Fed or macroeconomic news locks the pool."""
        if not self.config.get("alert_on_macro_news", True):
            return

        msg = (
            f"⚠️ *MACRO CIRCUIT PROTECTION ENGAGED*\n\n"
            f"🏛️ *Event:* `{event_name}` ({impact})\n"
            f"🔒 *Action:* Order placement temporarily locked (±30m)\n"
            f"🛡️ *Capital Shield:* 100% drawdown protected against Fed volatility."
        )
        self.send_telegram_message(msg)

    def get_notification_status(self) -> Dict[str, Any]:
        """Return notification engine status and recent alerts."""
        return {
            "config": self.config,
            "recent_alerts": self.recent_alerts,
            "is_configured": bool(self.config.get("telegram_bot_token") and self.config.get("telegram_chat_id"))
        }

# Global Notification Engine
notification_engine = NotificationEngine()
