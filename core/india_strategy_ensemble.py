"""
Aegis-Quant 7-Agent Strategy Ensemble for Indian Equities (NSE/BSE).
Specialized Quantitative Sub-Agents:
  1. Trend AI (Supertrend + EMA Ribbons 20/50/200)
  2. Momentum AI (RSI 14 + MACD + Stochastic)
  3. Mean Reversion AI (Bollinger Bands + VWAP Standard Deviations)
  4. Volume AI (OBV + Institutional Delivery Proxy)
  5. Volatility AI (ATR + India VIX Regime)
  6. Market Regime AI (NIFTY 50 Directional Alignment)
  7. News/Event AI (Macro & Corporate Action Guard)

Strict Policy:
No agent may place an order directly.
All signals pass to the Risk Engine and Smart Router before execution authorization.
"""

from typing import Dict, Any, List, Optional
from core.indian_market_data import indian_market_data, INDIAN_UNIVERSE
from core.signal_ensemble import signal_ensemble_engine


class IndiaStrategyEnsemble:
    """7-Agent Consensus & Calibrated Signal Generator for Indian Equities."""

    def __init__(self):
        pass

    def evaluate_asset(self, symbol: str) -> Dict[str, Any]:
        """
        Run 7 specialized agents on an Indian equity or ETF using authentic Signal Ensemble Engine.
        Returns consensus direction, calibrated confidence %, entry, stop-loss, target, dynamic R:R, and risk gate.
        """
        quotes_res = indian_market_data.get_quotes([symbol])
        quotes = quotes_res.get("quotes", {})
        q = quotes.get(symbol)

        if not q:
            meta = INDIAN_UNIVERSE.get(symbol, {"base_price": 1000.0, "tick": 0.05})
            ltp = meta.get("base_price", 1000.0)
            vol = 0.015
        else:
            ltp = q["ltp"]
            vol = q.get("volatility", 0.015)

        sig_res = signal_ensemble_engine.evaluate_signal(symbol, ltp, vol)

        return {
            "symbol": symbol,
            "exchange": "NSE",
            "action": sig_res["action"],
            "direction": sig_res["direction"],
            "confidence_pct": sig_res["confidence"],
            "confidence": sig_res["confidence"],
            "score": sig_res["confidence"],
            "entry_price": ltp,
            "price": ltp,
            "stop_loss": sig_res["sl"],
            "sl": sig_res["sl"],
            "take_profit": sig_res["tp"],
            "tp": sig_res["tp"],
            "expected_rr": sig_res["rr"],
            "rr": sig_res["rr"],
            "risk_reward": sig_res["risk_reward"],
            "horizon": "INTRADAY (MIS) / DELIVERY (CNC)",
            "risk_state": sig_res["risk_state"],
            "is_approved": sig_res["is_approved"],
            "risk_score": round(100.0 - sig_res["confidence"], 1),
            "currency": "INR",
            "currency_symbol": "₹",
            "sub_agents": sig_res["sub_agent_breakdown"],
            "fortress_shields_passed": sig_res["fortress_shields_passed"],
            "model_status": "CALIBRATED_PROBABILITY"
        }

    def evaluate_all(self) -> List[Dict[str, Any]]:
        """Evaluate all Indian universe assets."""
        return [self.evaluate_asset(sym) for sym in INDIAN_UNIVERSE.keys()]


# Global Singleton
india_strategy_ensemble = IndiaStrategyEnsemble()

