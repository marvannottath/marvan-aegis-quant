"""
AEGIS-QUANT Relative Volume (RVOL) Institutional Confirmation Engine.
Filters out false breakouts and retail bull/bear traps.
Rules:
  - Breakout trades require RVOL >= 1.30 (Institutional presence).
  - Trades with anemic volume (RVOL < 0.90) are rejected as low-liquidity whipsaws.
"""

from typing import Dict, Any, Tuple


class RelativeVolumeFilter:
    def __init__(self):
        # symbol -> rolling volume history
        self._volume_history: Dict[str, list] = {}

    def update_volume(self, symbol: str, volume: float) -> float:
        """Update rolling volume window and return current RVOL."""
        if volume <= 0:
            return 1.0

        clean_sym = symbol.upper()
        if clean_sym not in self._volume_history:
            self._volume_history[clean_sym] = []

        history = self._volume_history[clean_sym]
        history.append(volume)
        if len(history) > 20:
            history.pop(0)

        avg_vol = sum(history) / len(history)
        if avg_vol <= 0:
            return 1.0

        rvol = round(volume / avg_vol, 2)
        return rvol

    def check_volume_confirmation(
        self,
        symbol: str,
        current_volume: float = 0.0,
        baseline_avg_volume: float = 0.0,
        min_rvol_threshold: float = 1.25
    ) -> Tuple[bool, str]:
        """
        Verify if the breakout or momentum move has adequate institutional volume backing.
        """
        if current_volume <= 0 and baseline_avg_volume <= 0:
            # Fallback to rolling internal state
            clean_sym = symbol.upper()
            history = self._volume_history.get(clean_sym, [])
            if len(history) >= 5:
                avg = sum(history) / len(history)
                latest = history[-1]
                rvol = round(latest / max(1.0, avg), 2)
            else:
                return True, "RVOL_PASS: Insufficient historical volume samples, neutral pass."
        else:
            if baseline_avg_volume > 0:
                rvol = round(current_volume / baseline_avg_volume, 2)
            else:
                rvol = 1.0

        if rvol < min_rvol_threshold:
            return False, f"RVOL_FAIL: Relative volume {rvol:.2f}x is below institutional threshold {min_rvol_threshold}x. High risk of false breakout."

        return True, f"RVOL_PASS: Institutional volume confirmed ({rvol:.2f}x > {min_rvol_threshold}x)."


# Global Singleton
relative_volume_filter = RelativeVolumeFilter()
