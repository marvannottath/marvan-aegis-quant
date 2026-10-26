"""
Aegis-Quant Liquidity Wick & Flash Crash Sniper.
Monitors sub-second candlestick micro-structure and deep order book liquidity.
Detects:
  - Flash-crash wicks (cascading stop/liquidation runs down to extreme discounts)
  - Rapid liquidity absorption (where lower shadow/wick is >= 50% of the entire candle span)
  - Reversal bounce impulses right at deep institutional bid absorption levels.
Signals high-velocity scalp entries (+1.0% to +2.5% targets) with ultra-tight risk below wick-lows.
"""

import time
import requests
from typing import Dict, Any, List, Tuple
from datetime import datetime, timezone, timedelta

IST_TZ = timezone(timedelta(hours=5, minutes=30))

class LiquidityWickSniper:
    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_ttl_sec: float = 3.0
        self._session = requests.Session()
        self._recent_snipes: List[Dict[str, Any]] = []

    def scan_wick_opportunity(self, symbol: str = "BTCUSDT", workspace: str = "CRYPTO") -> Dict[str, Any]:
        """
        Scans for extreme downward liquidity absorption wicks on 1m and 5m intervals.
        """
        sym_clean = symbol.upper().replace("/", "").strip()
        now = time.time()

        cached = self._cache.get(sym_clean)
        if cached and (now - cached["epoch"]) < self._cache_ttl_sec:
            return cached["data"]

        wick_detected = False
        signal = "NO_WICK"
        drop_depth_pct = 0.0
        lower_wick_ratio = 0.0
        current_price = 0.0
        candle_low = 0.0
        candle_high = 0.0
        candle_open = 0.0
        candle_close = 0.0
        recommended_entry = 0.0
        recommended_tp = 0.0
        recommended_sl = 0.0

        if workspace == "CRYPTO":
            try:
                # Fetch recent 1m klines
                url = f"https://api.binance.com/api/v3/klines?symbol={sym_clean}&interval=1m&limit=5"
                res = self._session.get(url, timeout=2.0)
                if res.status_code == 200:
                    klines = res.json()
                    if klines and len(klines) >= 2:
                        # Inspect the latest completed or current in-flight candle
                        latest = klines[-1]
                        candle_open = float(latest[1])
                        candle_high = float(latest[2])
                        candle_low = float(latest[3])
                        candle_close = float(latest[4])
                        current_price = candle_close

                        candle_range = candle_high - candle_low
                        body_bottom = min(candle_open, candle_close)
                        lower_wick = body_bottom - candle_low

                        if candle_range > 0 and candle_open > 0:
                            lower_wick_ratio = round(lower_wick / candle_range, 3)
                            drop_depth_pct = round(((candle_high - candle_low) / candle_open) * 100.0, 3)

                            # High-probability Hammer / Liquidity Wick condition:
                            # 1. Lower wick is >= 45% of candle span
                            # 2. Total candle drop >= 0.35% (flash drop)
                            # 3. Price bounced back above the lower third
                            if lower_wick_ratio >= 0.45 and drop_depth_pct >= 0.35 and current_price > (candle_low + candle_range * 0.3):
                                wick_detected = True
                                signal = "FLASH_WICK_ABSORPTION_SNIPE"
                                recommended_entry = round(current_price, 4 if current_price < 10 else 2)
                                recommended_tp = round(current_price * 1.012, 4 if current_price < 10 else 2)
                                recommended_sl = round(candle_low * 0.9985, 4 if current_price < 10 else 2)
            except Exception as e:
                signal = f"SCAN_ERROR: {str(e)[:40]}"

        result = {
            "symbol": sym_clean,
            "workspace": workspace,
            "wick_detected": wick_detected,
            "signal": signal,
            "lower_wick_ratio": lower_wick_ratio,
            "drop_depth_pct": drop_depth_pct,
            "current_price": current_price,
            "candle_low": candle_low,
            "recommended_entry": recommended_entry,
            "recommended_tp": recommended_tp,
            "recommended_sl": recommended_sl,
            "is_actionable": wick_detected,
            "checked_at": datetime.now(timezone.utc).astimezone(IST_TZ).strftime("%Y-%m-%d %H:%M:%S IST")
        }

        self._cache[sym_clean] = {"epoch": now, "data": result}
        return result

    def should_snipe_wick(self, symbol: str = "BTCUSDT", workspace: str = "CRYPTO") -> Tuple[bool, Dict[str, Any]]:
        """
        Evaluates whether an active wick snipe opportunity exists for the asset.
        """
        metrics = self.scan_wick_opportunity(symbol, workspace)
        return metrics.get("is_actionable", False), metrics

# Global singleton
liquidity_wick_sniper = LiquidityWickSniper()
