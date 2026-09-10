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
    "ACKNOWLEDGED":     ["PARTIALLY_FILLED", "FILLED", "CANCELLED", "FAILED", "CLOSED"],
    "PARTIALLY_FILLED": ["FILLED", "CANCELLED", "FAILED", "CLOSED"],
    # Terminal states
    "FILLED":    ["CLOSED"],
    "CLOSED":    [],
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
        provider: str = "PAPER",
        provider_order_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create a new canonical order in CREATED state."""
        env_tag = environment[:3].upper() if environment else "PAP"
        order_id = f"ORD-{env_tag}-{int(time.time()*1000)}-{uuid.uuid4().hex[:6].upper()}"
        now_ts = _now_str()

        order = {
            "order_id":                     order_id,
            "internal_order_id":            order_id,
            "provider_order_id":            provider_order_id or "",
            "provider":                     provider or ("BINANCE" if "BINANCE" in environment else "PAPER"),
            "symbol":                       symbol,
            "side":                         side.upper(),
            "quantity":                     float(quantity),
            "price":                        float(price),
            "order_type":                   order_type.upper(),
            "environment":                  environment,
            "strategy":                     strategy,
            "status":                       "CREATED",
            "fill_qty":                     0.0,
            "executed_quantity":            0.0,
            "avg_fill_price":               0.0,
            "average_fill_price":           0.0,
            "fees":                         0.0,
            "raw_provider_event_reference": None,
            "created_at":                   now_ts,
            "submitted_at":                 None,
            "acknowledged_at":              None,
            "filled_at":                    None,
            "cancelled_at":                 None,
            "updated_at":                   now_ts,
            "transitions": [{"from": None, "to": "CREATED", "at": now_ts, "reason": "Order created"}],
            "execution_record":             None,
            "metadata":                     metadata or {},
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
        provider_order_id: Optional[str] = None,
        fees: float = 0.0,
        raw_event_ref: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Transition order to a new state.
        Raises OrderStateMachineError on invalid transitions.
        Handles idempotent duplicate events gracefully.
        """
        if order_id not in self.orders:
            raise OrderStateMachineError(f"Order '{order_id}' not found")

        order = self.orders[order_id]
        current = order["status"]
        now_ts = _now_str()

        # Idempotency guard: duplicate transition to same state is accepted without error
        if current == new_state:
            if provider_order_id and not order.get("provider_order_id"):
                order["provider_order_id"] = str(provider_order_id)
            if fill_qty > 0:
                order["fill_qty"] = round(fill_qty, 6)
                order["executed_quantity"] = round(fill_qty, 6)
            if avg_fill_price > 0:
                order["avg_fill_price"] = round(avg_fill_price, 2)
                order["average_fill_price"] = round(avg_fill_price, 2)
            self._save()
            return order

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
        order["updated_at"] = now_ts

        # Set transition-specific timestamps and provider metadata
        if new_state == "SUBMITTED":
            order["submitted_at"] = now_ts
        elif new_state == "ACKNOWLEDGED":
            order["acknowledged_at"] = now_ts
        elif new_state == "FILLED":
            order["filled_at"] = now_ts
        elif new_state in ("CANCELLED", "CLOSED", "FAILED", "REJECTED"):
            order["cancelled_at"] = now_ts

        if provider_order_id:
            order["provider_order_id"] = str(provider_order_id)
        if raw_event_ref:
            order["raw_provider_event_reference"] = raw_event_ref
        if fees > 0:
            order["fees"] = round(fees, 4)

        if fill_qty > 0:
            order["fill_qty"] = round(fill_qty, 6)
            order["executed_quantity"] = round(fill_qty, 6)
        if avg_fill_price > 0:
            order["avg_fill_price"] = round(avg_fill_price, 2)
            order["average_fill_price"] = round(avg_fill_price, 2)
        if execution_record is not None:
            order["execution_record"] = execution_record

        order["transitions"].append({
            "from": current,
            "to":   new_state,
            "at":   now_ts,
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
