"""
Institutional Dynamic Risk Management Engine.
Enforces strict portfolio constraints, max drawdown circuit breakers,
isolated position sizing limits, and true active risk profile profiles:
1. CONSERVATIVE: 2.0x Max Leverage, 1.0% Risk Cap per trade, 2-4 Max Positions
2. MODERATE: 10.0x Max Leverage, 2.5% Risk Cap per trade, 4-8 Max Positions
3. AGGRESSIVE: 25.0x Max Leverage, 5.0% Risk Cap per trade, 6-12 Max Positions
"""

from typing import Dict, Any, Optional

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
        "max_open_positions": 12,
        "min_open_positions": 6,
        "circuit_breaker_drawdown_pct": 20.0,
        "take_profit_target_pct": 6.0,
        "stop_loss_pct": 2.5
    }
}

class RiskEngine:
    def __init__(self, max_drawdown_pct: float = 10.0, default_profile: str = "AGGRESSIVE"):
        self.active_profile_name = default_profile.upper() if default_profile.upper() in PROFILES else "AGGRESSIVE"
        self.active_profile = PROFILES[self.active_profile_name]
        self.max_drawdown_pct = self.active_profile["circuit_breaker_drawdown_pct"]
        self.circuit_tripped = False
        self.custom_trade_cap_usd: float = 5000.0

    def set_risk_profile(self, profile_name: str) -> Dict[str, Any]:
        """Dynamically switch active enforced risk profile."""
        name = profile_name.upper()
        if name in PROFILES:
            self.active_profile_name = name
            self.active_profile = PROFILES[name]
            self.max_drawdown_pct = self.active_profile["circuit_breaker_drawdown_pct"]
            print(f"[RISK ENGINE] Active Risk Profile set to: {name} (Max Lev: {self.active_profile['max_leverage']}x)")
        return self.active_profile

    def set_max_trade_cap(self, cap_usd: float) -> float:
        """Set maximum trade capital safety cap."""
        self.custom_trade_cap_usd = max(100.0, float(cap_usd))
        return self.custom_trade_cap_usd

    def calculate_position_size(self, virtual_cash: float, volatility: float, opportunity_score: float) -> float:
        """
        Calculate strict risk-adjusted position size in USD.
        Enforces active profile max risk % and custom trade safety cap.
        """
        risk_pct = self.active_profile["max_risk_per_trade_pct"] / 100.0
        base_size = virtual_cash * risk_pct

        # Confluence scaling
        if opportunity_score >= 85.0:
            scale = 1.25
        elif opportunity_score >= 70.0:
            scale = 1.0
        else:
            scale = 0.75

        # Volatility normalization
        vol_factor = max(0.5, min(1.5, 0.01 / max(0.001, volatility)))
        recommended_size = base_size * scale * vol_factor

        # Strict safety bounds
        final_size = max(500.0, min(self.custom_trade_cap_usd, recommended_size))
        return round(min(final_size, virtual_cash * 0.5), 2)

    def validate_order(self, proposed_size_usd: float, leverage: float, current_open_count: int) -> tuple[bool, str]:
        """Strict pre-trade risk validation gate."""
        if self.circuit_tripped:
            return False, "Circuit Breaker Activated: Trading is locked for capital preservation."

        if leverage > self.active_profile["max_leverage"]:
            return False, f"Leverage {leverage}x exceeds active {self.active_profile_name} limit of {self.active_profile['max_leverage']}x."

        if current_open_count >= self.active_profile["max_open_positions"]:
            return False, f"Max position limit of {self.active_profile['max_open_positions']} reached for {self.active_profile_name} profile."

        if proposed_size_usd > self.custom_trade_cap_usd:
            return False, f"Proposed capital ${proposed_size_usd} exceeds safety cap of ${self.custom_trade_cap_usd}."

        return True, "Risk checks passed."

    def update_portfolio_drawdown(self, current_equity: float) -> bool:
        """Evaluate portfolio drawdown against peak equity."""
        if not hasattr(self, "peak_equity"):
            self.peak_equity = current_equity
        if current_equity > self.peak_equity:
            self.peak_equity = current_equity
        if self.peak_equity > 0:
            dd_pct = ((self.peak_equity - current_equity) / self.peak_equity) * 100.0
            if dd_pct >= self.max_drawdown_pct:
                self.circuit_tripped = True
                self.trip_reason = f"Max Drawdown of {dd_pct:.1f}% exceeded limit of {self.max_drawdown_pct}%."
                return True
        self.trip_reason = "NORMAL_OPERATIONS"
        return False

    def get_profile_summary(self) -> Dict[str, Any]:
        """Return full risk profile metadata for dashboard."""
        return {
            "active_profile": self.active_profile_name,
            "description": self.active_profile["description"],
            "default_leverage": self.active_profile["default_leverage"],
            "max_leverage": self.active_profile["max_leverage"],
            "max_risk_per_trade_pct": self.active_profile["max_risk_per_trade_pct"],
            "max_open_positions": self.active_profile["max_open_positions"],
            "min_open_positions": self.active_profile["min_open_positions"],
            "stop_loss_pct": self.active_profile["stop_loss_pct"],
            "take_profit_pct": self.active_profile["take_profit_target_pct"],
            "max_trade_cap_usd": self.custom_trade_cap_usd,
            "circuit_breaker_drawdown_pct": self.max_drawdown_pct
        }

    def check_circuit_breaker(self, current_equity: float, peak_equity: float) -> bool:
        """Evaluate maximum portfolio drawdown circuit breaker."""
        if peak_equity <= 0:
            return False
        dd_pct = ((peak_equity - current_equity) / peak_equity) * 100.0
        if dd_pct >= self.max_drawdown_pct:
            self.circuit_tripped = True
            return True
        return False

# Global Singleton Risk Engine
risk_engine = RiskEngine()
