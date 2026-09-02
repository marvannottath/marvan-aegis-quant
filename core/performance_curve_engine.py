"""
Aegis-Quant Performance Curve Engine.
Provides authoritative backend time-series performance data points for:
  - Metric: equity | pnl | drawdown
  - Range:  1D | 1W | 1M | 3M | ALL
Derived strictly from authoritative ledger entries, paper broker state history, or persisted backtest runs.
"""

import time
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta

IST_TZ = timezone(timedelta(hours=5, minutes=30))


class PerformanceCurveEngine:
    def get_curve(
        self,
        metric: str = "equity",
        time_range: str = "1D",
        environment: str = "AEGIS_QUANT_MASTER"
    ) -> Dict[str, Any]:
        """
        Return timestamped curve data points from authoritative sources.
        No fabricated data.
        """
        metric = metric.lower()
        if metric not in {"equity", "pnl", "drawdown"}:
            metric = "equity"
        
        time_range = time_range.upper()
        if time_range not in {"1D", "1W", "1M", "3M", "ALL"}:
            time_range = "1D"

        from core.double_entry_ledger import double_entry_ledger
        from execution.paper_broker import paper_broker
        from execution.profit_vault import profit_vault

        entries = double_entry_ledger.get_ledger_history(environment=environment)
        # Sort entries chronologically
        sorted_entries = sorted(entries, key=lambda e: e.get("timestamp", ""))

        now_dt = datetime.now(timezone.utc).astimezone(IST_TZ)
        now_str = now_dt.strftime("%Y-%m-%d %H:%M:%S IST")

        # Determine cutoff based on time_range
        range_deltas = {
            "1D": timedelta(days=1),
            "1W": timedelta(days=7),
            "1M": timedelta(days=30),
            "3M": timedelta(days=90),
            "ALL": timedelta(days=3650)
        }
        cutoff_dt = now_dt - range_deltas[time_range]

        # Build baseline point from opening balance or broker equity
        opening_entry = double_entry_ledger.ensure_opening_balance(environment, 100000.0)
        opening_amt = float(opening_entry.get("amount", 100000.0))
        opening_time = opening_entry.get("timestamp", "2026-01-01 00:00:00")

        points = []
        running_cash = opening_amt
        running_pnl = 0.0
        peak_equity = opening_amt

        # Add initial starting point
        points.append({
            "timestamp": opening_time,
            "value": opening_amt if metric == "equity" else (0.0 if metric == "pnl" else 0.0)
        })

        for e in sorted_entries:
            if e.get("ledger_type") == "OPENING_BALANCE":
                continue
            
            ts_str = e.get("timestamp", "")
            amt = float(e.get("amount", 0.0))
            ltype = e.get("ledger_type", "")
            credit_acc = e.get("credit_account", "")
            debit_acc = e.get("debit_account", "")

            if ltype in ("TRADING_LEDGER", "REALIZED_PNL_LEDGER"):
                if credit_acc == "CUSTOMER_TRADING_ACCOUNT":
                    running_pnl += amt
                    running_cash += amt
                elif debit_acc == "CUSTOMER_TRADING_ACCOUNT":
                    running_pnl -= amt
                    running_cash -= amt

            elif ltype in ("DEPOSIT", "BINANCE_PAY_DEPOSIT", "STRIPE_DEPOSIT"):
                if credit_acc == "CUSTOMER_TRADING_ACCOUNT":
                    running_cash += amt

            elif ltype == "WITHDRAWAL":
                if debit_acc == "CUSTOMER_TRADING_ACCOUNT":
                    running_cash -= amt

            cur_equity = round(running_cash, 2)
            if cur_equity > peak_equity:
                peak_equity = cur_equity
            
            dd_pct = round(((peak_equity - cur_equity) / peak_equity * 100.0), 2) if peak_equity > 0 else 0.0

            if metric == "equity":
                val = cur_equity
            elif metric == "pnl":
                val = round(running_pnl, 2)
            else:
                val = dd_pct

            points.append({
                "timestamp": ts_str,
                "value": val
            })

        # Add current live broker point
        broker_cash = round(float(paper_broker.equity) + float(profit_vault.get_vault_balance(environment)), 2)
        total_pnl = round(sum(float(t.get("pnl_usd", 0.0)) for t in paper_broker.trade_history), 2)
        
        if broker_cash > peak_equity:
            peak_equity = broker_cash
        dd_pct_live = round(((peak_equity - broker_cash) / peak_equity * 100.0), 2) if peak_equity > 0 else 0.0

        if metric == "equity":
            live_val = broker_cash
        elif metric == "pnl":
            live_val = total_pnl
        else:
            live_val = dd_pct_live

        points.append({
            "timestamp": now_str,
            "value": live_val
        })

        # Deduplicate points by timestamp if identical
        filtered_points = []
        seen = set()
        for p in points:
            if p["timestamp"] not in seen:
                seen.add(p["timestamp"])
                filtered_points.append(p)

        values = [p["value"] for p in filtered_points]
        latest_val = values[-1] if values else 0.0
        min_val = min(values) if values else 0.0
        max_val = max(values) if values else 0.0

        return {
            "status": "SUCCESS",
            "metric": metric,
            "range": time_range,
            "environment": environment,
            "points": filtered_points,
            "latest": latest_val,
            "min": min_val,
            "max": max_val,
            "point_count": len(filtered_points)
        }


# Global Singleton
performance_curve_engine = PerformanceCurveEngine()
