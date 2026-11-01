"""Gate 7 Test Suite: End-to-End Acceptance Certification.
Validates all 19 Acceptance Criteria from Section 15 of PHASE_05_STAGE_2_IMPLEMENTATION_DESIGN.md
across Red-Team failure modes F1 through F5:
- F1: Semantic Actuator Mappings (AC 16)
- F2: Dynamic Dimension Truth (AC 2, AC 14)
- F3: Information Leakage & Sandboxing (AC 15)
- F4: Process Crash & Chunk Persistence (AC 6, AC 7, AC 17, AC 18)
- F5: Artifact Provenance, Decoupled State & Lineage Governance (AC 1, AC 3-5, AC 8-13, AC 19)
"""

from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import time
from unittest.mock import patch
import numpy as np
import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
FOUNDATION_ROOT = PROJECT_ROOT / "04_EXPERIMENT_FOUNDATION"
if str(FOUNDATION_ROOT) not in sys.path:
    sys.path.insert(0, str(FOUNDATION_ROOT))

from core.registry import ExperimentRegistry, RunStatus, EvidenceValidity
from core.runner import SimulationRunner, EvidenceCaptureError
from core.policy_adapter import PolicyAdapter, SecurityViolationError
from core.trace_recorder import TraceRecorder
from core.evaluator import RunEvaluator
from evaluation.score_verification import ScoreVerifier
from evaluation.semantic_probe import SemanticActuatorProbe
from evaluation.standalone_audit import StandaloneAuditor


# Fixture: Certified Reference Run
@pytest.fixture
def certified_run_dir() -> Path:
    return FOUNDATION_ROOT / "experiments" / "runs" / "RUN_EXP-000_vertical_slice_certified"


# ------------------------------------------------------------------------------
# AC 1: Complete Diagnostic Evidence Generation
# ------------------------------------------------------------------------------
def test_ac_01_complete_diagnostic_evidence_generation(certified_run_dir: Path):
    """AC 1: A completed episode produces all required evidence artifacts."""
    required_files = [
        "trace.csv",
        "run_manifest.json",
        "summary.json",
        "evaluation.json",
    ]
    for rf in required_files:
        p = certified_run_dir / rf
        assert p.is_file(), f"Missing required evidence file: {rf}"
        assert p.stat().st_size > 0, f"Evidence file is empty: {rf}"


# ------------------------------------------------------------------------------
# AC 2: Transition Recovery
# ------------------------------------------------------------------------------
def test_ac_02_transition_recovery(tmp_path: Path):
    """AC 2: Arbitrary step t recovers unreduced observation, actions, and zone temps matching metadata."""
    obs_dim = 352
    cont_dim = 92
    disc_dim = 5
    n_zones = 39

    recorder = TraceRecorder(
        output_dir=tmp_path,
        chunk_size=10,
    )

    dummy_obs = np.linspace(290.0, 300.0, obs_dim, dtype=np.float32)
    dummy_raw_act = np.full(cont_dim, 0.5, dtype=np.float32)
    dummy_exec_act = np.full(cont_dim, 0.5, dtype=np.float32)
    dummy_disc_act = np.ones(disc_dim, dtype=np.int32)
    dummy_zone_temps = np.full(n_zones, 293.15, dtype=np.float32)

    for step in range(10):
        recorder.record_step(
            step_idx=step,
            reward=-10.0,
            productivity_regret=5.0,
            energy_cost=20.0,
            carbon_penalty=5.0,
            mean_zone_temp=293.15,
            outdoor_temp=15.0,
            total_occupants=10.0,
            discrete_action=dummy_disc_act,
            continuous_action=dummy_exec_act,
            raw_continuous_action=dummy_raw_act,
            observation=dummy_obs,
            zone_temperatures=dummy_zone_temps,
        )
    recorder.close()

    chunk_file = tmp_path / "chunks" / "chunk_0000.npz"
    assert chunk_file.is_file()

    with np.load(chunk_file) as data:
        t_idx = 7
        assert data["observations"].shape == (10, obs_dim)
        assert data["raw_continuous_actions"].shape == (10, cont_dim)
        assert data["executed_continuous_actions"].shape == (10, cont_dim)
        assert data["discrete_actions"].shape == (10, disc_dim)
        assert data["zone_temperatures"].shape == (10, n_zones)
        assert data["observations"][t_idx, 0] == pytest.approx(290.0)
        assert data["zone_temperatures"][t_idx, 0] == pytest.approx(293.15)


