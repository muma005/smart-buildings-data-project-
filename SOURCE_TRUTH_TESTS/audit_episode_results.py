"""Reconstructs the episode score independently and validates against official summary."""

import json
import math
from pathlib import Path
import pandas as pd
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = PROJECT_ROOT / "results" / "s0_episode" / "building_train_1" / "atlanta_2" / "transfer"
MANIFEST_PATH = PROJECT_ROOT / "results" / "s0_episode" / "run_manifest.json"


def audit_episode():
    timeseries_path = RESULTS_DIR / "timeseries.csv"
    rc_path = RESULTS_DIR / "reward_components.csv"
    summary_path = RESULTS_DIR / "summary.json"

    assert timeseries_path.is_file(), f"Missing {timeseries_path}"
    assert rc_path.is_file(), f"Missing {rc_path}"
    assert summary_path.is_file(), f"Missing {summary_path}"

    with open(summary_path, "r", encoding="utf-8") as f:
        official_summary = json.load(f)

    ts_df = pd.read_csv(timeseries_path)
    rc_df = pd.read_csv(rc_path)

    total_steps = len(ts_df)
    print(f"Total steps in episode timeseries: {total_steps}")
    assert total_steps == 8640, f"Expected 8640 steps, got {total_steps}"

    # Verify timeseries rewards
    recorded_rewards = ts_df["reward"].to_numpy(dtype=np.float64)
    assert np.all(np.isfinite(recorded_rewards)), "Non-finite reward detected!"

    total_reward = float(np.sum(recorded_rewards))
    mean_reward = float(np.mean(recorded_rewards))
    scenario_loss = abs(mean_reward)

    print(f"Recorded total reward: {total_reward:.6f}")
    print(f"Official summary total reward: {official_summary['total_reward']:.6f}")

    diff_reward = abs(total_reward - official_summary["total_reward"])
    print(f"Total reward difference: {diff_reward:.2e}")
    assert diff_reward < 1e-9, "Mismatch between sum of step rewards and official summary"

    # Verify per-step reward component reconstruction:
    # reward = (productivity_regret * 0.6 - energy_cost * 0.2 - carbon_emission * 0.2) / 1.0
    w_p = 0.6
    w_e = 0.2
    w_c = 0.2

    reconstructed_rewards = []
    for idx, row in rc_df.iterrows():
        p_regret = float(row["normalized_productivity_regret"])
        e_cost = float(row["normalized_energy_cost"])
        c_emis = float(row["normalized_carbon_emission"])

        r_calc = (p_regret * w_p - e_cost * w_e - c_emis * w_c) / (w_p + w_e + w_c)
        reconstructed_rewards.append(r_calc)

    reconstructed_rewards = np.array(reconstructed_rewards, dtype=np.float64)
    max_step_delta = float(np.max(np.abs(recorded_rewards - reconstructed_rewards)))
    print(f"Max discrepancy across all 8640 steps: {max_step_delta:.2e}")
    assert max_step_delta < 1e-5, f"Discrepancy too large: {max_step_delta}"

    # Build Run Manifest
    manifest = {
        "run_id": "RUN-S0-EPISODE-001",
        "scenario": "building_train_1/atlanta_2",
        "provenance": {
            "building": "building_train_1",
            "weather": "atlanta_2",
            "building_seed": 0,
            "weather_csv": "smart_buildings/weather/csv/atlanta.csv",
            "git_commit": "95cea5b1c57b5291f44baf0283e0a081d53f5b16",
        },
        "policy": {
            "name": "TransferPolicy",
            "path": "smart_buildings/baselines/transfer_policy.py",
            "type": "reference_all_zero_continuous_all_one_discrete",
        },
        "episode_metrics": {
            "total_steps": total_steps,
            "total_reward": total_reward,
            "mean_reward": mean_reward,
            "scenario_loss": scenario_loss,
            "avg_occupancy": float(official_summary["avg_occupancy"]),
            "avg_zone_temp": float(official_summary["avg_zone_temp"]),
        },
        "scoring_reconciliation": {
            "official_total_reward": float(official_summary["total_reward"]),
            "independent_total_reward": total_reward,
            "discrepancy_total": diff_reward,
            "max_per_step_component_discrepancy": max_step_delta,
            "status": "RECONCILED_AND_VERIFIED",
        },
        "artifacts": {
            "timeseries_csv": str(timeseries_path.relative_to(PROJECT_ROOT)),
            "reward_components_csv": str(rc_path.relative_to(PROJECT_ROOT)),
            "summary_json": str(summary_path.relative_to(PROJECT_ROOT)),
        },
    }

    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"Run manifest written to: {MANIFEST_PATH}")
    print("GATE S0.4 AUDIT PASSED!")


if __name__ == "__main__":
    audit_episode()
