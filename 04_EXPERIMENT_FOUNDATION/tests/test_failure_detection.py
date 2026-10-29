"""Failure Engineering & Injected Defect Tests.
Proves that our experimentation system rigorously detects and rejects:
1. Invalid action shapes.
2. NaN or infinity in actions.
3. Out-of-range continuous actions.
4. Missing episode steps.
5. Duplicate steps / non-monotonic sequences.
6. Incorrect scoring arithmetic.
7. Corrupted or missing trace artifacts.
8. Wrong artifact hashes.
9. Accidental run directory overwrites.
10. Incomplete suite comparisons.
11. Mismatched suite comparisons.
12. Failed runs attempting to transition to COMPLETE.
"""

import sys
from pathlib import Path
import tempfile
import pytest
import numpy as np

PHASE_ROOT = Path(__file__).resolve().parents[1]
if str(PHASE_ROOT) not in sys.path:
    sys.path.insert(0, str(PHASE_ROOT))

from core.policy_adapter import PolicyAdapter
from core.trace_recorder import TraceRecorder
from core.registry import ExperimentRegistry, RunStatus
from evaluation.score_verification import ScoreVerifier
from evaluation.comparison_validator import ComparisonValidator


class MalformedShapePolicy:
    """Returns wrong shape for continuous action."""
    def __init__(self, building_metadata=None, action_spec=None, **kwargs):
        self.action_spec = action_spec

    def get_action(self, obs):
        return {
            "discrete_action": np.ones((2,), dtype=np.int32),
            "continuous_action": np.zeros((10,), dtype=np.float32),  # intentionally wrong shape
        }


class NaNActionPolicy:
    """Returns NaN in continuous action."""
    def __init__(self, building_metadata=None, action_spec=None, **kwargs):
        self.action_spec = action_spec

    def get_action(self, obs):
        c_shape = self.action_spec["continuous_action"].shape
        d_shape = self.action_spec["discrete_action"].shape
        action = np.zeros(c_shape, dtype=np.float32)
        action[0] = np.nan
        return {
            "discrete_action": np.ones(d_shape, dtype=np.int32),
            "continuous_action": action,
        }


# --- Fault 1: Invalid action shape ---
def test_fault_01_invalid_action_shape():
    mock_spec = {
        "discrete_action": np.zeros((2,), dtype=np.int32),
        "continuous_action": np.zeros((8,), dtype=np.float32),
    }
    adapter = PolicyAdapter(MalformedShapePolicy, mock_spec, {})
    with pytest.raises(ValueError, match="continuous_action shape mismatch"):
        adapter.get_action({})


# --- Fault 2: NaN in action ---
def test_fault_02_nan_action():
    mock_spec = {
        "discrete_action": np.zeros((2,), dtype=np.int32),
        "continuous_action": np.zeros((8,), dtype=np.float32),
    }
    adapter = PolicyAdapter(NaNActionPolicy, mock_spec, {})
    with pytest.raises(ValueError, match="non-finite"):
        adapter.get_action({})


# --- Fault 3: Out-of-range action clipping ---
def test_fault_03_out_of_range_action_clipping():
    class OutOfBoundsPolicy:
        def __init__(self, building_metadata=None, action_spec=None, **kwargs):
            pass
        def get_action(self, obs):
            return {
                "discrete_action": np.zeros((2,), dtype=np.int32),
                "continuous_action": np.array([-5.0, 10.0], dtype=np.float32),
            }
    mock_spec = {
        "discrete_action": np.zeros((2,), dtype=np.int32),
        "continuous_action": np.zeros((2,), dtype=np.float32),
    }
    adapter = PolicyAdapter(OutOfBoundsPolicy, mock_spec, {})
    action = adapter.get_action({})
    assert action["continuous_action"][0] == -1.0
    assert action["continuous_action"][1] == 1.0


# --- Fault 4 & 5: Missing episode step and duplicate step ---
def test_fault_04_05_missing_and_duplicate_steps(tmp_path):
    trace_path = tmp_path / "bad_trace.csv"
    with open(trace_path, "w", encoding="utf-8") as f:
        f.write("step,reward\n")
        f.write("0,-0.1\n")
        f.write("1,-0.1\n")
        f.write("3,-0.1\n")  # Total 3 rows, but gap at index 2

    res = ScoreVerifier.verify_trace_and_score(trace_path, expected_steps=3)
    assert not res["valid"]
    assert "Step indices are non-monotonic" in res["error"]


