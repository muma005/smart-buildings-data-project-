"""Failure Engineering & Red-Team Defect Injection Tests (E2 & Scoring).
Covers Defect Modes 10-25:

Matched Comparisons (10-18):
10. Candidate and baseline use different suite versions.
11. One scenario is missing from a supposedly complete evaluation.
12. Duplicate scenario result.
13. Truncated episode.
14. Different simulator or evaluator versions where compatibility is required.
15. Missing or corrupted trace.
16. Run manifest hash does not match the artifact.
17. Run status says COMPLETE despite incomplete execution.
18. An unverified score is submitted for comparison.

Independent Scoring (19-25):
19. Incorrect step-reward arithmetic.
20. Incorrect episode aggregation.
21. Incorrect multi-scenario aggregation.
22. NaN or infinite reward.
23. Missing or duplicated step.
24. Corrupted trace data.
25. Official-versus-independent score mismatch.

Plus policy adapter / registry invariants and positive controls.
"""

import sys
from pathlib import Path
import pytest
import numpy as np

PHASE_ROOT = Path(__file__).resolve().parents[1]
if str(PHASE_ROOT) not in sys.path:
    sys.path.insert(0, str(PHASE_ROOT))

from core.policy_adapter import PolicyAdapter
from core.registry import ExperimentRegistry, RunStatus
from evaluation.score_verification import ScoreVerifier
from evaluation.comparison_validator import ComparisonValidator


# ==============================================================================
# Helper Mock Policies
# ==============================================================================

