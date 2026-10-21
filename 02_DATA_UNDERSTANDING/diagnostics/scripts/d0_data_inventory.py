"""D0 Data Inventory Script for Smart Buildings Challenge.
Recursively inspects the competition workspace, classifies all files,
and produces evidence/DATA_INVENTORY.csv.
"""

import os
import csv
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
OUTPUT_CSV = WORKSPACE_ROOT / "02_DATA_UNDERSTANDING" / "evidence" / "DATA_INVENTORY.csv"

def categorize_file(rel_path: str):
    p = rel_path.replace("\\", "/")
    parts = p.split("/")
    filename = parts[-1]
    ext = os.path.splitext(filename)[1].lower()
    
    # Defaults
    category = "Other"
    purpose = "General project file"
    source = "Starter Kit"
    shipped_or_gen = "Shipped"
    temporal = "Static"
    necessity = "Optional"
    deps = "None"
    
    if p.startswith("02_DATA_UNDERSTANDING"):
        category = "Investigation/Artifact"
        purpose = "Data understanding phase artifact or diagnostic"
        source = "Lead Investigator"
        shipped_or_gen = "Generated"
        necessity = "Diagnostic"
        return category, purpose, source, shipped_or_gen, temporal, necessity, deps

    if p.startswith(".venv") or p.startswith("__pycache__"):
        return None  # Exclude venv and pycache from official inventory

    if filename == "neurips-2026-smart-buildings.zip":
        category = "Archive"
        purpose = "Official competition distribution archive"
        source = "Kaggle / NeurIPS 2026"
        necessity = "Required"
    elif filename.startswith("Smart_Buildings_Problem"):
        category = "Documentation/Research"
        purpose = "Foundational problem research and problem establishment (R1-R5)"
        source = "Domain Research Team"
        necessity = "Required"
    elif "kaggle_evaluation" in parts:
        category = "Evaluation/Harness"
        purpose = "Kaggle evaluation gateway, protocol buffers, and remote drivers"
        necessity = "Required"
        deps = "grpc, protobuf"
    elif "smart_buildings/baselines" in p:
        category = "Code/Baseline"
        purpose = "Reference heuristic or PID control policy"
        necessity = "Diagnostic"
        deps = "smart_control"
    elif "smart_buildings/buildings" in p:
        category = "Configuration/Building"
        purpose = "Building specification (dimensions, AHUs, materials, schedules)"
        necessity = "Required"
        deps = "scenario_generator"
    elif "smart_buildings/weather/csv" in p:
        category = "Data/Weather_CSV"
        purpose = "Annual hourly meteorological observations (temperature, dew point, wind, humidity)"
        temporal = "Time-dependent"
        necessity = "Required"
    elif "smart_buildings/weather" in p and ext in [".yaml", ".yml"]:
        category = "Configuration/Weather"
        purpose = "Weather strip preset linking to annual CSV and 30-day start window"
        necessity = "Required"
        deps = "weather CSV"
    elif "training_scenarios" in p or "evaluation_scenarios" in p:
        if ext == ".gin":
            category = "Configuration/Scenario_Gin"
            purpose = "Gin config binding simulator parameters, building models, and reward functions"
            necessity = "Required"
            deps = "gin-config"
        elif ext == ".yaml":
            category = "Configuration/Scenario_YAML"
            purpose = "Scenario parameter specification"
            necessity = "Required"
        elif ext == ".npy":
            category = "Data/Floorplan_Zone_NPY"
            purpose = "2D array for floor plan wall raster or zone partitioning map"
            necessity = "Required"
            deps = "numpy"
        else:
            category = "Scenario/Asset"
            purpose = "Scenario artifact"
    elif "proto" in p:
        category = "Specification/Protobuf"
        purpose = "Protocol buffer definition or compiled Python bindings"
        deps = "google.protobuf"
    elif "smart_buildings/smart_control/reward" in p:
        category = "Code/Reward"
        purpose = "Comfort, energy, and carbon cost/reward calculation"
        necessity = "Required"
    elif "smart_buildings/smart_control/simulator" in p:
        category = "Code/Simulator"
        purpose = "Physical simulation: thermal convection, air handlers, boilers, pumps"
        necessity = "Required"
    elif "smart_buildings/smart_control/environment" in p:
        category = "Code/Environment"
        purpose = "Gymnasium environment wrapper, hybrid action space, step loop"
        necessity = "Required"
    elif "smart_buildings/smart_control/models" in p:
        category = "Code/Model_Base"
        purpose = "Abstract base classes for buildings, rewards, occupancy, world models"
        necessity = "Required"
    elif "smart_buildings/smart_control/utils" in p:
        category = "Code/Utility"
        purpose = "Scenario generation, normalization, conversion constants"
        necessity = "Required"
    elif p.startswith("smart_buildings") and ext == ".py":
        category = "Code/Runner"
        purpose = "Top-level runner script (evaluation, environment, generator)"
        necessity = "Required"
    elif filename == "training_set.yaml":
        category = "Configuration/Manifest"
        purpose = "Official pairing manifest defining the 30 development scenarios"
        necessity = "Required"

    return category, purpose, source, shipped_or_gen, temporal, necessity, deps

def generate_inventory():
    rows = []
    for root, dirs, files in os.walk(WORKSPACE_ROOT):
        # Skip venv, git, and pycache
        dirs[:] = [d for d in dirs if d not in [".venv", ".git", "__pycache__", ".pytest_cache", ".system_generated"]]
        for f in files:
            full_path = Path(root) / f
            rel_path = full_path.relative_to(WORKSPACE_ROOT)
            rel_str = str(rel_path)
            
            # Skip investigation artifacts inside inventory to focus on competition target
            if rel_str.startswith("02_DATA_UNDERSTANDING"):
                continue

            cat_info = categorize_file(rel_str)
            if cat_info is None:
                continue
            
            category, purpose, source, shipped_or_gen, temporal, necessity, deps = cat_info
            size = full_path.stat().st_size
            ext = full_path.suffix.lower()
            
            rows.append({
                "file_path": rel_str.replace("\\", "/"),
                "file_type": ext if ext else "no_ext",
                "file_size_bytes": size,
                "data_category": category,
                "purpose": purpose,
                "source_or_generator": source,
                "shipped_or_generated": shipped_or_gen,
                "temporal_characteristic": temporal,
                "operational_necessity": necessity,
                "relevant_dependencies": deps,
                "availability_status": "Verified Present"
            })
            
    rows.sort(key=lambda r: r["file_path"])
    
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
        
    print(f"Inventoried {len(rows)} files into {OUTPUT_CSV}")
    
    # Summary by category
    cats = {}
    total_size = 0
    for r in rows:
        c = r["data_category"]
        cats[c] = cats.get(c, 0) + 1
        total_size += r["file_size_bytes"]
        
    print(f"Total size: {total_size / (1024*1024):.2f} MB")
    print("Files by category:")
    for c, count in sorted(cats.items(), key=lambda x: -x[1]):
        print(f"  {c}: {count}")

if __name__ == "__main__":
    generate_inventory()
