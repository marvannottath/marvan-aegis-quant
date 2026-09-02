"""
Aegis-Quant User Wallet — 10-Bucket Balance Model.
All balances derived from the authoritative double-entry ledger.
No direct number storage — all values computed from ledger events.
"""

from typing import Dict, Any
from datetime import datetime, timezone, timedelta

IST_TZ = timezone(timedelta(hours=5, minutes=30))


class UserWallet:
    """
    10-bucket wallet model.
    All values computed from the double-entry ledger + live position data.
    """

    def compute_all(
        self,
        environment: str = "AEGIS_QUANT_MASTER",
    ) -> Dict[str, Any]:
        """
        Compute all 10 wallet buckets from authoritative sources.
        
        Sources:
          - double_entry_ledger: deposits, withdrawals, fees, PnL events
          - paper_broker:        live position margins + floating PnL
          - profit_vault:        secured vault balance
        """
        from core.double_entry_ledger import double_entry_ledger
        from execution.paper_broker    import paper_broker
        from execution.profit_vault    import profit_vault

        # 1. Compute ledger-derived values
        total_deposits    = double_entry_ledger.get_account_balance("CUSTOMER_TRADING_ACCOUNT", environment)
        total_withdrawals = abs(double_entry_ledger.get_account_balance("WITHDRAWAL_ACCOUNT", environment))
        realized_pnl      = double_entry_ledger.get_account_balance("REALIZED_PNL_ACCOUNT", environment)
        fees_paid         = abs(double_entry_ledger.get_account_balance("FEES_ACCOUNT", environment))
        locked_balance    = double_entry_ledger.get_account_balance("LOCKED_BALANCE_ACCOUNT", environment)

        # 2. Live broker state
        paper_broker._update_equity()
        used_margin      = sum(
            float(pos.get("capital_allocated", 0.0))
            for pos in paper_broker.positions.values()
        )
        unrealized_pnl   = round(
            sum(
                (float(pos.get("current_price", pos.get("entry_price", 0))) - float(pos.get("entry_price", 0)))
                * float(pos.get("units", 0))
                for pos in paper_broker.positions.values()
                if pos.get("side") == "BUY"
            ), 2
        )

        # 3. Vault balance
        vault_balance = round(float(profit_vault.vault_balance), 2)

        # 4. Compute derived buckets
        # Use broker's authoritative cash as the base for available
        cash = round(float(paper_broker.virtual_cash), 2)

        available_balance   = round(cash - locked_balance, 2)
        trading_balance     = round(cash - locked_balance - used_margin, 2)
        total_balance       = round(cash + used_margin + unrealized_pnl + locked_balance, 2)
        withdrawable_balance= round(max(0.0, available_balance - locked_balance), 2)

        # 5. Reconciliation check
        ledger_equity = round(total_deposits - total_withdrawals + realized_pnl - fees_paid, 2)
        broker_equity = round(float(paper_broker.equity), 2)
        recon_ok = abs(ledger_equity - broker_equity) < 1.0  # allow $1 float tolerance

        return {
            "environment":         environment,
            "computed_at":         datetime.now(timezone.utc).astimezone(IST_TZ).strftime("%Y-%m-%d %H:%M:%S IST"),
            # 10 buckets
            "total_balance":       total_balance,
            "available_balance":   available_balance,
            "trading_balance":     max(0.0, trading_balance),
            "used_margin":         round(used_margin, 2),
            "unrealized_pnl":      unrealized_pnl,
            "realized_pnl":        round(realized_pnl, 2),
            "fees_paid":           round(fees_paid, 2),
            "locked_balance":      round(locked_balance, 2),
            "withdrawable_balance":withdrawable_balance,
            "profit_vault":        vault_balance,
            # Reconciliation
            "ledger_equity":       ledger_equity,
            "broker_equity":       broker_equity,
            "reconciliation_ok":   recon_ok,
            "reconciliation_delta": round(abs(ledger_equity - broker_equity), 2),
        }


# Alias broker inside method
import importlib
def _get_broker():
    return importlib.import_module("execution.paper_broker").paper_broker


# Global singleton
user_wallet = UserWallet()
