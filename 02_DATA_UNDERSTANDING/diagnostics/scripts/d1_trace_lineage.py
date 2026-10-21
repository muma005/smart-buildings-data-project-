"""D1 Data Lineage and Provenance Trace Script.
Traces specific data elements through their end-to-end transformation pathways:
1. Weather: Raw CSV row -> ReplayWeatherController -> Observation -> Normalized Obs.
2. Building: YAML config -> Scenario Gin -> Building Object -> Thermal Model.
3. Occupancy & Internal Gains: Markov Occupancy -> Sensible Heat -> Zone Thermal Input.
4. Reward: Physical Step -> Cost/Carbon/Comfort Objects -> Step Reward -> Scenario Mean.
Generates evidence/PROVENANCE_REGISTER.csv.
"""

import sys
import csv
import json
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(WORKSPACE_ROOT))

import pandas as pd
import numpy as np

from smart_buildings.evaluate import (
    load_hybrid_environment,
    create_building_meta_data,
    initialize_policy,
    get_policy_action,
    validate_action,
)
from smart_buildings.baselines.all_off import AllOffPolicy
from smart_buildings.smart_control.utils import conversion_utils as utils

OUTPUT_CSV = WORKSPACE_ROOT / "02_DATA_UNDERSTANDING" / "evidence" / "PROVENANCE_REGISTER.csv"
OUTPUT_JSON = WORKSPACE_ROOT / "02_DATA_UNDERSTANDING" / "diagnostics" / "outputs" / "d1_provenance_trace.json"

def trace_weather():
    csv_path = WORKSPACE_ROOT / "smart_buildings" / "weather" / "csv" / "atlanta.csv"
    df = pd.read_csv(csv_path)
    df['Time_dt'] = pd.to_datetime(df['Time'], format="%Y%m%d-%H%M", utc=True)
    
    # Target timestamp for atlanta_2: 2023-03-05 06:00 UTC
    target_ts = pd.Timestamp("2023-03-05 06:00:00", tz="UTC")
    row = df[df['Time_dt'] == target_ts].iloc[0]
    
    raw_time_str = str(row['Time'])
    raw_temp_c = float(row['TempC'])
    raw_temp_f = float(row['TempF'])
    raw_humidity = float(row['Humidity'])
    raw_wind = float(row['WindspeedKmph'])
    raw_dewpoint = float(row['DewPointC'])
    
    # Trace conversion
    expected_k = utils.fahrenheit_to_kelvin(raw_temp_f)
    
    return {
        "raw_csv": str(csv_path.name),
        "target_ts_utc": str(target_ts),
        "raw_time_str": raw_time_str,
        "raw_temp_c": raw_temp_c,
        "raw_temp_f": raw_temp_f,
        "raw_humidity": raw_humidity,
        "raw_wind_kmph": raw_wind,
        "raw_dewpoint_c": raw_dewpoint,
        "converted_temp_kelvin": float(expected_k),
        "used_in_simulator": {
            "TempF": "Used directly for outdoor air temperature (linear interpolation in time, converted to Kelvin)",
            "TempC": "Unused (TempF preferred)",
            "Humidity": "Unused (never called by simulator)",
            "WindspeedKmph": "Unused (convection coefficient is fixed constant)",
            "DewPointC": "Unused"
        }
    }

