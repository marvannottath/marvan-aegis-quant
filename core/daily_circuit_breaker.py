"""
AEGIS-QUANT Daily Circuit Breaker & Drawdown Shield.
Locks trading session if:
  1. Consecutive losses reach limit (default: 2 trades)
  2. Daily net drawdown exceeds threshold (default: 3.0% of starting equity)
Resets automatically at 08:00 AM IST for each fresh trading day.
"""

import json
from pathlib import Path
from typing import Dict, Any, Tuple
from datetime import datetime, timezone, timedelta

IST_TZ = timezone(timedelta(hours=5, minutes=30))
CIRCUIT_DB = Path(__file__).resolve().parent.parent / "data" / "circuit_breaker_state.json"


class DailyCircuitBreaker:
    MAX_CONSECUTIVE_LOSSES = 2
    MAX_DAILY_DRAWDOWN_PCT = 3.0  # 3% of capital

    def __init__(self):
        self.session_date: str = ""
        self.daily_pnl: float = 0.0
        self.consecutive_losses: int = 0
        self.is_circuit_open: bool = False  # True means TRADING LOCKED
        self.lock_reason: str = ""
        self._load_state()

    def _load_state(self):
        CIRCUIT_DB.parent.mkdir(parents=True, exist_ok=True)
        today = datetime.now(timezone.utc).astimezone(IST_TZ).strftime("%Y-%m-%d")
        if CIRCUIT_DB.exists():
            try:
                with open(CIRCUIT_DB, "r") as f:
                    data = json.load(f)
                    if data.get("session_date") == today:
                        self.session_date = today
                        self.daily_pnl = float(data.get("daily_pnl", 0.0))
                        self.consecutive_losses = int(data.get("consecutive_losses", 0))
                        self.is_circuit_open = bool(data.get("is_circuit_open", False))
                        self.lock_reason = data.get("lock_reason", "")
                        return
            except Exception as e:
                print(f"[CIRCUIT_BREAKER] Load notice: {e}")

        # Fresh day initialization
        self.session_date = today
        self.daily_pnl = 0.0
        self.consecutive_losses = 0
        self.is_circuit_open = False
        self.lock_reason = ""
        self._save_state()

    def _save_state(self):
        try:
            tmp = CIRCUIT_DB.with_suffix(".tmp")
            with open(tmp, "w") as f:
                json.dump({
                    "session_date": self.session_date,
                    "daily_pnl": round(self.daily_pnl, 2),
                    "consecutive_losses": self.consecutive_losses,
                    "is_circuit_open": self.is_circuit_open,
                    "lock_reason": self.lock_reason,
                    "updated_at": datetime.now(timezone.utc).astimezone(IST_TZ).strftime("%Y-%m-%d %H:%M:%S IST"),
                }, f, indent=2)
            tmp.replace(CIRCUIT_DB)
        except Exception as e:
            print(f"[CIRCUIT_BREAKER] Save notice: {e}")

    def check_trading_allowed(self) -> Tuple[bool, str]:
        """Verify if orders are allowed or locked by circuit breaker."""
        today = datetime.now(timezone.utc).astimezone(IST_TZ).strftime("%Y-%m-%d")
        if self.session_date != today:
            self._load_state()

        if self.is_circuit_open:
            return False, f"CIRCUIT_LOCKED: {self.lock_reason}"
        return True, "CIRCUIT_OK: Trading allowed"

    def record_trade_result(self, pnl: float, capital_base: float = 1000.0) -> Dict[str, Any]:
        """Record trade outcome and update circuit breaker thresholds."""
        today = datetime.now(timezone.utc).astimezone(IST_TZ).strftime("%Y-%m-%d")
        if self.session_date != today:
            self._load_state()

        self.daily_pnl += pnl

        if pnl < 0:
            self.consecutive_losses += 1
        else:
            self.consecutive_losses = 0

        # Check thresholds
        drawdown_pct = abs(min(0.0, self.daily_pnl)) / max(100.0, capital_base) * 100.0

        if self.consecutive_losses >= self.MAX_CONSECUTIVE_LOSSES:
            self.is_circuit_open = True
            self.lock_reason = f"Max consecutive losses reached ({self.consecutive_losses}/{self.MAX_CONSECUTIVE_LOSSES}). Capital preservation lock engaged."

        elif drawdown_pct >= self.MAX_DAILY_DRAWDOWN_PCT:
            self.is_circuit_open = True
            self.lock_reason = f"Max daily drawdown limit reached (-{drawdown_pct:.1f}% >= -{self.MAX_DAILY_DRAWDOWN_PCT}%). Session halted."

        self._save_state()

        if self.is_circuit_open:
            try:
                from core.telegram_alerts import telegram_alerts
                tg_msg = (
                    f"🛑 *DAILY CIRCUIT BREAKER TRIGGERED*\n"
                    f"━━━━━━━━━━━━━━━━━━━\n"
                    f"• *Status:* TRADING LOCKED UNTIL TOMORROW\n"
                    f"• *Reason:* {self.lock_reason}\n"
                    f"• *Today's Net P&L:* ₹{self.daily_pnl:+,.2f}\n"
                    f"• *Action Taken:* All new entries frozen to protect capital!"
                )
                telegram_alerts.send_alert("Circuit Breaker Locked", tg_msg, event_type="CIRCUIT_BREAKER")
            except Exception:
                pass

        return {
            "is_circuit_open": self.is_circuit_open,
            "lock_reason": self.lock_reason,
            "daily_pnl": self.daily_pnl,
            "consecutive_losses": self.consecutive_losses,
        }

    def reset_circuit_breaker(self) -> Dict[str, Any]:
        """Manual admin override to reset circuit breaker."""
        self.is_circuit_open = False
        self.lock_reason = ""
        self.consecutive_losses = 0
        self._save_state()
        return {"status": "SUCCESS", "message": "Circuit breaker reset. Trading unlocked."}


# Global Singleton
daily_circuit_breaker = DailyCircuitBreaker()
