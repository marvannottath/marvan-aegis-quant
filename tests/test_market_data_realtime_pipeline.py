"""
Aegis-Quant Real-Time Market Data Connectivity Test Suite.
Validates end-to-end streaming market data pipeline:
  1. Live Binance public stream ingestion without private broker keys.
  2. Timestamp lifecycle: source_ts, recv_ts, IST string formatting, and age tracking.
  3. Real-time OHLCV aggregation and active candle updates.
  4. Market isolation: Crypto (LIVE stream) vs India (DATA_UNAVAILABLE) vs Forex/Gold (DATA_UNAVAILABLE).
  5. Separation of public market data health from private broker account authorization.
  6. /api/market-data/status and /api/chart-history truthful telemetry.
"""

import unittest
import asyncio
import time
import requests
from datetime import datetime, timezone, timedelta

BACKEND_URL = "http://127.0.0.1:8888"
IST_TZ = timezone(timedelta(hours=5, minutes=30))


class TestMarketDataRealtimePipeline(unittest.TestCase):

    def test_01_crypto_streamer_instance_and_state(self):
        """Verify CryptoMarketStreamer initializes with valid configuration."""
        from core.crypto_market_streamer import crypto_market_streamer
        status = crypto_market_streamer.get_status("BTCUSDT")
        self.assertIn("connection_state", status)
        self.assertIn("provider", status)
        self.assertEqual(status["provider"], "BINANCE_PUBLIC_STREAM")

    def test_02_crypto_market_streamer_ingests_ticks(self):
        """Verify CryptoMarketStreamer processes real Binance events and updates ticks."""
        from core.crypto_market_streamer import crypto_market_streamer

        # Simulate receiving a real Binance ticker event
        event_ts = time.time()
        raw_msg = {
            "stream": "btcusdt@ticker",
            "data": {
                "s": "BTCUSDT",
                "c": "82550.00",
                "P": "0.15",
                "o": "82420.00",
                "h": "83100.00",
                "l": "81900.00",
                "v": "15000.5",
                "E": int(event_ts * 1000)
            }
        }
        asyncio.run(crypto_market_streamer._handle_message(json_dumps(raw_msg)))

        tick = crypto_market_streamer.get_tick("BTCUSDT")
        self.assertIsNotNone(tick)
        self.assertEqual(tick["price"], 82550.0)
        self.assertEqual(tick["change_24h"], 0.15)
        self.assertEqual(tick["source"], "BINANCE_PUBLIC_STREAM")
        self.assertIn("IST", tick["source_time"])

    def test_03_crypto_market_streamer_updates_kline(self):
        """Verify real-time kline candle updates aggregate correctly."""
        from core.crypto_market_streamer import crypto_market_streamer

        now_sec = int(time.time())
        c_time = (now_sec // 3600) * 3600
        raw_msg = {
            "stream": "btcusdt@kline_1h",
            "data": {
                "s": "BTCUSDT",
                "E": int(time.time() * 1000),
                "k": {
                    "t": c_time * 1000,
                    "o": "82400.0",
                    "h": "82650.0",
                    "l": "82350.0",
                    "c": "82580.0",
                    "v": "120.5",
                    "x": False,
                    "i": "1h"
                }
            }
        }
        asyncio.run(crypto_market_streamer._handle_message(json_dumps(raw_msg)))

        candle = crypto_market_streamer.get_active_candle("BTCUSDT", "1h")
        self.assertIsNotNone(candle)
        self.assertEqual(candle["time"], c_time)
        self.assertEqual(candle["close"], 82580.0)
        self.assertEqual(candle["high"], 82650.0)
        self.assertFalse(candle["is_closed"])

    def test_04_market_data_status_api_endpoint(self):
        """Verify /api/market-data/status returns canonical telemetry for CRYPTO."""
        r = requests.get(f"{BACKEND_URL}/api/market-data/status?workspace=CRYPTO&symbol=BTCUSDT", timeout=5)
        self.assertEqual(r.status_code, 200)
        d = r.json()
        self.assertEqual(d["status"], "SUCCESS")
        self.assertEqual(d["workspace"], "CRYPTO")
        self.assertEqual(d["symbol"], "BTCUSDT")
        self.assertIn(d["feed_status"], ["LIVE", "CONNECTING", "STALE", "DISCONNECTED"])
        self.assertEqual(d["provider"], "BINANCE_PUBLIC_STREAM")

    def test_05_india_market_feed_status_unconfigured(self):
        """Verify INDIA workspace returns valid feed_status (LIVE public feed or DATA_UNAVAILABLE when unconfigured)."""
        r = requests.get(f"{BACKEND_URL}/api/market-data/status?workspace=INDIA&symbol=RELIANCE", timeout=5)
        self.assertEqual(r.status_code, 200)
        d = r.json()
        self.assertEqual(d["status"], "SUCCESS")
        self.assertEqual(d["workspace"], "INDIA")
        self.assertIn(d["feed_status"], ["LIVE", "DATA_UNAVAILABLE", "STALE"])
        if d["feed_status"] == "DATA_UNAVAILABLE":
            self.assertIsNone(d["latest_price"])
            self.assertIn("UPSTOX_NOT_CONFIGURED", d["provider"])
        else:
            self.assertGreater(d.get("latest_price", 0), 0)

    def test_06_forex_market_feed_status_disconnected(self):
        """Verify FOREX_GOLD workspace returns valid feed_status (LIVE public feed or DATA_UNAVAILABLE when disconnected)."""
        r = requests.get(f"{BACKEND_URL}/api/market-data/status?workspace=FOREX_GOLD&symbol=XAUUSD", timeout=5)
        self.assertEqual(r.status_code, 200)
        d = r.json()
        self.assertEqual(d["status"], "SUCCESS")
        self.assertEqual(d["workspace"], "FOREX_GOLD")
        self.assertIn(d["feed_status"], ["LIVE", "DATA_UNAVAILABLE", "STALE"])
        if d["feed_status"] == "DATA_UNAVAILABLE":
            self.assertIsNone(d["latest_price"])
            self.assertIn("MT5_DISCONNECTED", d["provider"])
        else:
            self.assertGreater(d.get("latest_price", 0), 0)

    def test_07_chart_history_includes_stream_telemetry(self):
        """Verify /api/chart-history returns stream telemetry and genuine candles."""
        r = requests.get(
            f"{BACKEND_URL}/api/chart-history",
            params={"symbol": "BTCUSDT", "timeframe": "1h", "workspace": "CRYPTO"},
            timeout=5
        )
        self.assertEqual(r.status_code, 200)
        d = r.json()
        self.assertEqual(d["symbol"], "BTCUSDT")
        self.assertGreater(len(d.get("candles", [])), 0)
        self.assertIn("last_event_time_ist", d)
        self.assertIn("event_age_seconds", d)
        self.assertIn("market_data_status", d)
        self.assertIn("market_data_source", d)

    def test_08_market_scanner_truthful_nulls_for_india(self):
        """Verify /api/market-scanner returns valid asset data for India stocks."""
        r = requests.get(f"{BACKEND_URL}/api/market-scanner?workspace=INDIA", timeout=5)
        self.assertEqual(r.status_code, 200)
        d = r.json()
        assets = d.get("assets", [])
        self.assertGreater(len(assets), 0)
        first = assets[0]
        self.assertIn(first["status"], ["LIVE", "DATA_UNAVAILABLE"])

    def test_09_public_market_feed_isolated_from_private_broker_auth(self):
        """Verify public market feed health does NOT grant false private broker connectivity in LIVE."""
        # 1. Market feed status
        r_market = requests.get(f"{BACKEND_URL}/api/market-data/status?workspace=CRYPTO&symbol=BTCUSDT", timeout=5)
        self.assertEqual(r_market.status_code, 200)

        # 2. Private broker portfolio aggregate (LIVE CRYPTO)
        r_port = requests.get(
            f"{BACKEND_URL}/api/portfolio/aggregate",
            params={"environment": "LIVE", "workspace": "CRYPTO"},
            timeout=5
        )
        self.assertEqual(r_port.status_code, 200)
        d_port = r_port.json()

        # Public market feed may be connected, but private broker MUST remain disconnected
        self.assertFalse(d_port.get("broker_connected"))
        self.assertIsNone(d_port.get("total_equity"))
        self.assertIsNone(d_port.get("free_cash"))
        self.assertEqual(d_port.get("reconciliation_status"), "BROKER_DISCONNECTED")

    def test_10_timestamp_consistency_across_endpoints(self):
        """Verify /api/market-data/status and /api/chart-history return consistent time-basis and timestamps."""
        r_status = requests.get(f"{BACKEND_URL}/api/market-data/status?workspace=CRYPTO&symbol=BTCUSDT", timeout=5)
        r_chart = requests.get(f"{BACKEND_URL}/api/chart-history?symbol=BTCUSDT&timeframe=1h&workspace=CRYPTO", timeout=5)
        self.assertEqual(r_status.status_code, 200)
        self.assertEqual(r_chart.status_code, 200)

        d_status = r_status.json()
        d_chart = r_chart.json()

        # Both must expose explicit source vs recv metrics and documented time basis
        self.assertEqual(d_status.get("time_basis"), "UTC_EPOCH_CONVERTED_TO_IST")
        self.assertEqual(d_chart.get("time_basis"), "UTC_EPOCH_CONVERTED_TO_IST")
        self.assertIn("source_event_time_ist", d_status)
        self.assertIn("server_recv_time_ist", d_status)
        self.assertIn("source_event_time_ist", d_chart)
        self.assertIn("server_recv_time_ist", d_chart)

        # Telemetry age must be non-negative
        self.assertGreaterEqual(d_status["event_age_seconds"], 0.0)
        self.assertGreaterEqual(d_chart["event_age_seconds"], 0.0)

    def test_11_upstream_stale_detection_never_fooled_by_heartbeats(self):
        """Verify streamer reports STALE if source tick is stale, even if connection/frame is recent."""
        from core.crypto_market_streamer import CryptoMarketStreamer
        test_streamer = CryptoMarketStreamer()
        test_streamer._connection_state = "LIVE"

        now = time.time()
        # Stale exchange event (10 seconds ago)
        stale_source = now - 10.0
        # Fresh local receive frame (0.1 second ago)
        fresh_recv = now - 0.1

        test_streamer._update_symbol_tick(
            sym="BTCUSDT",
            price=82500.0,
            change_24h=0.1,
            open_price=82400.0,
            high_price=82600.0,
            low_price=82300.0,
            volume=100.0,
            source_ts=stale_source,
            recv_ts=fresh_recv,
        )

        st = test_streamer.get_status("BTCUSDT")
        # Must be STALE because source tick is 10s old, despite fresh recv frame!
        self.assertEqual(st["feed_status"], "STALE")
        self.assertGreater(st["event_age_seconds"], 5.0)


def json_dumps(obj):
    import json
    return json.dumps(obj)


if __name__ == "__main__":
    unittest.main()