def trace_environment_step():
    scenario_dir = WORKSPACE_ROOT / "smart_buildings" / "training_scenarios" / "building_train_1" / "atlanta_2"
    gin_path = scenario_dir / "config.gin"
    
    env = load_hybrid_environment(gin_path)
    env.metrics_path = None
    env._occupancy_normalization_constant = 125.0
    
    metadata = create_building_meta_data(env, scenario_dir)
    action_spec = env.action_spec()
    policy = initialize_policy(AllOffPolicy, metadata, action_spec)
    
    reset_ret = env.reset()
    obs_0 = reset_ret[0] if isinstance(reset_ret, tuple) else reset_ret
    
    # Extract outside temp from observation
    field_names = metadata["observation_field_names"]
    outside_temp_idx = None
    for idx, name in enumerate(field_names):
        if "outside_air_temperature" in name or "ambient" in name:
            outside_temp_idx = idx
            break
            
    norm_outside_temp = float(obs_0[outside_temp_idx]) if outside_temp_idx is not None else None
    
    # Step environment
    raw_action = get_policy_action(policy, obs_0)
    action = validate_action(raw_action, action_spec)
    step_ret = env.step(action)
    
    obs_1 = step_ret[0]
    reward_1 = float(step_ret[1])
    
    # Inspect reward components stored inside env._reward_fn or simulator
    sim = env.building.simulator
    hvac = sim._hvac
    bldg = sim.building
    
    # Building thermal stats
    zone_temps = bldg.get_zone_average_temps()
    sample_zone = list(zone_temps.keys())[0]
    sample_zone_temp = float(zone_temps[sample_zone])
    
    # Material properties from building and scenario config
    scen_yaml_path = scenario_dir / "config.yaml"
    import yaml
    with open(scen_yaml_path, "r", encoding="utf-8") as yf:
        scen_yaml = yaml.safe_load(yf)
    materials_trace = scen_yaml.get("materials", {})
    materials_trace["unique_conductivities_in_grid"] = [float(x) for x in np.unique(bldg.conductivity)]
    materials_trace["unique_densities_in_grid"] = [float(x) for x in np.unique(bldg.density)]
    
    return {
        "outside_temp_feature_name": field_names[outside_temp_idx] if outside_temp_idx is not None else "None",
        "outside_temp_feature_index": outside_temp_idx,
        "normalized_outside_temp_step_0": norm_outside_temp,
        "sample_zone": sample_zone,
        "sample_zone_temp_kelvin": sample_zone_temp,
        "materials": materials_trace,
        "step_1_reward": reward_1,
        "internal_gain_w_per_m2": float(sim._internal_gain_w_per_m2),
        "internal_gain_standby_fraction": float(sim._internal_gain_standby_fraction),
        "occupant_sensible_heat_w": float(sim._occupant_sensible_heat_w)
    }

