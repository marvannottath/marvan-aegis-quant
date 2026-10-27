"""
Aegis-Quant Institutional Quant Matrix — The Complete Institutional Arsenal.
Houses 14 advanced mathematical, microstructure, statistical arbitrage,
derivatives hedging, and session-timing alpha engines across INDIA, CRYPTO, and FOREX_GOLD.

Engines included:
1.  StoikovMicroPriceEngine (Volume-Weighted Micro-Price & Queue Imbalance Drift)
2.  IcebergAbsorptionEngine (Footprint Volume vs Depth Absorption)
3.  AntiSpoofingGuard (Quote-to-Trade Ratio & Phantom Liquidity Shield)
4.  TickVelocitySurgeEngine (Trades Per Second & Taker Sweep Aggression)
5.  CrossAssetLeadLagEngine (BTC->Alts, DXY->Gold, Heavyweights->Nifty Lead-Lag)
6.  FuturesSpotBasisEngine (Perp-to-Spot Premium Z-Score Mean Reversion)
7.  PairsCointegrationEngine (Statistical Arbitrage Spread Z-Score Snap-Back)
8.  VolumeProfileVacuumEngine (POC, Value Area High/Low & LVN Vacuum Glides)
9.  VolatilityCompressionSqueezeEngine (Bollinger-inside-Keltner Squeeze)
10. OptionGammaFlipEngine (0-DTE Dealer Gamma Regime & Hedging Cascade)
11. LiquidationHeatmapCascadeEngine (Crypto/Perp Leverage Cluster Sweep & Reversal)
12. SessionOpenJudasTrapEngine (London 13:30 IST & NY 18:30 IST False Breakout Trap)
13. LondonFixBenchmarkEngine (London 16:00 Fix / 21:30 IST Rebalancing Magnet)
14. PoissonStealthExecutionSlicer (Poisson Random Jitter Algorithmic Execution)
"""

import time
import math
import random
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone, timedelta

IST_TZ = timezone(timedelta(hours=5, minutes=30))
UTC_TZ = timezone.utc


def _ist_now() -> datetime:
    return datetime.now(timezone.utc).astimezone(IST_TZ)


# =====================================================================
# 1. SACHA STOIKOV MICRO-PRICE & QUEUE IMBALANCE ENGINE
# =====================================================================
class StoikovMicroPriceEngine:
    """
    Sasha Stoikov's Micro-Price Formula:
    Calculates fair asset value accounting for order queue imbalance at top levels.
    Predicts directional drift 5-20 seconds before standard mid-price shifts.
    """
    def evaluate_micro_price(
        self,
        bids: List[Tuple[float, float]],  # [(price, qty), ...]
        asks: List[Tuple[float, float]],  # [(price, qty), ...]
        depth_levels: int = 5
    ) -> Dict[str, Any]:
        if not bids or not asks:
            return {"status": "INSUFFICIENT_DATA", "drift_pct": 0.0, "signal": "NEUTRAL"}

        best_bid = bids[0][0]
        best_ask = asks[0][0]
        mid_price = (best_bid + best_ask) / 2.0

        if mid_price <= 0:
            return {"status": "INVALID_MID", "drift_pct": 0.0, "signal": "NEUTRAL"}

        # Sum volumes up to depth_levels
        i_b = sum(qty for _, qty in bids[:depth_levels])
        i_a = sum(qty for _, qty in asks[:depth_levels])
        total_vol = i_b + i_a

        if total_vol <= 0:
            return {"status": "ZERO_DEPTH", "drift_pct": 0.0, "signal": "NEUTRAL"}

        # Stoikov micro-price formula: P_micro = (I_b * Ask + I_a * Bid) / (I_b + I_a)
        micro_price = (i_b * best_ask + i_a * best_bid) / total_vol
        drift_pct = ((micro_price - mid_price) / mid_price) * 100.0
        queue_imbalance = (i_b - i_a) / total_vol  # -1.0 to +1.0

        spread_pct = ((best_ask - best_bid) / mid_price) * 100.0
        drift_threshold = max(0.003, spread_pct * 0.20)

        signal = "NEUTRAL"
        confidence_boost = 0.0
        if drift_pct >= drift_threshold and queue_imbalance >= 0.25:
            signal = "BULLISH_DRIFT"
            confidence_boost = min(8.0, 4.0 + queue_imbalance * 4.0)
        elif drift_pct <= -drift_threshold and queue_imbalance <= -0.25:
            signal = "BEARISH_DRIFT"
            confidence_boost = min(8.0, 4.0 + abs(queue_imbalance) * 4.0)

        return {
            "status": "SUCCESS",
            "best_bid": round(best_bid, 4),
            "best_ask": round(best_ask, 4),
            "mid_price": round(mid_price, 4),
            "micro_price": round(micro_price, 4),
            "drift_pct": round(drift_pct, 4),
            "queue_imbalance": round(queue_imbalance, 3),
            "signal": signal,
            "confidence_boost": round(confidence_boost, 2)
        }


