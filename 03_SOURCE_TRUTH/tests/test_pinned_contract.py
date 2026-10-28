"""Static contract and source-truth verification tests.
These 7 tests correspond to the 7 checks that were previously skipped when SB_REPO_ROOT
was not pointing to a local Git checkout of the pinned starter-kit commit (95cea5b1c57b5291f44baf0283e0a081d53f5b16).
"""

import os
from pathlib import Path
import yaml
import pytest
import numpy as np

# Resolve starter-kit root
SB_REPO_ROOT = Path(os.getenv("SB_REPO_ROOT", Path(__file__).resolve().parents[1] / "starter_kit_pinned"))


@pytest.fixture(scope="module")
def repo_root():
    assert SB_REPO_ROOT.is_dir(), f"Starter-kit root not found at {SB_REPO_ROOT}"
    return SB_REPO_ROOT


def test_st01_transfer_policy_interface(repo_root):
    """Check 1: TransferPolicy class methods, docstring, and action shape contract."""
    policy_path = repo_root / "smart_buildings" / "baselines" / "transfer_policy.py"
    assert policy_path.is_file(), f"Missing {policy_path}"
    content = policy_path.read_text(encoding="utf-8")

    assert "class TransferPolicy" in content
    assert "def __init__" in content
    assert "building_meta_data" in content
    assert "action_spec" in content
    assert "def get_action" in content
    assert "continuous_action" in content
    assert "discrete_action" in content
    assert "3K + 2 + 2V" in content
    assert "K + 1" in content


def test_st02_floor_plan_and_zone_map_metadata(repo_root):
    """Check 2: floor_plan and zone_map are explicitly exposed in create_building_meta_data."""
    eval_path = repo_root / "smart_buildings" / "evaluate.py"
    assert eval_path.is_file(), f"Missing {eval_path}"
    content = eval_path.read_text(encoding="utf-8")

    assert "def create_building_meta_data" in content
    assert 'floor_plan_path = output_dir / "floor_plan.npy"' in content
    assert 'zone_map_path = output_dir / "zone_map.npy"' in content
    assert '"floor_plan": floor_plan' in content
    assert '"zone_map": zone_map' in content


def test_st03_material_generator_parameter_ranges(repo_root):
    """Check 3: Material sampling properties in materials.py match log/lin distributions."""
    mat_path = repo_root / "smart_buildings" / "smart_control" / "utils" / "materials.py"
    assert mat_path.is_file(), f"Missing {mat_path}"
    content = mat_path.read_text(encoding="utf-8")

    # Verify key property ranges and sampling scales
    assert '"exterior_cv_conductivity": (0.15, 0.55, "log")' in content
    assert '"exterior_cv_density": (350.0, 2400.0, "log")' in content
    assert '"interior_mass_cv_density": (10.0, 40.0, "log")' in content
    assert '"interior_wall_cv_conductivity": (0.45, 0.60, "lin")' in content
    assert '"interior_wall_cv_density": (110.0, 700.0, "log")' in content
    assert '"exterior_cv_heat_capacity": (840.0, 1000.0, "lin")' in content


def test_st04_manifest_30_pairs_uniqueness(repo_root):
    """Check 4: training_set.yaml contains exactly 30 pairs across 6 buildings and 5 stations."""
    manifest_path = repo_root / "smart_buildings" / "training_set.yaml"
    assert manifest_path.is_file(), f"Missing {manifest_path}"
    with open(manifest_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    scenarios = data.get("scenarios", [])
    assert len(scenarios) == 30, f"Expected 30 scenarios, found {len(scenarios)}"

    buildings = {s["building"] for s in scenarios}
    assert len(buildings) == 6, f"Expected 6 buildings, found {len(buildings)}"
    expected_buildings = {
        "building_train_1", "building_train_2", "building_train_4",
        "building_train_5", "building_train_7", "building_train_8"
    }
    assert buildings == expected_buildings

    weathers = [s["weather"] for s in scenarios]
    assert len(weathers) == len(set(weathers)), "All 30 weather strips must be unique"

    stations = {w.split("_")[0] for w in weathers}
    assert stations == {"atlanta", "denver", "fairbanks", "phoenix", "singapore"}


def test_st05_default_comfort_schedule(repo_root):
    """Check 5: Configured schedule is 06:00 to 19:00 (morning_start_hour=6, evening_start_hour=19)."""
    cfg_path = repo_root / "smart_buildings" / "training_scenarios" / "building_train_1" / "fairbanks_1" / "config.gin"
    if not cfg_path.is_file():
        # Fallback to local workspace if scenarios generated locally
        cfg_path = Path(__file__).resolve().parents[1] / "smart_buildings" / "training_scenarios" / "building_train_1" / "fairbanks_1" / "config.gin"

    assert cfg_path.is_file(), f"Missing {cfg_path}"
    content = cfg_path.read_text(encoding="utf-8")
    assert "morning_start_hour = 6" in content
    assert "evening_start_hour = 19" in content


def test_st06_reward_source_occupancy_and_rates(repo_root):
    """Check 6: SetpointEnergyCarbonRegretFunction normalizes by total_occupancy and leaves rates uncapped."""
    reward_path = repo_root / "smart_buildings" / "smart_control" / "reward" / "setpoint_energy_carbon_regret.py"
    assert reward_path.is_file(), f"Missing {reward_path}"
    content = reward_path.read_text(encoding="utf-8")

    # Normalization uses dynamic total_occupancy, NOT a constant 125.0
    assert "actual_productivity, total_occupancy = self._sum_zone_productivities(" in content
    assert "if total_occupancy > 0.0:" in content
    assert "normalized_productivity_regret = 0.0" in content
    # Confirms comment that rates are not saturation limits
    assert "NOT clipped to _max_electricity_rate" in content
    assert "Uncapped for the same reason as electricity above" in content


def test_st07_score_leaderboard_constants_and_metric(repo_root):
    """Check 7: score_leaderboard.py enforces BASELINE_STEPS=8640 and equal scenario weighting."""
    scorer_path = repo_root / "score_leaderboard.py"
    assert scorer_path.is_file(), f"Missing {scorer_path}"
    content = scorer_path.read_text(encoding="utf-8")

    assert "BASELINE_STEPS = 8640" in content
    assert 'BASELINES = ("bang_bang", "fixed_setpoint", "pid", "pid_water")' in content
    assert "abs(r) / BASELINE_STEPS" in content
    assert "score = sum(s for _, _, s, _ in rows) / len(rows)" in content
