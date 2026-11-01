"""Gate 5 Test Suite: State and Lineage Governance.
Validates:
1. Decoupled physical execution status (RunStatus) vs. evidence validity (EvidenceValidity) (AC 10).
2. Multi-node transitive lineage traversal and quarantine cascade (AC 11).
3. Containment of unrelated results (AC 12).
4. ComparisonValidator rejection of quarantined and invalid inputs.
5. Quarantine lifting and audit log tracking.
6. Formal state transition rejection for illegal transitions.
7. Typed dependency graph attachment and idempotency.
"""

from __future__ import annotations
import json
from pathlib import Path
import sys
import pytest

PHASE_ROOT = Path(__file__).resolve().parents[2] / "04_EXPERIMENT_FOUNDATION"
if str(PHASE_ROOT) not in sys.path:
    sys.path.insert(0, str(PHASE_ROOT))

from core.registry import ExperimentRegistry, RunStatus, EvidenceValidity
from evaluation.comparison_validator import ComparisonValidator


@pytest.fixture
def temp_registry(tmp_path: Path) -> ExperimentRegistry:
    runs_dir = tmp_path / "experiments" / "runs"
    return ExperimentRegistry(base_runs_dir=runs_dir)


def test_decoupled_status_preservation(temp_registry: ExperimentRegistry, tmp_path: Path):
    """AC 10: Quarantining a completed run updates evidence_validity = QUARANTINED

    while leaving execution_status = COMPLETE.
    """
    run_id, run_dir = temp_registry.create_run(
        experiment_id="EXP_DEC",
        policy_name="TransferPolicy",
        scenario_id="building_train_1/atlanta_2",
        config_hash="cfg_hash_1",
        policy_hash="pol_hash_1",
        expected_steps=8640,
    )

    # 1. Simulate complete physical execution
    temp_registry.update_status(run_dir, RunStatus.RUNNING)
    manifest = temp_registry.update_status(run_dir, RunStatus.COMPLETE, actual_steps=8640)
    assert manifest["execution_status"] == RunStatus.COMPLETE.value
    assert manifest["status"] == RunStatus.COMPLETE.value
    assert manifest["evidence_validity"] == EvidenceValidity.UNVERIFIED.value

    # 2. Independent audit marks run as VALID
    manifest = temp_registry.update_evidence_validity(
        run_dir,
        new_validity=EvidenceValidity.VALID,
        reason="Independent verification passed",
    )
    assert manifest["execution_status"] == RunStatus.COMPLETE.value
    assert manifest["evidence_validity"] == EvidenceValidity.VALID.value

    # 3. Governance applies quarantine
    manifest = temp_registry.update_evidence_validity(
        run_dir,
        new_validity=EvidenceValidity.QUARANTINED,
        reason="Upstream baseline tainted",
        taint_source="RUN_BASE_001",
    )

    # Proof for AC 10: execution_status remains COMPLETE, evidence_validity is QUARANTINED
    assert manifest["execution_status"] == "COMPLETE"
    assert manifest["status"] == "COMPLETE"
    assert manifest["evidence_validity"] == "QUARANTINED"
    assert len(manifest["quarantine_history"]) == 1
    assert manifest["quarantine_history"][0]["action"] == "QUARANTINE_APPLIED"
    assert manifest["quarantine_history"][0]["taint_source"] == "RUN_BASE_001"
    assert manifest["quarantine_history"][0]["reason"] == "Upstream baseline tainted"


