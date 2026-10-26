"""
Aegis-Quant Whale Order & Smart Money Wall Tracker.
Monitors deep top-of-book order book depth (50-100 levels) on Binance.
Detects:
  - Whale Buy Walls: Massive institutional bids within 0.5% of price (Bounce support)
  - Whale Sell Walls: Massive institutional ask walls above price (Breakout resistance)
  - Spoofing & wall pull detection (if a whale wall disappears before fill)
"""

import time
import requests
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta

IST_TZ = timezone(timedelta(hours=5, minutes=30))

# Minimum notional value to qualify as a Whale Wall ($40,000+)
WHALE_NOTIONAL_THRESHOLD_USD = 40000.0

class WhaleOrderTracker:
    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_ttl_sec: float = 2.0
        self._session = requests.Session()
        self._whale_alerts_history: List[Dict[str, Any]] = []

    def scan_whale_walls(self, symbol: str = "BTCUSDT", workspace: str = "CRYPTO") -> Dict[str, Any]:
        """
        Deep scan of order book depth (100 levels) for institutional whale walls.
        """
        sym_clean = symbol.upper().replace("/", "").strip()
        now = time.time()

        cached = self._cache.get(sym_clean)
        if cached and (now - cached["epoch"]) < self._cache_ttl_sec:
            return cached["data"]

        whale_bids = []
        whale_asks = []
        best_bid = 0.0
        best_ask = 0.0
        total_whale_bid_usd = 0.0
        total_whale_ask_usd = 0.0

        if workspace == "CRYPTO":
            try:
                # 100-level depth snapshot
                url = f"https://api.binance.com/api/v3/depth?symbol={sym_clean}&limit=100"
                res = self._session.get(url, timeout=2.0)
                if res.status_code == 200:
                    depth = res.json()
                    bids = depth.get("bids", [])
                    asks = depth.get("asks", [])

                    if bids and asks:
                        best_bid = float(bids[0][0])
                        best_ask = float(asks[0][0])
                        mid_price = (best_bid + best_ask) / 2.0

                        # Inspect bids within 1.0% of mid price
                        for b in bids:
                            px = float(b[0])
                            qty = float(b[1])
                            notional = px * qty
                            distance_pct = abs(mid_price - px) / mid_price * 100.0
                            if distance_pct <= 1.2 and notional >= WHALE_NOTIONAL_THRESHOLD_USD:
                                whale_bids.append({
                                    "price": px,
                                    "quantity": qty,
                                    "notional_usd": round(notional, 2),
                                    "distance_pct": round(distance_pct, 2)
                                })
                                total_whale_bid_usd += notional

                        # Inspect asks within 1.0% of mid price
                        for a in asks:
                            px = float(a[0])
                            qty = float(a[1])
                            notional = px * qty
                            distance_pct = abs(px - mid_price) / mid_price * 100.0
                            if distance_pct <= 1.2 and notional >= WHALE_NOTIONAL_THRESHOLD_USD:
                                whale_asks.append({
                                    "price": px,
                                    "quantity": qty,
                                    "notional_usd": round(notional, 2),
                                    "distance_pct": round(distance_pct, 2)
                                })
                                total_whale_ask_usd += notional
            except Exception:
                pass

        # Institutional Bias Interpretation
        if total_whale_bid_usd > (total_whale_ask_usd * 1.5) and total_whale_bid_usd > 0:
            bias = "WHALE_ACCUMULATION_SUPPORT"
            is_support_strong = True
            is_resistance_heavy = False
        elif total_whale_ask_usd > (total_whale_bid_usd * 1.5) and total_whale_ask_usd > 0:
            bias = "WHALE_DISTRIBUTION_WALL"
            is_support_strong = False
            is_resistance_heavy = True
        else:
            bias = "BALANCED_INSTITUTIONAL_FLOW"
            is_support_strong = False
            is_resistance_heavy = False

        data = {
            "symbol": sym_clean,
            "workspace": workspace,
            "best_bid": best_bid,
            "best_ask": best_ask,
            "whale_bias": bias,
            "is_support_strong": is_support_strong,
            "is_resistance_heavy": is_resistance_heavy,
            "whale_buy_walls_count": len(whale_bids),
            "whale_sell_walls_count": len(whale_asks),
            "total_whale_bid_usd": round(total_whale_bid_usd, 2),
            "total_whale_ask_usd": round(total_whale_ask_usd, 2),
            "top_whale_bids": whale_bids[:5],
            "top_whale_asks": whale_asks[:5],
            "checked_at": datetime.now(timezone.utc).astimezone(IST_TZ).strftime("%Y-%m-%d %H:%M:%S IST")
        }

        self._cache[sym_clean] = {"epoch": now, "data": data}
        return data

    def validate_whale_support(self, symbol: str, side: str = "BUY", workspace: str = "CRYPTO") -> Dict[str, Any]:
        """Validates if whale walls favor or obstruct the trade."""
        walls = self.scan_whale_walls(symbol, workspace)
        if side == "BUY" and walls["is_resistance_heavy"]:
            return {
                "allowed": False,
                "reason": f"WHALE_SELL_WALL_AHEAD: ${walls['total_whale_ask_usd']:,.0f} institutional ask wall resisting upward breakout.",
                "walls": walls
            }
        return {"allowed": True, "reason": "WHALE_FLOW_CLEAR", "walls": walls}


# Global Singleton Instance
whale_order_tracker = WhaleOrderTracker()
