"""Gate 4 Test Suite: Artifact Preservation and Reproducibility.
Verifies the run_dir/artifacts/ vault, local dependency snapshotting from sys.modules,
artifact_manifest.json generation with separate git commits, and policy replay directly
from frozen artifacts.
"""

from __future__ import annotations
import csv
import hashlib
import json
from pathlib import Path
import sys
import numpy as np
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
FOUNDATION_ROOT = PROJECT_ROOT / "04_EXPERIMENT_FOUNDATION"
if str(FOUNDATION_ROOT) not in sys.path:
    sys.path.insert(0, str(FOUNDATION_ROOT))

from smart_buildings.baselines.transfer_policy import TransferPolicy
from smart_buildings.evaluate import load_hybrid_environment, create_building_meta_data
from core.runner import SimulationRunner
from core.registry import ExperimentRegistry, RunStatus
from core.policy_adapter import PolicyAdapter
from evaluation.score_verification import ScoreVerifier


SCENARIO_DIR = PROJECT_ROOT / "smart_buildings" / "training_scenarios" / "building_train_1" / "atlanta_2"


def test_gate_04_vault_creation_and_artifact_manifest(tmp_path: Path):
    """Test 1: Verifies artifacts vault creation, separate commit provenance, and artifact_manifest.json."""
    if not (SCENARIO_DIR / "config.gin").is_file():
        pytest.skip("Scenario config not found")

    registry = ExperimentRegistry(base_runs_dir=tmp_path / "runs")
    runner = SimulationRunner(registry=registry)

    run_id, run_dir, manifest = runner.execute_episode(
        experiment_id="EXP_GATE_04_PRESERVE",
        policy_class=TransferPolicy,
        scenario_dir=SCENARIO_DIR,
        max_steps=5,
        chunk_size=5,
    )

    assert manifest["status"] == RunStatus.COMPLETE.value

    # 1. Verify artifacts directory structure
    artifacts_dir = run_dir / "artifacts"
    assert artifacts_dir.is_dir(), "artifacts/ directory must exist"
    assert (artifacts_dir / "config.gin").is_file(), "config.gin must be preserved in artifacts/"
    assert (artifacts_dir / "transfer_policy.py").is_file(), "Policy entrypoint must be preserved in artifacts/"

    local_deps_dir = artifacts_dir / "local_deps"
    assert local_deps_dir.is_dir(), "local_deps/ directory must exist in artifacts/"

    # 2. Verify artifact_manifest.json
    manifest_file = run_dir / "artifact_manifest.json"
    assert manifest_file.is_file(), "artifact_manifest.json must exist"

    with open(manifest_file, "r", encoding="utf-8") as f:
        art_manifest = json.load(f)

    # 3. Assert separate commit provenance (Acceptance Criteria 9)
    proj_commit = art_manifest.get("project_git_commit")
    sk_commit = art_manifest.get("starter_kit_commit")
    assert proj_commit is not None and len(proj_commit) == 40
    assert sk_commit is not None and len(sk_commit) == 40
    assert proj_commit != sk_commit, "project_git_commit and starter_kit_commit must be distinct"

    # Also assert in run_manifest.json
    run_manifest = registry.load_manifest(run_dir)
    assert run_manifest["project_git_commit"] != run_manifest["starter_kit_commit"]
    assert run_manifest["hashes"]["artifact_manifest_sha256"] is not None
    actual_art_sha = hashlib.sha256(manifest_file.read_bytes()).hexdigest()
    assert run_manifest["hashes"]["artifact_manifest_sha256"] == actual_art_sha

    # 4. Check runtime packages recorded
    assert "runtime_packages" in art_manifest
    assert "numpy" in art_manifest["runtime_packages"]

    # 5. Check artifacts list in manifest
    artifacts_list = art_manifest.get("artifacts", [])
    roles = {a["role"] for a in artifacts_list}
    assert "scenario_config" in roles
    assert "policy_entrypoint" in roles


