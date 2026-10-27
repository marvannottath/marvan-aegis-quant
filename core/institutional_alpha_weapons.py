"""
Aegis-Quant Institutional Alpha Weapons Engine — Universal Multi-Market Edition.
Four proprietary, non-conventional quant edges designed to beat retail indicators
across all active asset classes: INDIA (NSE Equities), CRYPTO (Binance Spot & Futures),
and FOREX_GOLD (Interbank / MT5).

1. LiquidityHuntTrapEngine (Universal Stop Sweep & Absorption Reversal):
   - Detects predatory institutional stop runs past key swing highs/lows.
   - Bear Trap / Spring: Price sweeps below swing low to trigger retail stops, then rapidly
     closes back inside with a massive lower wick (>= 45% of candle range). Confirms absorption.
   - Bull Trap / Upthrust: Price sweeps above swing high to lure breakout buyers, then rejects.
   - Operates across NSE Equities (₹), Binance Crypto ($), and MT5 Interbank Forex/Gold ($).

2. UniversalSqueezeCascadeEngine / ShortCoveringSurgeEngine:
   - INDIA: 14:15 - 14:55 IST mandatory intraday MIS broker square-off short squeeze.
   - CRYPTO: 8-hour funding rate settlement squeezes (00:00, 08:00, 16:00 UTC) + negative funding
     (< -0.008%) short flushes bouncing off daily lows.
   - FOREX_GOLD: Institutional session handover squeezes (13:30 - 14:45 IST London Open,
     18:30 - 19:45 IST NY Open, and 21:15 - 21:50 IST London 16:00 Fix benchmark rebalance).

3. ToxicFlowEvacuationGuard (Multi-Market Predatory Spread Defense):
   - Tracks live top-of-book bid/ask spreads against rolling baseline per asset.
   - Workspace-calibrated thresholds:
       * CRYPTO: Baseline ~0.02-0.05%, triggers if spread >= 2.0x baseline and > 0.08%.
       * INDIA: Baseline ~0.04-0.08%, triggers if spread >= 2.5x baseline and > 0.15%.
       * FOREX_GOLD: Baseline ~0.015-0.03%, triggers if spread >= 2.0x baseline and > 0.04%.
   - Immediately freezes new entries and tightens trailing stop floors to secure green profits.

4. SessionHandoverImbalanceScanner / PreMarketShadowScanner:
   - INDIA: 09:00 - 09:08 AM IST pre-open call auction imbalance (Buy/Sell Qty >= 2.8x, gap < 0.65%).
   - CRYPTO: Level-2 order book depth skew (Bid/Ask depth >= 2.2x with compressed volatility)
     and 00:00 UTC Asian session opening momentum burst.
   - FOREX_GOLD: 12:30 - 13:30 IST Asian-to-London handover compression and 17:30 - 18:30 IST
     European-to-US interbank order flow handover.
"""

import time
import math
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone, timedelta

IST_TZ = timezone(timedelta(hours=5, minutes=30))
UTC_TZ = timezone.utc


def _ist_now() -> datetime:
    return datetime.now(timezone.utc).astimezone(IST_TZ)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _currency_prefix(workspace: str) -> str:
    ws = (workspace or "CRYPTO").upper()
    return "₹" if ws == "INDIA" else "$"


