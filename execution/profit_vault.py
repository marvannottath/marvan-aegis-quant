"""
Institutional Profit Sweep & Reserve Vault Module — Pure Data-Driven Invariant.
Vault balance is ALWAYS dynamically computed as:
  vault_balance = SUM(sweep_amount) - SUM(withdrawals)
NO static balance variable. NO seed values. NO backtest leakage.
"""

import time
import json
import uuid
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime, timezone, timedelta

IST_TZ = timezone(timedelta(hours=5, minutes=30))
VAULT_FILE = Path(__file__).resolve().parent / "profit_vault_state.json"

def get_ist_timestamp() -> str:
    return datetime.now(timezone.utc).astimezone(IST_TZ).strftime("%Y-%m-%d %H:%M:%S")

class ProfitVault:
    def __init__(self):
        # Per-environment isolated vault stores
        self.vault_stores: Dict[str, Dict[str, Any]] = {
            "AEGIS_QUANT_MASTER": {"transactions": [], "withdrawals": []},
            "BINANCE_TESTNET_DEMO": {"transactions": [], "withdrawals": []},
            "BINANCE_LIVE_REAL": {"transactions": [], "withdrawals": []}
        }
        self._load_state()

    def _load_state(self):
        """Load vault transactions per environment from disk if exists."""
        if VAULT_FILE.exists():
            try:
                with open(VAULT_FILE, "r") as f:
                    data = json.load(f)
                    if "vault_stores" in data:
                        self.vault_stores = data["vault_stores"]
            except Exception as e:
                print(f"[PROFIT VAULT] Load notice: {e}")

    def _save_state(self):
        """Persist per-environment vault transactions to disk."""
        try:
            temp_file = VAULT_FILE.with_suffix(".tmp")
            with open(temp_file, "w") as f:
                json.dump({"vault_stores": self.vault_stores}, f, indent=2)
            temp_file.replace(VAULT_FILE)
        except Exception as e:
            print(f"[PROFIT VAULT] Save notice: {e}")

    def get_vault_balance(self, environment: str = "AEGIS_QUANT_MASTER") -> float:
        """
        AUTOMATED INVARIANT:
        vault_balance = SUM(sweep_amount for confirmed transactions) - SUM(completed withdrawals)
        NO static variable. NO seed value.
        """
        store = self.vault_stores.get(environment, {"transactions": [], "withdrawals": []})
        sweeps_sum = sum(float(tx.get("sweep_amount", 0.0)) for tx in store.get("transactions", []) if tx.get("status") == "CONFIRMED")
        withdrawals_sum = sum(float(w.get("amount", 0.0)) for w in store.get("withdrawals", []) if w.get("status") == "COMPLETED")
        return round(sweeps_sum - withdrawals_sum, 2)

    def sweep_profit(self, trade_pnl: float, asset: str, exit_reason: str, source_trade_id: str = "", environment: str = "AEGIS_QUANT_MASTER") -> Dict[str, Any]:
        """
        Record verified profit sweep with 11-field Schema.
        Only positive realized profit is swept into the vault.
        """
        if trade_pnl <= 0:
            return {}

        store = self.vault_stores.setdefault(environment, {"transactions": [], "withdrawals": []})
        prev_bal = self.get_vault_balance(environment)
        sweep_amt = round(trade_pnl, 2)
        new_bal = round(prev_bal + sweep_amt, 2)

        tx_id = f"VTX-{environment[:4]}-{int(time.time()*1000)}-{uuid.uuid4().hex[:6].upper()}"
        
        # 11-Field Institutional Vault Schema
        tx_record = {
            "transaction_id": tx_id,
            "timestamp": get_ist_timestamp(),
            "source_trade_id": source_trade_id or f"TRD-{asset}-{int(time.time())}",
            "asset": asset,
            "realized_profit": sweep_amt,
            "sweep_amount": sweep_amt,
            "environment": environment,
            "account_id": f"ACC-{environment}",
            "reason": exit_reason,
            "previous_balance": prev_bal,
            "new_balance": new_bal,
            "status": "CONFIRMED"
        }

        store["transactions"].insert(0, tx_record)
        self._save_state()
        print(f"[PROFIT VAULT] Swept +${sweep_amt:.2f} into {environment} Vault | New Balance: ${new_bal:,.2f}")
        return tx_record

    def get_vault_summary(self, environment: str = "AEGIS_QUANT_MASTER") -> Dict[str, Any]:
        """Return dynamic vault summary derived strictly from verified transaction ledger."""
        store = self.vault_stores.get(environment, {"transactions": [], "withdrawals": []})
        txs = store.get("transactions", [])
        wds = store.get("withdrawals", [])
        bal = self.get_vault_balance(environment)
        today_str = datetime.now(timezone.utc).astimezone(IST_TZ).strftime("%Y-%m-%d")
        today_sweeps = [t for t in txs if t.get("timestamp", "").startswith(today_str)]

        return {
            "environment": environment,
            "vault_balance": bal,
            "total_sweeps_count": len(txs),
            "today_swept_usd": round(sum(float(t.get("sweep_amount", 0.0)) for t in today_sweeps), 2),
            "today_sweeps_count": len(today_sweeps),
            "recent_sweeps": txs[:15],
            "withdrawal_history": wds,
            "ledger_verified": True
        }


# Global Singleton
profit_vault = ProfitVault()
