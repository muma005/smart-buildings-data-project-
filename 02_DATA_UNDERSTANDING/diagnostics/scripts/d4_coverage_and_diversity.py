"""D4 Coverage, Diversity and Limitations Diagnostic Script.
Computes comprehensive distributions of:
1. Building geometric, HVAC, and derived thermal characteristics (U, C, time constant).
2. Weather strip meteorological characteristics across the 30 official training scenarios.
3. Analysis of the non-Cartesian sampling structure and cross-building confounding.
Generates diagnostics/outputs/d4_diversity_metrics.json.
"""

import sys
import json
from pathlib import Path
import yaml
import numpy as np
import pandas as pd

WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(WORKSPACE_ROOT))

from smart_buildings.smart_control.utils.materials import facade_u, envelope_capacity

MANIFEST_PATH = WORKSPACE_ROOT / "smart_buildings" / "training_set.yaml"
BUILDINGS_DIR = WORKSPACE_ROOT / "smart_buildings" / "buildings"
WEATHER_DIR = WORKSPACE_ROOT / "smart_buildings" / "weather"
WEATHER_CSV_DIR = WORKSPACE_ROOT / "smart_buildings" / "weather" / "csv"
SCHEMAS_JSON = WORKSPACE_ROOT / "02_DATA_UNDERSTANDING" / "diagnostics" / "outputs" / "d2_building_schemas.json"
OUTPUT_JSON = WORKSPACE_ROOT / "02_DATA_UNDERSTANDING" / "diagnostics" / "outputs" / "d4_diversity_metrics.json"

def analyze_buildings():
    with open(SCHEMAS_JSON, "r", encoding="utf-8") as f:
        schemas = json.load(f)
        
    bldg_metrics = {}
    for b_file in BUILDINGS_DIR.glob("*.yaml"):
        b_name = b_file.stem
        with open(b_file, "r", encoding="utf-8") as f:
            b_cfg = yaml.safe_load(f)
            
        mat = b_cfg.get("materials", {})
        k_ext = mat.get("exterior_cv_conductivity", 0.3)
        rho_ext = mat.get("exterior_cv_density", 1200.0)
        cp_ext = mat.get("exterior_cv_heat_capacity", 900.0)
        
        # Derived physical characteristics using materials dict
        u_val = float(facade_u(mat))
        c_val = float(envelope_capacity(mat))  # J / (m^3 K)
        # Relative thermal time constant index ~ C / U
        time_constant_index = float(c_val / (u_val * 1e5))
        
        sch = schemas.get(b_name, {})
        K = sch.get("num_ahus_K", b_cfg["ahu"]["num_ahus"])
        V = sch.get("num_zones_V", 30)
        
        zones_per_ahu = V / K if K > 0 else 0.0
        
        bldg_metrics[b_name] = {
            "name": b_name,
            "width_cm": b_cfg["floor_plan"]["width"],
            "height_cm": b_cfg["floor_plan"]["height"],
            "num_floors": b_cfg["floor_plan"]["num_floors"],
            "shape": b_cfg["floor_plan"]["building_shape"],
            "min_room_size_cm": b_cfg["floor_plan"]["min_room_size"],
            "max_room_size_cm": b_cfg["floor_plan"]["max_room_size"],
            "num_ahus_K": K,
            "num_zones_V": V,
            "avg_zones_per_ahu": round(zones_per_ahu, 2),
            "materials": mat,
            "derived_facade_U_W_per_m2_K": round(u_val, 4),
            "derived_envelope_capacity_J_per_m3_K": round(c_val, 1),
            "relative_time_constant_index": round(time_constant_index, 2),
            "observation_dim": sch.get("observation_dimension"),
            "discrete_action_dim": sch.get("discrete_action_dim"),
            "continuous_action_dim": sch.get("continuous_action_dim")
        }
    return bldg_metrics

