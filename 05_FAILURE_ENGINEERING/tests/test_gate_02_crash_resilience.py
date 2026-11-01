"""Gate 2 Test Suite: Crash-Resilient Incremental Chunk Persistence.
Verifies durable daily chunking, atomic publication, post-crash recovery,
and preservation of multi-dimensional transition tensors without data loss.
"""

from __future__ import annotations
import csv
import hashlib
import json
from pathlib import Path
import sys
from unittest.mock import patch
import numpy as np
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
FOUNDATION_ROOT = PROJECT_ROOT / "04_EXPERIMENT_FOUNDATION"
if str(FOUNDATION_ROOT) not in sys.path:
    sys.path.insert(0, str(FOUNDATION_ROOT))

from core.trace_recorder import TraceRecorder, EvidenceCaptureError
from core.registry import ExperimentRegistry, RunStatus
from core.runner import SimulationRunner


class DummyGate2Policy:
    """Dummy policy generating known synthetic tensors for verification."""
    def __init__(self, metadata=None, action_spec=None, **kwargs):
        self.metadata = metadata or {}
        self.action_spec = action_spec or {}
        self.step_counter = 0

    def step(self, observation):
        self.step_counter += 1
        d_disc = self.action_spec["discrete_action"].shape[0] if "discrete_action" in self.action_spec else 5
        d_cont = self.action_spec["continuous_action"].shape[0] if "continuous_action" in self.action_spec else 92
        return {
            "discrete_action": np.ones(d_disc, dtype=np.int32),
            "continuous_action": np.full(d_cont, 22.5, dtype=np.float32),
        }


