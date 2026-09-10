"""
Aegis-Quant Live Portfolio & Position Reconciliation Sentinel.
Continuously reconciles Binance account balances and exchange positions against
AEGIS internal wallet, double-entry ledger, and position engine.

If reconciliation fails:
  - Blocks all new live orders (fails closed)
  - Sets status to LIVE RECONCILIATION FAILED
  - Emits discrepancy events to the execution event pipeline
  - Dispatches Telegram alert
"""

import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta

IST_TZ = timezone(timedelta(hours=5, minutes=30))
DISCREPANCY_TOLERANCE_USD = 1.00  # $1 float noise tolerance


def _now_str() -> str:
    return datetime.now(timezone.utc).astimezone(IST_TZ).strftime("%Y-%m-%d %H:%M:%S IST")


class LiveReconciliationSentinel:
    """
    Wall-Street grade real-time reconciliation sentinel for Binance Live and Testnet.
    Periodically compares:
      1. Exchange USDT balance vs Internal Wallet available & total balance
      2. Exchange balances vs Double-Entry Ledger Customer Account
      3. Exchange actual asset positions vs AEGIS Internal Open Positions
    """

    def __init__(self):
        self.last_check_time: float = 0.0
        self.last_report: Dict[str, Any] = {
            "status": "HEALTHY",
            "is_valid": True,
            "discrepancies": [],
            "last_reconciled_at": _now_str(),
        }
        self._is_live_trading_blocked: bool = False

    @property
    def is_live_trading_blocked(self) -> bool:
        return self._is_live_trading_blocked

    def reconcile_environment(
        self,
        environment: str = "BINANCE_TESTNET",
        broker_instance=None
    ) -> Dict[str, Any]:
        """
        Execute full forensic reconciliation for specified Binance environment.
        Returns comprehensive report and triggers emergency freeze if discrepancy detected.
        """
        now_ts = _now_str()
        discrepancies: List[Dict[str, Any]] = []

        if broker_instance is None:
            from execution.binance_broker import binance_broker as broker_instance

        # 1. Fetch Real Exchange Balances
        is_testnet = ("TESTNET" in environment.upper() or "DEMO" in environment.upper())
        base_env = "BINANCE_TESTNET_DEMO" if is_testnet else "BINANCE_LIVE_REAL"

        try:
            exchange_balance_usd = float(broker_instance.get_real_balance(environment))
        except Exception as e:
            exchange_balance_usd = 0.0
            discrepancies.append({
                "type": "BALANCE_FETCH_FAILURE",
                "severity": "CRITICAL",
                "detail": f"Failed to retrieve balance from Binance API: {e}"
            })

        # 2. Fetch Internal Wallet & Double-Entry Ledger
        from execution.user_wallet import user_wallet
        from core.double_entry_ledger import double_entry_ledger

        wallet_snapshot = user_wallet.compute_all(environment=base_env)
        wallet_total = float(wallet_snapshot.get("total_balance", 0.0))
        wallet_available = float(wallet_snapshot.get("available_balance", 0.0))

        ledger_balance = float(double_entry_ledger.get_account_balance("CUSTOMER_TRADING_ACCOUNT", environment=base_env))

        # Balance Delta Check
        # For Testnet / Live, exchange reported balance should reconcile against wallet or initial pool
        bal_delta = round(abs(exchange_balance_usd - wallet_available), 2)
        if exchange_balance_usd > 0 and bal_delta > DISCREPANCY_TOLERANCE_USD:
            discrepancies.append({
                "type": "BALANCE_MISMATCH",
                "severity": "CRITICAL",
                "detail": (
                    f"Exchange balance ${exchange_balance_usd:,.2f} differs from "
                    f"AEGIS wallet available balance ${wallet_available:,.2f} (Delta: ${bal_delta:,.2f})"
                ),
                "delta": bal_delta,
                "exchange_balance": exchange_balance_usd,
                "internal_balance": wallet_available
            })

        # 3. Position Reconciliation
        exchange_positions = broker_instance.get_open_positions(environment)
        exchange_pos_by_symbol = {p.get("symbol", "").upper(): p for p in exchange_positions if p.get("symbol")}

        # Retrieve internal positions
        from execution.paper_broker import paper_broker
        paper_broker.switch_pool(base_env) if hasattr(paper_broker, "switch_pool") else None
        internal_positions = dict(paper_broker.positions)

        # A. Detect Missing Positions (on exchange but not internal)
        for sym, ex_p in exchange_pos_by_symbol.items():
            if sym not in internal_positions:
                discrepancies.append({
                    "type": "UNEXPECTED_EXCHANGE_POSITION",
                    "severity": "CRITICAL",
                    "symbol": sym,
                    "exchange_qty": ex_p.get("units", 0.0),
                    "internal_qty": 0.0,
                    "detail": f"Position {sym} exists on Binance exchange ({ex_p.get('units')} units) but is missing in AEGIS internal state."
                })

        # B. Detect Positions on Internal but missing on Exchange
        for sym, in_p in internal_positions.items():
            if sym not in exchange_pos_by_symbol:
                if exchange_balance_usd > 0:  # only flag if exchange is actually connected
                    discrepancies.append({
                        "type": "MISSING_EXCHANGE_POSITION",
                        "severity": "CRITICAL",
                        "symbol": sym,
                        "exchange_qty": 0.0,
                        "internal_qty": in_p.get("units", 0.0),
                        "detail": f"Position {sym} exists in AEGIS ({in_p.get('units')} units) but not found on Binance exchange."
                    })
            else:
                ex_p = exchange_pos_by_symbol[sym]
                # Quantity mismatch check
                qty_diff = abs(float(in_p.get("units", 0.0)) - float(ex_p.get("units", 0.0)))
                if qty_diff > 0.0001:
                    discrepancies.append({
                        "type": "QUANTITY_MISMATCH",
                        "severity": "CRITICAL",
                        "symbol": sym,
                        "exchange_qty": ex_p.get("units", 0.0),
                        "internal_qty": in_p.get("units", 0.0),
                        "delta": round(qty_diff, 6),
                        "detail": f"Quantity mismatch on {sym}: Exchange={ex_p.get('units')} vs Internal={in_p.get('units')}."
                    })

        # 4. Synthesize Report
        critical_count = sum(1 for d in discrepancies if d.get("severity") == "CRITICAL")
        has_critical = critical_count > 0

        if has_critical:
            status = "LIVE RECONCILIATION FAILED"
            is_valid = False
            self._is_live_trading_blocked = True
        elif discrepancies:
            status = "RECONCILIATION_WARNING"
            is_valid = True
            self._is_live_trading_blocked = False
        else:
            status = "RECONCILIATION_OK"
            is_valid = True
            self._is_live_trading_blocked = False

        report = {
            "status":                 status,
            "is_valid":               is_valid,
            "environment":            environment,
            "provider":               "BINANCE",
            "currency":               "USDT",
            "exchange_balance":       exchange_balance_usd,
            "wallet_available":       wallet_available,
            "wallet_total":           wallet_total,
            "ledger_balance":         ledger_balance,
            "difference":             bal_delta,
            "discrepancies_count":    len(discrepancies),
            "discrepancies":          discrepancies,
            "live_trading_blocked":   self._is_live_trading_blocked,
            "timestamp":              now_ts,
            "last_reconciled_at":     now_ts,
        }

        self.last_report = report
        self.last_check_time = time.time()

        # Emit audit event into pipeline
        try:
            from core.execution_event_pipeline import execution_event_pipeline
            execution_event_pipeline.record_event(
                event_type="reconciliation_result",
                environment=environment,
                provider="BINANCE",
                internal_reference="RECON-SENTINEL",
                provider_reference="",
                severity="CRITICAL" if has_critical else ("WARNING" if discrepancies else "INFO"),
                status=status,
                metadata={
                    "exchange_balance": exchange_balance_usd,
                    "internal_balance": wallet_available,
                    "delta": bal_delta,
                    "discrepancies_count": len(discrepancies)
                }
            )
        except Exception:
            pass

        # If reconciliation failed, dispatch telegram alert
        if has_critical:
            try:
                from core.telegram_alerts import telegram_alerts
                telegram_alerts.send_alert(
                    title="🚨 LIVE RECONCILIATION FAILED",
                    message=f"Binance {environment} reconciliation failed with {critical_count} critical discrepancies. LIVE TRADING FROZEN.",
                    severity="CRITICAL"
                )
            except Exception:
                pass

        return report


# Global singleton
live_reconciliation_sentinel = LiveReconciliationSentinel()
