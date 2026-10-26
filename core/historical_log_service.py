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

        # ── 1. REAL KOTAK NEO LIVE EXECUTION TRADES (INDIA LIVE) ──────────
        try:
            from execution.kotak_neo_broker import kotak_neo_broker
            kotak_raw_trades = kotak_neo_broker.get_trade_book()
            if kotak_raw_trades:
                by_sym: Dict[str, List[dict]] = {}
                for kt in sorted(kotak_raw_trades, key=lambda x: str(x.get("exTm") or x.get("flTm") or "")):
                    sym = str(kt.get("trdSym", "")).replace("-EQ", "").upper()
                    if sym:
                        by_sym.setdefault(sym, []).append(kt)

                for sym, fills in by_sym.items():
                    buy_queue = []
                    for f in fills:
                        qty = float(f.get("fldQty", 0) or f.get("qty", 0) or 0)
                        if qty <= 0:
                            qty = float(f.get("brdLtQty", 1) or 1)
                        price = float(f.get("avgPrc", 0.0) or 0.0)
                        side = str(f.get("trnsTp", "")).upper()
                        tm = str(f.get("flTm", "")).strip()
                        dt = str(f.get("flDt", "")).strip()
                        
                        iso_date = datetime.now(timezone.utc).astimezone(IST_TZ).strftime("%Y-%m-%d")
                        if dt:
                            try:
                                parsed_d = datetime.strptime(dt, "%d-%b-%Y")
                                iso_date = parsed_d.strftime("%Y-%m-%d")
                            except Exception:
                                pass
                        full_ts = f"{iso_date} {tm}" if tm else f"{iso_date} 00:00:00"

                        if side == "B":
                            buy_queue.append({
                                "qty": qty,
                                "price": price,
                                "time": full_ts,
                                "ordNo": f.get("nOrdNo", "")
                            })
                        elif side == "S":
                            rem_qty = qty
                            while rem_qty > 0.0001 and buy_queue:
                                b = buy_queue[0]
                                match_qty = min(rem_qty, b["qty"])
                                entry_px = b["price"]
                                exit_px = price
                                gross = round((exit_px - entry_px) * match_qty, 2)
                                
                                stt = round(exit_px * match_qty * 0.00025, 2)
                                nse_turnover = round((entry_px + exit_px) * match_qty * 0.0000297, 2)
                                stamp = round(entry_px * match_qty * 0.00003, 2)
                                gst = round(nse_turnover * 0.18, 2)
                                tot_fee = max(0.20, round(stt + nse_turnover + stamp + gst, 2))
                                net = round(gross - tot_fee, 2)
                                
                                tid = f"TRD-KNEO-{sym}-{f.get('nOrdNo') or int(time.time()*1000)}"
                                res_status = "WIN" if net > 0 else ("LOSS" if net < 0 else "BREAKEVEN")
                                pnl_pct_calc = round((gross / (entry_px * match_qty)) * 100.0, 2) if (entry_px * match_qty) > 0 else 0.0
                                if "14:4" in tm or "15:0" in tm:
                                    exit_reason = "3:10 PM PRE_SQUAREOFF"
                                elif net > 0:
                                    exit_reason = "FEE_SECURED_TAKE_PROFIT"
                                elif gross >= 0 and net < 0:
                                    exit_reason = "REGULATORY_COST_COVERAGE"
                                elif pnl_pct_calc <= -0.50:
                                    exit_reason = "INTRADAY_STOP_LOSS"
                                else:
                                    exit_reason = "MARKET_SPREAD_EXIT"
                                
                                trades_map[tid] = {
                                    "trade_id": tid,
                                    "timestamp": full_ts,
                                    "date": iso_date,
                                    "symbol": sym,
                                    "asset": sym,
                                    "side": "BUY",
                                    "action": "BUY",
                                    "entry_price": entry_px,
                                    "exit_price": exit_px,
                                    "quantity": match_qty,
                                    "units": match_qty,
                                    "capital_allocated": round(entry_px * match_qty, 2),
                                    "leverage": 1.0,
                                    "gross_pnl": gross,
                                    "fee_usd": tot_fee,
                                    "net_pnl": net,
                                    "pnl_usd": net,
                                    "pnl_pct": round((gross / (entry_px * match_qty)) * 100.0, 2) if (entry_px * match_qty) > 0 else 0.0,
                                    "result": res_status,
                                    "close_reason": exit_reason,
                                    "workspace": "INDIA",
                                    "environment": "LIVE",
                                    "source": "KOTAK_NEO_LIVE"
                                }
                                b["qty"] -= match_qty
                                rem_qty -= match_qty
                                if b["qty"] <= 0.0001:
                                    buy_queue.pop(0)
        except Exception as ke:
            print(f"[HistoricalLogService] Kotak Neo live trades notice: {ke}")

        # ── 2. REAL BINANCE LIVE EXECUTION TRADES (CRYPTO LIVE) ───────────
        try:
            from execution.binance_broker import binance_broker
            if binance_broker.is_live_configured:
                for sym in ["BTCUSDT", "BNBUSDT", "SOLUSDT", "ETHUSDT", "XRPUSDT", "DOGEUSDT", "ADAUSDT"]:
                    try:
                        fills = binance_broker.get_execution_fills("BINANCE_LIVE", symbol=sym, limit=50)
                        if not fills:
                            continue
                        fills = sorted(fills, key=lambda x: int(x.get("time", 0)))
                        
                        buy_queue = []
                        for f in fills:
                            qty = float(f.get("qty", 0.0))
                            price = float(f.get("price", 0.0))
                            comm = float(f.get("commission", 0.0))
                            comm_asset = str(f.get("commissionAsset", "USDT")).upper()
                            if comm_asset in ["USDT", "BUSD", "USD"]:
                                fee_usd = comm
                            elif comm_asset == "BNB":
                                bnb_px = float(binance_broker.get_market_data("BINANCE_LIVE", "BNBUSDT").get("last_price", 745.0) or 745.0)
                                fee_usd = round(comm * bnb_px, 4)
                            else:
                                fee_usd = round(comm * price, 4)
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
                                    tid = f"TRD-BINA-LIVE-{sym_clean}-{f.get('id')}"
                                    
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
                                        "quantity": round(matched_qty, 4),
                                        "units": round(matched_qty, 4),
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
                                        "environment": "LIVE",
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

        # ── 3. PAPER BROKER POOLS (STRICTLY FOR DEMO ONLY!) ───────────────
        try:
            from execution.paper_broker import paper_broker
            for pool_name, pool in paper_broker.pools.items():
                if isinstance(pool, dict):
                    # Never import simulated trades into LIVE
                    if any(k in pool_name.upper() for k in ("LIVE", "REAL")):
                        continue
                    ws = "CRYPTO" if "BINANCE" in pool_name or "CRYPTO" in pool_name else ("INDIA" if "INDIA" in pool_name or "UPSTOX" in pool_name else "FOREX_GOLD")
                    for t in pool.get("trade_history", []):
                        norm = self._normalise_trade_record(t, pool_name=pool_name, workspace=ws)
                        norm["environment"] = "DEMO"
                        if norm and norm.get("trade_id") and norm["trade_id"] not in trades_map:
                            trades_map[norm["trade_id"]] = norm
        except Exception as e:
            print(f"[HistoricalLogService] In-memory paper broker load notice: {e}")

        # 4. Load from paper_broker_state.json file (DEMO only)
        if self.PAPER_BROKER_STATE.is_file():
            try:
                with open(self.PAPER_BROKER_STATE, "r") as f:
                    state = json.load(f)
                pools = state.get("pools", {})
                for pool_name, pool_data in pools.items():
                    if any(k in pool_name.upper() for k in ("LIVE", "REAL")):
                        continue
                    ws = "CRYPTO" if "BINANCE" in pool_name or "CRYPTO" in pool_name else ("INDIA" if "INDIA" in pool_name or "UPSTOX" in pool_name else "FOREX_GOLD")
                    for t in pool_data.get("trade_history", []):
                        norm = self._normalise_trade_record(t, pool_name=pool_name, workspace=ws)
                        norm["environment"] = "DEMO"
                        if norm and norm.get("trade_id") and norm["trade_id"] not in trades_map:
                            trades_map[norm["trade_id"]] = norm
            except Exception as e:
                print(f"[HistoricalLogService] File paper broker load notice: {e}")

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

        # Authoritatively resolve workspace from symbol
        s_upper = str(sym).upper().replace("/", "").replace("-", "")
        if any(s_upper.endswith(q) for q in ["USDT", "BUSD", "USDC", "BTC", "ETH"]) or s_upper in ["BTC", "ETH", "SOL", "BNB", "XRP", "DOGE", "ADA", "AVAX", "LINK", "SUI"]:
            resolved_ws = "CRYPTO"
        elif s_upper in ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "SBIN", "BHARTIARTL", "ITC", "NIFTY50", "BANKNIFTY", "TATAMOTORS"] or s_upper.endswith(".NS") or s_upper.endswith(".BO") or "NSE" in s_upper:
            resolved_ws = "INDIA"
        elif any(s_upper.endswith(c) for c in ["USD", "JPY", "EUR", "GBP", "CHF", "CAD", "AUD"]) or s_upper in ["XAUUSD", "GOLD", "EURUSD", "GBPUSD", "USDJPY"]:
            resolved_ws = "FOREX_GOLD"
        else:
            resolved_ws = workspace or "CRYPTO"

        # Gross & Net PnL and Fees
        pnl = float(t.get("net_pnl") if "net_pnl" in t else (t.get("pnl_usd") or t.get("realized_pnl") or 0.0))
        fee = float(t.get("fee_usd", 0.0))
        if fee == 0.0 and entry_px > 0 and units > 0:
            fee = round(((entry_px * units) + (exit_px * units)) * 0.001, 4)
        gross = float(t.get("gross_pnl") if "gross_pnl" in t else (pnl + fee))
        net = round(gross - fee, 2)

        res = t.get("result") or ("WIN" if net > 0 else ("LOSS" if net < 0 else "BREAKEVEN"))

        is_live = (
            any(k in pool_name.upper() for k in ("LIVE", "REAL"))
            or t.get("source") == "BINANCE_LIVE"
            or "LIVE" in str(t.get("environment", "")).upper()
            or "REAL" in str(t.get("environment", "")).upper()
        )
        env_tag = "LIVE" if is_live else "DEMO"

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
            "workspace": resolved_ws,
            "pool_name": pool_name,
            "environment": env_tag,
            "source": t.get("source", "AEGIS_LEDGER")
        }

    def query(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        symbol: Optional[str] = None,
        side: Optional[str] = None,
        workspace: Optional[str] = None,
        environment: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        self._ensure_loaded()
        res = self._cached_trades

        if environment and environment.upper() != "ALL":
            env_clean = environment.upper().strip()
            if env_clean == "LIVE":
                res = [
                    t for t in res
                    if t.get("environment") == "LIVE"
                ]
            elif env_clean in ("DEMO", "PAPER", "TESTNET", "SANDBOX"):
                res = [
                    t for t in res
                    if t.get("environment") != "LIVE"
                ]

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
