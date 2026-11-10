"""Baseline Characterization & Deficit Audit Tool.
Parses official starter kit baseline returns (30 scenarios x 4 policies)
and correlates performance with building thermal inertia (tau), scale (K, V),
and climatic regimes.
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Any

WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
BASELINE_RETURNS_PATH = WORKSPACE_ROOT / "starter_kit_pinned" / "baseline_returns.json"
OUTPUT_MATRIX_PATH = WORKSPACE_ROOT / "06_SOLUTION_DISCOVERY" / "baseline_deficit_matrix.json"
OUTPUT_REPORT_PATH = WORKSPACE_ROOT / "06_SOLUTION_DISCOVERY" / "BASELINE_CHARACTERIZATION_REPORT.md"

# Physical parameters established in Phase 02 (Data Understanding)
BUILDING_PROPERTIES = {
    "building_train_7": {"tau_hours": 1.94, "archetype": "Fast / Leaky", "U_value": 2.0772, "K_ahus": 4, "V_zones": 36},
    "building_train_2": {"tau_hours": 3.11, "archetype": "Fast / Commercial", "U_value": 1.6823, "K_ahus": 9, "V_zones": 85},
    "building_train_8": {"tau_hours": 4.94, "archetype": "Medium / Insulated", "U_value": 1.1793, "K_ahus": 3, "V_zones": 30},
    "building_train_4": {"tau_hours": 7.79, "archetype": "Medium / Massive", "U_value": 1.5837, "K_ahus": 6, "V_zones": 54},
    "building_train_5": {"tau_hours": 9.60, "archetype": "Slow / Dense", "U_value": 1.4880, "K_ahus": 8, "V_zones": 79},
    "building_train_1": {"tau_hours": 14.43, "archetype": "Slow / Massive", "U_value": 1.2972, "K_ahus": 4, "V_zones": 39},
}

CLIMATE_PROPERTIES = {
    "fairbanks": {"regime": "Extreme Subarctic Cold", "temp_range": "[-42.0 C, 28.9 C]"},
    "denver": {"regime": "High Altitude / Continental", "temp_range": "[-21.1 C, 37.2 C]"},
    "atlanta": {"regime": "Humid Subtropical / Variable", "temp_range": "[-3.9 C, 35.0 C]"},
    "phoenix": {"regime": "Extreme Desert Heat", "temp_range": "[0.4 C, 45.6 C]"},
    "singapore": {"regime": "Tropical Constant Hot/Humid", "temp_range": "[22.9 C, 34.0 C]"},
}

POLICIES = ["bang_bang", "fixed_setpoint", "pid", "pid_water"]


def audit_baselines() -> dict[str, Any]:
    with open(BASELINE_RETURNS_PATH, "r", encoding="utf-8") as f:
        raw_data: dict[str, dict[str, float]] = json.load(f)

    scenario_records = []
    policy_totals = {p: 0.0 for p in POLICIES}
    policy_mae = {p: 0.0 for p in POLICIES}

    building_stats: dict[str, dict[str, Any]] = {
        b: {p: {"total_return": 0.0, "scenarios_count": 0} for p in POLICIES}
        for b in BUILDING_PROPERTIES
    }
    climate_stats: dict[str, dict[str, Any]] = {
        c: {p: {"total_return": 0.0, "scenarios_count": 0} for p in POLICIES}
        for c in CLIMATE_PROPERTIES
    }

    for scenario_id, pol_returns in raw_data.items():
        bldg_name, weather_name = scenario_id.split("/")
        climate_family = weather_name.split("_")[0]

        bldg_props = BUILDING_PROPERTIES.get(bldg_name, {})
        climate_props = CLIMATE_PROPERTIES.get(climate_family, {})

        rec = {
            "scenario_id": scenario_id,
            "building": bldg_name,
            "weather": weather_name,
            "climate_family": climate_family,
            "tau_hours": bldg_props.get("tau_hours"),
            "archetype": bldg_props.get("archetype"),
            "K_ahus": bldg_props.get("K_ahus"),
            "V_zones": bldg_props.get("V_zones"),
            "returns": {},
            "mean_rewards": {},
            "mae_scores": {},
        }

        for p in POLICIES:
            ret = float(pol_returns[p])
            mean_r = ret / 8640.0
            mae_val = abs(mean_r)

            rec["returns"][p] = ret
            rec["mean_rewards"][p] = mean_r
            rec["mae_scores"][p] = mae_val

            policy_totals[p] += ret
            policy_mae[p] += mae_val

            if bldg_name in building_stats:
                building_stats[bldg_name][p]["total_return"] += ret
                building_stats[bldg_name][p]["scenarios_count"] += 1

            if climate_family in climate_stats:
                climate_stats[climate_family][p]["total_return"] += ret
                climate_stats[climate_family][p]["scenarios_count"] += 1

        # Deficit of pid_water vs other baselines
        rec["pid_water_advantage_over_fixed"] = rec["returns"]["pid_water"] - rec["returns"]["fixed_setpoint"]
        rec["pid_water_advantage_over_pid"] = rec["returns"]["pid_water"] - rec["returns"]["pid"]

        scenario_records.append(rec)

    # Compute overall benchmarks
    overall_summary = {}
    for p in POLICIES:
        mean_ret = policy_totals[p] / len(raw_data)
        overall_mae = policy_mae[p] / len(raw_data)
        overall_summary[p] = {
            "total_return": policy_totals[p],
            "mean_scenario_return": mean_ret,
            "mae_score": overall_mae,
        }

    # Format building summary
    building_summary = {}
    for b, b_data in building_stats.items():
        building_summary[b] = {
            "tau_hours": BUILDING_PROPERTIES[b]["tau_hours"],
            "archetype": BUILDING_PROPERTIES[b]["archetype"],
            "K_ahus": BUILDING_PROPERTIES[b]["K_ahus"],
            "V_zones": BUILDING_PROPERTIES[b]["V_zones"],
            "policy_mae": {
                p: abs(b_data[p]["total_return"] / (b_data[p]["scenarios_count"] * 8640.0))
                for p in POLICIES
            },
            "policy_mean_return": {
                p: b_data[p]["total_return"] / b_data[p]["scenarios_count"]
                for p in POLICIES
            },
        }

    # Format climate summary
    climate_summary = {}
    for c, c_data in climate_stats.items():
        climate_summary[c] = {
            "regime": CLIMATE_PROPERTIES[c]["regime"],
            "policy_mae": {
                p: abs(c_data[p]["total_return"] / (c_data[p]["scenarios_count"] * 8640.0))
                for p in POLICIES
            },
            "policy_mean_return": {
                p: c_data[p]["total_return"] / c_data[p]["scenarios_count"]
                for p in POLICIES
            },
        }

    audit_matrix = {
        "schema_version": "v1.0",
        "description": "Deconstructed baseline returns across 30 scenarios, buildings, and climates",
        "total_scenarios": len(raw_data),
        "overall_summary": overall_summary,
        "building_summary": building_summary,
        "climate_summary": climate_summary,
        "scenarios": scenario_records,
    }

    # Save JSON matrix
    OUTPUT_MATRIX_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_MATRIX_PATH, "w", encoding="utf-8") as f:
        json.dump(audit_matrix, f, indent=2)

    return audit_matrix


if __name__ == "__main__":
    matrix = audit_baselines()
    print("Baseline audit completed successfully.")
    print("Total scenarios processed:", matrix["total_scenarios"])
    for p, stats in matrix["overall_summary"].items():
        print(f"  {p:16s} -> MAE: {stats['mae_score']:.4f} | Total: {stats['total_return']:10.2f}")
