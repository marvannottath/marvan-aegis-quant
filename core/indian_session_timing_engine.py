"""
AEGIS-QUANT Institutional Indian Market Session & ORB Engine.
Enforces institutional time-of-day filters for NSE Cash / MIS Intraday Trading:
  1. 09:00 - 09:15 IST: Pre-Market Call Auction (Entries: BLOCKED)
  2. 09:15 - 09:45 IST: Opening Volatility & 30-min ORB Formation (Entries: BLOCKED)
     Tracks 30-minute High & Low for each stock to establish breakout thresholds.
  3. 09:45 - 11:45 IST: Morning Trend Momentum Session (Entries: ALLOWED)
     Executes clean breakouts above ORB High (BUY) or below ORB Low (SHORT).
  4. 11:45 - 13:15 IST: Midday Lunch Chop Zone (Entries: BLOCKED)
     Eliminates low-volume false breakouts and sideways whipsaws.
  5. 13:15 - 14:45 IST: Afternoon Institutional Wave (Entries: ALLOWED)
     Captures European market open trend continuation.
  6. 14:45 - 15:10 IST: Pre-Squareoff Cooldown (Entries: BLOCKED)
  7. 15:10 - 15:30 IST: Intraday MIS Squareoff Only (Handled by Sentinel)
"""

import json
from pathlib import Path
from typing import Dict, Any, Tuple, Optional
from datetime import datetime, timezone, timedelta

IST_TZ = timezone(timedelta(hours=5, minutes=30))
ORB_DB = Path(__file__).resolve().parent.parent / "data" / "indian_orb_session_state.json"


