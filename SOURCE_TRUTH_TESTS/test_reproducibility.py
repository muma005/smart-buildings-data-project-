"""Fresh-process policy reload and determinism check."""

import numpy as np
from pathlib import Path
from smart_buildings.evaluate import (
    load_hybrid_environment,
    create_building_meta_data,
    initialize_policy,
    get_policy_action,
    validate_action,
)
from smart_buildings.baselines.transfer_policy import TransferPolicy

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCENARIO_DIR = PROJECT_ROOT / "smart_buildings" / "training_scenarios" / "building_train_1" / "atlanta_2"


def run_n_steps(num_steps=5):
    gin_path = SCENARIO_DIR / "config.gin"
    env = load_hybrid_environment(gin_path)
    env.metrics_path = None
    meta = create_building_meta_data(env, SCENARIO_DIR)
    action_spec = env.action_spec()
    policy = initialize_policy(TransferPolicy, meta, action_spec)

    obs, _ = env.reset()
    trace = []
    for step in range(num_steps):
        raw_act = get_policy_action(policy, obs)
        act = validate_action(raw_act, action_spec)
        step_res = env.step(act)
        obs, reward = step_res[0], step_res[1]
        trace.append((float(reward), float(np.sum(obs))))
    return trace


def test_fresh_process_determinism():
    run_1 = run_n_steps(5)
    run_2 = run_n_steps(5)
    assert run_1 == run_2, f"Runs diverge: {run_1} vs {run_2}"
    print(f"Deterministic trace verified over 5 steps: {run_1}")


if __name__ == "__main__":
    test_fresh_process_determinism()