def test_gate_04_policy_replay_from_frozen_artifacts(tmp_path: Path):
    """Test 2: Verifies frozen policy can be loaded and executed directly from run_dir/artifacts/ (Acceptance Criteria 8)."""
    if not (SCENARIO_DIR / "config.gin").is_file():
        pytest.skip("Scenario config not found")

    registry = ExperimentRegistry(base_runs_dir=tmp_path / "runs")
    runner = SimulationRunner(registry=registry)

    run_id, run_dir, _ = runner.execute_episode(
        experiment_id="EXP_GATE_04_REPLAY",
        policy_class=TransferPolicy,
        scenario_dir=SCENARIO_DIR,
        max_steps=5,
        chunk_size=5,
    )

    # Load frozen policy from artifacts
    loaded_class, art_meta = PolicyAdapter.load_policy_from_artifacts(run_dir)
    assert loaded_class.__name__ == "TransferPolicy"

    # Instantiate via PolicyAdapter from frozen code
    env = load_hybrid_environment(SCENARIO_DIR / "config.gin")
    meta = create_building_meta_data(env, SCENARIO_DIR)
    action_spec = env.action_spec()
    adapter = PolicyAdapter(loaded_class, action_spec, meta)
    dummy_obs = np.full(352, 22.0, dtype=np.float32)
    action = adapter.get_action(dummy_obs)

    assert isinstance(action, dict)
    assert "discrete_action" in action
    assert "continuous_action" in action
    assert len(action["discrete_action"]) == 5
    assert len(action["continuous_action"]) == 92


def test_gate_04_tampered_artifact_rejected(tmp_path: Path):
    """Test 3: Verifies that tampering with a preserved artifact raises an integrity error."""
    if not (SCENARIO_DIR / "config.gin").is_file():
        pytest.skip("Scenario config not found")

    registry = ExperimentRegistry(base_runs_dir=tmp_path / "runs")
    runner = SimulationRunner(registry=registry)

    run_id, run_dir, _ = runner.execute_episode(
        experiment_id="EXP_GATE_04_TAMPER",
        policy_class=TransferPolicy,
        scenario_dir=SCENARIO_DIR,
        max_steps=5,
        chunk_size=5,
    )

    # Tamper with the frozen policy
    policy_file = run_dir / "artifacts" / "transfer_policy.py"
    original_code = policy_file.read_text(encoding="utf-8")
    policy_file.write_text(original_code + "\n# Tampered code insertion\n", encoding="utf-8")

    # PolicyAdapter loader must reject
    with pytest.raises(ValueError) as exc_info:
        PolicyAdapter.load_policy_from_artifacts(run_dir)
    assert "checksum mismatch" in str(exc_info.value).lower()

    # ScoreVerifier integrity audit must reject
    audit = ScoreVerifier.verify_run_integrity(run_dir=run_dir, expected_steps=5)
    assert audit["valid"] is False
    assert any("Preserved artifact checksum mismatch" in err for err in audit["errors"])


def test_gate_04_identical_commits_rejected(tmp_path: Path):
    """Test 4: Verifies audit rejects runs where project_git_commit and starter_kit_commit are erroneously identical."""
    registry = ExperimentRegistry(base_runs_dir=tmp_path / "runs")
    run_id, run_dir = registry.create_run(
        experiment_id="EXP_IDENTICAL_COMMITS",
        policy_name="Dummy",
        scenario_id="bldg/weather",
        config_hash="abc",
        policy_hash="def",
        expected_steps=100,
        project_git_commit="same_commit_hash_12345678901234567890",
        starter_kit_commit="same_commit_hash_12345678901234567890",
    )

    # Write artifact_manifest with identical commits
    art_manifest = {
        "project_git_commit": "same_commit_hash_12345678901234567890",
        "starter_kit_commit": "same_commit_hash_12345678901234567890",
        "artifacts": [],
    }
    with open(run_dir / "artifact_manifest.json", "w", encoding="utf-8") as f:
        json.dump(art_manifest, f, indent=2)

    audit = ScoreVerifier.verify_run_integrity(run_dir=run_dir, expected_steps=100, enforce_complete=False)
    assert audit["valid"] is False
    assert any("must not be identical" in err for err in audit["errors"])
