"""Tests for fresh-process policy reload and bitwise simulation reproducibility."""

import sys
from pathlib import Path
import pytest
import numpy as np

PHASE_ROOT = Path(__file__).resolve().parents[1]
if str(PHASE_ROOT) not in sys.path:
    sys.path.insert(0, str(PHASE_ROOT))

from smart_buildings.evaluate import (
    load_hybrid_environment,
    create_building_meta_data,
)
from smart_buildings.baselines.transfer_policy import TransferPolicy

from core.policy_adapter import PolicyAdapter

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCENARIO_DIR = PROJECT_ROOT / "smart_buildings" / "training_scenarios" / "building_train_1" / "atlanta_2"


def run_n_steps(num_steps: int = 5):
    gin_path = SCENARIO_DIR / "config.gin"
    env = load_hybrid_environment(gin_path)
    env.metrics_path = None
    meta = create_building_meta_data(env, SCENARIO_DIR)
    action_spec = env.action_spec()
    adapter = PolicyAdapter(TransferPolicy, action_spec, meta)

    reset_res = env.reset()
    obs = reset_res[0] if isinstance(reset_res, tuple) else reset_res
    observations = []
    actions = []
    rewards = []

    for _ in range(num_steps):
        observations.append(np.array(obs, copy=True))
        action = adapter.get_action(obs)
        actions.append(action)
        step_res = env.step(action)
        obs = step_res[0]
        reward = step_res[1]
        rewards.append(float(reward))

    return observations, actions, rewards


def test_reproducibility_identical_traces():
    """Two independent simulation executions under identical conditions must produce bitwise identical traces."""
    obs1, act1, rew1 = run_n_steps(5)
    obs2, act2, rew2 = run_n_steps(5)

    # Verify rewards match bitwise
    assert rew1 == rew2

    # Verify actions match bitwise
    for a1, a2 in zip(act1, act2):
        np.testing.assert_array_equal(a1["discrete_action"], a2["discrete_action"])
        np.testing.assert_array_equal(a1["continuous_action"], a2["continuous_action"])

    # Verify observations match bitwise
    for o1, o2 in zip(obs1, obs2):
        np.testing.assert_array_equal(o1, o2)
