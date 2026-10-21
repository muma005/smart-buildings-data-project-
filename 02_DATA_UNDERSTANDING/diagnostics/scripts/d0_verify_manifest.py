"""D0 Manifest Verification Script.
Audits training_set.yaml against the filesystem, checking buildings, weather presets,
and shipped scenario directories.
"""

import sys
import yaml
from pathlib import Path
import json

WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
MANIFEST_PATH = WORKSPACE_ROOT / "smart_buildings" / "training_set.yaml"
BUILDINGS_DIR = WORKSPACE_ROOT / "smart_buildings" / "buildings"
WEATHER_DIR = WORKSPACE_ROOT / "smart_buildings" / "weather"
TRAIN_SCENARIOS_DIR = WORKSPACE_ROOT / "smart_buildings" / "training_scenarios"
EVAL_SCENARIOS_DIR = WORKSPACE_ROOT / "smart_buildings" / "evaluation_scenarios"
OUTPUT_JSON = WORKSPACE_ROOT / "02_DATA_UNDERSTANDING" / "diagnostics" / "outputs" / "d0_manifest_audit.json"

def audit_manifest():
    if not MANIFEST_PATH.exists():
        raise FileNotFoundError(f"Manifest not found at {MANIFEST_PATH}")
        
    with open(MANIFEST_PATH, "r", encoding="utf-8") as fp:
        manifest_data = yaml.safe_load(fp)
        
    scenarios = manifest_data.get("scenarios", [])
    
    unique_buildings = sorted(list(set(s["building"] for s in scenarios)))
    unique_weathers = sorted(list(set(s["weather"] for s in scenarios)))
    
    # Weather families: strip suffix _1, _2, etc.
    weather_families = sorted(list(set(w.split("_")[0] for w in unique_weathers)))
    
    # Check all building YAMLs exist
    all_shipped_buildings = sorted([f.stem for f in BUILDINGS_DIR.glob("*.yaml")])
    missing_buildings = [b for b in unique_buildings if not (BUILDINGS_DIR / f"{b}.yaml").exists()]
    unreferenced_buildings = [b for b in all_shipped_buildings if b not in unique_buildings]
    
    # Check all weather YAMLs exist
    all_shipped_weathers = sorted([f.stem for f in WEATHER_DIR.glob("*.yaml")])
    missing_weathers = [w for w in unique_weathers if not (WEATHER_DIR / f"{w}.yaml").exists()]
    unreferenced_weathers = [w for w in all_shipped_weathers if w not in unique_weathers]
    
    # Check scenario folders exist
    scenario_status = []
    missing_scenario_dirs = []
    for s in scenarios:
        b = s["building"]
        w = s["weather"]
        scen_dir = TRAIN_SCENARIOS_DIR / b / w
        exists = scen_dir.exists()
        has_gin = (scen_dir / "config.gin").exists()
        has_yaml = (scen_dir / "config.yaml").exists()
        has_floor = (scen_dir / "floor_plan.npy").exists()
        has_zone = (scen_dir / "zone_map.npy").exists()
        
        complete = exists and has_gin and has_yaml and has_floor and has_zone
        if not complete:
            missing_scenario_dirs.append(f"{b}/{w}")
            
        scenario_status.append({
            "building": b,
            "weather": w,
            "directory_exists": exists,
            "config_gin": has_gin,
            "config_yaml": has_yaml,
            "floor_plan_npy": has_floor,
            "zone_map_npy": has_zone,
            "fully_formed": complete
        })
        
    # Check if scenarios exist in training_scenarios that are NOT in manifest
    all_found_scenarios = []
    for b_dir in TRAIN_SCENARIOS_DIR.iterdir():
        if b_dir.is_dir():
            for w_dir in b_dir.iterdir():
                if w_dir.is_dir():
                    all_found_scenarios.append(f"{b_dir.name}/{w_dir.name}")
                    
    manifest_pairs = [f"{s['building']}/{s['weather']}" for s in scenarios]
    unmanifested_scenarios = [s for s in all_found_scenarios if s not in manifest_pairs]
    
    # Evaluation scenarios inspection
    eval_scenarios = []
    if EVAL_SCENARIOS_DIR.exists():
        for b_dir in EVAL_SCENARIOS_DIR.iterdir():
            if b_dir.is_dir():
                for w_dir in b_dir.iterdir():
                    if w_dir.is_dir():
                        eval_scenarios.append(f"{b_dir.name}/{w_dir.name}")

    audit_result = {
        "manifest_file": str(MANIFEST_PATH),
        "total_manifest_scenarios": len(scenarios),
        "unique_buildings_count": len(unique_buildings),
        "unique_buildings": unique_buildings,
        "shipped_building_configs": all_shipped_buildings,
        "unreferenced_building_configs": unreferenced_buildings,
        "missing_building_configs": missing_buildings,
        "unique_weather_strips_count": len(unique_weathers),
        "unique_weather_strips": unique_weathers,
        "unique_weather_families_count": len(weather_families),
        "unique_weather_families": weather_families,
        "total_shipped_weather_presets": len(all_shipped_weathers),
        "unreferenced_weather_presets": unreferenced_weathers,
        "missing_weather_presets": missing_weathers,
        "missing_scenario_directories": missing_scenario_dirs,
        "unmanifested_scenarios_found": unmanifested_scenarios,
        "evaluation_scenarios_found": eval_scenarios,
        "scenario_status": scenario_status
    }
    
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as fp:
        json.dump(audit_result, fp, indent=2)
        
    print(f"Manifest Audit Complete:")
    print(f"  Total Scenarios in Manifest: {len(scenarios)}")
    print(f"  Unique Buildings: {len(unique_buildings)} -> {unique_buildings}")
    print(f"  Unique Weather Strips: {len(unique_weathers)} across {len(weather_families)} families ({weather_families})")
    print(f"  Total Shipped Building YAMLs: {len(all_shipped_buildings)}")
    print(f"  Total Shipped Weather YAMLs: {len(all_shipped_weathers)} (Unreferenced in training_set.yaml: {len(unreferenced_weathers)})")
    print(f"  Missing Scenario Directories: {len(missing_scenario_dirs)}")
    print(f"  Unmanifested Training Scenarios: {len(unmanifested_scenarios)}")
    print(f"  Evaluation Scenarios Present: {eval_scenarios}")
    
    assert len(scenarios) == 30, f"Expected 30 scenarios, found {len(scenarios)}"
    assert len(unique_buildings) == 6, f"Expected 6 buildings, found {len(unique_buildings)}"
    assert len(unique_weathers) == 30, f"Expected 30 unique weather strips, found {len(unique_weathers)}"
    assert len(missing_scenario_dirs) == 0, f"Missing scenarios: {missing_scenario_dirs}"
    assert len(unmanifested_scenarios) == 0, f"Found unmanifested scenarios: {unmanifested_scenarios}"
    print("ALL MANIFEST ASSERTIONS PASSED!")

if __name__ == "__main__":
    audit_manifest()