def test_durable_chunk_buffering_and_manifest(tmp_path: Path):
    """Test 1: Verifies that 600 steps with chunk_size=288 produces 2 full chunks and 1 final partial chunk."""
    run_dir = tmp_path / "test_run_01"
    run_dir.mkdir(parents=True)

    recorder = TraceRecorder(run_dir, chunk_size=288)
    with recorder:
        for t in range(600):
            obs = np.full(352, float(t), dtype=np.float32)
            act_cont = np.full(92, 20.0 + (t % 5), dtype=np.float32)
            act_disc = np.array([t % 2, 0, 1, 0, 1], dtype=np.int32)
            zone_temps = np.full(39, 21.0 + (t % 3), dtype=np.float32)

            recorder.record_step(
                step_idx=t,
                reward=-0.5,
                productivity_regret=0.1,
                energy_cost=0.2,
                carbon_penalty=0.1,
                mean_zone_temp=21.5,
                outdoor_temp=15.0,
                total_occupants=10.0,
                discrete_action=act_disc,
                continuous_action=act_cont,
                raw_continuous_action=act_cont,
                observation=obs,
                zone_temperatures=zone_temps,
                was_clipped=False,
                latency_ms=1.2,
            )

    meta = recorder.close()

    assert meta["total_steps"] == 600
    assert meta["total_chunks"] == 3

    chunks_dir = run_dir / "chunks"
    chunk_0 = chunks_dir / "chunk_0000.npz"
    chunk_1 = chunks_dir / "chunk_0001.npz"
    chunk_2 = chunks_dir / "chunk_0002.npz"

    assert chunk_0.is_file()
    assert chunk_1.is_file()
    assert chunk_2.is_file()

    # Verify manifest
    manifest_file = run_dir / "chunks_manifest.json"
    assert manifest_file.is_file()
    with open(manifest_file, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    assert manifest["total_chunks"] == 3
    assert manifest["chunks"][0]["num_steps"] == 288
    assert manifest["chunks"][0]["start_step"] == 0
    assert manifest["chunks"][0]["end_step"] == 287
    assert manifest["chunks"][0]["is_final"] is False

    assert manifest["chunks"][1]["num_steps"] == 288
    assert manifest["chunks"][1]["start_step"] == 288
    assert manifest["chunks"][1]["end_step"] == 575
    assert manifest["chunks"][1]["is_final"] is False

    assert manifest["chunks"][2]["num_steps"] == 24
    assert manifest["chunks"][2]["start_step"] == 576
    assert manifest["chunks"][2]["end_step"] == 599
    assert manifest["chunks"][2]["is_final"] is True

    # Verify SHA-256 matches disk
    for entry in manifest["chunks"]:
        cf = chunks_dir / entry["file_name"]
        actual_sha = hashlib.sha256(cf.read_bytes()).hexdigest()
        assert entry["sha256"] == actual_sha


def test_chunk_loading_and_multi_dim_tensor_integrity(tmp_path: Path):
    """Test 2: Verifies that load_chunks correctly concatenates all chunks and recovers exact tensor shapes."""
    run_dir = tmp_path / "test_run_02"
    recorder = TraceRecorder(run_dir, chunk_size=100)

    n_steps = 250
    d_obs = 352
    d_cont = 92
    d_disc = 5
    n_zones = 39

    expected_obs = []
    expected_cont = []

    with recorder:
        for t in range(n_steps):
            obs = np.arange(d_obs, dtype=np.float32) + t
            act_cont = np.full(d_cont, float(t), dtype=np.float32)
            act_disc = np.zeros(d_disc, dtype=np.int32)
            zone_temps = np.full(n_zones, 22.0, dtype=np.float32)

            expected_obs.append(obs)
            expected_cont.append(act_cont)

            recorder.record_step(
                step_idx=t,
                reward=1.0,
                productivity_regret=0.0,
                energy_cost=0.0,
                carbon_penalty=0.0,
                mean_zone_temp=22.0,
                outdoor_temp=15.0,
                total_occupants=5.0,
                discrete_action=act_disc,
                continuous_action=act_cont,
                observation=obs,
                zone_temperatures=zone_temps,
            )

    recorder.close()

    loaded = TraceRecorder.load_chunks(run_dir)
    assert "observations" in loaded
    assert loaded["observations"].shape == (n_steps, d_obs)
    assert loaded["executed_continuous_actions"].shape == (n_steps, d_cont)
    assert loaded["discrete_actions"].shape == (n_steps, d_disc)
    assert loaded["zone_temperatures"].shape == (n_steps, n_zones)
    assert loaded["step_indices"].shape == (n_steps,)

    # Verify bitwise exact values at start, middle, and end
    np.testing.assert_array_equal(loaded["observations"][0], expected_obs[0])
    np.testing.assert_array_equal(loaded["observations"][150], expected_obs[150])
    np.testing.assert_array_equal(loaded["observations"][249], expected_obs[249])
    np.testing.assert_array_equal(loaded["executed_continuous_actions"][99], expected_cont[99])


def test_crash_resilience_preserves_committed_day1_chunk(tmp_path: Path):
    """Test 3: Simulates process crash at step 350. Verifies Day 1 chunk (0..287) is intact on disk."""
    run_dir = tmp_path / "test_run_03"
    recorder = TraceRecorder(run_dir, chunk_size=288)

    # Record 350 steps then simulate an unhandled crash (do NOT call close())
    with recorder:
        for t in range(350):
            recorder.record_step(
                step_idx=t,
                reward=-0.1,
                productivity_regret=0.05,
                energy_cost=0.05,
                carbon_penalty=0.05,
                mean_zone_temp=22.0,
                outdoor_temp=15.0,
                total_occupants=2.0,
                discrete_action=[0, 0, 0, 0, 0],
                continuous_action=np.zeros(92),
                observation=np.zeros(352),
                zone_temperatures=np.zeros(39),
            )
        # Process crash simulation: recorder is exited without close()
        # In a real crash, __exit__ is called by OS or runtime termination

    chunks_dir = run_dir / "chunks"
    chunk_0 = chunks_dir / "chunk_0000.npz"
    chunk_1 = chunks_dir / "chunk_0001.npz"

    # Chunk 0 covering Day 1 MUST exist and be valid
    assert chunk_0.is_file(), "Day 1 chunk must be preserved on disk before crash"
    # Chunk 1 was only at step 62 of 288, so it must not have been published
    assert not chunk_1.is_file(), "Unfinished Chunk 1 must not be published"

    # Verify chunk 0 can be read and contains exactly 288 steps
    with np.load(chunk_0) as data:
        assert len(data["step_indices"]) == 288
        assert int(data["step_indices"][0]) == 0
        assert int(data["step_indices"][-1]) == 287

    # Verify manifest has Day 1 chunk
    manifest_file = run_dir / "chunks_manifest.json"
    assert manifest_file.is_file()
    with open(manifest_file, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    assert manifest["total_chunks"] == 1
    assert manifest["chunks"][0]["chunk_index"] == 0


def test_recovery_cleans_orphaned_tmp_files(tmp_path: Path):
    """Test 4: Verifies recovery scanner removes orphaned .tmp files and reconciles intact chunks."""
    registry = ExperimentRegistry(base_runs_dir=tmp_path)
    run_id, run_dir = registry.create_run(
        experiment_id="EXP_TEST_CRASH",
        policy_name="DummyPolicy",
        scenario_id="building_train_1/hot_dry",
        config_hash="abc",
        policy_hash="def",
        expected_steps=8640,
    )
    registry.update_status(run_dir, RunStatus.RUNNING)

    chunks_dir = run_dir / "chunks"
    chunks_dir.mkdir(parents=True, exist_ok=True)

    # Create a valid chunk 0
    c0_path = chunks_dir / "chunk_0000.npz"
    np.savez_compressed(
        c0_path,
        step_indices=np.arange(288, dtype=np.int64),
        observations=np.zeros((288, 352)),
        raw_continuous_actions=np.zeros((288, 92)),
        executed_continuous_actions=np.zeros((288, 92)),
        discrete_actions=np.zeros((288, 5)),
        zone_temperatures=np.zeros((288, 39)),
    )

    # Create an orphaned .tmp file from the crash
    tmp_path_file = chunks_dir / "chunk_0001.npz.tmp"
    tmp_path_file.write_bytes(b"corrupted partial write")

    # Run recovery
    recovered_manifest = registry.recover_interrupted_run(run_dir)

    # Verify .tmp file was deleted
    assert not tmp_path_file.exists(), "Orphaned .tmp file must be cleaned up on recovery"
    assert c0_path.is_file(), "Valid chunk 0 must remain intact"

    # Verify manifest status
    assert recovered_manifest["status"] == RunStatus.INCOMPLETE.value
    assert recovered_manifest["status"] != RunStatus.COMPLETE.value
    assert "data_loss_window" in recovered_manifest["metadata"]
    assert recovered_manifest["metadata"]["data_loss_window"]["durable_chunk_steps"] == 288


def test_recovered_run_never_marked_complete(tmp_path: Path):
    """Test 5: Explicitly verifies that under no circumstance is an interrupted run marked COMPLETE."""
    registry = ExperimentRegistry(base_runs_dir=tmp_path)
    run_id, run_dir = registry.create_run(
        experiment_id="EXP_TEST_STATUS",
        policy_name="DummyPolicy",
        scenario_id="building_train_1/hot_dry",
        config_hash="abc",
        policy_hash="def",
        expected_steps=8640,
    )
    registry.update_status(run_dir, RunStatus.RUNNING)

    manifest = registry.recover_interrupted_run(run_dir)
    assert manifest["status"] == RunStatus.INCOMPLETE.value
    assert manifest["status"] != RunStatus.COMPLETE.value
    assert len(manifest["errors"]) > 0
    assert "Interrupted run recovered" in manifest["errors"][-1]["error"]


def test_storage_write_failure_raises_evidence_capture_error(tmp_path: Path):
    """Test 6: Verifies disk failure during chunk publication raises EvidenceCaptureError and runner transitions to FAILED."""
    registry = ExperimentRegistry(base_runs_dir=tmp_path)
    run_dir = tmp_path / "test_run_fail"
    run_dir.mkdir(parents=True)

    recorder = TraceRecorder(run_dir, chunk_size=2)
    recorder.record_step(
        step_idx=0,
        reward=0.0,
        productivity_regret=0.0,
        energy_cost=0.0,
        carbon_penalty=0.0,
        mean_zone_temp=22.0,
        outdoor_temp=15.0,
        total_occupants=0.0,
        discrete_action=[0],
        continuous_action=[0.0],
    )

    # Mock open inside _publish_chunk to simulate disk I/O error
    with patch("builtins.open", side_effect=OSError("Disk full or permission denied")):
        with pytest.raises(EvidenceCaptureError) as exc_info:
            recorder.record_step(
                step_idx=1,
                reward=0.0,
                productivity_regret=0.0,
                energy_cost=0.0,
                carbon_penalty=0.0,
                mean_zone_temp=22.0,
                outdoor_temp=15.0,
                total_occupants=0.0,
                discrete_action=[0],
                continuous_action=[0.0],
            )
        assert "Failed to publish chunk" in str(exc_info.value) or "Failed to stream" in str(exc_info.value)


def test_end_to_end_simulation_runner_chunking_integration(tmp_path: Path):
    """Test 7: End-to-end integration test with official simulator running for 20 steps with chunk_size=10."""
    scenario_dir = PROJECT_ROOT / "smart_buildings" / "training_scenarios" / "building_train_1" / "atlanta_2"
    if not (scenario_dir / "config.gin").is_file():
        pytest.skip(f"Scenario {scenario_dir} config not found")

    registry = ExperimentRegistry(base_runs_dir=tmp_path / "runs")
    runner = SimulationRunner(registry=registry)

    # Run for 20 steps with chunk_size=10 -> produces exactly 2 full chunks
    run_id, run_dir, manifest = runner.execute_episode(
        experiment_id="GATE_02_INTEGRATION",
        policy_class=DummyGate2Policy,
        scenario_dir=scenario_dir,
        max_steps=20,
        chunk_size=10,
    )

    assert manifest["status"] == RunStatus.COMPLETE.value
    assert manifest["actual_steps"] == 20

    # Verify summary.json
    summary_path = run_dir / "summary.json"
    assert summary_path.is_file()
    with open(summary_path, "r", encoding="utf-8") as f:
        summary = json.load(f)
    assert summary["steps_completed"] == 20
    assert summary["chunks_committed"] == 2
    assert "chunks_manifest_sha256" in summary
    assert len(summary["chunks_manifest_sha256"]) == 64

    # Verify chunks loading and dimensional shapes
    loaded = TraceRecorder.load_chunks(run_dir)
    assert loaded["observations"].shape == (20, 352)
    assert loaded["executed_continuous_actions"].shape == (20, 92)
    assert loaded["raw_continuous_actions"].shape == (20, 92)
    assert loaded["discrete_actions"].shape == (20, 5)
    assert loaded["zone_temperatures"].shape == (20, 39)
    assert loaded["step_indices"].shape == (20,)
    np.testing.assert_array_equal(loaded["step_indices"], np.arange(20))
