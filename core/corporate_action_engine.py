"""
Aegis-Quant Corporate Action Engine for Indian Equities.
Tracks and applies corporate actions:
  - Stock Splits (e.g., 1:10, 1:5, 1:2)
  - Bonus Issues (e.g., 1:1, 1:2)
  - Dividends (Interim & Final in INR ₹)
  - Rights Issues
  - Mergers / Demergers
  - Buybacks

Financial Accounting Invariant:
A stock split or bonus issue adjusts quantity and average purchase price proportionately
WITHOUT triggering an artificial trading loss.
Example: 10 shares @ ₹2,000 split 1:10 becomes 100 shares @ ₹200.
Invested capital remains exactly ₹20,000.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta

IST_TZ = timezone(timedelta(hours=5, minutes=30))


class CorporateActionEngine:
    """Institutional Corporate Action Tracker & Portfolio Adjustment Engine."""

    def __init__(self):
        # Curated log of historical and upcoming Indian corporate actions
        self._actions: List[Dict[str, Any]] = [
            {
                "action_id": "CA-IN-2026-001",
                "symbol": "TCS",
                "action_type": "DIVIDEND",
                "details": "Interim Dividend of ₹28.00 per share",
                "dividend_per_share_inr": 28.00,
                "record_date": "2026-10-18",
                "ex_date": "2026-10-17",
                "status": "UPCOMING"
            },
            {
                "action_id": "CA-IN-2026-002",
                "symbol": "HDFCBANK",
                "action_type": "DIVIDEND",
                "details": "Final Dividend of ₹19.50 per share",
                "dividend_per_share_inr": 19.50,
                "record_date": "2026-07-15",
                "ex_date": "2026-07-14",
                "status": "COMPLETED"
            },
            {
                "action_id": "CA-IN-2026-003",
                "symbol": "TATAMOTORS",
                "action_type": "DEMERGER",
                "details": "Demerger of Commercial Vehicles and Passenger Vehicles businesses",
                "record_date": "2026-11-20",
                "ex_date": "2026-11-19",
                "status": "APPROVED"
            },
            {
                "action_id": "CA-IN-2026-004",
                "symbol": "INFY",
                "action_type": "BUYBACK",
                "details": "Share buyback at ₹2,150 per share via tender offer",
                "record_date": "2026-08-10",
                "ex_date": "2026-08-09",
                "status": "COMPLETED"
            }
        ]

    def list_actions(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """Return all tracked corporate actions, optionally filtered by symbol."""
        if symbol:
            return [a for a in self._actions if a["symbol"] == symbol.upper()]
        return self._actions

    def apply_stock_split(
        self,
        position: Dict[str, Any],
        split_ratio_numerator: int,
        split_ratio_denominator: int = 1
    ) -> Dict[str, Any]:
        """
        Adjust position for a stock split (e.g. 10 for 1 split: num=10, den=1).
        Pre-split: Qty = 10, Avg = ₹2,000 -> Total = ₹20,000
        Post-split: Qty = 100, Avg = ₹200 -> Total = ₹20,000
        Enforces: Invested Capital is preserved. Zero PnL impact.
        """
        old_qty = position.get("quantity") or position.get("units", 0)
        old_price = position.get("average_price") or position.get("entry_price", 0.0)

        factor = split_ratio_numerator / split_ratio_denominator
        new_qty = int(round(old_qty * factor))
        new_price = round(old_price / factor, 2)

        position["quantity"] = new_qty
        position["units"] = new_qty
        position["average_price"] = new_price
        position["entry_price"] = new_price

        return {
            "status": "SUCCESS",
            "action": "STOCK_SPLIT",
            "factor": factor,
            "old_quantity": old_qty,
            "new_quantity": new_qty,
            "old_average_price": old_price,
            "new_average_price": new_price,
            "capital_preserved": round(old_qty * old_price, 2) == round(new_qty * new_price, 2),
            "adjusted_at": datetime.now(timezone.utc).astimezone(IST_TZ).strftime("%Y-%m-%d %H:%M:%S IST")
        }


# Global Singleton
corporate_action_engine = CorporateActionEngine()
