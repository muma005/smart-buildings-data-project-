"""Gate 1 Test Suite: Reward and Schema Correctness.

Verifies:
1. Exact reward extraction via official `env.get_reward_info_and_response()` interface.
2. Step reward components (productivity regret, energy cost, carbon penalty) are accurately captured and non-zero when equipment operates.
3. Explicit `EvidenceCaptureError` is raised if reward info is missing or malformed (no silent zero substitution).
4. Independent score arithmetic reconstruction matches official agent reward within 1e-6.
5. Dynamic schema discovery and validation across distinct buildings with differing dimensions.
6. Preservation of distinction between raw policy output, executed action, and clipping flags.
"""

from __future__ import annotations
import sys
from pathlib import Path
import pytest
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
FOUNDATION_ROOT = PROJECT_ROOT / "04_EXPERIMENT_FOUNDATION"
if str(FOUNDATION_ROOT) not in sys.path:
    sys.path.insert(0, str(FOUNDATION_ROOT))

from smart_buildings.baselines.transfer_policy import TransferPolicy
from smart_buildings.evaluate import load_hybrid_environment, create_building_meta_data
from core.runner import SimulationRunner, EvidenceCaptureError
from core.registry import ExperimentRegistry, RunStatus
from core.policy_adapter import PolicyAdapter
from evaluation.score_verification import ScoreVerifier


SCENARIO_BLDG_1 = PROJECT_ROOT / "smart_buildings" / "training_scenarios" / "building_train_1" / "atlanta_2"
SCENARIO_BLDG_2 = PROJECT_ROOT / "smart_buildings" / "training_scenarios" / "building_train_2" / "atlanta_3"


class AlwaysActivePolicy:
    """Policy that commands HVAC equipment ON to verify physical energy/carbon capture."""

    def __init__(self, metadata, action_spec):
        self.disc_shape = action_spec["discrete_action"].shape
        self.cont_shape = action_spec["continuous_action"].shape

    def get_action(self, obs):
        return {
            "discrete_action": np.ones(self.disc_shape, dtype=np.int32),  # Turn all equipment ON
            "continuous_action": np.zeros(self.cont_shape, dtype=np.float32),
        }


def test_gate_01_reward_components_captured_and_nonzero_when_operating(tmp_path):
    """Verify that runner extracts true physical components and records non-zero values when equipment operates."""
    registry = ExperimentRegistry(tmp_path)
    runner = SimulationRunner(registry)

    run_id, run_dir, manifest = runner.execute_episode(
        experiment_id="EXP_GATE1_COMPONENTS",
        policy_class=AlwaysActivePolicy,
        scenario_dir=SCENARIO_BLDG_1,
        max_steps=5,
    )

    assert manifest["status"] == RunStatus.COMPLETE.value
    trace_path = run_dir / "trace.csv"
    assert trace_path.is_file()

    df = pd.read_csv(trace_path)
    assert len(df) == 5

    # Check required reward columns exist
    for col in ["reward", "productivity_regret", "energy_cost", "carbon_penalty"]:
        assert col in df.columns, f"Missing column {col} in trace.csv"

    # Verify that energy_cost and carbon_penalty are non-zero when equipment is actively running
    energy_sum = df["energy_cost"].abs().sum()
    carbon_sum = df["carbon_penalty"].abs().sum()
    assert energy_sum > 0.0, f"Expected non-zero energy cost when equipment is ON, got sum={energy_sum}"
    assert carbon_sum > 0.0, f"Expected non-zero carbon penalty when equipment is ON, got sum={carbon_sum}"

    # Verify reward matches the physical penalties
    assert np.all(df["reward"] < 0.0)


def test_gate_01_reconstructed_reward_parity(tmp_path):
    """Verify step-level mathematical reconstruction against official agent reward."""
    registry = ExperimentRegistry(tmp_path)
    runner = SimulationRunner(registry)

    run_id, run_dir, manifest = runner.execute_episode(
        experiment_id="EXP_GATE1_PARITY",
        policy_class=AlwaysActivePolicy,
        scenario_dir=SCENARIO_BLDG_1,
        max_steps=5,
    )

    df = pd.read_csv(run_dir / "trace.csv")

    for idx, row in df.iterrows():
        reconstructed = 0.6 * row["productivity_regret"] - 0.2 * row["energy_cost"] - 0.2 * row["carbon_penalty"]
        actual = row["reward"]
        delta = abs(actual - reconstructed)
        assert delta <= 1.0e-6, (
            f"Step {idx} reward arithmetic divergence: actual={actual}, "
            f"reconstructed={reconstructed}, delta={delta:.8e}"
        )


def test_gate_01_missing_reward_raises_evidence_capture_error(tmp_path, monkeypatch):
    """Verify that missing reward info raises EvidenceCaptureError rather than defaulting to zero."""
    registry = ExperimentRegistry(tmp_path)
    runner = SimulationRunner(registry)

    gin_path = SCENARIO_BLDG_1 / "config.gin"
    env = load_hybrid_environment(gin_path)
    env.metrics_path = None

    real_fn = env.get_reward_info_and_response
    call_count = 0

    def mock_get_reward():
        nonlocal call_count
        call_count += 1
        # Step() calls get_reward_info_and_response internally; let step() succeed
        if call_count == 1:
            return real_fn()
        # When runner queries afterwards, return malformed/None tuple
        return (None, None)

    monkeypatch.setattr(env, "get_reward_info_and_response", mock_get_reward)
    monkeypatch.setattr("core.runner.load_hybrid_environment", lambda p: env)

    with pytest.raises(EvidenceCaptureError, match="Environment failed to return RewardResponse"):
        runner.execute_episode(
            experiment_id="EXP_GATE1_FAIL_NULL",
            policy_class=TransferPolicy,
            scenario_dir=SCENARIO_BLDG_1,
            max_steps=3,
        )


