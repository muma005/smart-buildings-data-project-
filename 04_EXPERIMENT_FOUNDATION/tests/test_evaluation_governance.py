"""Tests for Evaluation Governance, Suite Manifests, and Environment Partitioning (E1).
Covers Defect Modes 01-09:
1. Duplicate scenario inside one suite.
2. Unknown scenario identifier.
3. Missing required provenance.
4. Undeclared suite-membership change.
5. Prohibited exact scenario overlap.
6. Prohibited building overlap.
7. Prohibited weather overlap.
8. Incorrect suite role or use.
9. Public benchmark falsely declared sealed or independent.
Plus positive controls for legitimate suites and allowed overlaps.
"""

import sys
from pathlib import Path
import pytest
import yaml

PHASE_ROOT = Path(__file__).resolve().parents[1]
if str(PHASE_ROOT) not in sys.path:
    sys.path.insert(0, str(PHASE_ROOT))

from evaluation.comparison_validator import SuiteValidator, ComparisonValidator

SUITES_DIR = PHASE_ROOT / "suites"
OFFICIAL_SUITE_PATH = SUITES_DIR / "official_suite.yaml"


# ==============================================================================
# Positive Controls: Legitimate Suites and Allowed Overlaps
# ==============================================================================

def test_official_suite_manifest_integrity():
    """Official suite YAML must declare exactly 30 scenarios, role SELECT, and pinned commit."""
    assert OFFICIAL_SUITE_PATH.is_file(), f"Missing {OFFICIAL_SUITE_PATH}"

    with open(OFFICIAL_SUITE_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    assert data["suite_name"] == "official_reference_suite"
    assert data["role"] == "SELECT"
    assert data["expected_scenario_count"] == 30
    assert data["steps_per_episode"] == 8640
    assert len(data["scenarios"]) == 30
    assert data["commit_pinned"] == "95cea5b1c57b5291f44baf0283e0a081d53f5b16"


def test_suite_validator_official_suite_passes():
    """SuiteValidator must accept the official reference suite without errors."""
    res = SuiteValidator.validate_suite_manifest(OFFICIAL_SUITE_PATH)
    assert res["valid"], f"Official suite failed validation: {res['rejection_reasons']}"
    assert len(res["scenario_ids"]) == 30
    assert len(res["buildings"]) == 6
    assert len(res["weathers"]) == 30


def test_additional_suites_integrity():
    """Dev and stress suites must be valid YAML with explicit roles and pass validation."""
    dev_path = SUITES_DIR / "additional_suites" / "dev_smoke.yaml"
    stress_path = SUITES_DIR / "additional_suites" / "stress_extremes.yaml"

    assert dev_path.is_file()
    assert stress_path.is_file()

    dev_res = SuiteValidator.validate_suite_manifest(dev_path)
    assert dev_res["valid"], f"Dev smoke failed: {dev_res['rejection_reasons']}"
    assert dev_res["role"] == "DEV"

    stress_res = SuiteValidator.validate_suite_manifest(stress_path)
    assert stress_res["valid"], f"Stress extremes failed: {stress_res['rejection_reasons']}"
    assert stress_res["role"] == "STRESS"


def test_allowed_overlap_between_dev_and_select():
    """DEV suites are explicitly ALLOWED to overlap with SELECT for rapid local testing."""
    dev_path = SUITES_DIR / "additional_suites" / "dev_smoke.yaml"
    res = SuiteValidator.check_suite_overlap(OFFICIAL_SUITE_PATH, dev_path)

    assert res["allowed"] is True
    assert res["status"] == "ALLOWED"
    assert len(res["exact_scenario_overlap"]) == 1
    assert "building_train_1/atlanta_2" in res["exact_scenario_overlap"]


# ==============================================================================
# Red-Team Defect Tests: Defect Modes 01 - 09
# ==============================================================================

# --- Defect 1: Duplicate scenario inside one suite ---
def test_defect_01_duplicate_scenario_inside_suite():
    bad_manifest = {
        "suite_name": "duplicate_scenario_suite",
        "version": "1.0.0",
        "role": "DEV",
        "commit_pinned": "95cea5b1c57b5291f44baf0283e0a081d53f5b16",
        "expected_scenario_count": 2,
        "steps_per_episode": 8640,
        "scenarios": [
            {"id": "building_train_1/atlanta_2", "building": "building_train_1", "weather": "atlanta_2"},
            {"id": "building_train_1/atlanta_2", "building": "building_train_1", "weather": "atlanta_2"},
        ],
    }
    res = SuiteValidator.validate_suite_manifest(bad_manifest)
    assert not res["valid"]
    assert any("Duplicate scenario inside suite" in r for r in res["rejection_reasons"])


# --- Defect 2: Unknown scenario identifier ---
def test_defect_02_unknown_scenario_identifier():
    bad_manifest = {
        "suite_name": "unknown_scenario_suite",
        "version": "1.0.0",
        "role": "DEV",
        "commit_pinned": "95cea5b1c57b5291f44baf0283e0a081d53f5b16",
        "expected_scenario_count": 1,
        "steps_per_episode": 8640,
        "scenarios": [
            {"id": "nonexistent_building/fabricated_weather", "building": "nonexistent", "weather": "fabricated"},
        ],
    }
    known_catalog = {"building_train_1/atlanta_2", "building_train_1/denver_7"}
    res = SuiteValidator.validate_suite_manifest(bad_manifest, known_scenarios=known_catalog)
    assert not res["valid"]
    assert any("Unknown scenario identifier" in r for r in res["rejection_reasons"])


# --- Defect 3: Missing required provenance ---
def test_defect_03_missing_required_provenance():
    bad_manifest = {
        "suite_name": "untracked_suite",
        "version": "1.0.0",
        "role": "STRESS",
        # Missing commit_pinned and generator_provenance!
        "expected_scenario_count": 1,
        "steps_per_episode": 8640,
        "scenarios": [
            {"id": "building_train_1/fairbanks_1", "building": "building_train_1", "weather": "fairbanks_1"},
        ],
    }
    res = SuiteValidator.validate_suite_manifest(bad_manifest)
    assert not res["valid"]
    assert any("Missing required provenance" in r for r in res["rejection_reasons"])


# --- Defect 4: Undeclared suite-membership change ---
def test_defect_04_undeclared_suite_membership_change():
    v1_manifest = {
        "suite_name": "test_suite",
        "version": "1.0.0",
        "role": "DEV",
        "scenarios": [
            {"id": "building_train_1/atlanta_2"},
        ],
    }
    # Silently swapped scenario without incrementing version
    v1_mutated = {
        "suite_name": "test_suite",
        "version": "1.0.0",
        "role": "DEV",
        "scenarios": [
            {"id": "building_train_1/denver_7"},
        ],
    }
    res = SuiteValidator.validate_suite_version_consistency(v1_manifest, v1_mutated)
    assert not res["valid"]
    assert "Undeclared suite-membership change" in res["error"]


# --- Defect 5: Prohibited exact scenario overlap between SELECT and GENERALIZATION ---
def test_defect_05_prohibited_exact_scenario_overlap():
    gen_manifest = {
        "suite_name": "leaked_generalization_suite",
        "version": "1.0.0",
        "role": "GENERALIZATION",
        "commit_pinned": "95cea5b1c57b5291f44baf0283e0a081d53f5b16",
        "transfer_provenance": "synthetic_transfer_v1",
        "expected_scenario_count": 1,
        "steps_per_episode": 8640,
        "scenarios": [
            # Direct copy of a public SELECT scenario!
            {"id": "building_train_1/atlanta_2", "building": "building_train_1", "weather": "atlanta_2"},
        ],
    }
    res = SuiteValidator.check_suite_overlap(OFFICIAL_SUITE_PATH, gen_manifest)
    assert res["allowed"] is False
    assert res["status"] == "DISALLOWED"
    assert any("Prohibited exact scenario overlap" in r for r in res["rejection_reasons"])


# --- Defect 6: Prohibited building overlap in building-generalization evaluation ---
def test_defect_06_prohibited_building_overlap():
    gen_manifest = {
        "suite_name": "building_transfer_suite",
        "version": "1.0.0",
        "role": "GENERALIZATION",
        "holdout_dimension": "BUILDING",
        "commit_pinned": "95cea5b1c57b5291f44baf0283e0a081d53f5b16",
        "transfer_provenance": "synthetic_weather_v1",
        "expected_scenario_count": 1,
        "steps_per_episode": 8640,
        "scenarios": [
            # Claims unseen building generalization, but uses known building_train_1!
            {"id": "building_train_1/unseen_weather_99", "building": "building_train_1", "weather": "unseen_weather_99"},
        ],
    }
    res = SuiteValidator.check_suite_overlap(OFFICIAL_SUITE_PATH, gen_manifest)
    assert res["allowed"] is False
    assert res["status"] == "DISALLOWED"
    assert any("Prohibited building overlap" in r for r in res["rejection_reasons"])


# --- Defect 7: Prohibited weather overlap in weather-generalization evaluation ---
def test_defect_07_prohibited_weather_overlap():
    gen_manifest = {
        "suite_name": "weather_transfer_suite",
        "version": "1.0.0",
        "role": "GENERALIZATION",
        "holdout_dimension": "WEATHER",
        "commit_pinned": "95cea5b1c57b5291f44baf0283e0a081d53f5b16",
        "transfer_provenance": "synthetic_building_v1",
        "expected_scenario_count": 1,
        "steps_per_episode": 8640,
        "scenarios": [
            # Claims unseen climate generalization, but reuses known atlanta_2 weather!
            {"id": "novel_building_99/atlanta_2", "building": "novel_building_99", "weather": "atlanta_2"},
        ],
    }
    res = SuiteValidator.check_suite_overlap(OFFICIAL_SUITE_PATH, gen_manifest)
    assert res["allowed"] is False
    assert res["status"] == "DISALLOWED"
    assert any("Prohibited weather overlap" in r for r in res["rejection_reasons"])


# --- Defect 8: Incorrect suite role or use ---
def test_defect_08_incorrect_suite_role_or_use():
    dev_path = SUITES_DIR / "additional_suites" / "dev_smoke.yaml"
    res = SuiteValidator.check_role_eligibility(dev_path, intended_use="CANDIDATE_SELECTION")
    assert not res["eligible"]
    assert "Incorrect suite role for candidate selection" in res["error"]
    assert "Only 'SELECT' suites" in res["error"]


# --- Defect 9: Public benchmark falsely declared sealed or independent ---
def test_defect_09_public_benchmark_falsely_declared_sealed():
    fake_sealed_manifest = {
        "suite_name": "supposedly_hidden_test_set",
        "version": "1.0.0",
        "role": "SEALED RELEASE",  # Prohibited declaration on local public scenarios!
        "commit_pinned": "95cea5b1c57b5291f44baf0283e0a081d53f5b16",
        "expected_scenario_count": 1,
        "steps_per_episode": 8640,
        "scenarios": [
            {"id": "building_train_1/atlanta_2", "building": "building_train_1", "weather": "atlanta_2"},
        ],
    }
    res = SuiteValidator.validate_suite_manifest(fake_sealed_manifest)
    assert not res["valid"]
    assert any("Public benchmark falsely declared sealed" in r for r in res["rejection_reasons"])
