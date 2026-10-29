"""
Dynamic Momentum Runner Lock Engine.
Enables laser-focused single-asset trading on the highest-momentum asset in the market.
Continuously monitors price velocity and volatility:
- Automatically selects and locks onto the top-momentum stock.
- Holds and repeatedly trades that single asset while momentum persists.
- If price movement becomes stagnant for >= 15 minutes, automatically unlocks and
  shifts the lock to the new highest-momentum asset in the market.
"""

import os
import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta

IST_TZ = timezone(timedelta(hours=5, minutes=30))
LOCK_STATE_FILE = Path(__file__).resolve().parent.parent / "data" / "momentum_lock_state.json"


def _now_str() -> str:
    return datetime.now(timezone.utc).astimezone(IST_TZ).strftime("%Y-%m-%d %H:%M:%S IST")


class DynamicMomentumLock:
    def __init__(self):
        self.state_file = LOCK_STATE_FILE
        self._symbol_cooldowns: Dict[str, float] = {}  # symbol -> epoch ts until which symbol cannot be picked
        self._states: Dict[str, Dict[str, Any]] = {
            "INDIA": {
                "enabled": False,
                "locked_symbol": None,
                "locked_at": None,
                "locked_price": 0.0,
                "momentum_score": 0.0,
                "stagnant_since": None,
                "stagnant_minutes": 0.0,
                "stagnant_threshold_minutes": 10,
                "last_price": 0.0,
                "price_history": [],
                "switch_reason": "",
                "rotation_count": 0
            },
            "CRYPTO": {
                "enabled": False,
                "locked_symbol": None,
                "locked_at": None,
                "locked_price": 0.0,
                "momentum_score": 0.0,
                "stagnant_since": None,
                "stagnant_minutes": 0.0,
                "stagnant_threshold_minutes": 10,
                "last_price": 0.0,
                "price_history": [],
                "switch_reason": "",
                "rotation_count": 0
            },
            "FOREX_GOLD": {
                "enabled": False,
                "locked_symbol": None,
                "locked_at": None,
                "locked_price": 0.0,
                "momentum_score": 0.0,
                "stagnant_since": None,
                "stagnant_minutes": 0.0,
                "stagnant_threshold_minutes": 10,
                "last_price": 0.0,
                "price_history": [],
                "switch_reason": "",
                "rotation_count": 0
            }
        }
        self._load_state()

    def _load_state(self):
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        if self.state_file.exists():
            try:
                with open(self.state_file, "r") as f:
                    data = json.load(f)
                    for k, v in data.items():
                        if k in self._states:
                            self._states[k].update(v)
            except Exception as e:
                print(f"[MOMENTUM LOCK] Load notice: {e}")

    def _save_state(self):
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.state_file.with_suffix(".tmp")
            with open(tmp, "w") as f:
                json.dump(self._states, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            tmp.replace(self.state_file)
        except Exception as e:
            try:
                with open(self.state_file, "w") as f:
                    json.dump(self._states, f, indent=2)
            except Exception as e2:
                print(f"[MOMENTUM LOCK] Save notice: {e2}")

    def is_active(self, workspace: str = "INDIA") -> bool:
        ws = workspace.upper()
        return bool(self._states.get(ws, {}).get("enabled", False))

    def allows_symbol(self, symbol: str, workspace: str = "INDIA") -> bool:
        """
        Returns True if symbol is allowed to be traded.
        If momentum lock is disabled, all symbols are allowed unless in symbol penalty cooldown.
        If active, ONLY the locked_symbol is allowed, provided it is not in penalty cooldown.
        """
        if not symbol:
            return False
        sym_upper = str(symbol).upper()
        if time.time() < self._symbol_cooldowns.get(sym_upper, 0.0):
            return False  # In penalty/stagnation cooldown

        ws = workspace.upper()
        state = self._states.get(ws, {})
        if not state.get("enabled", False):
            return True
        locked = state.get("locked_symbol")
        if not locked:
            return True
        if sym_upper == str(locked).upper():
            return True
        # Strict single-runner focus: do not leak into random non-locked stocks
        return False

    def demote_and_rotate(
        self,
        symbol: str,
        workspace: str = "INDIA",
        reason: str = "",
        cooldown_seconds: float = 1800.0
    ) -> bool:
        """
        Immediately demotes a failing, stagnant, or deteriorating symbol.
        Places it in a penalty cooldown (default 30 mins) so it cannot be rebought or relocked.
        If it was the currently locked symbol, clears the lock and triggers rotation to the next runner.
        """
        if not symbol:
            return False
        sym_upper = str(symbol).upper()
        self._symbol_cooldowns[sym_upper] = time.time() + cooldown_seconds

        ws = workspace.upper()
        state = self._states.get(ws)
        if not state:
            return False

        current_locked = state.get("locked_symbol")
        if current_locked and str(current_locked).upper() == sym_upper:
            state["locked_symbol"] = None
            state["locked_at"] = None
            state["stagnant_since"] = None
            state["stagnant_minutes"] = 0.0
            state["price_history"] = []
            state["rotation_count"] = state.get("rotation_count", 0) + 1
            state["switch_reason"] = f"DEMOTION: {sym_upper} ({reason}) -> Cooldown {cooldown_seconds/60:.0f}m"
            self._save_state()
            print(f"[MOMENTUM ROTATION] {state['switch_reason']}")
            return True
        return False

    def get_status(self, workspace: str = "INDIA") -> Dict[str, Any]:
        ws = workspace.upper()
        state = self._states.get(ws, {
            "enabled": False,
            "locked_symbol": None,
            "locked_at": None,
            "momentum_score": 0.0,
            "stagnant_minutes": 0.0,
            "stagnant_threshold_minutes": 15
        })
        return {
            "workspace": ws,
            "enabled": state.get("enabled", False),
            "locked_symbol": state.get("locked_symbol"),
            "locked_at": state.get("locked_at"),
            "locked_price": state.get("locked_price", 0.0),
            "current_price": state.get("last_price", 0.0),
            "momentum_score": state.get("momentum_score", 0.0),
            "stagnant_minutes": round(state.get("stagnant_minutes", 0.0), 1),
            "stagnant_threshold_minutes": state.get("stagnant_threshold_minutes", 15),
            "switch_reason": state.get("switch_reason", ""),
            "rotation_count": state.get("rotation_count", 0),
            "updated_at": _now_str()
        }

    def toggle(self, enabled: bool, workspace: str = "INDIA") -> Dict[str, Any]:
        ws = workspace.upper()
        if ws not in self._states:
            self._states[ws] = {
                "enabled": False,
                "locked_symbol": None,
                "locked_at": None,
                "locked_price": 0.0,
                "momentum_score": 0.0,
                "stagnant_since": None,
                "stagnant_minutes": 0.0,
                "stagnant_threshold_minutes": 15,
                "last_price": 0.0,
                "price_history": [],
                "switch_reason": "",
                "rotation_count": 0
            }
        self._states[ws]["enabled"] = bool(enabled)
        if not enabled:
            self._states[ws]["locked_symbol"] = None
            self._states[ws]["locked_at"] = None
            self._states[ws]["stagnant_since"] = None
            self._states[ws]["stagnant_minutes"] = 0.0
            self._states[ws]["switch_reason"] = "USER_DISABLED"
        else:
            self._states[ws]["switch_reason"] = "USER_ENABLED_SEARCHING_TOP_RUNNER"
        self._save_state()
        return self.get_status(ws)

    def update_cycle(self, candidate_opportunities: List[Dict[str, Any]], workspace: str = "INDIA"):
        """
        Evaluates current locked runner and candidate opportunities.
        1. If no symbol is locked, locks the candidate with the highest momentum.
        2. If locked, tracks price range over time to detect stagnation.
        3. If stagnant >= 15m, shifts lock to the new top runner.
        """
        ws = workspace.upper()
        state = self._states.get(ws)
        if not state or not state.get("enabled", False):
            return

        now_ts = time.time()
        now_dt_str = _now_str()

        # Available capital affordability filter for Indian equities
        avail_cap = 0.0
        if ws == "INDIA":
            try:
                from execution.kotak_neo_broker import kotak_neo_broker
                avail_cap = float(kotak_neo_broker.fetch_live_limits() or 0.0)
            except Exception:
                pass

        # Find top candidate with active BUY or SELL trading signal within account margin
        # Exclude any symbols currently placed on penalty/stagnation cooldown
        valid_candidates = []
        for c in candidate_opportunities:
            sym_name = str(c.get("symbol") or c.get("ticker") or c.get("asset") or "").upper()
            if not sym_name:
                continue
            if now_ts < self._symbol_cooldowns.get(sym_name, 0.0):
                continue
            sc = float(c.get("score", 0.0) or c.get("opportunity_score", 0.0))
            act = c.get("ai_action")
            if sc >= 60.0 and act in ["BUY", "SELL"]:
                px = float(c.get("price", 0.0) or c.get("last_price", 0.0))
                if ws == "INDIA" and avail_cap > 0 and px > 0:
                    req_margin = px / 5.0
                    if req_margin > avail_cap:
                        continue  # Skip unaffordable stocks whose 1-share margin exceeds account funds (e.g. LT @ ₹765 > ₹708)
                valid_candidates.append(c)

        valid_candidates.sort(
            key=lambda x: (
                float(x.get("score", 0.0) or x.get("opportunity_score", 0.0)),
                float(x.get("volatility", 0.0) or x.get("atr", 0.0))
            ),
            reverse=True
        )

        current_locked = state.get("locked_symbol")

        # If currently locked symbol is unaffordable in this account, clear it immediately so it rotates!
        if current_locked and ws == "INDIA" and avail_cap > 0:
            locked_cand = next(
                (c for c in candidate_opportunities if (c.get("symbol") or c.get("ticker") or c.get("asset")) == current_locked),
                None
            )
            cur_l_px = float((locked_cand.get("price", 0.0) or locked_cand.get("last_price", 0.0)) if locked_cand else state.get("locked_price", 0.0))
            if cur_l_px > 0 and (cur_l_px / 5.0) > avail_cap:
                old_unaff = current_locked
                current_locked = None
                state["locked_symbol"] = None
                state["switch_reason"] = f"CAPITAL_FILTER: {old_unaff} margin exceeds balance -> Unlocked"

        # Case 1: No symbol locked yet -> Lock top runner with active signal
        if not current_locked:
            if valid_candidates:
                top = valid_candidates[0]
                sym = top.get("symbol") or top.get("ticker") or top.get("asset")
                px = float(top.get("price", 0.0) or top.get("last_price", 0.0))
                score = float(top.get("score", 0.0) or top.get("opportunity_score", 0.0))
                act = top.get("ai_action", "BUY")
                state["locked_symbol"] = sym
                state["locked_action"] = act
                state["locked_at"] = now_dt_str
                state["locked_price"] = px
                state["last_price"] = px
                state["momentum_score"] = score
                state["stagnant_since"] = None
                state["stagnant_minutes"] = 0.0
                state["price_history"] = [{"t": now_ts, "p": px}]
                state["switch_reason"] = f"INITIAL_TOP_RUNNER_LOCK ({act} {score:.1f}%)"
                self._save_state()
                print(f"[MOMENTUM LOCK] Locked onto top runner: {sym} @ {px:,.4f} ({act} {score:.1f}%)")
            return

        # Case 2: Symbol is locked -> inspect its current quote and signal
        locked_candidate = next(
            (c for c in candidate_opportunities if (c.get("symbol") or c.get("ticker") or c.get("asset")) == current_locked),
            None
        )

        # Update current locked action & score
        if locked_candidate:
            state["locked_action"] = locked_candidate.get("ai_action", "HOLD")
            state["momentum_score"] = float(locked_candidate.get("score", 0.0) or locked_candidate.get("opportunity_score", 0.0))
        else:
            state["locked_action"] = "HOLD"
            state["momentum_score"] = 0.0

        # SIGNAL DETERIORATION / HOLD ROTATION:
        # If currently locked symbol entered HOLD or score dropped below 55%, demote & rotate immediately!
        signal_deteriorated = (state["locked_action"] not in ["BUY", "SELL"]) or (state["momentum_score"] < 55.0)
        if signal_deteriorated:
            old_sym = current_locked
            self._symbol_cooldowns[str(old_sym).upper()] = now_ts + 1200.0  # 20 min cooldown on degraded runner
            state["locked_symbol"] = None
            alt_candidates = [
                c for c in valid_candidates
                if str(c.get("symbol") or c.get("ticker") or c.get("asset")).upper() != str(old_sym).upper()
            ]
            if alt_candidates:
                new_top = alt_candidates[0]
                new_sym = new_top.get("symbol") or new_top.get("ticker") or new_top.get("asset")
                new_px = float(new_top.get("price", 0.0) or new_top.get("last_price", 0.0))
                new_score = float(new_top.get("score", 0.0) or new_top.get("opportunity_score", 0.0))
                new_act = new_top.get("ai_action", "BUY")
                state["locked_symbol"] = new_sym
                state["locked_action"] = new_act
                state["locked_at"] = now_dt_str
                state["locked_price"] = new_px
                state["last_price"] = new_px
                state["momentum_score"] = new_score
                state["stagnant_since"] = None
                state["stagnant_minutes"] = 0.0
                state["price_history"] = [{"t": now_ts, "p": new_px}]
                state["rotation_count"] = state.get("rotation_count", 0) + 1
                state["switch_reason"] = f"SIGNAL_SHIFT: {old_sym} deteriorated ({state['locked_action']}, {state['momentum_score']:.1f}%) -> Switched to {new_sym} ({new_act} {new_score:.1f}%)"
                self._save_state()
                print(f"[MOMENTUM ROTATION] {state['switch_reason']}")
                return
            else:
                state["switch_reason"] = f"SIGNAL_DROP: {old_sym} deteriorated ({state['locked_action']}, {state['momentum_score']:.1f}%) -> Unlocked (Waiting for active runner)"
                self._save_state()
                return

        cur_px = 0.0
        if locked_candidate:
            cur_px = float(locked_candidate.get("price", 0.0) or locked_candidate.get("last_price", 0.0))
            state["momentum_score"] = float(locked_candidate.get("score", 0.0) or locked_candidate.get("opportunity_score", 0.0))

        if cur_px <= 0.0:
            # Fallback to last known price
            cur_px = state.get("last_price", 0.0)

        if cur_px > 0.0:
            state["last_price"] = cur_px
            hist = state.setdefault("price_history", [])
            hist.append({"t": now_ts, "p": cur_px})
            # Keep history within last 20 minutes
            cutoff = now_ts - (20 * 60)
            hist[:] = [pt for pt in hist if pt["t"] >= cutoff]

            # Calculate price movement range over the last 10 minutes
            recent_10m = [pt["p"] for pt in hist if pt["t"] >= (now_ts - 10 * 60)]
            if len(recent_10m) >= 4:
                min_px = min(recent_10m)
                max_px = max(recent_10m)
                range_pct = ((max_px - min_px) / min_px) * 100.0 if min_px > 0 else 0.0

                # If movement is flat (< 0.15% movement over 10 minutes), mark stagnant
                if range_pct < 0.15:
                    if not state.get("stagnant_since"):
                        state["stagnant_since"] = now_ts
                    elapsed_stagnant = (now_ts - state["stagnant_since"]) / 60.0
                    state["stagnant_minutes"] = round(elapsed_stagnant, 1)

                    # If stagnant for >= threshold (default 10 minutes), ROTATE!
                    thresh = min(state.get("stagnant_threshold_minutes", 10), 10)
                    if elapsed_stagnant >= thresh:
                        old_sym = current_locked
                        self._symbol_cooldowns[str(old_sym).upper()] = now_ts + 1800.0  # 30m penalty cooldown for flat stagnant coin!
                        state["locked_symbol"] = None
                        alt_candidates = [
                            c for c in valid_candidates
                            if str(c.get("symbol") or c.get("ticker") or c.get("asset")).upper() != str(old_sym).upper()
                        ]
                        if alt_candidates:
                            new_top = alt_candidates[0]
                            new_sym = new_top.get("symbol") or new_top.get("ticker") or new_top.get("asset")
                            new_px = float(new_top.get("price", 0.0) or new_top.get("last_price", 0.0))
                            new_score = float(new_top.get("score", 0.0) or new_top.get("opportunity_score", 0.0))
                            new_act = new_top.get("ai_action", "BUY")

                            state["locked_symbol"] = new_sym
                            state["locked_action"] = new_act
                            state["locked_at"] = now_dt_str
                            state["locked_price"] = new_px
                            state["last_price"] = new_px
                            state["momentum_score"] = new_score
                            state["stagnant_since"] = None
                            state["stagnant_minutes"] = 0.0
                            state["price_history"] = [{"t": now_ts, "p": new_px}]
                            state["rotation_count"] = state.get("rotation_count", 0) + 1
                            state["switch_reason"] = f"STAGNATION_SHIFT: {old_sym} flat for {elapsed_stagnant:.0f}m ({range_pct:.2f}% range) -> Switched to {new_sym} ({new_score:.1f}%)"
                            self._save_state()
                            print(f"[MOMENTUM ROTATION] {state['switch_reason']}")
                            return
                        else:
                            state["locked_symbol"] = None
                            state["locked_action"] = "HOLD"
                            state["stagnant_since"] = None
                            state["stagnant_minutes"] = 0.0
                            state["switch_reason"] = f"STAGNATION_UNLOCKED: {old_sym} flat for {elapsed_stagnant:.0f}m ({range_pct:.2f}% range) -> Unlocked"
                            self._save_state()
                            return
                else:
                    # Healthy movement detected -> reset stagnation timer
                    state["stagnant_since"] = None
                    state["stagnant_minutes"] = 0.0

        self._save_state()


# Global singleton
dynamic_momentum_lock = DynamicMomentumLock()
