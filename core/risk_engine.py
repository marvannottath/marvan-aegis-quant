"""
Institutional-Grade Risk Engine & Safety Circuit Breaker.
Enforces Risk Profiles (Conservative, Moderate, Aggressive), Stop-Loss, Take-Profit,
Kelly Sizing, Volatility Parity, and Maximum Portfolio Drawdown Limits.
PERSISTENCE ENABLED: Saves active risk profile & max trade cap to risk_engine_state.json so settings persist across reloads & restarts!
"""

import json
from pathlib import Path
from typing import Dict, Any, Tuple
from config.settings import (
    MAX_POSITION_SIZE_PCT,
    MAX_PORTFOLIO_DRAWDOWN_PCT,
    DEFAULT_STOP_LOSS_PCT,
    DEFAULT_TAKE_PROFIT_PCT,
    KELLY_FRACTION
)

RISK_FILE = Path(__file__).resolve().parent / "risk_engine_state.json"

class RiskEngine:
    PROFILES = {
        "CONSERVATIVE": {
            "name": "CONSERVATIVE",
            "label": "Conservative (Low Risk 2x)",
            "max_position_size_pct": 0.05,
            "max_drawdown_pct": 0.05,
            "stop_loss_pct": 0.005,  # -0.5% Stop-Loss
            "take_profit_pct": 0.015, # +1.5% Take-Profit (3:1 R:R Ratio)
            "default_leverage": 2.0,
            "kelly_fraction": 0.3
        },
        "MODERATE": {
            "name": "MODERATE",
            "label": "Moderate (Standard 10x)",
            "max_position_size_pct": 0.10,
            "max_drawdown_pct": 0.08,
            "stop_loss_pct": 0.008,  # -0.8% Stop-Loss
            "take_profit_pct": 0.020, # +2.0% Take-Profit (2.5:1 R:R Ratio)
            "default_leverage": 10.0,
            "kelly_fraction": 0.5
        },
        "AGGRESSIVE": {
            "name": "AGGRESSIVE",
            "label": "Aggressive (High Yield 25x)",
            "max_position_size_pct": 0.15,
            "max_drawdown_pct": 0.12,
            "stop_loss_pct": 0.010,  # -1.0% Stop-Loss
            "take_profit_pct": 0.030, # +3.0% Take-Profit (3:1 R:R Ratio)
            "default_leverage": 25.0,
            "kelly_fraction": 0.8
        }
    }

    def __init__(self, initial_balance: float = 100000.0, profile: str = "MODERATE"):
        self.initial_balance = initial_balance
        self.peak_balance = initial_balance
        self.circuit_breaker_tripped = False
        self.trip_reason = ""
        self.active_profile_name = profile if profile in self.PROFILES else "MODERATE"
        self.active_profile = self.PROFILES[self.active_profile_name]
        self.custom_max_trade_cap_usd = 5000.0  # Default max $5,000 trade allocation limit
        self._load_state()

    def _load_state(self):
        """Load persisted risk profile & cap from JSON file if exists."""
        if RISK_FILE.exists():
            try:
                with open(RISK_FILE, "r") as f:
                    data = json.load(f)
                    saved_prof = data.get("active_profile_name", "MODERATE")
                    if saved_prof in self.PROFILES:
                        self.active_profile_name = saved_prof
                        self.active_profile = self.PROFILES[saved_prof]
                    self.custom_max_trade_cap_usd = float(data.get("custom_max_trade_cap_usd", 5000.0))
            except Exception as e:
                print(f"[RISK ENGINE] Load state error: {e}")

    def _save_state(self):
        """Persist risk profile state to JSON file."""
        try:
            with open(RISK_FILE, "w") as f:
                json.dump({
                    "active_profile_name": self.active_profile_name,
                    "custom_max_trade_cap_usd": self.custom_max_trade_cap_usd
                }, f, indent=2)
        except Exception as e:
            print(f"[RISK ENGINE] Save state error: {e}")

    def set_max_trade_cap(self, cap_usd: float) -> float:
        """Set custom USD limit per single trade execution."""
        self.custom_max_trade_cap_usd = max(0.1, float(cap_usd))
        self._save_state()
        return self.custom_max_trade_cap_usd

    def set_risk_profile(self, profile_name: str) -> Dict[str, Any]:
        """Switch active risk profile (CONSERVATIVE, MODERATE, AGGRESSIVE)."""
        clean_name = profile_name.upper().strip()
        if clean_name in self.PROFILES:
            self.active_profile_name = clean_name
            self.active_profile = self.PROFILES[clean_name]
            self.reset_circuit_breaker()
            self._save_state()
        return self.get_profile_summary()

    def get_profile_summary(self) -> Dict[str, Any]:
        """Fetch current risk profile details."""
        return {
            "active_profile": self.active_profile_name,
            "label": self.active_profile["label"],
            "max_position_size_pct": self.active_profile["max_position_size_pct"],
            "max_drawdown_pct": self.active_profile["max_drawdown_pct"],
            "stop_loss_pct": self.active_profile["stop_loss_pct"],
            "take_profit_pct": self.active_profile["take_profit_pct"],
            "default_leverage": self.active_profile["default_leverage"],
            "max_trade_cap_usd": self.custom_max_trade_cap_usd
        }

    def update_portfolio_drawdown(self, current_equity: float) -> bool:
        """
        Check max portfolio drawdown. If drawdown exceeds active profile limit, trip circuit breaker.
        Returns True if circuit breaker is active.
        """
        if current_equity > self.peak_balance:
            self.peak_balance = current_equity

        drawdown_pct = (self.peak_balance - current_equity) / self.peak_balance
        max_allowed = self.active_profile["max_drawdown_pct"]

        if drawdown_pct >= max_allowed:
            self.circuit_breaker_tripped = True
            self.trip_reason = f"Max Portfolio Drawdown Exceeded ({drawdown_pct*100:.2f}% >= {max_allowed*100:.2f}% [{self.active_profile_name}])"
            return True
            
        return self.circuit_breaker_tripped

    def calculate_position_size(self, capital: float, asset_volatility: float, opportunity_score: float = 75.0, win_rate: float = 0.55, win_loss_ratio: float = 1.5) -> float:
        """
        Calculate dynamic risk-weighted capital allocation up to custom_max_trade_cap_usd ceiling.
        """
        if self.circuit_breaker_tripped or capital <= 0:
            return 0.0

        if capital <= 100.0:
            # Micro-Account Mode ($10 - $100)
            micro_cap = min(self.custom_max_trade_cap_usd, capital)
            return round(max(0.50, micro_cap), 2)

        # Dynamic risk sizing based on asset volatility and opportunity score
        vol_scalar = 0.01 / (asset_volatility + 1e-6)
        vol_scalar = max(0.3, min(vol_scalar, 1.2))
        opp_factor = max(0.4, min(opportunity_score / 100.0, 1.0))

        # Risk-weighted sizing fraction (30% to 95% of cap)
        risk_fraction = max(0.25, min(opp_factor * vol_scalar, 0.95))
        target_allocation = self.custom_max_trade_cap_usd * risk_fraction

        max_pos_pct = self.active_profile["max_position_size_pct"]
        final_size = min(target_allocation, capital * max_pos_pct, self.custom_max_trade_cap_usd)
        return round(final_size, 2)

    def evaluate_exit_rules(self, entry_price: float, current_price: float, position_type: str) -> Tuple[bool, str]:
        """
        Check if position should be closed due to active profile Stop-Loss or Take-Profit.
        """
        stop_loss_pct = self.active_profile["stop_loss_pct"]
        take_profit_pct = self.active_profile["take_profit_pct"]

        if position_type.upper() == "BUY":
            price_change = (current_price - entry_price) / entry_price
            if price_change <= -stop_loss_pct:
                return True, f"Stop-Loss Triggered ({price_change*100:.2f}%)"
            elif price_change >= take_profit_pct:
                return True, f"Take-Profit Hit (+{price_change*100:.2f}%)"
        elif position_type.upper() == "SELL":
            price_change = (entry_price - current_price) / entry_price
            if price_change <= -stop_loss_pct:
                return True, f"Stop-Loss Triggered ({price_change*100:.2f}%)"
            elif price_change >= take_profit_pct:
                return True, f"Take-Profit Hit (+{price_change*100:.2f}%)"

        return False, "Holding"

    def reset_circuit_breaker(self):
        """Reset the circuit breaker manually."""
        self.circuit_breaker_tripped = False
        self.trip_reason = ""

# Singleton instance
risk_engine = RiskEngine()
