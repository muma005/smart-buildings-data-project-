"""D2 Schema Invariants and Data Dictionary Generator.
Audits observation and action spaces across all 6 shipped buildings,
verifies mathematical invariants D = K + 1 and C = 3K + 2 + 2V,
and generates evidence/DATA_DICTIONARY.csv.
"""

import sys
import csv
import json
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(WORKSPACE_ROOT))

from smart_buildings.evaluate import (
    load_hybrid_environment,
    create_building_meta_data,
)
from smart_buildings.smart_control.environment import hybrid_action_environment

OUTPUT_JSON = WORKSPACE_ROOT / "02_DATA_UNDERSTANDING" / "diagnostics" / "outputs" / "d2_building_schemas.json"
OUTPUT_CSV = WORKSPACE_ROOT / "02_DATA_UNDERSTANDING" / "evidence" / "DATA_DICTIONARY.csv"

# Select one scenario for each of the 6 buildings from training_set.yaml
SAMPLE_SCENARIOS = {
    "building_train_1": "atlanta_2",
    "building_train_2": "atlanta_3",
    "building_train_4": "atlanta_5",
    "building_train_5": "atlanta_6",
    "building_train_7": "atlanta_8",
    "building_train_8": "atlanta_1",
}

def audit_building_schemas():
    results = {}
    
    for b_name, w_name in SAMPLE_SCENARIOS.items():
        scen_dir = WORKSPACE_ROOT / "smart_buildings" / "training_scenarios" / b_name / w_name
        gin_path = scen_dir / "config.gin"
        
        print(f"Auditing schema for {b_name} ({w_name})...")
        env = load_hybrid_environment(gin_path)
        env.metrics_path = None
        env._occupancy_normalization_constant = 125.0
        
        metadata = create_building_meta_data(env, scen_dir)
        action_spec = env.action_spec()
        observation_spec = env.observation_spec()
        
        obs_dim = int(observation_spec.shape[0])
        discrete_dim = int(action_spec[hybrid_action_environment.DISCRETE_ACTION].shape[0])
        continuous_dim = int(action_spec[hybrid_action_environment.CONTINUOUS_ACTION].shape[0])
        
        K = len(metadata["ahu_zone_assignments"])  # AHUs
        # Zone count V: number of zones in ahu_zone_assignments or zone_temp_indices
        V_zone_temp = len(metadata["zone_temp_indices"])
        V_total_assigned = sum(len(zones) for zones in metadata["ahu_zone_assignments"].values())
        
        expected_D = K + 1
        expected_C = 3 * K + 2 + 2 * V_zone_temp
        
        d_matches = (discrete_dim == expected_D)
        c_matches = (continuous_dim == expected_C)
        
        results[b_name] = {
            "building": b_name,
            "sample_weather": w_name,
            "num_ahus_K": K,
            "num_zones_V": V_zone_temp,
            "total_assigned_zones": V_total_assigned,
            "observation_dimension": obs_dim,
            "discrete_action_dim": discrete_dim,
            "expected_discrete_dim": expected_D,
            "discrete_dim_invariant_holds": d_matches,
            "continuous_action_dim": continuous_dim,
            "expected_continuous_dim": expected_C,
            "continuous_dim_invariant_holds": c_matches,
            "observation_field_names_count": len(metadata["observation_field_names"]),
            "zone_action_indices_count": len(metadata["zone_action_indices"]),
            "zone_temp_indices_count": len(metadata["zone_temp_indices"]),
            "temp_indices_count": len(metadata["temp_indices"]),
            "pressure_indices_count": len(metadata["pressure_indices"]),
            "water_indices_count": len(metadata["water_indices"]),
            "recirculation_indices_count": len(metadata["recirculation_indices"]),
            "floor_plan_shape": list(metadata["floor_plan"].shape),
            "zone_map_shape": list(metadata["zone_map"].shape),
            "num_floors": metadata["num_floors"],
            "morning_start_hour": metadata["morning_start_hour"],
            "evening_start_hour": metadata["evening_start_hour"],
            "comfort_temp_window": list(metadata["comfort_temp_window"]),
            "eco_temp_window": list(metadata["eco_temp_window"]),
        }
        print(f"  {b_name}: K={K}, V={V_zone_temp} -> D={discrete_dim} (exp {expected_D}, {d_matches}), C={continuous_dim} (exp {expected_C}, {c_matches}), Obs={obs_dim}")
        
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as fp:
        json.dump(results, fp, indent=2)
        
    print(f"All building schemas audited and saved to {OUTPUT_JSON}")
    return results

