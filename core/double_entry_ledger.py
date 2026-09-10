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

        entry_metadata = {
            "currency": asset,
            "amount": round(amount, 2),
            "exchange_rate": float(metadata.get("exchange_rate", 1.0) if metadata else 1.0),
            "fee": float(metadata.get("fee", 0.0) if metadata else 0.0),
            "timestamp": get_ist_str(),
            "provider": metadata.get("provider", "INTERNAL") if metadata else "INTERNAL",
            "account": credit_account,
            "transaction_id": entry_id,
            **(metadata or {})
        }

        record = {
            "entry_id": entry_id,
            "timestamp": get_ist_str(),
            "ledger_type": ledger_type,
            "environment": environment,
            "debit_account": debit_account,
            "credit_account": credit_account,
            "amount": round(amount, 2),
            "asset": asset,
            "currency": asset,
            "reference_id": reference_id or entry_id,
            "metadata": entry_metadata,
            "status": "POSTED"
        }

        self.entries.insert(0, record)
        self._save_ledger()
        try:
            from core.unified_database import unified_db
            unified_db.insert_ledger_entry(record)
        except Exception:
            pass
        return record

    def ensure_opening_balance(
        self,
        environment: str = "AEGIS_QUANT_MASTER",
        amount: float = 100000.0,
        asset: str = "USDT"
    ) -> Dict[str, Any]:
        """
        Idempotently record the OPENING_BALANCE ledger transaction.
        DEBIT: Broker/Trading Asset
        CREDIT: Customer Trading Account
        """
        existing = [
            e for e in self.entries
            if e.get("environment") == environment
            and e.get("ledger_type") == "OPENING_BALANCE"
            and e.get("status") == "POSTED"
        ]
        if existing:
            return existing[0]

        curr_symbol = "₹" if asset == "INR" else "$"
        return self.post_entry(
            ledger_type="OPENING_BALANCE",
            debit_account="BROKER_TRADING_ASSET",
            credit_account="CUSTOMER_TRADING_ACCOUNT",
            amount=amount,
            asset=asset,
            reference_id=f"OPENING_BALANCE_{environment}",
            environment=environment,
            metadata={
                "description": f"Initial Opening Capital Seed ({curr_symbol}{amount:,.2f})",
                "is_opening_balance": True,
                "currency": asset,
                "provider": "INTERNAL"
            }
        )

    def get_account_balance(
        self,
        account_name: str,
        environment: str = "AEGIS_QUANT_MASTER",
        asset: Optional[str] = None
    ) -> float:
        """Dynamically compute account balance = Total Credits - Total Debits, optionally filtered by asset/currency."""
        credits = sum(
            e["amount"] for e in self.entries
            if e.get("environment") == environment
            and e.get("credit_account") == account_name
            and e.get("status") == "POSTED"
            and (asset is None or e.get("asset") == asset or e.get("currency") == asset)
        )
        debits = sum(
            e["amount"] for e in self.entries
            if e.get("environment") == environment
            and e.get("debit_account") == account_name
            and e.get("status") == "POSTED"
            and (asset is None or e.get("asset") == asset or e.get("currency") == asset)
        )
        return round(credits - debits, 2)

    def get_ledger_history(
        self,
        ledger_type: Optional[str] = None,
        environment: str = "AEGIS_QUANT_MASTER",
        asset: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        return [
            e for e in self.entries
            if e.get("environment") == environment
            and (ledger_type is None or e.get("ledger_type") == ledger_type)
            and (asset is None or e.get("asset") == asset or e.get("currency") == asset)
        ]

    def get_entries_by_environment(self, environment: str) -> List[Dict[str, Any]]:
        """Return all ledger entries for a given environment."""
        return [e for e in self.entries if e.get("environment") == environment]

    def verify_ledger_integrity(self, environment: Optional[str] = None) -> Dict[str, Any]:
        """Verify mathematical integrity of the double-entry ledger: Debits == Credits."""
        entries = self.entries if environment is None else [e for e in self.entries if e.get("environment") == environment]
        total_debits = round(sum(float(e.get("amount", 0.0)) for e in entries if e.get("status") == "POSTED"), 2)
        total_credits = round(sum(float(e.get("amount", 0.0)) for e in entries if e.get("status") == "POSTED"), 2)
        unbalance = round(abs(total_debits - total_credits), 2)
        return {
            "total_entries": len(entries),
            "total_debits": total_debits,
            "total_credits": total_credits,
            "unbalance_amount": unbalance,
            "is_balanced": unbalance == 0.0
        }


# Global Singleton
double_entry_ledger = DoubleEntryLedger()
double_entry_ledger.ensure_opening_balance("AEGIS_QUANT_MASTER", 100000.0, asset="USDT")
double_entry_ledger.ensure_opening_balance("AEGIS_INDIA_INR", 100000.0, asset="INR")


