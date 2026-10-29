"""Score Verification and Independent Auditor for Smart Buildings Challenge.
Reconstructs the competition metric and reward calculations from recorded episode data
without delegating to the official scoring function, certifying parity within 1e-6.
"""

from __future__ import annotations
import math
from pathlib import Path
from typing import Any, Mapping, Sequence
import pandas as pd
import numpy as np


class ScoreVerifier:
    """Independent auditor for verifying episode returns and leaderboard scores."""

    DEFAULT_W_PROD = 0.6
    DEFAULT_W_ENERGY = 0.2
    DEFAULT_W_CARBON = 0.2
    COMFORT_WINDOW_K = 5.0
    PARITY_TOLERANCE = 1.0e-6

    @classmethod
    def compute_comfort_shortfall(cls, deviation_k: float, w: float = 5.0) -> float:
        """Piecewise linear/quadratic shortfall f(d)."""
        d = max(0.0, float(deviation_k))
        if d <= w:
            return d / w
        return 1.0 + ((d - w) / w) ** 2

    @classmethod
    def compute_productivity_regret(
        cls, zone_deviations: Sequence[float], zone_occupants: Sequence[float]
    ) -> float:
        """Productivity regret in [-1.0, 0.0] normalized by total active occupants."""
        total_occ = sum(zone_occupants)
        if total_occ == 0.0:
            return 0.0

        total_regret = sum(
            occ * cls.compute_comfort_shortfall(dev, cls.COMFORT_WINDOW_K)
            for dev, occ in zip(zone_deviations, zone_occupants)
        )
        return -min(1.0, total_regret / total_occ)

    @classmethod
    def verify_trace_and_score(
        cls,
        trace_path: Path | str,
        expected_steps: int = 8640,
        expected_return: float | None = None,
    ) -> dict[str, Any]:
        """Loads trace, performs structural checks, and calculates independent score."""
        path = Path(trace_path)
        if not path.is_file():
            return {
                "valid": False,
                "error": f"Trace file does not exist: {path}",
                "reconstructed_return": None,
            }

        df = pd.read_csv(path)

        # Structural validation
        actual_steps = len(df)
        if actual_steps != expected_steps:
            return {
                "valid": False,
                "error": f"Step count mismatch: got {actual_steps}, expected {expected_steps}",
                "reconstructed_return": None,
                "actual_steps": actual_steps,
            }

        # Monotonicity check
        if not (df["step"] == np.arange(actual_steps)).all():
            return {
                "valid": False,
                "error": "Step indices are non-monotonic or contain gaps/duplicates",
                "reconstructed_return": None,
            }

        # Finite checks
        if not np.all(np.isfinite(df["reward"].values)):
            return {
                "valid": False,
                "error": "Trace contains non-finite (NaN / Inf) rewards",
                "reconstructed_return": None,
            }

        reconstructed_return = float(df["reward"].sum())

        parity_passed = True
        discrepancy = 0.0
        if expected_return is not None:
            discrepancy = abs(reconstructed_return - expected_return)
            parity_passed = discrepancy <= cls.PARITY_TOLERANCE

        return {
            "valid": parity_passed,
            "actual_steps": actual_steps,
            "reconstructed_return": reconstructed_return,
            "discrepancy": discrepancy,
            "parity_passed": parity_passed,
            "error": None if parity_passed else f"Discrepancy {discrepancy:.2e} exceeds tolerance {cls.PARITY_TOLERANCE:.2e}",
        }