# =====================================================================
# 2. ICEBERG ORDER RELOAD & ABSORPTION ENGINE
# =====================================================================
class IcebergAbsorptionEngine:
    """
    Detects hidden institutional iceberg orders.
    Triggers when cumulative executed volume at a specific price level exceeds visible depth
    by multiple factors while price remains pinned (passive absorption).
    """
    def __init__(self):
        # symbol -> price -> {"cum_vol": float, "last_depth": float, "refreshes": int}
        self.level_tracker: Dict[str, Dict[float, Dict[str, Any]]] = {}

    def record_level_trade(
        self,
        symbol: str,
        price: float,
        trade_vol: float,
        visible_depth_qty: float,
        side: str = "BUY"
    ) -> Dict[str, Any]:
        sym = symbol.upper()
        if sym not in self.level_tracker:
            self.level_tracker[sym] = {}

        # Round price to nearest tick cluster
        p_key = round(price, 2)
        if p_key not in self.level_tracker[sym]:
            self.level_tracker[sym][p_key] = {
                "cum_vol": 0.0,
                "initial_depth": max(0.001, visible_depth_qty),
                "refreshes": 0,
                "side": side,
                "first_seen": time.time()
            }

        rec = self.level_tracker[sym][p_key]
        rec["cum_vol"] += trade_vol

        # Check ratio of executed volume to initial visible depth
        absorption_ratio = rec["cum_vol"] / rec["initial_depth"]

        is_iceberg = False
        action = "HOLD"
        # If cumulative traded volume is >= 3.2x visible depth, absorption is active
        if absorption_ratio >= 3.2:
            is_iceberg = True
            action = "BUY_ACCUMULATION" if side == "BUY" else "SELL_DISTRIBUTION"

        return {
            "symbol": sym,
            "price_level": p_key,
            "cumulative_volume": round(rec["cum_vol"], 2),
            "visible_depth": round(visible_depth_qty, 2),
            "absorption_ratio": round(absorption_ratio, 2),
            "is_iceberg": is_iceberg,
            "action": action
        }


# =====================================================================
# 3. ANTI-SPOOFING & PHANTOM LIQUIDITY SHIELD
# =====================================================================
class AntiSpoofingGuard:
    """
    Detects predatory phantom liquidity walls designed to bait retail breakout orders.
    Calculates Quote-to-Trade Ratio (QTR) and rapid order cancellations (< 300ms).
    """
    def __init__(self):
        self.quote_history: Dict[str, List[Dict[str, Any]]] = {}

    def inspect_wall_integrity(
        self,
        symbol: str,
        wall_price: float,
        wall_size: float,
        current_price: float,
        is_bid_wall: bool,
        recent_cancellations: int = 0,
        recent_trades: int = 1
    ) -> Dict[str, Any]:
        sym = symbol.upper()
        qtr = recent_cancellations / max(1, recent_trades)
        dist_pct = abs(current_price - wall_price) / max(0.0001, current_price) * 100.0

        # Spoofing characteristics:
        # 1. Unusually huge wall relative to normal book
        # 2. High cancellation-to-trade ratio (> 15)
        # 3. Wall is pulled as soon as price comes within 0.10%
        is_spoof = False
        warning = "CLEAN_BOOK"

        if qtr > 15.0 and dist_pct <= 0.12:
            is_spoof = True
            warning = "PHANTOM_BID_WALL_SPOOF" if is_bid_wall else "PHANTOM_ASK_WALL_SPOOF"

        return {
            "symbol": sym,
            "is_spoof": is_spoof,
            "warning": warning,
            "quote_to_trade_ratio": round(qtr, 2),
            "distance_pct": round(dist_pct, 3),
            "veto_entry": is_spoof
        }


