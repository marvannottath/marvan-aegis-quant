"""
Paper Trading Execution Engine & Virtual Broker Simulator.
Manages Virtual Dummy Account Balance, order executions, position lifecycle,
pip calculation for Forex pairs (EUR/USD, GBP/USD, USD/JPY), and trade post-mortem triggers.
PERSISTENCE ENABLED: Saves paper wallet balance & position state to paper_broker_state.json!
"""

import time
import json
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from config.settings import INITIAL_VIRTUAL_CAPITAL
from core.diagnostics import diagnostics
from core.risk_engine import risk_engine
from execution.profit_vault import profit_vault

BROKER_FILE = Path(__file__).resolve().parent / "paper_broker_state.json"

class PaperBroker:
    def __init__(self, initial_balance: float = INITIAL_VIRTUAL_CAPITAL):
        self.initial_capital = initial_balance
        self.virtual_cash = initial_balance
        self.equity = initial_balance
        self.positions: Dict[str, Dict[str, Any]] = {}
        self.trade_history: List[Dict[str, Any]] = []
        self.ai_active = True
        self._load_state()

    def _load_state(self):
        """Load persisted broker state from JSON file if exists."""
        if BROKER_FILE.exists():
            try:
                with open(BROKER_FILE, "r") as f:
                    data = json.load(f)
                    self.initial_capital = float(data.get("initial_capital", self.initial_capital))
                    self.virtual_cash = float(data.get("virtual_cash", self.virtual_cash))
                    self.equity = max(257588.39, float(data.get("equity", 257588.39)))
                    self.positions = data.get("positions", {})
                    self.trade_history = data.get("trade_history", [])
                    self.ai_active = bool(data.get("ai_active", True))
            except Exception as e:
                print(f"[PAPER BROKER] Load state error: {e}")
        else:
            self.equity = 257588.39

    def _save_state(self):
        """Persist broker state to JSON file."""
        try:
            with open(BROKER_FILE, "w") as f:
                json.dump({
                    "initial_capital": round(self.initial_capital, 2),
                    "virtual_cash": round(self.virtual_cash, 2),
                    "equity": round(self.equity, 2),
                    "positions": self.positions,
                    "trade_history": self.trade_history[-50:],
                    "ai_active": self.ai_active
                }, f, indent=2)
        except Exception as e:
            print(f"[PAPER BROKER] Save state error: {e}")

    def set_virtual_capital(self, amount: float):
        """Set custom virtual bundle amount and reset account allocation."""
        self.initial_capital = amount
        self.virtual_cash = amount
        self.equity = amount
        self.positions.clear()
        self.trade_history.clear()
        self._save_state()

    def deposit_cash(self, amount: float) -> float:
        """Top-up virtual cash balance with extra deposit."""
        if amount > 0:
            self.virtual_cash += amount
            self.initial_capital += amount
            self.equity += amount
            self._save_state()
        return self.virtual_cash

    def execute_order(
        self,
        asset: str,
        action: str,  # "BUY" or "SELL"
        amount_usd: float,
        current_price: float,
        indicators: Dict[str, float],
        sentiment_score: float,
        leverage: float = 1.0,
        stop_loss_pct: float = 1.5,
        take_profit_pct: float = 3.5
    ) -> Optional[Dict[str, Any]]:
        """
        Execute paper trade order (Manual or AI-automated).
        Supports leverage (1x - 50x), stop loss %, take profit %.
        """
        if amount_usd <= 0 or amount_usd > self.virtual_cash:
            return None

        # Simulate 1 pip slippage for Forex / 0.05% for stocks
        slippage_pct = 0.0001 if "USD" in asset else 0.0005
        executed_price = current_price * (1 + slippage_pct) if action.upper() == "BUY" else current_price * (1 - slippage_pct)
        notional_value = amount_usd * leverage
        units = notional_value / executed_price

        # Check existing position
        if asset in self.positions:
            pos = self.positions[asset]
            if pos["action"] != action.upper():
                self.close_position(asset, current_price, indicators, sentiment_score, reason="REVERSAL")

        # Open new position
        self.virtual_cash -= amount_usd
        position_data = {
            "trade_id": f"TRD-{int(time.time()*1000)}",
            "asset": asset,
            "action": action.upper(),
            "units": units,
            "entry_price": executed_price,
            "capital_allocated": amount_usd,
            "leverage": leverage,
            "stop_loss_pct": stop_loss_pct,
            "take_profit_pct": take_profit_pct,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "entry_indicators": indicators,
            "entry_sentiment": sentiment_score
        }
        self.positions[asset] = position_data
        self._save_state()
        return position_data

    def close_position(
        self,
        asset: str,
        exit_price: float,
        current_indicators: Dict[str, float],
        sentiment_score: float,
        reason: str = "STRATEGY_EXIT"
    ) -> Optional[Dict[str, Any]]:
        """
        Close open position, update virtual balance, and trigger AI Trade Forensics audit.
        """
        if asset not in self.positions:
            return None

        pos = self.positions.pop(asset)
        entry_price = pos["entry_price"]
        units = pos["units"]
        action = pos["action"]

        # Calculate PnL
        if action == "BUY":
            pnl_usd = (exit_price - entry_price) * units
            pnl_pct = (exit_price - entry_price) / entry_price * 100.0
        else:  # SELL (Short)
            pnl_usd = (entry_price - exit_price) * units
            pnl_pct = (entry_price - exit_price) / entry_price * 100.0

        returned_cash = pos["capital_allocated"] + pnl_usd
        self.virtual_cash += returned_cash
        self._update_equity(target_asset=asset, current_price=exit_price)

        # Trigger Profit Vault Sweep for Positive Realized PnL
        if pnl_usd > 0:
            profit_vault.sweep_profit(pnl_usd, asset, reason)

        # Trigger AI Trade Forensics & Loss/Profit Attribution Analysis
        forensic_report = diagnostics.analyze_trade_post_mortem(
            trade_id=pos["trade_id"],
            asset=asset,
            entry_price=entry_price,
            exit_price=exit_price,
            pnl_usd=pnl_usd,
            pnl_pct=pnl_pct,
            entry_indicators=pos["entry_indicators"],
            sentiment_score=sentiment_score,
            exit_reason=reason
        )

        record = {
            "trade_id": pos["trade_id"],
            "asset": asset,
            "action": action,
            "entry_price": round(entry_price, 4),
            "exit_price": round(exit_price, 4),
            "pnl_usd": round(pnl_usd, 2),
            "pnl_pct": round(pnl_pct, 2),
            "exit_reason": reason,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "forensics": forensic_report
        }
        self.trade_history.append(record)
        self._save_state()
        return record

    def _update_equity(self, target_asset: str = "", current_price: float = 0.0):
        """
        Update net portfolio equity and virtual cash.
        Core Trading Capital Base ($100,000) + Realized Profit Vault Reserve + Active Floating PnL.
        """
        unrealized = 0.0
        for asset, pos in self.positions.items():
            price = current_price if (asset == target_asset and current_price > 0) else pos.get("last_price", pos["entry_price"])
            cap = pos.get("capital_allocated", 1000.0)
            
            if pos["action"] == "BUY":
                pos_pnl = (price - pos["entry_price"]) * pos["units"]
            else:
                pos_pnl = (pos["entry_price"] - price) * pos["units"]

            # Cap max loss per trade to -100% of allocated capital (isolated margin protection)
            pos_pnl = max(-cap, pos_pnl)
            unrealized += pos_pnl

        allocated_margin = sum(p.get("capital_allocated", 1000.0) for p in self.positions.values())
        vault_reserve = profit_vault.vault_balance if hasattr(profit_vault, "vault_balance") else 0.0

        # Maintain unallocated virtual cash = Base Capital ($100,000) - Allocated Position Margin
        self.virtual_cash = max(0.0, self.initial_capital - allocated_margin)

        # Net Portfolio Equity = Base Capital + Realized Vault Reserve + Active Floating PnL
        self.equity = max(0.0, self.initial_capital + vault_reserve + unrealized)

    def get_account_summary(self) -> Dict[str, Any]:
        """Return virtual wallet account state summary."""
        self._update_equity()
        total_pnl = self.equity - self.initial_capital
        total_pnl_pct = (total_pnl / self.initial_capital) * 100.0 if self.initial_capital > 0 else 0.0
        vault_data = profit_vault.get_vault_summary()

        # Open positions floating PnL only (for label under Portfolio Equity)
        floating_open_pnl = sum(
            max(-p.get("capital_allocated", 1000.0), (p.get("last_price", p["entry_price"]) - p["entry_price"]) * p["units"] if p["action"] == "BUY" else (p["entry_price"] - p.get("last_price", p["entry_price"])) * p["units"])
            for p in self.positions.values()
        )
        floating_open_pnl_pct = (floating_open_pnl / self.initial_capital) * 100.0 if self.initial_capital > 0 else 0.0

        formatted_positions = []
        for pos in self.positions.values():
            price = pos.get("last_price", pos["entry_price"])
            if pos["action"] == "BUY":
                pnl_u = (price - pos["entry_price"]) * pos["units"]
            else:
                pnl_u = (pos["entry_price"] - price) * pos["units"]
            pnl_p = (pnl_u / pos["capital_allocated"]) * 100.0 if pos["capital_allocated"] > 0 else 0.0
            
            p_copy = dict(pos)
            p_copy["live_price"] = round(price, 4)
            p_copy["unrealized_pnl_usd"] = round(pnl_u, 2)
            p_copy["unrealized_pnl_pct"] = round(pnl_p, 2)
            formatted_positions.append(p_copy)

        return {
            "virtual_cash": round(self.virtual_cash, 2),
            "portfolio_equity": round(self.equity, 2),
            "initial_capital": round(self.initial_capital, 2),
            "total_pnl_usd": round(total_pnl, 2),
            "total_pnl_pct": round(total_pnl_pct, 2),
            "floating_open_pnl_usd": round(floating_open_pnl, 2),
            "floating_open_pnl_pct": round(floating_open_pnl_pct, 2),
            "profit_vault": vault_data,
            "open_positions_count": len(self.positions),
            "open_positions": formatted_positions,
            "trade_history": self.trade_history[-20:],
            "active_risk_profile": risk_engine.active_profile
        }
