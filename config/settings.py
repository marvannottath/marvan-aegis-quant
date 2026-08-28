"""
Global Settings & Configuration for Aegis-Quant Trading System.
Includes Virtual Capital ($100k paper balance), Forex Pairs, Risk Limits, and Paths.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Trading System Settings
PAPER_TRADING_MODE = True
INITIAL_VIRTUAL_CAPITAL = 100000.0  # $100,000 USD Virtual Dummy Capital

# Asset Coverage (Commodities Gold + Forex + Equities + Crypto)
GOLD_ASSET = "XAUUSD"  # Gold Spot / USD ($2,510/oz)
FOREX_PAIRS = ["XAUUSD", "EURUSD", "GBPUSD", "USDJPY"]
EQUITY_SECTORS = ["XLK", "XLF", "XLE", "XLV"]  # Tech, Financials, Energy, Healthcare ETFs
CRYPTO_PAIRS = ["BTCUSD"]
ALL_ASSETS = FOREX_PAIRS + EQUITY_SECTORS + CRYPTO_PAIRS

# Risk Management Limits
MAX_POSITION_SIZE_PCT = 0.10     # Max 10% of portfolio per position
MAX_PORTFOLIO_DRAWDOWN_PCT = 0.08 # 8% Max Drawdown Circuit Breaker
DEFAULT_STOP_LOSS_PCT = 0.015     # 1.5% Stop Loss
DEFAULT_TAKE_PROFIT_PCT = 0.035    # 3.5% Take Profit
KELLY_FRACTION = 0.5             # Half-Kelly position sizing for safety

# Reinforcement Learning Settings
RL_STATE_DIM = 24
RL_ACTION_DIM = 3                # 0: HOLD, 1: BUY, 2: SELL
RL_LEARNING_RATE = 1e-3
RL_GAMMA = 0.99
RL_MEMORY_SIZE = 10000
RL_BATCH_SIZE = 64

# Diagnostics & Log Paths
LOG_DIR = BASE_DIR / "logs"
MODEL_DIR = BASE_DIR / "saved_models"
KEY_VAULT_PATH = BASE_DIR / ".vault.key"

LOG_DIR.mkdir(parents=True, exist_ok=True)
MODEL_DIR.mkdir(parents=True, exist_ok=True)
