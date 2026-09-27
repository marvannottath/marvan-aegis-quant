import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional

class HistoricalLogService:
    """Service that aggregates trade history from both Binance live closes and
    paper‑broker closes, normalises them to a common schema, and provides simple
    filtering.
    """

    CLOSED_SPOT_PATH = Path(__file__).resolve().parent.parent / "data" / "closed_spot_positions.json"
    PAPER_BROKER_STATE = Path(__file__).resolve().parent.parent / "data" / "paper_broker_state.json"

    def __init__(self):
        self._trades: List[Dict[str, Any]] = []
        self._load_all()

    # ---------------------------------------------------------------------
    # Internal loaders
    # ---------------------------------------------------------------------
    def _load_all(self) -> None:
        """Load and normalise data from both sources.
        The resulting list is sorted by entry timestamp (ascending).
        """
        self._trades.clear()
        # 1. Binance live closed positions
        if self.CLOSED_SPOT_PATH.is_file():
            try:
                with open(self.CLOSED_SPOT_PATH, "r") as f:
                    data = json.load(f)
                for rec in data.get("positions", []):
                    self._trades.append(self._normalise_binance(rec))
            except Exception as e:
                # If the file is corrupted we simply skip – the service will still work.
                print(f"[HistoricalLogService] Failed to read Binance closed positions: {e}")
        # 2. Paper broker closed positions (stored inside paper_broker_state.json)
        if self.PAPER_BROKER_STATE.is_file():
            try:
                with open(self.PAPER_BROKER_STATE, "r") as f:
                    state = json.load(f)
                # The paper broker stores a dict "positions" with current open positions
                # and a list "closed_positions" for historical closes (if present).
                closed = state.get("closed_positions", [])
                for rec in closed:
                    self._trades.append(self._normalise_paper(rec))
            except Exception as e:
                print(f"[HistoricalLogService] Failed to read paper broker state: {e}")
        # Sort by entry timestamp for deterministic output
        self._trades.sort(key=lambda t: t["entry_ts"])

    # ---------------------------------------------------------------------
    # Normalisation helpers – both sources end up with the same field names.
    # ---------------------------------------------------------------------
    @staticmethod
    def _parse_ts(ts: Any) -> int:
        """Return epoch milliseconds. Accepts ISO string, epoch int, or None.
        """
        if isinstance(ts, int):
            return ts
        if isinstance(ts, str):
            try:
                dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                return int(dt.timestamp() * 1000)
            except Exception:
                pass
        # fallback: now
        return int(datetime.now(timezone.utc).timestamp() * 1000)

    def _normalise_binance(self, rec: Dict[str, Any]) -> Dict[str, Any]:
        """Convert a Binance closed spot position record to the common schema.
        Expected keys in *rec* (based on how the broker writes the file):
            - symbol
            - side ("BUY" / "SELL")
            - entry_price, exit_price
            - entry_timestamp, exit_timestamp
            - realized_pnl_usd
            - fee_usd
            - close_reason (optional)
        """
        return {
            "trade_id": rec.get("broker_position_id") or rec.get("trade_id") or f"BIN-{rec.get('symbol')}-{self._parse_ts(rec.get('entry_timestamp'))}",
            "symbol": rec.get("symbol"),
            "side": rec.get("side"),
            "entry_price": float(rec.get("entry_price", 0.0)),
            "exit_price": float(rec.get("exit_price", 0.0)),
            "entry_ts": self._parse_ts(rec.get("entry_timestamp")),
            "exit_ts": self._parse_ts(rec.get("exit_timestamp")),
            "realized_pnl_usd": float(rec.get("realized_pnl_usd", 0.0)),
            "fee_usd": float(rec.get("fee_usd", 0.0)),
            "close_reason": rec.get("close_reason", "UNKNOWN"),
            "source": "BINANCE"
        }

    def _normalise_paper(self, rec: Dict[str, Any]) -> Dict[str, Any]:
        """Convert a paper‑broker closed record to the same schema.
        Paper records usually contain:
            - symbol, side, entry_price, exit_price, entry_ts, exit_ts
            - realized_pnl_usd, fee_usd (may be 0), close_reason
        """
        return {
            "trade_id": rec.get("trade_id") or f"PAPER-{rec.get('symbol')}-{self._parse_ts(rec.get('entry_ts'))}",
            "symbol": rec.get("symbol"),
            "side": rec.get("side"),
            "entry_price": float(rec.get("entry_price", 0.0)),
            "exit_price": float(rec.get("exit_price", 0.0)),
            "entry_ts": self._parse_ts(rec.get("entry_ts")),
            "exit_ts": self._parse_ts(rec.get("exit_ts")),
            "realized_pnl_usd": float(rec.get("realized_pnl_usd", 0.0)),
            "fee_usd": float(rec.get("fee_usd", 0.0)),
            "close_reason": rec.get("close_reason", "MANUAL"),
            "source": "PAPER"
        }

    # ---------------------------------------------------------------------
    # Public query API
    # ---------------------------------------------------------------------
    def query(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        symbol: Optional[str] = None,
        side: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Return a filtered list of trades.
        * start_date / end_date – ISO‑8601 date strings (e.g. "2026-09-20").
        * symbol – exact symbol filter (e.g. "BTCUSDT").
        * side – "BUY" or "SELL".
        """
        # Convert date strings to epoch ms boundaries (start = 00:00:00, end = 23:59:59)
        start_ts = None
        end_ts = None
        if start_date:
            dt = datetime.fromisoformat(start_date)
            start_ts = int(dt.replace(tzinfo=timezone.utc).timestamp() * 1000)
        if end_date:
            dt = datetime.fromisoformat(end_date)
            # end of day
            end_ts = int((dt.replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)).timestamp() * 1000)
        filtered = []
        for t in self._trades:
            if start_ts is not None and t["entry_ts"] < start_ts:
                continue
            if end_ts is not None and t["entry_ts"] > end_ts:
                continue
            if symbol and t["symbol"] != symbol:
                continue
            if side and t["side"].upper() != side.upper():
                continue
            filtered.append(t)
        return filtered

    # ---------------------------------------------------------------------
    # Optional retention (if configured) – Not used right now, but kept for future.
    # ---------------------------------------------------------------------
    def purge_older_than(self, days: int) -> None:
        """Remove trades older than *days* from the internal list. Does **not**
        modify the source JSON files (they are append‑only by the broker).
        """
        cutoff = int((datetime.now(timezone.utc) - timedelta(days=days)).timestamp() * 1000)
        self._trades = [t for t in self._trades if t["entry_ts"] >= cutoff]
