"""
Aegis-Quant Market Regime & Fear/Greed Dynamic Sizing Governor.
Dynamically scales order allocation based on real-time market sentiment and volatility regimes:
  - Extreme Fear (< 25) or High VIX (> 22): 0.50x Defensive Sizing
  - Normal / Moderate (25 - 75): 1.00x Optimal Standard Sizing
  - Extreme Greed (> 80): 0.75x Cautious Top-Protection Sizing
"""

import time
from typing import Dict, Any

class MarketRegimeSizer:
    def __init__(self):
        # Simulated live sentiment telemetry feed
        self.fear_greed_score = 64  # 0-100 (64 = Greed / Healthy Trend)
        self.india_vix = 13.8       # Below 15 = Low Volatility / Bullish
        self.last_updated = time.time()

    def update_sentiment(self, score: int, vix: float = 13.8) -> None:
        self.fear_greed_score = max(0, min(100, score))
        self.india_vix = max(5.0, vix)
        self.last_updated = time.time()

    def get_sizing_multiplier(self) -> Dict[str, Any]:
        """
        Calculates position sizing factor based on sentiment and volatility.
        """
        score = self.fear_greed_score
        vix = self.india_vix

        if score < 25 or vix > 24.0:
            regime = "EXTREME_VOLATILITY_PANIC"
            multiplier = 0.50
            guidance = "Defensive mode: 50% position sizing to preserve capital against market shakeouts."
        elif score > 80:
            regime = "EXTREME_GREED_BLOWOFF"
            multiplier = 0.75
            guidance = "Caution: 75% position sizing to guard against sudden exhaustion reversals."
        elif 45 <= score <= 75 and vix < 18.0:
            regime = "STEADY_BULL_EXPANSION"
            multiplier = 1.00
            guidance = "Optimal condition: 100% standard allocation with trailing ratchet active."
        else:
            regime = "NEUTRAL_CONSOLIDATION"
            multiplier = 0.85
            guidance = "Moderate sizing: 85% allocation in choppy/neutral range."

        return {
            "fear_greed_index": score,
            "sentiment_label": "EXTREME_FEAR" if score < 25 else ("FEAR" if score < 45 else ("NEUTRAL" if score < 55 else ("GREED" if score <= 80 else "EXTREME_GREED"))),
            "india_vix": vix,
            "regime": regime,
            "sizing_multiplier": multiplier,
            "guidance": guidance
        }

market_regime_sizer = MarketRegimeSizer()
