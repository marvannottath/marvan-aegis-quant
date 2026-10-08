"""
Aegis-Quant Capital Availability & Residual/Dust Engine.
Calculates strictly deployable tradeable capital across 9 balance buckets:
  1. Total Equity
  2. Broker Balance
  3. Available Cash
  4. Reserved Cash (Vault, pending withdrawals)
  5. Used Margin
  6. Open Order Reservation
  7. Non-Tradeable Residual / Dust
  8. Safety Buffer
  9. Deployable Tradeable Capital

Formula:
  Tradeable Capital = Available Cash - (Reserved Cash + Open Order Reservation + Non-Tradeable Residual + Safety Buffer)

Asset Residual Status Classification:
  - TRADEABLE: Size meets broker minimum notional and step requirements
  - RESIDUAL / DUST: Quantity below broker minimum notional or freeze cap
  - NON_TRADEABLE: Asset temporarily suspended or illiquid
  - LOCKED: Committed to active orders or pending settlement
  - PENDING_SETTLEMENT: T+1 or T+2 unsettled proceeds
"""

from dataclasses import dataclass, asdict
from typing import Dict, Any, List, Optional

# Classification constants
STATUS_TRADEABLE = "TRADEABLE"
STATUS_RESIDUAL = "RESIDUAL"
STATUS_NON_TRADEABLE = "NON_TRADEABLE"
STATUS_LOCKED = "LOCKED"
STATUS_PENDING_SETTLEMENT = "PENDING_SETTLEMENT"

# Broker Min Notional Thresholds (dynamic defaults)
VENUE_MIN_NOTIONAL = {
    "BINANCE": 5.0,     # 5.0 USDT minimum notional for Spot orders
    "UPSTOX": 1.0,      # ₹1 minimum notional
    "MT5": 10.0,        # $10 min margin
    "CTRADER": 10.0
}


@dataclass
class CapitalBreakdown:
    account_id: str
    currency: str
    total_equity: float
    broker_balance: float
    available_cash: float
    reserved_cash: float
    used_margin: float
    open_orders_reserved: float
    residual_dust_capital: float
    safety_buffer: float
    tradeable_capital: float
    can_open_new_trades: bool
    residual_assets: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class CapitalAvailabilityEngine:
    """Authoritative capital availability evaluator with dust/residual resilience."""

    def __init__(self, default_safety_buffer_pct: float = 2.0):
        self.default_safety_buffer_pct = default_safety_buffer_pct

    def classify_asset(
        self,
        symbol: str,
        quantity: float,
        current_price: float,
        broker: str = "BINANCE",
        is_locked: bool = False,
        is_pending: bool = False
    ) -> Dict[str, Any]:
        """Classify asset balance into TRADEABLE, RESIDUAL, LOCKED, etc."""
        if is_locked:
            return {
                "symbol": symbol,
                "quantity": quantity,
                "notional_value": round(quantity * current_price, 2),
                "status": STATUS_LOCKED,
                "reason": "Committed to active orders or margin collateral"
            }
        if is_pending:
            return {
                "symbol": symbol,
                "quantity": quantity,
                "notional_value": round(quantity * current_price, 2),
                "status": STATUS_PENDING_SETTLEMENT,
                "reason": "Awaiting venue clearing settlement"
            }

        notional = quantity * current_price
        min_notional = VENUE_MIN_NOTIONAL.get(broker.upper(), 5.0)

        if notional < min_notional:
            return {
                "symbol": symbol,
                "quantity": quantity,
                "notional_value": round(notional, 4),
                "status": STATUS_RESIDUAL,
                "reason": f"Value ({notional:.2f}) below broker min notional ({min_notional:.2f})"
            }

        return {
            "symbol": symbol,
            "quantity": quantity,
            "notional_value": round(notional, 2),
            "status": STATUS_TRADEABLE,
            "reason": "Meets broker execution constraints"
        }

    def compute_tradeable_capital(
        self,
        account_id: str,
        total_equity: float,
        broker_balance: float,
        available_cash: float,
        used_margin: float = 0.0,
        reserved_cash: float = 0.0,
        open_orders_reserved: float = 0.0,
        residual_dust_capital: float = 0.0,
        currency: str = "USDT",
        broker: str = "BINANCE",
        safety_buffer_pct: Optional[float] = None,
        residual_assets: Optional[List[Dict[str, Any]]] = None
    ) -> CapitalBreakdown:
        """
        Compute true deployable tradeable capital.
        Prevents dust or small trapped remainder from blocking the whole system.
        """
        buf_pct = safety_buffer_pct if safety_buffer_pct is not None else self.default_safety_buffer_pct
        safety_buffer = round(max(0.0, total_equity * (buf_pct / 100.0)), 2)

        # Deployable Tradeable Capital Calculation
        # Raw available cash minus safety reserve, pending orders, and locked funds
        deductions = (
            max(0.0, reserved_cash) +
            max(0.0, open_orders_reserved) +
            max(0.0, residual_dust_capital) +
            safety_buffer
        )

        tradeable = max(0.0, round(available_cash - deductions, 2))

        # Check if tradeable capital is sufficient for at least one minimum notional order
        min_notional = VENUE_MIN_NOTIONAL.get(broker.upper(), 5.0)
        can_trade = tradeable >= min_notional

        return CapitalBreakdown(
            account_id=account_id,
            currency=currency,
            total_equity=round(total_equity, 2),
            broker_balance=round(broker_balance, 2),
            available_cash=round(available_cash, 2),
            reserved_cash=round(reserved_cash, 2),
            used_margin=round(used_margin, 2),
            open_orders_reserved=round(open_orders_reserved, 2),
            residual_dust_capital=round(residual_dust_capital, 2),
            safety_buffer=safety_buffer,
            tradeable_capital=tradeable,
            can_open_new_trades=can_trade,
            residual_assets=residual_assets or []
        )

    compute_breakdown = compute_tradeable_capital


# Global singleton
capital_availability_engine = CapitalAvailabilityEngine()
