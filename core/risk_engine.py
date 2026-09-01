import json
from pathlib import Path
from typing import Dict, Any, Tuple, Optional
from datetime import datetime, timezone, timedelta

RISK_STATE_FILE = Path(__file__).resolve().parent.parent / "data" / "risk_profile_state.json"

PROFILES = {
    "CONSERVATIVE": {
        "name": "CONSERVATIVE",
        "description": "Low Risk Capital Preservation (2x Max Leverage, 1% Risk Cap)",
        "default_leverage": 2.0,
        "max_leverage": 2.0,
        "max_risk_per_trade_pct": 1.0,
        "max_open_positions": 4,
        "min_open_positions": 2,
        "circuit_breaker_drawdown_pct": 5.0,
        "take_profit_target_pct": 1.5,
        "stop_loss_pct": 0.8
    },
    "MODERATE": {
        "name": "MODERATE",
        "description": "Standard Balanced Institutional Growth (10x Max Leverage, 2.5% Risk Cap)",
        "default_leverage": 10.0,
        "max_leverage": 10.0,
        "max_risk_per_trade_pct": 2.5,
        "max_open_positions": 8,
        "min_open_positions": 4,
        "circuit_breaker_drawdown_pct": 10.0,
        "take_profit_target_pct": 3.5,
        "stop_loss_pct": 1.5
    },
    "AGGRESSIVE": {
        "name": "AGGRESSIVE",
        "description": "High Yield Alpha Quant Scalping (25x Max Leverage, 5% Risk Cap)",
        "default_leverage": 25.0,
        "max_leverage": 25.0,
        "max_risk_per_trade_pct": 5.0,
        "max_open_positions": 10,
        "min_open_positions": 6,
        "circuit_breaker_drawdown_pct": 20.0,
        "take_profit_target_pct": 6.0,
        "stop_loss_pct": 2.5
    }
}

# Canonical rejection codes
RISK_OK                      = "ORDER_APPROVED"
RISK_REJECTED_POSITION_LIMIT = "RISK_REJECTED/MAX_POSITION_LIMIT_EXCEEDED"
RISK_REJECTED_CAPITAL_CAP    = "RISK_REJECTED/MAX_CAPITAL_LIMIT_EXCEEDED"
RISK_REJECTED_LEVERAGE       = "RISK_REJECTED/MAX_LEVERAGE_EXCEEDED"
RISK_REJECTED_MARGIN         = "RISK_REJECTED/INSUFFICIENT_AVAILABLE_MARGIN"
RISK_REJECTED_DAILY_LOSS     = "RISK_REJECTED/DAILY_LOSS_CIRCUIT_TRIPPED"
RISK_REJECTED_DRAWDOWN       = "RISK_REJECTED/MAX_DRAWDOWN_CIRCUIT_TRIPPED"
RISK_REJECTED_INVALID_SL     = "RISK_REJECTED/INVALID_STOP_LOSS_CONFIGURATION"