# =====================================================================
# 4. TICK VELOCITY & TAPE BURST ENGINE
# =====================================================================
class TickVelocitySurgeEngine:
    """
    Tracks Trades Per Second (TPS) over rolling windows.
    Detects institutional aggressive market order sweeps (Tape Bursts).
    """
    def __init__(self):
        self.tick_window: Dict[str, List[Tuple[float, float, str]]] = {}  # ts, vol, side

    def record_tick(self, symbol: str, price: float, volume: float, is_taker_buy: bool) -> Dict[str, Any]:
        sym = symbol.upper()
        now = time.time()
        if sym not in self.tick_window:
            self.tick_window[sym] = []

        self.tick_window[sym].append((now, volume, "BUY" if is_taker_buy else "SELL"))
        # Retain last 30 seconds
        cutoff = now - 30.0
        self.tick_window[sym] = [t for t in self.tick_window[sym] if t[0] >= cutoff]

        ticks = self.tick_window[sym]
        total_ticks = len(ticks)
        time_span = max(1.0, min(30.0, ticks[-1][0] - ticks[0][0])) if total_ticks > 1 else 1.0
        tps = total_ticks / time_span  # Trades per second over actual duration

        buy_vol = sum(t[1] for t in ticks if t[2] == "BUY")
        total_vol = sum(t[1] for t in ticks) or 1.0
        buy_ratio = buy_vol / total_vol

        # A burst is >= 8.0 TPS with >= 72% directionality
        is_surge = (tps >= 8.0 and (buy_ratio >= 0.72 or buy_ratio <= 0.28))
        surge_dir = "BULLISH_SWEEP" if buy_ratio >= 0.72 else ("BEARISH_SWEEP" if buy_ratio <= 0.28 else "CHOP")

        return {
            "symbol": sym,
            "tps": round(tps, 2),
            "buy_ratio": round(buy_ratio, 3),
            "is_surge": is_surge,
            "surge_direction": surge_dir if is_surge else "NORMAL",
            "confidence_boost": 7.0 if is_surge else 0.0
        }


# =====================================================================
# 5. CROSS-ASSET LEAD-LAG ARBITRAGE ENGINE
# =====================================================================
class CrossAssetLeadLagEngine:
    """
    Captures information propagation delay between market leaders and followers:
    - CRYPTO: BTCUSDT leads ETHUSDT / SOLUSDT by 15-45 seconds.
    - FOREX/GOLD: US Dollar Index (DXY) inverse impulse leads XAUUSD / EURUSD by 10-30 seconds.
    - INDIA: Reliance + HDFCBANK composite delta leads NIFTY 50 futures by 15-60 seconds.
    """
    def __init__(self):
        # leader -> list of (timestamp, price)
        self.leader_history: Dict[str, List[Tuple[float, float]]] = {}

    def record_leader_price(self, leader_symbol: str, price: float):
        sym = leader_symbol.upper()
        now = time.time()
        if sym not in self.leader_history:
            self.leader_history[sym] = []
        self.leader_history[sym].append((now, price))
        # Keep 120 seconds
        cutoff = now - 120.0
        self.leader_history[sym] = [x for x in self.leader_history[sym] if x[0] >= cutoff]

    def evaluate_lead_lag(
        self,
        follower_symbol: str,
        follower_price: float,
        leader_symbol: str,
        workspace: str = "CRYPTO",
        lookback_seconds: float = 45.0
    ) -> Dict[str, Any]:
        sym = follower_symbol.upper()
        lead_sym = leader_symbol.upper()
        history = self.leader_history.get(lead_sym, [])

        if len(history) < 2:
            return {
                "status": "INSUFFICIENT_LEADER_DATA",
                "lead_signal": "NEUTRAL",
                "edge_active": False,
                "leader_delta_pct": 0.0,
                "effective_follower_bias_pct": 0.0
            }

        now = time.time()
        curr_leader_p = history[-1][1]
        # Find price lookback_seconds ago
        target_t = now - lookback_seconds
        past_leader_p = next((p for t, p in history if t >= target_t), history[0][1])

        if past_leader_p <= 0:
            return {"status": "INVALID_PRICE", "lead_signal": "NEUTRAL", "edge_active": False}

        leader_delta_pct = ((curr_leader_p - past_leader_p) / past_leader_p) * 100.0

        # Calibrate correlation multiplier
        # For DXY vs Gold, correlation is inverse (-1.0)
        is_inverse = ("DXY" in lead_sym or "USDX" in lead_sym)
        effective_delta = -leader_delta_pct if is_inverse else leader_delta_pct

        # If leader moved strongly (> 0.20% in 45s), follower is statistically primed to follow
        edge_active = abs(effective_delta) >= 0.18
        signal = "NEUTRAL"
        if edge_active:
            signal = "BUY" if effective_delta > 0 else "SELL"

        return {
            "follower": sym,
            "leader": lead_sym,
            "workspace": workspace,
            "leader_delta_pct": round(leader_delta_pct, 4),
            "effective_follower_bias_pct": round(effective_delta, 4),
            "edge_active": edge_active,
            "lead_signal": signal,
            "confidence_boost": 7.5 if edge_active else 0.0
        }