def create_provenance_register():
    register_rows = [
        {
            "variable_name": "outside_air_temperature",
            "category": "Weather / Environment",
            "source_origin": "Historical weather station CSV (smart_buildings/weather/csv/*.csv)",
            "raw_representation": "TempF (degrees Fahrenheit) recorded hourly",
            "intermediate_transformations": "Time mapped to UTC epoch seconds -> np.interp linear interpolation to 5-min step -> fahrenheit_to_kelvin(T_F)",
            "simulator_consumer": "SimulatorFlexibleGeometries.execute_step_sim -> ambient_temperature boundary condition in finite_differences_timestep",
            "policy_observation_path": "Mapped into observation vector via ObservationNormalizer (centered at 294 K, scaled by 20 K)",
            "policy_access": "Live live observation (index 0 / outside_air_temperature)",
            "notes": "Raw CSV also includes TempC, DewPointC, Windspeed, Humidity, which are completely ignored by thermal simulator"
        },
        {
            "variable_name": "convection_coefficient",
            "category": "Weather / Envelope Physics",
            "source_origin": "Weather strip YAML configuration (smart_buildings/weather/*.yaml)",
            "raw_representation": "convection_coefficient: float (e.g. 19.1 W/(m^2 K))",
            "intermediate_transformations": "Loaded via Gin config into ReplayWeatherController(convection_coefficient=...)",
            "simulator_consumer": "Passed to finite_differences_timestep to govern external film heat transfer rate UA_film",
            "policy_observation_path": "Not exposed to policy observation",
            "policy_access": "Hidden simulator parameter",
            "notes": "Does not vary with wind speed; constant throughout the 30-day episode"
        },
        {
            "variable_name": "building_geometry_floor_plan",
            "category": "Building Geometry",
            "source_origin": "Procedural floorplan generator (run_floor_generator.py -> config_generator.py)",
            "raw_representation": "Width, height, floors, min/max room size, building shape, composite style in building YAML",
            "intermediate_transformations": "Rasterized into 2D grid matrix floor_plan.npy (0=unconditioned/exterior, 1=interior, 2=wall)",
            "simulator_consumer": "FloorPlanBasedBuilding initializes finite difference control volumes and wall conductances",
            "policy_observation_path": "Provided in static metadata['floor_plan'] (2D numpy array)",
            "policy_access": "Supplied at policy initialization via building_metadata",
            "notes": "Exact geometry coordinates visible to policy at start"
        },
        {
            "variable_name": "building_zone_map",
            "category": "Building Geometry / Topology",
            "source_origin": "Room partitioning algorithm (building_utils.py -> room segmentation)",
            "raw_representation": "2D grid matrix zone_map.npy with integer zone indices",
            "intermediate_transformations": "Saved as zone_map.npy; rooms mapped to named zones (zone_1, zone_2, ...)",
            "simulator_consumer": "Groups control volumes into thermal zones for area-weighted averaging and HVAC terminal assignment",
            "policy_observation_path": "Provided in static metadata['zone_map'] (2D numpy array) and metadata['ahu_zone_assignments']",
            "policy_access": "Supplied at policy initialization via building_metadata",
            "notes": "Defines which rooms belong to which AHU"
        },
        {
            "variable_name": "envelope_material_properties",
            "category": "Thermal Physics / Envelope",
            "source_origin": "Latin Hypercube Sampling across 6 physical bounds (materials.py)",
            "raw_representation": "6 floats in building YAML: exterior_cv_conductivity, exterior_cv_density, exterior_cv_heat_capacity, interior_wall_cv_conductivity, interior_wall_cv_density, interior_mass_cv_density",
            "intermediate_transformations": "Written to config.gin -> injected into FloorPlanBasedBuilding constructor",
            "simulator_consumer": "Sets conductance matrix G and capacitance vector C for implicit Euler finite-difference heat diffusion solver",
            "policy_observation_path": "NOT directly exposed in observation or metadata",
            "policy_access": "Hidden simulator physical state",
            "notes": "Policy must infer thermal dynamics or adapt without explicit material labels"
        },
        {
            "variable_name": "zone_air_temperature",
            "category": "Thermal State / Sensor",
            "source_origin": "Simulator finite differences solver",
            "raw_representation": "Control volume temperatures updated by Crank-Nicolson / implicit finite differences diffusion",
            "intermediate_transformations": "Area-weighted spatial mean across CVs in zone -> vav.zone_air_temperature in Kelvin",
            "simulator_consumer": "Used by VAV thermostat and comfort regret calculation",
            "policy_observation_path": "Normalized by ObservationNormalizer: (T - 294.0) / 20.0 -> [-1, 1]",
            "policy_access": "Live observation (indices tracked in metadata['zone_temp_indices'])",
            "notes": "Primed at reset from initial building temperature grid (293.15 K) to prevent 0 K sentinel artifact"
        },
        {
            "variable_name": "occupancy_count",
            "category": "Occupant Disturbance",
            "source_origin": "RandomizedArrivalDepartureOccupancy model (Markov arrival/departure process)",
            "raw_representation": "Stochastic discrete person count per zone per timestep",
            "intermediate_transformations": "Integrated over 5-minute interval -> average person-hours",
            "simulator_consumer": "Multiplied by 70.0 W to inject sensible thermal power into zone; weights comfort shortfall in reward",
            "policy_observation_path": "Building-level aggregate occupancy is exposed in live observation; individual zone occupancies are NOT directly given",
            "policy_access": "Building-level occupancy in live observation; zone-level occupancy hidden",
            "notes": "Comfort penalty weight is proportional to zone occupancy, not zone floor area"
        },
        {
            "variable_name": "internal_gains",
            "category": "Thermal Loads",
            "source_origin": "Scenario configuration (internal_gain_w_per_m2, default 10.0 W/m^2)",
            "raw_representation": "W/m^2 multiplied by standby fraction (0.2) outside comfort hours",
            "intermediate_transformations": "watts_per_cv = gain * cv_area * fraction -> added to zone_q_aggregate",
            "simulator_consumer": "Injected into thermal finite differences power vector input_q",
            "policy_observation_path": "Not directly observed (indirectly reflected in comfort schedule flags)",
            "policy_access": "Hidden load parameter",
            "notes": "Square wave following comfort mode schedule"
        },
        {
            "variable_name": "electricity_consumption_and_cost",
            "category": "Energy & Cost Accounting",
            "source_origin": "Equipment power models (fans, chillers/heat pumps, pumps)",
            "raw_representation": "Instantaneous electrical watts consumed during 5-minute step",
            "intermediate_transformations": "Converted to kWh -> multiplied by time-of-use tariff ($0.16/0.18/0.20 per kWh) -> normalized by 80,000 W * K",
            "simulator_consumer": "Recorded in SimulationTracker and fed to reward function",
            "policy_observation_path": "Not exposed in live observation during the step",
            "policy_access": "Post-step reward and diagnostic evaluation",
            "notes": "Tariff is a piecewise hourly schedule configured in gin"
        },
        {
            "variable_name": "natural_gas_consumption_and_cost",
            "category": "Energy & Cost Accounting",
            "source_origin": "Boiler heating duty for hot water reheat loop",
            "raw_representation": "Instantaneous natural gas watts consumed by boiler",
            "intermediate_transformations": "Converted to Therms / Joules -> multiplied by gas price -> normalized by 205,000 W * K",
            "simulator_consumer": "Recorded in SimulationTracker and fed to reward function",
            "policy_observation_path": "Not exposed in live observation during the step",
            "policy_access": "Post-step reward and diagnostic evaluation",
            "notes": "Boiler efficiency factor applies"
        },
        {
            "variable_name": "carbon_emissions",
            "category": "Environmental Impact",
            "source_origin": "Electricity & natural gas consumption rates",
            "raw_representation": "kg CO2 emitted per step",
            "intermediate_transformations": "Electricity consumption * hourly emissions factor (kg CO2/kWh) + Gas consumption * gas emissions factor",
            "simulator_consumer": "Fed to setpoint_energy_carbon_regret reward calculation",
            "policy_observation_path": "Not exposed in live observation during the step",
            "policy_access": "Post-step reward and diagnostic evaluation",
            "notes": "Grid carbon intensity fluctuates hourly"
        },
        {
            "variable_name": "per_step_reward",
            "category": "Evaluation Metric",
            "source_origin": "setpoint_energy_carbon_regret.py",
            "raw_representation": "r_t = 0.6 * p_t - 0.2 * c_t - 0.2 * e_t (all non-positive)",
            "intermediate_transformations": "Occupancy-weighted comfort shortfall (linear <= 5K, quadratic > 5K), normalized cost, normalized carbon",
            "simulator_consumer": "Summed over 8,640 steps -> Episode Return -> Scenario Mean R / 8640",
            "policy_observation_path": "Returned as step reward from env.step(action)",
            "policy_access": "Returned post-action in RL step tuple; not an input to get_action(obs)",
            "notes": "Leaderboard score is MAE of scenario means against zero (Score = -mean(r_bar))"
        }
    ]
    
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=list(register_rows[0].keys()))
        writer.writeheader()
        writer.writerows(register_rows)
        
    print(f"Wrote {len(register_rows)} lineage records to {OUTPUT_CSV}")

def main():
    weather_trace = trace_weather()
    step_trace = trace_environment_step()
    
    full_trace = {
        "weather_lineage_example": weather_trace,
        "environment_step_trace": step_trace
    }
    
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as fp:
        json.dump(full_trace, fp, indent=2)
        
    print(f"Trace data saved to {OUTPUT_JSON}")
    create_provenance_register()
    print("D1 PROVENANCE INVESTIGATION COMPLETE!")

if __name__ == "__main__":
    main()
