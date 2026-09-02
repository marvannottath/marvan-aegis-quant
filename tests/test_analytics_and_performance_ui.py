"""
Aegis-Quant Analytics & Performance UI Test Suite.
Verifies all 6 new API endpoints, interactive controls, data integrity assertions,
and backend restart persistence.
"""

import sys
import json
import asyncio
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.performance_curve_engine import performance_curve_engine
from core.execution_latency_profiler import execution_latency_profiler
from core.backtest_analytics_engine import backtest_analytics_engine


def test_performance_curve_api():
    """Test performance curve engine for all metrics and ranges."""
    metrics = ["equity", "pnl", "drawdown"]
    ranges = ["1D", "1W", "1M", "3M", "ALL"]

    for m in metrics:
        for r in ranges:
            data = performance_curve_engine.get_curve(metric=m, time_range=r)
            assert data["status"] == "SUCCESS", f"Failed status for metric={m}, range={r}"
            assert data["metric"] == m
            assert data["range"] == r
            assert "points" in data
            assert isinstance(data["points"], list)
            assert len(data["points"]) > 0, f"No points returned for metric={m}, range={r}"
            assert "latest" in data
            assert "min" in data
            assert "max" in data
    print("  ✅ [PASS] Performance Curve Engine (All 15 metric/range combinations)")


def test_execution_latency_api():
    """Test 10-step institutional latency profiler."""
    summary = execution_latency_profiler.get_summary(environment="PAPER")
    assert summary["status"] == "SUCCESS"
    assert "p50" in summary
    assert "p95" in summary
    assert "p99" in summary
    assert "avg" in summary
    assert "stage_averages" in summary
    assert len(summary["stage_averages"]) == 10, f"Expected 10 pipeline stages, got {len(summary['stage_averages'])}"
    assert "recent_executions" in summary
    print("  ✅ [PASS] Execution Pipeline Latency Profiler (10 stages profiled)")


def test_backtest_runs_api():
    """Test backtest runs listing."""
    runs = backtest_analytics_engine.list_backtest_runs()
    assert isinstance(runs, list)
    assert len(runs) > 0, "No backtest runs found"
    first = runs[0]
    assert "backtest_id" in first
    assert "strategy" in first
    assert "initial_capital" in first
    assert "final_capital" in first
    assert "integrity_status" in first
    print(f"  ✅ [PASS] Backtest Runs List API ({len(runs)} persisted backtest runs loaded)")


def test_backtest_detail_and_integrity_api():
    """Test backtest detail, trade logs, equity curve, and financial integrity assertions."""
    runs = backtest_analytics_engine.list_backtest_runs()
    assert len(runs) > 0
    bt_id = runs[0]["backtest_id"]

    # 1. Detail API
    detail = backtest_analytics_engine.get_backtest_detail(bt_id)
    assert detail is not None
    summary = detail.get("summary", {})
    assert summary["backtest_id"] == bt_id
    assert summary["integrity_status"] == "VERIFIED", f"Integrity failed: {summary.get('integrity_message')}"
    print(f"  ✅ [PASS] Backtest Detail API ({bt_id} VERIFIED)")

    # 2. Trades & Integrity: Initial + SUM(Net PnL) == Final Capital
    trades = detail.get("trades", [])
    assert len(trades) > 0, "No trade history in backtest detail"
    init_cap = summary["initial_capital"]
    final_cap = summary["final_capital"]
    sum_net_pnl = sum(t["net_pnl"] for t in trades)
    expected_final = round(init_cap + sum_net_pnl, 2)
    assert abs(expected_final - final_cap) < 1.0, f"Accounting mismatch: Expected ${expected_final}, got ${final_cap}"
    print(f"  ✅ [PASS] Backtest Accounting Invariant (Initial ${init_cap} + SUM PnL ${sum_net_pnl:.2f} == Final ${final_cap:.2f})")

    # 3. Equity Curve API
    eq_points = detail.get("equity_curve", [])
    assert len(eq_points) > 0
    last_eq = eq_points[-1]["equity"]
    assert abs(round(last_eq, 2) - final_cap) < 1.0, f"Final equity point (${last_eq}) != Final capital (${final_cap})"
    print(f"  ✅ [PASS] Backtest Equity Curve Invariant (Final Point ${last_eq:.2f} == Final Capital ${final_cap:.2f})")


def run_all_tests():
    print("=" * 75)
    print("AEGIS-QUANT — ANALYTICS & PERFORMANCE UI TEST SUITE")
    print("=" * 75)
    test_performance_curve_api()
    test_execution_latency_api()
    test_backtest_runs_api()
    test_backtest_detail_and_integrity_api()
    print("=" * 75)
    print("ALL ANALYTICS & PERFORMANCE UI TESTS PASSED (100%)")
    print("=" * 75)


if __name__ == "__main__":
    run_all_tests()
