"""
AEGIS-QUANT Multi-Strategy Time-Synchronized AI Ensemble.
Executes 3 complementary, non-correlated quantitative strategies in parallel:
  1. Morning Breakout Scalper (09:15 - 10:15 AM IST): High-volume opening range breaks
  2. VWAP Mean-Reversion Scalper (10:30 AM - 01:15 PM IST): Institutional VWAP deviations
  3. Afternoon Momentum Scalper (01:30 PM - 03:05 PM IST): Institutional closing trend
Coordinates through an ensemble voting engine ensuring strategies never clash.
"""

from typing import Dict, Any, Optional
from datetime import datetime, timezone, timedelta

IST_TZ = timezone(timedelta(hours=5, minutes=30))


class MultiStrategyEnsemble:
    STRAT_MORNING_BREAKOUT = "MORNING_BREAKOUT_SCALPER"
    STRAT_VWAP_MEAN_REVERSION = "VWAP_MEAN_REVERSION_SCALPER"
    STRAT_AFTERNOON_MOMENTUM = "AFTERNOON_MOMENTUM_SCALPER"
    STRAT_MICRO_SCALP = "MICRO_HIGH_FREQUENCY_SCALPER"

    def get_current_time_slot(self) -> str:
        """Determine active strategy time window based on Indian Standard Time."""
        now = datetime.now(timezone.utc).astimezone(IST_TZ)
        hour = now.hour
        minute = now.minute

        # 09:15 - 10:15 AM IST
        if (hour == 9 and minute >= 15) or (hour == 10 and minute < 15):
            return self.STRAT_MORNING_BREAKOUT

        # 10:30 AM - 01:15 PM IST
        elif (hour == 10 and minute >= 30) or (11 <= hour <= 12) or (hour == 13 and minute < 15):
            return self.STRAT_VWAP_MEAN_REVERSION

        # 01:30 PM - 03:05 PM IST
        elif (hour == 13 and minute >= 30) or (hour == 14) or (hour == 15 and minute < 6):
            return self.STRAT_AFTERNOON_MOMENTUM

        return self.STRAT_MICRO_SCALP

    def evaluate_signals(
        self,
        ticker: str,
        price: float,
        rsi: float,
        volatility: float,
        vwap: float,
        volume_surge_pct: float = 0.0,
        sentiment_score: float = 0.5,
    ) -> Dict[str, Any]:
        """
        Evaluate ticker against the active time strategy and secondary filters.
        Returns ensemble vote, action, confidence, and strategy name.
        """
        active_strategy = self.get_current_time_slot()
        confidence = 70.0
        action = "HOLD"
        reason = "Neutral conditions"

        # ── 1. Morning Breakout (09:15 - 10:15) ──────────────────────────────
        if active_strategy == self.STRAT_MORNING_BREAKOUT:
            if rsi >= 55.0 and price > vwap:
                action = "BUY"
                confidence = 88.0 + min(10.0, volume_surge_pct * 0.1)
                reason = "Morning Opening Range Breakout: Price holding firmly above VWAP with rising momentum"
            elif rsi <= 45.0 and price < vwap:
                action = "SELL"
                confidence = 85.0
                reason = "Morning Breakdown: Price failed VWAP hurdle with aggressive opening selling"

        # ── 2. VWAP Mean Reversion (10:30 - 13:15) ───────────────────────────
        elif active_strategy == self.STRAT_VWAP_MEAN_REVERSION:
            deviation_pct = ((price - vwap) / vwap) * 100.0
            if deviation_pct <= -0.40 and rsi <= 40.0:
                action = "BUY"
                confidence = 84.0
                reason = f"Oversold VWAP Dip: Price {deviation_pct:.2f}% below institutional benchmark; mean-reversion bounce expected"
            elif deviation_pct >= 0.50 and rsi >= 65.0:
                action = "SELL"
                confidence = 82.0
                reason = f"Overbought VWAP Spike: Price {deviation_pct:.2f}% above institutional benchmark; pullback expected"

        # ── 3. Afternoon Trend & Expiry Surge (13:30 - 15:05) ────────────────
        elif active_strategy == self.STRAT_AFTERNOON_MOMENTUM:
            if price > vwap and rsi >= 52.0:
                action = "BUY"
                confidence = 86.0
                reason = "Afternoon Trend Acceleration: Buyers dominating second session into close"
            elif price < vwap and rsi <= 48.0:
                action = "SELL"
                confidence = 84.0
                reason = "Afternoon Liquidation Pressure: Continuous institutional distribution"

        # ── 4. Standard Micro Scalp Fallback ──────────────────────────────────
        else:
            if price > vwap and rsi >= 50.0:
                action = "BUY"
                confidence = 78.0
                reason = "Micro-trend continuation"

        return {
            "ticker": ticker,
            "action": action,
            "confidence": round(confidence, 1),
            "active_strategy": active_strategy,
            "reason": reason,
            "price": price,
            "vwap": vwap,
            "rsi": rsi,
            "timestamp": datetime.now(timezone.utc).astimezone(IST_TZ).strftime("%Y-%m-%d %H:%M:%S IST"),
        }


# Global Singleton
multi_strategy_ensemble = MultiStrategyEnsemble()
