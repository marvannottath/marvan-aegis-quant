import json
import os
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional

IST_TZ = timezone(timedelta(hours=5, minutes=30))

class HistoricalLogService:
    """
    Unified trade history service for Aegis Quant.
    Aggregates closed trades from:
    1. Real Binance live executions via Binance API
    2. Paper broker pools (BINANCE_LIVE_REAL, AEGIS_QUANT_MASTER, etc.)
    3. Persisted broker states
    Provides structured filtering by date, symbol, side, workspace.
    """

    PAPER_BROKER_STATE = Path(__file__).resolve().parent.parent / "data" / "paper_broker_state.json"

    def __init__(self):
        self._cached_trades: List[Dict[str, Any]] = []
        self._last_load_ts = 0.0

    def _ensure_loaded(self) -> None:
        now = time.time()
        if (now - self._last_load_ts) < 2.0 and self._cached_trades:
            return
        self._load_all()
        self._last_load_ts = now

    def _load_all(self) -> None:
        trades_map: Dict[str, Dict[str, Any]] = {}

        # 1. Load from paper_broker in-memory pools
        try:
            from execution.paper_broker import paper_broker
            for pool_name, pool in paper_broker.pools.items():
                if isinstance(pool, dict):
                    ws = "CRYPTO" if "BINANCE" in pool_name or "CRYPTO" in pool_name else ("INDIA" if "INDIA" in pool_name or "UPSTOX" in pool_name else "FOREX_GOLD")
                    for t in pool.get("trade_history", []):
                        norm = self._normalise_trade_record(t, pool_name=pool_name, workspace=ws)
                        if norm and norm.get("trade_id"):
                            trades_map[norm["trade_id"]] = norm
        except Exception as e:
            print(f"[HistoricalLogService] In-memory paper broker load notice: {e}")

        # 2. Load from paper_broker_state.json file
        if self.PAPER_BROKER_STATE.is_file():
            try:
                with open(self.PAPER_BROKER_STATE, "r") as f:
                    state = json.load(f)
                pools = state.get("pools", {})
                for pool_name, pool_data in pools.items():
                    ws = "CRYPTO" if "BINANCE" in pool_name or "CRYPTO" in pool_name else ("INDIA" if "INDIA" in pool_name or "UPSTOX" in pool_name else "FOREX_GOLD")
                    for t in pool_data.get("trade_history", []):
                        norm = self._normalise_trade_record(t, pool_name=pool_name, workspace=ws)
                        if norm and norm.get("trade_id"):
                            trades_map[norm["trade_id"]] = norm
                # Also check root trade_history
                for t in state.get("trade_history", []):
                    norm = self._normalise_trade_record(t, pool_name="AEGIS_QUANT_MASTER", workspace="FOREX_GOLD")
                    if norm and norm.get("trade_id"):
                        trades_map[norm["trade_id"]] = norm
            except Exception as e:
                print(f"[HistoricalLogService] File paper broker load notice: {e}")

        # 3. Load live Binance execution fills if configured
        try:
            from execution.binance_broker import binance_broker
            if binance_broker.is_live_configured:
                # Query recent trades for active symbols
                for sym in ["BTCUSDT", "BNBUSDT", "SOLUSDT", "ETHUSDT", "XRPUSDT", "DOGEUSDT", "ADAUSDT"]:
                    try:
                        fills = binance_broker.get_execution_fills("BINANCE_LIVE", symbol=sym, limit=50)
                        if not fills:
                            continue
                        fills = sorted(fills, key=lambda x: int(x.get("time", 0)))
                        
                        # Reconstruct round-trip trades via FIFO matching
                        buy_queue = []
                        for f in fills:
                            qty = float(f.get("qty", 0.0))
                            price = float(f.get("price", 0.0))
                            comm = float(f.get("commission", 0.0))
                            comm_asset = f.get("commissionAsset", "USDT")
                            fee_usd = comm if comm_asset in ["USDT", "BUSD", "USD"] else round(comm * price, 4)
                            is_buyer = bool(f.get("isBuyer"))
                            ts_ms = int(f.get("time", time.time() * 1000))
                            
                            if is_buyer:
                                buy_queue.append({
                                    "id": f.get("id"),
                                    "qty": qty,
                                    "price": price,
                                    "fee": fee_usd,
                                    "time": ts_ms
                                })
                            else:
                                rem_sell_qty = qty
                                while rem_sell_qty > 0.000001 and buy_queue:
                                    b = buy_queue[0]
                                    matched_qty = min(rem_sell_qty, b["qty"])
                                    entry_px = b["price"]
                                    exit_px = price
                                    
                                    b_fee = (matched_qty / b["qty"]) * b["fee"] if b["qty"] > 0 else 0.0
                                    s_fee = (matched_qty / qty) * fee_usd if qty > 0 else 0.0
                                    tot_fee = round(b_fee + s_fee, 4)
                                    
                                    gross_pnl = round((exit_px - entry_px) * matched_qty, 4)
                                    net_pnl = round(gross_pnl - tot_fee, 2)
                                    dt_str = datetime.fromtimestamp(ts_ms / 1000.0, tz=timezone.utc).astimezone(IST_TZ).strftime("%Y-%m-%d %H:%M:%S")
                                    sym_clean = sym.replace("USDT", "")
                                    tid = f"TRD-BINA-{sym_clean}-{f.get('id')}"
                                    
                                    trades_map[tid] = {
                                        "trade_id": tid,
                                        "timestamp": dt_str,
                                        "date": dt_str[:10],
                                        "symbol": sym,
                                        "asset": sym,
                                        "side": "BUY",
                                        "action": "BUY",
                                        "entry_price": entry_px,
                                        "exit_price": exit_px,
                                        "quantity": round(matched_qty, 6),
                                        "units": round(matched_qty, 6),
                                        "capital_allocated": round(entry_px * matched_qty, 2),
                                        "leverage": 1.0,
                                        "gross_pnl": gross_pnl,
                                        "fee_usd": tot_fee,
                                        "net_pnl": net_pnl,
                                        "pnl_usd": net_pnl,
                                        "pnl_pct": round((gross_pnl / (entry_px * matched_qty)) * 100.0, 2) if (entry_px * matched_qty) > 0 else 0.0,
                                        "result": "WIN" if net_pnl > 0 else ("LOSS" if net_pnl < 0 else "BREAKEVEN"),
                                        "close_reason": "BINANCE_LIVE_FILL",
                                        "workspace": "CRYPTO",
                                        "source": "BINANCE_LIVE"
                                    }
                                    
                                    b["qty"] -= matched_qty
                                    rem_sell_qty -= matched_qty
                                    if b["qty"] <= 0.000001:
                                        buy_queue.pop(0)
                    except Exception as fill_err:
                        print(f"[HistoricalLogService] Fill parse notice for {sym}: {fill_err}")
        except Exception as e:
            print(f"[HistoricalLogService] Binance live fills notice: {e}")

        # Convert to list and sort descending by timestamp
        all_trades = list(trades_map.values())
        all_trades.sort(key=lambda t: str(t.get("timestamp", "")), reverse=True)
        self._cached_trades = all_trades

    def _normalise_trade_record(self, t: Dict[str, Any], pool_name: str = "", workspace: str = "CRYPTO") -> Dict[str, Any]:
        raw_ts = str(t.get("timestamp", ""))
        if not raw_ts:
            raw_ts = datetime.now(timezone.utc).astimezone(IST_TZ).strftime("%Y-%m-%d %H:%M:%S")
        date_str = raw_ts[:10]

        sym = t.get("symbol") or t.get("asset") or "BTCUSDT"
        side = t.get("side") or t.get("action") or "BUY"
        entry_px = float(t.get("entry_price") or t.get("price") or 0.0)
        exit_px = float(t.get("exit_price") or entry_px)
        units = float(t.get("units") or t.get("quantity") or 0.0)

        # Gross & Net PnL and Fees
        pnl = float(t.get("net_pnl") if "net_pnl" in t else (t.get("pnl_usd") or t.get("realized_pnl") or 0.0))
        fee = float(t.get("fee_usd", 0.0))
        if fee == 0.0 and entry_px > 0 and units > 0:
            fee = round(((entry_px * units) + (exit_px * units)) * 0.001, 4)
        gross = float(t.get("gross_pnl") if "gross_pnl" in t else (pnl + fee))
        net = round(gross - fee, 2)

        res = t.get("result") or ("WIN" if net > 0 else ("LOSS" if net < 0 else "BREAKEVEN"))

        return {
            "trade_id": t.get("trade_id") or f"TRD-{int(time.time()*1000)}",
            "timestamp": raw_ts,
            "date": date_str,
            "symbol": sym,
            "asset": sym,
            "side": side,
            "action": side,
            "entry_price": entry_px,
            "exit_price": exit_px,
            "quantity": units,
            "units": units,
            "gross_pnl": gross,
            "fee_usd": fee,
            "net_pnl": net,
            "pnl_usd": net,
            "result": res,
            "close_reason": t.get("reason") or t.get("close_reason", "EXECUTION_COMPLETE"),
            "workspace": workspace,
            "pool_name": pool_name,
            "source": t.get("source", "AEGIS_LEDGER")
        }

    def query(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        symbol: Optional[str] = None,
        side: Optional[str] = None,
        workspace: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        self._ensure_loaded()
        res = self._cached_trades

        if workspace and workspace.upper() != "ALL":
            res = [t for t in res if t.get("workspace") == workspace.upper()]

        if start_date:
            res = [t for t in res if t.get("date", "") >= start_date]

        if end_date:
            res = [t for t in res if t.get("date", "") <= end_date]

        if symbol:
            sym_clean = symbol.upper().strip()
            res = [t for t in res if t.get("symbol") == sym_clean or t.get("asset") == sym_clean]

        if side:
            side_clean = side.upper().strip()
            res = [t for t in res if t.get("side", "").upper() == side_clean or t.get("action", "").upper() == side_clean]

        return res


# Global singleton
historical_log_service = HistoricalLogService()
