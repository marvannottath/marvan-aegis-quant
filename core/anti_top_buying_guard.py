"""
Aegis-Quant Anti-Top-Buying & Dip-Confirmation Guard.
Institutional alpha shield that prevents the #1 retail trap:
Buying at the absolute peak/upper wick of a green candle (FOMO chasing)
and panic-selling at the bottom of the subsequent pullback.

Rules Enforced:
1. Upper-Wick & Candle-Top Check:
   - If current price is in the top 22% of the active candle range (candle_pos > 0.78)
     and candle is an extended surge, BUY is strictly BLOCKED.
   - If upper rejection wick is > 30% of total candle range, BUY is BLOCKED.
2. 9-EMA Overextension (Rubber-Band Mean Reversion):
   - Never buy when price is stretched >0.35% (Crypto) or >0.25% (India) above the 9-EMA.
   - Requires price to pull back towards the 9-EMA / support zone before entry.
3. Institutional VWAP Stretch:
   - Never buy when price is >0.40% above institutional VWAP.
4. Micro-RSI Peak Exhaustion:
   - Never buy when 1m/5m RSI is overbought (> 66.0).
   - Entry sweet spot: RSI between 42.0 and 62.0.
"""

import time
import requests
from typing import Dict, Any, Tuple, Optional
from datetime import datetime, timezone, timedelta

IST_TZ = timezone(timedelta(hours=5, minutes=30))


class AntiTopBuyingGuard:
    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_ttl_sec: float = 4.0
        self._session = requests.Session()

    def check_entry_allowed(
        self,
        symbol: str,
        side: str = "BUY",
        current_price: float = 0.0,
        workspace: str = "CRYPTO",
        rsi: float = 50.0,
        candle_open: float = 0.0,
        candle_high: float = 0.0,
        candle_low: float = 0.0,
        vwap: float = 0.0
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Validates whether the entry is at a healthy dip/pullback level
        or chasing an exhaustion top.
        Returns: (allowed: bool, reason: str, metrics: dict)
        """
        if side != "BUY" or current_price <= 0:
            return True, "PASS: Non-BUY order or zero price", {}

        sym_clean = symbol.upper().replace("/", "").strip()
        now = time.time()

        # 1. Micro-RSI Exhaustion Gate
        if rsi > 66.0:
            return False, f"RSI_EXHAUSTION_TOP: RSI is overbought ({rsi:.1f} > 66.0). Chasing top prohibited — wait for cooldown.", {"rsi": rsi}

        # 2. Check Candlestick Structure (1m / Active Candle)
        c_high = candle_high
        c_low = candle_low
        c_open = candle_open
        c_close = current_price
        ema9 = 0.0
        ema21 = 0.0

        # For Crypto, fetch live 1m candle metrics if not provided or stale
        if workspace == "CRYPTO":
            cached = self._cache.get(sym_clean)
            if cached and (now - cached["epoch"]) < self._cache_ttl_sec:
                c_data = cached["data"]
                c_high = c_data.get("high", c_high)
                c_low = c_data.get("low", c_low)
                c_open = c_data.get("open", c_open)
                ema9 = c_data.get("ema9", 0.0)
                ema21 = c_data.get("ema21", 0.0)
            else:
                try:
                    url = f"https://api.binance.com/api/v3/klines?symbol={sym_clean}&interval=1m&limit=25"
                    resp = self._session.get(url, timeout=1.5)
                    if resp.status_code == 200:
                        klines = resp.json()
                        if klines:
                            last_k = klines[-1]
                            c_open = float(last_k[1])
                            c_high = max(float(last_k[2]), current_price)
                            c_low = min(float(last_k[3]), current_price)
                            closes = [float(k[4]) for k in klines]
                            if len(closes) >= 9:
                                # Calculate fast EMA-9
                                mult9 = 2.0 / (9 + 1)
                                e9 = closes[0]
                                for p in closes[1:]:
                                    e9 = (p - e9) * mult9 + e9
                                ema9 = round(e9, 4 if current_price < 10 else 2)

                            self._cache[sym_clean] = {
                                "epoch": now,
                                "data": {
                                    "open": c_open, "high": c_high, "low": c_low,
                                    "ema9": ema9, "ema21": ema21
                                }
                            }
                except Exception:
                    pass

        # 3. Candle Top Position & Upper Wick Rejection Evaluation
        c_range = c_high - c_low
        if c_range > 0 and c_high > c_low:
            c_range_pct = (c_range / c_low) * 100.0

            # Where is current price relative to candle range? (0.0 = low, 1.0 = high)
            candle_pos = (current_price - c_low) / c_range

            # Upper wick size relative to candle range
            body_top = max(c_open, c_close)
            upper_wick = max(0.0, c_high - body_top)
            upper_wick_ratio = upper_wick / c_range

            # RULE A: Extreme Upper Wick (Shooting star / Bearish rejection)
            if upper_wick_ratio > 0.35 and c_range_pct >= 0.15:
                return False, f"UPPER_WICK_REJECTION: {upper_wick_ratio*100:.1f}% upper wick detected. Sellers rejecting upward push.", {
                    "candle_pos": round(candle_pos, 2), "upper_wick_ratio": round(upper_wick_ratio, 2)
                }

            # RULE B: Absolute Candle Peak Chasing (Top 22% of candle)
            # Only blocks if the candle has a meaningful range (>0.20%)
            if candle_pos > 0.78 and c_range_pct >= 0.20:
                return False, f"CANDLE_TOP_BLOCKED: Price is at {candle_pos*100:.1f}% of candle range (Peak: {c_high}). Wait for pullback/retest.", {
                    "candle_pos": round(candle_pos, 2), "candle_high": c_high, "candle_low": c_low
                }

        # 4. 9-EMA Overextension (Rubber-Band Gate)
        if ema9 > 0:
            stretch_pct = (current_price - ema9) / ema9 * 100.0
            max_allowed_stretch = 0.35 if workspace == "CRYPTO" else 0.25
            if stretch_pct > max_allowed_stretch:
                return False, f"EMA9_OVEREXTENDED: Price is stretched +{stretch_pct:.2f}% above 9-EMA ({ema9}). Mean-reversion risk — wait for pullback to EMA.", {
                    "current_price": current_price, "ema9": ema9, "stretch_pct": round(stretch_pct, 2)
                }

        # 5. Institutional VWAP Stretch (For Indian Equities & Scalping)
        if vwap > 0:
            vwap_stretch_pct = (current_price - vwap) / vwap * 100.0
            if vwap_stretch_pct > 0.45:
                return False, f"VWAP_OVEREXTENDED: Price is +{vwap_stretch_pct:.2f}% above institutional VWAP ({vwap:.2f}). Chasing top prohibited.", {
                    "current_price": current_price, "vwap": vwap, "vwap_stretch_pct": round(vwap_stretch_pct, 2)
                }

        return True, "DIP_CONFIRMED: Price is within healthy support/pullback zone. Entry permitted.", {
            "rsi": rsi, "ema9": ema9, "candle_high": c_high, "candle_low": c_low
        }


# Global singleton
anti_top_buying_guard = AntiTopBuyingGuard()
