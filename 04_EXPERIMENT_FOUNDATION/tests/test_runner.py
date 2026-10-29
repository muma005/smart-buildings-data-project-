"""Tests for the Simulation Runner, Policy Adapter, Trace Recorder, and Registry."""

import sys
from pathlib import Path
import shutil
import tempfile
import pytest
import numpy as np

PHASE_ROOT = Path(__file__).resolve().parents[1]
if str(PHASE_ROOT) not in sys.path:
    sys.path.insert(0, str(PHASE_ROOT))

from smart_buildings.baselines.transfer_policy import TransferPolicy
from smart_buildings.baselines.fixed_setpoint import FixedSetpointPolicy
from smart_buildings.evaluate import load_hybrid_environment, create_building_meta_data

from core.policy_adapter import PolicyAdapter
from core.trace_recorder import TraceRecorder
from core.registry import ExperimentRegistry, RunStatus
from core.runner import SimulationRunner

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCENARIO_DIR = PROJECT_ROOT / "smart_buildings" / "training_scenarios" / "building_train_1" / "atlanta_2"


@pytest.fixture(scope="module")
def env_and_meta():
    gin_path = SCENARIO_DIR / "config.gin"
    env = load_hybrid_environment(gin_path)
    env.metrics_path = None
    meta = create_building_meta_data(env, SCENARIO_DIR)
    action_spec = env.action_spec()
    return env, meta, action_spec


def test_policy_adapter_contract(env_and_meta):
    """Adapter must compute source hash and return valid clipped actions."""
    env, meta, action_spec = env_and_meta
    adapter = PolicyAdapter(TransferPolicy, action_spec, meta)

    assert len(adapter.source_hash) == 64  # Valid SHA-256
    reset_res = env.reset()
    obs = reset_res[0] if isinstance(reset_res, tuple) else reset_res
    action = adapter.get_action(obs)

    assert "discrete_action" in action
    assert "continuous_action" in action
    assert action["discrete_action"].shape == action_spec["discrete_action"].shape
    assert action["continuous_action"].shape == action_spec["continuous_action"].shape
    assert np.all(action["continuous_action"] >= -1.0)
    assert np.all(action["continuous_action"] <= 1.0)


def test_trace_recorder_monotonicity(tmp_path):
    """Recorder must enforce strict step sequence monotonicity."""
    with TraceRecorder(tmp_path, prefix="test_trace") as recorder:
        recorder.record_step(
            step_idx=0,
            reward=-0.1,
            productivity_regret=-0.05,
            energy_cost=0.03,
            carbon_penalty=0.02,
            mean_zone_temp=22.1,
            outdoor_temp=18.0,
            total_occupants=10.0,
            discrete_action=[1, 1],
            continuous_action=[0.0, 0.5],
        )
        # Attempting to record step 2 instead of step 1 must fail
        with pytest.raises(ValueError, match="Step sequence discontinuity"):
            recorder.record_step(
                step_idx=2,
                reward=-0.1,
                productivity_regret=-0.05,
                energy_cost=0.03,
                carbon_penalty=0.02,
                mean_zone_temp=22.1,
                outdoor_temp=18.0,
                total_occupants=10.0,
                discrete_action=[1, 1],
                continuous_action=[0.0, 0.5],
            )


def test_registry_lifecycle_and_invariants(tmp_path):
    """Registry must assign unique IDs, prevent overwrites, and enforce transition rules."""
    registry = ExperimentRegistry(tmp_path)
    run_id, run_dir = registry.create_run(
        experiment_id="EXP_TEST",
        policy_name="TransferPolicy",
        scenario_id="building_train_1/atlanta_2",
        config_hash="abc123",
        policy_hash="def456",
        expected_steps=100,
    )

    assert run_dir.is_dir()
    manifest = registry.load_manifest(run_dir)
    assert manifest["status"] == RunStatus.INITIALIZED.value

    # Transition to RUNNING
    registry.update_status(run_dir, RunStatus.RUNNING)
    manifest = registry.load_manifest(run_dir)
    assert manifest["status"] == RunStatus.RUNNING.value

    # Illegal transition: RUNNING -> INITIALIZED
    with pytest.raises(ValueError, match="Illegal state transition"):
        registry.update_status(run_dir, RunStatus.INITIALIZED)

    # Valid transition to COMPLETE
    registry.update_status(run_dir, RunStatus.COMPLETE, actual_steps=100)
    manifest = registry.load_manifest(run_dir)
    assert manifest["status"] == RunStatus.COMPLETE.value


def test_simulation_runner_short_episode(tmp_path):
    """Runner must execute a multi-step episode, commit manifest, and produce trace."""
    registry = ExperimentRegistry(tmp_path)
    runner = SimulationRunner(registry)

    run_id, run_dir, manifest = runner.execute_episode(
        experiment_id="EXP_SHORT",
        policy_class=TransferPolicy,
        scenario_dir=SCENARIO_DIR,
        max_steps=5,
    )

    assert manifest["status"] == RunStatus.COMPLETE.value
    assert manifest["actual_steps"] == 5
    assert (run_dir / "trace.csv").is_file()
    assert (run_dir / "summary.json").is_file()
    assert manifest["hashes"]["trace_sha256"] is not None