def analyze_weather_strips():
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = yaml.safe_load(f)
        
    scenarios = manifest.get("scenarios", [])
    strip_metrics = {}
    
    # Cache loaded CSVs
    csv_cache = {}
    
    for s in scenarios:
        w_name = s["weather"]
        b_name = s["building"]
        w_yaml_path = WEATHER_DIR / f"{w_name}.yaml"
        with open(w_yaml_path, "r", encoding="utf-8") as f:
            w_cfg = yaml.safe_load(f)
            
        csv_rel = w_cfg["weather_csv"]
        csv_path = WEATHER_DIR / csv_rel
        
        if csv_rel not in csv_cache:
            df = pd.read_csv(csv_path)
            df['dt'] = pd.to_datetime(df['Time'], format="%Y%m%d-%H%M", utc=True)
            csv_cache[csv_rel] = df
            
        df = csv_cache[csv_rel]
        start_ts = pd.Timestamp(w_cfg["start_timestamp"], tz="UTC")
        end_ts = start_ts + pd.Timedelta(30, unit="days")
        
        mask = (df['dt'] >= start_ts) & (df['dt'] < end_ts)
        strip_df = df[mask]
        
        temps_c = strip_df['TempC'].to_numpy()
        temps_f = strip_df['TempF'].to_numpy()
        
        # Calculate diurnal swing: daily max - daily min averaged over 30 days
        strip_df = strip_df.copy()
        strip_df['date'] = strip_df['dt'].dt.date
        daily_swings = strip_df.groupby('date')['TempC'].apply(lambda x: x.max() - x.min())
        avg_diurnal_swing = float(daily_swings.mean())
        
        # Heating degree days (base 18 C) and Cooling degree days (base 18 C)
        daily_means = strip_df.groupby('date')['TempC'].mean()
        hdd_18 = float(np.sum(np.maximum(0, 18.0 - daily_means)))
        cdd_18 = float(np.sum(np.maximum(0, daily_means - 18.0)))
        
        strip_metrics[f"{b_name}/{w_name}"] = {
            "building": b_name,
            "weather_preset": w_name,
            "station": w_name.split("_")[0],
            "start_timestamp": str(start_ts),
            "end_timestamp": str(end_ts),
            "convection_coefficient": w_cfg.get("convection_coefficient"),
            "num_hours": len(strip_df),
            "temp_c_min": round(float(np.min(temps_c)), 2),
            "temp_c_max": round(float(np.max(temps_c)), 2),
            "temp_c_mean": round(float(np.mean(temps_c)), 2),
            "temp_c_std": round(float(np.std(temps_c)), 2),
            "avg_diurnal_swing_C": round(avg_diurnal_swing, 2),
            "hdd_base_18C": round(hdd_18, 1),
            "cdd_base_18C": round(cdd_18, 1)
        }
        
    return strip_metrics

def main():
    print("Executing D4 Coverage and Diversity Analysis...")
    bldg_metrics = analyze_buildings()
    strip_metrics = analyze_weather_strips()
    
    # Station aggregate statistics
    station_stats = {}
    for scen_key, m in strip_metrics.items():
        st = m["station"]
        if st not in station_stats:
            station_stats[st] = {
                "min_observed": 999.0,
                "max_observed": -999.0,
                "means": [],
                "swings": [],
                "hdds": [],
                "cdds": []
            }
        station_stats[st]["min_observed"] = min(station_stats[st]["min_observed"], m["temp_c_min"])
        station_stats[st]["max_observed"] = max(station_stats[st]["max_observed"], m["temp_c_max"])
        station_stats[st]["means"].append(m["temp_c_mean"])
        station_stats[st]["swings"].append(m["avg_diurnal_swing_C"])
        station_stats[st]["hdds"].append(m["hdd_base_18C"])
        station_stats[st]["cdds"].append(m["cdd_base_18C"])
        
    station_summary = {}
    for st, data in station_stats.items():
        station_summary[st] = {
            "absolute_min_C": data["min_observed"],
            "absolute_max_C": data["max_observed"],
            "average_mean_C": round(float(np.mean(data["means"])), 2),
            "average_diurnal_swing_C": round(float(np.mean(data["swings"])), 2),
            "average_hdd_18C": round(float(np.mean(data["hdds"])), 1),
            "average_cdd_18C": round(float(np.mean(data["cdds"])), 1),
        }
        
    output_data = {
        "buildings_diversity": bldg_metrics,
        "station_summary": station_summary,
        "scenario_weather_metrics": strip_metrics
    }
    
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as fp:
        json.dump(output_data, fp, indent=2)
        
    print(f"Coverage metrics saved to {OUTPUT_JSON}")
    print("\nStation Climatic Diversity Summary:")
    for st, s in sorted(station_summary.items()):
        print(f"  {st:12s}: Range [{s['absolute_min_C']:5.1f} C to {s['absolute_max_C']:5.1f} C], Mean: {s['average_mean_C']:4.1f} C, Diurnal Swing: {s['average_diurnal_swing_C']:4.1f} C, HDD: {s['average_hdd_18C']:5.1f}, CDD: {s['average_cdd_18C']:5.1f}")
        
    print("\nBuilding Structural Diversity Summary:")
    for b_name, b in sorted(bldg_metrics.items()):
        print(f"  {b_name:18s}: Floors={b['num_floors']}, AHUs={b['num_ahus_K']}, Zones={b['num_zones_V']:2d}, Zones/AHU={b['avg_zones_per_ahu']:4.1f}, Facade U={b['derived_facade_U_W_per_m2_K']:.3f}, Tau_index={b['relative_time_constant_index']:.2f}")

if __name__ == "__main__":
    main()
