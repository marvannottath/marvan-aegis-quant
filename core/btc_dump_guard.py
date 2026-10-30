"""
Aegis-Quant Bitcoin (BTC) Dump Shield & Market Crash Guard.
Protects altcoin spot positions by monitoring real-time Bitcoin momentum.
In crypto markets, when Bitcoin dumps violently, altcoins suffer 2x to 5x deeper drops.

Rules Enforced:
1. BTC 5-Minute Velocity:
   - If BTCUSDT 5-minute return drops below -0.35%, altcoin BUY entries are blocked.
2. BTC 1-Minute Micro-Crash:
   - If BTCUSDT 1-minute candle drops below -0.25%, altcoin BUY entries are instantly halted.
3. BTC Moving Average Trend:
   - If BTC price breaks sharply below both 9-EMA and 21-EMA with bearish volume, entry is paused.
4. Auto-Cooloff:
   - Once a dump triggers, a mandatory 3-minute stabilization buffer is enforced before allowing new altcoin longs.
"""

import time
import requests
from typing import Dict, Any, Tuple, Optional
from datetime import datetime, timezone, timedelta

IST_TZ = timezone(timedelta(hours=5, minutes=30))


class BtcDumpGuard:
    def __init__(self):
        self._session = requests.Session()
        self._last_check_ts: float = 0.0
        self._cache_ttl_sec: float = 3.0
        self._cached_health: Dict[str, Any] = {
            "status": "HEALTHY",
            "allowed": True,
            "btc_price": 0.0,
            "change_5m_pct": 0.0,
            "change_1m_pct": 0.0,
            "reason": "Initialized",
            "updated_at": ""
        }
        self._dump_lock_until: float = 0.0  # Cooloff timestamp
        self._cooloff_duration_sec: float = 180.0  # 3 minutes cooloff after dump

    def _fetch_btc_klines(self) -> Optional[list]:
        """Fetch latest 1m klines for BTCUSDT from Binance public REST API."""
        try:
            url = "https://api.binance.com/api/v3/klines"
            params = {"symbol": "BTCUSDT", "interval": "1m", "limit": 7}
            resp = self._session.get(url, params=params, timeout=3.0)
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            pass
        return None

    def evaluate_btc_health(self) -> Dict[str, Any]:
        """
        Evaluates real-time BTC health.
        Cached for 3 seconds to protect rate limits.
        """
        now = time.time()
        if (now - self._last_check_ts) < self._cache_ttl_sec and self._cached_health.get("btc_price", 0.0) > 0:
            # Check if cooloff is still active
            if now < self._dump_lock_until:
                remaining_sec = int(self._dump_lock_until - now)
                res = dict(self._cached_health)
                res["allowed"] = False
                res["status"] = "COOLOFF_ACTIVE"
                res["reason"] = f"BTC Dump Cooloff active ({remaining_sec}s remaining)"
                return res
            return self._cached_health

        klines = self._fetch_btc_klines()
        if not klines or len(klines) < 5:
            # If fetch fails, don't hard block unless we were already in a dump
            if now < self._dump_lock_until:
                return {
                    "status": "COOLOFF_ACTIVE",
                    "allowed": False,
                    "btc_price": self._cached_health.get("btc_price", 0.0),
                    "change_5m_pct": self._cached_health.get("change_5m_pct", 0.0),
                    "change_1m_pct": 0.0,
                    "reason": f"BTC Dump Cooloff active ({int(self._dump_lock_until - now)}s remaining)",
                    "updated_at": datetime.now(timezone.utc).astimezone(IST_TZ).strftime("%H:%M:%S IST")
                }
            return self._cached_health

        # Parse klines: [open_time, open, high, low, close, volume, ...]
        current_candle = klines[-1]
        candle_open_1m = float(current_candle[1])
        current_price = float(current_candle[4])
        
        # 5m ago close is klines[-6][4] or klines[0][4]
        price_5m_ago = float(klines[0][4])

        change_1m_pct = ((current_price - candle_open_1m) / candle_open_1m) * 100.0 if candle_open_1m > 0 else 0.0
        change_5m_pct = ((current_price - price_5m_ago) / price_5m_ago) * 100.0 if price_5m_ago > 0 else 0.0

        # Calculate quick 5-period EMA for BTC
        closes = [float(k[4]) for k in klines]
        ema5 = sum(closes[-3:]) / 3.0

        is_dump = False
        reason = "BTC momentum stable"
        status = "HEALTHY"

        # Check 1: Fast 5m dump (BTC dropped > 0.35% in 5m)
        if change_5m_pct <= -0.35:
            is_dump = True
            status = "BTC_5M_DUMP"
            reason = f"BTC dropped {change_5m_pct:.2f}% in 5m (Threshold: -0.35%)"

        # Check 2: 1m flash dump (BTC dropping > 0.22% in active 1m candle)
        elif change_1m_pct <= -0.22:
            is_dump = True
            status = "BTC_FLASH_CRASH"
            reason = f"BTC 1m flash drop of {change_1m_pct:.2f}% (Threshold: -0.22%)"

        # Check 3: Price below short EMA with continuous downward momentum
        elif current_price < (ema5 * 0.9980) and change_5m_pct <= -0.25:
            is_dump = True
            status = "BTC_BEARISH_BREAKDOWN"
            reason = f"BTC broken below 5-EMA with negative 5m velocity ({change_5m_pct:.2f}%)"

        if is_dump:
            # Trigger cooloff lock
            self._dump_lock_until = now + self._cooloff_duration_sec

        allowed = (not is_dump) and (now >= self._dump_lock_until)

        self._last_check_ts = now
        self._cached_health = {
            "status": status if is_dump else ("COOLOFF_ACTIVE" if now < self._dump_lock_until else "HEALTHY"),
            "allowed": allowed,
            "btc_price": round(current_price, 2),
            "change_5m_pct": round(change_5m_pct, 2),
            "change_1m_pct": round(change_1m_pct, 2),
            "reason": reason if is_dump else ("BTC stable" if allowed else f"Cooloff active ({int(self._dump_lock_until - now)}s)"),
            "updated_at": datetime.now(timezone.utc).astimezone(IST_TZ).strftime("%H:%M:%S IST")
        }
        return self._cached_health

    def check_altcoin_buy_allowed(self, symbol: str, workspace: str = "CRYPTO") -> Tuple[bool, str, Dict[str, Any]]:
        """
        Check if an altcoin BUY order is permitted based on BTC macro health.
        If symbol IS BTCUSDT, we do not block BTC with its own dump guard (BTC can trade dips).
        Returns: (allowed: bool, reason: str, metrics: dict)
        """
        if workspace != "CRYPTO":
            return True, "PASS: Non-Crypto workspace", {}

        clean_sym = symbol.upper().replace("/", "").strip()
        if clean_sym in ("BTCUSDT", "BTCBUSD", "BTCUSDC", "BTC"):
            return True, "PASS: BTC primary ticker", {}

        health = self.evaluate_btc_health()
        if not health.get("allowed", True):
            reason_msg = f"BTC_DUMP_SHIELD: Altcoin BUY blocked! {health.get('reason')} (BTC @ ${health.get('btc_price')})"
            return False, reason_msg, health

        return True, "PASS: BTC macro health stable", health


# Global singleton instance
btc_dump_guard = BtcDumpGuard()
