"""
Aegis-Quant Close In-Flight Order Tracker.
Provides restart-safe atomic persistence for pending/ambiguous position close orders.
Ensures in-flight reconciliation barriers survive daemon and process restarts.

Key Responsibilities:
1. Persists minimum required fields:
   - environment (e.g. BINANCE_TESTNET, BINANCE_LIVE)
   - symbol (e.g. BTCUSDT)
   - client_order_id (original client-assigned order ID)
   - provider_order_id (exchange order ID if known)
   - requested_quantity (original position volume requested to close)
   - already_reconciled_executed_qty (executed quantity already accounted for in local books)
   - created_at / created_at_str
   - status (UNKNOWN, PARTIALLY_FILLED, RESTING_ORDER, etc.)
   - exit_price
   - reason
2. Safe atomic persistence with restricted file permissions (0600).
3. Data validation on load:
   - Validates schema and required types.
   - Detects corrupted/malformed files and enters FAIL-CLOSED mode.
   - While in FAIL-CLOSED mode, all close attempts are blocked to prevent duplicate orders.
4. Environment isolation: maintains separation between TESTNET and LIVE orders.
5. Never stores API keys or secrets.
"""

import os
import json
import time
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime, timezone, timedelta

IST_TZ = timezone(timedelta(hours=5, minutes=30))
DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "close_in_flight.json"

REQUIRED_FIELDS = {
    "environment",
    "symbol",
    "client_order_id",
    "requested_quantity",
    "already_reconciled_executed_qty",
    "status"
}


def _now_str() -> str:
    return datetime.now(timezone.utc).astimezone(IST_TZ).strftime("%Y-%m-%d %H:%M:%S IST")


