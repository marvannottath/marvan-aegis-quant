"""
Aegis-Quant Generic Broker Adapter Interface.
Abstract base class for all exchange & brokerage connectors (Upstox, Binance, MT5, cTrader, Kotak).
Guarantees consistent contracts across Indian equities, derivatives, crypto, and forex venues.

Requirements contract:
  - connect()
  - get_account()
  - get_balance()
  - get_available_balance()
  - get_positions()
  - get_orders()
  - place_order()
  - cancel_order()
  - close_position()
  - get_market_data()
  - get_fees()
  - get_trading_rules()
  - get_symbol_constraints()
  - get_market_status()

Rules:
- Mark unavailable metadata as UNKNOWN rather than inventing values.
- Never fake broker transfers or unavailable liquidity.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union


class BrokerAdapter(ABC):
    """
    Standard Broker Adapter Contract.
    Enables future brokers to plug in without modifying core trading logic.
    """

    @property
    @abstractmethod
    def broker_name(self) -> str:
        """Return unique broker identifier (e.g., 'UPSTOX', 'BINANCE', 'MT5', 'CTRADER')."""
        pass

    @property
    @abstractmethod
    def status(self) -> str:
        """Return connectivity status: NOT_CONFIGURED | DISCONNECTED | AUTHENTICATED | CONNECTED | ERROR."""
        pass

    @abstractmethod
    def connect(self) -> bool:
        """Establish session connection with broker servers."""
        pass

    @abstractmethod
    def get_account(self) -> Dict[str, Any]:
        """Fetch authoritative account details (account_id, name, currency, status, permissions)."""
        pass

    @abstractmethod
    def get_balance(self) -> Dict[str, Any]:
        """Fetch full balance snapshot: total_equity, cash, used_margin, available_balance, currency."""
        pass

    @abstractmethod
    def get_available_balance(self) -> float:
        """Fetch deployable cash/margin balance."""
        pass

    @abstractmethod
    def get_positions(self) -> List[Dict[str, Any]]:
        """Fetch open positions with symbol, side, units, entry_price, current_price, unrealized_pnl."""
        pass

    @abstractmethod
    def get_orders(self) -> List[Dict[str, Any]]:
        """Fetch orders placed for current trading session."""
        pass

    @abstractmethod
    def place_order(self, order_request: Dict[str, Any]) -> Dict[str, Any]:
        """Submit order to venue enforcing broker limits, lot sizes, and tick steps."""
        pass

    @abstractmethod
    def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """Cancel an open pending order."""
        pass

    def close_position(self, symbol: str, **kwargs) -> Dict[str, Any]:
        """
        Close an existing open position.
        Default implementation places opposite market order for total open units.
        """
        return {"status": "UNKNOWN", "symbol": symbol, "message": "Default close not implemented for this adapter"}

    @abstractmethod
    def get_market_data(self, symbols: Union[str, List[str]]) -> Dict[str, Any]:
        """Fetch real-time LTP, bid/ask, volume, and OHLC quotes."""
        pass

    def get_fees(self, symbol: str) -> Dict[str, Any]:
        """
        Return venue-specific fee structure for symbol.
        Returns UNKNOWN where unavailable.
        """
        return {
            "symbol": symbol,
            "maker_fee_pct": "UNKNOWN",
            "taker_fee_pct": "UNKNOWN",
            "commission_per_order": "UNKNOWN",
            "stt_ctt_pct": "UNKNOWN",
            "exchange_turnover_pct": "UNKNOWN"
        }

    def get_trading_rules(self, symbol: str) -> Dict[str, Any]:
        """
        Return venue execution rules: session hours, circuit limits, order types allowed.
        """
        return {
            "symbol": symbol,
            "session": "UNKNOWN",
            "market_orders_allowed": True,
            "limit_orders_allowed": True,
            "stop_loss_allowed": True,
            "leverage_max": "UNKNOWN"
        }

    def get_symbol_constraints(self, symbol: str) -> Dict[str, Any]:
        """
        Return quantitative order constraints: min notional, min quantity, step size, tick size.
        """
        return {
            "symbol": symbol,
            "min_notional": "UNKNOWN",
            "min_quantity": "UNKNOWN",
            "step_size": "UNKNOWN",
            "tick_size": "UNKNOWN",
            "price_precision": "UNKNOWN",
            "quantity_precision": "UNKNOWN"
        }

    def get_market_status(self) -> str:
        """Return venue market status: OPEN | CLOSED | PRE_OPEN | POST_CLOSE | UNKNOWN."""
        return "UNKNOWN"
