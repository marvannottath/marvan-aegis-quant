"""
Daily Strategy Sync Module.
Periodically fetches market sentiment, trending themes, and institutional macro data.
Aligns RL trading model weights with current human market behavior.
"""

import time
import logging
from datetime import datetime
from typing import Dict, Any
from sync.sentiment_analyzer import SentimentAnalyzer
from config.settings import FOREX_PAIRS, EQUITY_SECTORS

class DailyStrategySync:
    def __init__(self):
        self.sentiment_analyzer = SentimentAnalyzer()
        self.last_sync_time: str = ""
        self.current_alignment_score: float = 0.0
        self.sector_weights: Dict[str, float] = {}

    def run_sync_job(self) -> Dict[str, Any]:
        """
        Execute Daily Sync process:
        1. Fetch macro & Forex sentiment.
        2. Calculate strategy alignment score.
        3. Rebalance asset class preference weights.
        """
        logging.info("Executing Daily Strategy Sync job...")
        
        forex_sentiment = self.sentiment_analyzer.fetch_market_sentiment("Forex EURUSD GBPUSD")
        tech_sentiment = self.sentiment_analyzer.fetch_market_sentiment("Technology Stocks Tech")
        
        forex_score = forex_sentiment["sentiment_score"]
        tech_score = tech_sentiment["sentiment_score"]
        
        # Aggregate market sentiment alignment score (-1.0 to +1.0)
        overall_score = round((forex_score + tech_score) / 2.0, 2)
        self.current_alignment_score = overall_score
        self.last_sync_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Dynamic Sector Weighting based on sentiment alignment
        self.sector_weights = {
            "Forex_EURUSD": round(max(0.1, 0.25 + forex_score * 0.1), 2),
            "Forex_GBPUSD": round(max(0.1, 0.25 + forex_score * 0.08), 2),
            "Equities_Tech": round(max(0.1, 0.25 + tech_score * 0.12), 2),
            "Crypto_BTC": round(max(0.05, 0.25 + overall_score * 0.05), 2),
        }

        sync_report = {
            "timestamp": self.last_sync_time,
            "overall_alignment_score": overall_score,
            "market_regime": "BULLISH" if overall_score > 0.15 else ("BEARISH" if overall_score < -0.15 else "NEUTRAL_SIDEWAYS"),
            "forex_sentiment": forex_sentiment,
            "tech_sentiment": tech_sentiment,
            "allocated_sector_weights": self.sector_weights
        }

        logging.info(f"Daily Sync Complete. Alignment Score: {overall_score} | Regime: {sync_report['market_regime']}")
        return sync_report

# Singleton DailySync Instance
daily_sync = DailyStrategySync()
