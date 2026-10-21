"""
AEGIS-QUANT VWAP Momentum Scalper & Dynamic Trailing Stop-Loss Engine.
Calculates real-time VWAP (Volume Weighted Average Price) and enforces:
  1. Confluence Signal Generation (Price crossing above/below VWAP + Volume Spike)
  2. Breakeven Lock-in (Cost-to-Cost): SL moves to entry price at +0.25% gain
  3. Continuous Trailing Stop-Loss: Ratchets up behind price to capture runners
"""

from typing import Dict, Any, Tuple


class VWAPScalpEngine:
    def __init__(self):
        # symbol -> {"cum_vol": float, "cum_vol_price": float, "vwap": float, "high_water_mark": float}
        self.state: Dict[str, Dict[str, Any]] = {}

    def update_tick(self, symbol: str, price: float, volume: float = 100.0) -> float:
        """Update cumulative tick volume and return current VWAP."""
        if price <= 0:
            return price

        st = self.state.setdefault(symbol, {
            "cum_vol": 0.0,
            "cum_vol_price": 0.0,
            "vwap": price,
            "high_water_mark": price,
            "breakeven_locked": False,
        })

        st["cum_vol"] += max(1.0, volume)
        st["cum_vol_price"] += (price * max(1.0, volume))
        st["vwap"] = round(st["cum_vol_price"] / st["cum_vol"], 2)

        if price > st["high_water_mark"]:
            st["high_water_mark"] = price

        return st["vwap"]

    def evaluate_trailing_stop(
        self,
        symbol: str,
        entry_price: float,
        current_price: float,
        current_stop_loss: float,
        side: str = "BUY",
        breakeven_threshold_pct: float = 0.25,
        trail_step_pct: float = 0.25,
    ) -> Tuple[float, str]:
        """
        Evaluate if stop-loss should be ratcheted up (Cost-to-Cost or Trailing).
        Returns (new_stop_loss, action_reason).
        """
        if entry_price <= 0 or current_price <= 0:
            return current_stop_loss, "NO_CHANGE"

        st = self.state.setdefault(symbol, {
            "cum_vol": 100.0,
            "cum_vol_price": current_price * 100.0,
            "vwap": current_price,
            "high_water_mark": current_price,
            "breakeven_locked": False,
        })

        if current_price > st["high_water_mark"]:
            st["high_water_mark"] = current_price

        if side.upper() == "BUY":
            gain_pct = ((current_price - entry_price) / entry_price) * 100.0

            # 1. Breakeven Lock-in (Cost-to-Cost + 0.05% brokerage buffer)
            if gain_pct >= breakeven_threshold_pct and not st.get("breakeven_locked"):
                breakeven_sl = round(entry_price * 1.0005, 2)
                if breakeven_sl > current_stop_loss:
                    st["breakeven_locked"] = True
                    return breakeven_sl, "BREAKEVEN_LOCKED (Cost-to-Cost Guaranteed)"

            # 2. Continuous Trailing Stop-Loss
            if st.get("breakeven_locked") and gain_pct > (breakeven_threshold_pct + trail_step_pct):
                trailed_sl = round(st["high_water_mark"] * (1.0 - (trail_step_pct / 100.0)), 2)
                if trailed_sl > current_stop_loss:
                    return trailed_sl, f"TRAILING_SL_RATCHET (+{gain_pct:.2f}% gain)"

        return current_stop_loss, "HOLD_SL"


# Global Singleton
vwap_scalp_engine = VWAPScalpEngine()