def test_transitive_lineage_and_containment(temp_registry: ExperimentRegistry):
    """AC 11 & AC 12: Transitive Lineage Traversal and Containment of Unrelated Results.

    Graph:
      Baseline_A -> Candidate_B -> Comparison_D
      Baseline_Z -> Candidate_F (unrelated)
    """
    # 1. Setup Baseline_A
    base_a_id, base_a_dir = temp_registry.create_run(
        experiment_id="EXP_LINEAGE",
        policy_name="BaselinePolicy",
        scenario_id="sc_1",
        config_hash="c1",
        policy_hash="p1",
        run_id="Baseline_A",
    )
    temp_registry.update_status(base_a_dir, RunStatus.RUNNING)
    temp_registry.update_status(base_a_dir, RunStatus.COMPLETE, actual_steps=8640)
    temp_registry.update_evidence_validity(base_a_dir, EvidenceValidity.VALID)

    # 2. Setup Candidate_B depending on Baseline_A
    cand_b_id, cand_b_dir = temp_registry.create_run(
        experiment_id="EXP_LINEAGE",
        policy_name="CandidatePolicyB",
        scenario_id="sc_1",
        config_hash="c1",
        policy_hash="p2",
        run_id="Candidate_B",
        dependencies=[
            {
                "type": "baseline_comparator",
                "target_id": "Baseline_A",
                "role": "control_group",
                "required": True,
            }
        ],
    )
    temp_registry.update_status(cand_b_dir, RunStatus.RUNNING)
    temp_registry.update_status(cand_b_dir, RunStatus.COMPLETE, actual_steps=8640)
    temp_registry.update_evidence_validity(cand_b_dir, EvidenceValidity.VALID)

    # 3. Setup Comparison_D depending on Candidate_B
    comp_d_id, comp_d_dir = temp_registry.create_run(
        experiment_id="EXP_LINEAGE",
        policy_name="ComparisonReportD",
        scenario_id="sc_1",
        config_hash="c1",
        policy_hash="p_comp",
        run_id="Comparison_D",
        dependencies=[
            {
                "type": "candidate_run",
                "target_id": "Candidate_B",
                "role": "treatment_group",
                "required": True,
            },
            {
                "type": "baseline_run",
                "target_id": "Baseline_A",
                "role": "control_group",
                "required": True,
            },
        ],
    )
    temp_registry.update_status(comp_d_dir, RunStatus.RUNNING)
    temp_registry.update_status(comp_d_dir, RunStatus.COMPLETE, actual_steps=8640)
    temp_registry.update_evidence_validity(comp_d_dir, EvidenceValidity.VALID)

    # 4. Setup unrelated Candidate_F depending on Baseline_Z
    cand_f_id, cand_f_dir = temp_registry.create_run(
        experiment_id="EXP_LINEAGE",
        policy_name="CandidatePolicyF",
        scenario_id="sc_1",
        config_hash="c1",
        policy_hash="p3",
        run_id="Candidate_F",
        dependencies=[
            {
                "type": "baseline_comparator",
                "target_id": "Baseline_Z",
                "role": "control_group",
                "required": True,
            }
        ],
    )
    temp_registry.update_status(cand_f_dir, RunStatus.RUNNING)
    temp_registry.update_status(cand_f_dir, RunStatus.COMPLETE, actual_steps=8640)
    temp_registry.update_evidence_validity(cand_f_dir, EvidenceValidity.VALID)

    # 5. Quarantine Baseline_A with cascade=True
    quarantined = temp_registry.quarantine_run(
        run_id="Baseline_A",
        reason="Corrupted baseline weather profile",
        cascade=True,
    )

    # Verify quarantined list contains Baseline_A, Candidate_B, Comparison_D
    assert "Baseline_A" in quarantined
    assert "Candidate_B" in quarantined
    assert "Comparison_D" in quarantined
    assert "Candidate_F" not in quarantined

    # Verify downstream manifests reflect QUARANTINED status
    m_base_a = temp_registry.load_manifest(base_a_dir)
    m_cand_b = temp_registry.load_manifest(cand_b_dir)
    m_comp_d = temp_registry.load_manifest(comp_d_dir)
    m_cand_f = temp_registry.load_manifest(cand_f_dir)

    assert m_base_a["evidence_validity"] == "QUARANTINED"
    assert m_cand_b["evidence_validity"] == "QUARANTINED"
    assert m_comp_d["evidence_validity"] == "QUARANTINED"

    # Verify AC 10 preservation on downstream runs
    assert m_cand_b["execution_status"] == "COMPLETE"
    assert m_cand_b["quarantine_history"][-1]["taint_source"] == "Baseline_A"

    # Verify AC 12: Candidate_F remains VALID and completely unaffected
    assert m_cand_f["evidence_validity"] == "VALID"
    assert m_cand_f["execution_status"] == "COMPLETE"
    assert len(m_cand_f["quarantine_history"]) == 0


