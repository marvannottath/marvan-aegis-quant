"""
US Economic News & Fed Event Auto-Pause Safety Filter Module.
Tracks high-impact macroeconomic events (Fed Interest Rate Decisions, CPI Inflation Data, NFP Employment).
Automatically locks out autonomous AI trade placement during high-volatility news windows.
"""

import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple

class EconomicCalendarFilter:
    def __init__(self):
        self.news_events: List[Dict[str, Any]] = [
            {
                "id": "EVT-101",
                "title": "US Federal Reserve FOMC Interest Rate Decision",
                "impact": "HIGH",
                "currency": "USD",
                "asset_affected": "XAUUSD / Forex",
                "scheduled_time": (datetime.now() + timedelta(hours=18)).strftime("%Y-%m-%d %H:%M:%S"),
                "status": "SCHEDULED"
            },
            {
                "id": "EVT-102",
                "title": "US Core Inflation CPI (YoY) Release",
                "impact": "HIGH",
                "currency": "USD",
                "asset_affected": "XAUUSD / Forex",
                "scheduled_time": (datetime.now() + timedelta(hours=14)).strftime("%Y-%m-%d %H:%M:%S"),
                "status": "SCHEDULED"
            },
            {
                "id": "EVT-103",
                "title": "US Non-Farm Payrolls (NFP) Employment Data",
                "impact": "HIGH",
                "currency": "USD",
                "asset_affected": "XAUUSD / Forex",
                "scheduled_time": (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S"),
                "status": "SCHEDULED"
            }
        ]
        self.manual_override_active = False

    def is_news_lockout_active(self) -> Tuple[bool, str]:
        """
        Check if system should be locked out due to high-impact economic news.
        Returns (is_locked, reason).
        """
        if self.manual_override_active:
            return False, "Manual News Lockout Override Enabled"

        now = datetime.now()
        for evt in self.news_events:
            if evt["impact"] == "HIGH":
                try:
                    evt_time = datetime.strptime(evt["scheduled_time"], "%Y-%m-%d %H:%M:%S")
                    diff_minutes = (evt_time - now).total_seconds() / 60.0
                    
                    # 15 minutes before or 15 minutes after news event
                    if -15.0 <= diff_minutes <= 15.0:
                        return True, f"HIGH VOLATILITY NEWS LOCKOUT: {evt['title']} ({int(diff_minutes)}m window)"
                except Exception:
                    pass

        return False, "NO_HIGH_IMPACT_NEWS"

    def get_upcoming_events(self) -> List[Dict[str, Any]]:
        """Fetch list of upcoming economic calendar events."""
        lockout_active, reason = self.is_news_lockout_active()
        return {
            "lockout_active": lockout_active,
            "lockout_reason": reason,
            "events": self.news_events
        }

# Global Economic Calendar Instance
economic_filter = EconomicCalendarFilter()