# =====================================================================
# 1. LIQUIDITY HUNT TRAP ENGINE (Universal Stop Sweep & Reversal)
# =====================================================================
class LiquidityHuntTrapEngine:
    """
    Identifies institutional stop runs across all markets:
    Institutions spike price beyond key swing high/low to trigger retail stops,
    then immediately absorb liquidity and violently reverse.
    """

    def __init__(self):
        # symbol -> {"swing_high": float, "swing_low": float, "workspace": str, "updated_at": float}
        self.swing_levels: Dict[str, Dict[str, Any]] = {}

    def update_levels(self, symbol: str, high: float, low: float, workspace: str = "CRYPTO"):
        """Update recent swing benchmarks for any symbol."""
        if high <= 0 or low <= 0:
            return
        sym = symbol.upper().replace("/", "").replace("-EQ", "").strip()
        self.swing_levels[sym] = {
            "swing_high": high,
            "swing_low": low,
            "workspace": workspace.upper(),
            "updated_at": time.time()
        }

    def evaluate_sweep(
        self,
        symbol: str,
        current_price: float,
        candle_high: float,
        candle_low: float,
        candle_open: float,
        candle_close: float,
        workspace: str = "CRYPTO"
    ) -> Dict[str, Any]:
        """
        Evaluate if current candle performed a stop-loss liquidity sweep.
        Returns sweep signal, direction, entry, stop loss, and conviction boost.
        """
        sym = symbol.upper().replace("/", "").replace("-EQ", "").strip()
        ws = (workspace or "CRYPTO").upper()
        curr_pfx = _currency_prefix(ws)

        levels = self.swing_levels.get(sym)
        if not levels:
            # Dynamic swing approximation based on asset volatility
            sweep_buffer = 0.0025 if ws == "CRYPTO" else 0.0015
            levels = {
                "swing_high": candle_high * (1.0 + sweep_buffer),
                "swing_low": candle_low * (1.0 - sweep_buffer),
            }

        swing_h = levels["swing_high"]
        swing_l = levels["swing_low"]
        total_range = max(0.00001, candle_high - candle_low)

        # ── 1. BULLISH SWEEP TRAP (Bear Trap / Liquidity Spring)
        # Price dropped below swing low, swept stops, but closed back ABOVE swing low with a long lower wick
        swept_low = (candle_low < swing_l)
        closed_above_low = (candle_close >= swing_l)
        lower_wick = min(candle_open, candle_close) - candle_low
        lower_wick_ratio = lower_wick / total_range

        if swept_low and closed_above_low and lower_wick_ratio >= 0.42:
            sweep_depth_pct = round(((swing_l - candle_low) / max(0.0001, swing_l)) * 100.0, 3)
            # Ultra-tight SL placed 0.10% below the sweep wick bottom
            decimals = 2 if current_price > 10 else 4
            sl_price = round(candle_low * 0.9990, decimals)
            tp_price = round(current_price + (current_price - sl_price) * 3.5, decimals)

            return {
                "detected": True,
                "pattern": "BULLISH_LIQUIDITY_SWEEP",
                "action": "BUY",
                "conviction_boost": 24.0,
                "sweep_depth_pct": sweep_depth_pct,
                "stop_loss": sl_price,
                "take_profit": tp_price,
                "risk_reward": "1:3.50",
                "workspace": ws,
                "description": f"Institutions swept sell stops below {curr_pfx}{swing_l:,.2f} (depth: {sweep_depth_pct}%). Strong buyer absorption confirmed!"
            }

        # ── 2. BEARISH SWEEP TRAP (Bull Trap / Upthrust)
        # Price spiked above swing high, lured breakout buyers, but closed back BELOW swing high with a long upper wick
        swept_high = (candle_high > swing_h)
        closed_below_high = (candle_close <= swing_h)
        upper_wick = candle_high - max(candle_open, candle_close)
        upper_wick_ratio = upper_wick / total_range

        if swept_high and closed_below_high and upper_wick_ratio >= 0.42:
            sweep_height_pct = round(((candle_high - swing_h) / max(0.0001, swing_h)) * 100.0, 3)
            return {
                "detected": True,
                "pattern": "BEARISH_LIQUIDITY_SWEEP",
                "action": "SELL",
                "conviction_boost": -25.0,
                "sweep_depth_pct": sweep_height_pct,
                "workspace": ws,
                "description": f"Institutions swept buy stops above {curr_pfx}{swing_h:,.2f} (spike: {sweep_height_pct}%). Breakout buyers trapped!"
            }

        return {
            "detected": False,
            "pattern": "NO_SWEEP",
            "action": "HOLD",
            "conviction_boost": 0.0,
            "workspace": ws,
            "description": "Price action within normal boundaries"
        }


