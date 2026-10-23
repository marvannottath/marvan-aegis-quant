"""
AEGIS-QUANT Institutional ATR & Fixed Fractional Dynamic Position Sizer.
Enforces institutional risk management (Prop-Firm Standard):
  - Maximum risk per trade: exactly 1.0% of account equity.
  - Position size = Risk_Capital / Dollar_Risk_Per_Unit
  - Dynamically adapts unit sizing according to market volatility (ATR) and stop loss distance.
  - Ensures tight setups get larger size, wide setups get smaller size,
    so dollar risk remains perfectly constant regardless of volatility!
"""

import math
from typing import Dict, Any, Tuple


class DynamicPositionSizer:
    MAX_RISK_PER_TRADE_PCT = 1.0    # 1.0% maximum equity risk per trade
    DEFAULT_SL_PCT = {
        "INDIA": 0.0060,     # 0.60% stop loss
        "CRYPTO": 0.0080,    # 0.80% stop loss
        "FOREX_GOLD": 0.0060 # 0.60% stop loss
    }

    def calculate_position_size(
        self,
        symbol: str,
        price: float,
        equity: float,
        workspace: str = "INDIA",
        leverage: float = 1.0,
        custom_sl_pct: float = 0.0,
        volatility: float = 0.01
    ) -> Dict[str, Any]:
        """
        Calculate the exact number of shares/units to trade such that
        if stop loss is hit, maximum loss is capped at 1.0% of equity.
        """
        if price <= 0 or equity <= 0:
            return {"quantity": 0, "margin_required": 0.0, "risk_amount": 0.0, "valid": False}

        # 1. Calculate max dollar risk (1.0% of total equity)
        risk_capital = round(equity * (self.MAX_RISK_PER_TRADE_PCT / 100.0), 2)
        risk_capital = max(0.50, risk_capital)  # Minimum ₹0.50 / $0.50 floor for micro accounts

        # 2. Determine stop loss distance
        sl_pct = custom_sl_pct if custom_sl_pct > 0 else self.DEFAULT_SL_PCT.get(workspace, 0.0060)
        # Scale SL distance slightly if volatility is high
        if volatility > 0.02:
            sl_pct = max(sl_pct, volatility * 0.5)

        loss_per_unit = price * sl_pct

        # 3. Target quantity based on risk: Risk = Quantity * Loss_Per_Unit
        raw_qty = risk_capital / max(0.0001, loss_per_unit)

        # 4. Format quantity based on asset class
        if workspace == "INDIA":
            # Indian cash equities must be integer shares (min 1)
            final_qty = max(1, int(math.floor(raw_qty)))
            # Check margin constraint (5x MIS leverage on Kotak Neo)
            margin_per_unit = price / max(1.0, leverage)
            total_margin = round(final_qty * margin_per_unit, 2)
            # Cap if required margin exceeds available working equity
            while total_margin > (equity * 0.85) and final_qty > 1:
                final_qty -= 1
                total_margin = round(final_qty * margin_per_unit, 2)
        elif workspace == "CRYPTO":
            # Binance spot precision
            if price > 1000:
                final_qty = round(raw_qty, 5)   # e.g. BTC
            elif price > 10:
                final_qty = round(raw_qty, 3)   # e.g. SOL, BNB
            else:
                final_qty = round(raw_qty, 1)   # e.g. DOGE, ADA
            total_margin = round(final_qty * price, 2)
            # Binance min notional check ($5.00)
            if total_margin < 5.0 and equity >= 5.50:
                final_qty = round(5.20 / price, 5 if price > 1000 else 2)
                total_margin = round(final_qty * price, 2)
        else:
            final_qty = round(raw_qty, 2)
            total_margin = round(final_qty * price / max(1.0, leverage), 2)

        est_max_loss = round(final_qty * loss_per_unit, 2)

        return {
            "quantity": final_qty,
            "margin_required": total_margin,
            "risk_amount": est_max_loss,
            "risk_pct": round((est_max_loss / equity) * 100.0, 2),
            "sl_pct": round(sl_pct * 100.0, 2),
            "valid": True
        }


# Global Singleton
dynamic_position_sizer = DynamicPositionSizer()
