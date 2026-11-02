"""Tests for Actuator Semantic Verification Remediation.
Validates:
1. Multi-building representative zone coverage:
   - building_train_1 (compact facility): VAV_1, VAV_2, VAV_3, VAV_15
   - building_train_2 (85-zone complex, 9 AHUs): VAV_1, VAV_10, VAV_25, VAV_50, VAV_85
2. Multi-channel physical response verification:
   - reheat_valve_percentage_command (thermal rise: ΔT > 0, dominant positive margin)
   - supply_air_damper_percentage_command (thermal drop / cooling: ΔT < 0, dominant negative margin)
3. Clean negative controls (0.0% false-positive rate across correctly mapped channels).
4. Positive failure detection:
   - Permuted zone mappings (target zone command actuates culprit zone)
   - Cross-channel type swap (reheat valve command wired to supply air damper)
5. Strict non-remapping policy (auto_remapping_applied is False).
6. Honest limitation disclosure and boundary enforcement.
"""

from __future__ import annotations
import json
from pathlib import Path
import sys
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FOUNDATION_ROOT = PROJECT_ROOT / "04_EXPERIMENT_FOUNDATION"
for p in [str(PROJECT_ROOT), str(FOUNDATION_ROOT)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from evaluation.semantic_probe import SemanticActuatorProbe


# ==============================================================================
# 1. Multi-Building Clean Negative Controls (Zero False Positives)
# ==============================================================================

def test_semantic_clean_controls_bldg1_multi_zone():
    """Confirms 0.0% false positives across multiple zones in building_train_1."""
    # Representative zones across floors/branches in building_train_1
    zones_to_test = ["VAV_1", "VAV_2", "VAV_3", "VAV_15"]
    base_temps = {f"VAV_{i}": 293.15 for i in range(1, 40)}

    for zone in zones_to_test:
        initial = dict(base_temps)
        final = dict(base_temps)
        # Healthy heating pulse: target rises by +0.55 K, unpulsed zones rise by <= +0.05 K
        final[zone] = initial[zone] + 0.55
        for z in final:
            if z != zone:
                final[z] += 0.04

        report = SemanticActuatorProbe.evaluate_response(
            target_zone=zone,
            initial_temperatures=initial,
            final_temperatures=final,
            min_delta_t_k=0.20,
            min_margin_k=0.05,
            channel_name="reheat_valve_percentage_command",
        )
        assert report["passed"] is True
        assert report["target_zone"] == zone
        assert report["delta_t_target_k"] == pytest.approx(0.55)
        assert report["margin_k"] == pytest.approx(0.51)
        assert len(report["rejection_reasons"]) == 0

        diag = SemanticActuatorProbe.diagnose_channel_misalignment(report)
        assert diag["misalignment_detected"] is False
        assert diag["status"] == "NOMINAL"
        assert diag["target_zone"] == zone
        assert diag["auto_remapping_applied"] is False


def test_semantic_clean_controls_bldg2_multi_ahu_zones():
    """Confirms 0.0% false positives across representative zones spanning distinct AHUs in 85-zone building_train_2."""
    # Representative zones from different AHUs in 85-zone building
    zones_to_test = ["VAV_1", "VAV_10", "VAV_25", "VAV_50", "VAV_85"]
    base_temps = {f"VAV_{i}": 293.15 for i in range(1, 86)}

    for zone in zones_to_test:
        initial = dict(base_temps)
        final = dict(base_temps)
        # Healthy heating pulse in large commercial building
        final[zone] = initial[zone] + 1.15
        for z in final:
            if z != zone:
                final[z] += 0.02

        report = SemanticActuatorProbe.evaluate_response(
            target_zone=zone,
            initial_temperatures=initial,
            final_temperatures=final,
            min_delta_t_k=0.20,
            min_margin_k=0.05,
            channel_name="reheat_valve_percentage_command",
        )
        assert report["passed"] is True
        assert report["target_zone"] == zone
        assert report["delta_t_target_k"] == pytest.approx(1.15)
        assert report["margin_k"] == pytest.approx(1.13)
        assert len(report["rejection_reasons"]) == 0

        diag = SemanticActuatorProbe.diagnose_channel_misalignment(report)
        assert diag["misalignment_detected"] is False
        assert diag["status"] == "NOMINAL"
        assert diag["auto_remapping_applied"] is False


# ==============================================================================
# 2. Multi-Channel Support: Supply Air Damper (Cooling Effect)
# ==============================================================================

def test_semantic_damper_cooling_clean_control():
    """Verifies clean control for supply_air_damper_percentage_command (thermal drop)."""
    initial_temps = {"VAV_1": 294.00, "VAV_2": 294.00, "VAV_3": 294.00}
    # VAV_1 damper opens with cool supply air: temperature drops by -0.30 K
    # Unventilated zones warm slightly (+0.10 K) due to internal gains
    final_temps = {
        "VAV_1": 293.70,  # ΔT = -0.30 K
        "VAV_2": 294.10,  # ΔT = +0.10 K
        "VAV_3": 294.08,  # ΔT = +0.08 K
    }

    report = SemanticActuatorProbe.evaluate_response(
        target_zone="VAV_1",
        initial_temperatures=initial_temps,
        final_temperatures=final_temps,
        min_delta_t_k=0.20,
        min_margin_k=0.05,
        channel_name="supply_air_damper_percentage_command",
    )

    assert report["passed"] is True
    assert report["expected_direction"] == "negative"
    assert report["delta_t_target_k"] == pytest.approx(-0.30)
    assert report["margin_k"] >= 0.05
    assert len(report["rejection_reasons"]) == 0

    diag = SemanticActuatorProbe.diagnose_channel_misalignment(report)
    assert diag["misalignment_detected"] is False
    assert diag["status"] == "NOMINAL"
    assert diag["auto_remapping_applied"] is False


def test_semantic_damper_swapped_detection():
    """Detects swapped supply air damper channels between VAV_1 and VAV_2."""
    initial_temps = {"VAV_1": 294.00, "VAV_2": 294.00, "VAV_3": 294.00}
    # Command sent to VAV_1 damper, but VAV_2 damper opened instead!
    final_temps = {
        "VAV_1": 294.08,  # ΔT = +0.08 K (target fails to cool)
        "VAV_2": 293.65,  # ΔT = -0.35 K (culprit zone cools instead!)
        "VAV_3": 294.05,  # ΔT = +0.05 K
    }

    report = SemanticActuatorProbe.evaluate_response(
        target_zone="VAV_1",
        initial_temperatures=initial_temps,
        final_temperatures=final_temps,
        min_delta_t_k=0.20,
        min_margin_k=0.05,
        channel_name="supply_air_damper_percentage_command",
    )

    assert report["passed"] is False
    assert any("swapped actuator channel" in r for r in report["rejection_reasons"])

    diag = SemanticActuatorProbe.diagnose_channel_misalignment(report)
    assert diag["misalignment_detected"] is True
    assert diag["status"] == "DEFECT_CONFIRMED"
    assert diag["culprit_zone"] == "VAV_2"
    assert diag["suspected_permutation"]["actuated_culprit_zone"] == "VAV_2"
    assert diag["auto_remapping_applied"] is False
    assert diag["policy_action"] == "DO_NOT_REMAP_REJECT_RUN"


# ==============================================================================
# 3. Cross-Channel Type Swap Detection (Reheat vs Damper Wiring Error)
# ==============================================================================

def test_semantic_cross_channel_type_swap_heating_to_cooling():
    """Detects when reheat channel is erroneously wired to supply air damper."""
    initial_temps = {"VAV_1": 294.00, "VAV_2": 294.00, "VAV_3": 294.00}
    # Commanded reheat valve on VAV_1, but observed significant cooling (-0.45 K)!
    final_temps = {"VAV_1": 293.55, "VAV_2": 294.02, "VAV_3": 294.01}

    report = SemanticActuatorProbe.evaluate_response(
        target_zone="VAV_1",
        initial_temperatures=initial_temps,
        final_temperatures=final_temps,
        min_delta_t_k=0.20,
        min_margin_k=0.05,
        channel_name="reheat_valve_percentage_command",
        expected_direction="positive",
    )

    assert report["passed"] is False
    diag = SemanticActuatorProbe.diagnose_channel_misalignment(report)

    assert diag["misalignment_detected"] is True
    assert diag["status"] == "DEFECT_CONFIRMED"
    timeline = diag["timeline_analysis"]
    assert timeline["confirmed_root_cause"]["type"] == "CROSS_CHANNEL_TYPE_PERMUTATION"
    assert diag["suspected_permutation"]["observed_effect"] == "COOLING"
    assert diag["suspected_permutation"]["suspected_actual_channel"] == "supply_air_damper_percentage_command"
    assert diag["auto_remapping_applied"] is False


# ==============================================================================
# 4. Comprehensive Multi-Zone Matrix Evaluation
# ==============================================================================

def test_evaluate_multi_zone_matrix_execution(tmp_path: Path):
    """Executes a multi-building, multi-zone, multi-channel verification matrix.

    Validates:
    - 0.0% false-positive rate on clean controls.
    - 100.0% detection rate on defects.
    - Strict prohibition of automatic remapping.
    - Generation of machine-readable matrix artifact.
    """
    cases = [
        # Case 1: Bldg 1 VAV_1 Clean Reheat
        {
            "building": "building_train_1",
            "target_zone": "VAV_1",
            "channel_name": "reheat_valve_percentage_command",
            "case_type": "CLEAN_CONTROL",
            "initial_temperatures": {"VAV_1": 293.0, "VAV_2": 293.0, "VAV_3": 293.0},
            "final_temperatures": {"VAV_1": 293.55, "VAV_2": 293.05, "VAV_3": 293.02},
            "min_delta_t_k": 0.20,
            "min_margin_k": 0.05,
        },
        # Case 2: Bldg 1 VAV_2 Clean Reheat
        {
            "building": "building_train_1",
            "target_zone": "VAV_2",
            "channel_name": "reheat_valve_percentage_command",
            "case_type": "CLEAN_CONTROL",
            "initial_temperatures": {"VAV_1": 293.0, "VAV_2": 293.0, "VAV_3": 293.0},
            "final_temperatures": {"VAV_1": 293.04, "VAV_2": 293.60, "VAV_3": 293.03},
            "min_delta_t_k": 0.20,
            "min_margin_k": 0.05,
        },
        # Case 3: Bldg 1 VAV_1 Clean Damper Cooling
        {
            "building": "building_train_1",
            "target_zone": "VAV_1",
            "channel_name": "supply_air_damper_percentage_command",
            "case_type": "CLEAN_CONTROL",
            "initial_temperatures": {"VAV_1": 294.0, "VAV_2": 294.0, "VAV_3": 294.0},
            "final_temperatures": {"VAV_1": 293.65, "VAV_2": 294.10, "VAV_3": 294.08},
            "min_delta_t_k": 0.20,
            "min_margin_k": 0.05,
        },
        # Case 4: Bldg 2 VAV_10 Clean Reheat (85 zones)
        {
            "building": "building_train_2",
            "target_zone": "VAV_10",
            "channel_name": "reheat_valve_percentage_command",
            "case_type": "CLEAN_CONTROL",
            "initial_temperatures": {f"VAV_{i}": 293.0 for i in range(1, 86)},
            "final_temperatures": {f"VAV_{i}": (294.15 if i == 10 else 293.02) for i in range(1, 86)},
            "min_delta_t_k": 0.20,
            "min_margin_k": 0.05,
        },
        # Case 5: Bldg 1 Injected Reheat Swap (VAV_1 -> VAV_2)
        {
            "building": "building_train_1",
            "target_zone": "VAV_1",
            "channel_name": "reheat_valve_percentage_command",
            "case_type": "INJECTED_DEFECT",
            "initial_temperatures": {"VAV_1": 293.0, "VAV_2": 293.0, "VAV_3": 293.0},
            "final_temperatures": {"VAV_1": 293.05, "VAV_2": 293.90, "VAV_3": 293.02},
            "min_delta_t_k": 0.20,
            "min_margin_k": 0.05,
        },
        # Case 6: Bldg 2 Injected Reheat Swap (VAV_1 -> VAV_85)
        {
            "building": "building_train_2",
            "target_zone": "VAV_1",
            "channel_name": "reheat_valve_percentage_command",
            "case_type": "INJECTED_DEFECT",
            "initial_temperatures": {f"VAV_{i}": 293.0 for i in range(1, 86)},
            "final_temperatures": {f"VAV_{i}": (294.20 if i == 85 else 293.03) for i in range(1, 86)},
            "min_delta_t_k": 0.20,
            "min_margin_k": 0.05,
        },
        # Case 7: Bldg 1 Injected Cross-Channel Type Swap (Reheat commanded, cooling observed)
        {
            "building": "building_train_1",
            "target_zone": "VAV_1",
            "channel_name": "reheat_valve_percentage_command",
            "case_type": "INJECTED_DEFECT",
            "initial_temperatures": {"VAV_1": 294.0, "VAV_2": 294.0, "VAV_3": 294.0},
            "final_temperatures": {"VAV_1": 293.60, "VAV_2": 294.02, "VAV_3": 294.01},
            "min_delta_t_k": 0.20,
            "min_margin_k": 0.05,
        },
    ]

    out_json = tmp_path / "multi_zone_matrix_report.json"
    matrix = SemanticActuatorProbe.evaluate_multi_zone_matrix(cases, output_path=out_json)

    assert out_json.is_file()
    assert matrix["total_cases_evaluated"] == 7
    assert matrix["clean_controls_count"] == 4
    assert matrix["clean_controls_passed"] == 4
    assert matrix["false_positive_rate"] == 0.0
    assert matrix["injected_defects_count"] == 3
    assert matrix["injected_defects_detected"] == 3
    assert matrix["detection_rate"] == 1.0
    assert matrix["auto_remapping_prohibition_verified"] is True
    assert matrix["all_passed_acceptance"] is True

    # Verify limitations are explicitly recorded
    assert len(matrix["limitations_and_boundaries"]) >= 4
    lim_categories = [lim["category"] for lim in matrix["limitations_and_boundaries"]]
    assert "CHANNEL_TYPE_VERIFIABILITY" in lim_categories
    assert "CENTRAL_PLANT_ACTUATORS" in lim_categories
    assert "AUTOMATIC_REMAPPING_PROHIBITION" in lim_categories
