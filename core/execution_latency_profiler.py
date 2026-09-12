"""
Aegis-Quant Execution Pipeline Latency Profiler.
Profiles the 10-step institutional execution pipeline:
  1. Market Tick Received
  2. Market Data Validation
  3. Feature Calculation
  4. AI Agent Processing
  5. Ensemble Decision
  6. Risk Evaluation
  7. Execution Gate
  8. Order Submission
  9. Fill / Execution Confirmation
  10. Ledger Write
Calculates P50, P95, P99, min, max, avg latencies from authoritative execution events.
"""

import time
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta

IST_TZ = timezone(timedelta(hours=5, minutes=30))
LATENCY_LOG_FILE = Path(__file__).resolve().parent.parent / "data" / "execution_latency_log.json"

PIPELINE_STAGES = [
    "Market Tick",
    "Validation",
    "Feature Calculation",
    "AI Processing",
    "Ensemble",
    "Risk",
    "Security Gate",
    "Order Submission",
    "Exchange/Fills",
    "Ledger Write"
]


class ExecutionLatencyProfiler:
    def __init__(self):
        self.executions: List[Dict[str, Any]] = []
        self._load_log()

    def _load_log(self):
        if LATENCY_LOG_FILE.exists():
            try:
                with open(LATENCY_LOG_FILE, "r") as f:
                    data = json.load(f)
                    # Filter out any legacy synthetic seed executions
                    raw = data.get("executions", [])
                    self.executions = [e for e in raw if e.get("execution_id") != "EXEC-INIT-001"]
            except Exception as e:
                print(f"[LATENCY PROFILER] Load notice: {e}")

    def _save_log(self):
        try:
            LATENCY_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
            tmp = LATENCY_LOG_FILE.with_suffix(".tmp")
            with open(tmp, "w") as f:
                json.dump({"executions": self.executions[:200]}, f, indent=2)
            tmp.replace(LATENCY_LOG_FILE)
        except Exception as e:
            print(f"[LATENCY PROFILER] Save notice: {e}")

    def record_execution(
        self,
        execution_id: Optional[str] = None,
        symbol: str = "BTCUSD",
        status: str = "PASS",
        stages: Any = None,
        risk_result: str = "APPROVED",
        order_id: str = "",
        environment: str = "PAPER",
        **kwargs
    ) -> Dict[str, Any]:
        """Record an authoritative 10-stage execution pipeline trace."""
        timestamp = datetime.now(timezone.utc).astimezone(IST_TZ).strftime("%Y-%m-%d %H:%M:%S IST")

        # Normalize stages
        normalized_stages: List[Dict[str, Any]] = []
        if isinstance(stages, dict):
            for idx, (k, v) in enumerate(stages.items(), 1):
                clean_name = str(k).replace("_", " ").title()
                dur = float(v) if isinstance(v, (int, float)) else 0.5
                normalized_stages.append({
                    "stage": clean_name,
                    "duration_ms": round(dur, 2),
                    "status": "PASS"
                })
        elif isinstance(stages, list):
            for s in stages:
                if isinstance(s, dict):
                    normalized_stages.append(s)
        else:
            for s_name in PIPELINE_STAGES:
                normalized_stages.append({
                    "stage": s_name,
                    "duration_ms": 0.5,
                    "status": "PASS"
                })

        total_duration = round(sum(float(s.get("duration_ms", 0.0)) for s in normalized_stages), 2)
        exec_id = execution_id or f"EXEC-{int(time.time()*1000)}"

        record = {
            "execution_id": exec_id,
            "timestamp": timestamp,
            "environment": environment,
            "symbol": symbol,
            "status": status,
            "risk_result": risk_result,
            "order_id": order_id,
            "total_latency_ms": total_duration,
            "stages": normalized_stages
        }

        self.executions.insert(0, record)
        self._save_log()
        try:
            from core.unified_database import unified_database
            unified_database.insert_execution_trace(record)
        except Exception:
            pass
        return record

    def get_summary(self, environment: str = "ALL") -> Dict[str, Any]:
        """Compute P50, P95, P99, min, max, avg, and stage averages from authoritative traces."""
        if environment and environment not in ["ALL", ""]:
            if environment in ["PAPER", "AEGIS_QUANT_MASTER"]:
                env_execs = [e for e in self.executions if e.get("environment") in ["PAPER", "AEGIS_QUANT_MASTER"]]
            else:
                env_execs = [e for e in self.executions if e.get("environment") == environment]
        else:
            env_execs = self.executions

        is_fallback = False
        if not env_execs and self.executions:
            env_execs = self.executions
            is_fallback = True

        all_totals = [float(e["total_latency_ms"]) for e in env_execs if e.get("total_latency_ms") is not None]
        if not all_totals and self.executions:
            all_totals = [float(e["total_latency_ms"]) for e in self.executions if e.get("total_latency_ms") is not None]
            is_fallback = True

        if not all_totals:
            return {
                "status": "NO_DATA",
                "message": "NO EXECUTIONS YET — PROFILER ARMED",
                "sample_count": 0,
                "p50": None, "p95": None, "p99": None,
                "avg": None, "min": None, "max": None,
                "stage_averages": [],
                "recent_executions": [],
                "is_fallback": False
            }

        sorted_totals = sorted(all_totals)
        n = len(sorted_totals)

        def pct(p):
            idx = max(0, int(round(p / 100 * n)) - 1)
            return round(sorted_totals[idx], 2)

        p50 = pct(50)
        p95 = pct(95)
        p99 = pct(99)
        avg = round(sum(all_totals) / n, 2)
        min_val = round(min(all_totals), 2)
        max_val = round(max(all_totals), 2)

        # Average duration per pipeline stage
        stage_sums = {st: 0.0 for st in PIPELINE_STAGES}
        stage_counts = {st: 0 for st in PIPELINE_STAGES}

        for ex in self.executions:
            for s in ex.get("stages", []):
                st_name = s.get("stage")
                if st_name in stage_sums:
                    stage_sums[st_name] += float(s.get("duration_ms", 0.0))
                    stage_counts[st_name] += 1

        stage_averages = [
            {
                "stage_number": idx + 1,
                "stage": st_name,
                "avg_duration_ms": round(stage_sums[st_name] / max(1, stage_counts[st_name]), 2),
                "status": "PASS"
            }
            for idx, st_name in enumerate(PIPELINE_STAGES)
        ]

        return {
            "status": "SUCCESS",
            "environment": environment,
            "sample_count": n,
            "p50": p50,
            "p95": p95,
            "p99": p99,
            "avg": avg,
            "min": min_val,
            "max": max_val,
            "stage_averages": stage_averages,
            "recent_executions": env_execs[:20],
            "is_fallback": is_fallback
        }


# Global Singleton
execution_latency_profiler = ExecutionLatencyProfiler()
