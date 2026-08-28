"""
Master Orchestrator & CLI Launcher for Aegis-Quant Trading System.
Supports `--mode run` (Live Paper Trading + Web Dashboard), `--mode backtest`, and `--mode encrypt-key`.
"""

import sys
import time
import argparse
import uvicorn
from pathlib import Path
from config.settings import FOREX_PAIRS
from config.security import vault
from core.data_loader import DataLoader
from core.diagnostics import diagnostics
from core.risk_engine import RiskEngine
from models.rl_agent import RLAgent
from sync.daily_sync import daily_sync
from execution.paper_broker import PaperBroker
from backtest.backtest_engine import BacktestEngine
from dashboard.app import app, paper_broker, risk_engine, backtester

def run_backtest_mode(ticker: str = "EURUSD=X"):
    """Execute offline strategy backtest and print metrics."""
    print("=" * 60)
    print(f"   Aegis-Quant Backtesting Engine - Asset: {ticker}")
    print("=" * 60)
    
    result = backtester.run_backtest(ticker=ticker, period="60d")
    m = result["metrics"]
    
    print(f"Asset Ticker:        {result['ticker']}")
    print(f"Period:              {result['period']}")
    print(f"Initial Capital:     ${result['initial_capital']:,.2f}")
    print(f"Final Equity:        ${result['final_equity']:,.2f}")
    print(f"Total Return:        {result['total_return_pct']}%")
    print(f"Sharpe Ratio:        {m['sharpe_ratio']}")
    print(f"Sortino Ratio:       {m['sortino_ratio']}")
    print(f"Max Drawdown:        {m['max_drawdown_pct']}%")
    print(f"Win Rate:            {m['win_rate_pct']}%")
    print(f"Total Trades:        {m['total_trades']}")
    print("=" * 60)

def run_live_system():
    """Launch paper trading loop, daily sentiment sync, and FastAPI dashboard."""
    print("=" * 60)
    print("   Starting Marvan Aegis-Quant Autonomous Trading System")
    print("   Mode: Paper Trading ($100,000 Virtual Capital Default)")
    print("   Dashboard: http://127.0.0.1:8000")
    print("=" * 60)

    # Execute initial sentiment sync
    daily_sync.run_sync_job()

    # Seed mock paper trade to initialize AI Forensics Feed
    loader = DataLoader()
    quote = loader.get_latest_quote("EURUSD=X")
    pos = paper_broker.execute_order(
        asset="EURUSD=X",
        action="BUY",
        amount_usd=10000.0,
        current_price=quote["price"],
        indicators={"RSI": 42.5, "Volatility": 0.008},
        sentiment_score=daily_sync.current_alignment_score
    )
    if pos:
        paper_broker.close_position(
            asset="EURUSD=X",
            exit_price=quote["price"] * 1.0045,  # +0.45% profit trade
            current_indicators={"RSI": 68.2, "Volatility": 0.007},
            sentiment_score=daily_sync.current_alignment_score,
            reason="TAKE_PROFIT_HIT"
        )

    # Launch FastAPI web server
    import os
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")

def encrypt_key_interactive():
    """CLI utility to encrypt secret API keys using Fernet AES-256."""
    key_name = input("Enter Key Name (e.g. NEWS_API_KEY): ").strip()
    raw_val = input("Enter Secret Key Value: ").strip()
    encrypted = vault.encrypt_secret(raw_val)
    print(f"\n[Encrypted Secret for {key_name}]:\n{encrypted}\n")
    print("Store this encrypted secret safely in your .env file!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Aegis-Quant Algorithmic Trading System Launcher")
    parser.add_argument("--mode", type=str, default="run", choices=["run", "backtest", "encrypt-key"],
                        help="Execution mode: 'run', 'backtest', or 'encrypt-key'")
    parser.add_argument("--ticker", type=str, default="EURUSD=X", help="Asset ticker for backtesting")
    
    args = parser.parse_args()
    
    if args.mode == "backtest":
        run_backtest_mode(ticker=args.ticker)
    elif args.mode == "encrypt-key":
        encrypt_key_interactive()
    else:
        run_live_system()