class IndianSessionTimingEngine:
    def __init__(self):
        self.session_date: str = ""
        self.orb_ranges: Dict[str, Dict[str, float]] = {}  # symbol -> {"high": float, "low": float, "open": float}
        self._load_state()

    def _get_ist_now(self) -> datetime:
        return datetime.now(timezone.utc).astimezone(IST_TZ)

    def _load_state(self):
        ORB_DB.parent.mkdir(parents=True, exist_ok=True)
        today = self._get_ist_now().strftime("%Y-%m-%d")
        if ORB_DB.exists():
            try:
                with open(ORB_DB, "r") as f:
                    data = json.load(f)
                    if data.get("session_date") == today:
                        self.session_date = today
                        self.orb_ranges = data.get("orb_ranges", {})
                        return
            except Exception:
                pass

        # Reset for fresh day
        self.session_date = today
        self.orb_ranges = {}
        self._save_state()

    def _save_state(self):
        try:
            tmp = ORB_DB.with_suffix(".tmp")
            with open(tmp, "w") as f:
                json.dump({
                    "session_date": self.session_date,
                    "orb_ranges": self.orb_ranges,
                    "updated_at": self._get_ist_now().strftime("%Y-%m-%d %H:%M:%S IST")
                }, f, indent=2)
            tmp.replace(ORB_DB)
        except Exception:
            pass

    def get_current_session_window(self) -> Dict[str, Any]:
        """
        Evaluate current Indian market timing window and entry permission.
        """
        now = self._get_ist_now()
        today = now.strftime("%Y-%m-%d")
        if self.session_date != today:
            self._load_state()

        # Weekend Check
        if now.weekday() >= 5:
            return {
                "session": "WEEKEND",
                "is_entry_allowed": False,
                "reason": "Market closed on weekends (Saturday/Sunday)",
                "time_ist": now.strftime("%H:%M:%S IST")
            }

        time_val = now.hour * 100 + now.minute

        if time_val < 900:
            return {
                "session": "PRE_MARKET_CLOSED",
                "is_entry_allowed": False,
                "reason": "Market opens at 09:15 AM IST",
                "time_ist": now.strftime("%H:%M:%S IST")
            }
        elif 900 <= time_val < 915:
            return {
                "session": "PRE_MARKET_AUCTION",
                "is_entry_allowed": False,
                "reason": "NSE Pre-market auction session (09:00 - 09:15 AM IST)",
                "time_ist": now.strftime("%H:%M:%S IST")
            }
        elif 915 <= time_val < 945:
            return {
                "session": "ORB_FORMATION_WINDOW",
                "is_entry_allowed": False,
                "reason": "Opening Volatility / 30-min ORB Formation (09:15 - 09:45 AM IST). Building High/Low ranges to prevent whipsaws.",
                "time_ist": now.strftime("%H:%M:%S IST")
            }
        elif 945 <= time_val < 1145:
            return {
                "session": "MORNING_TREND_WINDOW",
                "is_entry_allowed": True,
                "reason": "Prime Morning Trend Session (09:45 - 11:45 AM IST). Institutional momentum active.",
                "time_ist": now.strftime("%H:%M:%S IST")
            }
        elif 1145 <= time_val < 1315:
            return {
                "session": "LUNCH_CHOP_WINDOW",
                "is_entry_allowed": False,
                "reason": "Midday Lunch Lull / Chop Zone (11:45 AM - 01:15 PM IST). New entries blocked to eliminate false breakouts.",
                "time_ist": now.strftime("%H:%M:%S IST")
            }
        elif 1315 <= time_val < 1445:
            return {
                "session": "AFTERNOON_TREND_WINDOW",
                "is_entry_allowed": True,
                "reason": "Afternoon Trend Continuation / European Open (01:15 - 02:45 PM IST). Active momentum window.",
                "time_ist": now.strftime("%H:%M:%S IST")
            }
        elif 1445 <= time_val < 1510:
            return {
                "session": "PRE_CLOSE_FREEZE",
                "is_entry_allowed": False,
                "reason": "Pre-Close Freeze (02:45 - 03:10 PM IST). Approaching square-off; new entries blocked.",
                "time_ist": now.strftime("%H:%M:%S IST")
            }
        elif 1510 <= time_val <= 1530:
            return {
                "session": "AUTO_SQUAREOFF_ONLY",
                "is_entry_allowed": False,
                "reason": "Intraday Square-off Window (03:10 - 03:30 PM IST). Exits only.",
                "time_ist": now.strftime("%H:%M:%S IST")
            }
        else:
            return {
                "session": "MARKET_CLOSED",
                "is_entry_allowed": False,
                "reason": "Market closed after 03:30 PM IST.",
                "time_ist": now.strftime("%H:%M:%S IST")
            }

    def update_tick(self, symbol: str, price: float):
        """Record high and low during the 09:15 - 09:45 ORB formation window."""
        if price <= 0:
            return

        now = self._get_ist_now()
        time_val = now.hour * 100 + now.minute

        # Track tick during opening range or update ranges
        clean_sym = symbol.replace("-EQ", "").upper()
        if clean_sym not in self.orb_ranges:
            self.orb_ranges[clean_sym] = {
                "high": price,
                "low": price,
                "open": price,
                "last": price
            }
        else:
            rec = self.orb_ranges[clean_sym]
            rec["last"] = price
            # Only expand ORB high/low during 09:15 to 09:45 AM
            if 915 <= time_val <= 945:
                rec["high"] = max(rec["high"], price)
                rec["low"] = min(rec["low"], price)

        # Periodic save
        if now.second % 30 == 0:
            self._save_state()

    def evaluate_orb_signal(self, symbol: str, current_price: float) -> Dict[str, Any]:
        """
        Check if current price has cleanly broken out of the 30-min Opening Range.
        Returns:
          signal: 'BUY' (Breakout above High) | 'SELL' (Breakout below Low) | 'NEUTRAL'
        """
        clean_sym = symbol.replace("-EQ", "").upper()
        rec = self.orb_ranges.get(clean_sym)
        if not rec:
            return {"signal": "NEUTRAL", "reason": "No ORB range established"}

        high = rec["high"]
        low = rec["low"]
        range_pts = high - low
        range_pct = (range_pts / low * 100.0) if low > 0 else 0.0

        # Require a valid opening range (> 0.25% range)
        if range_pct < 0.25:
            return {"signal": "NEUTRAL", "reason": f"Range too tight ({range_pct:.2f}%)"}

        # Buffer of 0.05% above high / below low to confirm true breakout
        breakout_buffer = round(high * 0.0005, 2)

        if current_price > (high + breakout_buffer):
            return {
                "signal": "BUY",
                "orb_high": high,
                "orb_low": low,
                "current_price": current_price,
                "breakout_pct": round((current_price - high) / high * 100.0, 2),
                "reason": f"ORB Bullish Breakout above 30m High ₹{high:,.2f}"
            }
        elif current_price < (low - breakout_buffer):
            return {
                "signal": "SELL",
                "orb_high": high,
                "orb_low": low,
                "current_price": current_price,
                "breakout_pct": round((low - current_price) / low * 100.0, 2),
                "reason": f"ORB Bearish Breakdown below 30m Low ₹{low:,.2f}"
            }

        return {
            "signal": "NEUTRAL",
            "orb_high": high,
            "orb_low": low,
            "current_price": current_price,
            "reason": f"Inside 30m Opening Range (₹{low:,.2f} - ₹{high:,.2f})"
        }


# Global Singleton
indian_session_timing_engine = IndianSessionTimingEngine()
