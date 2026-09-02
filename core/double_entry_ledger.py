"""
Double-Entry Accounting & Multi-Ledger Engine for Aegis Quant.
Maintains 6 Isolated Ledgers:
  1. DEPOSIT_LEDGER
  2. TRADING_LEDGER
  3. REALIZED_PNL_LEDGER
  4. VAULT_LEDGER
  5. WITHDRAWAL_LEDGER
  6. FEES_LEDGER

Every balance is derived dynamically from verified debit/credit entries:
  - Deposit:     DR: Cash/Asset Account       | CR: Customer Trading Account
  - Withdrawal:  DR: Customer Trading Account | CR: Cash/Asset Account
  - Vault Sweep: DR: Customer Trading Account | CR: Vault Reserve Account
  - Trade PnL:   DR: Market Realized Gain     | CR: Customer Trading Account
  - Fee:         DR: Customer Trading Account | CR: Platform Fee Account
"""

import json
import uuid
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta

IST_TZ = timezone(timedelta(hours=5, minutes=30))
LEDGER_FILE = Path(__file__).resolve().parent.parent / "data" / "double_entry_ledger.json"

def get_ist_str() -> str:
    return datetime.now(timezone.utc).astimezone(IST_TZ).strftime("%Y-%m-%d %H:%M:%S")

class DoubleEntryLedger:
    def __init__(self):
        self.entries: List[Dict[str, Any]] = []
        self._load_ledger()

    def _load_ledger(self):
        if LEDGER_FILE.exists():
            try:
                with open(LEDGER_FILE, "r") as f:
                    data = json.load(f)
                    self.entries = data.get("entries", [])
            except Exception as e:
                print(f"[DOUBLE ENTRY LEDGER] Load error: {e}")

    def _save_ledger(self):
        try:
            LEDGER_FILE.parent.mkdir(parents=True, exist_ok=True)
            temp_file = LEDGER_FILE.with_suffix(".tmp")
            with open(temp_file, "w") as f:
                json.dump({"entries": self.entries}, f, indent=2)
            temp_file.replace(LEDGER_FILE)
        except Exception as e:
            print(f"[DOUBLE ENTRY LEDGER] Save error: {e}")

    def post_entry(
        self,
        ledger_type: str,
        debit_account: str,
        credit_account: str,
        amount: float,
        asset: str = "USDT",
        reference_id: str = "",
        environment: str = "AEGIS_QUANT_MASTER",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Record double-entry transaction.
        Debit Amount == Credit Amount strictly enforced.
        """
        if amount <= 0:
            raise ValueError("Ledger entry amount must be strictly positive.")

        entry_id = f"DEL-{ledger_type[:3]}-{int(time.time()*1000)}-{uuid.uuid4().hex[:6].upper()}"

        record = {
            "entry_id": entry_id,
            "timestamp": get_ist_str(),
            "ledger_type": ledger_type,
            "environment": environment,
            "debit_account": debit_account,
            "credit_account": credit_account,
            "amount": round(amount, 2),
            "asset": asset,
            "reference_id": reference_id or entry_id,
            "metadata": metadata or {},
            "status": "POSTED"
        }

        self.entries.insert(0, record)
        self._save_ledger()
        return record

    def ensure_opening_balance(self, environment: str = "AEGIS_QUANT_MASTER", amount: float = 100000.0) -> Dict[str, Any]:
        """
        Idempotently record the OPENING_BALANCE ledger transaction.
        DEBIT: Broker/Trading Asset ($100,000)
        CREDIT: Customer Trading Account ($100,000)
        """
        existing = [
            e for e in self.entries
            if e.get("environment") == environment
            and e.get("ledger_type") == "OPENING_BALANCE"
            and e.get("status") == "POSTED"
        ]
        if existing:
            return existing[0]

        return self.post_entry(
            ledger_type="OPENING_BALANCE",
            debit_account="BROKER_TRADING_ASSET",
            credit_account="CUSTOMER_TRADING_ACCOUNT",
            amount=amount,
            asset="USDT",
            reference_id=f"OPENING_BALANCE_{environment}",
            environment=environment,
            metadata={"description": "Initial Opening Capital Seed", "is_opening_balance": True}
        )

    def get_account_balance(self, account_name: str, environment: str = "AEGIS_QUANT_MASTER") -> float:
        """Dynamically compute account balance = Total Credits - Total Debits."""
        credits = sum(e["amount"] for e in self.entries if e.get("environment") == environment and e.get("credit_account") == account_name and e.get("status") == "POSTED")
        debits = sum(e["amount"] for e in self.entries if e.get("environment") == environment and e.get("debit_account") == account_name and e.get("status") == "POSTED")
        return round(credits - debits, 2)

    def get_ledger_history(self, ledger_type: Optional[str] = None, environment: str = "AEGIS_QUANT_MASTER") -> List[Dict[str, Any]]:
        return [e for e in self.entries if e.get("environment") == environment and (ledger_type is None or e.get("ledger_type") == ledger_type)]


# Global Singleton
double_entry_ledger = DoubleEntryLedger()
double_entry_ledger.ensure_opening_balance("AEGIS_QUANT_MASTER", 100000.0)