def generate_data_dictionary():
    dict_entries = [
        # Metadata
        {
            "field_name": "n_discrete_action",
            "entity": "Building Metadata",
            "description": "Total count of binary on/off control commands for plant equipment",
            "source": "env.action_spec()['discrete_action'].shape[0]",
            "data_type": "int",
            "physical_units": "count",
            "representation": "Native scalar",
            "granularity": "Per-building static",
            "expected_range": "[4, 8]",
            "allowed_values": "Integers >= 2",
            "missing_value_convention": "None (always present)",
            "transformation": "D = K + 1",
            "timestamp_meaning": "Static at initialization",
            "policy_availability": "A (Supplied at initialization)",
            "source_code_reference": "smart_buildings/evaluate.py:create_building_meta_data"
        },
        {
            "field_name": "n_continuous_action",
            "entity": "Building Metadata",
            "description": "Total count of continuous setpoint and damper controls",
            "source": "env.action_spec()['continuous_action'].shape[0]",
            "data_type": "int",
            "physical_units": "count",
            "representation": "Native scalar",
            "granularity": "Per-building static",
            "expected_range": "[68, 172]",
            "allowed_values": "Integers > 0",
            "missing_value_convention": "None (always present)",
            "transformation": "C = 3K + 2 + 2V",
            "timestamp_meaning": "Static at initialization",
            "policy_availability": "A (Supplied at initialization)",
            "source_code_reference": "smart_buildings/evaluate.py:create_building_meta_data"
        },
        {
            "field_name": "floor_plan",
            "entity": "Building Geometry",
            "description": "2D raster layout of building floor plan (0: exterior, 1: room space, 2: interior wall)",
            "source": "floor_plan.npy",
            "data_type": "numpy.ndarray (int32)",
            "physical_units": "grid cells (1 cell = 100cm x 100cm)",
            "representation": "Spatial matrix [height, width]",
            "granularity": "Building footprint",
            "expected_range": "{0, 1, 2}",
            "allowed_values": "0, 1, 2",
            "missing_value_convention": "None",
            "transformation": "Rasterized from procedural CAD geometry",
            "timestamp_meaning": "Static at initialization",
            "policy_availability": "A (Supplied at initialization)",
            "source_code_reference": "smart_buildings/smart_control/simulator/building.py"
        },
        {
            "field_name": "zone_map",
            "entity": "Building Geometry",
            "description": "2D spatial partition map assigning each cell to an integer zone index",
            "source": "zone_map.npy",
            "data_type": "numpy.ndarray (int32)",
            "physical_units": "zone index",
            "representation": "Spatial matrix [height, width]",
            "granularity": "Building footprint",
            "expected_range": "[0, V]",
            "allowed_values": "Integers >= 0",
            "missing_value_convention": "0 indicates unconditioned / non-zone space",
            "transformation": "Procedural room segmentation",
            "timestamp_meaning": "Static at initialization",
            "policy_availability": "A (Supplied at initialization)",
            "source_code_reference": "smart_buildings/smart_control/simulator/building.py"
        },
        {
            "field_name": "ahu_zone_assignments",
            "entity": "HVAC Topology",
            "description": "Mapping from AHU identifiers (e.g. 'ahs_ahu_1') to lists of served zone names",
            "source": "Scenario configuration / HVAC graph",
            "data_type": "dict[str, list[str]]",
            "physical_units": "identifiers",
            "representation": "Topology dictionary",
            "granularity": "Building topology",
            "expected_range": "1 to 10 zones per AHU",
            "allowed_values": "Valid zone room identifiers",
            "missing_value_convention": "None (all physical zones assigned)",
            "transformation": "K-means spatial clustering of zone centroids",
            "timestamp_meaning": "Static at initialization",
            "policy_availability": "A (Supplied at initialization)",
            "source_code_reference": "smart_buildings/smart_control/simulator/building.py"
        },
        {
            "field_name": "comfort_temp_window",
            "entity": "Schedule / Comfort",
            "description": "Lower and upper permissible air temperature bounds during comfort hours",
            "source": "Scenario configuration",
            "data_type": "tuple[float, float]",
            "physical_units": "Kelvin",
            "representation": "Native temperatures",
            "granularity": "Building-wide schedule",
            "expected_range": "[294.0, 297.0] (~20.85 C to 23.85 C)",
            "allowed_values": "Positive floats in K",
            "missing_value_convention": "None",
            "transformation": "Configured in scenario generator",
            "timestamp_meaning": "Applies when is_comfort_mode=True",
            "policy_availability": "A (Supplied at initialization)",
            "source_code_reference": "smart_buildings/smart_control/simulator/setpoint_schedule.py"
        },
        {
            "field_name": "eco_temp_window",
            "entity": "Schedule / Comfort",
            "description": "Lower and upper permissible air temperature bounds during eco (unoccupied) hours",
            "source": "Scenario configuration",
            "data_type": "tuple[float, float]",
            "physical_units": "Kelvin",
            "representation": "Native temperatures",
            "granularity": "Building-wide schedule",
            "expected_range": "[289.0, 298.0] (~15.85 C to 24.85 C)",
            "allowed_values": "Positive floats in K",
            "missing_value_convention": "None",
            "transformation": "Configured in scenario generator",
            "timestamp_meaning": "Applies when is_comfort_mode=False",
            "policy_availability": "A (Supplied at initialization)",
            "source_code_reference": "smart_buildings/smart_control/simulator/setpoint_schedule.py"
        },
        # Live Observation Fields
        {
            "field_name": "outside_air_temperature_sensor",
            "entity": "Observation / Sensor",
            "description": "Measured ambient outside air temperature",
            "source": "ReplayWeatherController.get_current_temp",
            "data_type": "float32",
            "physical_units": "Kelvin (or normalized)",
            "representation": "Continuous sensor reading",
            "granularity": "5-minute step",
            "expected_range": "[230.0, 325.0] K",
            "allowed_values": "Finite floats",
            "missing_value_convention": "Last observed carried forward",
            "transformation": "Linear interpolation from hourly weather CSV",
            "timestamp_meaning": "Instantaneous measurement at step start",
            "policy_availability": "B (Supplied live during operation)",
            "source_code_reference": "smart_buildings/smart_control/simulator/weather_controller.py"
        },
        {
            "field_name": "zone_air_temperature_sensor",
            "entity": "Observation / Sensor",
            "description": "Area-weighted average indoor air temperature for a specific thermal zone",
            "source": "FloorPlanBasedBuilding.get_zone_average_temps",
            "data_type": "float32",
            "physical_units": "Kelvin (or normalized)",
            "representation": "Continuous sensor reading",
            "granularity": "5-minute step",
            "expected_range": "[280.0, 315.0] K",
            "allowed_values": "Finite floats",
            "missing_value_convention": "Last observed carried forward",
            "transformation": "Area-weighted mean of finite-difference air control volumes",
            "timestamp_meaning": "Measured prior to current action execution",
            "policy_availability": "B (Supplied live during operation)",
            "source_code_reference": "smart_buildings/smart_control/simulator/simulator_flexible_floor_plan.py"
        },
        {
            "field_name": "discrete_action",
            "entity": "Policy Action",
            "description": "Binary commands controlling on/off operational state of each AHU and central HWS boiler",
            "source": "Policy get_action(obs)",
            "data_type": "int32 array [K+1]",
            "physical_units": "binary command {0: OFF, 1: ON}",
            "representation": "Discrete {0, 1}",
            "granularity": "5-minute step",
            "expected_range": "{0, 1}",
            "allowed_values": "0 or 1",
            "missing_value_convention": "Rejected action penalty (-inf) if missing or invalid",
            "transformation": "Mapped to 1.0 (ON) and -1.0 (OFF) in simulator",
            "timestamp_meaning": "Command executed across upcoming 5-minute interval",
            "policy_availability": "Action Output",
            "source_code_reference": "smart_buildings/smart_control/environment/hybrid_action_environment.py"
        },
        {
            "field_name": "continuous_action",
            "entity": "Policy Action",
            "description": "Normalized setpoint commands for AHUs (temp, pressure, recirc), HWS, and VAVs (damper, reheat)",
            "source": "Policy get_action(obs)",
            "data_type": "float32 array [3K + 2 + 2V]",
            "physical_units": "normalized scale [-1.0, 1.0]",
            "representation": "Bounded Box(-1.0, 1.0)",
            "granularity": "5-minute step",
            "expected_range": "[-1.0, 1.0]",
            "allowed_values": "Floats in [-1.0, 1.0]",
            "missing_value_convention": "Rejected action penalty (-inf) if out of bounds",
            "transformation": "Denormalized via BoundedActionNormalizer to physical engineering units",
            "timestamp_meaning": "Actuator target maintained across 5-minute interval",
            "policy_availability": "Action Output",
            "source_code_reference": "smart_buildings/smart_control/utils/bounded_action_normalizer.py"
        },
        # Reward components
        {
            "field_name": "comfort_penalty",
            "entity": "Evaluation / Reward",
            "description": "Occupancy-weighted piecewise temperature violation shortfall",
            "source": "SetpointEnergyCarbonRegret",
            "data_type": "float",
            "physical_units": "normalized regret <= 0",
            "representation": "Negative penalty",
            "granularity": "5-minute step",
            "expected_range": "(-inf, 0.0]",
            "allowed_values": "Floats <= 0.0",
            "missing_value_convention": "0.0 when occupancy is zero or all zones in comfort band",
            "transformation": "Linear shortfall up to 5K, quadratic beyond 5K, weighted by zone occupancy",
            "timestamp_meaning": "Calculated over elapsed 5-minute step",
            "policy_availability": "D (Post-evaluation output; returned in RL step tuple)",
            "source_code_reference": "smart_buildings/smart_control/reward/setpoint_energy_carbon_regret.py"
        },
        {
            "field_name": "step_reward",
            "entity": "Evaluation / Reward",
            "description": "Weighted combination of comfort regret (0.6), energy cost (0.2), and carbon emissions (0.2)",
            "source": "SetpointEnergyCarbonRegret.reward",
            "data_type": "float",
            "physical_units": "non-positive reward <= 0",
            "representation": "Negative scalar",
            "granularity": "5-minute step",
            "expected_range": "[-1.0, 0.0] typical; can exceed -1.0 under severe violations",
            "allowed_values": "Floats <= 0.0",
            "missing_value_convention": "None",
            "transformation": "r_t = 0.6 * p_t - 0.2 * c_t - 0.2 * e_t",
            "timestamp_meaning": "Calculated over elapsed 5-minute step",
            "policy_availability": "D (Returned in step tuple; NOT passed to get_action)",
            "source_code_reference": "smart_buildings/smart_control/reward/base_setpoint_energy_carbon_reward.py"
        }
    ]
    
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=list(dict_entries[0].keys()))
        writer.writeheader()
        writer.writerows(dict_entries)
        
    print(f"Generated {len(dict_entries)} data dictionary definitions into {OUTPUT_CSV}")

if __name__ == "__main__":
    audit_building_schemas()
    generate_data_dictionary()