def test_gate_01_divergent_step0_reward_raises_evidence_capture_error(tmp_path, monkeypatch):
    """Verify that step 0 arithmetic divergence triggers immediate failure."""
    registry = ExperimentRegistry(tmp_path)
    runner = SimulationRunner(registry)

    gin_path = SCENARIO_BLDG_1 / "config.gin"
    env = load_hybrid_environment(gin_path)
    env.metrics_path = None

    real_fn = env.get_reward_info_and_response

    class CorruptedResponse:
        def __init__(self, original):
            self.agent_reward_value = -999.0  # Deliberate corruption
            self.normalized_productivity_regret = original.normalized_productivity_regret
            self.normalized_energy_cost = original.normalized_energy_cost
            self.normalized_carbon_emission = original.normalized_carbon_emission
            self.total_occupancy = original.total_occupancy
            self.productivity_weight = 0.6
            self.energy_cost_weight = 0.2
            self.carbon_emission_weight = 0.2

    def mock_get_reward():
        info, resp = real_fn()
        return info, CorruptedResponse(resp)

    monkeypatch.setattr(env, "get_reward_info_and_response", mock_get_reward)
    monkeypatch.setattr("core.runner.load_hybrid_environment", lambda p: env)

    with pytest.raises(EvidenceCaptureError, match="Step 0 reward arithmetic divergence"):
        runner.execute_episode(
            experiment_id="EXP_GATE1_FAIL_DIVERGENCE",
            policy_class=TransferPolicy,
            scenario_dir=SCENARIO_BLDG_1,
            max_steps=3,
        )


def test_gate_01_dynamic_schema_multi_building(tmp_path):
    """Verify dynamic schema handling across buildings with differing dimensions."""
    env1 = load_hybrid_environment(SCENARIO_BLDG_1 / "config.gin")
    meta1 = create_building_meta_data(env1, SCENARIO_BLDG_1)
    act1 = env1.action_spec()

    env2 = load_hybrid_environment(SCENARIO_BLDG_2 / "config.gin")
    meta2 = create_building_meta_data(env2, SCENARIO_BLDG_2)
    act2 = env2.action_spec()

    # Assert dimensions differ between Building 1 and Building 2
    assert env1.observation_space.shape[0] == 352
    assert env2.observation_space.shape[0] == 703
    assert act1["continuous_action"].shape[0] == 92
    assert act2["continuous_action"].shape[0] == 199
    assert act1["discrete_action"].shape[0] == 5
    assert act2["discrete_action"].shape[0] == 10

    # PolicyAdapter dynamically adapts to each building without hardcoding
    adapter1 = PolicyAdapter(TransferPolicy, act1, meta1)
    adapter2 = PolicyAdapter(TransferPolicy, act2, meta2)

    assert adapter1.continuous_shape == (92,)
    assert adapter2.continuous_shape == (199,)
    assert adapter1.discrete_shape == (5,)
    assert adapter2.discrete_shape == (10,)

    # Run 2-step episodes on both buildings to confirm runner handles dynamic shapes
    registry = ExperimentRegistry(tmp_path)
    runner = SimulationRunner(registry)

    _, run_dir1, m1 = runner.execute_episode(
        experiment_id="EXP_BLDG1",
        policy_class=TransferPolicy,
        scenario_dir=SCENARIO_BLDG_1,
        max_steps=2,
    )
    assert m1["status"] == RunStatus.COMPLETE.value

    _, run_dir2, m2 = runner.execute_episode(
        experiment_id="EXP_BLDG2",
        policy_class=TransferPolicy,
        scenario_dir=SCENARIO_BLDG_2,
        max_steps=2,
    )
    assert m2["status"] == RunStatus.COMPLETE.value

    env1.close()
    env2.close()


def test_gate_01_raw_vs_executed_action_and_clipping(tmp_path):
    """Verify that adapter captures raw unclipped actions and flags clipping."""
    env = load_hybrid_environment(SCENARIO_BLDG_1 / "config.gin")
    meta = create_building_meta_data(env, SCENARIO_BLDG_1)
    action_spec = env.action_spec()

    class OutOfBoundsPolicy:
        def __init__(self, metadata, action_spec):
            self.disc_shape = action_spec["discrete_action"].shape
            self.cont_shape = action_spec["continuous_action"].shape

        def get_action(self, obs):
            return {
                "discrete_action": np.ones(self.disc_shape, dtype=np.int32),
                "continuous_action": np.full(self.cont_shape, 2.5, dtype=np.float32),
            }

    adapter = PolicyAdapter(OutOfBoundsPolicy, action_spec, meta)
    reset_res = env.reset()
    obs = reset_res[0] if isinstance(reset_res, tuple) else reset_res

    action = adapter.get_action(obs)

    # Executed action must be clipped to 1.0
    assert np.all(action["continuous_action"] == 1.0)

    # Decision metadata must preserve raw continuous action (2.5)
    decision = adapter.last_decision
    assert np.all(decision["raw_continuous_action"] == 2.5)
    assert np.all(decision["executed_continuous_action"] == 1.0)
    assert decision["was_clipped"] is True
    assert decision["max_clip_delta"] == pytest.approx(1.5, abs=1e-5)
    assert decision["latency_ms"] >= 0.0

    env.close()
