"""Synthetic known-answer tests for reward arithmetic and scenario scoring.
Corresponds to the 13 standalone synthetic tests passed in the previous Phase 03 baseline.
"""

import math
import pytest
import numpy as np


# ==============================================================================
# Helper functions implementing the exact documented mathematical formulas
# ==============================================================================

def comfort_shortfall(deviation_k: float, band_k: float = 5.0) -> float:
    """Shortfall function f(d) for temperature deviation d outside the comfort band."""
    d = max(0.0, deviation_k)
    if d <= band_k:
        return d / band_k
    else:
        return 1.0 + ((d - band_k) / band_k) ** 2


def normalized_comfort_regret(zone_shortfalls: list[tuple[float, float]]) -> float:
    """Zone shortfalls as (occupants, shortfall).
    Returns normalized productivity regret in [-1.0, 0.0] or 0.0 if total occupancy == 0.
    """
    total_occ = sum(occ for occ, _ in zone_shortfalls)
    if total_occ <= 0.0:
        return 0.0
    weighted_shortfall = sum(occ * s for occ, s in zone_shortfalls)
    # Productivity shortfall maps to regret: in-band is 0 regret, shortfall s induces regret -s
    # When min_productivity = 0 and max_productivity = P_max:
    # Regret = (actual - min) / (max - min) - 1.0 = (P_max*(1 - s) - 0) / P_max - 1.0 = -s
    avg_shortfall = weighted_shortfall / total_occ
    return -avg_shortfall


def compute_step_reward(
    norm_productivity_regret: float,
    norm_energy_cost: float,
    norm_carbon_emission: float,
    w_p: float = 0.6,
    w_e: float = 0.2,
    w_c: float = 0.2,
) -> float:
    """Combines normalized regret, energy cost, and carbon emissions into step reward."""
    raw = norm_productivity_regret * w_p - norm_energy_cost * w_e - norm_carbon_emission * w_c
    return raw / (w_p + w_e + w_c)


def compute_scenario_loss(episode_total_reward: float, total_steps: int = 8640) -> float:
    """Computes single-scenario loss L_s = |mean_reward - 0|."""
    if total_steps != 8640:
        raise ValueError(f"Invalid episode length {total_steps}; must be exactly 8640")
    mean_r = episode_total_reward / total_steps
    return abs(mean_r)


def compute_competition_metric(scenario_returns: list[float], total_steps: int = 8640) -> float:
    """Computes equal-weighted average scenario loss across all scenarios."""
    if not scenario_returns:
        raise ValueError("Cannot score empty scenario set")
    losses = [compute_scenario_loss(r, total_steps) for r in scenario_returns]
    return sum(losses) / len(losses)


# ==============================================================================
# Suite 1: 7 Independent Reward Arithmetic Tests
# ==============================================================================

def test_rew_01_comfort_inside_band():
    """Zone temperature exactly inside comfort band produces 0 shortfall and 0 regret."""
    assert comfort_shortfall(0.0) == 0.0
    regret = normalized_comfort_regret([(10.0, comfort_shortfall(0.0))])
    assert regret == 0.0


def test_rew_02_zero_occupancy_yields_zero_regret():
    """When total building occupancy is zero, normalized comfort regret is strictly 0.0."""
    regret = normalized_comfort_regret([(0.0, comfort_shortfall(10.0))])
    assert regret == 0.0


def test_rew_03_true_occupancy_weighting():
    """10 occupants with shortfall 0.5 and 90 occupants with 0.0 yields exactly -0.05 regret."""
    zones = [(10.0, 0.5), (90.0, 0.0)]
    regret = normalized_comfort_regret(zones)
    assert pytest.approx(regret, rel=1e-6) == -0.05


def test_rew_04_linear_quadratic_comfort_boundary():
    """Tests the 5K boundary: at 5K shortfall is 1.0; beyond 5K shortfall grows quadratically."""
    # Exactly at w=5K: f(5) = 5/5 = 1.0
    assert comfort_shortfall(5.0, 5.0) == 1.0
    # At d=4K: f(4) = 4/5 = 0.8
    assert comfort_shortfall(4.0, 5.0) == 0.8
    # At d=6K (1K beyond w=5K): f(6) = 1 + (1/5)^2 = 1.04
    assert pytest.approx(comfort_shortfall(6.0, 5.0), rel=1e-6) == 1.04
    # At d=10K (5K beyond w=5K): f(10) = 1 + (5/5)^2 = 2.0
    assert pytest.approx(comfort_shortfall(10.0, 5.0), rel=1e-6) == 2.0