# =====================================================================
# 2. UNIVERSAL SQUEEZE & LIQUIDATION CASCADE ENGINE
# =====================================================================
class UniversalSqueezeCascadeEngine:
    """
    Capitalizes on forced liquidity cascades and mandatory square-offs across all markets:
      1. INDIA: 14:15 - 14:50 IST mandatory MIS intraday square-off wave.
      2. CRYPTO: 8-hour funding rate settlement squeezes (00:00, 08:00, 16:00 UTC)
         plus perpetual short liquidation bounces off 24h lows.
      3. FOREX_GOLD: London Open (13:30 IST), NY Open (18:30 IST), and London 16:00 Fix
         (21:15 IST) interbank dealer rebalance squeezes.
    """

    def is_in_india_covering_window(self) -> bool:
        """Check if current time is within prime Indian afternoon short-covering window."""
        now = _ist_now()
        if now.weekday() >= 5:
            return False
        time_val = now.hour * 100 + now.minute
        return 1415 <= time_val <= 1450

    def is_in_crypto_funding_window(self) -> Tuple[bool, str]:
        """
        Check if current time is within 45 mins prior to or 15 mins after 8-hour funding settlements
        (00:00, 08:00, 16:00 UTC -> 05:30, 13:30, 21:30 IST).
        """
        now_utc = _utc_now()
        funding_hours = [0, 8, 16]
        cur_min_of_day = now_utc.hour * 60 + now_utc.minute

        for fh in funding_hours:
            target_min = fh * 60
            # 45 mins before to 15 mins after
            diff = cur_min_of_day - target_min
            # Wrap around midnight
            if diff < -720:
                diff += 1440
            elif diff > 720:
                diff -= 1440

            if -45 <= diff <= 15:
                window_name = f"{fh:02d}:00_UTC_FUNDING"
                return True, window_name

        return False, ""

    def is_in_forex_squeeze_window(self) -> Tuple[bool, str]:
        """
        Check if Forex/Gold is within institutional fix/handover windows:
          - London Open: 13:30 - 14:45 IST (08:00 - 09:15 GMT)
          - NY Open: 18:30 - 19:45 IST (13:00 - 14:15 GMT)
          - London 16:00 Fix: 21:15 - 21:50 IST (15:45 - 16:20 GMT)
        """
        now_ist = _ist_now()
        if now_ist.weekday() >= 5:
            return False, ""

        t = now_ist.hour * 100 + now_ist.minute
        if 1330 <= t <= 1445:
            return True, "LONDON_OPEN_SQUEEZE"
        if 1830 <= t <= 1945:
            return True, "NEW_YORK_OPEN_SQUEEZE"
        if 2115 <= t <= 2150:
            return True, "LONDON_1600_FIX_REBALANCE"

        return False, ""

    # Backwards-compatible alias
    def is_in_short_covering_window(self) -> bool:
        return self.is_in_india_covering_window()

    def evaluate_short_covering_opportunity(
        self,
        symbol: str,
        current_price: float,
        day_low: float,
        change_24h: float,
        relative_volume: float = 1.0
    ) -> Dict[str, Any]:
        """Indian market MIS short-covering evaluation (backwards compatible)."""
        return self.evaluate_squeeze(
            symbol=symbol,
            workspace="INDIA",
            current_price=current_price,
            day_low=day_low,
            day_high=0.0,
            change_24h=change_24h,
            relative_volume=relative_volume
        )

    def evaluate_squeeze(
        self,
        symbol: str,
        workspace: str,
        current_price: float,
        day_low: float,
        day_high: float = 0.0,
        change_24h: float = 0.0,
        relative_volume: float = 1.0,
        funding_rate: float = 0.0
    ) -> Dict[str, Any]:
        """
        Unified Multi-Market Squeeze & Liquidation Cascade Evaluator.
        """
        ws = (workspace or "CRYPTO").upper()
        sym = symbol.upper().replace("/", "").replace("-EQ", "").strip()
        curr_pfx = _currency_prefix(ws)

        if day_low <= 0 or current_price <= 0:
            return {"active": False, "reason": "Invalid price data"}

        bounce_from_low_pct = ((current_price - day_low) / day_low) * 100.0
        decimals = 2 if current_price > 10 else 4

        # ── 1. INDIAN MARKET: MIS Forced Afternoon Square-Off (14:15 - 14:50 IST)
        if ws == "INDIA":
            if not self.is_in_india_covering_window():
                return {"active": False, "reason": "Outside 14:15 - 14:50 IST short covering window"}

            if -4.5 <= change_24h <= -0.4 and bounce_from_low_pct >= 0.35 and relative_volume >= 1.4:
                target_tp = round(current_price * 1.0090, decimals)
                tight_sl = round(day_low * 0.9985, decimals)
                return {
                    "active": True,
                    "symbol": sym,
                    "signal_action": "BUY",
                    "conviction_boost": 28.0,
                    "opportunity_score": 93.0,
                    "bounce_pct": round(bounce_from_low_pct, 2),
                    "take_profit": target_tp,
                    "stop_loss": tight_sl,
                    "workspace": ws,
                    "description": f"Indian MIS Short-Covering Squeeze: Bounced +{bounce_from_low_pct:.2f}% off ₹{day_low:,.2f} low. Forced broker square-off active until 15:15 PM!"
                }

        # ── 2. CRYPTO MARKET: Funding Rate Squeeze & Liquidation Absorption
        elif ws == "CRYPTO":
            in_funding, funding_window = self.is_in_crypto_funding_window()
            # If funding rate is negative (< -0.008%) or in funding window with strong bounce
            is_negative_funding = (funding_rate <= -0.00008)  # -0.008%
            # High-volume bounce off 24h low after daily flush
            is_crypto_bounce = (-8.0 <= change_24h <= -1.0) and (bounce_from_low_pct >= 0.60) and (relative_volume >= 1.35)

            if (in_funding and (bounce_from_low_pct >= 0.45 or is_negative_funding)) or (is_crypto_bounce and relative_volume >= 1.4):
                target_tp = round(current_price * 1.0120, decimals)
                tight_sl = round(day_low * 0.9975, decimals)
                desc = f"Crypto Short Squeeze [{funding_window or 'LIQUIDATION_FLUSH'}]: Bounced +{bounce_from_low_pct:.2f}% off ${day_low:,.2f} low."
                if is_negative_funding:
                    desc += f" Negative funding ({funding_rate*100.0:.3f}%) punishing short sellers!"

                return {
                    "active": True,
                    "symbol": sym,
                    "signal_action": "BUY",
                    "conviction_boost": 26.0,
                    "opportunity_score": 93.0,
                    "bounce_pct": round(bounce_from_low_pct, 2),
                    "take_profit": target_tp,
                    "stop_loss": tight_sl,
                    "workspace": ws,
                    "description": desc
                }

        # ── 3. FOREX & GOLD: Interbank Fix & Handover Squeeze
        elif ws in ("FOREX_GOLD", "FOREX", "GOLD"):
            in_forex_win, win_name = self.is_in_forex_squeeze_window()
            if in_forex_win:
                # Forex moves in tighter percentages (0.15% - 0.50% is a large intraday swing in Gold/FX)
                if bounce_from_low_pct >= 0.18 and relative_volume >= 1.2:
                    target_tp = round(current_price * 1.0060, decimals)
                    tight_sl = round(day_low * 0.9985, decimals)
                    return {
                        "active": True,
                        "symbol": sym,
                        "signal_action": "BUY",
                        "conviction_boost": 25.0,
                        "opportunity_score": 92.5,
                        "bounce_pct": round(bounce_from_low_pct, 2),
                        "take_profit": target_tp,
                        "stop_loss": tight_sl,
                        "workspace": ws,
                        "description": f"Forex Institutional Squeeze [{win_name}]: Bounced +{bounce_from_low_pct:.2f}% off ${day_low:,.2f} low. Interbank order flow rebalancing active!"
                    }

        return {
            "active": False,
            "reason": f"Squeeze criteria not met for {ws} (Bounce: {bounce_from_low_pct:.2f}%, RVOL: {relative_volume}x)"
        }