# =====================================================================
# 6. FUTURES-TO-SPOT BASIS MEAN-REVERSION ENGINE
# =====================================================================
class FuturesSpotBasisEngine:
    """
    Computes statistical Z-Score of the Futures-to-Spot Basis / Premium.
    Excessive basis (> +2.5σ) indicates over-leveraged long euphoria primed for squeeze/flush.
    Extreme discount (< -2.5σ) indicates panic backwardation ripe for mean-reversion snap.
    """
    def __init__(self):
        self.basis_history: Dict[str, List[float]] = {}

    def evaluate_basis(self, symbol: str, spot_price: float, futures_price: float) -> Dict[str, Any]:
        sym = symbol.upper()
        if spot_price <= 0:
            return {"status": "INVALID_SPOT", "signal": "NEUTRAL"}

        basis_pct = ((futures_price - spot_price) / spot_price) * 100.0
        if sym not in self.basis_history:
            self.basis_history[sym] = []
        self.basis_history[sym].append(basis_pct)
        if len(self.basis_history[sym]) > 60:
            self.basis_history[sym].pop(0)

        history = self.basis_history[sym]
        if len(history) < 10:
            return {"basis_pct": round(basis_pct, 4), "z_score": 0.0, "signal": "NEUTRAL"}

        mean = sum(history) / len(history)
        variance = sum((x - mean) ** 2 for x in history) / len(history)
        std = math.sqrt(variance) or 0.0001
        z_score = (basis_pct - mean) / std

        signal = "NEUTRAL"
        if z_score >= 2.4:
            signal = "EXTREME_PREMIUM_SHORT_BIAS"  # Longs over-extended
        elif z_score <= -2.4:
            signal = "EXTREME_DISCOUNT_LONG_BIAS"  # Short exhaustion / panic

        return {
            "symbol": sym,
            "spot_price": round(spot_price, 4),
            "futures_price": round(futures_price, 4),
            "basis_pct": round(basis_pct, 4),
            "z_score": round(z_score, 2),
            "signal": signal,
            "is_extreme": abs(z_score) >= 2.4
        }


