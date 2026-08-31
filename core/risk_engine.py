import json
from pathlib import Path
from typing import Dict, Any, Optional

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

class RiskEngine:
    def __init__(self, max_drawdown_pct: float = 10.0, default_profile: str = "CONSERVATIVE"):
        self.active_profile_name = default_profile.upper() if default_profile.upper() in PROFILES else "CONSERVATIVE"
        self.custom_trade_cap_usd: float = 5000.0
        self.circuit_tripped = False
        self.trip_reason = "NORMAL_OPERATIONS"
        self._load_state()
        self.active_profile = PROFILES.get(self.active_profile_name, PROFILES["CONSERVATIVE"])
        self.max_drawdown_pct = self.active_profile["circuit_breaker_drawdown_pct"]

    def _load_state(self):
        """Load persisted risk profile from disk."""
        if RISK_STATE_FILE.exists():
            try:
                with open(RISK_STATE_FILE, "r") as f:
                    data = json.load(f)
                    p_name = data.get("active_profile_name", "CONSERVATIVE").upper()
                    if p_name in PROFILES:
                        self.active_profile_name = p_name
                    self.custom_trade_cap_usd = float(data.get("custom_trade_cap_usd", 5000.0))
            except Exception as e:
                print(f"[RISK ENGINE] Load state notice: {e}")

    def _save_state(self):
        """Persist risk profile to disk."""
        try:
            RISK_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(RISK_STATE_FILE, "w") as f:
                json.dump({
                    "active_profile_name": self.active_profile_name,
                    "custom_trade_cap_usd": self.custom_trade_cap_usd
                }, f, indent=2)
        except Exception as e:
            print(f"[RISK ENGINE] Save state notice: {e}")

    def set_risk_profile(self, profile_name: str) -> Dict[str, Any]:
        """Dynamically switch active enforced risk profile and persist to disk."""
        name = profile_name.upper()
        if name in PROFILES:
            self.active_profile_name = name
            self.active_profile = PROFILES[name]
            self.max_drawdown_pct = self.active_profile["circuit_breaker_drawdown_pct"]
            self._save_state()
            print(f"[RISK ENGINE] Active Risk Profile set & saved to: {name} (Max Lev: {self.active_profile['max_leverage']}x)")
        return self.active_profile

    def set_max_trade_cap(self, cap_usd: float) -> float:
        """Set maximum trade capital safety cap and persist."""
        self.custom_trade_cap_usd = max(100.0, float(cap_usd))
        self._save_state()
        return self.custom_trade_cap_usd

    def get_profile_summary(self) -> Dict[str, Any]:
        """Fetch summary of active risk profile settings."""
        return {
            "active_profile": self.active_profile_name,
            "description": self.active_profile["description"],
            "default_leverage": self.active_profile["default_leverage"],
            "max_leverage": self.active_profile["max_leverage"],
            "max_risk_pct": self.active_profile["max_risk_per_trade_pct"],
            "max_positions": self.active_profile["max_open_positions"],
            "stop_loss_pct": self.active_profile["stop_loss_pct"] / 100.0,
            "take_profit_pct": self.active_profile["take_profit_target_pct"] / 100.0,
            "max_trade_cap_usd": self.custom_trade_cap_usd
        }

    def calculate_position_size(self, virtual_cash: float, volatility: float, confidence_score: float) -> float:
        """Dynamically size positions based on profile risk cap and volatility."""
        risk_pct = self.active_profile["max_risk_per_trade_pct"] / 100.0
        base_size = virtual_cash * risk_pct
        
        # Volatility & confidence scalar
        vol_scalar = max(0.5, min(1.5, (0.01 / max(0.001, volatility))))
        conf_scalar = max(0.6, min(1.3, confidence_score / 70.0))
        
        size = base_size * vol_scalar * conf_scalar
        return min(self.custom_trade_cap_usd, max(100.0, round(size, 2)))

    def validate_order(self, position_size_usd: float, leverage: float, current_open_positions_count: int) -> tuple:
        """Enforce risk profile limits before executing orders."""
        if current_open_positions_count >= self.active_profile["max_open_positions"]:
            return False, f"Max position limit ({self.active_profile['max_open_positions']}) reached for {self.active_profile_name} profile."
        
        if leverage > self.active_profile["max_leverage"]:
            return False, f"Requested leverage ({leverage}x) exceeds max leverage ({self.active_profile['max_leverage']}x) for {self.active_profile_name} profile."
            
        if position_size_usd > self.custom_trade_cap_usd * 1.5:
            return False, f"Position size (${position_size_usd:,.2f}) exceeds safety cap (${self.custom_trade_cap_usd:,.2f})."
            
        return True, "ORDER_APPROVED"

    def update_portfolio_drawdown(self, current_equity: float, peak_equity: float = 600000.0) -> bool:
        """Check if portfolio drawdown trips the circuit breaker."""
        if peak_equity > 0:
            drawdown_pct = ((peak_equity - current_equity) / peak_equity) * 100.0
            if drawdown_pct >= self.max_drawdown_pct:
                self.circuit_tripped = True
                self.trip_reason = f"CIRCUIT TRIPPED: Drawdown {drawdown_pct:.1f}% exceeded limit {self.max_drawdown_pct:.1f}%"
                return True
        self.circuit_tripped = False
        self.trip_reason = "NORMAL_OPERATIONS"
        return False

# Global Singleton Risk Engine
risk_engine = RiskEngine()