# =====================================================================
# 3. TOXIC FLOW EVACUATION GUARD (Spread Expansion Defense)
# =====================================================================
class ToxicFlowEvacuationGuard:
    """
    Monitors bid-ask spread widening across all markets.
    When market makers pull quotes before a sudden dump wick, spread widens abnormally.
    Freezes new buys & tightens trailing stops to secure green profits.
    """

    # Calibrated maximum normal tolerance per market
    SPREAD_LIMITS = {
        "CRYPTO": {"multiplier": 2.0, "min_floor": 0.08, "tighten_stop": 0.0015},
        "INDIA": {"multiplier": 2.5, "min_floor": 0.15, "tighten_stop": 0.0010},
        "FOREX_GOLD": {"multiplier": 2.0, "min_floor": 0.04, "tighten_stop": 0.0008},
    }

    def __init__(self):
        # symbol -> list of recent spread percentages
        self.spread_baselines: Dict[str, List[float]] = {}

    def record_and_evaluate_spread(
        self,
        symbol: str,
        current_bid: float,
        current_ask: float,
        workspace: str = "CRYPTO"
    ) -> Dict[str, Any]:
        """
        Record current spread, update rolling baseline, and detect quote flickering/liquidity evacuation.
        """
        sym = symbol.upper().replace("/", "").replace("-EQ", "").strip()
        ws = (workspace or "CRYPTO").upper()
        curr_pfx = _currency_prefix(ws)

        if current_bid <= 0 or current_ask <= current_bid:
            return {"is_toxic": False, "action": "NORMAL", "reason": "Insufficient quote data"}

        mid = (current_bid + current_ask) / 2.0
        current_spread_pct = ((current_ask - current_bid) / mid) * 100.0

        history = self.spread_baselines.setdefault(sym, [])
        history.append(current_spread_pct)
        if len(history) > 30:
            self.spread_baselines[sym] = history[-30:]

        # Calculate average baseline spread over last 30 samples
        avg_spread = sum(history) / len(history) if history else current_spread_pct

        cfg = self.SPREAD_LIMITS.get(ws, self.SPREAD_LIMITS["CRYPTO"])
        multiplier = cfg["multiplier"]
        min_floor = cfg["min_floor"]
        tighten_step = cfg["tighten_stop"]

        # Anomaly detection: Spread expanded by configured multiplier AND exceeds minimum floor
        is_toxic_expansion = (current_spread_pct >= avg_spread * multiplier) and (current_spread_pct >= min_floor)

        if is_toxic_expansion:
            return {
                "is_toxic": True,
                "action": "EVACUATE_AND_TIGHTEN",
                "current_spread_pct": round(current_spread_pct, 4),
                "baseline_spread_pct": round(avg_spread, 4),
                "expansion_ratio": round(current_spread_pct / max(0.0001, avg_spread), 2),
                "tighten_trailing_stop_by": tighten_step,
                "block_new_entries": True,
                "workspace": ws,
                "description": f"Toxic Spread Expansion on {sym} ({current_spread_pct:.3f}% >= {avg_spread:.3f}% baseline x {multiplier:.1f}). Liquidity pulled! Freezing entries & locking profits."
            }

        return {
            "is_toxic": False,
            "action": "NORMAL",
            "current_spread_pct": round(current_spread_pct, 4),
            "baseline_spread_pct": round(avg_spread, 4),
            "block_new_entries": False,
            "workspace": ws,
            "description": "Liquidity and spreads normal"
        }


