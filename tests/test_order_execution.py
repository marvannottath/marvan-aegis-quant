"""
Pytest Test Suite: Aegis-Quant Execution Engine
Verifies idempotency, concurrency, race conditions, and boundary isolation.
"""
import sys
import os
import asyncio
from decimal import Decimal
import sqlite3
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from trading_engine import (
    ExecutionEngine,
    MockBrokerAdapter,
    OrderRequest,
    OrderRecord,  # <-- Added missing import
    OrderSide,
    OrderStatus,
    DuplicateOrderPayloadMismatch,
    InsufficientMarginError,
    ExecutionError,
)

import asyncio
from decimal import Decimal
import sqlite3
import pytest

from trading_engine import (
    ExecutionEngine,
    MockBrokerAdapter,
    OrderRequest,
    OrderSide,
    OrderStatus,
    DuplicateOrderPayloadMismatch,
    InsufficientMarginError,
    ExecutionError,
)


@pytest.fixture
def sqlite_conn():
    """Provides an isolated in-memory SQLite connection."""
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.execute("PRAGMA journal_mode = WAL;")
    yield conn
    conn.close()


@pytest.fixture
def broker():
    """Provides a fresh mock broker adapter."""
    return MockBrokerAdapter(latency=0.02)


@pytest.fixture
def engine(sqlite_conn, broker):
    """Initializes the engine with funded accounts across workspaces."""
    inst = ExecutionEngine(sqlite_conn, broker)
    with sqlite_conn:
        sqlite_conn.executemany(
            "INSERT INTO accounts (account_id, workspace_id, balance) VALUES (?, ?, ?)",
            [
                ("ACC_CRYPTO_01", "CRYPTO", "10000.00"),
                ("ACC_INDIA_01", "INDIA", "500000.00"),
                ("ACC_FX_01", "FOREX_GOLD", "5000.00"),
            ]
        )
    return inst


# -----------------------------------------------------------------------------
# 1. Pure Idempotency Tests
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_order_idempotency_sequential_duplicates(engine, broker):
    """Submitting the identical request sequentially must return the original order without extra broker calls."""
    req = OrderRequest(
        client_order_id="ORD-IDEMP-001",
        workspace_id="CRYPTO",
        account_id="ACC_CRYPTO_01",
        symbol="BTCUSDT",
        side=OrderSide.BUY,
        quantity=Decimal("0.100"),
        price=Decimal("50000.00")
    )

    first_res = await engine.execute_order(req)
    second_res = await engine.execute_order(req)
    third_res = await engine.execute_order(req)

    assert first_res.status == OrderStatus.FILLED
    assert second_res.status == OrderStatus.FILLED
    assert third_res.status == OrderStatus.FILLED
    assert first_res.broker_order_id == second_res.broker_order_id == third_res.broker_order_id
    
    # Invariant: Broker must receive exactly one external transmission
    assert broker.submission_count == 1


@pytest.mark.asyncio
async def test_order_idempotency_payload_mismatch_rejection(engine, broker):
    """Reusing a client_order_id with different price or quantity must be rejected."""
    original_req = OrderRequest(
        client_order_id="ORD-MISMATCH-002",
        workspace_id="CRYPTO",
        account_id="ACC_CRYPTO_01",
        symbol="ETHUSDT",
        side=OrderSide.BUY,
        quantity=Decimal("1.00"),
        price=Decimal("3000.00")
    )
    await engine.execute_order(original_req)

    tampered_req = OrderRequest(
        client_order_id="ORD-MISMATCH-002",
        workspace_id="CRYPTO",
        account_id="ACC_CRYPTO_01",
        symbol="ETHUSDT",
        side=OrderSide.BUY,
        quantity=Decimal("2.00"),  # Changed quantity
        price=Decimal("3000.00")
    )

    with pytest.raises(DuplicateOrderPayloadMismatch) as exc_info:
        await engine.execute_order(tampered_req)

    assert "reused with different order parameters" in str(exc_info.value)
    assert broker.submission_count == 1


# -----------------------------------------------------------------------------
# 2. Concurrency and Race Condition Tests
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_concurrent_identical_orders_race_condition(engine, broker):
    """20 concurrent requests with the exact same client_order_id must yield exactly 1 execution."""
    req = OrderRequest(
        client_order_id="ORD-CONCUR-003",
        workspace_id="CRYPTO",
        account_id="ACC_CRYPTO_01",
        symbol="SOLUSDT",
        side=OrderSide.BUY,
        quantity=Decimal("10.00"),
        price=Decimal("150.00")
    )

    # Fire 20 tasks concurrently
    tasks = [engine.execute_order(req) for _ in range(20)]
    results = await asyncio.gather(*tasks, return_exceptions=False)

    # All caller tasks should receive identical successful records
    assert len(results) == 20
    assert all(r.status == OrderStatus.FILLED for r in results)
    assert len({r.broker_order_id for r in results}) == 1
    
    # Broker must be reached exactly once
    assert broker.submission_count == 1

    # Margin check: 10 * 150 = 1500 deducted from 10000 = 8500
    cursor = engine.db.cursor()
    cursor.execute("SELECT balance FROM accounts WHERE account_id = 'ACC_CRYPTO_01'")
    assert Decimal(cursor.fetchone()[0]) == Decimal("8500.00")