class CloseInFlightTracker:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DEFAULT_DB_PATH
        self.in_flight_orders: Dict[str, Dict[str, Any]] = {}
        self._corrupted: bool = False
        self._corruption_error: str = ""
        self.load()

    def is_corrupted(self) -> bool:
        """Returns True if the persistence layer is corrupted and must fail closed."""
        return self._corrupted

    def get_corruption_error(self) -> str:
        return self._corruption_error

    def reset_for_testing(self, db_path: Optional[Path] = None):
        """Helper for test suites to reset state cleanly."""
        if db_path is not None:
            self.db_path = db_path
        self.in_flight_orders.clear()
        self._corrupted = False
        self._corruption_error = ""

    def load(self):
        """
        Load in-flight orders from disk with strict validation.
        Fails closed on corruption or invalid schemas.
        """
        self._corrupted = False
        self._corruption_error = ""
        self.in_flight_orders = {}

        if not self.db_path.exists():
            return

        try:
            with open(self.db_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if not isinstance(data, dict):
                self._corrupted = True
                self._corruption_error = f"Root JSON is {type(data).__name__}, expected dict"
                print(f"[CLOSE_IN_FLIGHT CRITICAL] Persistence corrupt: {self._corruption_error}")
                return

            validated_orders: Dict[str, Dict[str, Any]] = {}
            for sym, item in data.items():
                if not isinstance(item, dict):
                    self._corrupted = True
                    self._corruption_error = f"Item for {sym} is not a dict"
                    print(f"[CLOSE_IN_FLIGHT CRITICAL] Persistence corrupt: {self._corruption_error}")
                    return

                missing = REQUIRED_FIELDS - set(item.keys())
                if missing:
                    self._corrupted = True
                    self._corruption_error = f"Item for {sym} missing required fields: {missing}"
                    print(f"[CLOSE_IN_FLIGHT CRITICAL] Persistence corrupt: {self._corruption_error}")
                    return

                try:
                    item["requested_quantity"] = float(item["requested_quantity"])
                    item["already_reconciled_executed_qty"] = float(item["already_reconciled_executed_qty"])
                    if "exit_price" in item:
                        item["exit_price"] = float(item["exit_price"])
                    if "created_at" in item:
                        item["created_at"] = float(item["created_at"])
                except (ValueError, TypeError) as conv_err:
                    self._corrupted = True
                    self._corruption_error = f"Numeric conversion error in {sym}: {conv_err}"
                    print(f"[CLOSE_IN_FLIGHT CRITICAL] Persistence corrupt: {self._corruption_error}")
                    return

                validated_orders[sym] = item

            self.in_flight_orders = validated_orders

        except Exception as e:
            self._corrupted = True
            self._corruption_error = f"Failed to read/parse state file: {e}"
            print(f"[CLOSE_IN_FLIGHT CRITICAL] Persistence read error (FAIL CLOSED): {e}")

    def save(self):
        """
        Atomically write in-flight orders to disk with restricted permissions (0600).
        Refuses to write if currently in corrupted state to preserve evidence.
        """
        if self._corrupted:
            print("[CLOSE_IN_FLIGHT WARNING] Refusing to overwrite state file while marked corrupted")
            return

        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            tmp_path = self.db_path.with_suffix(".tmp")
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(self.in_flight_orders, f, indent=2)

            try:
                os.chmod(tmp_path, 0o600)
            except Exception:
                pass

            tmp_path.replace(self.db_path)

            try:
                os.chmod(self.db_path, 0o600)
            except Exception:
                pass

        except Exception as e:
            print(f"[CLOSE_IN_FLIGHT ERROR] Failed to atomically save in-flight orders: {e}")

    def record_in_flight(
        self,
        symbol: str,
        environment: str,
        client_order_id: str,
        requested_quantity: float,
        already_reconciled_qty: float = 0.0,
        provider_order_id: Optional[str] = None,
        status: str = "UNKNOWN",
        exit_price: float = 0.0,
        reason: str = "CLOSE_ORDER"
    ) -> Dict[str, Any]:
        """Record or update a position close order in flight."""
        if self._corrupted:
            print(f"[CLOSE_IN_FLIGHT WARNING] System corrupted; rejecting record for {symbol}")
            return {}

        now_ts = time.time()
        entry = {
            "environment": environment,
            "symbol": symbol,
            "client_order_id": client_order_id,
            "provider_order_id": str(provider_order_id) if provider_order_id else None,
            "requested_quantity": float(requested_quantity),
            "already_reconciled_executed_qty": float(already_reconciled_qty),
            "created_at": now_ts,
            "created_at_str": _now_str(),
            "status": status,
            "exit_price": float(exit_price),
            "reason": reason
        }
        self.in_flight_orders[symbol] = entry
        self.save()
        return entry

    def update_reconciled_qty(self, symbol: str, executed_qty: float, status: Optional[str] = None):
        """Incrementally update reconciled executed quantity for an in-flight order."""
        if symbol in self.in_flight_orders:
            self.in_flight_orders[symbol]["already_reconciled_executed_qty"] = float(executed_qty)
            if status:
                self.in_flight_orders[symbol]["status"] = status
            self.save()

    def clear_in_flight(self, symbol: str):
        """Remove symbol from in-flight tracking once conclusively resolved."""
        if symbol in self.in_flight_orders:
            self.in_flight_orders.pop(symbol, None)
            self.save()

    def get_in_flight(self, symbol: str) -> Optional[Dict[str, Any]]:
        return self.in_flight_orders.get(symbol)

    def get_all_pending(self, environment: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        if environment:
            return {
                sym: o for sym, o in self.in_flight_orders.items()
                if o.get("environment") == environment
            }
        return dict(self.in_flight_orders)

    def is_blocked(self, symbol: str, environment: Optional[str] = None) -> bool:
        """
        Check whether a close operation on symbol is blocked.
        Returns True if:
        1. Persistence is corrupted (fail-closed).
        2. Symbol is currently in flight with an unresolved status.
        """
        if self._corrupted:
            return True

        if symbol not in self.in_flight_orders:
            return False

        order = self.in_flight_orders[symbol]
        if environment and order.get("environment") != environment:
            return False

        # Block any status that is not conclusively closed/terminal
        stat = str(order.get("status", "")).upper()
        return stat in [
            "UNKNOWN",
            "PARTIALLY_FILLED",
            "PENDING_RECONCILIATION",
            "NEW",
            "AMBIGUOUS_TIMEOUT",
            "WORKING"
        ]


# Global singleton instance
close_in_flight_tracker = CloseInFlightTracker()
