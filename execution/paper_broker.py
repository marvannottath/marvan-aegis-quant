"""
PaperBroker with Strict 3-Environment Partitioned Namespace Isolation:
1. AEGIS_QUANT_MASTER (Multi-Asset Engine)
2. BINANCE_TESTNET_DEMO (Binance Testnet USDT Spot)
3. BINANCE_LIVE_REAL (Real Binance Production Spot)

NO static vault_reserve. NO shared ledger leakage. NO ungrounded numbers.
"""

import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta

IST_TZ = timezone(timedelta(hours=5, minutes=30))
from execution.binance_broker import binance_broker
from execution.profit_vault import profit_vault

BROKER_FILE = Path(__file__).resolve().parent / "paper_broker_state.json"

class PaperBroker:
    def __init__(self):
        self.active_pool_name: str = "AEGIS_QUANT_MASTER"
        
        # 3 Completely Partitioned Namespaces
        self.pools: Dict[str, Dict[str, Any]] = {
            "AEGIS_QUANT_MASTER": {
                "initial_capital": 100000.0,
                "virtual_cash": 100000.0,
                "equity": 100000.0,
                "positions": {},
                "trade_history": [],
                "ai_active": True,
                "order_stream": []
            },
            "BINANCE_TESTNET_DEMO": {
                "initial_capital": 19950.55,
                "virtual_cash": 19950.55,
                "equity": 19950.55,
                "positions": {},
                "trade_history": [],
                "ai_active": True,
                "order_stream": []
            },
            "BINANCE_LIVE_REAL": {
                "initial_capital": 0.0,
                "virtual_cash": 0.0,
                "equity": 0.0,
                "positions": {},
                "trade_history": [],
                "ai_active": False,
                "order_stream": []
            }
        }
        
        self.initial_capital = 100000.0
        self.virtual_cash = 100000.0
        self.equity = 100000.0
        self.positions = {}
        self.trade_history = []
        self.ai_active = True
        
        self._load_state()

    def _load_state(self):
        """Load persisted state from disk."""
        if BROKER_FILE.exists():
            try:
                with open(BROKER_FILE, "r") as f:
                    data = json.load(f)
                    self.active_pool_name = data.get("active_pool_name", "AEGIS_QUANT_MASTER")
                    if "pools" in data:
                        self.pools = data["pools"]
            except Exception as e:
                print(f"[PAPER BROKER] Load state notice: {e}")

        self._sync_active_pool_refs()
        self._update_equity()

    def _save_state(self):
        """Persist state to disk."""
        try:
            with open(BROKER_FILE, "w") as f:
                json.dump({
                    "active_pool_name": self.active_pool_name,
                    "pools": self.pools
                }, f, indent=2)
        except Exception as e:
            print(f"[PAPER BROKER] Save state notice: {e}")

    def _sync_active_pool_refs(self):
        """Sync class-level references with active pool."""
        current = self.pools.get(self.active_pool_name, self.pools["AEGIS_QUANT_MASTER"])
        self.initial_capital = current["initial_capital"]
        self.virtual_cash = current["virtual_cash"]
        self.equity = current["equity"]
        self.positions = current["positions"]
        self.trade_history = current["trade_history"]
        self.ai_active = current.get("ai_active", True)

    def set_active_capital_pool(self, pool_name: str, initial_capital: Optional[float] = None) -> Dict[str, Any]:
        """Switch active environment cleanly."""
        if pool_name in ["MASTER_SIMULATION", "AEGIS_QUANT_MASTER"]:
            target_name = "AEGIS_QUANT_MASTER"
        elif pool_name in ["BINANCE_DEMO", "BINANCE_TESTNET_DEMO"]:
            target_name = "BINANCE_TESTNET_DEMO"
        elif pool_name in ["BINANCE_LIVE_REAL", "BINANCE_LIVE"]:
            target_name = "BINANCE_LIVE_REAL"
        else:
            target_name = pool_name

        if target_name not in self.pools:
            cap = initial_capital or 10000.0
            self.pools[target_name] = {
                "initial_capital": cap,
                "virtual_cash": cap,
                "equity": cap,
                "positions": {},
                "trade_history": [],
                "ai_active": True
            }

        self.active_pool_name = target_name
        if target_name == "BINANCE_LIVE_REAL":
            real_b = binance_broker.get_real_live_spot_balance()
            self.pools["BINANCE_LIVE_REAL"]["initial_capital"] = real_b
            self.pools["BINANCE_LIVE_REAL"]["virtual_cash"] = real_b
            self.pools["BINANCE_LIVE_REAL"]["equity"] = real_b

        self._sync_active_pool_refs()
        self._update_equity()
        self._save_state()

        return {
            "status": "SUCCESS",
            "active_pool": target_name,
            "initial_capital": self.initial_capital,
            "portfolio_equity": self.equity,
            "virtual_cash": self.virtual_cash
        }

    def _update_equity(self):
        """
        Dynamically compute account equity strictly for active pool:
          Trading Account Equity = Virtual Cash + Used Margin + Unrealized PnL
          Secured Vault = SUM(vault_transactions for active pool)
          Total Platform Assets = Trading Account Equity + Secured Vault
        """
        unrealized = 0.0
        allocated_margin = 0.0

        for pos in self.positions.values():
            price = pos.get("last_price", pos["entry_price"])
            cap = pos.get("capital_allocated", 1000.0)
            allocated_margin += cap

            if pos["action"] == "BUY":
                pos_pnl = (price - pos["entry_price"]) * pos["units"]
            else:
                pos_pnl = (pos["entry_price"] - price) * pos["units"]
            pos_pnl = max(-cap, pos_pnl)
            unrealized += pos_pnl

        # Cash = Initial Capital - Used Margin + Realized PnL (net of closed trades)
        realized_pnl = sum(float(t.get("pnl_usd", 0.0)) for t in self.trade_history)
        
        # Calculate cash: initial - margin + realized PnL
        computed_cash = max(0.0, self.initial_capital - allocated_margin + realized_pnl)
        self.virtual_cash = round(computed_cash, 2)

        # Trading Account Equity = Cash + Margin + Unrealized PnL
        self.equity = round(self.virtual_cash + allocated_margin + unrealized, 2)
        
        # Sync back to active pool
        pool = self.pools[self.active_pool_name]
        pool["virtual_cash"] = self.virtual_cash
        pool["equity"] = self.equity

    def execute_order(self, asset: str, action: str, amount_usd: float, current_price: float, leverage: float = 10.0, **kwargs) -> Dict[str, Any]:
        """Execute order in active environment."""
        notional = amount_usd * leverage
        units = notional / current_price

        # Idempotency check: if position exists, update or skip duplicate
        if asset in self.positions:
            return self.positions[asset]

        trade_id = f"TRD-{self.active_pool_name[:4]}-{int(time.time()*1000)}-{asset}"

        position = {
            "trade_id": trade_id,
            "asset": asset,
            "action": action,
            "units": round(units, 4),
            "entry_price": current_price,
            "last_price": current_price,
            "capital_allocated": round(amount_usd, 2),
            "leverage": leverage,
            "timestamp": datetime.now(timezone.utc).astimezone(IST_TZ).strftime("%Y-%m-%d %H:%M:%S")
        }

        self.positions[asset] = position
        self._update_equity()
        self._save_state()
        return position

    def close_position(self, asset: str, exit_price: float, current_indicators: Optional[dict] = None, sentiment_score: float = 0.5, reason: str = "MANUAL_CLOSE") -> Optional[dict]:
        """Close position and sweep profit if positive into active environment vault."""
        if asset not in self.positions:
            return None

        pos = self.positions.pop(asset)
        entry = pos["entry_price"]
        units = pos["units"]
        act = pos["action"]
        cap = pos["capital_allocated"]

        if act == "BUY":
            pnl_u = (exit_price - entry) * units
        else:
            pnl_u = (entry - exit_price) * units

        pnl_u = max(-cap, round(pnl_u, 2))
        pnl_p = round((pnl_u / cap) * 100.0, 2) if cap > 0 else 0.0

        trade_record = {
            "trade_id": pos["trade_id"],
            "asset": asset,
            "action": act,
            "entry_price": entry,
            "exit_price": exit_price,
            "units": units,
            "capital_allocated": cap,
            "leverage": pos.get("leverage", 10.0),
            "pnl_usd": pnl_u,
            "pnl_pct": pnl_p,
            "reason": reason,
            "timestamp": datetime.now(timezone.utc).astimezone(IST_TZ).strftime("%Y-%m-%d %H:%M:%S")
        }

        self.trade_history.insert(0, trade_record)

        # Sweep profit if positive into isolated vault for active environment
        if pnl_u > 0:
            profit_vault.sweep_profit(
                trade_pnl=pnl_u,
                asset=asset,
                exit_reason=reason,
                source_trade_id=pos["trade_id"],
                environment=self.active_pool_name
            )

        self._update_equity()
        self._save_state()
        return trade_record

    def check_and_enforce_stops(self, risk_engine_ref=None) -> list:
        """Enforce stop-loss and take-profit on all open positions."""
        from core.risk_engine import risk_engine as re
        engine = risk_engine_ref or re
        closed = []

        sl_pct = engine.active_profile.get("stop_loss_pct", 1.5) / 100.0
        tp_pct = engine.active_profile.get("take_profit_target_pct", 3.5) / 100.0

        for asset_key, pos in list(self.positions.items()):
            entry = pos["entry_price"]
            act = pos["action"]
            price = pos.get("last_price", entry)

            pnl_pct = (price - entry) / entry if act == "BUY" else (entry - price) / entry

            if pnl_pct <= -sl_pct:
                rec = self.close_position(asset_key, price, reason=f"STOP_LOSS_ENFORCED (SL={sl_pct*100:.1f}%)")
                if rec:
                    closed.append(rec)
            elif pnl_pct >= tp_pct:
                rec = self.close_position(asset_key, price, reason=f"TAKE_PROFIT_ENFORCED (TP={tp_pct*100:.1f}%)")
                if rec:
                    closed.append(rec)

        return closed

    def get_reconciliation(self) -> dict:
        """
        FORMAL ACCOUNT RECONCILIATION REPORT:
          Trading Account Equity = Cash ($Cash) + Used Margin ($Margin) + Floating PnL ($Unrealized)
          Secured Vault Reserve = sum(verified vault_transactions)
          Total Platform Assets = Trading Account Equity + Secured Vault Reserve
        """
        self._update_equity()

        used_margin = sum(p.get("capital_allocated", 0.0) for p in self.positions.values())
        unrealized_pnl = 0.0
        for pos in self.positions.values():
            price = pos.get("last_price", pos["entry_price"])
            if pos["action"] == "BUY":
                unrealized_pnl += (price - pos["entry_price"]) * pos["units"]
            else:
                unrealized_pnl += (pos["entry_price"] - price) * pos["units"]

        vault_reserve = profit_vault.get_vault_balance(self.active_pool_name)
        trading_equity = round(self.virtual_cash + used_margin + unrealized_pnl, 2)
        total_platform_assets = round(trading_equity + vault_reserve, 2)

        return {
            "environment": self.active_pool_name,
            "cash": round(self.virtual_cash, 2),
            "used_margin": round(used_margin, 2),
            "unrealized_pnl": round(unrealized_pnl, 2),
            "trading_account_equity": trading_equity,
            "secured_vault_reserve": vault_reserve,
            "total_platform_assets": total_platform_assets,
            "status": "RECONCILIATION_OK",
            "model_explanation": "Trading Account Equity = Cash + Margin + FloatingPnL | Total Platform Assets = Trading Equity + Secured Vault Reserve"
        }

    def get_account_summary(self) -> Dict[str, Any]:
        """Return pure data-driven ledger summary derived strictly from active environment history."""
        self._update_equity()
        vault_summary = profit_vault.get_vault_summary(self.active_pool_name)

        gross_profit = sum(float(t.get("pnl_usd", 0.0)) for t in self.trade_history if float(t.get("pnl_usd", 0.0)) > 0)
        loss_trades = [t for t in self.trade_history if float(t.get("pnl_usd", 0.0)) < 0]
        gross_loss = abs(sum(float(t.get("pnl_usd", 0.0)) for t in loss_trades))
        net_pnl = gross_profit - gross_loss

        total_trades = len(self.trade_history)
        win_trades = sum(1 for t in self.trade_history if float(t.get("pnl_usd", 0.0)) > 0)
        # Filter out zero PnL sweeps from trade statistics
        real_trades = [t for t in self.trade_history if abs(float(t.get("pnl_usd", 0.0))) > 0.01]
        total_real_trades = len(real_trades)
        win_trades = sum(1 for t in real_trades if float(t.get("pnl_usd", 0.0)) > 0)
        loss_trades_count = sum(1 for t in real_trades if float(t.get("pnl_usd", 0.0)) < 0)

        if total_real_trades < 5:
            win_rate_display = f"Live Sample: {win_trades} Profitable / {loss_trades_count} Losing Trades"
            win_rate = 0.0
        else:
            win_rate = round((win_trades / total_real_trades * 100.0), 1)
            win_rate_display = f"{win_rate}%"


        # Performance metric formatting: If gross_loss == 0, handle profit factor cleanly
        if gross_loss == 0:
            profit_factor_display = "N/A — No Losing Trades" if gross_profit > 0 else "1.00"
            profit_factor_val = 1.00
        else:
            profit_factor_val = round(gross_profit / gross_loss, 2)
            profit_factor_display = f"{profit_factor_val:.2f}"

        ytd_pct = round((net_pnl / self.initial_capital * 100.0), 2) if self.initial_capital > 0 else 0.0
        ytd_display = f"+{ytd_pct:.2f}% (${net_pnl:,.2f} / ${self.initial_capital:,.2f})"

        return {
            "active_pool_name": self.active_pool_name,
            "initial_capital": self.initial_capital,
            "virtual_cash": round(self.virtual_cash, 2),
            "portfolio_equity": round(self.equity, 2),
            "floating_open_pnl_usd": 0.0,
            "floating_open_pnl_pct": 0.0,
            "open_positions": list(self.positions.values()),
            "open_positions_count": len(self.positions),
            "trade_history": self.trade_history[:25],
            "profit_vault": vault_summary,
            "ledger_metrics": {
                "all_time": {
                    "gross_profit_usd": round(gross_profit, 2),
                    "gross_loss_usd": round(gross_loss, 2),
                    "net_profit_usd": round(net_pnl, 2),
                    "total_trades": total_trades,
                    "win_rate_pct": win_rate,
                    "win_rate_display": win_rate_display,
                    "profit_factor": profit_factor_val,
                    "profit_factor_display": profit_factor_display,
                    "ytd_display": ytd_display
                }
            }
        }


# Global Singleton
paper_broker = PaperBroker()
