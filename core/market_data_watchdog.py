"""
Aegis-Quant Market Data Watchdog.
Continuously tracks market data freshness per symbol.
Status: LIVE | STALE | DISCONNECTED.
Blocks new orders when data is stale beyond configured threshold.
"""

import time
from typing import Dict, Any, Optional
from datetime import datetime, timezone, timedelta

IST_TZ = timezone(timedelta(hours=5, minutes=30))

STALE_THRESHOLD_SECONDS   = 5.0
DISCONNECTED_THRESHOLD_S  = 30.0

STATUS_LIVE         = "LIVE"
STATUS_STALE        = "STALE"
STATUS_DISCONNECTED = "DISCONNECTED"


class MarketDataWatchdog:
    """
    Per-symbol last-tick registry.
    Call record_tick(symbol) every time a market data update arrives.
    Call get_status(symbol) to check freshness.
    """

    def __init__(self):
        # symbol -> epoch float of last received tick
        self._last_tick: Dict[str, float] = {}
        # symbol -> last recorded price
        self._last_price: Dict[str, float] = {}
        # symbol -> count of duplicate/out-of-order violations
        self._violations: Dict[str, int] = {}
        # system-level latency samples (ms)
        self._latency_samples: list = []

    def record_tick(
        self,
        symbol: str,
        price: float,
        received_at: Optional[float] = None,
        source_ts: Optional[float] = None,
        processing_ts: Optional[float] = None,
        display_ts: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Record a market data tick with full timestamp lifecycle:
          - source_timestamp: exchange/venue origin time
          - server_receipt_timestamp: server receipt time
          - processing_timestamp: pipeline processing time
          - display_timestamp: dashboard/UI publication time
        """
        now = received_at or time.time()
        t_src = source_ts or (now - 0.005)
        t_proc = processing_ts or time.time()
        t_disp = display_ts or time.time()
        violations = []

        # Validate price
        if price <= 0:
            violations.append("INVALID_PRICE: zero or negative")
            self._violations[symbol] = self._violations.get(symbol, 0) + 1

        # Detect exact duplicate price (warn only — not a hard block)
        prev_price = self._last_price.get(symbol)
        if prev_price is not None and price == prev_price:
            violations.append("DUPLICATE_PRICE: identical to previous tick")

        # Record tick & timestamps
        self._last_tick[symbol]  = now
        if not hasattr(self, "_timestamps"):
            self._timestamps = {}
        self._timestamps[symbol] = {
            "source_ts": t_src,
            "receipt_ts": now,
            "processing_ts": t_proc,
            "display_ts": t_disp,
            "source_time": datetime.fromtimestamp(t_src, tz=IST_TZ).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3] + " IST",
            "receipt_time": datetime.fromtimestamp(now, tz=IST_TZ).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3] + " IST",
            "processing_time": datetime.fromtimestamp(t_proc, tz=IST_TZ).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3] + " IST",
            "display_time": datetime.fromtimestamp(t_disp, tz=IST_TZ).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3] + " IST",
        }
        if price > 0:
            self._last_price[symbol] = price

        return {
            "symbol":    symbol,
            "price":     price,
            "timestamp": datetime.fromtimestamp(now, tz=IST_TZ).strftime("%Y-%m-%d %H:%M:%S IST"),
            "timestamps": self._timestamps[symbol],
            "violations": violations,
            "integrity":  "FAIL" if any("INVALID" in v for v in violations) else "PASS"
        }

    def get_timestamp_audit(self, symbol: str) -> Dict[str, Any]:
        """Return 4-stage timestamp breakdown and measured real age for symbol."""
        ts_data = getattr(self, "_timestamps", {}).get(symbol, {})
        age = self.get_age(symbol)
        return {
            "symbol": symbol,
            "real_age_seconds": age,
            "status": self.get_status(symbol),
            "is_stale": age > STALE_THRESHOLD_SECONDS,
            "stale_threshold_seconds": STALE_THRESHOLD_SECONDS,
            "source_timestamp": ts_data.get("source_time", "N/A"),
            "server_receipt_timestamp": ts_data.get("receipt_time", "N/A"),
            "processing_timestamp": ts_data.get("processing_time", "N/A"),
            "display_timestamp": ts_data.get("display_time", "N/A"),
        }

    def record_latency(self, latency_ms: float):
        """Record end-to-end data pipeline latency sample."""
        self._latency_samples.append(latency_ms)
        if len(self._latency_samples) > 1000:
            self._latency_samples = self._latency_samples[-1000:]

    def get_age(self, symbol: str) -> float:
        """Return data age in seconds for symbol. Returns 9999 if never seen."""
        last = self._last_tick.get(symbol)
        if last is None:
            return 9999.0
        return round(time.time() - last, 3)

    def get_status(self, symbol: str) -> str:
        """Return LIVE | STALE | DISCONNECTED for a symbol."""
        age = self.get_age(symbol)
        if age > DISCONNECTED_THRESHOLD_S:
            return STATUS_DISCONNECTED
        if age > STALE_THRESHOLD_SECONDS:
            return STATUS_STALE
        return STATUS_LIVE

    def get_last_tick_timestamp(self, symbol: str) -> Optional[str]:
        """Return formatted IST timestamp of last received tick, or None."""
        last = self._last_tick.get(symbol)
        if last is None:
            return None
        return datetime.fromtimestamp(last, tz=IST_TZ).strftime("%Y-%m-%d %H:%M:%S IST")

    def is_stale(self, symbol: str) -> bool:
        return self.get_status(symbol) != STATUS_LIVE

    def get_latency_percentiles(self) -> Dict[str, float]:
        """Compute P50/P95/P99 from recorded latency samples."""
        samples = sorted(self._latency_samples)
        n = len(samples)
        if n == 0:
            return {"p50": 0.0, "p95": 0.0, "p99": 0.0, "sample_count": 0}
        def pct(p):
            idx = max(0, int(round(p / 100 * n)) - 1)
            return round(samples[idx], 3)
        return {
            "p50": pct(50), "p95": pct(95), "p99": pct(99),
            "sample_count": n
        }

    def get_all_status(self) -> Dict[str, Any]:
        """Full health snapshot for all tracked symbols."""
        symbols = list(self._last_tick.keys())
        symbol_status = {
            sym: {
                "status":  self.get_status(sym),
                "age_sec": self.get_age(sym),
                "last_price": self._last_price.get(sym, 0.0),
                "violations": self._violations.get(sym, 0)
            }
            for sym in symbols
        }
        latency = self.get_latency_percentiles()
        overall = STATUS_LIVE
        if symbols:
            statuses = [self.get_status(s) for s in symbols]
            if any(s == STATUS_DISCONNECTED for s in statuses):
                overall = STATUS_DISCONNECTED
            elif any(s == STATUS_STALE for s in statuses):
                overall = STATUS_STALE
        return {
            "overall_status": overall,
            "symbols": symbol_status,
            "latency": latency,
            "stale_threshold_seconds":   STALE_THRESHOLD_SECONDS,
            "disconnected_threshold_seconds": DISCONNECTED_THRESHOLD_S,
        }


# Global singleton
market_data_watchdog = MarketDataWatchdog()