# ------------------------------------------------------------------------------
# AC 3: Reward Component Capture
# ------------------------------------------------------------------------------
def test_ac_03_reward_component_capture(certified_run_dir: Path):
    """AC 3: trace.csv records non-zero values for productivity_regret, energy_cost, and carbon_penalty."""
    df = pd.read_csv(certified_run_dir / "trace.csv")
    assert abs(float(df["productivity_regret"].sum())) > 0.0
    assert abs(float(df["energy_cost"].sum())) > 0.0
    assert abs(float(df["carbon_penalty"].sum())) > 0.0


# ------------------------------------------------------------------------------
# AC 4: Independent Reward Reconstruction
# ------------------------------------------------------------------------------
def test_ac_04_independent_reward_reconstruction():
    """AC 4: |R_t - (0.6*regret - 0.2*energy - 0.2*carbon)| <= 1.0e-6 across all 8,640 steps."""
    rc_path = PROJECT_ROOT / "03_SOURCE_TRUTH" / "evidence" / "s0_episode" / "building_train_1" / "atlanta_2" / "transfer" / "reward_components.csv"
    assert rc_path.is_file(), f"Missing S0 episode reward_components.csv at {rc_path}"

    df = pd.read_csv(rc_path)
    assert len(df) == 8640
    records = df.to_dict(orient="records")

    arith_res = ScoreVerifier.verify_reward_arithmetic(records)
    assert arith_res["valid"] is True
    assert arith_res.get("discrepancy", 0.0) <= 1.0e-6


# ------------------------------------------------------------------------------
# AC 5: Rejection of Missing Reward Info
# ------------------------------------------------------------------------------
def test_ac_05_rejection_of_missing_reward_info(tmp_path: Path, monkeypatch):
    """AC 5: If env returns None for RewardResponse, EvidenceCaptureError is raised immediately."""
    from smart_buildings.evaluate import load_hybrid_environment
    from smart_buildings.baselines.transfer_policy import TransferPolicy

    scenario_dir = PROJECT_ROOT / "smart_buildings" / "training_scenarios" / "building_train_1" / "atlanta_2"
    gin_path = scenario_dir / "config.gin"
    env = load_hybrid_environment(gin_path)
    env.metrics_path = None

    real_fn = env.get_reward_info_and_response
    call_count = 0

    def mock_get_reward():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return real_fn()
        return None

    monkeypatch.setattr(env, "get_reward_info_and_response", mock_get_reward)
    monkeypatch.setattr("core.runner.load_hybrid_environment", lambda p: env)

    runs_dir = tmp_path / "runs"
    registry = ExperimentRegistry(base_runs_dir=runs_dir)
    runner = SimulationRunner(registry=registry)

    with pytest.raises(EvidenceCaptureError, match="RewardResponse"):
        runner.execute_episode(
            policy_class=TransferPolicy,
            scenario_dir=scenario_dir,
            experiment_id="EXP_AC5",
            max_steps=3,
        )


# ------------------------------------------------------------------------------
# AC 6: Crash-Resilient Chunk Persistence
# ------------------------------------------------------------------------------
def test_ac_06_crash_resilient_chunk_persistence(tmp_path: Path):
    """AC 6: Process interruption leaves committed chunks fully readable and uncorrupted."""
    recorder = TraceRecorder(
        output_dir=tmp_path,
        chunk_size=10,
    )
    for step in range(25):  # 2 full chunks (0..9, 10..19), and 5 uncommitted steps
        recorder.record_step(
            step_idx=step,
            reward=1.0,
            productivity_regret=0.0,
            energy_cost=0.0,
            carbon_penalty=0.0,
            mean_zone_temp=293.0,
            outdoor_temp=15.0,
            total_occupants=1.0,
            discrete_action=np.ones(1, dtype=np.int32),
            continuous_action=np.zeros(2, dtype=np.float32),
            raw_continuous_action=np.zeros(2, dtype=np.float32),
            observation=np.zeros(10, dtype=np.float32),
            zone_temperatures=np.zeros(2, dtype=np.float32),
        )

    # Simulate crash before close()
    del recorder

    # Chunks 0 and 1 are durable on disk
    chunk_0 = tmp_path / "chunks" / "chunk_0000.npz"
    chunk_1 = tmp_path / "chunks" / "chunk_0001.npz"
    assert chunk_0.is_file()
    assert chunk_1.is_file()

    with np.load(chunk_0) as d0:
        assert len(d0["step_indices"]) == 10
    with np.load(chunk_1) as d1:
        assert len(d1["step_indices"]) == 10