class MalformedShapePolicy:
    """Returns wrong shape for continuous action."""
    def __init__(self, building_metadata=None, action_spec=None, **kwargs):
        self.action_spec = action_spec

    def get_action(self, obs):
        return {
            "discrete_action": np.ones((2,), dtype=np.int32),
            "continuous_action": np.zeros((10,), dtype=np.float32),
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


# ==============================================================================
# Low-Level Invariant Tests
# ==============================================================================

def test_fault_invalid_action_shape():
    mock_spec = {
        "discrete_action": np.zeros((2,), dtype=np.int32),
        "continuous_action": np.zeros((8,), dtype=np.float32),
    }
    adapter = PolicyAdapter(MalformedShapePolicy, mock_spec, {})
    with pytest.raises(ValueError, match="continuous_action shape mismatch"):
        adapter.get_action({})


def test_fault_nan_action():
    mock_spec = {
        "discrete_action": np.zeros((2,), dtype=np.int32),
        "continuous_action": np.zeros((8,), dtype=np.float32),
    }
    adapter = PolicyAdapter(NaNActionPolicy, mock_spec, {})
    with pytest.raises(ValueError, match="non-finite"):
        adapter.get_action({})


def test_fault_out_of_range_action_clipping():
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


def test_fault_prevent_run_directory_overwrite(tmp_path):
    registry = ExperimentRegistry(tmp_path)
    run_id, run_dir = registry.create_run(
        experiment_id="TEST",
        policy_name="P",
        scenario_id="b1/a2",
        config_hash="h1",
        policy_hash="h2",
        run_id="RUN_FIXED_TEST_ID",
    )
    with pytest.raises(FileExistsError, match="already exists"):
        registry.create_run(
            experiment_id="TEST",
            policy_name="P",
            scenario_id="b1/a2",
            config_hash="h1",
            policy_hash="h2",
            run_id="RUN_FIXED_TEST_ID",
        )


def test_fault_illegal_state_transition(tmp_path):
    registry = ExperimentRegistry(tmp_path)
    run_id, run_dir = registry.create_run(
        experiment_id="TEST",
        policy_name="P",
        scenario_id="b1/a2",
        config_hash="h1",
        policy_hash="h2",
    )
    registry.update_status(run_dir, RunStatus.FAILED)
    with pytest.raises(ValueError, match="Illegal state transition"):
        registry.update_status(run_dir, RunStatus.COMPLETE)


# ==============================================================================
# Positive Control: Matched Comparison
# ==============================================================================

def _get_valid_eval_pair():
    cand_eval = {
        "suite_name": "official_reference_suite",
        "suite_version": "1.0.0",
        "evaluator_version": "1.0.0",
        "simulator_version": "v1",
        "expected_scenario_count": 30,
        "steps_per_episode": 8640,
        "status": "COMPLETE",
        "all_episodes_valid": True,
        "scores_independently_verified": True,
        "artifact_hash_verified": True,
        "scenario_returns": {f"sc_{i}": -100.0 for i in range(30)},
        "scenario_steps": {f"sc_{i}": 8640 for i in range(30)},
        "total_suite_return": -3000.0,
    }
    base_eval = {
        "suite_name": "official_reference_suite",
        "suite_version": "1.0.0",
        "evaluator_version": "1.0.0",
        "simulator_version": "v1",
        "expected_scenario_count": 30,
        "steps_per_episode": 8640,
        "status": "COMPLETE",
        "all_episodes_valid": True,
        "scores_independently_verified": True,
        "artifact_hash_verified": True,
        "scenario_returns": {f"sc_{i}": -120.0 for i in range(30)},
        "scenario_steps": {f"sc_{i}": 8640 for i in range(30)},
        "total_suite_return": -3600.0,
    }
    return cand_eval, base_eval


def test_positive_matched_comparison_passes():
    cand, base = _get_valid_eval_pair()
    res = ComparisonValidator.validate_comparison(cand, base)
    assert res["valid_comparison"] is True
    assert res["candidate_score"] == pytest.approx(-3000.0)
    assert res["baseline_score"] == pytest.approx(-3600.0)
    assert res["score_delta"] == pytest.approx(600.0)
    assert res["candidate_is_improvement"] is True


# ==============================================================================
# Matched Comparison Defect Modes (Defects 10 - 18)
# ==============================================================================

# --- Defect 10: Candidate and baseline use different suite versions ---
def test_defect_10_different_suite_versions():
    cand, base = _get_valid_eval_pair()
    cand["suite_version"] = "1.1.0"  # Candidate ran on different suite version
    res = ComparisonValidator.validate_comparison(cand, base)
    assert not res["valid_comparison"]
    assert any("Suite version mismatch" in r for r in res["rejection_reasons"])


# --- Defect 11: One scenario is missing from a supposedly complete evaluation ---
def test_defect_11_missing_scenario_in_complete_evaluation():
    cand, base = _get_valid_eval_pair()
    # Remove scenario 29 from candidate (only 29/30)
    del cand["scenario_returns"]["sc_29"]
    del cand["scenario_steps"]["sc_29"]
    cand["total_suite_return"] = sum(cand["scenario_returns"].values())

    res = ComparisonValidator.validate_comparison(cand, base)
    assert not res["valid_comparison"]
    assert any("Candidate incomplete" in r for r in res["rejection_reasons"])
    assert any("Candidate missing scenarios" in r for r in res["rejection_reasons"])


# --- Defect 12: Duplicate scenario result ---
def test_defect_12_duplicate_scenario_result():
    cand, base = _get_valid_eval_pair()
    cand["has_duplicate_scenarios"] = True  # Injected duplicate evaluation result
    res = ComparisonValidator.validate_comparison(cand, base)
    assert not res["valid_comparison"]
    assert any("duplicate scenario results" in r for r in res["rejection_reasons"])


# --- Defect 13: Truncated episode ---
def test_defect_13_truncated_episode():
    cand, base = _get_valid_eval_pair()
    # Scenario 5 only ran 5000 steps instead of required 8640 steps
    cand["scenario_steps"]["sc_5"] = 5000
    res = ComparisonValidator.validate_comparison(cand, base)
    assert not res["valid_comparison"]
    assert any("truncated" in r for r in res["rejection_reasons"])


# --- Defect 14: Different simulator or evaluator versions ---
def test_defect_14_different_simulator_or_evaluator_version():
    cand, base = _get_valid_eval_pair()
    cand["evaluator_version"] = "2.0.0"  # Evaluator version mismatch
    cand["simulator_version"] = "v2"     # Simulator version mismatch
    res = ComparisonValidator.validate_comparison(cand, base)
    assert not res["valid_comparison"]
    assert any("Evaluator version mismatch" in r for r in res["rejection_reasons"])
    assert any("Simulator version mismatch" in r for r in res["rejection_reasons"])


# --- Defect 15: Missing or corrupted trace ---
def test_defect_15_missing_or_corrupted_trace():
    cand, base = _get_valid_eval_pair()
    cand["trace_corrupted"] = True
    res = ComparisonValidator.validate_comparison(cand, base)
    assert not res["valid_comparison"]
    assert any("missing or corrupted trace" in r for r in res["rejection_reasons"])


# --- Defect 16: Run manifest hash does not match the artifact ---
def test_defect_16_manifest_hash_mismatch():
    cand, base = _get_valid_eval_pair()
    cand["artifact_hash_verified"] = False  # Artifact modified post-run!
    res = ComparisonValidator.validate_comparison(cand, base)
    assert not res["valid_comparison"]
    assert any("manifest hash does not match artifact" in r for r in res["rejection_reasons"])


# --- Defect 17: Run status says COMPLETE despite incomplete execution ---
def test_defect_17_claims_complete_despite_incomplete():
    cand, base = _get_valid_eval_pair()
    cand["status"] = "COMPLETE"
    cand["is_incomplete"] = True  # Flag indicating aborted execution marked COMPLETE
    res = ComparisonValidator.validate_comparison(cand, base)
    assert not res["valid_comparison"]
    assert any("claims status COMPLETE despite incomplete" in r for r in res["rejection_reasons"])


# --- Defect 18: An unverified score is submitted for comparison ---
def test_defect_18_unverified_scores_rejected():
    cand, base = _get_valid_eval_pair()
    cand["scores_independently_verified"] = False  # Scores not audited independently!
    res = ComparisonValidator.validate_comparison(cand, base)
    assert not res["valid_comparison"]
    assert any("contains unverified scores" in r for r in res["rejection_reasons"])


# ==============================================================================
# Independent Scoring Defect Modes (Defects 19 - 25)
# ==============================================================================

# --- Defect 19: Incorrect step-reward arithmetic ---
def test_defect_19_incorrect_step_reward_arithmetic():
    # Injected defect: reward calculated by adding instead of subtracting energy cost
    records = [
        {
            "step": 0,
            "normalized_productivity_regret": -0.1,
            "normalized_energy_cost": 0.05,
            "normalized_carbon_emission": 0.02,
            # Correct: 0.6*(-0.1) - 0.2*(0.05) - 0.2*(0.02) = -0.06 - 0.01 - 0.004 = -0.074
            # Defect: Inverted cost sign to +0.05
            "agent_reward": -0.054,
        }
    ]
    res = ScoreVerifier.verify_reward_arithmetic(records)
    assert not res["valid"]
    assert "Step-reward arithmetic mismatch" in res["error"]


# --- Defect 20: Incorrect episode aggregation ---
def test_defect_20_incorrect_episode_aggregation():
    step_rewards = [-0.1, -0.2, -0.3, -0.4]  # sum is -1.0
    # Defect: reported return is fabricated as -0.5
    res = ScoreVerifier.verify_episode_aggregation(step_rewards, reported_return=-0.5)
    assert not res["valid"]
    assert "Episode aggregation mismatch" in res["error"]


# --- Defect 21: Incorrect multi-scenario aggregation ---
def test_defect_21_incorrect_multi_scenario_aggregation():
    scenario_returns = {
        "sc_1": -100.0,
        "sc_2": -150.0,
        "sc_3": -200.0,
    }  # True sum = -450.0
    # Defect: reported return claims -350.0
    res = ScoreVerifier.verify_multi_scenario_score(scenario_returns, reported_suite_return=-350.0)
    assert not res["valid"]
    assert "Multi-scenario aggregation mismatch" in res["error"]


# --- Defect 22: NaN or infinite reward ---
def test_defect_22_nan_or_infinite_reward(tmp_path):
    nan_trace = tmp_path / "nan_trace.csv"
    with open(nan_trace, "w", encoding="utf-8") as f:
        f.write("step,reward\n0,-0.1\n1,NaN\n2,-0.2\n")
    res = ScoreVerifier.verify_trace_and_score(nan_trace, expected_steps=3)
    assert not res["valid"]
    assert "non-finite" in res["error"]

    inf_trace = tmp_path / "inf_trace.csv"
    with open(inf_trace, "w", encoding="utf-8") as f:
        f.write("step,reward\n0,-0.1\n1,inf\n2,-0.2\n")
    res2 = ScoreVerifier.verify_trace_and_score(inf_trace, expected_steps=3)
    assert not res2["valid"]
    assert "non-finite" in res2["error"]


# --- Defect 23: Missing or duplicated step ---
def test_defect_23_missing_or_duplicated_step(tmp_path):
    gap_trace = tmp_path / "gap_trace.csv"
    with open(gap_trace, "w", encoding="utf-8") as f:
        f.write("step,reward\n0,-0.1\n2,-0.2\n")  # Missing step 1
    res = ScoreVerifier.verify_trace_and_score(gap_trace, expected_steps=2)
    assert not res["valid"]
    assert "non-monotonic" in res["error"]

    dup_trace = tmp_path / "dup_trace.csv"
    with open(dup_trace, "w", encoding="utf-8") as f:
        f.write("step,reward\n0,-0.1\n0,-0.1\n")  # Duplicated step 0
    res2 = ScoreVerifier.verify_trace_and_score(dup_trace, expected_steps=2)
    assert not res2["valid"]
    assert "non-monotonic" in res2["error"]


# --- Defect 24: Corrupted trace data ---
def test_defect_24_corrupted_trace_data(tmp_path):
    # Unparseable syntax
    corrupt_trace = tmp_path / "corrupt_data.csv"
    with open(corrupt_trace, "w", encoding="utf-8") as f:
        f.write("step,reward\n0,-0.1\ncorrupted_line_without_numbers\n")
    res = ScoreVerifier.verify_trace_and_score(corrupt_trace, expected_steps=2)
    assert not res["valid"]
    assert "Corrupted trace data" in res["error"]

    # Missing required header
    missing_header_trace = tmp_path / "no_headers.csv"
    with open(missing_header_trace, "w", encoding="utf-8") as f:
        f.write("foo,bar\n0,-0.1\n1,-0.2\n")
    res2 = ScoreVerifier.verify_trace_and_score(missing_header_trace, expected_steps=2)
    assert not res2["valid"]
    assert "missing required columns" in res2["error"]


# --- Defect 25: Official-versus-independent score mismatch ---
def test_defect_25_official_vs_independent_score_mismatch(tmp_path):
    trace_path = tmp_path / "valid_trace.csv"
    with open(trace_path, "w", encoding="utf-8") as f:
        f.write("step,reward\n0,-0.1\n1,-0.2\n")
    # True reconstructed sum is -0.3. Injected official expected return is -0.35 (diff = 0.05 > 1e-6)
    res = ScoreVerifier.verify_trace_and_score(trace_path, expected_steps=2, expected_return=-0.35)
    assert not res["valid"]
    assert "exceeds tolerance" in res["error"]
    assert res["discrepancy"] == pytest.approx(0.05)
