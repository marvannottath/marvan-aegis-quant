"""
Aegis-Quant Dynamic ATR Volatility Take-Profit & Stop-Loss Engine.
Calculates dynamic institutional exit barriers based on Average True Range (ATR):
  - Quiet/Chop regimes: Quick scalp targets (TP: +0.35% to +0.45%, SL: -0.40%)
  - Normal regimes: Standard targets (TP: +0.60%, SL: -0.80%)
  - High-volatility breakouts: Expansive targets (TP: +1.20% to +2.50%, SL: -1.00%)
Allows winning momentum runners to run without getting prematurely closed at tiny micro-targets.
"""

import time
import requests
from typing import Dict, Any
from datetime import datetime, timezone, timedelta

IST_TZ = timezone(timedelta(hours=5, minutes=30))

class DynamicATRTargets:
    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_ttl_sec: float = 15.0
        self._session = requests.Session()

    def calculate_atr(self, symbol: str, period: int = 14, interval: str = "5m") -> float:
        """Fetch 5m candles and compute 14-period ATR."""
        sym_clean = symbol.upper().replace("/", "").strip()
        try:
            url = f"https://api.binance.com/api/v3/klines?symbol={sym_clean}&interval={interval}&limit={period + 2}"
            res = self._session.get(url, timeout=1.8)
            if res.status_code == 200:
                klines = res.json()
                tr_list = []
                for i in range(1, len(klines)):
                    h = float(klines[i][2])
                    l = float(klines[i][3])
                    prev_c = float(klines[i - 1][4])
                    tr = max(h - l, abs(h - prev_c), abs(l - prev_c))
                    tr_list.append(tr)
                if tr_list:
                    return sum(tr_list[-period:]) / len(tr_list[-period:])
        except Exception:
            pass
        return 0.0

    def get_dynamic_exit_targets(self, symbol: str, entry_price: float, workspace: str = "CRYPTO") -> Dict[str, Any]:
        """
        Computes dynamic Take Profit and Stop Loss prices and percentages based on live ATR volatility.
        """
        sym_clean = symbol.upper().replace("/", "").strip()
        now = time.time()

        cached = self._cache.get(sym_clean)
        if cached and (now - cached["epoch"]) < self._cache_ttl_sec:
            c_data = cached["data"]
            # Recalculate prices with the new entry price
            tp_pct = c_data["tp_pct"]
            sl_pct = c_data["sl_pct"]
            return {
                "symbol": sym_clean,
                "entry_price": entry_price,
                "atr": c_data["atr"],
                "volatility_regime": c_data["volatility_regime"],
                "tp_pct": tp_pct,
                "sl_pct": sl_pct,
                "take_profit_price": round(entry_price * (1.0 + tp_pct / 100.0), 4 if entry_price < 10 else 2),
                "stop_loss_price": round(entry_price * (1.0 - sl_pct / 100.0), 4 if entry_price < 10 else 2)
            }

        atr = self.calculate_atr(sym_clean, period=14, interval="5m")

        if entry_price > 0 and atr > 0:
            atr_pct = (atr / entry_price) * 100.0

            # Scale TP by 1.5x ATR and SL by 1.0x ATR
            raw_tp = atr_pct * 1.5
            raw_sl = atr_pct * 1.0

            # Clamp boundaries:
            # TP between 1.50% and 4.00% (ensures meaningful reward)
            tp_pct = round(max(1.50, min(4.00, raw_tp)), 2)
            # SL between 1.20% and 2.50% (gives trade breathing room beyond noise)
            sl_pct = round(max(1.20, min(2.50, raw_sl)), 2)

            if atr_pct > 0.80:
                regime = "HIGH_VOLATILITY_EXPANSION"
            elif atr_pct < 0.25:
                regime = "LOW_VOLATILITY_CHOP"
            else:
                regime = "NORMAL_TREND"
        else:
            # Fallback to calibrated institutional baseline with proper breathing room
            if workspace == "INDIA":
                tp_pct = 1.80
                sl_pct = 1.50
            elif workspace == "CRYPTO":
                tp_pct = 2.50
                sl_pct = 2.00
            else:
                tp_pct = 1.60
                sl_pct = 1.40
            atr = 0.0
            regime = "BASELINE_CALIBRATED"

        tp_price = round(entry_price * (1.0 + tp_pct / 100.0), 4 if entry_price < 10 else 2)
        sl_price = round(entry_price * (1.0 - sl_pct / 100.0), 4 if entry_price < 10 else 2)

        data = {
            "symbol": sym_clean,
            "entry_price": entry_price,
            "atr": round(atr, 4),
            "volatility_regime": regime,
            "tp_pct": tp_pct,
            "sl_pct": sl_pct,
            "take_profit_price": tp_price,
            "stop_loss_price": sl_price,
            "risk_reward_ratio": round(tp_pct / max(0.01, sl_pct), 2),
            "calculated_at": datetime.now(timezone.utc).astimezone(IST_TZ).strftime("%Y-%m-%d %H:%M:%S IST")
        }

        self._cache[sym_clean] = {"epoch": now, "data": data}
        return data


# Global Singleton Instance
dynamic_atr_targets = DynamicATRTargets()
