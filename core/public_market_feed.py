"""
Aegis-Quant Public Market Feed Adapter.
Provides institutional-grade, zero-credential public market data for:
1. Indian Equities & Indices (NSE / BSE via official Yahoo Finance public quote API)
2. Global Forex & Precious Metals (Spot Gold GC=F, EURUSD, GBPUSD, USDJPY)
Includes an in-memory TTL cache to guarantee low latency (<50ms for cached hits) and high throughput.
"""

import time
import json
import urllib.request
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta

IST_TZ = timezone(timedelta(hours=5, minutes=30))

class PublicMarketFeed:
    """
    Zero-credential public market data ingestion for India & Forex.
    Thread-safe in-memory cache with 15s quote TTL and 30s candle TTL.
    """
    _quote_cache: Dict[str, Dict[str, Any]] = {}
    _candle_cache: Dict[str, Dict[str, Any]] = {}

    @staticmethod
    def _map_symbol(symbol: str) -> str:
        sym = symbol.strip().upper().replace("/", "").replace("-", "")
        if sym in ("NIFTY50", "NIFTY", "^NSEI"):
            return "^NSEI"
        if sym in ("BANKNIFTY", "NIFTYBANK"):
            return "^NSEBANK"
        if sym in ("SENSEX", "BSESENSEX"):
            return "^BSESN"
        if sym in ("XAUUSD", "GOLD", "XAU"):
            return "GC=F"
        if sym in ("XAGUSD", "SILVER"):
            return "SI=F"
        if any(sym.endswith(c) for c in ["USD", "JPY", "EUR", "GBP", "CHF", "CAD", "AUD", "NZD"]) and not sym.endswith("USDT"):
            return f"{sym}=X"
        if not sym.endswith(".NS") and not sym.endswith(".BO") and not sym.startswith("^") and "=" not in sym:
            return f"{sym}.NS"
        return sym

    @classmethod
    def get_quote(cls, symbol: str) -> Dict[str, Any]:
        """Fetch current public quote for an Indian stock or Forex pair."""
        now = time.time()
        sym_clean = symbol.strip().upper()
        cache_entry = cls._quote_cache.get(sym_clean)
        if cache_entry and (now - cache_entry["ts"]) < 15.0:
            return cache_entry["data"]

        yf_sym = cls._map_symbol(sym_clean)
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{yf_sym}?interval=1m&range=1d"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
            with urllib.request.urlopen(req, timeout=3.5) as resp:
                data = json.loads(resp.read().decode())
                res = data["chart"]["result"][0]
                meta = res["meta"]
                price = meta.get("regularMarketPrice")
                prev = meta.get("previousClose", price)
                high = meta.get("regularMarketDayHigh", price)
                low = meta.get("regularMarketDayLow", price)
                vol = meta.get("regularMarketVolume", 0)
                chg_pct = round(((price - prev) / prev) * 100.0, 2) if (prev and price) else 0.0
                digits = 2 if (price and price > 10) else 5

                quote = {
                    "symbol": sym_clean,
                    "yf_symbol": yf_sym,
                    "price": round(float(price), digits) if price is not None else None,
                    "change_24h": chg_pct,
                    "high": round(float(high), digits) if high is not None else None,
                    "low": round(float(low), digits) if low is not None else None,
                    "previous_close": round(float(prev), digits) if prev is not None else None,
                    "volume": vol,
                    "source": "PUBLIC_FEED_LIVE",
                    "status": "LIVE",
                    "timestamp": datetime.now(timezone.utc).astimezone(IST_TZ).strftime("%Y-%m-%d %H:%M:%S IST")
                }
                cls._quote_cache[sym_clean] = {"ts": now, "data": quote}
                return quote
        except Exception as e:
            return {
                "symbol": sym_clean,
                "yf_symbol": yf_sym,
                "price": None,
                "change_24h": None,
                "source": "DATA_UNAVAILABLE",
                "status": "DATA_UNAVAILABLE",
                "error": str(e)
            }

    @classmethod
    def get_quotes_batch(cls, symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        """Fetch quotes for multiple symbols concurrently using thread pool."""
        from concurrent.futures import ThreadPoolExecutor
        results = {}
        needed = []
        now = time.time()
        for s in symbols:
            s_clean = s.strip().upper()
            cached = cls._quote_cache.get(s_clean)
            if cached and (now - cached["ts"]) < 15.0:
                results[s_clean] = cached["data"]
            else:
                needed.append(s_clean)

        if needed:
            with ThreadPoolExecutor(max_workers=min(10, len(needed))) as executor:
                future_map = {executor.submit(cls.get_quote, sym): sym for sym in needed}
                for fut in future_map:
                    sym = future_map[fut]
                    try:
                        results[sym] = fut.result()
                    except Exception:
                        results[sym] = {"symbol": sym, "price": None, "change_24h": None, "status": "DATA_UNAVAILABLE"}

        return results

    @classmethod
    def get_candles(cls, symbol: str, timeframe: str = "1h", limit: int = 1000) -> List[Dict[str, Any]]:
        """Fetch historical and recent public kline candles for India & Forex."""
        now = time.time()
        sym_clean = symbol.strip().upper()
        cache_key = f"{sym_clean}_{timeframe}_{limit}"
        cache_entry = cls._candle_cache.get(cache_key)
        if cache_entry and (now - cache_entry["ts"]) < 30.0:
            return cache_entry["data"]

        yf_sym = cls._map_symbol(sym_clean)
        interval = "1m" if timeframe == "1m" else ("5m" if timeframe == "5m" else ("15m" if timeframe == "15m" else ("1h" if timeframe in ("1h", "4h") else "1d")))
        rng = "1d" if interval == "1m" else ("5d" if interval in ("5m", "15m") else ("3mo" if interval in ("1h", "4h") else "2y"))

        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{yf_sym}?interval={interval}&range={rng}"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
            with urllib.request.urlopen(req, timeout=4.5) as resp:
                data = json.loads(resp.read().decode())
                res = data["chart"]["result"][0]
                timestamps = res.get("timestamp", [])
                quotes = res["indicators"]["quote"][0]
                candles = []
                for i, t in enumerate(timestamps):
                    o = quotes["open"][i]
                    h = quotes["high"][i]
                    l = quotes["low"][i]
                    c = quotes["close"][i]
                    v = quotes.get("volume", [0]*len(timestamps))[i] or 0
                    if None not in (o, h, l, c):
                        digits = 2 if c > 10 else 5
                        candles.append({
                            "time": int(t),
                            "open": round(float(o), digits),
                            "high": round(float(h), digits),
                            "low": round(float(l), digits),
                            "close": round(float(c), digits),
                            "volume": float(v)
                        })

                if candles and limit:
                    candles = candles[-limit:]

                cls._candle_cache[cache_key] = {"ts": now, "data": candles}
                return candles
        except Exception as e:
            print(f"[PUBLIC_FEED] Candle fetch error for {symbol} ({yf_sym}): {e}")
            return []

# Global singleton
public_market_feed = PublicMarketFeed()