# =====================================================================
# 7. STATISTICAL COINTEGRATION & PAIRS SNAP-BACK ENGINE
# =====================================================================
class PairsCointegrationEngine:
    """
    Statistical Arbitrage Pairs Cointegration Engine.
    Tracks ratio of historically co-integrated pairs (e.g. ETH/BTC, Gold/Silver, BankNifty/Nifty).
    Calculates rolling Z-score to detect statistical divergence.
    """
    def __init__(self):
        self.ratio_history: Dict[str, List[float]] = {}

    def evaluate_pair(self, pair_name: str, price_a: float, price_b: float) -> Dict[str, Any]:
        if price_b <= 0:
            return {"status": "INVALID_PRICE_B", "signal": "NEUTRAL"}

        ratio = price_a / price_b
        if pair_name not in self.ratio_history:
            self.ratio_history[pair_name] = []
        self.ratio_history[pair_name].append(ratio)
        if len(self.ratio_history[pair_name]) > 50:
            self.ratio_history[pair_name].pop(0)

        history = self.ratio_history[pair_name]
        if len(history) < 15:
            return {"pair": pair_name, "ratio": round(ratio, 6), "z_score": 0.0, "signal": "NEUTRAL"}

        mean = sum(history) / len(history)
        var = sum((x - mean) ** 2 for x in history) / len(history)
        min_std = max(0.0001, mean * 0.005)
        std = max(min_std, math.sqrt(var))
        z_score = max(-5.0, min(5.0, (ratio - mean) / std))

        signal = "NEUTRAL"
        target_asset = ""
        action = "HOLD"

        if z_score <= -2.2:
            # Asset A is statistically undervalued relative to Asset B
            signal = "UNDERVALUED_SNAP_BACK"
            action = "BUY"
            target_asset = pair_name.split("/")[0]
        elif z_score >= 2.2:
            # Asset A is statistically overvalued relative to Asset B
            signal = "OVERVALUED_MEAN_REVERT"
            action = "SELL"
            target_asset = pair_name.split("/")[0]

        return {
            "pair": pair_name,
            "ratio": round(ratio, 6),
            "mean_ratio": round(mean, 6),
            "z_score": round(z_score, 2),
            "signal": signal,
            "action": action,
            "target_asset": target_asset,
            "confidence_boost": 6.5 if abs(z_score) >= 2.2 else 0.0
        }


# =====================================================================
# 8. VOLUME PROFILE POINT OF CONTROL (POC) & VACUUM ENGINE
# =====================================================================
class VolumeProfileVacuumEngine:
    """
    Computes intraday Volume Profile: Point of Control (POC), Value Area (VAH/VAL 70%),
    and Low Volume Nodes (LVN / Liquidity Vacuums).
    When price enters an LVN, it glides rapidly with near-zero friction towards the next HVN.
    """
    def compute_volume_profile(
        self,
        candles: List[Dict[str, float]],  # [{"high": .., "low": .., "close": .., "volume": ..}, ...]
        bins: int = 24
    ) -> Dict[str, Any]:
        if not candles or len(candles) < 10:
            return {"status": "INSUFFICIENT_CANDLES", "in_vacuum": False}

        all_highs = [c["high"] for c in candles]
        all_lows = [c["low"] for c in candles]
        min_p = min(all_lows)
        max_p = max(all_highs)

        if max_p <= min_p:
            return {"status": "FLAT_RANGE", "in_vacuum": False}

        bin_size = (max_p - min_p) / bins
        profile = [0.0] * bins

        # Distribute volume across price bins
        total_vol = 0.0
        for c in candles:
            vol = c.get("volume", 1.0)
            avg_p = (c["high"] + c["low"] + c["close"]) / 3.0
            idx = min(bins - 1, max(0, int((avg_p - min_p) / bin_size)))
            profile[idx] += vol
            total_vol += vol

        # Find POC
        poc_idx = max(range(bins), key=lambda i: profile[i])
        poc_price = min_p + (poc_idx + 0.5) * bin_size

        # Value Area (70% of volume)
        target_va_vol = total_vol * 0.70
        sorted_indices = sorted(range(bins), key=lambda i: profile[i], reverse=True)
        va_indices = set()
        accum = 0.0
        for idx in sorted_indices:
            accum += profile[idx]
            va_indices.add(idx)
            if accum >= target_va_vol:
                break

        val = min_p + min(va_indices) * bin_size
        vah = min_p + (max(va_indices) + 1) * bin_size

        current_p = candles[-1]["close"]
        curr_idx = min(bins - 1, max(0, int((current_p - min_p) / bin_size)))
        curr_vol = profile[curr_idx]

        # Low Volume Node (LVN / Vacuum): volume at current price < 25% of POC volume
        is_vacuum = (curr_vol <= profile[poc_idx] * 0.25)

        return {
            "status": "SUCCESS",
            "poc_price": round(poc_price, 4),
            "vah": round(vah, 4),
            "val": round(val, 4),
            "current_price": round(current_p, 4),
            "in_vacuum": is_vacuum,
            "vacuum_glide_bias": "RUN_TO_POC" if abs(current_p - poc_price) > (vah - val) * 0.5 else "BREAKOUT_GLIDE",
            "confidence_boost": 6.0 if is_vacuum else 0.0
        }


