"""
Aegis-Quant Generic Broker Adapter Interface.
Abstract base class for all exchange & brokerage connectors (Upstox, Zerodha, Binance, FIX).
Allows new brokers to be added without modifying the core trading or risk engines.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional


class BrokerAdapter(ABC):
    """
    Abstract interface for all broker adapters.
    Guarantees consistent contracts across Indian equities, derivatives, and crypto venues.
    """

    @property
    @abstractmethod
    def broker_name(self) -> str:
        """Return unique broker identifier (e.g., 'UPSTOX', 'ZERODHA', 'BINANCE')."""
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
    def authenticate(self, credentials: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Validate API credentials and obtain/refresh session tokens."""
        pass

    @abstractmethod
    def get_profile(self) -> Dict[str, Any]:
        """Fetch user profile details (user_id, client_code, exchanges enabled)."""
        pass

    @abstractmethod
    def get_funds(self) -> Dict[str, Any]:
        """
        Fetch authoritative cash and margin balances in account currency.
        Returns:
          available_margin, used_margin, payin, payout, cash, currency
        """
        pass

    @abstractmethod
    def get_holdings(self) -> List[Dict[str, Any]]:
        """
        Fetch long-term portfolio holdings (demat/CNC).
        Returns list of:
          isin, company_name, symbol, exchange, quantity, average_price, ltp, pnl_usd_or_inr
        """
        pass

    @abstractmethod
    def get_positions(self) -> List[Dict[str, Any]]:
        """
        Fetch open and closed intraday/derivatives positions.
        Returns list of:
          symbol, exchange, product (MIS/CNC), side, quantity, buy_price, sell_price, ltp, unrealized_pnl
        """
        pass

    @abstractmethod
    def get_orders(self) -> List[Dict[str, Any]]:
        """Fetch all orders placed for the current trading day."""
        pass

    @abstractmethod
    def get_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Fetch detailed status and lifecycle transitions for a specific order."""
        pass

    @abstractmethod
    def place_order(self, order_request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Place order on the broker/exchange.
        Enforces tick size, freeze quantities, session hours, and product types.
        """
        pass

    @abstractmethod
    def modify_order(self, order_id: str, changes: Dict[str, Any]) -> Dict[str, Any]:
        """Modify an active pending or open limit/stop order."""
        pass

    @abstractmethod
    def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """Cancel an open pending order."""
        pass

    @abstractmethod
    def get_trades(self) -> List[Dict[str, Any]]:
        """Fetch trade fills for the day."""
        pass

    @abstractmethod
    def get_market_data(self, symbols: List[str]) -> Dict[str, Any]:
        """Fetch real-time LTP, bid/ask, volume, and OHLC quotes."""
        pass

    @abstractmethod
    def get_instruments(self, exchange: str = "NSE") -> List[Dict[str, Any]]:
        """Fetch broker master instrument list for an exchange."""
        pass

    @abstractmethod
    def reconcile(self) -> Dict[str, Any]:
        """
        Reconcile broker balances & positions against internal double-entry ledger.
        Returns reconciliation status, delta, and discrepancies.
        """
        pass
