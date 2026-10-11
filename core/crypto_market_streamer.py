"""
Aegis-Quant Real-Time Public Crypto Market Data Streamer.
Maintains a resilient, server-side WebSocket connection to Binance Public Streams:
  - Multi-ticker & 24h stats (!miniTicker@arr and @ticker)
  - Real-time kline candle formation (@kline_<interval>)
  - Telemetry lifecycle: source event timestamp, server receipt timestamp, display timestamp
  - Truthful status tracking: LIVE | STALE | RECONNECTING | DISCONNECTED
Requires ZERO private trading API keys.
"""

import asyncio
import json
import time
import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timezone, timedelta

logger = logging.getLogger("crypto_market_streamer")
IST_TZ = timezone(timedelta(hours=5, minutes=30))

STREAM_URL = (
    "wss://stream.binance.com:9443/stream?streams="
    "!miniTicker@arr/"
    "btcusdt@ticker/ethusdt@ticker/solusdt@ticker/bnbusdt@ticker/adausdt@ticker/"
    "btcusdt@kline_1m/btcusdt@kline_5m/btcusdt@kline_15m/btcusdt@kline_1h/btcusdt@kline_4h/btcusdt@kline_1d/"
    "ethusdt@kline_1h/solusdt@kline_1h/bnbusdt@kline_1h"
)

STALE_THRESHOLD_SECONDS = 5.0
DISCONNECTED_THRESHOLD_SECONDS = 30.0


def _ist_str(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=IST_TZ).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3] + " IST"


