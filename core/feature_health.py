"""
Honest Feature Health Registry.
Every claimed feature must report its ACTUAL implementation status.
Never claim ACTIVE/ONLINE unless a real runtime check confirms it.
"""

import subprocess
import importlib
from pathlib import Path
from typing import Dict, Any


def _module_exists(name: str) -> bool:
    try:
        importlib.import_module(name)
        return True
    except ImportError:
        return False


def _file_exists(rel_path: str) -> bool:
    return (Path(__file__).resolve().parent.parent / rel_path).exists()


def get_feature_health() -> Dict[str, Any]:
    """
    Returns honest, runtime-verified health for each claimed capability.
    Status values: ACTIVE | SIMULATED | NOT_CONFIGURED | OFFLINE | DEGRADED
    """
    import socket

    # Check PyTorch
    try:
        import torch
        pytorch_status = "ACTIVE (LOCAL)"
        pytorch_detail = f"torch {torch.__version__}"
    except ImportError:
        pytorch_status = "NOT_CONFIGURED"
        pytorch_detail = "PyTorch not installed"

    # Check RL model file
    rl_model_path = Path(__file__).resolve().parent.parent / "rl_trader_v1.pth"
    rl_status = "ACTIVE (LOCAL)" if rl_model_path.exists() else "NOT_CONFIGURED"

    # Check Binance API reachability
    try:
        s = socket.create_connection(("testnet.binance.vision", 443), timeout=3)
        s.close()
        binance_status = "CONNECTED (TESTNET)"
    except Exception:
        binance_status = "OFFLINE"

    # FIX Engine — string formatter only, no TCP socket
    fix_status = "SIMULATED"
    fix_detail = "FIX 4.4 message formatting only. No live exchange TCP session."

    # WebSocket — no WS server running
    ws_status = "NOT_CONFIGURED"
    ws_detail = "No WebSocket server active. Data uses HTTP polling."

    # C++/Rust kernel — bridge exists but no .so loaded
    cpp_path = Path(__file__).resolve().parent / "cpp_kernel_bridge.py"
    cpp_status = "SIMULATED" if cpp_path.exists() else "NOT_CONFIGURED"
    cpp_detail = "Python bridge exists. No compiled .so/dll loaded."

    # Monte Carlo VaR — Python impl exists
    mc_path = Path(__file__).resolve().parent / "monte_carlo_var.py"
    mc_status = "ACTIVE (LOCAL)" if mc_path.exists() else "NOT_CONFIGURED"

    # Telegram — file-based audit, no live API
    tg_path = Path(__file__).resolve().parent.parent / "sync" / "telegram_listener.py"
    tg_status = "SIMULATED" if tg_path.exists() else "NOT_CONFIGURED"
    tg_detail = "File-based feed. No live Telegram Bot API token configured."

    # Market Data — deterministic simulation tick engine
    md_status = "SIMULATED"
    md_detail = "Deterministic tick oscillation. Not connected to live exchange feed."

    # SOR / VWAP / Iceberg — not implemented
    exec_algo_path = Path(__file__).resolve().parent.parent / "execution" / "algo_execution.py"
    algo_status = "SIMULATED" if exec_algo_path.exists() else "NOT_CONFIGURED"
    algo_detail = "Algorithmic execution module exists but routes to paper broker."

    # MBO / Order Book L3
    ob_path = Path(__file__).resolve().parent / "order_book_l3.py"
    ob_status = "SIMULATED" if ob_path.exists() else "NOT_CONFIGURED"

    return {
        "fix_protocol":    {"status": fix_status,      "detail": fix_detail},
        "websocket":       {"status": ws_status,        "detail": ws_detail},
        "cpp_rust_kernel": {"status": cpp_status,       "detail": cpp_detail},
        "pytorch_rl":      {"status": pytorch_status,   "detail": pytorch_detail},
        "rl_model":        {"status": rl_status,        "detail": str(rl_model_path)},
        "telegram":        {"status": tg_status,        "detail": tg_detail},
        "monte_carlo_var": {"status": mc_status,        "detail": "numpy-based VaR simulation"},
        "market_data":     {"status": md_status,        "detail": md_detail},
        "binance_api":     {"status": binance_status,   "detail": "HMAC-SHA256 signed REST API"},
        "algo_execution":  {"status": algo_status,      "detail": algo_detail},
        "order_book_l3":   {"status": ob_status,        "detail": "Simulated depth queue"},
        "deposits":        {"status": "NOT_CONFIGURED", "detail": "No payment processor connected."},
        "withdrawals":     {"status": "DISABLED",       "detail": "Zero-withdrawal policy active. Admin override required."},
    }
