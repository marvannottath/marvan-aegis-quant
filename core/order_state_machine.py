"""
Aegis-Quant Order State Machine.
Immutable, append-only order lifecycle with explicit allowed transitions.
Every state transition generates an audit record with timestamp and reason.

Allowed transitions:
  CREATED        -> RISK_PENDING
  RISK_PENDING   -> APPROVED | REJECTED
  APPROVED       -> SUBMITTED
  SUBMITTED      -> ACKNOWLEDGED | FAILED | CANCELLED
  ACKNOWLEDGED   -> PARTIALLY_FILLED | FILLED | CANCELLED | FAILED
  PARTIALLY_FILLED -> FILLED | CANCELLED | FAILED
"""

import uuid
import time
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta

IST_TZ = timezone(timedelta(hours=5, minutes=30))
ORDERS_DB = Path(__file__).resolve().parent.parent / "data" / "orders_state_machine.json"


class OrderStateMachineError(Exception):
    pass


# Allowed state transitions
ORDER_TRANSITIONS: Dict[str, List[str]] = {
    "CREATED":          ["RISK_PENDING"],
    "RISK_PENDING":     ["APPROVED", "REJECTED"],
    "APPROVED":         ["SUBMITTED"],
    "SUBMITTED":        ["ACKNOWLEDGED", "FAILED", "CANCELLED"],
    "ACKNOWLEDGED":     ["PARTIALLY_FILLED", "FILLED", "CANCELLED", "FAILED"],
    "PARTIALLY_FILLED": ["FILLED", "CANCELLED", "FAILED"],
    # Terminal states
    "FILLED":    [],
    "REJECTED":  [],
    "CANCELLED": [],
    "FAILED":    [],
}


def _now_str() -> str:
    return datetime.now(timezone.utc).astimezone(IST_TZ).strftime("%Y-%m-%d %H:%M:%S IST")


class OrderStateMachine:
    def __init__(self):
        self.orders: Dict[str, Dict[str, Any]] = {}
        self._load()

    def _load(self):
        ORDERS_DB.parent.mkdir(parents=True, exist_ok=True)
        if ORDERS_DB.exists():
            try:
                with open(ORDERS_DB, "r") as f:
                    self.orders = json.load(f)
            except Exception as e:
                print(f"[ORDER_SM] Load error: {e}")

    def _save(self):
        try:
            tmp = ORDERS_DB.with_suffix(".tmp")
            with open(tmp, "w") as f:
                json.dump(self.orders, f, indent=2)
            tmp.replace(ORDERS_DB)
        except Exception as e:
            print(f"[ORDER_SM] Save error: {e}")

    def create_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        order_type: str,
        environment: str,
        price: float = 0.0,
        strategy: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create a new order in CREATED state."""
        order_id = f"ORD-{environment[:3]}-{int(time.time()*1000)}-{uuid.uuid4().hex[:6].upper()}"
        order = {
            "order_id":    order_id,
            "symbol":      symbol,
            "side":        side,
            "quantity":    quantity,
            "price":       price,
            "order_type":  order_type,
            "environment": environment,
            "strategy":    strategy,
            "status":      "CREATED",
            "fill_qty":    0.0,
            "avg_fill_price": 0.0,
            "created_at":  _now_str(),
            "updated_at":  _now_str(),
            "transitions": [{"from": None, "to": "CREATED", "at": _now_str(), "reason": "Order created"}],
            "execution_record": None,
            "metadata":    metadata or {},
        }
        self.orders[order_id] = order
        self._save()
        return order

    def transition(
        self,
        order_id: str,
        new_state: str,
        reason: str = "",
        execution_record: Optional[Dict[str, Any]] = None,
        fill_qty: float = 0.0,
        avg_fill_price: float = 0.0,
    ) -> Dict[str, Any]:
        """
        Transition order to a new state.
        Raises OrderStateMachineError on invalid transitions.
        FILLED status requires an execution_record.
        """
        if order_id not in self.orders:
            raise OrderStateMachineError(f"Order '{order_id}' not found")

        order = self.orders[order_id]
        current = order["status"]
        allowed = ORDER_TRANSITIONS.get(current, [])

        if new_state not in allowed:
            raise OrderStateMachineError(
                f"Invalid transition {current} -> {new_state} for order {order_id}. "
                f"Allowed: {allowed}"
            )

        # FILLED requires execution record
        if new_state == "FILLED" and execution_record is None:
            raise OrderStateMachineError(
                f"Cannot mark order {order_id} as FILLED without an execution_record"
            )

        order["status"]     = new_state
        order["updated_at"] = _now_str()
        if fill_qty > 0:
            order["fill_qty"] = round(fill_qty, 6)
        if avg_fill_price > 0:
            order["avg_fill_price"] = round(avg_fill_price, 2)
        if execution_record is not None:
            order["execution_record"] = execution_record

        order["transitions"].append({
            "from": current,
            "to":   new_state,
            "at":   _now_str(),
            "reason": reason,
        })

        self._save()
        return order

    def get_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        return self.orders.get(order_id)

    def get_orders_by_environment(self, environment: str) -> List[Dict[str, Any]]:
        return [o for o in self.orders.values() if o["environment"] == environment]

    def get_open_orders(self, environment: str) -> List[Dict[str, Any]]:
        open_states = {"CREATED", "RISK_PENDING", "APPROVED", "SUBMITTED", "ACKNOWLEDGED", "PARTIALLY_FILLED"}
        return [o for o in self.orders.values() if o["environment"] == environment and o["status"] in open_states]


# Global singleton
order_state_machine = OrderStateMachine()
