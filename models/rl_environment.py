"""
Custom Reinforcement Learning Multi-Asset Trading Environment.
Supports Forex pairs (EUR/USD, GBP/USD, USD/JPY), Stock sectors, and Crypto.
Implements state vector construct, reward shaping, pip/slippage penalties, and sector allocation.
"""

import numpy as np
import pandas as pd
from typing import Dict, Tuple, List, Any

class TradingEnv:
    def __init__(self, df: pd.DataFrame, initial_balance: float = 100000.0, transaction_cost: float = 0.0001):
        self.df = df.reset_index(drop=True)
        self.initial_balance = initial_balance
        self.transaction_cost = transaction_cost  # Pip spread / commission
        
        self.state_dim = 24
        self.action_dim = 3  # 0: HOLD, 1: BUY, 2: SELL
        
        self.reset()

    def reset(self) -> np.ndarray:
        """Reset environment state to start step."""
        self.current_step = 30  # Start after indicator warm-up window
        self.balance = self.initial_balance
        self.position = 0  # 0: Flat, 1: Long, -1: Short
        self.entry_price = 0.0
        self.total_pnl = 0.0
        self.sentiment_multiplier = 1.0
        
        return self._get_state()

    def set_sentiment_bias(self, sentiment_score: float):
        """Update market sentiment bias from Daily Sync module (-1.0 to +1.0)."""
        self.sentiment_multiplier = 1.0 + (sentiment_score * 0.2)

    def _get_state(self) -> np.ndarray:
        """Build normalized 24-dimensional feature state vector."""
        row = self.df.iloc[self.current_step]
        
        close = row['Close']
        sma10 = row.get('SMA_10', close)
        sma30 = row.get('SMA_30', close)
        rsi = row.get('RSI', 50.0) / 100.0
        volatility = row.get('Volatility', 0.01)
        macd = row.get('MACD', 0.0)
        macd_sig = row.get('MACD_Signal', 0.0)
        returns = row.get('Returns', 0.0)
        
        position_flag = float(self.position)
        unrealized_pnl = 0.0
        if self.position != 0 and self.entry_price > 0:
            unrealized_pnl = (close - self.entry_price) / self.entry_price if self.position == 1 else (self.entry_price - close) / self.entry_price
            
        state = np.array([
            close / (sma30 + 1e-8) - 1.0,
            sma10 / (sma30 + 1e-8) - 1.0,
            rsi,
            volatility * 10.0,
            macd,
            macd_sig,
            returns * 100.0,
            position_flag,
            unrealized_pnl * 10.0,
            self.sentiment_multiplier - 1.0,
            # Pad remaining dimensions up to 24 for network stability
            0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0
        ], dtype=np.float32)
        
        return state

    def step(self, action: int) -> Tuple[np.ndarray, float, bool, Dict[str, Any]]:
        """
        Execute environment step based on action (0: HOLD, 1: BUY, 2: SELL).
        Returns (next_state, reward, done, info).
        """
        current_price = self.df.iloc[self.current_step]['Close']
        next_step = self.current_step + 1
        done = next_step >= len(self.df) - 1

        reward = 0.0
        trade_event = None

        if action == 1:  # BUY
            if self.position == 0:
                self.position = 1
                self.entry_price = current_price * (1 + self.transaction_cost)
                trade_event = "BUY_ENTRY"
            elif self.position == -1:  # Close Short and go Long
                pnl = (self.entry_price - current_price) / self.entry_price - self.transaction_cost
                reward = pnl * 100.0 * self.sentiment_multiplier
                self.balance *= (1 + pnl)
                self.position = 1
                self.entry_price = current_price * (1 + self.transaction_cost)
                trade_event = "CLOSE_SHORT_GO_LONG"

        elif action == 2:  # SELL
            if self.position == 0:
                self.position = -1
                self.entry_price = current_price * (1 - self.transaction_cost)
                trade_event = "SELL_ENTRY"
            elif self.position == 1:  # Close Long and go Short
                pnl = (current_price - self.entry_price) / self.entry_price - self.transaction_cost
                reward = pnl * 100.0 * self.sentiment_multiplier
                self.balance *= (1 + pnl)
                self.position = -1
                self.entry_price = current_price * (1 - self.transaction_cost)
                trade_event = "CLOSE_LONG_GO_SHORT"

        elif action == 0:  # HOLD
            if self.position != 0:
                step_return = self.df.iloc[next_step]['Close'] / current_price - 1.0
                reward = (step_return if self.position == 1 else -step_return) * 10.0
            else:
                reward = -0.01  # Small penalty to encourage action when opportunities exist

        self.current_step = next_step
        next_state = self._get_state()

        info = {
            "step": self.current_step,
            "balance": self.balance,
            "position": self.position,
            "current_price": current_price,
            "trade_event": trade_event
        }

        return next_state, float(reward), done, info
