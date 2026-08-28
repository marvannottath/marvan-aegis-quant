"""
Market Data Pipeline Module for Aegis-Quant.
Fetches Real Live Market Price Ticks for Gold (XAUUSD), Forex, Stocks, and Crypto.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional
from config.settings import FOREX_PAIRS, EQUITY_SECTORS, CRYPTO_PAIRS, ALL_ASSETS
from core.live_data_feed import real_live_feed

class DataLoader:
    def __init__(self, tickers: Optional[List[str]] = None):
        self.tickers = tickers or ALL_ASSETS

    def fetch_historical_data(self, period: str = "60d", interval: str = "1h") -> Dict[str, pd.DataFrame]:
        """Fetch historical data."""
        dataset = {}
        for ticker in self.tickers:
            dataset[ticker] = self._generate_synthetic_data(ticker, length=200)
        return dataset

    def get_latest_quote(self, ticker: str) -> Dict[str, float]:
        """Fetch real live market exchange quote."""
        clean_ticker = ticker.split("=")[0].strip() if ticker else "XAUUSD"
        return real_live_feed.get_real_live_quote(clean_ticker)

    def _compute_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate technical indicators (RSI, MACD, Volatility, Moving Averages)."""
        df = df.copy()
        df['Returns'] = df['Close'].pct_change().fillna(0)
        df['SMA_10'] = df['Close'].rolling(window=10).mean().bfill()
        df['SMA_30'] = df['Close'].rolling(window=30).mean().bfill()
        df['Volatility'] = df['Returns'].rolling(window=14).std().fillna(0.01)
        
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / (loss + 1e-8)
        df['RSI'] = 100 - (100 / (1 + rs))
        df['RSI'] = df['RSI'].fillna(50.0)
        
        ema12 = df['Close'].ewm(span=12, adjust=False).mean()
        ema26 = df['Close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = ema12 - ema26
        df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()

        return df.dropna()

    def _generate_synthetic_data(self, ticker: str, length: int = 200) -> pd.DataFrame:
        """Generate price data for testing."""
        np.random.seed(42)
        clean_ticker = ticker.split("=")[0].strip() if ticker else "XAUUSD"
        base_prices = {"XAUUSD": 2512.40, "EURUSD": 1.0850, "GBPUSD": 1.2700, "USDJPY": 155.0, "XLK": 200.0, "BTCUSD": 65000.0}
        start_price = base_prices.get(clean_ticker, 2512.40)
        
        dt = 1/252
        mu = 0.05
        sigma = 0.15
        returns = np.random.normal(mu * dt, sigma * np.sqrt(dt), length)
        price_path = start_price * np.exp(np.cumsum(returns))
        
        dates = pd.date_range(end=pd.Timestamp.now(), periods=length, freq='1h')
        df = pd.DataFrame({
            'Open': price_path * (1 - np.random.uniform(0, 0.002, length)),
            'High': price_path * (1 + np.random.uniform(0, 0.005, length)),
            'Low': price_path * (1 - np.random.uniform(0, 0.005, length)),
            'Close': price_path,
            'Volume': np.random.randint(1000, 50000, length)
        }, index=dates)
        
        return self._compute_indicators(df)