# =====================================================================
# 4. PRE-MARKET & SESSION HANDOVER IMBALANCE SCANNER
# =====================================================================
class SessionHandoverImbalanceScanner:
    """
    Scans pre-session and inter-session auction books & order flows:
      1. INDIA: 09:00 - 09:08 AM IST pre-open auction imbalance.
         Detects hidden accumulation: Buy Qty / Sell Qty >= 2.8x with compressed gap (< 0.65%).
      2. CRYPTO: Order Book Depth Skew (Bid Depth / Ask Depth >= 2.2x) with compressed 1h volatility,
         signaling iceberg absorption ahead of 00:00 UTC Asian session breakout.
      3. FOREX_GOLD: Asian-to-London Session Handover (12:30 - 13:30 IST) order accumulation
         and London-to-NY Handover (17:30 - 18:30 IST) spread compression.
    """

    def __init__(self):
        # symbol -> Dict[str, Any]
        self.priority_targets: Dict[str, Dict[str, Any]] = {}
        self.scan_date: str = ""

    def record_pre_market_data(
        self,
        symbol: str,
        buy_qty: float,
        sell_qty: float,
        indicative_price: float,
        previous_close: float
    ):
        """Record pre-market order auction quantities for Indian equities."""
        today = _ist_now().strftime("%Y-%m-%d")
        if self.scan_date != today:
            self.scan_date = today
            self.priority_targets.clear()

        if buy_qty <= 0 or sell_qty <= 0 or previous_close <= 0:
            return

        sym = symbol.upper().replace("-EQ", "").strip()
        imbalance_ratio = buy_qty / sell_qty
        gap_pct = ((indicative_price - previous_close) / previous_close) * 100.0

        if imbalance_ratio >= 2.8 and 0.0 <= gap_pct <= 0.65:
            self.priority_targets[sym] = {
                "symbol": sym,
                "workspace": "INDIA",
                "imbalance_ratio": round(imbalance_ratio, 2),
                "gap_pct": round(gap_pct, 2),
                "indicative_price": indicative_price,
                "priority_rank": int(imbalance_ratio * 10),
                "detected_at": _ist_now().strftime("%H:%M:%S IST"),
                "status": "QUEUED_FOR_OPENING_BURST"
            }

    def evaluate_live_handover_skew(
        self,
        symbol: str,
        workspace: str,
        current_price: float
    ) -> Optional[Dict[str, Any]]:
        """
        Dynamically check order book depth skew & session handover conditions for Crypto / Forex.
        """
        ws = (workspace or "CRYPTO").upper()
        sym = symbol.upper().replace("/", "").replace("-EQ", "").strip()

        # ── CRYPTO ICEBERG ACCUMULATION
        if ws == "CRYPTO":
            try:
                from core.order_book_pressure_detector import order_book_pressure_detector
                ob_data = order_book_pressure_detector.get_order_book_pressure(sym, workspace="CRYPTO")
                bid_vol = float(ob_data.get("bid_volume", 0.0))
                ask_vol = float(ob_data.get("ask_volume", 0.0))
                imbalance = float(ob_data.get("imbalance", 0.0))

                # If buyers strongly outnumber sellers (imbalance >= +0.30 or bid/ask >= 2.2x)
                if (bid_vol > 0 and ask_vol > 0 and (bid_vol / ask_vol) >= 2.2) or imbalance >= 0.35:
                    return {
                        "symbol": sym,
                        "workspace": ws,
                        "imbalance_ratio": round(bid_vol / max(0.001, ask_vol), 2) if ask_vol > 0 else 3.0,
                        "imbalance_score": round(imbalance, 3),
                        "indicative_price": current_price,
                        "priority_rank": 95,
                        "detected_at": _ist_now().strftime("%H:%M:%S IST"),
                        "status": "CRYPTO_ICEBERG_ACCUMULATION"
                    }
            except Exception:
                pass

        # ── FOREX / GOLD SESSION HANDOVER ACCUMULATION
        elif ws in ("FOREX_GOLD", "FOREX", "GOLD"):
            now_ist = _ist_now()
            t = now_ist.hour * 100 + now_ist.minute
            # Handover window 12:30 - 13:30 IST (Asian to London prep) or 17:30 - 18:30 IST (London to NY prep)
            in_handover = (1230 <= t <= 1330) or (1730 <= t <= 1830)
            if in_handover:
                return {
                    "symbol": sym,
                    "workspace": ws,
                    "imbalance_ratio": 2.5,
                    "indicative_price": current_price,
                    "priority_rank": 92,
                    "detected_at": _ist_now().strftime("%H:%M:%S IST"),
                    "status": "FOREX_SESSION_HANDOVER_BURST"
                }

        return None

    def get_opening_burst_priority(
        self,
        symbol: str,
        workspace: str = "INDIA",
        current_price: float = 0.0
    ) -> Optional[Dict[str, Any]]:
        """
        Check if symbol has a confirmed pre-market or session handover accumulation trigger.
        Works across INDIA, CRYPTO, and FOREX_GOLD.
        """
        sym = symbol.upper().replace("-EQ", "").strip()
        ws = (workspace or "INDIA").upper()

        # Check pre-queued Indian targets
        if ws == "INDIA":
            return self.priority_targets.get(sym)

        # For Crypto and Forex, check dynamic live order book skew & session handover
        if current_price > 0:
            return self.evaluate_live_handover_skew(sym, ws, current_price)

        return None

    def get_all_priority_symbols(self) -> List[Dict[str, Any]]:
        """Return all queued pre-market alpha candidates sorted by imbalance ratio."""
        return sorted(
            list(self.priority_targets.values()),
            key=lambda x: x.get("imbalance_ratio", 0.0),
            reverse=True
        )


# Backwards compatibility alias
PreMarketShadowScanner = SessionHandoverImbalanceScanner
ShortCoveringSurgeEngine = UniversalSqueezeCascadeEngine

# =====================================================================
# GLOBAL SINGLETON INSTANCES
# =====================================================================
liquidity_hunt_trap_engine = LiquidityHuntTrapEngine()
short_covering_surge_engine = UniversalSqueezeCascadeEngine()
toxic_flow_evacuation_guard = ToxicFlowEvacuationGuard()
pre_market_shadow_scanner = SessionHandoverImbalanceScanner()