def test_comparison_rejection_on_quarantined_and_invalid():
    """ComparisonValidator rejects comparisons involving QUARANTINED or INVALID runs."""
    valid_cand = {
        "suite_name": "official_reference_suite",
        "suite_version": "1.0.0",
        "evaluator_version": "1.0.0",
        "simulator_version": "v1",
        "status": "COMPLETE",
        "expected_scenario_count": 2,
        "scenario_returns": {"sc_1": -100.0, "sc_2": -150.0},
        "scenario_steps": {"sc_1": 8640, "sc_2": 8640},
        "total_suite_return": -250.0,
        "all_episodes_valid": True,
        "scores_independently_verified": True,
        "evidence_validity": "VALID",
    }
    valid_base = {
        "suite_name": "official_reference_suite",
        "suite_version": "1.0.0",
        "evaluator_version": "1.0.0",
        "simulator_version": "v1",
        "status": "COMPLETE",
        "expected_scenario_count": 2,
        "scenario_returns": {"sc_1": -200.0, "sc_2": -250.0},
        "scenario_steps": {"sc_1": 8640, "sc_2": 8640},
        "total_suite_return": -450.0,
        "all_episodes_valid": True,
        "scores_independently_verified": True,
        "evidence_validity": "VALID",
    }

    # Clean control pair passes
    res_clean = ComparisonValidator.validate_comparison(valid_cand, valid_base)
    assert res_clean["valid_comparison"] is True
    assert res_clean["candidate_is_improvement"] is True

    # 1. Quarantined Candidate rejected
    cand_quarantined = dict(valid_cand, evidence_validity="QUARANTINED")
    res1 = ComparisonValidator.validate_comparison(cand_quarantined, valid_base)
    assert res1["valid_comparison"] is False
    assert any("Candidate evidence validity is QUARANTINED" in r for r in res1["rejection_reasons"])

    # 2. Quarantined Baseline rejected
    base_quarantined = dict(valid_base, evidence_validity="QUARANTINED")
    res2 = ComparisonValidator.validate_comparison(valid_cand, base_quarantined)
    assert res2["valid_comparison"] is False
    assert any("Baseline evidence validity is QUARANTINED" in r for r in res2["rejection_reasons"])

    # 3. Invalid Candidate rejected
    cand_invalid = dict(valid_cand, evidence_validity="INVALID")
    res3 = ComparisonValidator.validate_comparison(cand_invalid, valid_base)
    assert res3["valid_comparison"] is False
    assert any("Candidate evidence validity is INVALID" in r for r in res3["rejection_reasons"])


def test_comparison_rejection_via_run_manifest(tmp_path: Path):
    """ComparisonValidator inspects run_dir and rejects when run_manifest is quarantined."""
    cand_dir = tmp_path / "cand_run"
    cand_dir.mkdir()
    cand_manifest = {
        "run_id": "CAND_RUN",
        "execution_status": "COMPLETE",
        "status": "COMPLETE",
        "evidence_validity": "QUARANTINED",
    }
    with open(cand_dir / "run_manifest.json", "w", encoding="utf-8") as f:
        json.dump(cand_manifest, f)

    cand_eval = {
        "suite_name": "official_reference_suite",
        "suite_version": "1.0.0",
        "evaluator_version": "1.0.0",
        "simulator_version": "v1",
        "status": "COMPLETE",
        "expected_scenario_count": 1,
        "scenario_returns": {"sc_1": -100.0},
        "scenario_steps": {"sc_1": 8640},
        "total_suite_return": -100.0,
        "all_episodes_valid": True,
        "scores_independently_verified": True,
        "run_dir": str(cand_dir),
    }
    base_eval = {
        "suite_name": "official_reference_suite",
        "suite_version": "1.0.0",
        "evaluator_version": "1.0.0",
        "simulator_version": "v1",
        "status": "COMPLETE",
        "expected_scenario_count": 1,
        "scenario_returns": {"sc_1": -200.0},
        "scenario_steps": {"sc_1": 8640},
        "total_suite_return": -200.0,
        "all_episodes_valid": True,
        "scores_independently_verified": True,
        "evidence_validity": "VALID",
    }

    res = ComparisonValidator.validate_comparison(cand_eval, base_eval)
    assert res["valid_comparison"] is False
    assert any("Candidate evidence validity is QUARANTINED" in r for r in res["rejection_reasons"])