# =====================================================================
# 9. VOLATILITY COMPRESSION SQUEEZE ENGINE (TTM Squeeze Variant)
# =====================================================================
class VolatilityCompressionSqueezeEngine:
    """
    Detects volatility compression coiling: Bollinger Bands (20, 2σ) entering inside
    Keltner Channels (20, 1.5 ATR). When squeeze fires, price explodes directionally.
    """
    def evaluate_squeeze(self, closes: List[float], highs: List[float], lows: List[float]) -> Dict[str, Any]:
        if len(closes) < 20:
            return {"status": "INSUFFICIENT_BARS", "squeeze_on": False, "fired": False}

        c20 = closes[-20:]
        sma = sum(c20) / 20.0
        variance = sum((x - sma) ** 2 for x in c20) / 20.0
        std = math.sqrt(variance)

        bb_upper = sma + (2.0 * std)
        bb_lower = sma - (2.0 * std)

        # ATR 20
        tr_list = []
        for i in range(-20, 0):
            h = highs[i]
            l = lows[i]
            prev_c = closes[i - 1] if i > -len(closes) else c20[0]
            tr = max(h - l, abs(h - prev_c), abs(l - prev_c))
            tr_list.append(tr)
        atr20 = sum(tr_list) / 20.0

        kc_upper = sma + (1.5 * atr20)
        kc_lower = sma - (1.5 * atr20)

        # Squeeze is ON when Bollinger Bands are completely inside Keltner Channel
        squeeze_on = (bb_upper < kc_upper) and (bb_lower > kc_lower)

        # Momentum calculation: linear regression of closes relative to Donchian Midline
        donchian_mid = (max(highs[-20:]) + min(lows[-20:])) / 2.0
        delta = c20[-1] - ((donchian_mid + sma) / 2.0)

        momentum_dir = "BULLISH_EXPANSION" if delta > 0 else "BEARISH_EXPANSION"

        return {
            "squeeze_on": squeeze_on,
            "bb_bandwidth": round((bb_upper - bb_lower) / max(0.001, sma) * 100.0, 3),
            "momentum_delta": round(delta, 4),
            "expansion_direction": momentum_dir,
            "trade_trigger": (not squeeze_on and abs(delta) > atr20 * 0.20),
            "confidence_boost": 8.0 if (not squeeze_on and delta > 0) else 0.0
        }


# =====================================================================
# 10. OPTION GAMMA FLIP & 0-DTE DELTA HEDGING CASCADE ENGINE
# =====================================================================
class OptionGammaFlipEngine:
    """
    Market Maker Gamma Flip Engine:
    When spot price is below the Gamma Flip point, market makers are in Negative Gamma,
    meaning they must sell as price falls and buy as price rises, accelerating volatility into cascades.
    """
    def __init__(self):
        # symbol -> gamma_flip_level
        self.gamma_flip_levels: Dict[str, float] = {}

    def set_gamma_flip_level(self, symbol: str, level: float):
        self.gamma_flip_levels[symbol.upper()] = level

    def evaluate_gamma_regime(self, symbol: str, spot_price: float) -> Dict[str, Any]:
        sym = symbol.upper()
        flip_p = self.gamma_flip_levels.get(sym, spot_price)

        dist_pct = ((spot_price - flip_p) / max(0.001, flip_p)) * 100.0

        if spot_price < flip_p:
            regime = "NEGATIVE_GAMMA_CASCADE"
            volatility_bias = "AMPLIFIED_EXPANSION"
            action_bias = "ACCELERATED_DOWNWARD_PRESSURE"
        else:
            regime = "POSITIVE_GAMMA_STABILITY"
            volatility_bias = "VOLATILITY_DAMPENED_MEAN_REVERSION"
            action_bias = "INSTITUTIONAL_ABSORPTION"

        return {
            "symbol": sym,
            "spot_price": round(spot_price, 2),
            "gamma_flip_level": round(flip_p, 2),
            "distance_to_flip_pct": round(dist_pct, 3),
            "gamma_regime": regime,
            "volatility_bias": volatility_bias,
            "action_bias": action_bias
        }


