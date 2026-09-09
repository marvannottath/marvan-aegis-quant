"""
Aegis-Quant Provider-Neutral Universal Trading Models.
Defines canonical data contracts for:
  - UniversalOrder
  - UniversalPosition
  - UniversalPnLEngine

Allows Binance, Upstox, and Forex trades to flow through the identical risk,
telemetry, analytics, and accounting pipelines without coupling to specific broker APIs.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta

IST_TZ = timezone(timedelta(hours=5, minutes=30))


class UniversalOrder:
    """Canonical Order Data Model."""

    def __init__(
        self,
        order_id: str,
        user_id: str,
        account_id: str,
        environment: str,
        asset_class: str,  # INDIAN_EQUITY | FOREX | CRYPTO | ETF
        venue: str,        # UPSTOX | BINANCE | INSTITUTIONAL_FX | PAPER
        symbol: str,
        exchange: str,     # NSE | BSE | BINANCE | FOREX
        side: str,         # BUY | SELL
        quantity: float,
        price: float,
        order_type: str = "MARKET",  # MARKET | LIMIT | SL | SL-M
        product: str = "CNC",        # CNC | MIS | SPOT | DERIVATIVE
        strategy_id: str = "ENSEMBLE_V2",
        strategy_version: str = "2.4",
        signal_id: str = "",
        risk_decision: str = "APPROVED",
        execution_algorithm: str = "DIRECT_ROUTING",
        venue_order_id: Optional[str] = None,
        status: str = "CREATED",
        created_at: Optional[str] = None,
        fees: float = 0.0,
        slippage: float = 0.0,
        currency: str = "INR",
        metadata: Optional[Dict[str, Any]] = None
    ):
        now_str = datetime.now(timezone.utc).astimezone(IST_TZ).strftime("%Y-%m-%d %H:%M:%S IST")
        self.order_id = order_id
        self.user_id = user_id
        self.account_id = account_id
        self.environment = environment
        self.asset_class = asset_class
        self.venue = venue
        self.symbol = symbol
        self.exchange = exchange
        self.side = side
        self.quantity = quantity
        self.price = price
        self.order_type = order_type
        self.product = product
        self.strategy_id = strategy_id
        self.strategy_version = strategy_version
        self.signal_id = signal_id
        self.risk_decision = risk_decision
        self.execution_algorithm = execution_algorithm
        self.venue_order_id = venue_order_id
        self.status = status
        self.created_at = created_at or now_str
        self.submitted_at: Optional[str] = None
        self.acknowledged_at: Optional[str] = None
        self.filled_at: Optional[str] = None
        self.cancelled_at: Optional[str] = None
        self.fees = fees
        self.slippage = slippage
        self.currency = currency
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "order_id": self.order_id,
            "user_id": self.user_id,
            "account_id": self.account_id,
            "environment": self.environment,
            "asset_class": self.asset_class,
            "venue": self.venue,
            "symbol": self.symbol,
            "exchange": self.exchange,
            "side": self.side,
            "quantity": self.quantity,
            "price": self.price,
            "order_type": self.order_type,
            "product": self.product,
            "strategy_id": self.strategy_id,
            "strategy_version": self.strategy_version,
            "signal_id": self.signal_id,
            "risk_decision": self.risk_decision,
            "execution_algorithm": self.execution_algorithm,
            "venue_order_id": self.venue_order_id,
            "status": self.status,
            "created_at": self.created_at,
            "submitted_at": self.submitted_at,
            "acknowledged_at": self.acknowledged_at,
            "filled_at": self.filled_at,
            "cancelled_at": self.cancelled_at,
            "fees": self.fees,
            "slippage": self.slippage,
            "currency": self.currency,
            "metadata": self.metadata
        }


class UniversalPosition:
    """Canonical Position Data Model."""

    def __init__(
        self,
        position_id: str,
        user_id: str,
        account_id: str,
        venue: str,
        asset_class: str,
        symbol: str,
        exchange: str,
        quantity: float,
        average_price: float,
        market_price: float,
        currency: str = "INR",
        product: str = "CNC",
        side: str = "BUY"
    ):
        self.position_id = position_id
        self.user_id = user_id
        self.account_id = account_id
        self.venue = venue
        self.asset_class = asset_class
        self.symbol = symbol
        self.exchange = exchange
        self.quantity = quantity
        self.average_price = average_price
        self.market_price = market_price
        self.currency = currency
        self.product = product
        self.side = side
        self.updated_at = datetime.now(timezone.utc).astimezone(IST_TZ).strftime("%Y-%m-%d %H:%M:%S IST")

    @property
    def market_value(self) -> float:
        return round(self.quantity * self.market_price, 2)

    @property
    def unrealized_pnl(self) -> float:
        if self.side == "BUY":
            return round((self.market_price - self.average_price) * self.quantity, 2)
        else:
            return round((self.average_price - self.market_price) * self.quantity, 2)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "position_id": self.position_id,
            "user_id": self.user_id,
            "account_id": self.account_id,
            "venue": self.venue,
            "asset_class": self.asset_class,
            "symbol": self.symbol,
            "exchange": self.exchange,
            "quantity": self.quantity,
            "average_price": self.average_price,
            "market_price": self.market_price,
            "market_value": self.market_value,
            "unrealized_pnl": self.unrealized_pnl,
            "currency": self.currency,
            "currency_symbol": "₹" if self.currency == "INR" else "$",
            "product": self.product,
            "side": self.side,
            "updated_at": self.updated_at
        }


class UniversalPnLEngine:
    """Universal PnL Engine Strictly Partitioned by Currency and Asset Class."""

    @staticmethod
    def calculate_pnl(trades: List[Dict[str, Any]], asset_class: Optional[str] = None) -> Dict[str, Any]:
        filtered = [t for t in trades if asset_class is None or t.get("asset_class") == asset_class]
        realized = sum(float(t.get("realized_pnl", 0.0) or t.get("pnl_usd", 0.0)) for t in filtered)
        fees = sum(float(t.get("fees", 0.0)) for t in filtered)
        net = realized - fees
        return {
            "asset_class": asset_class or "ALL",
            "trades_count": len(filtered),
            "gross_realized_pnl": round(realized, 2),
            "fees_paid": round(fees, 2),
            "net_realized_pnl": round(net, 2)
        }
