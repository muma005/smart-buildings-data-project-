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
    def compute_step_reward(
        cls,
        productivity_regret: float,
        energy_cost: float,
        carbon_emission: float,
        w_p: float = DEFAULT_W_PROD,
        w_e: float = DEFAULT_W_ENERGY,
        w_c: float = DEFAULT_W_CARBON,
    ) -> float:
        """Independent reconstruction of per-step agent reward.
        
        Official starter kit formula:
        agent_reward = w_p * regret - w_e * energy_cost - w_c * carbon_emission
        where regret <= 0, and energy_cost and carbon_emission are non-negative penalties.
        """
        return float(w_p * productivity_regret - w_e * energy_cost - w_c * carbon_emission)

    @classmethod
    def verify_reward_arithmetic(
        cls,
        step_records: Sequence[Mapping[str, float]],
        w_p: float = DEFAULT_W_PROD,
        w_e: float = DEFAULT_W_ENERGY,
        w_c: float = DEFAULT_W_CARBON,
    ) -> dict[str, Any]:
        """Validates step-reward arithmetic against individual component costs (Defect 19)."""
        for idx, rec in enumerate(step_records):
            regret = rec.get("normalized_productivity_regret", rec.get("productivity_regret", 0.0))
            energy = rec.get("normalized_energy_cost", rec.get("energy_cost", 0.0))
            carbon = rec.get("normalized_carbon_emission", rec.get("carbon_emission", 0.0))

            expected = cls.compute_step_reward(regret, energy, carbon, w_p=w_p, w_e=w_e, w_c=w_c)
            actual = rec.get("agent_reward", rec.get("reward"))

            if actual is None:
                return {
                    "valid": False,
                    "error": f"Missing reward value in record at step {idx}",
                }

            discrepancy = abs(float(actual) - expected)
            if discrepancy > cls.PARITY_TOLERANCE:
                return {
                    "valid": False,
                    "error": (
                        f"Step-reward arithmetic mismatch at step {idx}: expected {expected:.6f}, "
                        f"got {float(actual):.6f} (discrepancy {discrepancy:.2e} > tolerance {cls.PARITY_TOLERANCE:.2e})"
                    ),
                    "step": idx,
                    "discrepancy": discrepancy,
                }

        return {"valid": True, "error": None}

    @classmethod
    def verify_episode_aggregation(
        cls,
        step_rewards: Sequence[float],
        reported_return: float,
    ) -> dict[str, Any]:
        """Verifies that an episode return is the exact sum of step rewards (Defect 20)."""
        reconstructed = float(sum(step_rewards))
        discrepancy = abs(reconstructed - float(reported_return))
        passed = discrepancy <= cls.PARITY_TOLERANCE
        return {
            "valid": passed,
            "reconstructed_return": reconstructed,
            "reported_return": reported_return,
            "discrepancy": discrepancy,
            "error": None if passed else (
                f"Episode aggregation mismatch: reconstructed return ({reconstructed:.6f}) "
                f"differs from reported return ({float(reported_return):.6f}) by {discrepancy:.2e}"
            ),
        }

    @classmethod
    def verify_multi_scenario_score(
        cls,
        scenario_returns: Mapping[str, float],
        reported_suite_return: float | None = None,
    ) -> dict[str, Any]:
        """Verifies multi-scenario score aggregation under official rules (equal weight sum) (Defect 21)."""
        if not scenario_returns:
            return {
                "valid": False,
                "error": "No scenario returns provided for multi-scenario aggregation",
                "total_suite_return": 0.0,
            }

        total_return = float(sum(scenario_returns.values()))
        discrepancy = 0.0
        passed = True

        if reported_suite_return is not None:
            discrepancy = abs(total_return - float(reported_suite_return))
            passed = discrepancy <= cls.PARITY_TOLERANCE

        return {
            "valid": passed,
            "scenario_count": len(scenario_returns),
            "total_suite_return": total_return,
            "discrepancy": discrepancy,
            "error": None if passed else (
                f"Multi-scenario aggregation mismatch: reconstructed sum ({total_return:.6f}) "
                f"differs from reported suite return ({float(reported_suite_return):.6f}) by {discrepancy:.2e}"
            ),
        }

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

        try:
            df = pd.read_csv(path)
        except Exception as e:
            return {
                "valid": False,
                "error": f"Corrupted trace data: failed to parse CSV: {str(e)}",
                "reconstructed_return": None,
            }

        if "step" not in df.columns or "reward" not in df.columns:
            return {
                "valid": False,
                "error": "Corrupted trace data: missing required columns ('step', 'reward')",
                "reconstructed_return": None,
            }

        actual_steps = len(df)
        if actual_steps != expected_steps:
            return {
                "valid": False,
                "error": f"Step count mismatch: got {actual_steps}, expected {expected_steps}",
                "reconstructed_return": None,
                "actual_steps": actual_steps,
            }

        # Monotonicity check
        try:
            step_indices = pd.to_numeric(df["step"], errors="raise").values
        except Exception as e:
            return {
                "valid": False,
                "error": f"Corrupted trace data: non-integer step indices: {str(e)}",
                "reconstructed_return": None,
            }

        if not (step_indices == np.arange(actual_steps)).all():
            return {
                "valid": False,
                "error": "Step indices are non-monotonic or contain gaps/duplicates",
                "reconstructed_return": None,
            }

        # Non-numeric or non-finite reward check
        try:
            reward_vals = pd.to_numeric(df["reward"], errors="raise").values
        except Exception as e:
            return {
                "valid": False,
                "error": f"Corrupted trace data: non-numeric reward values: {str(e)}",
                "reconstructed_return": None,
            }

        if not np.all(np.isfinite(reward_vals)):
            return {
                "valid": False,
                "error": "Trace contains non-finite (NaN / Inf) rewards",
                "reconstructed_return": None,
            }

        reconstructed_return = float(np.sum(reward_vals))

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
            "error": None if parity_passed else (
                f"Discrepancy {discrepancy:.2e} exceeds tolerance {cls.PARITY_TOLERANCE:.2e}"
            ),
        }