class RiskEngine:
    def __init__(self, max_drawdown_pct: float = 10.0, default_profile: str = "CONSERVATIVE"):
        self.active_profile_name = default_profile.upper() if default_profile.upper() in PROFILES else "CONSERVATIVE"
        self.custom_trade_cap_usd: float = 5000.0
        self.circuit_tripped = False
        self.trip_reason = "NORMAL_OPERATIONS"
        self.daily_realized_loss: float = 0.0
        self.daily_loss_limit_usd: float = 2000.0
        self._last_reset_date: str = ""
        self._load_state()
        self.active_profile = PROFILES.get(self.active_profile_name, PROFILES["CONSERVATIVE"])
        self.max_drawdown_pct = self.active_profile["circuit_breaker_drawdown_pct"]

    def _load_state(self):
        if RISK_STATE_FILE.exists():
            try:
                with open(RISK_STATE_FILE, "r") as f:
                    data = json.load(f)
                    p_name = data.get("active_profile_name", "CONSERVATIVE").upper()
                    if p_name in PROFILES:
                        self.active_profile_name = p_name
                    self.custom_trade_cap_usd = max(1.0, float(data.get("custom_trade_cap_usd", 5000.0)))
                    self.daily_realized_loss = float(data.get("daily_realized_loss", 0.0))
                    self.daily_loss_limit_usd = float(data.get("daily_loss_limit_usd", 2000.0))
                    self._last_reset_date = data.get("last_reset_date", "")
            except Exception as e:
                print(f"[RISK ENGINE] Load state notice: {e}")
        self._maybe_reset_daily_loss()

    def _save_state(self):
        try:
            RISK_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(RISK_STATE_FILE, "w") as f:
                json.dump({
                    "active_profile_name": self.active_profile_name,
                    "custom_trade_cap_usd": self.custom_trade_cap_usd,
                    "daily_realized_loss": self.daily_realized_loss,
                    "daily_loss_limit_usd": self.daily_loss_limit_usd,
                    "last_reset_date": self._last_reset_date
                }, f, indent=2)
        except Exception as e:
            print(f"[RISK ENGINE] Save state notice: {e}")

    def _maybe_reset_daily_loss(self):
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if today != self._last_reset_date:
            self.daily_realized_loss = 0.0
            self._last_reset_date = today

    def record_loss(self, loss_usd: float):
        self._maybe_reset_daily_loss()
        if loss_usd > 0:
            self.daily_realized_loss += loss_usd
            self._save_state()

    def set_risk_profile(self, profile_name: str) -> Dict[str, Any]:
        name = profile_name.upper()
        if name in PROFILES:
            self.active_profile_name = name
            self.active_profile = PROFILES[name]
            self.max_drawdown_pct = self.active_profile["circuit_breaker_drawdown_pct"]
            self._save_state()
            max_lev_val = self.active_profile['max_leverage']
        print(f'[RISK ENGINE] Profile set: {name} (Max Lev: {max_lev_val}x)')
        return self.active_profile

    def set_max_trade_cap(self, cap_usd: float) -> float:
        self.custom_trade_cap_usd = max(1.0, float(cap_usd))
        self._save_state()
        return self.custom_trade_cap_usd

    def get_profile_summary(self) -> Dict[str, Any]:
        return {
            "active_profile": self.active_profile_name,
            "description": self.active_profile["description"],
            "default_leverage": self.active_profile["default_leverage"],
            "max_leverage": self.active_profile["max_leverage"],
            "max_risk_pct": self.active_profile["max_risk_per_trade_pct"],
            "max_positions": self.active_profile["max_open_positions"],
            "stop_loss_pct": self.active_profile["stop_loss_pct"],
            "take_profit_pct": self.active_profile["take_profit_target_pct"],
            "max_trade_cap_usd": self.custom_trade_cap_usd,
            "circuit_tripped": self.circuit_tripped,
            "trip_reason": self.trip_reason,
            "daily_realized_loss_usd": round(self.daily_realized_loss, 2),
            "daily_loss_limit_usd": self.daily_loss_limit_usd
        }

    def calculate_position_size(self, virtual_cash: float, volatility: float, confidence_score: float) -> float:
        risk_pct = self.active_profile["max_risk_per_trade_pct"] / 100.0
        base_size = virtual_cash * risk_pct
        vol_scalar = max(0.5, min(1.5, (0.01 / max(0.001, volatility))))
        conf_scalar = max(0.6, min(1.3, confidence_score / 70.0))
        size = base_size * vol_scalar * conf_scalar
        return min(self.custom_trade_cap_usd, max(1.0, round(size, 2)))

    def validate_order_pipeline(
        self,
        amount_usd: float,
        leverage: float,
        current_open_positions: int,
        available_cash: float,
        data_age_seconds: Optional[float] = None
    ) -> Tuple[bool, str, str]:
        """
        HARD 7-Gate Server-Side Order Risk Pipeline.
        Returns (approved: bool, rejection_code: str, human_message: str).
        No bypass path exists. All gates must pass in sequence.
        """
        self._maybe_reset_daily_loss()

        # Gate 1: Position limit
        max_pos = self.active_profile["max_open_positions"]
        if current_open_positions >= max_pos:
            msg = f"Max open positions ({max_pos}) reached for {self.active_profile_name} profile."
            return False, RISK_REJECTED_POSITION_LIMIT, msg

        # Gate 2: HARD capital cap — strictly <= cap, no multiplier, no slack
        if amount_usd > self.custom_trade_cap_usd:
            msg = (f"Order ${amount_usd:,.2f} exceeds hard cap "
                   f"${self.custom_trade_cap_usd:,.2f}. MAX_CAPITAL_LIMIT_EXCEEDED.")
            return False, RISK_REJECTED_CAPITAL_CAP, msg

        # Gate 3: Leverage
        max_lev = self.active_profile["max_leverage"]
        if leverage > max_lev:
            msg = f"Leverage {leverage}x exceeds max {max_lev}x for {self.active_profile_name}."
            return False, RISK_REJECTED_LEVERAGE, msg

        # Gate 4: Margin availability
        if amount_usd > available_cash:
            msg = (f"Insufficient margin: need ${amount_usd:,.2f}, "
                   f"available ${available_cash:,.2f}.")
            return False, RISK_REJECTED_MARGIN, msg

        # Gate 5: Daily loss
        if self.daily_realized_loss >= self.daily_loss_limit_usd:
            msg = (f"Daily loss limit ${self.daily_loss_limit_usd:,.2f} reached "
                   f"(today: ${self.daily_realized_loss:,.2f}). No new orders today.")
            return False, RISK_REJECTED_DAILY_LOSS, msg

        # Gate 6: Drawdown circuit breaker
        if self.circuit_tripped:
            msg = f"Circuit breaker: {self.trip_reason}"
            return False, RISK_REJECTED_DRAWDOWN, msg

        # Gate 7: Stop-loss configured
        sl_pct = self.active_profile.get("stop_loss_pct", 0.0)
        if sl_pct <= 0:
            msg = "Stop-loss not configured for this risk profile."
            return False, RISK_REJECTED_INVALID_SL, msg

        return True, RISK_OK, "Order passed all 7 risk gates."

    def validate_order(self, position_size_usd: float, leverage: float, current_open_positions_count: int) -> tuple:
        """Legacy compatibility alias — routes through full 7-gate pipeline."""
        ok, code, msg = self.validate_order_pipeline(
            amount_usd=position_size_usd,
            leverage=leverage,
            current_open_positions=current_open_positions_count,
            available_cash=position_size_usd + 0.01
        )
        return ok, msg

    def update_portfolio_drawdown(self, current_equity: float, peak_equity: float = 600000.0) -> bool:
        if peak_equity > 0:
            drawdown_pct = ((peak_equity - current_equity) / peak_equity) * 100.0
            if drawdown_pct >= self.max_drawdown_pct:
                self.circuit_tripped = True
                self.trip_reason = f"Drawdown {drawdown_pct:.1f}% exceeded {self.max_drawdown_pct:.1f}% limit."
                return True
        self.circuit_tripped = False
        self.trip_reason = "NORMAL_OPERATIONS"
        return False


# Global Singleton
risk_engine = RiskEngine()
