"""Tests for Evaluation Governance, Suite Manifests, and Comparison Validation."""

import sys
from pathlib import Path
import pytest
import yaml

PHASE_ROOT = Path(__file__).resolve().parents[1]
if str(PHASE_ROOT) not in sys.path:
    sys.path.insert(0, str(PHASE_ROOT))

from evaluation.comparison_validator import ComparisonValidator

SUITES_DIR = PHASE_ROOT / "suites"


def test_official_suite_manifest_integrity():
    """Official suite YAML must declare exactly 30 scenarios, role SELECT, and pinned commit."""
    manifest_path = SUITES_DIR / "official_suite.yaml"
    assert manifest_path.is_file(), f"Missing {manifest_path}"

    with open(manifest_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    assert data["suite_name"] == "official_reference_suite"
    assert data["role"] == "SELECT"
    assert data["expected_scenario_count"] == 30
    assert data["steps_per_episode"] == 8640
    assert len(data["scenarios"]) == 30
    assert data["commit_pinned"] == "95cea5b1c57b5291f44baf0283e0a081d53f5b16"


def test_additional_suites_integrity():
    """Dev and stress suites must be valid YAML with explicit roles."""
    dev_path = SUITES_DIR / "additional_suites" / "dev_smoke.yaml"
    stress_path = SUITES_DIR / "additional_suites" / "stress_extremes.yaml"

    assert dev_path.is_file()
    assert stress_path.is_file()

    with open(dev_path, "r", encoding="utf-8") as f:
        dev_data = yaml.safe_load(f)
    assert dev_data["role"] == "DEV"
    assert dev_data["expected_scenario_count"] == 1

    with open(stress_path, "r", encoding="utf-8") as f:
        stress_data = yaml.safe_load(f)
    assert stress_data["role"] == "STRESS"
    assert stress_data["expected_scenario_count"] == 2


def test_comparison_validator_valid_pair():
    """Valid comparison between candidate and baseline on official suite."""
    cand_eval = {
        "suite_name": "official_reference_suite",
        "suite_version": "1.0.0",
        "evaluator_version": "1.0.0",
        "expected_scenario_count": 30,
        "scenario_returns": {f"sc_{i}": -100.0 for i in range(30)},
        "all_episodes_valid": True,
        "total_suite_return": -3000.0,
    }
    base_eval = {
        "suite_name": "official_reference_suite",
        "suite_version": "1.0.0",
        "evaluator_version": "1.0.0",
        "expected_scenario_count": 30,
        "scenario_returns": {f"sc_{i}": -120.0 for i in range(30)},
        "all_episodes_valid": True,
        "total_suite_return": -3600.0,
    }

    res = ComparisonValidator.validate_comparison(cand_eval, base_eval)
    assert res["valid_comparison"]
    assert res["score_delta"] == pytest.approx(600.0)
    assert res["candidate_is_improvement"] is True
    assert len(res["scenario_deltas"]) == 30