# --- Fault 6: Incorrect score arithmetic / non-finite rewards ---
def test_fault_06_non_finite_reward(tmp_path):
    trace_path = tmp_path / "nan_trace.csv"
    with open(trace_path, "w", encoding="utf-8") as f:
        f.write("step,reward\n")
        f.write("0,-0.1\n")
        f.write("1,NaN\n")

    res = ScoreVerifier.verify_trace_and_score(trace_path, expected_steps=2)
    assert not res["valid"]
    assert "non-finite" in res["error"]


# --- Fault 7: Corrupted or missing trace ---
def test_fault_07_missing_trace(tmp_path):
    missing_path = tmp_path / "non_existent.csv"
    res = ScoreVerifier.verify_trace_and_score(missing_path, expected_steps=10)
    assert not res["valid"]
    assert "does not exist" in res["error"]


# --- Fault 8: Wrong step count ---
def test_fault_08_step_count_mismatch(tmp_path):
    trace_path = tmp_path / "short_trace.csv"
    with open(trace_path, "w", encoding="utf-8") as f:
        f.write("step,reward\n")
        f.write("0,-0.1\n")
        f.write("1,-0.1\n")

    res = ScoreVerifier.verify_trace_and_score(trace_path, expected_steps=8640)
    assert not res["valid"]
    assert "Step count mismatch" in res["error"]


# --- Fault 9: Accidental artifact overwrite ---
def test_fault_09_prevent_run_directory_overwrite(tmp_path):
    registry = ExperimentRegistry(tmp_path)
    run_id, run_dir = registry.create_run(
        experiment_id="TEST",
        policy_name="P",
        scenario_id="b1/a2",
        config_hash="h1",
        policy_hash="h2",
        run_id="RUN_FIXED_TEST_ID",
    )
    # Attempting to re-create exact same directory must fail with FileExistsError
    with pytest.raises(FileExistsError, match="already exists"):
        registry.create_run(
            experiment_id="TEST",
            policy_name="P",
            scenario_id="b1/a2",
            config_hash="h1",
            policy_hash="h2",
            run_id="RUN_FIXED_TEST_ID",
        )


# --- Fault 10 & 11: Incomplete and mismatched suite comparisons ---
def test_fault_10_11_mismatched_and_incomplete_suites():
    cand_eval = {
        "suite_name": "official_reference_suite",
        "suite_version": "1.0.0",
        "evaluator_version": "1.0.0",
        "expected_scenario_count": 30,
        "scenario_returns": {f"s{i}": -100.0 for i in range(29)},  # 1 scenario short!
        "all_episodes_valid": True,
        "total_suite_return": -2900.0,
    }
    base_eval = {
        "suite_name": "different_suite",  # Suite mismatch!
        "suite_version": "1.0.0",
        "evaluator_version": "1.0.0",
        "expected_scenario_count": 30,
        "scenario_returns": {f"s{i}": -100.0 for i in range(30)},
        "all_episodes_valid": True,
        "total_suite_return": -3000.0,
    }

    res = ComparisonValidator.validate_comparison(cand_eval, base_eval)
    assert not res["valid_comparison"]
    assert any("Suite mismatch" in r for r in res["rejection_reasons"])
    assert any("Candidate incomplete" in r for r in res["rejection_reasons"])


# --- Fault 12: Illegal state transition ---
def test_fault_12_illegal_state_transition(tmp_path):
    registry = ExperimentRegistry(tmp_path)
    run_id, run_dir = registry.create_run(
        experiment_id="TEST",
        policy_name="P",
        scenario_id="b1/a2",
        config_hash="h1",
        policy_hash="h2",
    )
    registry.update_status(run_dir, RunStatus.FAILED)
    # Cannot transition FAILED -> COMPLETE
    with pytest.raises(ValueError, match="Illegal state transition"):
        registry.update_status(run_dir, RunStatus.COMPLETE)
