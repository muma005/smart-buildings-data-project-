"""Gate 3 Test Suite: Independent Evidence Verification Engine.
Verifies that ScoreVerifier and RunEvaluator independently audit all evidence
without trusting self-reported metrics, detecting chunk discontinuities,
checksum tampering, non-finite tensor values, dimensional mismatches,
arithmetic violations, and return discrepancies.
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

from core.trace_recorder import TraceRecorder
from core.registry import ExperimentRegistry, RunStatus
from core.evaluator import RunEvaluator
from evaluation.score_verification import ScoreVerifier


def _create_synthetic_valid_run(
    base_dir: Path,
    n_steps: int = 600,
    chunk_size: int = 288,
    d_obs: int = 352,
    d_cont: int = 92,
    d_disc: int = 5,
    n_zones: int = 39,
) -> Path:
    """Helper creating an end-to-end valid run directory matching official schema."""
    registry = ExperimentRegistry(base_runs_dir=base_dir)
    run_id, run_dir = registry.create_run(
        experiment_id="EXP_SYNTHETIC_VERIFY",
        policy_name="TestPolicy",
        scenario_id="building_train_1/atlanta_2",
        config_hash="a1b2c3d4",
        policy_hash="e5f6a7b8",
        expected_steps=n_steps,
    )
    registry.update_status(run_dir, RunStatus.RUNNING)

    recorder = TraceRecorder(run_dir, chunk_size=chunk_size)
    with recorder:
        for t in range(n_steps):
            regret = -0.1
            energy = 0.2
            carbon = 0.1
            w_p, w_e, w_c = 0.6, 0.2, 0.2
            reward = float(w_p * regret - w_e * energy - w_c * carbon)

            obs = np.full(d_obs, float(t % 10), dtype=np.float32)
            act_cont = np.full(d_cont, 21.0, dtype=np.float32)
            act_disc = np.zeros(d_disc, dtype=np.int32)
            zone_temps = np.full(n_zones, 22.0, dtype=np.float32)

            recorder.record_step(
                step_idx=t,
                reward=reward,
                productivity_regret=regret,
                energy_cost=energy,
                carbon_penalty=carbon,
                mean_zone_temp=22.0,
                outdoor_temp=15.0,
                total_occupants=10.0,
                discrete_action=act_disc,
                continuous_action=act_cont,
                raw_continuous_action=act_cont,
                observation=obs,
                zone_temperatures=zone_temps,
                was_clipped=False,
                latency_ms=1.5,
            )

    trace_meta = recorder.close()

    # Create summary.json
    summary = {
        "run_id": run_id,
        "scenario_id": "building_train_1/atlanta_2",
        "policy": "TestPolicy",
        "steps_completed": n_steps,
        "cumulative_reward": trace_meta["cumulative_reward"],
        "trace_sha256": trace_meta["sha256"],
        "chunks_committed": trace_meta["total_chunks"],
        "chunks_manifest_sha256": trace_meta["chunks_manifest_sha256"],
    }
    summary_path = run_dir / "summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    # Complete the run
    registry.update_status(
        run_dir=run_dir,
        new_status=RunStatus.COMPLETE,
        actual_steps=n_steps,
        trace_hash=trace_meta["sha256"],
        chunks_manifest_hash=trace_meta["chunks_manifest_sha256"],
        artifacts_update={
            "trace_path": trace_meta["trace_path"],
            "summary_path": str(summary_path),
            "chunks_dir": trace_meta["chunks_dir"],
            "chunks_manifest_path": trace_meta["chunks_manifest_path"],
        },
    )
    return run_dir


def test_gate_03_valid_run_passes_full_audit(tmp_path: Path):
    """Test 1: Full independent evidence verification passes on a valid completed episode."""
    run_dir = _create_synthetic_valid_run(tmp_path, n_steps=600, chunk_size=288)

    expected_dims = {
        "observations": 352,
        "raw_continuous_actions": 92,
        "executed_continuous_actions": 92,
        "discrete_actions": 5,
        "zone_temperatures": 39,
    }

    res = ScoreVerifier.verify_run_integrity(
        run_dir=run_dir,
        expected_steps=600,
        expected_dims=expected_dims,
        enforce_complete=True,
    )

    assert res["valid"] is True, f"Expected valid audit, got errors: {res['errors']}"
    assert len(res["errors"]) == 0
    assert res["status"] == "COMPLETE"
    assert res["details"]["total_chunks"] == 3
    assert res["details"]["total_chunk_steps"] == 600
    assert res["details"]["trace_steps"] == 600
    assert res["checks"]["chunk_continuity_valid"] is True
    assert res["checks"]["chunk_hashes_valid"] is True
    assert res["checks"]["tensor_shapes_valid"] is True
    assert res["checks"]["finite_values_valid"] is True
    assert res["checks"]["reward_arithmetic_valid"] is True
    assert res["checks"]["return_parity_valid"] is True
    assert res["checks"]["step_count_parity_valid"] is True


def test_gate_03_detects_chunk_step_continuity_gap(tmp_path: Path):
    """Test 2: Verifies audit fails when chunk sequence contains a step discontinuity/gap."""
    run_dir = _create_synthetic_valid_run(tmp_path, n_steps=600, chunk_size=288)

    # Tamper with chunks_manifest.json to introduce a step gap
    manifest_path = run_dir / "chunks_manifest.json"
    with open(manifest_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Make Chunk 1 start at 295 instead of 288
    data["chunks"][1]["start_step"] = 295
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    # Update hash in run_manifest so it doesn't fail on manifest hash
    run_manifest_path = run_dir / "run_manifest.json"
    with open(run_manifest_path, "r", encoding="utf-8") as f:
        rm = json.load(f)
    rm["hashes"]["chunks_manifest_sha256"] = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    with open(run_manifest_path, "w", encoding="utf-8") as f:
        json.dump(rm, f, indent=2)

    res = ScoreVerifier.verify_run_integrity(run_dir=run_dir, expected_steps=600)
    assert res["valid"] is False
    assert res["checks"]["chunk_continuity_valid"] is False
    assert any("step discontinuity" in err for err in res["errors"])


def test_gate_03_detects_chunk_file_sha_tampering(tmp_path: Path):
    """Test 3: Verifies audit fails when a chunk binary on disk is modified/tampered."""
    run_dir = _create_synthetic_valid_run(tmp_path, n_steps=600, chunk_size=288)

    chunk_0 = run_dir / "chunks" / "chunk_0000.npz"
    raw_bytes = bytearray(chunk_0.read_bytes())
    # Alter bytes in place
    raw_bytes[100] = (raw_bytes[100] + 1) % 256
    chunk_0.write_bytes(bytes(raw_bytes))

    res = ScoreVerifier.verify_run_integrity(run_dir=run_dir, expected_steps=600)
    assert res["valid"] is False
    assert res["checks"]["chunk_hashes_valid"] is False
    assert any("SHA-256 mismatch" in err for err in res["errors"])


def test_gate_03_detects_non_finite_tensor_values(tmp_path: Path):
    """Test 4: Verifies audit fails when a chunk contains NaN or Inf values in tensors."""
    run_dir = _create_synthetic_valid_run(tmp_path, n_steps=600, chunk_size=288)

    chunk_0 = run_dir / "chunks" / "chunk_0000.npz"
    with np.load(chunk_0) as d:
        step_indices = d["step_indices"]
        observations = d["observations"].copy()
        raw_cont = d["raw_continuous_actions"]
        exec_cont = d["executed_continuous_actions"]
        disc = d["discrete_actions"]
        zone_temps = d["zone_temperatures"]

    # Inject NaN into observation tensor
    observations[5, 10] = np.nan

    np.savez_compressed(
        chunk_0,
        step_indices=step_indices,
        observations=observations,
        raw_continuous_actions=raw_cont,
        executed_continuous_actions=exec_cont,
        discrete_actions=disc,
        zone_temperatures=zone_temps,
    )

    # Update hash in chunks_manifest and run_manifest so hash passes but tensor scan catches NaN
    new_sha = hashlib.sha256(chunk_0.read_bytes()).hexdigest()
    cm_path = run_dir / "chunks_manifest.json"
    with open(cm_path, "r", encoding="utf-8") as f:
        cm_data = json.load(f)
    cm_data["chunks"][0]["sha256"] = new_sha
    with open(cm_path, "w", encoding="utf-8") as f:
        json.dump(cm_data, f, indent=2)

    rm_path = run_dir / "run_manifest.json"
    with open(rm_path, "r", encoding="utf-8") as f:
        rm_data = json.load(f)
    rm_data["hashes"]["chunks_manifest_sha256"] = hashlib.sha256(cm_path.read_bytes()).hexdigest()
    with open(rm_path, "w", encoding="utf-8") as f:
        json.dump(rm_data, f, indent=2)

    res = ScoreVerifier.verify_run_integrity(run_dir=run_dir, expected_steps=600)
    assert res["valid"] is False
    assert res["checks"]["finite_values_valid"] is False
    assert any("contains non-finite (NaN/Inf) values" in err for err in res["errors"])


def test_gate_03_detects_dimension_mismatch(tmp_path: Path):
    """Test 5: Verifies audit fails when high-dimensional tensor shapes don't match building schema."""
    run_dir = _create_synthetic_valid_run(tmp_path, n_steps=600, chunk_size=288)

    # Pass incorrect expected dimensions
    expected_dims = {
        "observations": 703,  # Building 1 is 352, so 703 must fail
        "raw_continuous_actions": 92,
        "executed_continuous_actions": 92,
        "discrete_actions": 5,
        "zone_temperatures": 39,
    }

    res = ScoreVerifier.verify_run_integrity(
        run_dir=run_dir,
        expected_steps=600,
        expected_dims=expected_dims,
    )
    assert res["valid"] is False
    assert res["checks"]["tensor_shapes_valid"] is False
    assert any("Dimension mismatch for 'observations'" in err for err in res["errors"])