def test_quarantine_lifting(temp_registry: ExperimentRegistry):
    """Lifting quarantine restores VALID eligibility and appends QUARANTINE_LIFTED to audit log."""
    run_id, run_dir = temp_registry.create_run(
        experiment_id="EXP_LIFT",
        policy_name="TestPolicy",
        scenario_id="sc_1",
        config_hash="c1",
        policy_hash="p1",
        run_id="Run_To_Lift",
    )
    temp_registry.update_status(run_dir, RunStatus.RUNNING)
    temp_registry.update_status(run_dir, RunStatus.COMPLETE, actual_steps=8640)
    temp_registry.update_evidence_validity(run_dir, EvidenceValidity.VALID)

    # Quarantine
    temp_registry.quarantine_run("Run_To_Lift", reason="Pending investigation")
    m1 = temp_registry.load_manifest(run_dir)
    assert m1["evidence_validity"] == "QUARANTINED"

    # Lift
    lifted = temp_registry.lift_quarantine("Run_To_Lift", reason="Investigation completed: baseline confirmed valid")
    assert "Run_To_Lift" in lifted

    m2 = temp_registry.load_manifest(run_dir)
    assert m2["evidence_validity"] == "VALID"
    assert m2["execution_status"] == "COMPLETE"
    assert len(m2["quarantine_history"]) == 2
    assert m2["quarantine_history"][1]["action"] == "QUARANTINE_LIFTED"
    assert "Investigation completed" in m2["quarantine_history"][1]["reason"]


def test_invalid_state_transition_rejection(temp_registry: ExperimentRegistry):
    """Enforces strict state transitions: terminal states cannot transition to VALID."""
    run_id, run_dir = temp_registry.create_run(
        experiment_id="EXP_FSM",
        policy_name="TestPolicy",
        scenario_id="sc_1",
        config_hash="c1",
        policy_hash="p1",
    )

    # Transition to INVALID
    temp_registry.update_evidence_validity(run_dir, EvidenceValidity.INVALID, reason="Corrupted chunk header")
    m = temp_registry.load_manifest(run_dir)
    assert m["evidence_validity"] == "INVALID"

    # Attempt illegal INVALID -> VALID transition
    with pytest.raises(ValueError, match="Illegal evidence validity transition"):
        temp_registry.update_evidence_validity(run_dir, EvidenceValidity.VALID)

    # Attempt illegal INVALID -> QUARANTINED transition
    with pytest.raises(ValueError, match="Illegal evidence validity transition"):
        temp_registry.update_evidence_validity(run_dir, EvidenceValidity.QUARANTINED)


def test_typed_dependencies_management(temp_registry: ExperimentRegistry):
    """Tests add_dependency typed graph construction and idempotency."""
    run_id, run_dir = temp_registry.create_run(
        experiment_id="EXP_DEPS",
        policy_name="TransferPolicy",
        scenario_id="sc_1",
        config_hash="c1",
        policy_hash="p1",
    )

    # Add dependencies
    temp_registry.add_dependency(
        run_dir,
        dep_type="baseline_comparator",
        target_id="RUN_BASE_001",
        role="control_group",
        required=True,
    )
    temp_registry.add_dependency(
        run_dir,
        dep_type="policy_artifact",
        target_id="POL_TRANSFER_V1",
        role="controller",
        required=True,
    )

    m = temp_registry.load_manifest(run_dir)
    assert len(m["dependencies"]) == 2
    assert m["dependencies"][0]["type"] == "baseline_comparator"
    assert m["dependencies"][0]["target_id"] == "RUN_BASE_001"
    assert m["dependencies"][1]["type"] == "policy_artifact"

    # Test idempotency (re-adding same type & target_id updates without duplication)
    temp_registry.add_dependency(
        run_dir,
        dep_type="baseline_comparator",
        target_id="RUN_BASE_001",
        role="updated_role",
        required=False,
    )
    m_updated = temp_registry.load_manifest(run_dir)
    assert len(m_updated["dependencies"]) == 2
    assert m_updated["dependencies"][0]["role"] == "updated_role"
    assert m_updated["dependencies"][0]["required"] is False
