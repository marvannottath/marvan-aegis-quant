"""
Mobile Push Notification & Alert Engine for Marvan's Pool.
Full Multi-Channel Telegram Push Dispatcher:
1. Real-time Profit Harvest Sweeps (0 USD minimum cap).
2. New AI Autonomous Trade Executions.
3. Vault Withdrawals & Capital Deposits.
4. Risk Engine Circuit Breaker & Macro News Alerts.
"""

import json
import time
import requests
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime, timezone, timedelta

IST_TZ = timezone(timedelta(hours=5, minutes=30))
CONFIG_FILE = Path(__file__).resolve().parent.parent / "data" / "notification_config.json"

class NotificationEngine:
    def __init__(self):
        self.config: Dict[str, Any] = {
            "telegram_enabled": True,
            "telegram_bot_token": "",
            "telegram_chat_id": "",
            "alert_on_profit_sweep": True,
            "min_sweep_usd_for_alert": 0.0,
            "alert_on_trade_open": True,
            "alert_on_security_event": True,
            "alert_on_macro_news": True,
            "discord_webhook_url": ""
        }
        self.recent_alerts: List[Dict[str, Any]] = []
        self.last_sweep_alert_time: float = 0.0
        self._load_config()

    def _load_config(self):
        """Load notification preferences from disk."""
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r") as f:
                    saved = json.load(f)
                    self.config.update(saved)
            except Exception as e:
                print(f"[NOTIFICATION] Load config notice: {e}")
        else:
            self._save_config()

    def _save_config(self):
        """Save notification preferences to disk."""
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            print(f"[NOTIFICATION] Save config notice: {e}")

    def update_config(self, new_config: Dict[str, Any]) -> Dict[str, Any]:
        """Update notification settings."""
        self.config.update(new_config)
        self._save_config()
        return self.config

    def send_telegram_message(self, text: str, custom_token: str = None, custom_chat_id: str = None):
        """Send message via Telegram Bot API with robust requests library."""
        bot_token = (custom_token or self.config.get("telegram_bot_token", "")).strip()
        chat_id = (custom_chat_id or self.config.get("telegram_chat_id", "")).strip()

        if not bot_token:
            return False, "⚠️ Telegram Bot Token is missing. Please paste your Bot Token from @BotFather."
        if not chat_id:
            return False, "⚠️ Personal Chat ID is missing. Please enter your Chat ID."

        if bot_token.lower() in ["dummy", "dummy_token", "dummy_test_token", "test", "demo"]:
            self.recent_alerts.insert(0, {
                "timestamp": datetime.now(timezone.utc).astimezone(IST_TZ).strftime("%Y-%m-%d %H:%M:%S"),
                "channel": "Telegram Simulator (Demo)",
                "message": text,
                "status": "SIMULATED_TEST 🟢"
            })
            return True, "⚡ [Demo Mode Active] Simulated ping successful! To receive real push alerts on your phone, paste your real Bot Token from @BotFather."

        try:
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "Markdown"
            }
            resp = requests.post(url, json=payload, timeout=8)
            try:
                res_json = resp.json()
            except Exception:
                res_json = {}

            if resp.status_code == 200 and res_json.get("ok"):
                self.recent_alerts.insert(0, {
                    "timestamp": datetime.now(timezone.utc).astimezone(IST_TZ).strftime("%Y-%m-%d %H:%M:%S"),
                    "channel": "Telegram Bot Push",
                    "message": text,
                    "status": "DELIVERED 🟢"
                })
                if len(self.recent_alerts) > 50:
                    self.recent_alerts.pop()
                return True, "⚡ Real Telegram alert delivered to your phone! 📱"
            else:
                desc = res_json.get("description", f"Telegram API returned HTTP {resp.status_code}")
                if "chat not found" in desc.lower() or "bot was blocked" in desc.lower() or "bot can't initiate conversation" in desc.lower():
                    return False, f"⚠️ Telegram: '{desc}'. 👉 Please open your Bot in Telegram and click 'START' first!"
                if "not found" in desc.lower() or "unauthorized" in desc.lower() or resp.status_code in [401, 404]:
                    return False, f"⚠️ Invalid Telegram Bot Token ({desc}). Please copy the exact token given by @BotFather on Telegram!"
                return False, f"⚠️ Telegram API: {desc}"
        except Exception as e:
            print(f"[NOTIFICATION] Telegram dispatch error: {e}")
            return False, f"Network/Connection error: {str(e)}"

    def notify_profit_sweep(self, asset: str, profit_usd: float, vault_total: float, reason: str):
        """Triggered automatically when trading profits are swept into the vault."""
        if not self.config.get("alert_on_profit_sweep", True):
            return

        min_amt = float(self.config.get("min_sweep_usd_for_alert", 0.0))
        if profit_usd < min_amt:
            return

        # Throttle to max 1 sweep alert every 6 seconds to respect Telegram rate limits
        now = time.time()
        if now - self.last_sweep_alert_time < 6.0:
            return
        self.last_sweep_alert_time = now

        ist_now = datetime.now(timezone.utc).astimezone(IST_TZ)
        ist_time_str = ist_now.strftime("%d %b %Y, %I:%M:%S %p")

        msg = (
            f"🎉 *MARVAN'S POOL - PROFIT HARVEST ALERT* 💎

"
            f"💰 *Profit Swept:* `+${profit_usd:,.2f} USD`
"
            f"📊 *Asset Ticker:* `{asset}`
"
            f"🛡️ *Total Vault Reserve:* `${vault_total:,.2f} USD`
"
            f"📌 *Exit Reason:* `{reason}`
"
            f"⏰ *Time (IST):* `{ist_time_str}`

"
            f"🔒 _100% Realized & Safe in Untouchable Reserve Vault._"
        )
        self.send_telegram_message(msg)

    def notify_trade_opened(self, asset: str, action: str, size_usd: float, leverage: float, price: float, opp_score: float = 80.0):
        """Triggered when a new autonomous trade position is entered."""
        if not self.config.get("alert_on_trade_open", True):
            return

        ist_now = datetime.now(timezone.utc).astimezone(IST_TZ)
        ist_time_str = ist_now.strftime("%d %b %Y, %I:%M:%S %p")
        act_icon = "🟢 BUY / LONG" if action.upper() == "BUY" else "🔴 SELL / SHORT"

        msg = (
            f"🚀 *MARVAN'S POOL - NEW AI TRADE OPENED* ⚡

"
            f"📊 *Asset:* `{asset}`
"
            f"🎯 *Action:* `{act_icon}`
"
            f"💵 *Margin Allocated:* `${size_usd:,.2f} USD`
"
            f"⚡ *Leverage:* `{leverage:.0f}x`
"
            f"📈 *Entry Price:* `${price:,.4f}`
"
            f"🧠 *AI Opportunity:* `{opp_score:.0f}% Confluence`
"
            f"⏰ *Time (IST):* `{ist_time_str}`

"
            f"🛡️ _Protected with Hard Risk Circuit & Isolated Margin._"
        )
        self.send_telegram_message(msg)

    def notify_withdrawal(self, amount_usd: float, method: str, destination: str):
        """Triggered when a vault withdrawal is dispatched."""
        ist_now = datetime.now(timezone.utc).astimezone(IST_TZ)
        msg = (
            f"💸 *MARVAN'S POOL - VAULT WITHDRAWAL DISPATCHED* 🏦

"
            f"💵 *Amount:* `${amount_usd:,.2f} USD`
"
            f"💳 *Method:* `{method}`
"
            f"📍 *Destination:* `{destination}`
"
            f"⏰ *Time (IST):* `{ist_now.strftime('%d %b %Y, %I:%M:%S %p')}`

"
            f"⚡ _Processed instantly via institutional multi-hop escrow._"
        )
        self.send_telegram_message(msg)

    def notify_security_event(self, event_title: str, details: str, severity: str = "HIGH"):
        """Triggered when SIEM or Super Admin auth events occur."""
        if not self.config.get("alert_on_security_event", True):
            return

        icon = "🚨" if severity == "HIGH" else "🛡️"
        msg = (
            f"{icon} *MARVAN'S POOL - SECURITY ALERT* [{severity}]

"
            f"🔐 *Event:* `{event_title}`
"
            f"📝 *Details:* `{details}`
"
            f"⏰ *Time (IST):* `{datetime.now(timezone.utc).astimezone(IST_TZ).strftime('%I:%M:%S %p')}`
"
            f"🛡️ _Zero-Trust SIEM Sentinel Active._"
        )
        self.send_telegram_message(msg)

    def notify_macro_lockout(self, event_name: str, impact: str = "HIGH IMPACT"):
        """Triggered when US Fed or macroeconomic news locks the pool."""
        if not self.config.get("alert_on_macro_news", True):
            return

        msg = (
            f"⚠️ *MACRO CIRCUIT PROTECTION ENGAGED*

"
            f"🏛️ *Event:* `{event_name}` ({impact})
"
            f"🔒 *Action:* Order placement temporarily locked (±30m)
"
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
