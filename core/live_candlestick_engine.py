"""
Guaranteed Live Candlestick & Tick Streamer for Gold Spot (XAUUSD).
Connects to Real Market Exchange feeds with live tick streaming.
"""

from typing import Dict, List, Any
from core.live_data_feed import real_live_feed

class LiveCandlestickEngine:
    def __init__(self):
        pass

    def get_candlesticks(self, ticker: str = "XAUUSD") -> List[Dict[str, Any]]:
        """Fetch latest real market candlestick history with live tick updates."""
        clean_ticker = ticker.split("=")[0].strip() if ticker else "XAUUSD"
        return real_live_feed.fetch_real_candlesticks(clean_ticker=clean_ticker, count=40)

# Singleton Candlestick Engine
candlestick_engine = LiveCandlestickEngine()