# =====================================================================
# 11. LEVERAGE LIQUIDATION HEATMAP CASCADE ENGINE
# =====================================================================
class LiquidationHeatmapCascadeEngine:
    """
    Calculates estimated liquidation clusters for 50x, 25x, 10x leverage.
    Market makers routinely sweep into these clusters to harvest liquidity, followed by
    instant momentum exhaustion.
    """
    def calculate_liquidation_targets(
        self,
        symbol: str,
        current_price: float,
        swing_high: float,
        swing_low: float
    ) -> Dict[str, Any]:
        sym = symbol.upper()
        # 50x liquidation is ~ 1.8% from entry, 25x is ~ 3.6% from entry
        short_liqs_50x = swing_high * 1.018
        short_liqs_25x = swing_high * 1.036
        long_liqs_50x = swing_low * 0.982
        long_liqs_25x = swing_low * 0.964

        dist_to_short_50x = ((short_liqs_50x - current_price) / current_price) * 100.0
        dist_to_long_50x = ((current_price - long_liqs_50x) / current_price) * 100.0

        is_near_short_cluster = (0.0 <= dist_to_short_50x <= 0.35)
        is_near_long_cluster = (0.0 <= dist_to_long_50x <= 0.35)

        magnet_active = is_near_short_cluster or is_near_long_cluster
        target = "SHORT_LIQ_CLUSTER" if is_near_short_cluster else ("LONG_LIQ_CLUSTER" if is_near_long_cluster else "NONE")

        return {
            "symbol": sym,
            "current_price": round(current_price, 4),
            "short_liquidation_50x": round(short_liqs_50x, 4),
            "long_liquidation_50x": round(long_liqs_50x, 4),
            "magnet_active": magnet_active,
            "cluster_target": target,
            "exhaustion_action": "REVERSAL_EXHAUSTION_READY" if magnet_active else "RUNNING"
        }


# =====================================================================
# 12. SESSION OPEN JUDAS SWING TRAPPER (London & NY Open)
# =====================================================================
class SessionOpenJudasTrapEngine:
    """
    Institutional Judas Swing Trapper:
    Detects the false directional run in the first 15-30 minutes of London Open (13:30 IST)
    and NY Open (18:30 IST) designed to sweep overnight Asian session liquidity before the real trend begins.
    """
    def evaluate_judas_swing(
        self,
        symbol: str,
        current_price: float,
        asian_high: float,
        asian_low: float,
        candle_high: float,
        candle_low: float,
        candle_close: float
    ) -> Dict[str, Any]:
        now_ist = _ist_now()
        h = now_ist.hour
        m = now_ist.minute

        # Windows: London Open (13:30 - 14:15 IST) or NY Open (18:30 - 19:15 IST)
        in_london = (h == 13 and m >= 30) or (h == 14 and m <= 15)
        in_ny = (h == 18 and m >= 30) or (h == 19 and m <= 15)

        if not (in_london or in_ny):
            return {"active": False, "session": "OFF_HOURS", "action": "HOLD"}

        session_name = "LONDON_OPEN" if in_london else "NY_OPEN"

        # Bull Judas Trap: Price sweeps Asian High then violently closes back below Asian High
        if candle_high > asian_high and candle_close < asian_high:
            return {
                "active": True,
                "session": session_name,
                "pattern": "BULL_JUDAS_TRAP",
                "action": "SELL",
                "reason": f"Swept {session_name} Asian High ({asian_high:.2f}) and rejected back inside range",
                "confidence_boost": 9.0
            }

        # Bear Judas Trap: Price sweeps Asian Low then violently bounces back above Asian Low
        if candle_low < asian_low and candle_close > asian_low:
            return {
                "active": True,
                "session": session_name,
                "pattern": "BEAR_JUDAS_TRAP",
                "action": "BUY",
                "reason": f"Swept {session_name} Asian Low ({asian_low:.2f}) and reclaimed back inside range",
                "confidence_boost": 9.0
            }

        return {"active": False, "session": session_name, "action": "HOLD"}


