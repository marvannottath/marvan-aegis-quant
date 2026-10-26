"""
Aegis-Quant Anti-Chop Symbol Cooldown & Daily Max Drawdown Circuit Breaker.
Two critical capital shields:
  1. Symbol Cooldown Guard: If a trade hits Stop-Loss on a symbol, blacklists that
     symbol for 15 minutes to stop revenge trading and repetitive whipsaw entries.
  2. Daily Max Drawdown Circuit Breaker: Tracks cumulative rolling daily net loss.
     If daily loss exceeds 2.5% of starting capital, immediately halts new entries
     for 4 hours to protect capital from catastrophic flash crashes.
"""

import time
from typing import Dict, Any, Tuple
from datetime import datetime, timezone, timedelta

IST_TZ = timezone(timedelta(hours=5, minutes=30))

COOLDOWN_DURATION_SEC = 900.0  # 15 minutes
MAX_DAILY_DRAWDOWN_PCT = 2.50   # 2.5% maximum daily loss ceiling
CIRCUIT_TRIP_DURATION_SEC = 14400.0  # 4 hours halt

class DrawdownCircuitBreaker:
    def __init__(self):
        # Symbol -> epoch when cooldown expires
        self._symbol_cooldowns: Dict[str, float] = {}
        self._cooldown_reasons: Dict[str, str] = {}

        # Daily Drawdown Tracker
        self._current_day_str: str = ""
        self._starting_equity: float = 0.0
        self._daily_realized_loss: float = 0.0
        self._circuit_breaker_active: bool = False
        self._circuit_tripped_at: float = 0.0

    def _sync_day(self, current_equity: float):
        today = datetime.now(timezone.utc).astimezone(IST_TZ).strftime("%Y-%m-%d")
        if self._current_day_str != today:
            self._current_day_str = today
            self._starting_equity = max(1.0, current_equity)
            self._daily_realized_loss = 0.0
            self._circuit_breaker_active = False
            self._circuit_tripped_at = 0.0

    def record_stop_loss(self, symbol: str, loss_amount_usd: float = 0.0):
        """Put symbol into 15-minute anti-chop cooldown after SL hit."""
        sym_clean = symbol.upper().replace("/", "").strip()
        expire_at = time.time() + COOLDOWN_DURATION_SEC
        self._symbol_cooldowns[sym_clean] = expire_at
        self._cooldown_reasons[sym_clean] = f"Hit Stop-Loss (${abs(loss_amount_usd):.2f}). 15m anti-chop cooldown engaged."

    def is_symbol_in_cooldown(self, symbol: str) -> Tuple[bool, str, float]:
        """Check if symbol is currently in cooldown."""
        sym_clean = symbol.upper().replace("/", "").strip()
        expire_at = self._symbol_cooldowns.get(sym_clean, 0.0)
        remaining = expire_at - time.time()
        if remaining > 0:
            return True, f"SYMBOL_COOLDOWN: {sym_clean} in cooldown for {int(remaining)}s ({self._cooldown_reasons.get(sym_clean, '')})", remaining
        return False, "COOLDOWN_CLEAR", 0.0

    def record_trade_pnl(self, pnl_usd: float, current_equity: float):
        """Record PnL to test against daily drawdown breaker."""
        self._sync_day(current_equity)
        if pnl_usd < 0:
            self._daily_realized_loss += abs(pnl_usd)
            loss_pct = (self._daily_realized_loss / max(1.0, self._starting_equity)) * 100.0
            if loss_pct >= MAX_DAILY_DRAWDOWN_PCT and not self._circuit_breaker_active:
                self._circuit_breaker_active = True
                self._circuit_tripped_at = time.time()

    def check_circuit_breaker(self, current_equity: float = 0.0) -> Tuple[bool, str]:
        """Validates if daily circuit breaker is tripped."""
        if current_equity > 0:
            self._sync_day(current_equity)

        now = time.time()
        if self._circuit_breaker_active:
            elapsed = now - self._circuit_tripped_at
            if elapsed < CIRCUIT_TRIP_DURATION_SEC:
                rem_min = int((CIRCUIT_TRIP_DURATION_SEC - elapsed) / 60)
                return False, f"DAILY_DRAWDOWN_BREAKER_ACTIVE: Daily loss exceeded {MAX_DAILY_DRAWDOWN_PCT}%. Entries halted for {rem_min}m."
            else:
                # Reset after duration
                self._circuit_breaker_active = False

        return True, "CIRCUIT_BREAKER_PASS"

    def get_status(self) -> Dict[str, Any]:
        """Full telemetry status snapshot."""
        now = time.time()
        active_cooldowns = {}
        for sym, exp in list(self._symbol_cooldowns.items()):
            rem = exp - now
            if rem > 0:
                active_cooldowns[sym] = {
                    "remaining_seconds": round(rem, 1),
                    "reason": self._cooldown_reasons.get(sym, "")
                }

        loss_pct = (self._daily_realized_loss / max(1.0, self._starting_equity)) * 100.0 if self._starting_equity > 0 else 0.0

        return {
            "circuit_breaker_active": self._circuit_breaker_active,
            "max_daily_drawdown_limit_pct": MAX_DAILY_DRAWDOWN_PCT,
            "current_day": self._current_day_str,
            "starting_equity": round(self._starting_equity, 2),
            "daily_realized_loss": round(self._daily_realized_loss, 2),
            "daily_loss_pct": round(loss_pct, 2),
            "active_symbol_cooldowns": active_cooldowns,
            "timestamp": datetime.now(timezone.utc).astimezone(IST_TZ).strftime("%Y-%m-%d %H:%M:%S IST")
        }


# Global Singleton Instance
drawdown_circuit_breaker = DrawdownCircuitBreaker()
