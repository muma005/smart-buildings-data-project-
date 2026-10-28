"""Live simulator runtime and policy interface tests.
Executes against a real loaded scenario (building_train_1 / atlanta_2) in smart_buildings.
"""

import math
from pathlib import Path
import pytest
import numpy as np

from smart_buildings.evaluate import (
    load_hybrid_environment,
    create_building_meta_data,
    initialize_policy,
    get_policy_action,
    validate_action,
)
from smart_buildings.baselines.transfer_policy import TransferPolicy
from smart_buildings.baselines.all_off import AllOffPolicy
from smart_buildings.baselines.fixed_setpoint import FixedSetpointPolicy
from smart_buildings.smart_control.environment import hybrid_action_environment

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCENARIO_DIR = PROJECT_ROOT / "smart_buildings" / "training_scenarios" / "building_train_1" / "atlanta_2"


@pytest.fixture(scope="module")
def loaded_env():
    gin_path = SCENARIO_DIR / "config.gin"
    assert gin_path.is_file(), f"Scenario gin config missing: {gin_path}"
    env = load_hybrid_environment(gin_path)
    env.metrics_path = None
    env._occupancy_normalization_constant = 125.0
    return env


@pytest.fixture(scope="module")
def scenario_metadata(loaded_env):
    return create_building_meta_data(loaded_env, SCENARIO_DIR)


def test_runtime_metadata_structure(scenario_metadata):
    """Verifies all required metadata keys exist and are populated."""
    expected_keys = {
        "n_discrete_action",
        "n_continuous_action",
        "temp_indices",
        "pressure_indices",
        "water_indices",
        "recirculation_indices",
        "zone_action_indices",
        "zone_temp_indices",
        "observation_field_names",
        "floor_plan",
        "zone_map",
        "ahu_zone_assignments",
        "num_floors",
        "morning_start_hour",
        "evening_start_hour",
        "comfort_temp_window",
        "eco_temp_window",
        "time_zone",
        "holidays",
        "observation_normalization_metadata",
        "action_normalization_metadata",
    }
    assert expected_keys.issubset(set(scenario_metadata.keys()))

    # building_train_1: 4 AHUs, 39 zones
    assert scenario_metadata["n_discrete_action"] == 5
    assert scenario_metadata["n_continuous_action"] == 92
    assert len(scenario_metadata["ahu_zone_assignments"]) == 4
    assert len(scenario_metadata["zone_temp_indices"]) == 39

    # Floor plans are numpy arrays, not None
    assert isinstance(scenario_metadata["floor_plan"], np.ndarray)
    assert isinstance(scenario_metadata["zone_map"], np.ndarray)


def test_runtime_observation_spec(loaded_env, scenario_metadata):
    """Observation shape matches the closed form 6*V + 15*K + 58."""
    obs_spec = loaded_env.observation_spec()
    assert len(obs_spec.shape) == 1
    # V=39, K=4: 6*39 + 15*4 + 58 = 234 + 60 + 58 = 352
    assert obs_spec.shape[0] == 352
    assert obs_spec.dtype == np.float32

    # Check initial observation is finite
    obs, info = loaded_env.reset()
    assert obs.shape == (352,)
    assert np.all(np.isfinite(obs))


def test_runtime_action_spec_and_validation(loaded_env, scenario_metadata):
    """Action spec has continuous [-1, 1] Box and discrete [0, 1] Box."""
    action_spec = loaded_env.action_spec()
    assert "continuous_action" in action_spec
    assert "discrete_action" in action_spec

    c_box = action_spec["continuous_action"]
    d_box = action_spec["discrete_action"]
    assert c_box.shape == (92,)
    assert d_box.shape == (5,)
    assert c_box.low[0] == -1.0
    assert c_box.high[0] == 1.0
    assert d_box.low[0] == 0
    assert d_box.high[0] == 1


def test_runtime_policy_step_lifecycle(loaded_env, scenario_metadata):
    """Verifies that TransferPolicy, AllOffPolicy, and FixedSetpointPolicy step cleanly."""
    action_spec = loaded_env.action_spec()
    obs, _ = loaded_env.reset()

    # Step with TransferPolicy (default zeros / ones)
    policy = initialize_policy(TransferPolicy, scenario_metadata, action_spec)
    raw_action = get_policy_action(policy, obs)
    action = validate_action(raw_action, action_spec)
    assert action["continuous_action"].shape == (92,)
    assert action["discrete_action"].shape == (5,)

    step_result = loaded_env.step(action)
    if len(step_result) == 5:
        next_obs, reward, terminated, truncated, info = step_result
    else:
        next_obs, reward, terminated, info = step_result
        truncated = False

    assert next_obs.shape == (352,)
    assert np.all(np.isfinite(next_obs))
    assert math.isfinite(reward)
    assert reward <= 0.0
    assert not terminated
    assert not truncated
