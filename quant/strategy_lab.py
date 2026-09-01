"""
Aegis Quant Strategy Lab & Lifecycle Management Engine.
Strategy Lifecycle Pipeline:
  DRAFT -> TEST -> VALIDATED -> PAPER -> LIVE -> DEGRADED -> RETIRED

Aegis Strategy Score (0-100):
  Evaluates Profitability, Risk, Robustness, Stability, Execution, Liquidity, Out-of-Sample performance, and Overfit Risk.
"""

import time
import json
from pathlib import Path
from typing import Dict, Any, List, Optional

STRATEGY_FILE = Path(__file__).resolve().parent.parent / "data" / "strategy_lab_registry.json"

class StrategyLab:
    def __init__(self):
        self.strategies: List[Dict[str, Any]] = []
        self._load_registry()

    def _load_registry(self):
        if STRATEGY_FILE.exists():
            try:
                with open(STRATEGY_FILE, "r") as f:
                    data = json.load(f)
                    self.strategies = data.get("strategies", [])
            except Exception as e:
                print(f"[STRATEGY LAB] Load notice: {e}")

        if not self.strategies:
            # Seed Institutional Benchmark Strategies
            self.strategies = [
                {
                    "strategy_id": "STRAT-001",
                    "name": "Alpha Trend Momentum Core",
                    "version": "v3.2",
                    "lifecycle_stage": "LIVE",
                    "asset_class": "Crypto / Gold",
                    "sharpe_ratio": 2.45,
                    "max_drawdown_pct": 4.12,
                    "win_rate_pct": 74.5,
                    "aegis_score": 88,
                    "metrics": {
                        "profitability": 86,
                        "risk": 91,
                        "robustness": 88,
                        "out_of_sample": 87,
                        "overfit_risk": 11
                    },
                    "degraded_auto_pause": False
                },
                {
                    "strategy_id": "STRAT-002",
                    "name": "Volatility Mean Reversion Rebalancer",
                    "version": "v2.1",
                    "lifecycle_stage": "VALIDATED",
                    "asset_class": "Forex Majors",
                    "sharpe_ratio": 1.98,
                    "max_drawdown_pct": 5.20,
                    "win_rate_pct": 68.2,
                    "aegis_score": 82,
                    "metrics": {
                        "profitability": 80,
                        "risk": 84,
                        "robustness": 82,
                        "out_of_sample": 81,
                        "overfit_risk": 15
                    },
                    "degraded_auto_pause": False
                }
            ]
            self._save_registry()

    def _save_registry(self):
        try:
            STRATEGY_FILE.parent.mkdir(parents=True, exist_ok=True)
            temp_file = STRATEGY_FILE.with_suffix(".tmp")
            with open(temp_file, "w") as f:
                json.dump({"strategies": self.strategies}, f, indent=2)
            temp_file.replace(STRATEGY_FILE)
        except Exception as e:
            print(f"[STRATEGY LAB] Save notice: {e}")

    def calculate_aegis_score(self, prof: float, risk: float, rob: float, oos: float, overfit: float) -> int:
        """Calculate Aegis Strategy Score (0-100)."""
        score = (prof * 0.25) + (risk * 0.30) + (rob * 0.20) + (oos * 0.25) - (overfit * 0.5)
        return int(max(0, min(100, score)))

    def evaluate_auto_degradation(self, strategy_id: str, recent_drawdown: float) -> Dict[str, Any]:
        """Automatically degrade and pause live strategies that breach drawdown thresholds."""
        strat = next((s for s in self.strategies if s["strategy_id"] == strategy_id), None)
        if not strat:
            return {"status": "NOT_FOUND"}

        if recent_drawdown > strat["max_drawdown_pct"] * 1.5:
            strat["lifecycle_stage"] = "DEGRADED"
            strat["degraded_auto_pause"] = True
            self._save_registry()
            print(f"[STRATEGY LAB] AUTO-DEGRADATION WARNING: Strategy {strategy_id} paused due to drawdown breach ({recent_drawdown:.2f}%).")
            return {"status": "PAUSED_DEGRADED", "strategy_id": strategy_id, "message": f"Strategy paused and degraded to DEGRADED state."}

        return {"status": "HEALTHY", "strategy_id": strategy_id}

    def get_registered_strategies(self) -> List[Dict[str, Any]]:
        return self.strategies


# Global Singleton
strategy_lab = StrategyLab()
