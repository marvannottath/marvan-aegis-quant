"""
Aegis-Quant Anti-Chop Symbol Cooldown & Daily Max Drawdown Circuit Breaker.
Two critical capital shields:
  1. Symbol Cooldown Guard: If a trade hits Stop-Loss on a symbol, blacklists that
     symbol for 3 minutes to stop revenge trading and repetitive whipsaw entries.
  2. Daily Max Drawdown Circuit Breaker: Tracks cumulative rolling daily net loss
     strictly ISOLATED per workspace (CRYPTO, INDIA, FOREX_GOLD).
     A loss in Crypto never affects India equities or vice versa.
"""

import time
from typing import Dict, Any, Tuple
from datetime import datetime, timezone, timedelta

IST_TZ = timezone(timedelta(hours=5, minutes=30))

COOLDOWN_DURATION_SEC = 180.0  # 3 minutes anti-chop cooldown
MAX_DAILY_DRAWDOWN_PCT = 3.50   # 3.5% maximum daily loss ceiling
CIRCUIT_TRIP_DURATION_SEC = 3600.0  # 1 hour halt

# Minimum absolute loss threshold before tripping circuit breaker (avoids micro cents tripping small accounts)
MIN_ABS_LOSS_THRESHOLDS = {
    "CRYPTO": 0.50,       # At least $0.50 USD loss
    "INDIA": 35.0,        # At least ₹35 INR loss
    "FOREX_GOLD": 1.0,    # At least $1.00 USD loss
}


class DrawdownCircuitBreaker:
    def __init__(self):
        # Symbol -> epoch when cooldown expires
        self._symbol_cooldowns: Dict[str, float] = {}
        self._cooldown_reasons: Dict[str, str] = {}

        # Workspace-Isolated Daily Drawdown Trackers
        self._workspaces: Dict[str, Dict[str, Any]] = {}

    def _get_ws_state(self, workspace: str, current_equity: float = 0.0) -> Dict[str, Any]:
        ws = (workspace or "CRYPTO").upper()
        today = datetime.now(timezone.utc).astimezone(IST_TZ).strftime("%Y-%m-%d")
        
        if ws not in self._workspaces or self._workspaces[ws].get("current_day") != today:
            self._workspaces[ws] = {
                "current_day": today,
                "starting_equity": max(1.0, current_equity),
                "daily_realized_loss": 0.0,
                "circuit_breaker_active": False,
                "circuit_tripped_at": 0.0,
            }
        elif current_equity > 0 and self._workspaces[ws]["starting_equity"] <= 1.0:
            self._workspaces[ws]["starting_equity"] = current_equity

        return self._workspaces[ws]

    def record_stop_loss(self, symbol: str, loss_amount_usd: float = 0.0, workspace: str = "CRYPTO"):
        """Put symbol into 3-minute anti-chop cooldown after SL hit."""
        sym_clean = symbol.upper().replace("/", "").strip()
        expire_at = time.time() + COOLDOWN_DURATION_SEC
        self._symbol_cooldowns[sym_clean] = expire_at
        currency_sym = "₹" if (workspace or "").upper() == "INDIA" else "$"
        self._cooldown_reasons[sym_clean] = f"Hit Stop-Loss ({currency_sym}{abs(loss_amount_usd):.2f}). 3m anti-chop cooldown engaged."

    def is_symbol_in_cooldown(self, symbol: str) -> Tuple[bool, str, float]:
        """Check if symbol is currently in cooldown."""
        sym_clean = symbol.upper().replace("/", "").strip()
        expire_at = self._symbol_cooldowns.get(sym_clean, 0.0)
        remaining = expire_at - time.time()
        if remaining > 0:
            return True, f"SYMBOL_COOLDOWN: {sym_clean} in cooldown for {int(remaining)}s ({self._cooldown_reasons.get(sym_clean, '')})", remaining
        return False, "COOLDOWN_CLEAR", 0.0

    def record_trade_pnl(self, pnl_usd: float, current_equity: float, workspace: str = "CRYPTO"):
        """Record PnL to test against workspace-isolated daily drawdown breaker."""
        ws_state = self._get_ws_state(workspace, current_equity)
        if pnl_usd < 0:
            loss_abs = abs(pnl_usd)
            ws_state["daily_realized_loss"] += loss_abs
            min_thresh = MIN_ABS_LOSS_THRESHOLDS.get((workspace or "CRYPTO").upper(), 0.50)
            loss_pct = (ws_state["daily_realized_loss"] / max(1.0, ws_state["starting_equity"])) * 100.0

            if loss_abs >= min_thresh and loss_pct >= MAX_DAILY_DRAWDOWN_PCT and not ws_state["circuit_breaker_active"]:
                ws_state["circuit_breaker_active"] = True
                ws_state["circuit_tripped_at"] = time.time()

    def check_circuit_breaker(self, current_equity: float = 0.0, workspace: str = "CRYPTO") -> Tuple[bool, str]:
        """Validates if workspace-specific daily circuit breaker is tripped."""
        ws = (workspace or "CRYPTO").upper()
        ws_state = self._get_ws_state(ws, current_equity)

        now = time.time()
        if ws_state["circuit_breaker_active"]:
            elapsed = now - ws_state["circuit_tripped_at"]
            if elapsed < CIRCUIT_TRIP_DURATION_SEC:
                rem_min = int((CIRCUIT_TRIP_DURATION_SEC - elapsed) / 60)
                return False, f"DAILY_DRAWDOWN_BREAKER_ACTIVE ({ws}): Daily loss exceeded {MAX_DAILY_DRAWDOWN_PCT}%. Entries halted for {rem_min}m."
            else:
                ws_state["circuit_breaker_active"] = False

        return True, "CIRCUIT_BREAKER_PASS"

    def reset_circuit_breaker(self, workspace: str = "CRYPTO"):
        """Manual or operator reset for a workspace circuit breaker."""
        ws = (workspace or "CRYPTO").upper()
        if ws in self._workspaces:
            self._workspaces[ws]["circuit_breaker_active"] = False
            self._workspaces[ws]["daily_realized_loss"] = 0.0
            self._workspaces[ws]["circuit_tripped_at"] = 0.0

    def get_status(self, workspace: str = "CRYPTO") -> Dict[str, Any]:
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

        ws = (workspace or "CRYPTO").upper()
        ws_state = self._get_ws_state(ws)
        loss_pct = (ws_state["daily_realized_loss"] / max(1.0, ws_state["starting_equity"])) * 100.0 if ws_state["starting_equity"] > 0 else 0.0

        return {
            "workspace": ws,
            "circuit_breaker_active": ws_state["circuit_breaker_active"],
            "max_daily_drawdown_limit_pct": MAX_DAILY_DRAWDOWN_PCT,
            "current_day": ws_state["current_day"],
            "starting_equity": round(ws_state["starting_equity"], 2),
            "daily_realized_loss": round(ws_state["daily_realized_loss"], 2),
            "daily_loss_pct": round(loss_pct, 2),
            "active_symbol_cooldowns": active_cooldowns,
            "timestamp": datetime.now(timezone.utc).astimezone(IST_TZ).strftime("%Y-%m-%d %H:%M:%S IST")
        }


# Global Singleton Instance
drawdown_circuit_breaker = DrawdownCircuitBreaker()
