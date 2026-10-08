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
        environment: str = "AEGIS_QUANT_MASTER",
        workspace: Optional[str] = None
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

        opening_amt = 100000.0
        if environment in ["BINANCE_TESTNET", "BINANCE_DEMO", "BINANCE_TESTNET_DEMO"]:
            opening_amt = 19950.55
        elif environment in ["BINANCE_LIVE", "BINANCE_LIVE_REAL"]:
            opening_amt = paper_broker.pools.get(environment, {}).get("initial_capital", 0.0)
        elif environment in paper_broker.pools:
            opening_amt = paper_broker.pools[environment].get("initial_capital", 100000.0)

        # Collect closed trades & vault sweeps strictly for the requested environment
        sweeps = profit_vault.get_sweep_history(environment)
        if environment == "AEGIS_QUANT_MASTER":
            trades = list(paper_broker.trade_history)
        elif environment in paper_broker.pools:
            pool_data = paper_broker.pools[environment]
            trades = pool_data.get("trade_history", [])
        else:
            trades = []

        def _parse_ts(ts_str: str) -> Optional[datetime]:
            try:
                clean_str = str(ts_str).replace(" IST", "").strip()
                dt = datetime.strptime(clean_str, "%Y-%m-%d %H:%M:%S")
                return dt.replace(tzinfo=IST_TZ)
            except Exception:
                return None

        # Reconcile current authoritative equity from Single Source of Truth
        from core.position_snapshot_service import position_snapshot_service
        from core.workspace_manager import workspace_manager

        if workspace:
            target_ws = workspace_manager._normalize_workspace(workspace)
        elif "INDIA" in environment or "UPSTOX" in environment:
            target_ws = "INDIA"
        elif "FOREX" in environment or "MT5" in environment or environment == "AEGIS_QUANT_MASTER":
            target_ws = "FOREX_GOLD"
        env_mode = "LIVE" if str(environment).upper() in ["LIVE", "BINANCE_LIVE_REAL", "MT5_LIVE_REAL", "UPSTOX_LIVE"] else "PAPER"
        try:
            agg = position_snapshot_service.get_portfolio_aggregate(target_ws, environment=env_mode)
            cur_equity = round(float(agg.get("total_equity", opening_amt)), 2)
        except Exception:
            if environment in paper_broker.pools and environment != "AEGIS_QUANT_MASTER":
                pool_data = paper_broker.pools[environment]
                v_cash = float(pool_data.get("virtual_cash", opening_amt))
                v_vault = float(profit_vault.get_vault_balance(environment))
                v_pos = pool_data.get("positions", {})
                v_margin = sum(float(p.get("capital_allocated", p.get("margin", 0.0))) for p in v_pos.values()) if isinstance(v_pos, dict) else 0.0
                cur_equity = round(v_cash + v_vault + v_margin, 2)
            else:
                # Strictly isolate fallback by target_ws; never bleed un-scoped paper_broker.equity
                ws_pool_map = {
                    "INDIA": "AEGIS_INDIA_INR",
                    "FOREX_GOLD": "MT5_LIVE_REAL",
                    "CRYPTO": "BINANCE_LIVE_REAL"
                }
                mapped_pool = ws_pool_map.get(target_ws)
                if mapped_pool and mapped_pool in paper_broker.pools:
                    p_data = paper_broker.pools[mapped_pool]
                    p_cash = float(p_data.get("virtual_cash", opening_amt))
                    p_vault = float(profit_vault.get_vault_balance(mapped_pool))
                    p_pos = p_data.get("positions", {})
                    p_margin = sum(float(p.get("capital_allocated", p.get("margin", 0.0))) for p in p_pos.values()) if isinstance(p_pos, dict) else 0.0
                    cur_equity = round(p_cash + p_vault + p_margin, 2)
                else:
                    cur_equity = round(float(opening_amt), 2)

        # Build clean non-double-counted event series
        events = []
        if trades:
            # Each trade in trade_history already contains the exact realized pnl_usd
            for t in trades:
                ts_val = t.get("timestamp", now_str)
                pnl = float(t.get("pnl_usd") or t.get("realized_pnl") or 0.0)
                events.append({"timestamp": ts_val, "pnl": pnl})
        elif sweeps:
            # Fallback if only vault sweeps exist
            for s in sweeps:
                ts_val = s.get("timestamp", now_str)
                amt = float(s.get("sweep_amount") or s.get("realized_profit") or 0.0)
                if amt != 0.0:
                    events.append({"timestamp": ts_val, "pnl": amt})

        if not events:
            val = cur_equity if metric == "equity" else 0.0
            # Generate 12 evenly-spaced points across the window for continuous line rendering
            num_baseline_points = 12
            total_seconds = max(60.0, (now_dt - cutoff_dt).total_seconds())
            sec_step = total_seconds / (num_baseline_points - 1)
            baseline_points = []
            for i in range(num_baseline_points):
                pt_dt = cutoff_dt + timedelta(seconds=i * sec_step)
                baseline_points.append({
                    "timestamp": pt_dt.strftime("%Y-%m-%d %H:%M:%S"),
                    "value": val
                })
            return {
                "status": "SUCCESS",
                "metric": metric,
                "range": time_range,
                "environment": environment,
                "points": baseline_points,
                "latest": val,
                "min": val,
                "max": val,
                "point_count": len(baseline_points),
                "baseline_anchor": True
            }

        # Sort chronologically
        events.sort(key=lambda x: x.get("timestamp", ""))
        total_historical_pnl = sum(e["pnl"] for e in events)

        # Baseline equity at the beginning of all recorded history
        historical_base_equity = round(cur_equity - total_historical_pnl, 2)

        # Pre-cutoff accumulation
        pre_cutoff_pnl = 0.0
        window_events = []

        for ev in events:
            ev_dt = _parse_ts(ev["timestamp"])
            if time_range != "ALL" and ev_dt and ev_dt < cutoff_dt:
                pre_cutoff_pnl += ev["pnl"]
            else:
                window_events.append(ev)

        # Baseline equity at the start of the timeframe window
        start_equity = round(historical_base_equity + pre_cutoff_pnl, 2)
        start_ts = cutoff_dt.strftime("%Y-%m-%d %H:%M:%S") if time_range != "ALL" else (events[0]["timestamp"] if events else now_str)

        points = []
        running_equity = start_equity
        running_pnl = 0.0
        peak_equity = start_equity

        # First anchor point of the timeframe
        points.append({
            "timestamp": start_ts,
            "value": start_equity if metric == "equity" else 0.0
        })

        for ev in window_events:
            pnl_amt = ev["pnl"]
            running_pnl += pnl_amt
            running_equity += pnl_amt
            if running_equity > peak_equity:
                peak_equity = running_equity

            dd_pct = round(((peak_equity - running_equity) / peak_equity * 100.0), 2) if peak_equity > 0 else 0.0

            if metric == "equity":
                val = round(running_equity, 2)
            elif metric == "pnl":
                val = round(running_pnl, 2)
            else:
                val = dd_pct

            points.append({
                "timestamp": ev["timestamp"],
                "value": val
            })

        # Ensure current terminal point exactly matches authoritative live balance
        if cur_equity > peak_equity:
            peak_equity = cur_equity
        live_dd = round(((peak_equity - cur_equity) / peak_equity * 100.0), 2) if peak_equity > 0 else 0.0

        if metric == "equity":
            live_val = cur_equity
        elif metric == "pnl":
            live_val = round(running_pnl, 2)
        else:
            live_val = live_dd

        points.append({
            "timestamp": now_str,
            "value": live_val
        })

        # Deduplicate points by timestamp
        filtered_points = []
        seen = set()
        for p in points:
            if p["timestamp"] not in seen:
                seen.add(p["timestamp"])
                filtered_points.append(p)

        # Downsample points to a maximum of 100 points for smooth Chart.js rendering
        if len(filtered_points) > 100:
            step = (len(filtered_points) - 1) / 99.0
            downsampled = [filtered_points[int(round(i * step))] for i in range(99)]
            if filtered_points[-1] not in downsampled:
                downsampled.append(filtered_points[-1])
            filtered_points = downsampled

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
