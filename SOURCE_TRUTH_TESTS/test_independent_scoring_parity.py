"""Scoring parity tests between IndependentEvaluator and official baseline returns.
Verifies that the independent evaluator produces bitwise or within-tolerance (< 1e-6)
parity with official competition leaderboard scores.
"""

from pathlib import Path
import json
import pytest
import numpy as np

from SOURCE_TRUTH_TESTS.independent_evaluator import IndependentEvaluator

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BASELINE_JSON_PATH = PROJECT_ROOT / "starter_kit_pinned" / "baseline_returns.json"


@pytest.fixture(scope="module")
def baseline_returns():
    assert BASELINE_JSON_PATH.is_file(), f"Missing {BASELINE_JSON_PATH}"
    with open(BASELINE_JSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def test_parity_official_baselines_count(baseline_returns):
    """Verifies baseline_returns.json has exactly 30 scenarios."""
    assert len(baseline_returns) == 30


@pytest.mark.parametrize("policy_name", ["bang_bang", "fixed_setpoint", "pid", "pid_water"])
def test_parity_independent_scorer_matches_official_formula(baseline_returns, policy_name):
    """For each baseline policy, independent evaluation matches official score_leaderboard.py."""
    # Extract returns for this baseline
    policy_returns = {
        scenario_id: data[policy_name]
        for scenario_id, data in baseline_returns.items()
    }

    # Independent calculation
    audit_result = IndependentEvaluator.compute_leaderboard_score(
        policy_returns, expected_scenarios=30, strict_steps=True
    )
    indep_score = audit_result["score"]

    # Official calculation: sum(abs(r) / 8640) / len(rows)
    official_losses = [abs(r) / 8640.0 for r in policy_returns.values()]
    official_score = sum(official_losses) / len(official_losses)

    # Parity check: difference must be < 1e-12
    assert pytest.approx(indep_score, abs=1e-12) == official_score
    print(f"Policy: {policy_name:15} | Score: {indep_score:.6f} | Delta: {abs(indep_score - official_score):.2e}")


def test_parity_incomplete_detection(baseline_returns):
    """Independent evaluator rejects 29 scenarios when 30 are expected."""
    subset = {k: v["pid"] for i, (k, v) in enumerate(baseline_returns.items()) if i < 29}
    with pytest.raises(RuntimeError, match="Incomplete scenario set"):
        IndependentEvaluator.compute_leaderboard_score(subset, expected_scenarios=30)
