"""
AEGIS QUANT — AI Trading Controller
=====================================
Workspace-specific AI state controller with 5 operational states,
14-gate resume preflight, persistent state, and immutable audit trail.

States (per workspace):
    RUNNING   — AI autonomous trading active
    PAUSED    — new AI orders blocked; monitoring continues; existing orders preserved
    STOPPED   — AI loop terminated; pending AI orders cancelled per policy
    BLOCKED   — automatically blocked (kill switch / market closed / gate failure)
    DISABLED  — explicitly disabled; requires admin to re-enable

Key Invariants:
    - AI PAUSED  ≠ AI STOPPED  ≠ EMERGENCY KILL SWITCH  ≠ MARKET CLOSED
    - MARKET CLOSED does NOT automatically close positions
    - AI STOP must cancel only AI-generated PENDING orders — never manual, never FILLED
    - Frontend alone cannot change state — server-side enforcement only
    - AI state survives page reload, workspace switch, and backend restart
    - RUNNING → PAUSED/STOPPED/BLOCKED allowed;
      PAUSED/STOPPED → RUNNING only after 14-gate preflight passes
"""

import json
import threading
import time
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List

UTC = timezone.utc
IST = timezone(timedelta(hours=5, minutes=30))

# State constants
RUNNING  = "RUNNING"
PAUSED   = "PAUSED"
STOPPED  = "STOPPED"
BLOCKED  = "BLOCKED"
DISABLED = "DISABLED"

WORKSPACES = ("INDIA", "FOREX_GOLD", "CRYPTO")
STATE_FILE = Path("data/ai_trading_state.json")

# Transitions allowed per spec
ALLOWED_TRANSITIONS = {
    RUNNING:  {PAUSED, STOPPED, BLOCKED, DISABLED},
    PAUSED:   {RUNNING, STOPPED, BLOCKED},
    STOPPED:  {RUNNING, BLOCKED},
    BLOCKED:  {PAUSED, RUNNING},
    DISABLED: {RUNNING},
}