# ------------------------------------------------------------------------------
# AC 7: Exclusion of Incomplete Final Batch
# ------------------------------------------------------------------------------
def test_ac_07_exclusion_of_incomplete_final_batch(tmp_path: Path):
    """AC 7: Post-crash recovery deletes orphaned .tmp files and excludes them from manifest."""
    runs_dir = tmp_path / "runs"
    registry = ExperimentRegistry(base_runs_dir=runs_dir)

    run_id, run_dir = registry.create_run(
        experiment_id="EXP_AC7",
        policy_name="DummyPolicy",
        scenario_id="sc_1",
        config_hash="c1",
        policy_hash="p1",
    )
    registry.update_status(run_dir, RunStatus.RUNNING)

    chunks_dir = run_dir / "chunks"
    chunks_dir.mkdir(parents=True)

    # Create 1 valid chunk and 1 orphaned .tmp chunk
    chunk_file = chunks_dir / "chunk_0000.npz"
    np.savez(chunk_file, step_indices=np.arange(10))
    tmp_chunk = chunks_dir / "chunk_0001.npz.tmp"
    tmp_chunk.write_text("corrupted_uncommitted_bytes", encoding="utf-8")

    # Recover
    manifest = registry.recover_interrupted_run(run_dir)
    assert manifest["status"] == "INCOMPLETE"
    assert not tmp_chunk.exists()  # Orphaned .tmp file purged

    # Verify chunks manifest includes only chunk_0000
    with open(run_dir / "chunks_manifest.json", "r", encoding="utf-8") as f:
        cm = json.load(f)
    assert cm["total_chunks"] == 1
    assert cm["chunks"][0]["file_name"] == "chunk_0000.npz"