@pytest.mark.asyncio
async def test_concurrent_margin_exhaustion_prevents_overdraw(engine, broker):
    """
    Two distinct orders submitted concurrently when account margin only covers one.
    Only one order must succeed; the second must fail with InsufficientMarginError.
    Account balance must never become negative.
    """
    # Account ACC_CRYPTO_01 balance is 10000. Each order requires 6000.
    req_a = OrderRequest(
        client_order_id="ORD-MARGIN-A",
        workspace_id="CRYPTO",
        account_id="ACC_CRYPTO_01",
        symbol="BTCUSDT",
        side=OrderSide.BUY,
        quantity=Decimal("0.10"),
        price=Decimal("60000.00")  # Cost = 6000
    )
    req_b = OrderRequest(
        client_order_id="ORD-MARGIN-B",
        workspace_id="CRYPTO",
        account_id="ACC_CRYPTO_01",
        symbol="BTCUSDT",
        side=OrderSide.BUY,
        quantity=Decimal("0.10"),
        price=Decimal("60000.00")  # Cost = 6000
    )

    results = await asyncio.gather(
        engine.execute_order(req_a),
        engine.execute_order(req_b),
        return_exceptions=True
    )

    successes = [r for r in results if isinstance(r, OrderRecord)]
    failures = [r for r in results if isinstance(r, InsufficientMarginError)]

    # Invariant: Exactly one succeeded, exactly one rejected
    assert len(successes) == 1
    assert len(failures) == 1
    assert broker.submission_count == 1

    # Verify final balance is 4000.00 (10000 - 6000)
    cursor = engine.db.cursor()
    cursor.execute("SELECT balance FROM accounts WHERE account_id = 'ACC_CRYPTO_01'")
    assert Decimal(cursor.fetchone()[0]) == Decimal("4000.00")


# -----------------------------------------------------------------------------
# 3. Workspace Scoping and Database Integrity Tests
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_workspace_scoped_order_id_independence(engine, broker):
    """
    Identical client_order_id across different workspaces must be treated 
    as isolated orders without collision.
    """
    req_crypto = OrderRequest(
        client_order_id="ORD-SHARED-ID-100",
        workspace_id="CRYPTO",
        account_id="ACC_CRYPTO_01",
        symbol="BTCUSDT",
        side=OrderSide.BUY,
        quantity=Decimal("0.02"),
        price=Decimal("50000.00")  # Cost = 1000 USDT
    )
    req_fx = OrderRequest(
        client_order_id="ORD-SHARED-ID-100",
        workspace_id="FOREX_GOLD",
        account_id="ACC_FX_01",
        symbol="XAUUSD",
        side=OrderSide.BUY,
        quantity=Decimal("1.00"),
        price=Decimal("2000.00")   # Cost = 2000 USD
    )

    res_crypto = await engine.execute_order(req_crypto)
    res_fx = await engine.execute_order(req_fx)

    assert res_crypto.workspace_id == "CRYPTO"
    assert res_fx.workspace_id == "FOREX_GOLD"
    assert broker.submission_count == 2


@pytest.mark.asyncio
async def test_broker_network_failure_rolls_back_state(engine, monkeypatch):
    """When the broker fails to accept an order, margin reservation must be restored."""
    async def mock_failing_broker(order: OrderRequest):
        await asyncio.sleep(0.01)
        raise ConnectionResetError("Broker TCP connection reset by peer")

    monkeypatch.setattr(engine.broker, "place_order", mock_failing_broker)

    req = OrderRequest(
        client_order_id="ORD-FAIL-001",
        workspace_id="CRYPTO",
        account_id="ACC_CRYPTO_01",
        symbol="BTCUSDT",
        side=OrderSide.BUY,
        quantity=Decimal("0.05"),
        price=Decimal("50000.00")  # Cost = 2500
    )

    with pytest.raises(ConnectionResetError):
        await engine.execute_order(req)

    # Balance must be fully restored to 10000.00
    cursor = engine.db.cursor()
    cursor.execute("SELECT balance FROM accounts WHERE account_id = 'ACC_CRYPTO_01'")
    assert Decimal(cursor.fetchone()[0]) == Decimal("10000.00")

    # Order record must register as REJECTED
    cursor.execute("SELECT status FROM orders WHERE client_order_id = 'ORD-FAIL-001'")
    assert cursor.fetchone()[0] == OrderStatus.REJECTED.value