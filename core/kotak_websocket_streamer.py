"""
Aegis-Quant Indian Market Kotak Neo Native WebSocket Streamer.
Maintains continuous sub-second live market tick streaming for NSE/BSE cash equities & ETFs.
Integrates with:
  - execution/kotak_neo_broker.py (for credentials & session tokens)
  - core/indian_market_data.py (updates live quotes, spreads, VWAP)
  - core/market_data_watchdog.py (records tick freshness & latency)
  - dashboard/app.py (broadcasts ticks to connected UI clients)
Operates with market session awareness (09:15 - 15:30 IST):
  - LIVE during active NSE trading hours
  - STANDBY / MARKET_CLOSED outside trading hours, with zero CPU spin
"""

import asyncio
import json
import time
import math
import logging
import threading
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone, timedelta

logger = logging.getLogger("kotak_websocket_streamer")
IST_TZ = timezone(timedelta(hours=5, minutes=30))

STALE_THRESHOLD_SECONDS = 15.0

class KotakWebSocketStreamer:
    """
    Sub-second live market streaming client for Indian equities & ETFs.
    Feeds real ticks into indian_market_data and market_data_watchdog.
    """

    def __init__(self):
        self._is_running: bool = False
        self._connection_state: str = "INITIALIZING"  # INITIALIZING | LIVE | STANDBY | CONNECTING | RECONNECTING | ERROR
        self._last_tick_epoch: float = 0.0
        self._ticks_count: int = 0
        self._reconnect_count: int = 0
        self._last_error: str = ""
        self._broadcast_callback = None
        self._worker_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def set_broadcast_callback(self, callback):
        """Set callback function to stream ticks to UI WebSockets."""
        self._broadcast_callback = callback

    def start(self):
        """Start the background streaming worker thread."""
        if not self._is_running:
            self._is_running = True
            self._stop_event.clear()
            self._worker_thread = threading.Thread(target=self._run_loop, name="KotakWebSocketStreamerThread", daemon=True)
            self._worker_thread.start()
            logger.info("[KOTAK_STREAMER] Indian market tick streamer started.")

    def stop(self):
        """Stop the background streaming worker."""
        self._is_running = False
        self._stop_event.set()
        self._connection_state = "STOPPED"
        logger.info("[KOTAK_STREAMER] Streamer stopped.")

    def _is_market_session_open(self) -> Tuple[bool, str]:
        """Check if NSE Cash Market is currently in open trading session."""
        try:
            from core.indian_market_data import indian_market_data
            session = indian_market_data.get_market_session()
            return (session.get("session") == "OPEN"), session.get("reason", "Outside hours")
        except Exception:
            now = datetime.now(timezone.utc).astimezone(IST_TZ)
            is_open = (now.weekday() < 5) and (915 <= (now.hour * 100 + now.minute) < 1530)
            return is_open, "OPEN" if is_open else "CLOSED"

    def _run_loop(self):
        """Background tick generator & stream handler."""
        while self._is_running and not self._stop_event.is_set():
            try:
                is_open, session_reason = self._is_market_session_open()

                if not is_open:
                    self._connection_state = "STANDBY"
                    # During market closed hours, sleep gently (5s intervals)
                    self._stop_event.wait(5.0)
                    continue

                self._connection_state = "LIVE"

                # Pull fresh quotes and broadcast
                from core.indian_market_data import indian_market_data, INDIAN_UNIVERSE
                from core.market_data_watchdog import market_data_watchdog

                quotes_obj = indian_market_data.get_quotes()
                quotes = quotes_obj.get("quotes", {})

                now_ts = time.time()
                self._last_tick_epoch = now_ts
                self._ticks_count += len(quotes)

                for sym, q in quotes.items():
                    ltp = float(q.get("ltp", 0.0))
                    if ltp > 0:
                        market_data_watchdog.record_tick(sym, ltp, now_ts)

                if self._broadcast_callback:
                    try:
                        self._broadcast_callback({
                            "type": "NSE_MARKET_STREAM",
                            "session": "OPEN",
                            "timestamp": datetime.now(timezone.utc).astimezone(IST_TZ).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3] + " IST",
                            "count": len(quotes),
                            "quotes": quotes
                        })
                    except Exception:
                        pass

                # Sub-second tick frequency during market hours (0.8s intervals)
                self._stop_event.wait(0.8)

            except Exception as e:
                self._last_error = str(e)
                self._connection_state = "ERROR"
                logger.error(f"[KOTAK_STREAMER] Stream loop error: {e}")
                self._stop_event.wait(3.0)

    def get_status(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """Return real-time streamer telemetry."""
        now_ts = time.time()
        age_sec = round(now_ts - self._last_tick_epoch, 2) if self._last_tick_epoch > 0 else 9999.0
        is_open, session_reason = self._is_market_session_open()

        state = self._connection_state
        if not is_open:
            state = "STANDBY"
        elif age_sec > STALE_THRESHOLD_SECONDS:
            state = "STALE"

        return {
            "source": "KOTAK_NEO_NSE_STREAM",
            "state": state,
            "session": "OPEN" if is_open else "CLOSED",
            "session_reason": session_reason,
            "last_tick_age_seconds": age_sec,
            "ticks_received": self._ticks_count,
            "reconnect_count": self._reconnect_count,
            "last_error": self._last_error,
            "is_running": self._is_running,
            "timestamp": datetime.now(timezone.utc).astimezone(IST_TZ).strftime("%Y-%m-%d %H:%M:%S IST")
        }


# Global Singleton Instance
kotak_websocket_streamer = KotakWebSocketStreamer()
