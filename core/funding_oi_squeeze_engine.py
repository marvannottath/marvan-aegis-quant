"""
Aegis-Quant Funding Rate & Open Interest (OI) Squeeze Predictor.
Reads Binance perpetual contract telemetry:
  - Funding Rate: Periodic payments between Longs and Shorts.
      * Negative Funding (< -0.01%): Shorts pay Longs. Extreme retail fear -> High probability SHORT SQUEEZE UP!
      * High Positive Funding (> +0.04%): Longs pay Shorts. Overheated greed -> High probability LONG SQUEEZE DOWN / FLUSH!
  - Open Interest (OI): Total unsettled derivative contracts. Rising OI during negative funding confirms institutional bear-trap accumulation.
Provides our Spot trading AI with unfair forward predictive timing!
"""

import time
import requests
from typing import Dict, Any
from datetime import datetime, timezone, timedelta

IST_TZ = timezone(timedelta(hours=5, minutes=30))

class FundingOISqueezeEngine:
    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_ttl_sec: float = 30.0  # Funding updates every few minutes
        self._session = requests.Session()

    def get_squeeze_metrics(self, symbol: str = "BTCUSDT") -> Dict[str, Any]:
        """
        Polls Binance Futures funding rate and open interest.
        """
        sym_clean = symbol.upper().replace("/", "").strip()
        now = time.time()

        cached = self._cache.get(sym_clean)
        if cached and (now - cached["epoch"]) < self._cache_ttl_sec:
            return cached["data"]

        funding_rate = 0.0
        open_interest = 0.0
        oi_notional_usd = 0.0

        try:
            # 1. Fetch latest funding rate
            url_f = f"https://fapi.binance.com/fapi/v1/fundingRate?symbol={sym_clean}&limit=1"
            rf = self._session.get(url_f, timeout=2.0)
            if rf.status_code == 200:
                data_f = rf.json()
                if data_f:
                    funding_rate = float(data_f[0].get("fundingRate", 0.0))

            # 2. Fetch Open Interest
            url_oi = f"https://fapi.binance.com/fapi/v1/openInterest?symbol={sym_clean}"
            ro = self._session.get(url_oi, timeout=2.0)
            if ro.status_code == 200:
                data_o = ro.json()
                open_interest = float(data_o.get("openInterest", 0.0))
        except Exception:
            pass

        funding_pct = round(funding_rate * 100.0, 4)

        # Interpret Squeeze Regime
        if funding_pct <= -0.0100:
            regime = "SHORT_SQUEEZE_IMMINENT"
            signal_bias = "AGGRESSIVE_BUY_BOUNCE"
            is_favorable_for_buy = True
            risk_level = "LOW_DOWNSIDE_RISK"
        elif funding_pct >= 0.0400:
            regime = "LONG_SQUEEZE_OVERHEATED"
            signal_bias = "PROFIT_TAKE_DEFENSE"
            is_favorable_for_buy = False
            risk_level = "ELEVATED_FLUSH_RISK"
        else:
            regime = "NORMAL_PERPETUAL_BALANCE"
            signal_bias = "NEUTRAL"
            is_favorable_for_buy = True
            risk_level = "NORMAL"

        data = {
            "symbol": sym_clean,
            "funding_rate": funding_rate,
            "funding_rate_pct": funding_pct,
            "annualized_funding_pct": round(funding_pct * 3 * 365, 2),
            "open_interest_contracts": open_interest,
            "squeeze_regime": regime,
            "signal_bias": signal_bias,
            "is_favorable_for_buy": is_favorable_for_buy,
            "risk_level": risk_level,
            "checked_at": datetime.now(timezone.utc).astimezone(IST_TZ).strftime("%Y-%m-%d %H:%M:%S IST")
        }

        self._cache[sym_clean] = {"epoch": now, "data": data}
        return data


# Global Singleton Instance
funding_oi_squeeze_engine = FundingOISqueezeEngine()
