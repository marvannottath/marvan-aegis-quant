"""
Aegis-Quant Top-Gainer & High-Volume Multi-Asset Momentum Screener.
Continuously scans the global cryptocurrency universe on Binance:
  - Filters all liquid USDT pairs with 24h volume >= $20,000,000 USDT.
  - Excludes stablecoin-to-stablecoin pairs (e.g. USDC, FDUSD, DAI).
  - Ranks by Composite Momentum Score (Price Velocity + Volume Weight).
  - Automatically identifies highest-alpha momentum candidates to maximize portfolio returns.
"""

import time
import requests
from typing import Dict, Any, List
from datetime import datetime, timezone, timedelta

IST_TZ = timezone(timedelta(hours=5, minutes=30))

STABLECOIN_BASES = {
    "USDC", "FDUSD", "TUSD", "BUSD", "EUR", "DAI", "USDP", "AEUR", "USDE"
}

class MultiAssetMomentumScreener:
    def __init__(self):
        self._cache: Dict[str, Any] = {}
        self._cache_ttl_sec: float = 15.0
        self._session = requests.Session()

    def get_top_momentum_assets(self, limit: int = 8) -> Dict[str, Any]:
        """
        Scans all 24h tickers and returns top institutional momentum candidates.
        """
        now = time.time()
        if self._cache and (now - self._cache.get("epoch", 0)) < self._cache_ttl_sec:
            return self._cache["data"]

        candidates = []
        try:
            url = "https://api.binance.com/api/v3/ticker/24hr"
            res = self._session.get(url, timeout=3.5)
            if res.status_code == 200:
                tickers = res.json()
                for t in tickers:
                    sym = t.get("symbol", "")
                    if not sym.endswith("USDT"):
                        continue

                    base = sym[:-4]
                    if base in STABLECOIN_BASES:
                        continue

                    quote_vol = float(t.get("quoteVolume", 0.0))
                    # Only liquid institutional instruments ($20M+ 24h volume)
                    if quote_vol < 20_000_000.0:
                        continue

                    price_change_pct = float(t.get("priceChangePercent", 0.0))
                    last_price = float(t.get("lastPrice", 0.0))
                    high_price = float(t.get("highPrice", 0.0))
                    low_price = float(t.get("lowPrice", 0.0))

                    # Momentum classification
                    if 3.0 <= price_change_pct <= 12.0:
                        status = "PRIME_MOMENTUM_RUNNER"
                    elif price_change_pct > 12.0:
                        status = "OVEREXTENDED_HIGH_VOL"
                    elif 1.2 <= price_change_pct < 3.0:
                        status = "BREAKOUT_CANDIDATE"
                    else:
                        status = "CONSOLIDATION_WATCH"

                    # Composite score: price change with logarithmic volume weighting
                    vol_score = min(5.0, (quote_vol / 50_000_000.0))
                    composite_score = round(price_change_pct + vol_score, 2)

                    candidates.append({
                        "symbol": sym,
                        "base_asset": base,
                        "price": last_price,
                        "price_change_pct": round(price_change_pct, 2),
                        "quote_volume_usd": round(quote_vol, 2),
                        "high_24h": high_price,
                        "low_24h": low_price,
                        "composite_score": composite_score,
                        "status": status,
                        "is_favorable": status in ("PRIME_MOMENTUM_RUNNER", "BREAKOUT_CANDIDATE")
                    })

                # Sort descending by composite score
                candidates.sort(key=lambda x: x["composite_score"], reverse=True)
        except Exception as e:
            candidates = [{"error": str(e)[:60]}]

        top_candidates = candidates[:limit]

        result = {
            "screener_name": "INSTITUTIONAL_MULTI_ASSET_MOMENTUM",
            "total_screened_eligible": len(candidates),
            "top_limit": limit,
            "top_assets": top_candidates,
            "screened_at": datetime.now(timezone.utc).astimezone(IST_TZ).strftime("%Y-%m-%d %H:%M:%S IST")
        }

        self._cache = {"epoch": now, "data": result}
        return result

# Global singleton
multi_asset_momentum_screener = MultiAssetMomentumScreener()