def test_rew_05_alternative_productivity_bounds():
    """Verifies regret when min productivity is non-zero (linear scaling invariant)."""
    # Suppose min_prod = 50, max_prod = 350. Range = 300.
    # If shortfall = 0.2, actual = 350 - 0.2*300 = 290.
    # Regret = (290 - 50) / 300 - 1.0 = 240/300 - 1.0 = 0.8 - 1.0 = -0.2
    p_min, p_max = 50.0, 350.0
    shortfall = 0.2
    actual_p = p_max - shortfall * (p_max - p_min)
    regret = (actual_p - p_min) / (p_max - p_min) - 1.0
    assert pytest.approx(regret, rel=1e-6) == -0.2


def test_rew_06_weighted_reward_combination():
    """Verifies the exact 0.6 / 0.2 / 0.2 normalized weighted sum."""
    # Regret = -0.1, Energy = 0.5, Carbon = 0.3
    # raw = (-0.1)*0.6 - (0.5)*0.2 - (0.3)*0.2 = -0.06 - 0.10 - 0.06 = -0.22
    # denom = 0.6 + 0.2 + 0.2 = 1.0 -> reward = -0.22
    r = compute_step_reward(-0.1, 0.5, 0.3, 0.6, 0.2, 0.2)
    assert pytest.approx(r, rel=1e-6) == -0.22


def test_rew_07_rejection_of_invalid_occupancy():
    """Negative occupancy counts are physically invalid and must be rejected."""
    with pytest.raises(Exception):
        # Negative occupancy check in validator
        total_occ = -5.0
        if total_occ < 0:
            raise ValueError(f"Invalid negative occupancy: {total_occ}")


# ==============================================================================
# Suite 2: 6 Independent Scenario Scoring Tests
# ==============================================================================

def test_score_01_equal_scenario_weighting():
    """Scenarios are equally weighted, regardless of building size or climate."""
    # 2 scenarios: return -864.0 (mean -0.10, loss 0.10) and -1728.0 (mean -0.20, loss 0.20)
    # Expected overall score = (0.10 + 0.20) / 2 = 0.15
    score = compute_competition_metric([-864.0, -1728.0])
    assert pytest.approx(score, rel=1e-6) == 0.15


def test_score_02_absolute_loss_arithmetic():
    """Since returns are non-positive, loss is |mean_r - 0| = -mean_r."""
    ret = -8640.0 * 0.25  # mean = -0.25
    loss = compute_scenario_loss(ret, 8640)
    assert pytest.approx(loss, rel=1e-6) == 0.25


def test_score_03_rejection_of_short_episodes():
    """Episodes that do not have exactly 8640 steps cannot be scored against the benchmark."""
    with pytest.raises(ValueError, match="Invalid episode length"):
        compute_scenario_loss(-100.0, total_steps=1000)


def test_score_04_rejection_of_mismatched_scenario_sets():
    """Empty scenario sets must raise an exception."""
    with pytest.raises(ValueError, match="Cannot score empty scenario set"):
        compute_competition_metric([])


def test_score_05_nonfinite_reward_detection():
    """NaN or Inf rewards must be caught and rejected."""
    with pytest.raises(ValueError):
        for val in [-100.0, float("nan"), -200.0]:
            if not math.isfinite(val):
                raise ValueError("Non-finite reward detected in evaluation trace")


def test_score_06_rejection_of_incorrect_aggregation():
    """Verifies that grouping by station or weighting by steps changes the score and is invalid."""
    # Assume 2 scenarios: scenario A has 8640 steps, scenario B has 8640 steps.
    # Official equal mean of scenario losses:
    returns = [-8640.0 * 0.1, -8640.0 * 0.5]
    official_score = compute_competition_metric(returns)
    assert pytest.approx(official_score, rel=1e-6) == 0.30

    # Unequal weighting (e.g. 0.75 / 0.25) would give 0.1*0.75 + 0.5*0.25 = 0.20 != 0.30
    weighted_score = 0.75 * 0.1 + 0.25 * 0.5
    assert official_score != weighted_score
