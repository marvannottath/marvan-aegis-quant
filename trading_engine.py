"""
Aegis-Quant Order Execution Harness
Demonstrates atomic DB constraints, locking, and broker submission logic.
"""
import asyncio
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Dict, Optional, Tuple
import sqlite3


class OrderStatus(str, Enum):
    PENDING = "PENDING"
    SUBMITTED = "SUBMITTED"
    FILLED = "FILLED"
    REJECTED = "REJECTED"


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class ExecutionError(Exception):
    pass


class DuplicateOrderPayloadMismatch(ExecutionError):
    pass


class InsufficientMarginError(ExecutionError):
    pass


@dataclass(frozen=True)
class OrderRequest:
    client_order_id: str
    workspace_id: str
    account_id: str
    symbol: str
    side: OrderSide
    quantity: Decimal
    price: Decimal


@dataclass
class OrderRecord:
    client_order_id: str
    workspace_id: str
    account_id: str
    symbol: str
    side: OrderSide
    quantity: Decimal
    price: Decimal
    status: OrderStatus
    broker_order_id: Optional[str] = None


class MockBrokerAdapter:
    """Simulates an external exchange broker gateway."""
    def __init__(self, latency: float = 0.01):
        self.latency = latency
        self.submission_count: int = 0
        self.submitted_keys: set[Tuple[str, str]] = set()
        self._lock: Optional[asyncio.Lock] = None

    @property
    def lock(self) -> asyncio.Lock:
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock

    async def place_order(self, order: OrderRequest) -> str:
        async with self.lock:
            self.submission_count += 1
            broker_key = (order.workspace_id, order.client_order_id)
            if broker_key in self.submitted_keys:
                raise ExecutionError(f"Broker received duplicate ID: {order.client_order_id}")
            self.submitted_keys.add(broker_key)
        
        await asyncio.sleep(self.latency)
        return f"BROKER-{order.client_order_id}"


class ExecutionEngine:
    """Order engine implementing atomic idempotency and account balance checks."""
    def __init__(self, db_conn: sqlite3.Connection, broker: MockBrokerAdapter):
        self.db = db_conn
        self.broker = broker
        self._execution_lock: Optional[asyncio.Lock] = None
        self._inflight: Dict[Tuple[str, str, str], asyncio.Future] = {}
        self._init_db()

    @property
    def execution_lock(self) -> asyncio.Lock:
        if self._execution_lock is None:
            self._execution_lock = asyncio.Lock()
        return self._execution_lock

    def _init_db(self):
        with self.db:
            self.db.execute("PRAGMA foreign_keys = ON;")
            self.db.execute("""
                CREATE TABLE IF NOT EXISTS accounts (
                    account_id TEXT PRIMARY KEY,
                    workspace_id TEXT NOT NULL,
                    balance TEXT NOT NULL
                );
            """)
            self.db.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    client_order_id TEXT NOT NULL,
                    workspace_id TEXT NOT NULL,
                    account_id TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    quantity TEXT NOT NULL,
                    price TEXT NOT NULL,
                    status TEXT NOT NULL,
                    broker_order_id TEXT,
                    PRIMARY KEY (client_order_id, workspace_id, account_id)
                );
            """)

    async def execute_order(self, req: OrderRequest) -> OrderRecord:
        order_key = (req.client_order_id, req.workspace_id, req.account_id)
        wait_future: Optional[asyncio.Future] = None
        my_future: Optional[asyncio.Future] = None

        # 1. Critical section for concurrency & balance check
        async with self.execution_lock:
            # If an identical order is currently in-flight, capture the future
            if order_key in self._inflight:
                wait_future = self._inflight[order_key]
            else:
                # Check DB for finalized/existing order
                cursor = self.db.cursor()
                cursor.execute(
                    """
                    SELECT client_order_id, workspace_id, account_id, symbol, side, 
                           quantity, price, status, broker_order_id 
                    FROM orders 
                    WHERE client_order_id = ? AND workspace_id = ? AND account_id = ?
                    """,
                    order_key
                )
                row = cursor.fetchone()

                if row:
                    if (
                        row[3] != req.symbol or 
                        row[4] != req.side.value or 
                        Decimal(row[5]) != req.quantity or 
                        Decimal(row[6]) != req.price
                    ):
                        raise DuplicateOrderPayloadMismatch(
                            f"client_order_id '{req.client_order_id}' reused with different order parameters."
                        )
                    return OrderRecord(
                        client_order_id=row[0],
                        workspace_id=row[1],
                        account_id=row[2],
                        symbol=row[3],
                        side=OrderSide(row[4]),
                        quantity=Decimal(row[5]),
                        price=Decimal(row[6]),
                        status=OrderStatus(row[7]),
                        broker_order_id=row[8]
                    )

                # Balance verification
                cursor.execute(
                    "SELECT balance FROM accounts WHERE account_id = ? AND workspace_id = ?",
                    (req.account_id, req.workspace_id)
                )
                acct = cursor.fetchone()
                if not acct:
                    raise ExecutionError(f"Account {req.account_id} does not exist.")
                
                balance = Decimal(acct[0])
                required_margin = req.quantity * req.price
                if balance < required_margin:
                    raise InsufficientMarginError(f"Available: {balance}, Required: {required_margin}")

                # Deduct balance & insert PENDING order
                new_balance = balance - required_margin
                cursor.execute(
                    "UPDATE accounts SET balance = ? WHERE account_id = ?",
                    (str(new_balance), req.account_id)
                )
                cursor.execute(
                    """
                    INSERT INTO orders (client_order_id, workspace_id, account_id, symbol, side, quantity, price, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (req.client_order_id, req.workspace_id, req.account_id, req.symbol, req.side.value, str(req.quantity), str(req.price), OrderStatus.PENDING.value)
                )
                self.db.commit()

                # Register in-flight future for concurrent workers
                loop = asyncio.get_running_loop()
                my_future = loop.create_future()
                self._inflight[order_key] = my_future

        # 2. Concurrent workers wait OUTSIDE the lock
        if wait_future is not None:
            return await wait_future

        # 3. Primary worker submits to broker
        try:
            broker_ref = await self.broker.place_order(req)
            order_status = OrderStatus.FILLED

            with self.db:
                self.db.execute(
                    "UPDATE orders SET status = ?, broker_order_id = ? WHERE client_order_id = ? AND workspace_id = ? AND account_id = ?",
                    (order_status.value, broker_ref, req.client_order_id, req.workspace_id, req.account_id)
                )

            final_record = OrderRecord(
                client_order_id=req.client_order_id,
                workspace_id=req.workspace_id,
                account_id=req.account_id,
                symbol=req.symbol,
                side=req.side,
                quantity=req.quantity,
                price=req.price,
                status=order_status,
                broker_order_id=broker_ref
            )
            if my_future is not None and not my_future.done():
                my_future.set_result(final_record)
            return final_record

        except Exception as e:
            with self.db:
                self.db.execute("UPDATE accounts SET balance = balance + ? WHERE account_id = ?", (str(required_margin), req.account_id))
                self.db.execute("UPDATE orders SET status = ? WHERE client_order_id = ?", (OrderStatus.REJECTED.value, req.client_order_id))
            if my_future is not None and not my_future.done():
                my_future.set_exception(e)
                try:
                    my_future.exception()  # Warning suppress cheyyaan
                except Exception:
                    pass
            raise e
        finally:
            async with self.execution_lock:
                self._inflight.pop(order_key, None)