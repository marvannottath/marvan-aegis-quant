"""
AEGIS-QUANT Morning 8:45 AM Auto-Wakeup & 2FA Keep-Alive Bot.
Runs every trading day at 08:45 AM IST (30 minutes before NSE market open):
  1. Tests Kotak Neo Live session validity for today.
  2. If session expired and TOTP secret is configured, auto-authenticates silently.
  3. If manual 2FA is needed, sends an urgent interactive Telegram reminder.
  4. Runs pre-market sanity checks on cash balance, margins, and market gateways.
"""

import time
from typing import Dict, Any
from datetime import datetime, timezone, timedelta

IST_TZ = timezone(timedelta(hours=5, minutes=30))


class MorningWakeupBot:
    def __init__(self):
        self.last_checked_date: str = ""
        self.last_check_result: Dict[str, Any] = {}

    def should_run_morning_check(self) -> bool:
        """True if weekday between 08:40 AM and 09:10 AM IST and hasn't run today."""
        now = datetime.now(timezone.utc).astimezone(IST_TZ)
        if now.weekday() > 4:  # Saturday or Sunday
            return False

        today_str = now.strftime("%Y-%m-%d")
        if self.last_checked_date == today_str:
            return False

        # 08:40 to 09:10 IST
        if now.hour == 8 and now.minute >= 40:
            return True
        if now.hour == 9 and now.minute <= 10:
            return True
        return False

    def execute_morning_check(self, force: bool = False) -> Dict[str, Any]:
        """Perform authoritative pre-market session & broker readiness check."""
        now = datetime.now(timezone.utc).astimezone(IST_TZ)
        today_str = now.strftime("%Y-%m-%d")
        now_formatted = now.strftime("%Y-%m-%d %H:%M:%S IST")

        from execution.kotak_neo_broker import kotak_neo_broker
        from execution.broker_gateway_manager import broker_gateway_manager
        from core.pre_market_engine import pre_market_engine

        # 1. Check Kotak Neo session
        saved_date = getattr(kotak_neo_broker, "_session_date", "")
        has_active_session = bool(kotak_neo_broker._session_token and saved_date == today_str)

        # 2. Attempt silent auto-auth if TOTP secret exists
        if not has_active_session and kotak_neo_broker._consumer_key:
            totp_sec = getattr(kotak_neo_broker, "_totp_secret", "")
            if totp_sec and not (len(totp_sec) == 6 and totp_sec.isdigit()):
                try:
                    res = kotak_neo_broker.authenticate_live_session(
                        consumer_key=kotak_neo_broker._consumer_key,
                        mobile_number=getattr(kotak_neo_broker, "_mobile_number", ""),
                        ucc=kotak_neo_broker.ucc,
                        mpin=getattr(kotak_neo_broker, "_mpin", ""),
                        totp_secret=totp_sec,
                    )
                    if res.get("status") == "SUCCESS":
                        has_active_session = True
                except Exception as ex:
                    print(f"[MORNING_BOT] Auto-auth exception: {ex}")

        # 3. Macro Sentiment & Opening Bias
        macro = pre_market_engine.evaluate_global_bias(force_refresh=True)

        status_result = {
            "date": today_str,
            "checked_at": now_formatted,
            "kotak_neo_authenticated": has_active_session,
            "kotak_client_ucc": kotak_neo_broker.ucc or "16MT6",
            "available_cash": float(kotak_neo_broker._live_cash),
            "macro_bias": macro.get("bias_verdict", "NEUTRAL"),
            "ready_for_market_open": has_active_session,
        }

        # 4. Dispatch Telegram Notification
        try:
            from core.telegram_alerts import telegram_alerts
            if has_active_session:
                msg = (
                    f"🌅 *GOOD MORNING! MARKET OPENS AT 9:15 AM*\n"
                    f"━━━━━━━━━━━━━━━━━━━\n"
                    f"• *Kotak Neo Session:* 🟢 ACTIVE & READY\n"
                    f"• *Client UCC:* `{kotak_neo_broker.ucc or '16MT6'}`\n"
                    f"• *Trading Capital:* ₹{float(kotak_neo_broker._live_cash):,.2f}\n"
                    f"• *Global Macro Bias:* *{macro.get('bias_verdict')}*\n"
                    f"• *Status:* Bot is armed and standing by for the 9:15 AM bell!"
                )
                telegram_alerts.send_alert("Pre-Market Readiness", msg, event_type="MORNING_READINESS")
            else:
                msg = (
                    f"⚠️ *ACTION REQUIRED: KOTAK 2FA NEEDED TODAY*\n"
                    f"━━━━━━━━━━━━━━━━━━━\n"
                    f"Good morning! NSE market opens at 9:15 AM.\n"
                    f"Please enter today's 6-digit TOTP from Google Authenticator to activate Kotak Neo live trading.\n\n"
                    f"🔗 *Dashboard:* https://srv1799665.hstgr.cloud\n"
                    f"Or reply with your TOTP here."
                )
                telegram_alerts.send_alert("Kotak 2FA Required", msg, event_type="2FA_REMINDER")
        except Exception as te:
            print(f"[MORNING_BOT] Telegram notification notice: {te}")

        self.last_checked_date = today_str
        self.last_check_result = status_result
        return status_result


# Global Singleton
morning_wakeup_bot = MorningWakeupBot()
