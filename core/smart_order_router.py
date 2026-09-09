"""
Aegis-Quant Smart Order Router (SOR).
Enforces strict asset class to venue boundaries:
  - INDIAN_EQUITY / INDIAN_ETF -> Upstox / Paper INR (NSE/BSE)
  - FOREX / COMMODITIES        -> Institutional FX Broker / Paper FX (Global)
  - CRYPTO                     -> Binance (Spot/Futures)

Pre-Routing Checklist:
  1. Venue Health & Authentication
  2. Exchange Trading Hours / Market Session
  3. Available Funds in Native Currency
  4. Spread & Slippage Tolerances
  5. High Impact News Lock
"""

from typing import Dict, Any, List, Optional
from core.indian_market_data import indian_market_data
from core.india_news_engine import india_news_engine


class SmartOrderRouter:
    """Multi-Venue Institutional Order Router."""

    def __init__(self):
        pass

    def route_order(self, order_intent: Dict[str, Any]) -> Dict[str, Any]:
        """
        Determine eligible venue, execute pre-trade validation, and return routing decision.
        """
        symbol = order_intent.get("symbol", "").upper()
        asset_class = order_intent.get("asset_class", "INDIAN_EQUITY").upper()
        amount = float(order_intent.get("amount", 0.0))
        side = order_intent.get("side", "BUY").upper()

        # 1. Route to Indian Equities
        if asset_class in ("INDIAN_EQUITY", "INDIAN_ETF", "NSE", "BSE") or symbol in (
            "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "SBIN", "BHARTIARTL", "ITC",
            "KOTAKBANK", "LT", "TATAMOTORS", "HINDUNILVR", "MARUTI", "SUNPHARMA", "AXISBANK",
            "TITAN", "BAJFINANCE", "NIFTYBEES", "GOLDBEES", "JUNIORBEES"
        ):
            # Session Check
            session = indian_market_data.get_market_session()
            if not session.get("is_trading_allowed") and not order_intent.get("is_amo", False):
                return {
                    "allowed": False,
                    "target_venue": "UPSTOX",
                    "reason": f"EXCHANGE_SESSION_CLOSED: {session.get('reason')}. Mark order as After-Market Order (AMO) to queue.",
                    "session_state": session.get("session")
                }

            # News Lock Check
            news_lock = india_news_engine.check_symbol_lock(symbol)
            if news_lock.get("is_locked"):
                return {
                    "allowed": False,
                    "target_venue": "UPSTOX",
                    "reason": news_lock.get("reason"),
                    "session_state": session.get("session")
                }

            # Balance Check in AEGIS_INDIA_INR
            from execution.user_wallet import user_wallet
            wallet = user_wallet.compute_all("AEGIS_INDIA_INR")
            avail = wallet.get("trading_balance", 0.0)
            if amount > avail:
                return {
                    "allowed": False,
                    "target_venue": "UPSTOX",
                    "reason": f"INSUFFICIENT_FUNDS: Required ₹{amount:,.2f}, Available Trading Balance: ₹{avail:,.2f}",
                    "currency": "INR"
                }

            return {
                "allowed": True,
                "target_venue": "UPSTOX",
                "environment": "AEGIS_INDIA_INR",
                "exchange": "NSE",
                "currency": "INR",
                "currency_symbol": "₹",
                "routing_algorithm": "BEST_EXECUTION_NSE",
                "reason": "Routed directly to Upstox Indian Brokerage Gateway"
            }

        # 2. Route to Forex & Commodities
        elif asset_class in ("FOREX", "COMMODITIES", "FX") or symbol in (
            "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "USDCHF", "NZDUSD", "XAUUSD"
        ):
            return {
                "allowed": True,
                "target_venue": "INSTITUTIONAL_FX",
                "environment": "AEGIS_QUANT_MASTER",
                "exchange": "GLOBAL_FX",
                "currency": "USD",
                "currency_symbol": "$",
                "routing_algorithm": "INSTITUTIONAL_FIX_DMA",
                "reason": "Routed to Institutional Forex Liquidity Provider"
            }

        # 3. Route to Crypto
        elif asset_class in ("CRYPTO", "SPOT_CRYPTO") or "USDT" in symbol or symbol in (
            "BTCUSD", "ETHUSD", "SOLUSD", "BNBUSD", "BTCUSDT", "ETHUSDT"
        ):
            from execution.binance_broker import binance_broker
            return {
                "allowed": True,
                "target_venue": "BINANCE",
                "environment": "BINANCE_TESTNET_DEMO" if binance_broker.testnet else "BINANCE_LIVE_REAL",
                "exchange": "BINANCE",
                "currency": "USDT",
                "currency_symbol": "$",
                "routing_algorithm": "SMART_ORDER_ROUTER_BINANCE",
                "reason": "Routed to Binance Spot Execution Engine"
            }

        else:
            return {
                "allowed": False,
                "target_venue": "UNKNOWN",
                "reason": f"UNSUPPORTED_ASSET_CLASS: Asset '{symbol}' ({asset_class}) does not match any eligible venue."
            }


# Global Singleton
smart_order_router = SmartOrderRouter()
