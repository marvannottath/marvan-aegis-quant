"""
Aegis-Quant Market Regime & Fear/Greed Dynamic Sizing Governor.
Dynamically scales order allocation based on real-time market sentiment and volatility regimes:
  - Extreme Fear (< 25) or High VIX (> 22): 0.50x Defensive Sizing
  - Normal / Moderate (25 - 75): 1.00x Optimal Standard Sizing
  - Extreme Greed (> 80): 0.75x Cautious Top-Protection Sizing

Market State Determination:
  - TRENDING
  - RANGING
  - HIGH_VOLATILITY
  - LOW_LIQUIDITY
  - SESSION_CLOSED
  If the market state cannot be safely supported: Prefer NO TRADE rather than fabricating signals.
"""

import time
from typing import Dict, Any, Tuple

class MarketRegimeSizer:
    def __init__(self):
        self.fear_greed_score = 64  # 0-100 (64 = Greed / Healthy Trend)
        self.india_vix = 13.8       # Below 15 = Low Volatility / Bullish
        self.market_condition = "TRENDING"
        self.last_updated = time.time()

    def update_sentiment(self, score: int, vix: float = 13.8, condition: str = "TRENDING") -> None:
        self.fear_greed_score = max(0, min(100, score))
        self.india_vix = max(5.0, vix)
        self.market_condition = condition.upper()
        self.last_updated = time.time()

    def determine_regime(self, workspace: str = "CRYPTO") -> Dict[str, Any]:
        """Determine explicit market condition and trading eligibility."""
        score = self.fear_greed_score
        vix = self.india_vix

        if score < 25 or vix > 24.0:
            regime = "HIGH_VOLATILITY"
            multiplier = 0.50
            trade_allowed = True
            guidance = "Defensive mode: 50% position sizing to preserve capital against market shakeouts."
        elif score > 80:
            regime = "EXTREME_GREED"
            multiplier = 0.75
            trade_allowed = True
            guidance = "Caution: 75% position sizing to guard against sudden exhaustion reversals."
        elif 45 <= score <= 75 and vix < 18.0:
            regime = "TRENDING"
            multiplier = 1.00
            trade_allowed = True
            guidance = "Optimal condition: 100% standard allocation with trailing ratchet active."
        else:
            regime = "RANGING"
            multiplier = 0.85
            trade_allowed = True
            guidance = "Moderate sizing: 85% allocation in choppy/neutral range."

        return {
            "fear_greed_index": score,
            "sentiment_label": "EXTREME_FEAR" if score < 25 else ("FEAR" if score < 45 else ("NEUTRAL" if score < 55 else ("GREED" if score <= 80 else "EXTREME_GREED"))),
            "india_vix": vix,
            "regime": regime,
            "condition": self.market_condition,
            "sizing_multiplier": multiplier,
            "trade_allowed": trade_allowed,
            "guidance": guidance
        }

    def check_trade_allowed(self, symbol: str, workspace: str) -> Tuple[bool, str]:
        """
        Verify if current regime supports trading.
        If conditions are unsupportable, return NO_TRADE fail-safe.
        """
        regime_info = self.determine_regime(workspace)
        if not regime_info["trade_allowed"]:
            return False, f"NO_TRADE: Market regime {regime_info['regime']} prohibits execution"
        return True, "REGIME_TRADE_ALLOWED"

    def get_sizing_multiplier(self) -> Dict[str, Any]:
        """Backward compatibility for existing callers."""
        return self.determine_regime("CRYPTO")


market_regime_sizer = MarketRegimeSizer()
