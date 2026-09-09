"""
Aegis-Quant Indian Tax & Trade Statement Preparation Engine.
Generates institutional trade ledgers and statement reports for Indian equity & derivative trades.
Itemizes all Indian statutory and regulatory levies:
  1. Securities Transaction Tax (STT)
  2. Exchange Turnover Charges (NSE/BSE)
  3. SEBI Turnover Charges
  4. Stamp Duty
  5. Goods & Services Tax (GST 18%)
  6. Brokerage

Disclaimer:
This statement is for accounting reconciliation and recordkeeping only.
Does NOT constitute financial, legal, or tax advisory.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta

IST_TZ = timezone(timedelta(hours=5, minutes=30))


class IndiaStatementEngine:
    """Tax and Trade Statement Exporter for Indian Markets."""

    def __init__(self):
        pass

    def compute_statutory_charges(
        self,
        trade_value: float,
        side: str = "BUY",
        product: str = "CNC",
        brokerage_per_order: float = 20.0
    ) -> Dict[str, float]:
        """
        Compute standard Indian statutory charges on equity trades.
        Rates:
          - STT: 0.1% on delivery (BUY & SELL), 0.025% on intraday (SELL only)
          - Exchange Turnover: 0.00297%
          - SEBI Charges: 0.0001% (₹10 per crore)
          - Stamp Duty: 0.015% on BUY delivery, 0.003% on BUY intraday
          - GST: 18% on (Brokerage + Exchange Turnover + SEBI Charges)
        """
        trade_val = abs(trade_value)
        is_buy = side.upper() == "BUY"
        is_delivery = product.upper() == "CNC"

        # 1. Brokerage (capped at ₹20 or 0.05%)
        brokerage = min(brokerage_per_order, round(trade_val * 0.0005, 2))

        # 2. STT
        if is_delivery:
            stt = round(trade_val * 0.001, 2)
        else:
            stt = round(trade_val * 0.00025, 2) if not is_buy else 0.0

        # 3. Exchange Turnover (NSE 0.00297%)
        exchange_turnover = round(trade_val * 0.0000297, 2)

        # 4. SEBI Charges (0.0001%)
        sebi_charges = round(trade_val * 0.000001, 2)

        # 5. Stamp Duty (State Govt - on BUY side only)
        if is_buy:
            stamp_duty_rate = 0.00015 if is_delivery else 0.00003
            stamp_duty = round(trade_val * stamp_duty_rate, 2)
        else:
            stamp_duty = 0.0

        # 6. GST (18% on Brokerage + Exchange Turnover + SEBI)
        taxable_services = brokerage + exchange_turnover + sebi_charges
        gst = round(taxable_services * 0.18, 2)

        total_charges = round(brokerage + stt + exchange_turnover + sebi_charges + stamp_duty + gst, 2)

        return {
            "brokerage": brokerage,
            "stt": stt,
            "exchange_turnover": exchange_turnover,
            "sebi_charges": sebi_charges,
            "stamp_duty": stamp_duty,
            "gst": gst,
            "total_statutory_charges": total_charges
        }

    def generate_statement(self, trades: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Generate comprehensive trade statement and charges breakdown."""
        from execution.paper_broker import paper_broker
        pool = paper_broker.pools.get("AEGIS_INDIA_INR", {})
        trade_list = trades if trades is not None else pool.get("trade_history", [])

        statement_entries = []
        total_gross_pnl = 0.0
        total_statutory_charges = 0.0

        for t in trade_list:
            units = float(t.get("units", 1))
            entry = float(t.get("entry_price", 1000.0))
            exit_p = float(t.get("exit_price", entry))
            pnl_gross = float(t.get("pnl_usd", 0.0) or t.get("realized_pnl", 0.0))
            product = t.get("product", "CNC")
            side = t.get("side", "BUY")

            trade_val = round(units * entry, 2)
            charges = self.compute_statutory_charges(trade_val, side=side, product=product)
            tot_chg = charges["total_statutory_charges"]

            net_pnl = round(pnl_gross - tot_chg, 2)
            total_gross_pnl += pnl_gross
            total_statutory_charges += tot_chg

            statement_entries.append({
                "trade_id": t.get("trade_id", f"TRD-{int(time.time()*1000)}"),
                "order_id": t.get("order_id", ""),
                "date": t.get("timestamp", datetime.now(timezone.utc).astimezone(IST_TZ).strftime("%Y-%m-%d")),
                "settlement_date": "T+1 Rolling",
                "symbol": t.get("asset") or t.get("symbol", "NIFTY50"),
                "exchange": "NSE",
                "product": product,
                "side": side,
                "quantity": int(units),
                "buy_price": entry if side == "BUY" else exit_p,
                "sell_price": exit_p if side == "BUY" else entry,
                "gross_trade_value": trade_val,
                "charges": charges,
                "gross_pnl_inr": round(pnl_gross, 2),
                "net_pnl_inr": net_pnl,
                "currency": "INR",
                "currency_symbol": "₹"
            })

        net_total_pnl = round(total_gross_pnl - total_statutory_charges, 2)

        return {
            "title": "Aegis-Quant Indian Equity Trade & Statutory Statement",
            "environment": "AEGIS_INDIA_INR",
            "base_currency": "INR (₹)",
            "settlement_framework": "SEBI T+1 Rolling Settlement",
            "total_trades_count": len(statement_entries),
            "gross_realized_pnl": round(total_gross_pnl, 2),
            "total_statutory_levies": round(total_statutory_charges, 2),
            "net_realized_pnl": net_total_pnl,
            "disclaimer": "This document is generated for accounting reconciliation and transaction recordkeeping only. It does not constitute official tax advice.",
            "generated_at": datetime.now(timezone.utc).astimezone(IST_TZ).strftime("%Y-%m-%d %H:%M:%S IST"),
            "entries": statement_entries
        }


# Global Singleton
india_statement_engine = IndiaStatementEngine()
