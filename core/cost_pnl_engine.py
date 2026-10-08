"""
Aegis-Quant Authoritative Cost + PnL Engine.
Single Authoritative Calculation Path for Trade Economics.

Formula:
  Gross PnL - Applicable Costs = Net PnL

Applicable Costs Breakdown:
  Costs = entry_fee + exit_fee + commission + spread_cost + slippage_cost + funding_cost + swap_cost + taxes_charges

Authoritative consumer feeds:
- live PnL
- portfolio equity
- performance curve
- profit vault allocation
- double-entry ledger reconciliation
- backtest & trade analytics
"""

from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional

# Venue / Broker Standard Fee & Tax Rates (dynamic defaults)
VENUE_DEFAULTS = {
    "BINANCE": {
        "spot_maker_fee_pct": 0.075,      # with BNB / tier
        "spot_taker_fee_pct": 0.10,
        "futures_maker_fee_pct": 0.02,
        "futures_taker_fee_pct": 0.05,
        "funding_interval_hours": 8,
        "tax_rate_pct": 0.0,             # offshore
    },
    "UPSTOX": {
        "equity_delivery_brokerage": 0.0,
        "equity_intraday_brokerage_pct": 0.05,
        "max_brokerage_per_order_inr": 20.0,
        "stt_ctt_pct": 0.025,            # Securities Transaction Tax
        "exchange_turnover_pct": 0.00345,
        "gst_pct": 18.0,                 # 18% on brokerage + turnover
        "sebi_charges_pct": 0.0001,
        "stamp_duty_pct": 0.003,
    },
    "MT5": {
        "commission_per_lot_usd": 3.50,  # $7 round-turn
        "typical_spread_pips": 1.2,
        "swap_rate_annual_pct": 2.5,
    },
    "CTRADER": {
        "commission_per_million_usd": 30.0,
        "typical_spread_pips": 0.3,
        "swap_rate_annual_pct": 2.5,
    }
}


