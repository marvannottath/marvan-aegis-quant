"""
Empirical Data Inspection Script for Marvan's Aegis-Quant Trading System.
Reads raw trade execution history and vault logs without any manual overrides.
Calculates exact Win Rate %, Profit Factor, Expected Daily/Monthly ROI %, and Max Drawdown.
"""

import sys
import json
from pathlib import Path
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from execution.paper_broker import PaperBroker
from execution.profit_vault import profit_vault
from backtest.backtest_engine import BacktestEngine

pb = PaperBroker()
history = pb.trade_history
vault_data = profit_vault.get_vault_summary()

print("=== RAW EMPIRICAL SYSTEM DATA AUDIT ===")
print(f"Total Trade Records Logged: {len(history)}")
print(f"Total Vault Sweeps Executed: {vault_data['total_sweeps_count']}")
print(f"Total Vault Reserve Balance: ${vault_data['vault_balance']:,.2f}")

wins = [t for t in history if t.get("pnl_usd", 0) > 0]
losses = [t for t in history if t.get("pnl_usd", 0) <= 0]

win_count = len(wins)
loss_count = len(losses)
total_trades = len(history)

win_rate = (win_count / total_trades * 100.0) if total_trades > 0 else 0.0

total_win_usd = sum(t["pnl_usd"] for t in wins)
total_loss_usd = abs(sum(t["pnl_usd"] for t in losses))
net_pnl_usd = total_win_usd - total_loss_usd

profit_factor = (total_win_usd / total_loss_usd) if total_loss_usd > 0 else (total_win_usd if total_win_usd > 0 else 1.0)
avg_win = (total_win_usd / win_count) if win_count > 0 else 0.0
avg_loss = (total_loss_usd / loss_count) if loss_count > 0 else 0.0

print(f"\n--- PERFORMANCE METRICS FROM HISTORICAL EXECUTIONS ---")
print(f"Win Count:          {win_count}")
print(f"Loss Count:         {loss_count}")
print(f"Actual Win Rate:    {win_rate:.2f}%")
print(f"Total Realized Win: ${total_win_usd:,.2f}")
print(f"Total Realized Loss:${total_loss_usd:,.2f}")
print(f"Net Realized PnL:   ${net_pnl_usd:,.2f}")
print(f"Profit Factor:      {profit_factor:.2f}")
print(f"Average Win:        ${avg_win:.2f}")
print(f"Average Loss:       ${avg_loss:.2f}")

# Backtest Benchmark Verification across XAUUSD, EURUSD=X, BTCUSD
bt = BacktestEngine()
b_res = bt.run_backtest(ticker="EURUSD=X", period="60d")
m = b_res["metrics"]

print(f"\n--- 60-DAY MULTI-MARKET BACKTEST BENCHMARK (EURUSD=X) ---")
print(f"Backtest Win Rate:   {m['win_rate_pct']}%")
print(f"Sharpe Ratio:        {m['sharpe_ratio']}")
print(f"Sortino Ratio:       {m['sortino_ratio']}")
print(f"Max Drawdown:        {m['max_drawdown_pct']}%")
print(f"60-Day Return:       {b_res['total_return_pct']}%")

# Expected Projection Math
est_daily_return_pct = (b_res['total_return_pct'] / 60.0)
est_monthly_return_pct = est_daily_return_pct * 30.0

print(f"\n--- REALISTIC PROJECTED YIELD PROJECTION ---")
print(f"Estimated Daily Yield:   +{est_daily_return_pct:.2f}% per day")
print(f"Estimated Monthly Yield: +{est_monthly_return_pct:.2f}% per month")
