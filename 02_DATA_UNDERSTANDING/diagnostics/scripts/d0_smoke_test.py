"""D0 Smoke Test Script.
Loads a representative scenario (building_train_1 / atlanta_2) using evaluate.py routines,
retrieves building metadata, observation and action specifications,
and runs a 2-step verification rollout using AllOffPolicy and FixedSetpointPolicy.
"""

import sys
from pathlib import Path
import json

WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(WORKSPACE_ROOT))

import numpy as np

from smart_buildings.evaluate import (
    load_hybrid_environment,
    create_building_meta_data,
    initialize_policy,
    get_policy_action,
    validate_action,
)
from smart_buildings.baselines.all_off import AllOffPolicy
from smart_buildings.baselines.fixed_setpoint import FixedSetpointPolicy
from smart_buildings.smart_control.environment import hybrid_action_environment

OUTPUT_JSON = WORKSPACE_ROOT / "02_DATA_UNDERSTANDING" / "diagnostics" / "outputs" / "d0_smoke_test.json"

def run_smoke_test():
    scenario_dir = WORKSPACE_ROOT / "smart_buildings" / "training_scenarios" / "building_train_1" / "atlanta_2"
    gin_path = scenario_dir / "config.gin"
    
    print(f"Loading scenario environment via gin config {gin_path}...")
    env = load_hybrid_environment(gin_path)
    
    # Environment configs matching evaluate.py
    env.metrics_path = None
    env._occupancy_normalization_constant = 125.0
    
    building_metadata = create_building_meta_data(env, scenario_dir)
    action_spec = env.action_spec()
    observation_spec = env.observation_spec()
    
    print("Environment successfully instantiated!")
    print(f"Building Metadata Keys: {list(building_metadata.keys())}")
    print(f"  n_discrete_action: {building_metadata['n_discrete_action']}")
    print(f"  n_continuous_action: {building_metadata['n_continuous_action']}")
    print(f"  zone_temp_indices count: {len(building_metadata['zone_temp_indices'])}")
    print(f"  num_ahus: {len(building_metadata['ahu_zone_assignments'])}")
    print(f"Action Spec: {action_spec}")
    print(f"Observation Spec: shape={observation_spec.shape}, dtype={observation_spec.dtype}")
    
    obs_dim = observation_spec.shape[0]
    discrete_dim = action_spec[hybrid_action_environment.DISCRETE_ACTION].shape[0]
    continuous_dim = action_spec[hybrid_action_environment.CONTINUOUS_ACTION].shape[0]
    
    # Initialize policies
    all_off_policy = initialize_policy(AllOffPolicy, building_metadata, action_spec)
    fixed_setpoint_policy = initialize_policy(FixedSetpointPolicy, building_metadata, action_spec)
    
    # Reset env
    reset_ret = env.reset()
    if isinstance(reset_ret, tuple):
        initial_obs, reset_info = reset_ret
    else:
        initial_obs = reset_ret
        reset_info = {}
        
    print(f"Initial observation received, shape: {initial_obs.shape}, finite={np.all(np.isfinite(initial_obs))}")
    
    # Step 1: AllOffPolicy
    raw_action_1 = get_policy_action(all_off_policy, initial_obs)
    action_1 = validate_action(raw_action_1, action_spec)
    step_1_ret = env.step(action_1)
    if len(step_1_ret) == 5:
        obs_1, reward_1, terminated_1, truncated_1, info_1 = step_1_ret
    else:
        obs_1, reward_1, terminated_1, info_1 = step_1_ret
        truncated_1 = False
        
    print(f"Step 1 (AllOff) executed: reward={reward_1}, terminated={terminated_1}, truncated={truncated_1}")
    
    # Step 2: FixedSetpointPolicy
    raw_action_2 = get_policy_action(fixed_setpoint_policy, obs_1)
    action_2 = validate_action(raw_action_2, action_spec)
    step_2_ret = env.step(action_2)
    if len(step_2_ret) == 5:
        obs_2, reward_2, terminated_2, truncated_2, info_2 = step_2_ret
    else:
        obs_2, reward_2, terminated_2, info_2 = step_2_ret
        truncated_2 = False
        
    print(f"Step 2 (FixedSetpoint) executed: reward={reward_2}, terminated={terminated_2}, truncated={truncated_2}")
    
    smoke_record = {
        "scenario": "building_train_1/atlanta_2",
        "status": "SUCCESS",
        "observation_dim": int(obs_dim),
        "discrete_action_dim": int(discrete_dim),
        "continuous_action_dim": int(continuous_dim),
        "building_metadata_keys": list(building_metadata.keys()),
        "n_discrete_action": int(building_metadata['n_discrete_action']),
        "n_continuous_action": int(building_metadata['n_continuous_action']),
        "zone_count": len(building_metadata['zone_temp_indices']),
        "ahu_count": len(building_metadata['ahu_zone_assignments']),
        "initial_obs_finite": bool(np.all(np.isfinite(initial_obs))),
        "step_1_reward": float(reward_1),
        "step_2_reward": float(reward_2),
        "step_1_obs_finite": bool(np.all(np.isfinite(obs_1))),
        "step_2_obs_finite": bool(np.all(np.isfinite(obs_2))),
    }
    
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as fp:
        json.dump(smoke_record, fp, indent=2)
        
    print(f"Smoke test results written to {OUTPUT_JSON}")
    print("D0 SMOKE TEST PASSED!")

if __name__ == "__main__":
    run_smoke_test()
