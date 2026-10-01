"""
Aegis PnL Calendar & Monthly Performance Heatmap Service.
Aggregates closed trades, multi-desk ledger writes, and walk-forward audited records into an
institutional daily calendar heatmap with profit/loss metrics, win-rate breakdown, and monthly KPIs.
"""

import time
import calendar
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional

IST_TZ = timezone(timedelta(hours=5, minutes=30))
USD_TO_INR_RATE = 87.50


class PnLCalendarService:
    def __init__(self):
        pass

    def get_monthly_calendar(self, year_month: Optional[str] = None, workspace: str = "ALL") -> Dict[str, Any]:
        """
        Build full monthly calendar grid with daily Net PnL, trades, and win rate.
        year_month format: 'YYYY-MM' (defaults to current IST month).
        """
        now = datetime.now(timezone.utc).astimezone(IST_TZ)
        if not year_month:
            year_month = now.strftime("%Y-%m")

        try:
            year, month = map(int, year_month.split("-"))
        except Exception:
            year, month = now.year, now.month
            year_month = f"{year:04d}-{month:02d}"

        _, num_days = calendar.monthrange(year, month)
        first_day_date = datetime(year, month, 1)
        first_day_weekday = first_day_date.weekday()  # 0=Monday .. 6=Sunday

        # Fetch real trades from unified historical_log_service
        real_trades_by_date: Dict[str, List[dict]] = {}
        try:
            from core.historical_log_service import historical_log_service
            start_str = f"{year_month}-01"
            end_str = f"{year_month}-{num_days:02d}"
            all_month_trades = historical_log_service.query(
                start_date=start_str,
                end_date=end_str,
                workspace=workspace if workspace != "ALL" else None
            )
            for t in all_month_trades:
                d_str = t.get("date") or str(t.get("timestamp", ""))[:10]
                if d_str:
                    real_trades_by_date.setdefault(d_str, []).append(t)
        except Exception as e:
            print(f"[PNL CALENDAR] Historical log service load notice: {e}")

        days_list: List[Dict[str, Any]] = []

        total_net_pnl_usd = 0.0
        total_gross_wins = 0.0
        total_gross_losses = 0.0
        total_trades = 0
        total_win_trades = 0
        total_loss_trades = 0
        green_days_count = 0
        red_days_count = 0
        best_day = {"date": "-", "pnl_usd": 0.0}
        worst_day = {"date": "-", "pnl_usd": 0.0}

        current_day_num = now.day if (year == now.year and month == now.month) else (num_days if (year < now.year or (year == now.year and month < now.month)) else 0)

        for day in range(1, num_days + 1):
            date_obj = datetime(year, month, day)
            date_str = date_obj.strftime("%Y-%m-%d")
            day_name = date_obj.strftime("%a")
            is_weekend = (date_obj.weekday() >= 5)

            is_future = (year == now.year and month == now.month and day > now.day) or (year > now.year) or (year == now.year and month > now.month)

            if is_future:
                days_list.append({
                    "date": date_str,
                    "day_of_month": day,
                    "day_of_week": day_name,
                    "is_weekend": is_weekend,
                    "is_future": True,
                    "trades_count": 0,
                    "win_rate": 0.0,
                    "net_pnl_usd": 0.0,
                    "net_pnl_inr": 0.0,
                    "status": "FUTURE",
                    "top_asset": "-",
                    "trades": []
                })
                continue

            day_real_trades = real_trades_by_date.get(date_str, [])

            if day_real_trades:
                d_trades_cnt = len(day_real_trades)
                d_wins = [t for t in day_real_trades if float(t.get("net_pnl", 0.0) or t.get("pnl_usd", 0.0)) > 0]
                d_losses = [t for t in day_real_trades if float(t.get("net_pnl", 0.0) or t.get("pnl_usd", 0.0)) < 0]
                d_win_cnt = len(d_wins)
                d_loss_cnt = len(d_losses)
                d_pnl = round(sum(float(t.get("net_pnl", 0.0) or t.get("pnl_usd", 0.0)) for t in day_real_trades), 2)
                d_top_asset = day_real_trades[0].get("symbol") or day_real_trades[0].get("asset") or "BTCUSDT"
            else:
                d_pnl = 0.0
                d_trades_cnt = 0
                d_win_cnt = 0
                d_loss_cnt = 0
                d_top_asset = "-"

            d_pnl = round(d_pnl, 2)
            d_pnl_inr = round(d_pnl * USD_TO_INR_RATE, 2)
            d_win_rate = round((d_win_cnt / d_trades_cnt) * 100.0, 1) if d_trades_cnt > 0 else 0.0

            if d_pnl > 0:
                d_status = "PROFIT"
                green_days_count += 1
                total_gross_wins += d_pnl
                if d_pnl > best_day["pnl_usd"]:
                    best_day = {"date": date_str, "pnl_usd": d_pnl}
            elif d_pnl < 0:
                d_status = "LOSS"
                red_days_count += 1
                total_gross_losses += abs(d_pnl)
                if d_pnl < worst_day["pnl_usd"]:
                    worst_day = {"date": date_str, "pnl_usd": d_pnl}
            else:
                d_status = "NEUTRAL"

            total_net_pnl_usd += d_pnl
            total_trades += d_trades_cnt
            total_win_trades += d_win_cnt
            total_loss_trades += d_loss_cnt

            days_list.append({
                "date": date_str,
                "day_of_month": day,
                "day_of_week": day_name,
                "is_weekend": is_weekend,
                "is_future": False,
                "trades_count": d_trades_cnt,
                "win_count": d_win_cnt,
                "loss_count": d_loss_cnt,
                "win_rate": d_win_rate,
                "net_pnl_usd": d_pnl,
                "net_pnl_inr": d_pnl_inr,
                "status": d_status,
                "top_asset": d_top_asset,
                "trades": day_real_trades
            })

        active_days = green_days_count + red_days_count
        win_day_rate = round((green_days_count / active_days) * 100.0, 1) if active_days > 0 else 0.0
        overall_win_rate = round((total_win_trades / total_trades) * 100.0, 1) if total_trades > 0 else 0.0
        profit_factor = round(total_gross_wins / max(0.01, total_gross_losses), 2) if total_gross_losses > 0 else (round(total_gross_wins, 2) if total_gross_wins > 0 else 1.0)

        month_dt = datetime(year, month, 1)
        month_name = month_dt.strftime("%B %Y").upper()

        return {
            "status": "SUCCESS",
            "year_month": year_month,
            "month_name": month_name,
            "calendar_metadata": {
                "year": year,
                "month": month,
                "num_days": num_days,
                "first_day_weekday": first_day_weekday
            },
            "kpis": {
                "total_net_pnl_usd": round(total_net_pnl_usd, 2),
                "total_net_pnl_inr": round(total_net_pnl_usd * USD_TO_INR_RATE, 2),
                "green_days": green_days_count,
                "red_days": red_days_count,
                "win_day_rate": win_day_rate,
                "overall_win_rate": overall_win_rate,
                "total_trades": total_trades,
                "profit_factor": profit_factor,
                "best_day": best_day,
                "worst_day": worst_day
            },
            "days": days_list
        }


# Global singleton
pnl_calendar_service = PnLCalendarService()
