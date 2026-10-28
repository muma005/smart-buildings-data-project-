"""Independent Evaluator and Scoring Auditor for Smart Buildings Challenge.
Reconstructs the competition metric and reward calculations from recorded episode data
without delegating to the official scoring function.
"""

from __future__ import annotations
import math
from typing import Sequence, Mapping, Any
import numpy as np


class IndependentEvaluator:
    """Standalone auditor for calculating scenario returns and leaderboard score."""

    DEFAULT_W_PROD = 0.6
    DEFAULT_W_ENERGY = 0.2
    DEFAULT_W_CARBON = 0.2
    EXPECTED_EPISODE_STEPS = 8640
    COMFORT_WINDOW_K = 5.0

    @staticmethod
    def compute_comfort_shortfall(deviation_k: float, w: float = 5.0) -> float:
        """Piecewise linear/quadratic shortfall f(d)."""
        d = max(0.0, float(deviation_k))
        if d <= w:
            return d / w
        return 1.0 + ((d - w) / w) ** 2

    @classmethod
    def compute_zone_comfort_regret(
        cls,
        deviations_k: Sequence[float],
        occupancies: Sequence[float],
        w: float = 5.0,
    ) -> float:
        """Computes occupancy-weighted comfort regret.
        Returns 0.0 if total occupancy is 0.
        """
        assert len(deviations_k) == len(occupancies), "Deviations and occupancies length mismatch"
        total_occ = sum(occupancies)
        if total_occ <= 0.0:
            return 0.0
        weighted_shortfall = sum(occ * cls.compute_comfort_shortfall(d, w) for d, occ in zip(deviations_k, occupancies))
        return -(weighted_shortfall / total_occ)

    @classmethod
    def compute_step_reward(
        cls,
        norm_productivity_regret: float,
        norm_energy_cost: float,
        norm_carbon_emission: float,
        w_p: float = DEFAULT_W_PROD,
        w_e: float = DEFAULT_W_ENERGY,
        w_c: float = DEFAULT_W_CARBON,
    ) -> float:
        """Combines normalized regret, energy cost, and carbon emissions into step reward."""
        for val, name in [
            (norm_productivity_regret, "productivity_regret"),
            (norm_energy_cost, "energy_cost"),
            (norm_carbon_emission, "carbon_emission"),
        ]:
            if not math.isfinite(val):
                raise ValueError(f"Non-finite value for {name}: {val}")

        raw = norm_productivity_regret * w_p - norm_energy_cost * w_e - norm_carbon_emission * w_c
        return raw / (w_p + w_e + w_c)

    @classmethod
    def compute_scenario_loss(
        cls,
        step_rewards: Sequence[float] | None = None,
        total_reward: float | None = None,
        total_steps: int = EXPECTED_EPISODE_STEPS,
        strict_steps: bool = True,
    ) -> float:
        """Computes single-scenario loss L_s = |(1/N) * sum(r_t)|."""
        if strict_steps and total_steps != cls.EXPECTED_EPISODE_STEPS:
            raise ValueError(
                f"Episode length mismatch: got {total_steps}, expected {cls.EXPECTED_EPISODE_STEPS}"
            )

        if step_rewards is not None:
            if strict_steps and len(step_rewards) != cls.EXPECTED_EPISODE_STEPS:
                raise ValueError(
                    f"Step rewards count mismatch: got {len(step_rewards)}, expected {cls.EXPECTED_EPISODE_STEPS}"
                )
            tot_r = float(np.sum(step_rewards))
            actual_steps = len(step_rewards)
        elif total_reward is not None:
            tot_r = float(total_reward)
            actual_steps = total_steps
        else:
            raise ValueError("Must provide either step_rewards or total_reward")

        if not math.isfinite(tot_r):
            raise ValueError(f"Non-finite total reward: {tot_r}")

        mean_reward = tot_r / actual_steps
        return abs(mean_reward)

    @classmethod
    def compute_leaderboard_score(
        cls,
        scenario_results: Mapping[str, Any],
        expected_scenarios: int | None = 30,
        strict_steps: bool = True,
    ) -> dict[str, Any]:
        """Calculates final competition metric across all scenarios.
        
        Args:
            scenario_results: Mapping of scenario_id -> float (total_reward) OR dict with 'total_reward', 'total_steps'.
            expected_scenarios: Optional expected count of scenarios (e.g. 30).
            strict_steps: Whether to enforce 8640 steps per episode.
            
        Returns:
            Dictionary with 'score', 'scenario_losses', 'scenario_count', and audit status.
        """
        if not scenario_results:
            raise ValueError("Scenario results mapping is empty")

        if expected_scenarios is not None and len(scenario_results) != expected_scenarios:
            raise RuntimeError(
                f"Incomplete scenario set: got {len(scenario_results)} scenarios, expected {expected_scenarios}"
            )

        losses = {}
        for scenario_id, data in scenario_results.items():
            if isinstance(data, dict):
                tot_r = data["total_reward"]
                steps = data.get("total_steps", cls.EXPECTED_EPISODE_STEPS)
            else:
                tot_r = float(data)
                steps = cls.EXPECTED_EPISODE_STEPS
            losses[scenario_id] = cls.compute_scenario_loss(
                total_reward=tot_r, total_steps=steps, strict_steps=strict_steps
            )

        mean_score = float(np.mean(list(losses.values())))
        return {
            "score": mean_score,
            "scenario_count": len(losses),
            "scenario_losses": losses,
            "status": "CERTIFIED",
        }