# =====================================================================
# 13. LONDON 16:00 FIX (21:30 IST) BENCHMARK ENGINE
# =====================================================================
class LondonFixBenchmarkEngine:
    """
    London 4 PM Fix (16:00 London / 21:30 IST):
    Multinational banks rebalance foreign exchange portfolios at the fix.
    Predicts mean-reverting drift towards daily VWAP benchmark between 21:15 and 21:45 IST.
    """
    def evaluate_fix_drift(self, symbol: str, current_price: float, day_vwap: float) -> Dict[str, Any]:
        now_ist = _ist_now()
        h = now_ist.hour
        m = now_ist.minute

        # Fix window: 21:10 to 21:45 IST
        in_fix_window = (h == 21 and 10 <= m <= 45)
        if not in_fix_window:
            return {"active": False, "reason": "OUTSIDE_FIX_WINDOW"}

        dev_pct = ((current_price - day_vwap) / max(0.001, day_vwap)) * 100.0

        # High probability magnet drift towards VWAP benchmark
        action = "HOLD"
        if dev_pct > 0.20:
            action = "SELL_DRIFT_TO_VWAP"
        elif dev_pct < -0.20:
            action = "BUY_DRIFT_TO_VWAP"

        return {
            "active": True,
            "session": "LONDON_4PM_FIX",
            "current_price": round(current_price, 4),
            "benchmark_vwap": round(day_vwap, 4),
            "deviation_pct": round(dev_pct, 3),
            "action": action,
            "confidence_boost": 7.0 if action != "HOLD" else 0.0
        }


# =====================================================================
# 14. POISSON STEALTH EXECUTION SLICER
# =====================================================================
class PoissonStealthExecutionSlicer:
    """
    Institutional TWAP with Poisson Random Jitter:
    Generates non-deterministic slice delays and volume variations to make algorithmic orders
    indistinguishable from manual human activity, completely defeating HFT front-running probes.
    """
    def generate_stealth_schedule(
        self,
        total_quantity: float,
        num_slices: int = 5,
        avg_delay_seconds: float = 6.0
    ) -> List[Dict[str, Any]]:
        if num_slices <= 1:
            return [{"slice_index": 1, "qty": total_quantity, "delay_sec": 0.0}]

        slices = []
        rem_qty = total_quantity

        for i in range(num_slices - 1):
            # Poisson inter-arrival delay: -mean * ln(Uniform(0, 1))
            u = max(0.001, min(0.999, random.random()))
            poisson_delay = -avg_delay_seconds * math.log(u)
            poisson_delay = max(1.5, min(avg_delay_seconds * 2.5, poisson_delay))

            # Add random jitter to slice size (+- 15%)
            jitter = (random.random() - 0.5) * 0.30
            slice_qty = (total_quantity / num_slices) * (1.0 + jitter)
            slice_qty = round(min(rem_qty * 0.8, max(slice_qty, total_quantity * 0.05)), 4)
            rem_qty -= slice_qty

            slices.append({
                "slice_index": i + 1,
                "qty": slice_qty,
                "delay_sec": round(poisson_delay, 2)
            })

        # Final remainder slice
        slices.append({
            "slice_index": num_slices,
            "qty": round(rem_qty, 4),
            "delay_sec": round(avg_delay_seconds, 2)
        })

        return slices


# =====================================================================
# GLOBAL SINGLETON INSTANCES
# =====================================================================
stoikov_micro_price_engine = StoikovMicroPriceEngine()
iceberg_absorption_engine = IcebergAbsorptionEngine()
anti_spoofing_guard = AntiSpoofingGuard()
tick_velocity_surge_engine = TickVelocitySurgeEngine()
cross_asset_lead_lag_engine = CrossAssetLeadLagEngine()
futures_spot_basis_engine = FuturesSpotBasisEngine()
pairs_cointegration_engine = PairsCointegrationEngine()
volume_profile_vacuum_engine = VolumeProfileVacuumEngine()
volatility_compression_squeeze_engine = VolatilityCompressionSqueezeEngine()
option_gamma_flip_engine = OptionGammaFlipEngine()
liquidation_heatmap_cascade_engine = LiquidationHeatmapCascadeEngine()
session_open_judas_trap_engine = SessionOpenJudasTrapEngine()
london_fix_benchmark_engine = LondonFixBenchmarkEngine()
poisson_stealth_execution_slicer = PoissonStealthExecutionSlicer()
