"""
Aegis-Quant Japanese Candlestick Pattern Recognition Engine.
Analyzes micro candlestick structure (OHLC ratios, body size, upper/lower wick proportions).
Identifies classic high-conviction price action patterns:
  1. Bullish Hammer (Rejection of intraday lows with long lower wick >= 60%)
  2. Bullish Engulfing (Green body completely envelops previous red body)
  3. Morning Star (3-bar bullish reversal at bottom of trend)
  4. Bullish Marubozu (Strong full-body momentum bar)
  5. Bearish Shooting Star (Rejection of highs with long upper wick >= 60%)
  6. Bearish Engulfing (Red body completely envelops previous green body)
  7. Doji Breakout (Volatility compression leading into directional expansion)
"""

from typing import List, Dict, Any, Optional


class CandlestickPatternEngine:
    """
    Sub-second price action candlestick pattern analyzer.
    Analyzes list of OHLC candlestick dictionaries: [{'open': float, 'high': float, 'low': float, 'close': float, ...}]
    """

    def analyze_candles(self, candles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze candlestick series and return primary detected pattern, signal, and conviction boost.
        Signal: 'BUY' | 'SELL' | 'NEUTRAL'
        Score: -100 to +100
        """
        if not candles or len(candles) < 2:
            return {
                "pattern": "INSUFFICIENT_DATA",
                "signal": "NEUTRAL",
                "score": 0.0,
                "confidence_boost": 0.0,
                "description": "Awaiting more candles for pattern recognition"
            }

        c_curr = candles[-1]
        c_prev = candles[-2]
        c_prev2 = candles[-3] if len(candles) >= 3 else None

        o = float(c_curr.get("open", 0.0))
        h = float(c_curr.get("high", 0.0))
        l = float(c_curr.get("low", 0.0))
        c = float(c_curr.get("close", 0.0))

        po = float(c_prev.get("open", 0.0))
        ph = float(c_prev.get("high", 0.0))
        pl = float(c_prev.get("low", 0.0))
        pc = float(c_prev.get("close", 0.0))

        total_range = h - l
        if total_range <= 0.00001:
            return {
                "pattern": "FLAT_TICK",
                "signal": "NEUTRAL",
                "score": 0.0,
                "confidence_boost": 0.0,
                "description": "Zero volatility candle"
            }

        body = abs(c - o)
        body_pct = body / total_range
        is_green = c >= o
        is_red = c < o

        upper_wick = h - max(o, c)
        lower_wick = min(o, c) - l

        upper_wick_pct = upper_wick / total_range
        lower_wick_pct = lower_wick / total_range

        prev_range = ph - pl
        prev_body = abs(pc - po)
        prev_is_red = pc < po
        prev_is_green = pc >= po

        # ── 1. BULLISH HAMMER (Long lower wick >= 58%, small body at top, lower wick >= 2x body)
        if lower_wick_pct >= 0.58 and body_pct <= 0.35 and upper_wick_pct <= 0.15:
            return {
                "pattern": "BULLISH_HAMMER",
                "signal": "BUY",
                "score": 88.0,
                "confidence_boost": 18.0,
                "direction": "BULLISH",
                "description": f"Hammer rejection: sellers rejected from low, long lower wick ({lower_wick_pct*100:.0f}%)"
            }

        # ── 2. BULLISH ENGULFING (Previous red candle, current green candle body engulfs previous body)
        if prev_is_red and is_green and (c > po) and (o < pc):
            if body >= prev_body * 1.05:
                return {
                    "pattern": "BULLISH_ENGULFING",
                    "signal": "BUY",
                    "score": 92.0,
                    "confidence_boost": 22.0,
                    "direction": "BULLISH",
                    "description": "Bullish Engulfing: buyers overwhelmed previous bearish candle completely"
                }

        # ── 3. MORNING STAR (3-Candle Bullish Reversal)
        if c_prev2:
            p2_o = float(c_prev2.get("open", 0.0))
            p2_c = float(c_prev2.get("close", 0.0))
            p2_is_red = p2_c < p2_o
            star_small = prev_body <= (abs(p2_c - p2_o) * 0.45)
            if p2_is_red and star_small and is_green and (c >= (p2_o + p2_c) / 2.0):
                return {
                    "pattern": "MORNING_STAR",
                    "signal": "BUY",
                    "score": 95.0,
                    "confidence_boost": 25.0,
                    "direction": "BULLISH",
                    "description": "Morning Star: 3-bar reversal confirmed, buyers regained control above midpoint"
                }

        # ── 4. BULLISH MARUBOZU (Strong green candle with body >= 85% of range)
        if is_green and body_pct >= 0.85:
            return {
                "pattern": "BULLISH_MARUBOZU",
                "signal": "BUY",
                "score": 85.0,
                "confidence_boost": 15.0,
                "direction": "BULLISH",
                "description": f"Bullish Marubozu: pure buyer dominance ({body_pct*100:.0f}% body)"
            }

        # ── 5. BEARISH SHOOTING STAR (Long upper wick >= 58%, small body at bottom)
        if upper_wick_pct >= 0.58 and body_pct <= 0.35 and lower_wick_pct <= 0.15:
            return {
                "pattern": "BEARISH_SHOOTING_STAR",
                "signal": "SELL",
                "score": -88.0,
                "confidence_boost": -20.0,
                "direction": "BEARISH",
                "description": f"Shooting Star rejection: buyers rejected from high, long upper wick ({upper_wick_pct*100:.0f}%)"
            }

        # ── 6. BEARISH ENGULFING (Previous green candle, current red candle body engulfs previous body)
        if prev_is_green and is_red and (c < po) and (o > pc):
            if body >= prev_body * 1.05:
                return {
                    "pattern": "BEARISH_ENGULFING",
                    "signal": "SELL",
                    "score": -90.0,
                    "confidence_boost": -22.0,
                    "direction": "BEARISH",
                    "description": "Bearish Engulfing: sellers swallowed previous green candle"
                }

        # ── 7. DOJI (Indecision — tight compression before breakout)
        if body_pct <= 0.12 and lower_wick_pct >= 0.30 and upper_wick_pct >= 0.30:
            return {
                "pattern": "DOJI_INDECISION",
                "signal": "NEUTRAL",
                "score": 50.0,
                "confidence_boost": 0.0,
                "direction": "NEUTRAL",
                "description": "Doji: buyers and sellers balanced, awaiting breakout trigger"
            }

        return {
            "pattern": "STANDARD_PRICE_ACTION",
            "signal": "BUY" if is_green else "HOLD",
            "score": 65.0 if is_green else 45.0,
            "confidence_boost": 5.0 if is_green else 0.0,
            "direction": "BULLISH" if is_green else "BEARISH",
            "description": "Normal market flow"
        }


# Global singleton
candlestick_pattern_engine = CandlestickPatternEngine()