@dataclass
class TradeEconomics:
    symbol: str
    side: str                          # BUY / SELL (or LONG / SHORT)
    quantity: float
    entry_price: float
    exit_price: float
    currency: str                      # USDT | INR | USD
    instrument: str                    # SPOT | FUTURES | EQUITY | FOREX | COMMODITY
    broker: str                        # BINANCE | UPSTOX | MT5 | CTRADER

    # Economics Breakdown
    gross_pnl: float
    entry_fee: float
    exit_fee: float
    commission: float
    spread_cost: float
    slippage_cost: float
    funding_cost: float
    swap_cost: float
    taxes_charges: float
    total_costs: float
    net_pnl: float
    net_pnl_pct: float
    is_profit: bool

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class CostPnLEngine:
    """Authoritative Trade Economics and Cost + PnL Calculator."""

    def calculate_trade_economics(
        self,
        symbol: str,
        side: str,
        quantity: float,
        entry_price: float,
        exit_price: float,
        currency: str = "USDT",
        instrument: str = "SPOT",
        broker: str = "BINANCE",
        entry_fee: Optional[float] = None,
        exit_fee: Optional[float] = None,
        commission: Optional[float] = None,
        spread_cost: Optional[float] = None,
        slippage_cost: Optional[float] = None,
        funding_cost: Optional[float] = None,
        swap_cost: Optional[float] = None,
        taxes_charges: Optional[float] = None,
        expected_price: Optional[float] = None
    ) -> TradeEconomics:
        """
        Calculate complete trade economics with deterministic formula:
        Gross PnL - (All applicable costs) = Net PnL
        """
        side_norm = side.upper()
        is_long = side_norm in ["BUY", "LONG"]

        # 1. Gross PnL
        if is_long:
            gross_pnl = (exit_price - entry_price) * quantity
        else:
            gross_pnl = (entry_price - exit_price) * quantity

        entry_val = entry_price * quantity
        exit_val = exit_price * quantity

        # 2. Broker / Venue specific cost derivation if not explicitly provided
        broker_norm = broker.upper()
        calc_entry_fee = entry_fee if entry_fee is not None else 0.0
        calc_exit_fee = exit_fee if exit_fee is not None else 0.0
        calc_commission = commission if commission is not None else 0.0
        calc_spread = spread_cost if spread_cost is not None else 0.0
        calc_slippage = slippage_cost if slippage_cost is not None else 0.0
        calc_funding = funding_cost if funding_cost is not None else 0.0
        calc_swap = swap_cost if swap_cost is not None else 0.0
        calc_taxes = taxes_charges if taxes_charges is not None else 0.0

        # Slippage calculation if expected price is provided
        if slippage_cost is None and expected_price is not None and expected_price > 0:
            slip_diff = abs(entry_price - expected_price) * quantity
            calc_slippage = round(slip_diff, 4)

        # Dynamic default fees when not provided explicitly
        if entry_fee is None:
            if "BINANCE" in broker_norm:
                rate = VENUE_DEFAULTS["BINANCE"]["spot_taker_fee_pct"] / 100.0
                calc_entry_fee = round(entry_val * rate, 4)
            elif "UPSTOX" in broker_norm or currency == "INR":
                rate = VENUE_DEFAULTS["UPSTOX"]["equity_intraday_brokerage_pct"] / 100.0
                calc_entry_fee = min(VENUE_DEFAULTS["UPSTOX"]["max_brokerage_per_order_inr"], round(entry_val * rate, 2))
            elif "MT5" in broker_norm or "FOREX" in broker_norm:
                calc_entry_fee = round(quantity * 3.50, 2)  # half-turn

        if exit_fee is None:
            if "BINANCE" in broker_norm:
                rate = VENUE_DEFAULTS["BINANCE"]["spot_taker_fee_pct"] / 100.0
                calc_exit_fee = round(exit_val * rate, 4)
            elif "UPSTOX" in broker_norm or currency == "INR":
                rate = VENUE_DEFAULTS["UPSTOX"]["equity_intraday_brokerage_pct"] / 100.0
                calc_exit_fee = min(VENUE_DEFAULTS["UPSTOX"]["max_brokerage_per_order_inr"], round(exit_val * rate, 2))
            elif "MT5" in broker_norm or "FOREX" in broker_norm:
                calc_exit_fee = round(quantity * 3.50, 2)

        # Taxes for Indian Equities (STT + GST + Stamp Duty)
        if taxes_charges is None and (currency == "INR" or "UPSTOX" in broker_norm):
            stt = round(exit_val * (VENUE_DEFAULTS["UPSTOX"]["stt_ctt_pct"] / 100.0), 2)
            gst = round((calc_entry_fee + calc_exit_fee) * (VENUE_DEFAULTS["UPSTOX"]["gst_pct"] / 100.0), 2)
            calc_taxes = round(stt + gst, 2)

        # 3. Total Costs
        total_costs = (
            calc_entry_fee +
            calc_exit_fee +
            calc_commission +
            calc_spread +
            calc_slippage +
            calc_funding +
            calc_swap +
            calc_taxes
        )

        # 4. Net PnL = Gross PnL - Total Costs
        net_pnl = gross_pnl - total_costs
        capital_base = max(1.0, entry_val)
        net_pnl_pct = (net_pnl / capital_base) * 100.0

        return TradeEconomics(
            symbol=symbol,
            side=side_norm,
            quantity=round(quantity, 6),
            entry_price=round(entry_price, 4),
            exit_price=round(exit_price, 4),
            currency=currency,
            instrument=instrument,
            broker=broker,
            gross_pnl=round(gross_pnl, 2),
            entry_fee=round(calc_entry_fee, 2),
            exit_fee=round(calc_exit_fee, 2),
            commission=round(calc_commission, 2),
            spread_cost=round(calc_spread, 2),
            slippage_cost=round(calc_slippage, 2),
            funding_cost=round(calc_funding, 2),
            swap_cost=round(calc_swap, 2),
            taxes_charges=round(calc_taxes, 2),
            total_costs=round(total_costs, 2),
            net_pnl=round(net_pnl, 2),
            net_pnl_pct=round(net_pnl_pct, 2),
            is_profit=net_pnl > 0
        )

    def calculate_unrealized_pnl(
        self,
        side: str,
        quantity: float,
        entry_price: float,
        current_price: float,
        currency: str = "USDT",
        broker: str = "BINANCE",
        entry_fee: float = 0.0
    ) -> Dict[str, float]:
        """Calculate live floating unrealized PnL and estimated exit costs."""
        is_long = side.upper() in ["BUY", "LONG"]
        if is_long:
            gross = (current_price - entry_price) * quantity
        else:
            gross = (entry_price - current_price) * quantity

        current_val = current_price * quantity
        est_exit_fee = 0.0
        if "BINANCE" in broker.upper():
            est_exit_fee = round(current_val * 0.001, 2)
        elif currency == "INR":
            est_exit_fee = min(20.0, round(current_val * 0.0005, 2))

        net = gross - entry_fee - est_exit_fee
        entry_val = max(1.0, entry_price * quantity)
        pnl_pct = (net / entry_val) * 100.0

        return {
            "gross_unrealized_pnl": round(gross, 2),
            "estimated_exit_costs": round(est_exit_fee, 2),
            "net_unrealized_pnl": round(net, 2),
            "unrealized_pnl_pct": round(pnl_pct, 2)
        }


# Global singleton
cost_pnl_engine = CostPnLEngine()
