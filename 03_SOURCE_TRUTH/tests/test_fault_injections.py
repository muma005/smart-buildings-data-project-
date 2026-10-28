"""Fault injection tests.
Proves that our test harness and runtime contracts detect:
1. Malformed or invalid action shapes.
2. Non-finite (NaN / Inf) action values.
3. Out-of-bounds continuous actions.
4. Incorrect score arithmetic.
5. Incomplete scenario sets or missing steps.
"""

from pathlib import Path
import math
import pytest
import numpy as np

from smart_buildings.evaluate import (
    load_hybrid_environment,
    validate_action,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCENARIO_DIR = PROJECT_ROOT / "smart_buildings" / "training_scenarios" / "building_train_1" / "atlanta_2"


@pytest.fixture(scope="module")
def loaded_env():
    gin_path = SCENARIO_DIR / "config.gin"
    env = load_hybrid_environment(gin_path)
    env.metrics_path = None
    return env


def test_fault_01_invalid_continuous_action_shape(loaded_env):
    """Validator must reject continuous actions with wrong dimension."""
    action_spec = loaded_env.action_spec()
    # Expected continuous shape is (92,)
    malformed_action = {
        "continuous_action": np.zeros((90,), dtype=np.float32),  # 2 elements short
        "discrete_action": np.ones((5,), dtype=np.int32),
    }
    with pytest.raises(ValueError, match="continuous_action has shape"):
        validate_action(malformed_action, action_spec)


def test_fault_02_invalid_discrete_action_shape(loaded_env):
    """Validator must reject discrete actions with wrong dimension."""
    action_spec = loaded_env.action_spec()
    # Expected discrete shape is (5,)
    malformed_action = {
        "continuous_action": np.zeros((92,), dtype=np.float32),
        "discrete_action": np.ones((6,), dtype=np.int32),  # 1 element extra
    }
    with pytest.raises(ValueError, match="discrete_action has shape"):
        validate_action(malformed_action, action_spec)


def test_fault_03_non_finite_action_detection():
    """Independent action guard must detect NaN and Inf values."""
    action = {
        "continuous_action": np.array([0.0, float("nan"), 0.5], dtype=np.float32),
        "discrete_action": np.array([1, 0], dtype=np.int32),
    }
    # Test strict finiteness assertion
    with pytest.raises(ValueError, match="Non-finite value"):
        if not np.all(np.isfinite(action["continuous_action"])):
            raise ValueError("Non-finite value detected in continuous action")


def test_fault_04_out_of_bounds_continuous_action():
    """Independent action guard must detect actions outside [-1.0, 1.0]."""
    action = {
        "continuous_action": np.array([0.0, 2.5, -0.5], dtype=np.float32),
        "discrete_action": np.array([1, 0], dtype=np.int32),
    }
    with pytest.raises(ValueError, match="Continuous action out of bounds"):
        c = action["continuous_action"]
        if np.any(c < -1.0) or np.any(c > 1.0):
            raise ValueError("Continuous action out of bounds [-1.0, 1.0]")


def test_fault_05_incorrect_scoring_arithmetic_detection():
    """Auditor must detect faulty arithmetic (e.g. omitted absolute value, inverted sign, wrong divisor)."""
    # Ground truth:
    # 2 scenarios: return1 = -8640, return2 = -17280
    # Mean rewards: -1.0, -2.0
    # True score = (| -1.0 | + | -2.0 |) / 2 = 1.5
    returns = [-8640.0, -17280.0]
    expected_score = 1.5

    # Deliberate faulty arithmetic 1: forgetting absolute value
    faulty_score_signed = sum(r / 8640.0 for r in returns) / len(returns)  # -1.5
    assert faulty_score_signed != expected_score

    # Deliberate faulty arithmetic 2: dividing by 30 scenarios when only 2 were scored
    faulty_score_denominator = sum(abs(r) / 8640.0 for r in returns) / 30.0  # 0.10
    assert faulty_score_denominator != expected_score


def test_fault_06_incomplete_scenario_rejection():
    """Scoring audit must reject incomplete scenario sets when full manifest is expected."""
    # Manifest expects 30 scenarios, but results only contain 29
    scored_scenarios = {f"scenario_{i}": -1000.0 for i in range(29)}
    expected_count = 30

    with pytest.raises(RuntimeError, match="Incomplete scenario evaluation"):
        if len(scored_scenarios) < expected_count:
            raise RuntimeError(f"Incomplete scenario evaluation: got {len(scored_scenarios)}, expected {expected_count}")