class AITradingController:
    """
    Workspace-aware AI state controller.
    - Workspace states are independent (INDIA PAUSED ≠ CRYPTO PAUSED).
    - Emergency Kill Switch remains a separate global control in kill_switch.py.
    - All state transitions are server-side only and audit-logged.
    """

    def __init__(self):
        self._lock = threading.RLock()
        # Default all workspaces to PAUSED on first init (safer than RUNNING)
        self._states: Dict[str, Dict[str, Any]] = {
            ws: {
                "state": PAUSED,
                "reason": "Initial startup — manual resume required",
                "user": "SYSTEM",
                "timestamp": datetime.now(UTC).isoformat(),
                "block_reason": None,
            }
            for ws in WORKSPACES
        }
        self._test_broker_override: Dict[str, bool] = {}
        self._load_state()

    # ─── Persistence ─────────────────────────────────────────────────────────

    def _load_state(self):
        """Load persisted AI state from disk. DO NOT auto-resume if PAUSED/STOPPED."""
        try:
            if STATE_FILE.exists():
                raw = json.loads(STATE_FILE.read_text())
                for ws in WORKSPACES:
                    if ws in raw:
                        persisted = raw[ws]
                        # Never auto-start RUNNING on load — safety first
                        if persisted.get("state") == RUNNING:
                            persisted["state"] = PAUSED
                            persisted["reason"] = "Auto-paused at restart — manual resume required"
                            persisted["user"] = "SYSTEM_RESTART"
                        self._states[ws] = persisted
        except Exception:
            pass  # Load failure keeps defaults (all PAUSED)

    def _save_state(self):
        """Persist AI state to disk atomically."""
        try:
            STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                ws: self._states[ws]
                for ws in WORKSPACES
            }
            payload["_saved_at"] = datetime.now(UTC).isoformat()
            tmp = STATE_FILE.with_suffix(".tmp")
            tmp.write_text(json.dumps(payload, indent=2))
            tmp.replace(STATE_FILE)
        except Exception:
            pass

    # ─── State Queries ────────────────────────────────────────────────────────

    def get_state(self, workspace: str) -> str:
        """Return current AI state for the given workspace."""
        with self._lock:
            ws = workspace.upper()
            return self._states.get(ws, {}).get("state", PAUSED)

    def get_state_detail(self, workspace: str) -> Dict[str, Any]:
        """Return full state record for a workspace."""
        with self._lock:
            ws = workspace.upper()
            entry = self._states.get(ws, {}).copy()
            entry["workspace"] = ws
            entry["is_execution_allowed"] = (entry.get("state") == RUNNING)
            return entry

    def get_all_states(self) -> Dict[str, Dict[str, Any]]:
        """Return state details for all workspaces."""
        return {ws: self.get_state_detail(ws) for ws in WORKSPACES}

    def is_execution_allowed(self, workspace: str) -> Tuple[bool, str]:
        """
        Returns (allowed, reason). Only RUNNING state allows AI order execution.
        Used by execution_gate.validate_order() — Gate 21.
        """
        state = self.get_state(workspace)
        if state == RUNNING:
            return True, "AI_RUNNING"
        detail = self._states.get(workspace.upper(), {})
        reason = detail.get("reason", "AI not running")
        block_reason = detail.get("block_reason", "")
        msg = f"AI_TRADING_BLOCKED — state={state} — {block_reason or reason}"
        return False, msg

    # ─── State Transitions ────────────────────────────────────────────────────

    def pause(self, workspace: str, user: str, reason: str = "MANUAL_PAUSE") -> Dict[str, Any]:
        """
        Pause AI trading for a workspace.
        - Stops new AI orders.
        - Does NOT cancel existing orders.
        - Does NOT stop monitoring/reconciliation/alerts.
        """
        with self._lock:
            ws = workspace.upper()
            current = self.get_state(ws)
            if current not in ALLOWED_TRANSITIONS.get(current, set()) | {current}:
                pass  # allow any → PAUSED for safety
            if current == PAUSED:
                return {"ok": True, "workspace": ws, "state": PAUSED, "message": "Already PAUSED"}

            self._transition(ws, PAUSED, user, reason)
            self._emit_audit("AI_PAUSE", ws, current, PAUSED, user, reason)
            return {"ok": True, "workspace": ws, "state": PAUSED, "reason": reason, "user": user}

    def stop(self, workspace: str, user: str, reason: str = "MANUAL_STOP",
             cancel_pending_ai_orders: bool = True) -> Dict[str, Any]:
        """
        Stop AI trading for a workspace.
        - Terminates autonomous trading loop for this workspace.
        - Cancels eligible AI-generated PENDING orders (if cancel_pending_ai_orders=True).
        - Does NOT cancel manual orders.
        - Does NOT cancel FILLED orders.
        - Preserves all historical state and positions.
        """
        with self._lock:
            ws = workspace.upper()
            current = self.get_state(ws)
            if current == STOPPED:
                return {"ok": True, "workspace": ws, "state": STOPPED, "message": "Already STOPPED"}

            self._transition(ws, STOPPED, user, reason)
            self._emit_audit("AI_STOP", ws, current, STOPPED, user, reason)

            cancelled_orders = []
            if cancel_pending_ai_orders:
                cancelled_orders = self._cancel_pending_ai_orders(ws, user)

            return {
                "ok": True,
                "workspace": ws,
                "state": STOPPED,
                "reason": reason,
                "user": user,
                "cancelled_ai_orders": cancelled_orders,
            }

    def auto_block_for_market_close(self, workspace: str) -> Dict[str, Any]:
        """
        Auto-block AI when market session closes.
        Only blocks if currently RUNNING — does not override PAUSED/STOPPED.
        """
        with self._lock:
            ws = workspace.upper()
            current = self.get_state(ws)
            if current != RUNNING:
                return {"ok": True, "workspace": ws, "state": current, "message": "Not RUNNING — no action"}

            block_reason = "MARKET_CLOSED — auto-blocked until manual resume"
            self._transition(ws, BLOCKED, "MARKET_SESSION_ENGINE", block_reason,
                             block_reason=block_reason)
            self._emit_audit("AI_AUTO_BLOCKED_MARKET_CLOSE", ws, RUNNING, BLOCKED,
                             "MARKET_SESSION_ENGINE", block_reason)
            return {
                "ok": True,
                "workspace": ws,
                "state": BLOCKED,
                "reason": block_reason,
                "auto_resume": False,  # Requires manual resume by default
            }

    def auto_block_for_drawdown(self, workspace: str, drawdown_pct: float, max_drawdown_pct: float) -> Dict[str, Any]:
        """
        Auto-block AI when portfolio drawdown breaches circuit breaker limit.
        Guarantees that trading is frozen immediately to prevent capital erosion.
        """
        with self._lock:
            ws = workspace.upper()
            current = self.get_state(ws)
            if current != RUNNING:
                return {"ok": True, "workspace": ws, "state": current, "message": f"Not RUNNING ({current}) — no action"}

            block_reason = f"MAX_DRAWDOWN_BREACHED — Drawdown {drawdown_pct:.2f}% >= {max_drawdown_pct:.1f}% limit. Circuit breaker tripped."
            self._transition(ws, BLOCKED, "RISK_CIRCUIT_BREAKER", block_reason, block_reason=block_reason)
            self._emit_audit("AI_AUTO_BLOCKED_DRAWDOWN", ws, RUNNING, BLOCKED, "RISK_CIRCUIT_BREAKER", block_reason)
            return {
                "ok": True,
                "workspace": ws,
                "state": BLOCKED,
                "reason": block_reason,
                "auto_resume": False,
            }

    def block(self, workspace: str, user: str, reason: str) -> Dict[str, Any]:
        """Generic block (kill switch, gate failure, etc.)."""
        with self._lock:
            ws = workspace.upper()
            current = self.get_state(ws)
            self._transition(ws, BLOCKED, user, reason, block_reason=reason)
            self._emit_audit("AI_BLOCKED", ws, current, BLOCKED, user, reason)
            return {"ok": True, "workspace": ws, "state": BLOCKED, "reason": reason}

    def resume(self, workspace: str, user: str) -> Dict[str, Any]:
        """
        Resume AI trading for a workspace.
        Runs 14-gate preflight — if any gate fails, AI is set to BLOCKED.
        """
        with self._lock:
            ws = workspace.upper()
            current = self.get_state(ws)

            # Run preflight
            preflight_ok, gates = self._run_resume_preflight(ws)

            if not preflight_ok:
                failed = [g["name"] for g in gates if not g.get("passed", False)]
                block_reason = f"RESUME_BLOCKED — failed gates: {', '.join(failed)}"
                self._transition(ws, BLOCKED, user, block_reason, block_reason=block_reason)
                self._emit_audit("AI_BLOCKED", ws, current, BLOCKED, user, block_reason)
                return {
                    "ok": False,
                    "workspace": ws,
                    "state": BLOCKED,
                    "reason": block_reason,
                    "failed_gates": failed,
                    "gates": gates,
                    "gates_passed": sum(1 for g in gates if g.get("passed") is True),
                    "gates_total": len(gates),
                }

            self._transition(ws, RUNNING, user, "Manual resume — all preflight gates passed")
            self._emit_audit("AI_RESUME", ws, current, RUNNING, user,
                             "All 14 preflight gates passed")
            return {
                "ok": True,
                "workspace": ws,
                "state": RUNNING,
                "user": user,
                "gates": gates,
                "gates_passed": sum(1 for g in gates if g.get("passed") is True),
                "gates_total": len(gates),
            }

    def resume_preflight_check(self, workspace: str) -> Dict[str, Any]:
        """Check resume readiness without actually resuming."""
        ws = workspace.upper()
        ok, gates = self._run_resume_preflight(ws)
        passed_count = sum(1 for g in gates if g.get("passed") is True)
        failed_count = sum(1 for g in gates if g.get("passed") is False)
        return {
            "workspace": ws,
            "ready_to_resume": ok,
            "gates_passed": passed_count,
            "gates_failed": failed_count,
            "gates_total": len(gates),
            "gates": gates,
        }

    # ─── 14-Gate Resume Preflight (STRICT FAIL-CLOSED) ──────────────────────

    def _run_resume_preflight(self, workspace: str) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        Run 14 gates before allowing AI resume.
        RULE (Phase 5D):
          ANY UNKNOWN / EXCEPTION / TIMEOUT / MISSING DATA must produce:
            passed = False
            state = BLOCKED
          No fail-open path. No default PASS. No skipped gate accepted as pass.
        Returns (all_passed: bool, gates: list)
        """
        ws = workspace.upper()
        now_ts = datetime.now(UTC).isoformat()
        gates = []

        # Gate 1: Workspace Valid
        try:
            g1_ok = ws in WORKSPACES
            g1_msg = f"Workspace '{ws}' {'recognized' if g1_ok else 'INVALID_WORKSPACE'}"
        except Exception as e:
            g1_ok = False
            g1_msg = f"CHECK_FAILED: Workspace validation error: {e}"
        gates.append({
            "id": 1, "name": "Workspace Valid", "passed": g1_ok,
            "detail": g1_msg, "workspace": ws, "timestamp": now_ts
        })

        # Gate 2: Market Session OPEN
        try:
            from core.market_session_engine import market_session_engine
            sess = market_session_engine.get_state(ws)
            g2_ok = (sess == "OPEN")
            g2_msg = f"Session state: {sess} — {'OPEN' if g2_ok else 'NOT OPEN'}"
        except Exception as e:
            g2_ok = False
            g2_msg = f"CHECK_FAILED: Session engine error: {e}"
        gates.append({
            "id": 2, "name": "Market Session OPEN", "passed": g2_ok,
            "detail": g2_msg, "workspace": ws, "timestamp": now_ts
        })

        # Gate 3: Broker/Exchange Connection (MUST BE VERIFIED — NO UNCONFIGURED PASS)
        try:
            if ws in self._test_broker_override:
                g3_ok = bool(self._test_broker_override[ws])
                g3_msg = f"Broker connection: {'VERIFIED (TEST OVERRIDE)' if g3_ok else 'UNVERIFIED'}"
            elif ws == "INDIA":
                from execution.upstox_broker import upstox_broker
                state = upstox_broker.get_configuration_state()
                g3_ok = state in ("AUTHENTICATED", "READ-ONLY VERIFIED")
                g3_msg = f"Upstox: {state} — {'Connection verified' if g3_ok else 'Broker connection unverified'}"
            elif ws == "CRYPTO":
                from execution.binance_broker import binance_broker
                state = binance_broker.get_configuration_state()
                g3_ok = state in ("AUTHENTICATED", "TESTNET VERIFIED")
                g3_msg = f"Binance: {state} — {'Connection verified' if g3_ok else 'Broker connection unverified'}"
            elif ws == "FOREX_GOLD":
                g3_ok = False
                g3_msg = "Forex provider is SIMULATED / NOT CONFIGURED — broker connection unverified"
            else:
                g3_ok = False
                g3_msg = f"Unknown workspace '{ws}' — broker connection unverified"
        except Exception as e:
            g3_ok = False
            g3_msg = f"CHECK_FAILED: Broker check error: {e}"
        gates.append({
            "id": 3, "name": "Broker/Exchange Connection", "passed": g3_ok,
            "detail": g3_msg, "workspace": ws, "timestamp": now_ts
        })

        # Gate 4: Market Data Freshness (0.0 <= age <= 5.0, age 9999.0 is NOT allowed)
        try:
            from core.market_data_watchdog import market_data_watchdog
            symbol_map = {"INDIA": "RELIANCE", "CRYPTO": "BTCUSDT", "FOREX_GOLD": "XAUUSD"}
            sym = symbol_map.get(ws, "BTCUSDT")
            age = market_data_watchdog.get_age(sym)
            if age == 9999.0:
                g4_ok = False
                g4_msg = f"{sym} market data NOT SUBSCRIBED (age=9999.0s) — live feed missing"
            elif age > 5.0:
                g4_ok = False
                g4_msg = f"{sym} market data STALE ({age:.1f}s > 5.0s threshold)"
            elif age < 0.0:
                g4_ok = False
                g4_msg = f"{sym} invalid market data age ({age:.1f}s)"
            else:
                g4_ok = True
                g4_msg = f"{sym} data FRESH (age={age:.1f}s <= 5.0s)"
        except Exception as e:
            g4_ok = False
            g4_msg = f"CHECK_FAILED: Market data watchdog error: {e}"
        gates.append({
            "id": 4, "name": "Market Data Freshness", "passed": g4_ok,
            "detail": g4_msg, "workspace": ws, "timestamp": now_ts
        })

        # Gate 5: Account Synchronization
        try:
            from execution.paper_broker import paper_broker
            from core.workspace_manager import workspace_manager
            meta = workspace_manager.get_workspace_meta(ws)
            target_pool = meta.get("default_pool", "AEGIS_QUANT_MASTER")
            pool_name = paper_broker.active_pool_name if paper_broker.active_pool_name in meta.get("allowed_pools", [target_pool]) else target_pool
            pool = paper_broker.pools.get(pool_name, {})
            cash = pool.get("virtual_cash", getattr(paper_broker, "virtual_cash", None))
            
            if cash is not None and isinstance(cash, (int, float)) and cash > 0:
                g5_ok = True
                g5_msg = f"Account synchronized — virtual_cash={float(cash):.2f}"
            else:
                g5_ok = False
                if cash == 0.0 and "LIVE" in pool_name:
                    g5_msg = f"Account sync failed — Live wallet balance is 0.00 USDT (Deposit funds to trade)"
                else:
                    g5_msg = f"Account sync failed — invalid virtual_cash={cash}"
        except Exception as e:
            g5_ok = False
            g5_msg = f"CHECK_FAILED: Account sync error: {e}"
        gates.append({
            "id": 5, "name": "Account Synchronization", "passed": g5_ok,
            "detail": g5_msg, "workspace": ws, "timestamp": now_ts
        })

        # Gate 6: Position Synchronization
        try:
            from core.position_snapshot_service import position_snapshot_service
            snap = position_snapshot_service.get_snapshot(ws)
            if not snap:
                g6_ok = False
                g6_msg = f"Position snapshot unavailable for {ws}"
            elif snap.get("reconciliation_status") in ("FAIL", "UNKNOWN", "RECONCILIATION_FAIL"):
                g6_ok = False
                g6_msg = f"Position reconciliation status: {snap.get('reconciliation_status')}"
            elif snap.get("delta_detected", False):
                g6_ok = False
                g6_msg = f"Position delta detected: {snap.get('delta_description', 'Discrepancy detected')}"
            elif "open_position_count" in snap:
                g6_ok = True
                g6_msg = f"Positions synchronized ({snap.get('open_position_count', 0)} open)"
            else:
                g6_ok = False
                g6_msg = "Position snapshot schema invalid"
        except Exception as e:
            g6_ok = False
            g6_msg = f"CHECK_FAILED: Position sync error: {e}"
        gates.append({
            "id": 6, "name": "Position Synchronization", "passed": g6_ok,
            "detail": g6_msg, "workspace": ws, "timestamp": now_ts
        })

        # Gate 7: Risk Engine Circuit Breaker CLEAR
        try:
            from core.risk_engine import risk_engine
            if risk_engine.circuit_tripped:
                g7_ok = False
                g7_msg = f"Circuit breaker TRIPPED: {risk_engine.trip_reason}"
            else:
                g7_ok = True
                g7_msg = "Circuit breaker CLEAR (NORMAL_OPERATIONS)"
        except Exception as e:
            g7_ok = False
            g7_msg = f"CHECK_FAILED: Risk engine error: {e}"
        gates.append({
            "id": 7, "name": "Risk Engine Circuit Breaker CLEAR", "passed": g7_ok,
            "detail": g7_msg, "workspace": ws, "timestamp": now_ts
        })

        # Gate 8: Daily Drawdown Within Limits (FAIL-CLOSED)
        try:
            from core.risk_engine import risk_engine
            dd_info = risk_engine.get_drawdown(ws)
            dd_pct = float(dd_info.get("drawdown_pct", 0.0))
            max_dd = float(dd_info.get("max_drawdown_pct", risk_engine.max_drawdown_pct))
            if dd_info.get("breached", False) or dd_pct >= max_dd:
                g8_ok = False
                g8_msg = f"Drawdown {dd_pct:.2f}% breached limit {max_dd:.2f}%"
            else:
                g8_ok = True
                g8_msg = f"Drawdown {dd_pct:.2f}% within limit {max_dd:.2f}%"
        except Exception as e:
            g8_ok = False
            g8_msg = f"CHECK_FAILED: Drawdown evaluation error: {e}"
        gates.append({
            "id": 8, "name": "Daily Drawdown Within Limits", "passed": g8_ok,
            "detail": g8_msg, "workspace": ws, "timestamp": now_ts
        })

        # Gate 9: Daily Loss Limits Not Breached (FAIL-CLOSED)
        try:
            from core.risk_engine import risk_engine
            loss = float(risk_engine.daily_realized_loss)
            limit = float(risk_engine.daily_loss_limit_usd)
            if abs(loss) >= limit:
                g9_ok = False
                g9_msg = f"Daily loss ${abs(loss):.2f} reached limit ${limit:.2f}"
            else:
                g9_ok = True
                g9_msg = f"Daily loss ${abs(loss):.2f} within limit ${limit:.2f}"
        except Exception as e:
            g9_ok = False
            g9_msg = f"CHECK_FAILED: Loss limit check error: {e}"
        gates.append({
            "id": 9, "name": "Daily Loss Limits Not Breached", "passed": g9_ok,
            "detail": g9_msg, "workspace": ws, "timestamp": now_ts
        })

        # Gate 10: News Lockout Not Active (FAIL-CLOSED)
        try:
            from sync.economic_calendar import economic_filter
            locked, reason = economic_filter.is_news_lockout_active()
            if locked:
                g10_ok = False
                g10_msg = f"News lockout ACTIVE — {reason}"
            else:
                g10_ok = True
                g10_msg = "News lockout CLEAR"
        except Exception as e:
            g10_ok = False
            g10_msg = f"CHECK_FAILED: News check error: {e}"
        gates.append({
            "id": 10, "name": "News Lockout Not Active", "passed": g10_ok,
            "detail": g10_msg, "workspace": ws, "timestamp": now_ts
        })

        # Gate 11: Reconciliation Sentinel Healthy (FAIL-CLOSED)
        try:
            from core.reconciliation_sentinel import reconciliation_sentinel
            status = str(reconciliation_sentinel.last_report.get("status", "UNKNOWN")).upper()
            if status in ("HEALTHY", "PASS"):
                g11_ok = True
                g11_msg = f"Reconciliation status: {status}"
            else:
                g11_ok = False
                g11_msg = f"Reconciliation status NOT HEALTHY: {status}"
        except Exception as e:
            g11_ok = False
            g11_msg = f"CHECK_FAILED: Reconciliation sentinel error: {e}"
        gates.append({
            "id": 11, "name": "Reconciliation Sentinel Healthy", "passed": g11_ok,
            "detail": g11_msg, "workspace": ws, "timestamp": now_ts
        })

        # Gate 12: Emergency Kill Switch CLEAR (FAIL-CLOSED)
        try:
            from core.environment_gate import environment_gate
            ks_active = environment_gate._is_kill_switch_active()
            if ks_active:
                g12_ok = False
                g12_msg = "Kill switch ACTIVE — all execution blocked"
            else:
                g12_ok = True
                g12_msg = "Kill switch CLEAR"
        except Exception as e:
            g12_ok = False
            g12_msg = f"CHECK_FAILED: Kill switch error: {e}"
        gates.append({
            "id": 12, "name": "Emergency Kill Switch CLEAR", "passed": g12_ok,
            "detail": g12_msg, "workspace": ws, "timestamp": now_ts
        })

        # Gate 13: Execution Environment Valid (PAPER) (FAIL-CLOSED)
        try:
            from core.environment_gate import environment_gate
            env_ok, env_msg = environment_gate.check_order_allowed("PAPER", 0.0)
            g13_ok = bool(env_ok)
            g13_msg = env_msg if env_ok else f"Environment gate rejected: {env_msg}"
        except Exception as e:
            g13_ok = False
            g13_msg = f"CHECK_FAILED: Environment gate error: {e}"
        gates.append({
            "id": 13, "name": "Execution Environment Valid (PAPER)", "passed": g13_ok,
            "detail": g13_msg, "workspace": ws, "timestamp": now_ts
        })

        # Gate 14: Instrument Master Loaded (FAIL-CLOSED)
        try:
            from core.instrument_master import instrument_master
            ws_instruments = [s for s in instrument_master.get_all_symbols()
                              if instrument_master.get_workspace(s) == ws]
            if len(ws_instruments) >= 1:
                g14_ok = True
                g14_msg = f"{len(ws_instruments)} instruments registered for {ws}"
            else:
                g14_ok = False
                g14_msg = f"Zero instruments registered for workspace {ws}"
        except Exception as e:
            g14_ok = False
            g14_msg = f"CHECK_FAILED: Instrument master error: {e}"
        gates.append({
            "id": 14, "name": "Instrument Master Loaded", "passed": g14_ok,
            "detail": g14_msg, "workspace": ws, "timestamp": now_ts
        })

        passed_count = sum(1 for g in gates if g.get("passed") is True)
        failed_count = sum(1 for g in gates if g.get("passed") is False)
        unknown_count = sum(1 for g in gates if g.get("passed") is None)
        skipped_count = sum(1 for g in gates if g.get("skipped", False))

        # Strict evidence rule: must be exactly 14, all passed, 0 failed, 0 unknown, 0 skipped
        all_passed = (
            len(gates) == 14
            and passed_count == 14
            and failed_count == 0
            and unknown_count == 0
            and skipped_count == 0
        )
        return all_passed, gates


    # ─── Pending AI Order Cancellation ───────────────────────────────────────

    def _cancel_pending_ai_orders(self, workspace: str, cancelled_by: str) -> List[str]:
        """
        Cancel AI-generated orders that are still PENDING or SUBMITTED.
        NEVER cancels: manually created, FILLED, PARTIALLY_FILLED, CANCELLED, FAILED orders.
        Returns list of cancelled order IDs.
        """
        cancelled = []
        try:
            from core.order_state_machine import OrderStateMachine
            osm = OrderStateMachine()
            all_orders = osm.get_orders_by_workspace(workspace)
            for order in all_orders:
                # Only cancel AI-generated orders
                if order.get("source", "MANUAL") not in ("AI", "AI_GENERATED", "AUTONOMOUS"):
                    continue
                # Only cancel pre-execution states
                if order.get("status") not in ("PENDING", "SUBMITTED", "QUEUED"):
                    continue
                try:
                    osm.transition(
                        order["order_id"],
                        "CANCELLED",
                        reason=f"AI STOP — cancelled by {cancelled_by}"
                    )
                    cancelled.append(order["order_id"])
                    self._emit_audit(
                        "AI_ORDER_CANCELLED_ON_STOP", workspace,
                        order["order_id"], order["order_id"],
                        cancelled_by,
                        f"AI STOP — AI-generated order {order['order_id']} cancelled"
                    )
                except Exception:
                    pass
        except Exception:
            pass
        return cancelled

    # ─── Internal Helpers ─────────────────────────────────────────────────────

    def _transition(self, workspace: str, new_state: str, user: str, reason: str,
                    block_reason: Optional[str] = None):
        """Apply state transition and persist."""
        now = datetime.now(UTC).isoformat()
        self._states[workspace] = {
            "state": new_state,
            "reason": reason,
            "user": user,
            "timestamp": now,
            "block_reason": block_reason,
        }
        self._save_state()

    def _emit_audit(self, event_type: str, workspace: str, prev: str, new: str,
                    user: str, reason: str):
        """Emit SHA-256-chained audit event for state transition."""
        try:
            from core.audit_logger import audit_logger
            audit_logger.log_event(
                event_type=event_type,
                workspace=workspace,
                amount=0.0,
                symbol="AI_TRADING_CONTROLLER",
                order_id="SYSTEM",
                user=user,
                execution_id=f"AIT-{workspace}-{int(time.time()*1000)}",
                ip_address="SYSTEM",
                environment="ALL",
                previous_state=prev,
                new_state=new,
                reason=reason,
            )
        except Exception:
            pass  # Audit failure must never block state transitions


# Global singleton
ai_trading_controller = AITradingController()
