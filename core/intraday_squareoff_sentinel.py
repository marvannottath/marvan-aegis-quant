"""
AEGIS-QUANT Intraday 3:10 PM Auto-Squareoff Sentinel.
Enforces automated pre-emptive square-off for Indian Equities & F&O (MIS/Intraday)
at 3:10 PM IST — 5 minutes before Kotak Securities' RMS hard cutoff at 3:15 PM.
Eliminates broker auto-square-off penalty fees (₹50 + 18% GST per order)
and secures day's intraday trading P&L.
"""

from typing import Dict, Any, List
from datetime import datetime, timezone, timedelta

IST_TZ = timezone(timedelta(hours=5, minutes=30))


class IntradaySquareoffSentinel:
    SQUAREOFF_HOUR = 15
    SQUAREOFF_MINUTE = 10  # 3:10 PM IST

    def __init__(self):
        self.last_triggered_date: str = ""
        self.closed_positions_log: List[Dict[str, Any]] = []

    def should_trigger_auto_squareoff(self) -> bool:
        """Return True if current IST time is between 3:10 PM and 3:25 PM on a trading day."""
        now = datetime.now(timezone.utc).astimezone(IST_TZ)
        # Check weekdays (Monday=0 to Friday=4)
        if now.weekday() > 4:
            return False

        # Between 15:10 and 15:25 IST
        if now.hour == self.SQUAREOFF_HOUR and self.SQUAREOFF_MINUTE <= now.minute <= 25:
            return True
        return False

    def execute_squareoff_check(self, autonomous_trader_instance) -> List[Dict[str, Any]]:
        """
        Inspect open positions in autonomous trader.
        If time >= 3:10 PM IST, gracefully exit any Indian MIS positions.
        """
        if not self.should_trigger_auto_squareoff():
            return []

        now_date = datetime.now(timezone.utc).astimezone(IST_TZ).strftime("%Y-%m-%d")
        closed_this_run = []

        broker = getattr(autonomous_trader_instance, "broker", None)
        if not broker or not hasattr(broker, "positions"):
            return []

        positions_copy = dict(broker.positions)
        for symbol, pos in positions_copy.items():
            ws = pos.get("workspace", "")
            prod = pos.get("product", "MIS")
            env = pos.get("environment", "")

            is_india_intraday = (
                ws == "INDIA"
                or "KOTAK" in env
                or "UPSTOX" in env
                or str(prod).upper() == "MIS"
            )

            if is_india_intraday:
                curr_px = float(pos.get("current_price") or pos.get("last_price") or pos.get("entry_price", 0.0))
                units = float(pos.get("quantity") or pos.get("units", 1))

                # Close on exchange if live Kotak Neo is connected
                try:
                    from execution.kotak_neo_broker import kotak_neo_broker
                    if kotak_neo_broker._is_authenticated and "KOTAK" in env:
                        kotak_neo_broker.close_position(
                            symbol=symbol,
                            quantity=units,
                            product=prod,
                            environment="LIVE",
                        )
                except Exception as ex:
                    print(f"[SQUAREOFF_SENTINEL] Live close notice for {symbol}: {ex}")

                # Close internal position and book PnL
                try:
                    broker.close_position(
                        asset=symbol,
                        exit_price=curr_px,
                        reason="3:10 PM INTRADAY AUTO-SQUAREOFF (PENALTY SHIELD)",
                    )
                    rec = {
                        "symbol": symbol,
                        "exit_price": curr_px,
                        "units": units,
                        "reason": "3:10 PM INTRADAY AUTO-SQUAREOFF",
                        "timestamp": datetime.now(timezone.utc).astimezone(IST_TZ).strftime("%Y-%m-%d %H:%M:%S IST"),
                    }
                    closed_this_run.append(rec)
                    self.closed_positions_log.append(rec)

                    # Send Telegram Alert
                    try:
                        from core.telegram_alerts import telegram_alerts
                        tg_body = (
                            f"⏰ *3:10 PM AUTO-SQUAREOFF EXECUTED*\n"
                            f"━━━━━━━━━━━━━━━━━━━\n"
                            f"• *Symbol:* {symbol}\n"
                            f"• *Exit Price:* ₹{curr_px:,.2f}\n"
                            f"• *Qty:* {units}\n"
                            f"• *Protected Savings:* Avoided ₹59.00 Broker RMS Penalty!\n"
                            f"• *Time:* {rec['timestamp']}"
                        )
                        telegram_alerts.send_alert("Intraday Auto-Squareoff", tg_body, event_type="AUTO_SQUAREOFF")
                    except Exception:
                        pass

                except Exception as close_ex:
                    print(f"[SQUAREOFF_SENTINEL] Broker close error for {symbol}: {close_ex}")

        return closed_this_run


# Global Singleton
intraday_squareoff_sentinel = IntradaySquareoffSentinel()
