"""
Kotak Neo Broker Adapter for Aegis-Quant.
Implements the BrokerAdapter interface for Indian Equity & Derivatives markets (NSE/BSE).
Architecture:
  - Inherits from core.broker_adapter.BrokerAdapter
  - Defaults strictly to PAPER / MOCK mode (isolated from live exchange execution)
  - Zero live credentials bundled; reads from environment/vault only
  - Hard fail-closed live execution gate: LIVE_TRADING_ENABLED=false
  - Enforces NSE tick rules (0.05 step), INR currency, and ledger reconciliation
"""

import os
import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone, timedelta

from core.broker_adapter import BrokerAdapter

IST_TZ = timezone(timedelta(hours=5, minutes=30))
KOTAK_CONFIG_FILE = Path(__file__).resolve().parent / "kotak_neo_config.json"


def _ist_now() -> str:
    return datetime.now(timezone.utc).astimezone(IST_TZ).strftime("%Y-%m-%d %H:%M:%S IST")


class KotakNeoBrokerAdapter(BrokerAdapter):
    """
    Kotak Neo API adapter with paper/mock isolation.
    Designed for future live integration without risking unauthorized trade dispatch.
    """

    BASE_URL = "https://gw-napi.kotaksecurities.com"

    def __init__(self):
        self._consumer_key: str = os.getenv("KOTAK_NEO_CONSUMER_KEY", "").strip()
        self._consumer_secret: str = os.getenv("KOTAK_NEO_CONSUMER_SECRET", "").strip()
        self._mobile_number: str = os.getenv("KOTAK_NEO_MOBILE_NUMBER", "").strip()
        self._ucc: str = os.getenv("KOTAK_NEO_UCC", "").strip()
        self._access_token: str = os.getenv("KOTAK_NEO_ACCESS_TOKEN", "").strip()
        self._session_token: str = ""
        self._token_expiry: float = 0.0

        if not self._consumer_key and KOTAK_CONFIG_FILE.exists():
            try:
                with open(KOTAK_CONFIG_FILE, "r") as f:
                    cfg = json.load(f)
                    self._consumer_key = cfg.get("consumer_key", "").strip()
                    self._consumer_secret = cfg.get("consumer_secret", "").strip()
                    self._mobile_number = cfg.get("mobile_number", "").strip()
                    self._ucc = cfg.get("ucc", "").strip()
            except Exception as e:
                print(f"[KOTAK_NEO] Config read notice: {e}")

        self._profile: Dict[str, Any] = {}
        self._is_authenticated: bool = False
        self._last_error: str = ""
        self._paper_mode: bool = True
        self._read_only: bool = True

        # Mock / Paper ledger storage for test simulation
        self._mock_positions: Dict[str, Dict[str, Any]] = {}
        self._mock_orders: Dict[str, Dict[str, Any]] = {}
        self._mock_cash: float = 50000.0  # INR default paper allocation

    @property
    def broker_name(self) -> str:
        return "KOTAK_NEO"

    @property
    def status(self) -> str:
        if not self._consumer_key or not self._consumer_secret:
            return "NOT_CONFIGURED"
        if not self._is_authenticated:
            return "DISCONNECTED"
        return "CONNECTED"

    def connect(self) -> bool:
        if not self._consumer_key:
            self._last_error = "Kotak Neo credentials not configured."
            return False
        return self.authenticate().get("authenticated", False)

    def authenticate(self, credentials: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Authenticate against Kotak Neo API or initialize paper mode.
        Fails safely if live credentials are not present.
        """
        creds = credentials or {}
        key = creds.get("consumer_key") or self._consumer_key
        secret = creds.get("consumer_secret") or self._consumer_secret

        if not key or not secret:
            self._is_authenticated = False
            return {
                "authenticated": False,
                "status": "NOT_CONFIGURED",
                "message": "Kotak Neo API consumer_key or consumer_secret missing.",
                "paper_mode": self._paper_mode,
            }

        # Safe verification: in paper mode, mark authenticated without external network call
        if self._paper_mode:
            self._is_authenticated = True
            self._profile = {
                "user_id": self._ucc or "KOTAK_MOCK_USER",
                "client_code": self._ucc or "NEO_PAPER_CLIENT",
                "exchanges": ["NSE", "BSE"],
                "broker": "KOTAK_NEO",
                "mode": "PAPER_MOCK",
                "updated_at": _ist_now(),
            }
            return {
                "authenticated": True,
                "status": "CONNECTED",
                "profile": self._profile,
                "paper_mode": True,
            }

        return {
            "authenticated": False,
            "status": "LIVE_LOCKED",
            "message": "Live execution is locked by server safety gate (LIVE_TRADING_ENABLED=false).",
        }

    def get_profile(self) -> Dict[str, Any]:
        if not self._profile:
            return {
                "user_id": self._ucc or "NOT_CONNECTED",
                "client_code": self._ucc or "NOT_CONNECTED",
                "broker": "KOTAK_NEO",
                "status": self.status,
            }
        return self._profile

    def get_funds(self) -> Dict[str, Any]:
        """Fetch cash and margin balances in INR."""
        used_margin = sum(
            float(p.get("quantity", 0)) * float(p.get("buy_price", 0))
            for p in self._mock_positions.values()
        )
        avail = max(0.0, self._mock_cash - used_margin)
        return {
            "available_margin": round(avail, 2),
            "used_margin": round(used_margin, 2),
            "payin": 0.0,
            "payout": 0.0,
            "cash": round(self._mock_cash, 2),
            "currency": "INR",
            "updated_at": _ist_now(),
        }

    def get_holdings(self) -> List[Dict[str, Any]]:
        return []

    def get_positions(self) -> List[Dict[str, Any]]:
        return list(self._mock_positions.values())

    def get_orders(self) -> List[Dict[str, Any]]:
        return list(self._mock_orders.values())

    def get_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        return self._mock_orders.get(order_id)

    def place_order(self, order_request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Submit order to paper engine.
        Live order placement is strictly blocked by server-side policy.
        """
        # 1. Server-side live trading lockout
        is_live = os.getenv("LIVE_TRADING_ENABLED", "false").lower() == "true"
        if order_request.get("environment") == "LIVE" and not is_live:
            return {
                "status": "REJECTED",
                "order_id": None,
                "message": "LIVE order rejected: LIVE_TRADING_ENABLED is false on server.",
            }

        symbol = order_request.get("symbol", "").strip()
        side = order_request.get("side", "").upper()
        quantity = float(order_request.get("quantity", 0))
        price = float(order_request.get("price", 0.0))
        order_type = order_request.get("order_type", "LIMIT").upper()

        if quantity <= 0:
            return {"status": "REJECTED", "message": "Invalid quantity"}

        # Validate NSE tick size (multiple of 0.05)
        if price > 0 and round(price * 100) % 5 != 0:
            return {"status": "REJECTED", "message": "Price does not conform to NSE tick size (0.05)"}

        order_id = f"KNEO-{int(time.time() * 1000)}"
        record = {
            "order_id": order_id,
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "price": price,
            "order_type": order_type,
            "product": order_request.get("product", "MIS"),
            "status": "FILLED" if self._paper_mode else "SUBMITTED",
            "fill_qty": quantity,
            "avg_fill_price": price if price > 0 else 100.0,
            "created_at": _ist_now(),
        }
        self._mock_orders[order_id] = record

        # Update paper position
        if self._paper_mode:
            pos_key = f"{symbol}:{order_request.get('product', 'MIS')}"
            current_pos = self._mock_positions.get(pos_key, {
                "symbol": symbol,
                "exchange": "NSE",
                "product": order_request.get("product", "MIS"),
                "quantity": 0,
                "buy_price": 0.0,
                "sell_price": 0.0,
                "ltp": price if price > 0 else 100.0,
                "unrealized_pnl": 0.0,
            })
            if side == "BUY":
                current_pos["quantity"] += quantity
                current_pos["buy_price"] = price if price > 0 else 100.0
            elif side == "SELL":
                current_pos["quantity"] -= quantity
                current_pos["sell_price"] = price if price > 0 else 100.0

            if current_pos["quantity"] == 0:
                self._mock_positions.pop(pos_key, None)
            else:
                self._mock_positions[pos_key] = current_pos

        return {
            "status": "ACCEPTED",
            "order_id": order_id,
            "fill_price": price if price > 0 else 100.0,
            "message": "Order placed in Kotak Neo paper simulation.",
        }

    def modify_order(self, order_id: str, changes: Dict[str, Any]) -> Dict[str, Any]:
        if order_id not in self._mock_orders:
            return {"status": "ERROR", "message": "Order not found"}
        self._mock_orders[order_id].update(changes)
        return {"status": "SUCCESS", "order": self._mock_orders[order_id]}

    def cancel_order(self, order_id: str) -> Dict[str, Any]:
        if order_id not in self._mock_orders:
            return {"status": "ERROR", "message": "Order not found"}
        self._mock_orders[order_id]["status"] = "CANCELLED"
        return {"status": "SUCCESS", "order_id": order_id}

    def get_trades(self) -> List[Dict[str, Any]]:
        return [
            {
                "trade_id": f"TRD-{ord['order_id']}",
                "order_id": ord["order_id"],
                "symbol": ord["symbol"],
                "side": ord["side"],
                "quantity": ord.get("fill_qty", ord["quantity"]),
                "price": ord.get("avg_fill_price", ord["price"]),
                "timestamp": ord["created_at"],
            }
            for ord in self._mock_orders.values()
            if ord.get("status") == "FILLED"
        ]

    def get_market_data(self, symbols: List[str]) -> Dict[str, Any]:
        quotes = {}
        for sym in symbols:
            quotes[sym] = {
                "symbol": sym,
                "ltp": 100.0,
                "bid": 99.95,
                "ask": 100.05,
                "volume": 1000,
                "updated_at": _ist_now(),
            }
        return quotes

    def get_instruments(self, exchange: str = "NSE") -> List[Dict[str, Any]]:
        return [
            {"symbol": "RELIANCE", "exchange": "NSE", "tick_size": 0.05, "lot_size": 1},
            {"symbol": "TCS", "exchange": "NSE", "tick_size": 0.05, "lot_size": 1},
            {"symbol": "INFY", "exchange": "NSE", "tick_size": 0.05, "lot_size": 1},
            {"symbol": "HDFCBANK", "exchange": "NSE", "tick_size": 0.05, "lot_size": 1},
            {"symbol": "ICICIBANK", "exchange": "NSE", "tick_size": 0.05, "lot_size": 1},
        ]

    def reconcile(self) -> Dict[str, Any]:
        return {
            "broker": "KOTAK_NEO",
            "status": "RECONCILED",
            "mode": "PAPER_MOCK",
            "delta": 0.0,
            "discrepancies": [],
            "timestamp": _ist_now(),
        }


# Global singleton
kotak_neo_broker = KotakNeoBrokerAdapter()