class CryptoMarketStreamer:
    """
    Authoritative server-side streaming client for Binance public market data.
    Consolidated upstream feed to prevent redundant browser connections and guarantee
    observable real-time market telemetry.
    """

    def __init__(self):
        self._is_running: bool = False
        self._connection_state: str = "DISCONNECTED"  # DISCONNECTED | CONNECTING | LIVE | RECONNECTING
        self._last_event_ts: float = 0.0
        self._last_source_ts: float = 0.0
        self._event_count: int = 0
        self._reconnect_count: int = 0
        self._last_error: str = ""

        # Symbol -> latest ticker payload
        self._tickers: Dict[str, Dict[str, Any]] = {}
        # (Symbol, Interval) -> latest active kline candle
        self._active_candles: Dict[Tuple[str, str], Dict[str, Any]] = {}
        # Reference to broadcast callback
        self._broadcast_callback = None
        self._task: Optional[asyncio.Task] = None

    def set_broadcast_callback(self, callback):
        """Register callback function to broadcast to connected WebSocket clients."""
        self._broadcast_callback = callback

    def start(self):
        """Start the background streaming worker."""
        if not self._is_running:
            self._is_running = True
            self._task = asyncio.create_task(self._run_loop())

    def stop(self):
        """Stop the background worker."""
        self._is_running = False
        if self._task and not self._task.done():
            self._task.cancel()
        self._connection_state = "DISCONNECTED"

    async def _run_loop(self):
        """Main resilient connection loop with exponential backoff."""
        import websockets

        backoff = 1.0
        while self._is_running:
            try:
                self._connection_state = "CONNECTING"
                logger.info(f"[STREAMER] Connecting to Binance public stream: {STREAM_URL[:50]}...")
                async with websockets.connect(
                    STREAM_URL,
                    ping_interval=20,
                    ping_timeout=10,
                    close_timeout=5
                ) as ws:
                    self._connection_state = "LIVE"
                    backoff = 1.0
                    logger.info("[STREAMER] Connected to Binance public market stream!")

                    while self._is_running:
                        msg_str = await ws.recv()
                        await self._handle_message(msg_str)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self._last_error = str(e)
                self._connection_state = "RECONNECTING"
                self._reconnect_count += 1
                logger.warning(f"[STREAMER] Connection error: {e}. Reconnecting in {backoff}s...")
                await asyncio.sleep(backoff)
                backoff = min(backoff * 1.5, 10.0)

    async def _handle_message(self, msg_str: str):
        """Process incoming Binance stream event."""
        now = time.time()
        self._last_event_ts = now
        self._event_count += 1

        try:
            data = json.loads(msg_str)
            stream_name = data.get("stream", "")
            payload = data.get("data", {})

            # 1. Mini-ticker Array (!miniTicker@arr)
            if "!miniTicker" in stream_name and isinstance(payload, list):
                for item in payload:
                    sym = item.get("s", "").upper()
                    cur_p = float(item.get("c", 0.0))
                    open_p = float(item.get("o", 0.0))
                    high_p = float(item.get("h", 0.0))
                    low_p = float(item.get("l", 0.0))
                    vol = float(item.get("v", 0.0))
                    event_ts = float(item.get("E", int(now * 1000))) / 1000.0

                    if cur_p > 0:
                        change_24h = round(((cur_p - open_p) / open_p) * 100.0, 2) if open_p > 0 else 0.0
                        self._update_symbol_tick(
                            sym=sym,
                            price=cur_p,
                            change_24h=change_24h,
                            open_price=open_p,
                            high_price=high_p,
                            low_price=low_p,
                            volume=vol,
                            source_ts=event_ts,
                            recv_ts=now,
                        )

            # 2. Individual Symbol Ticker (@ticker)
            elif "@ticker" in stream_name:
                sym = payload.get("s", "").upper()
                cur_p = float(payload.get("c", 0.0))
                change_pct = float(payload.get("P", 0.0))
                open_p = float(payload.get("o", 0.0))
                high_p = float(payload.get("h", 0.0))
                low_p = float(payload.get("l", 0.0))
                vol = float(payload.get("v", 0.0))
                event_ts = float(payload.get("E", int(now * 1000))) / 1000.0

                if cur_p > 0:
                    self._update_symbol_tick(
                        sym=sym,
                        price=cur_p,
                        change_24h=change_pct,
                        open_price=open_p,
                        high_price=high_p,
                        low_price=low_p,
                        volume=vol,
                        source_ts=event_ts,
                        recv_ts=now,
                    )
                    # Broadcast tick
                    if self._broadcast_callback:
                        await self._broadcast_callback({
                            "event_type": "MARKET_TICK",
                            "symbol": sym,
                            "price": cur_p,
                            "change_24h": change_pct,
                            "source_time": _ist_str(event_ts),
                            "recv_time": _ist_str(now),
                            "source": "BINANCE_PUBLIC_STREAM",
                            "status": "LIVE"
                        })

            # 3. Kline Candle Update (@kline_<interval>)
            elif "@kline" in stream_name:
                sym = payload.get("s", "").upper()
                k = payload.get("k", {})
                interval = k.get("i", "1h")
                c_start = int(k.get("t", 0)) // 1000  # seconds
                c_open = float(k.get("o", 0.0))
                c_high = float(k.get("h", 0.0))
                c_low = float(k.get("l", 0.0))
                c_close = float(k.get("c", 0.0))
                c_vol = float(k.get("v", 0.0))
                is_closed = bool(k.get("x", False))
                event_ts = float(payload.get("E", int(now * 1000))) / 1000.0

                candle_record = {
                    "time": c_start,
                    "open": c_open,
                    "high": c_high,
                    "low": c_low,
                    "close": c_close,
                    "volume": c_vol,
                    "is_closed": is_closed,
                    "source_ts": event_ts,
                    "recv_ts": now,
                    "updated_at": _ist_str(now)
                }
                self._active_candles[(sym, interval)] = candle_record

                # Broadcast live candle update to chart clients
                if self._broadcast_callback:
                    await self._broadcast_callback({
                        "event_type": "KLINE_UPDATE",
                        "symbol": sym,
                        "interval": interval,
                        "candle": {
                            "time": c_start,
                            "open": c_open,
                            "high": c_high,
                            "low": c_low,
                            "close": c_close,
                            "volume": c_vol
                        },
                        "is_closed": is_closed,
                        "source_time": _ist_str(event_ts),
                        "recv_time": _ist_str(now),
                        "source": "BINANCE_PUBLIC_STREAM",
                        "status": "LIVE"
                    })

        except Exception as e:
            logger.debug(f"[STREAMER] Parse error: {e}")

    def _update_symbol_tick(
        self,
        sym: str,
        price: float,
        change_24h: float,
        open_price: float,
        high_price: float,
        low_price: float,
        volume: float,
        source_ts: float,
        recv_ts: float,
    ):
        """Update in-memory state and watchdog."""
        self._last_source_ts = max(self._last_source_ts, source_ts)
        self._tickers[sym] = {
            "symbol": sym,
            "price": price,
            "change_24h": change_24h,
            "open_price": open_price,
            "high_price": high_price,
            "low_price": low_price,
            "volume": volume,
            "source_ts": source_ts,
            "recv_ts": recv_ts,
            "source_time": _ist_str(source_ts),
            "recv_time": _ist_str(recv_ts),
            "source": "BINANCE_PUBLIC_STREAM",
        }
        # Feed watchdog
        try:
            from core.market_data_watchdog import market_data_watchdog
            market_data_watchdog.record_tick(
                symbol=sym,
                price=price,
                received_at=recv_ts,
                source_ts=source_ts
            )
        except Exception:
            pass

    def get_tick(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetch latest tick for symbol."""
        clean = symbol.replace("/", "").replace("-", "").upper()
        if clean in ["BTC", "ETH", "SOL", "BNB"]:
            clean = f"{clean}USDT"
        return self._tickers.get(clean)

    def get_active_candle(self, symbol: str, interval: str) -> Optional[Dict[str, Any]]:
        """Fetch active unclosed candle for symbol and interval."""
        clean = symbol.replace("/", "").replace("-", "").upper()
        if clean in ["BTC", "ETH", "SOL", "BNB"]:
            clean = f"{clean}USDT"
        return self._active_candles.get((clean, interval))

    def get_status(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """Compute authoritative telemetry status with distinct source and receive metrics."""
        now = time.time()
        target_sym = (symbol or "BTCUSDT").replace("/", "").replace("-", "").upper()
        sym_tick = self.get_tick(target_sym)

        # Upstream exchange source timestamp ('E' field from Binance)
        sym_source_ts = sym_tick.get("source_ts", self._last_source_ts) if sym_tick else self._last_source_ts
        # Local backend packet receipt timestamp
        sym_recv_ts = sym_tick.get("recv_ts", self._last_event_ts) if sym_tick else self._last_event_ts

        # Time bases:
        # source_age: seconds elapsed since upstream exchange emitted the market tick
        # recv_age: seconds elapsed since backend received the packet from upstream WebSocket
        source_age = round(max(0.0, now - sym_source_ts), 2) if sym_source_ts > 0 else 9999.0
        recv_age = round(max(0.0, now - sym_recv_ts), 2) if sym_recv_ts > 0 else 9999.0

        # Authoritative freshness check: MUST be based on genuine upstream source event age!
        # Never report LIVE solely because a recent application heartbeat/packet was received.
        effective_age = source_age

        if self._connection_state == "LIVE":
            if effective_age <= STALE_THRESHOLD_SECONDS:
                computed_state = "LIVE"
            elif effective_age <= DISCONNECTED_THRESHOLD_SECONDS:
                computed_state = "STALE"
            else:
                computed_state = "DISCONNECTED"
        else:
            computed_state = self._connection_state

        canonical_source_str = _ist_str(sym_source_ts) if sym_source_ts > 0 else "NONE"
        canonical_recv_str = _ist_str(sym_recv_ts) if sym_recv_ts > 0 else "NONE"

        return {
            "connection_state": computed_state,
            "feed_status": computed_state,
            "stream_connected": (self._connection_state == "LIVE"),
            "provider": "BINANCE_PUBLIC_STREAM",
            "time_basis": "UTC_EPOCH_CONVERTED_TO_IST",
            "source_event_time_ist": canonical_source_str,
            "server_recv_time_ist": canonical_recv_str,
            "last_event_time_ist": canonical_source_str,
            "last_source_time_ist": canonical_source_str,
            "event_age_seconds": effective_age,
            "source_age_seconds": source_age,
            "recv_age_seconds": recv_age,
            "events_received": self._event_count,
            "reconnect_count": self._reconnect_count,
            "symbol": target_sym,
            "symbol_price": sym_tick.get("price") if sym_tick else None,
            "symbol_change_24h": sym_tick.get("change_24h") if sym_tick else None,
            "tracked_symbols_count": len(self._tickers),
        }


# Global singleton
crypto_market_streamer = CryptoMarketStreamer()