def test_gate_03_detects_step_reward_arithmetic_violation(tmp_path: Path):
    """Test 6: Verifies audit catches divergence between recorded step reward and component formula."""
    run_dir = _create_synthetic_valid_run(tmp_path, n_steps=600, chunk_size=288)

    trace_path = run_dir / "trace.csv"
    import pandas as pd
    df = pd.read_csv(trace_path)
    # Tamper with step 50 reward
    df.loc[50, "reward"] += 0.05
    df.to_csv(trace_path, index=False)

    # Update hash in run_manifest so it doesn't fail on SHA check
    rm_path = run_dir / "run_manifest.json"
    with open(rm_path, "r", encoding="utf-8") as f:
        rm = json.load(f)
    rm["hashes"]["trace_sha256"] = hashlib.sha256(trace_path.read_bytes()).hexdigest()
    with open(rm_path, "w", encoding="utf-8") as f:
        json.dump(rm, f, indent=2)

    res = ScoreVerifier.verify_run_integrity(run_dir=run_dir, expected_steps=600)
    assert res["valid"] is False
    assert res["checks"]["reward_arithmetic_valid"] is False
    assert any("arithmetic discrepancy" in err for err in res["errors"])


def test_gate_03_detects_return_parity_discrepancy(tmp_path: Path):
    """Test 7: Verifies audit catches discrepancy between trace sum and reported summary return."""
    run_dir = _create_synthetic_valid_run(tmp_path, n_steps=600, chunk_size=288)

    summary_path = run_dir / "summary.json"
    with open(summary_path, "r", encoding="utf-8") as f:
        summary = json.load(f)
    # Inflate cumulative reward
    summary["cumulative_reward"] += 5.0
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    res = ScoreVerifier.verify_run_integrity(run_dir=run_dir, expected_steps=600)
    assert res["valid"] is False
    assert res["checks"]["return_parity_valid"] is False
    assert any("Return parity mismatch" in err for err in res["errors"])


def test_gate_03_run_evaluator_integration(tmp_path: Path):
    """Test 8: Verifies RunEvaluator generates evaluation.json and integrates run_integrity audit."""
    run_dir = _create_synthetic_valid_run(tmp_path, n_steps=600, chunk_size=288)

    eval_result = RunEvaluator.evaluate_run(run_dir, expected_steps=600)

    assert eval_result["overall_valid"] is True
    assert "run_integrity" in eval_result
    assert eval_result["run_integrity"]["valid"] is True
    assert "score_verification" in eval_result
    assert "diagnostics" in eval_result

    eval_file = run_dir / "evaluation.json"
    assert eval_file.is_file()
    with open(eval_file, "r", encoding="utf-8") as f:
        disk_data = json.load(f)
    assert disk_data["overall_valid"] is True
    assert disk_data["run_integrity"]["checks"]["chunk_continuity_valid"] is True