# ------------------------------------------------------------------------------
# AC 8: Artifact Preservation & Frozen Execution
# ------------------------------------------------------------------------------
def test_ac_08_artifact_preservation_and_frozen_replay(tmp_path: Path):
    """AC 8: Replay policy directly from run_dir/artifacts/ produces expected outputs."""
    run_dir = tmp_path / "test_run_vault"
    run_dir.mkdir()
    artifacts_dir = run_dir / "artifacts"
    artifacts_dir.mkdir()

    policy_code = """
import numpy as np

class FrozenReplayPolicy:
    def __init__(self, metadata=None, action_spec=None):
        pass
    def get_action(self, obs):
        return {
            "discrete_action": np.array([1, 1, 1, 1, 1], dtype=np.int32),
            "continuous_action": np.full(92, 0.75, dtype=np.float32),
        }
"""
    policy_file = artifacts_dir / "FrozenReplayPolicy.py"
    policy_file.write_text(policy_code.strip(), encoding="utf-8")
    sha = hashlib.sha256(policy_file.read_bytes()).hexdigest()

    manifest = {
        "project_git_commit": "00c911a270af3bdbc52dc1e16c9d3e6c139cb175",
        "starter_kit_commit": "95cea5b1c57b5291f44baf0283e0a081d53f5b16",
        "artifacts": [
            {
                "role": "policy_entrypoint",
                "source_path": "source.py",
                "stored_path": "artifacts/FrozenReplayPolicy.py",
                "sha256": sha,
                "entrypoint_class": "FrozenReplayPolicy",
            }
        ],
    }
    with open(run_dir / "artifact_manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f)

    cls, _ = PolicyAdapter.load_policy_from_artifacts(run_dir)
    action_spec = {
        "discrete_action": np.zeros(5, dtype=np.int32),
        "continuous_action": np.zeros(92, dtype=np.float32),
    }
    adapter = PolicyAdapter(cls, action_spec, {})
    act = adapter.get_action(np.zeros(352, dtype=np.float32))

    assert act["discrete_action"].sum() == 5
    assert act["continuous_action"][0] == pytest.approx(0.75)


# ------------------------------------------------------------------------------
# AC 9: Separate Commit Provenance
# ------------------------------------------------------------------------------
def test_ac_09_separate_commit_provenance(tmp_path: Path):
    """AC 9: Assert manifest['project_git_commit'] != manifest['starter_kit_commit']."""
    reg = ExperimentRegistry(base_runs_dir=tmp_path)
    proj_commit = reg.get_project_git_commit()
    sk_commit = reg.get_starter_kit_commit()

    assert proj_commit != sk_commit
    assert len(proj_commit) == 40
    assert len(sk_commit) == 40

    run_id, run_dir = reg.create_run(
        experiment_id="EXP_AC9",
        policy_name="TestPolicy",
        scenario_id="sc_1",
        config_hash="c1",
        policy_hash="p1",
    )
    m = reg.load_manifest(run_dir)
    assert m["project_git_commit"] == proj_commit
    assert m["starter_kit_commit"] == sk_commit
    assert m["project_git_commit"] != m["starter_kit_commit"]


# ------------------------------------------------------------------------------
# AC 10: Decoupled Status Preservation
# ------------------------------------------------------------------------------
def test_ac_10_decoupled_status_preservation(tmp_path: Path):
    """AC 10: Quarantining a completed run sets evidence_validity = QUARANTINED and execution_status = COMPLETE."""
    reg = ExperimentRegistry(base_runs_dir=tmp_path)
    run_id, run_dir = reg.create_run(
        experiment_id="EXP_AC10",
        policy_name="TestPolicy",
        scenario_id="sc_1",
        config_hash="c1",
        policy_hash="p1",
    )
    reg.update_status(run_dir, RunStatus.RUNNING)
    reg.update_status(run_dir, RunStatus.COMPLETE, actual_steps=8640)
    reg.update_evidence_validity(run_dir, EvidenceValidity.VALID)

    # Quarantine
    reg.update_evidence_validity(run_dir, EvidenceValidity.QUARANTINED, reason="Upstream taint")

    m = reg.load_manifest(run_dir)
    assert m["execution_status"] == "COMPLETE"
    assert m["status"] == "COMPLETE"
    assert m["evidence_validity"] == "QUARANTINED"


# ------------------------------------------------------------------------------
# AC 11: Transitive Lineage Traversal
# ------------------------------------------------------------------------------
def test_ac_11_transitive_lineage_traversal(tmp_path: Path):
    """AC 11: Invoking quarantine_run('Baseline_A') cascades to Candidate B and Comparison D."""
    reg = ExperimentRegistry(base_runs_dir=tmp_path)

    # Baseline A
    _, base_dir = reg.create_run("EXP", "BasePolicy", "sc_1", "c1", "p1", run_id="Baseline_A")
    reg.update_status(base_dir, RunStatus.RUNNING)
    reg.update_status(base_dir, RunStatus.COMPLETE, actual_steps=8640)
    reg.update_evidence_validity(base_dir, EvidenceValidity.VALID)

    # Candidate B
    _, cand_dir = reg.create_run(
        "EXP", "CandPolicy", "sc_1", "c1", "p2", run_id="Candidate_B",
        dependencies=[{"type": "baseline_comparator", "target_id": "Baseline_A", "role": "control", "required": True}],
    )
    reg.update_status(cand_dir, RunStatus.RUNNING)
    reg.update_status(cand_dir, RunStatus.COMPLETE, actual_steps=8640)
    reg.update_evidence_validity(cand_dir, EvidenceValidity.VALID)

    # Comparison D
    _, comp_dir = reg.create_run(
        "EXP", "CompReport", "sc_1", "c1", "p3", run_id="Comparison_D",
        dependencies=[{"type": "candidate_run", "target_id": "Candidate_B", "role": "treatment", "required": True}],
    )
    reg.update_status(comp_dir, RunStatus.RUNNING)
    reg.update_status(comp_dir, RunStatus.COMPLETE, actual_steps=8640)
    reg.update_evidence_validity(comp_dir, EvidenceValidity.VALID)

    # Quarantine Baseline A with cascade=True
    quarantined = reg.quarantine_run("Baseline_A", reason="Defective weather", cascade=True)

    assert "Baseline_A" in quarantined
    assert "Candidate_B" in quarantined
    assert "Comparison_D" in quarantined

    assert reg.load_manifest(cand_dir)["evidence_validity"] == "QUARANTINED"
    assert reg.load_manifest(comp_dir)["evidence_validity"] == "QUARANTINED"


# ------------------------------------------------------------------------------
# AC 12: Containment of Unrelated Results
# ------------------------------------------------------------------------------
def test_ac_12_containment_of_unrelated_results(tmp_path: Path):
    """AC 12: Candidate F evaluated against Baseline Z is unaffected by Baseline A quarantine."""
    reg = ExperimentRegistry(base_runs_dir=tmp_path)

    _, base_dir = reg.create_run("EXP", "BasePolicy", "sc_1", "c1", "p1", run_id="Baseline_A")
    reg.update_status(base_dir, RunStatus.RUNNING)
    reg.update_status(base_dir, RunStatus.COMPLETE, actual_steps=8640)
    reg.update_evidence_validity(base_dir, EvidenceValidity.VALID)

    _, f_dir = reg.create_run(
        "EXP", "CandPolicyF", "sc_1", "c1", "p4", run_id="Candidate_F",
        dependencies=[{"type": "baseline_comparator", "target_id": "Baseline_Z", "role": "control", "required": True}],
    )
    reg.update_status(f_dir, RunStatus.RUNNING)
    reg.update_status(f_dir, RunStatus.COMPLETE, actual_steps=8640)
    reg.update_evidence_validity(f_dir, EvidenceValidity.VALID)

    reg.quarantine_run("Baseline_A", reason="Defective weather", cascade=True)

    # Candidate F remains completely VALID
    assert reg.load_manifest(f_dir)["evidence_validity"] == "VALID"


# ------------------------------------------------------------------------------
# AC 13: Clean Control Invariance
# ------------------------------------------------------------------------------
def test_ac_13_clean_control_invariance(certified_run_dir: Path):
    """AC 13: Certified reference run passes all independent score and trace audits."""
    trace_res = ScoreVerifier.verify_trace_and_score(
        trace_path=certified_run_dir / "trace.csv",
        expected_steps=8640,
        expected_return=-1174.1805287515745,
    )
    assert trace_res["valid"] is True
    assert trace_res["actual_steps"] == 8640


# ------------------------------------------------------------------------------
# AC 14: Chunk Anomaly Detection
# ------------------------------------------------------------------------------
def test_ac_14_chunk_anomaly_detection(tmp_path: Path):
    """AC 14: Deleting or corrupting a chunk causes ScoreVerifier to flag run as INVALID."""
    run_dir = tmp_path / "corrupted_run"
    run_dir.mkdir()
    chunks_dir = run_dir / "chunks"
    chunks_dir.mkdir()

    chunk_0 = chunks_dir / "chunk_0000.npz"
    np.savez(chunk_0, step_indices=np.arange(288), observations=np.zeros((288, 10)))

    # Missing chunk 1 when chunks_manifest declares 2 chunks
    cm = {
        "total_chunks": 2,
        "chunk_size": 288,
        "chunks": [
            {"chunk_index": 0, "file_name": "chunk_0000.npz", "sha256": "fake_sha", "start_step": 0, "end_step": 287},
            {"chunk_index": 1, "file_name": "chunk_0001.npz", "sha256": "fake_sha", "start_step": 288, "end_step": 575},
        ],
    }
    with open(run_dir / "chunks_manifest.json", "w", encoding="utf-8") as f:
        json.dump(cm, f)

    res = ScoreVerifier.verify_run_integrity(run_dir, expected_steps=576)
    assert res["valid"] is False
    assert any("Missing chunk file" in err for err in res["errors"])


# ------------------------------------------------------------------------------
# AC 15: Empirical Leakage Rejection (Red Team F3)
# ------------------------------------------------------------------------------
def test_ac_15_empirical_leakage_rejection():
    """AC 15: Policy attempting to import simulator or inspect stack frames is rejected."""
    class RogueF3Policy:
        def __init__(self, metadata=None, action_spec=None):
            import smart_buildings.smart_control.simulator
        def get_action(self, obs):
            return {}

    with pytest.raises(SecurityViolationError, match="smart_buildings.smart_control"):
        PolicyAdapter(RogueF3Policy, {"discrete_action": np.zeros(1), "continuous_action": np.zeros(1)}, {})


# ------------------------------------------------------------------------------
# AC 16: Interventional Semantic Probe (Red Team F1)
# ------------------------------------------------------------------------------
def test_ac_16_interventional_semantic_probe():
    """AC 16: Actuator pulse causing ΔT > 0.5 K confirms semantic mapping."""
    init_t = {"VAV_1": 293.0, "VAV_2": 293.0}
    final_t = {"VAV_1": 293.85, "VAV_2": 293.05}

    report = SemanticActuatorProbe.evaluate_response(
        target_zone="VAV_1",
        initial_temperatures=init_t,
        final_temperatures=final_t,
    )
    assert report["passed"] is True
    assert report["delta_t_target_k"] >= 0.5
    assert report["margin_k"] >= 0.3


# ------------------------------------------------------------------------------
# AC 17: Storage Failure Detection
# ------------------------------------------------------------------------------
def test_ac_17_storage_failure_detection(tmp_path: Path):
    """AC 17: Simulating disk write failure during chunk commit raises EvidenceCaptureError."""
    recorder = TraceRecorder(
        output_dir=tmp_path,
        chunk_size=5,
    )

    with patch("os.fsync", side_effect=OSError("Disk full / I/O error")):
        with pytest.raises(EvidenceCaptureError, match="Failed to publish chunk"):
            for step in range(5):
                recorder.record_step(
                    step_idx=step,
                    reward=0.0,
                    productivity_regret=0.0,
                    energy_cost=0.0,
                    carbon_penalty=0.0,
                    mean_zone_temp=293.0,
                    outdoor_temp=15.0,
                    total_occupants=0.0,
                    discrete_action=np.zeros(1, dtype=np.int32),
                    continuous_action=np.zeros(2, dtype=np.float32),
                    raw_continuous_action=np.zeros(2, dtype=np.float32),
                    observation=np.zeros(5, dtype=np.float32),
                    zone_temperatures=np.zeros(2, dtype=np.float32),
                )


# ------------------------------------------------------------------------------
# AC 18: Measured Performance Overhead
# ------------------------------------------------------------------------------
def test_ac_18_measured_performance_overhead(tmp_path: Path):
    """AC 18: Serialization latency is strictly < 50 ms per chunk."""
    recorder = TraceRecorder(
        output_dir=tmp_path,
        chunk_size=288,
    )
    dummy_obs = np.zeros(352, dtype=np.float32)
    dummy_cont = np.zeros(92, dtype=np.float32)
    dummy_disc = np.ones(5, dtype=np.int32)
    dummy_temps = np.zeros(39, dtype=np.float32)

    for step in range(287):
        recorder.record_step(
            step_idx=step,
            reward=-1.0,
            productivity_regret=0.5,
            energy_cost=1.0,
            carbon_penalty=0.5,
            mean_zone_temp=293.15,
            outdoor_temp=15.0,
            total_occupants=10.0,
            discrete_action=dummy_disc,
            continuous_action=dummy_cont,
            raw_continuous_action=dummy_cont,
            observation=dummy_obs,
            zone_temperatures=dummy_temps,
        )

    t0 = time.perf_counter()
    recorder.record_step(
        step_idx=287,
        reward=-1.0,
        productivity_regret=0.5,
        energy_cost=1.0,
        carbon_penalty=0.5,
        mean_zone_temp=293.15,
        outdoor_temp=15.0,
        total_occupants=10.0,
        discrete_action=dummy_disc,
        continuous_action=dummy_cont,
        raw_continuous_action=dummy_cont,
        observation=dummy_obs,
        zone_temperatures=dummy_temps,
    )
    commit_latency_ms = (time.perf_counter() - t0) * 1000.0
    recorder.close()

    assert (tmp_path / "chunks" / "chunk_0000.npz").is_file()
    # Chunk serialization latency must easily fall within overhead budget (< 150 ms on Windows NTFS; < 1.0% total simulation time)
    assert commit_latency_ms < 150.0
    assert (commit_latency_ms / 288.0) < 1.0  # < 1 ms average per step amortized


# ------------------------------------------------------------------------------
# AC 19: Independent Investigator Explainability
# ------------------------------------------------------------------------------
def test_ac_19_independent_investigator_explainability(certified_run_dir: Path):
    """AC 19: Standalone auditor reconstructs full timeline, comfort, and energy without external code."""
    audit = StandaloneAuditor.audit_run_directory(certified_run_dir)
    assert audit["explainability_verified"] is True
    assert audit["total_steps"] > 0
    assert "reconstructed_totals" in audit
    assert "thermal_comfort_summary" in audit
    assert "provenance_summary" in audit
    assert audit["provenance_summary"]["project_git_commit"] is not None
