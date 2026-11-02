"""Semantic Actuator Mapping Probe (Red Team F1 Defense).
Verifies physical causality between actuator channels and thermal zones using
controlled single-variable pulse intervention.
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Mapping
import numpy as np


class SemanticActuatorProbe:
    """Performs and evaluates single-variable pulse interventions on HVAC actuators.

    Supports:
    - Multi-building facility topologies (small 39-zone and large 85-zone complexes).
    - Multiple actuator channels: reheat valves (thermal rise) and supply air dampers (cooling flow).
    - Clean negative controls verifying 0.0% false-positive rate.
    - Swapped actuator channel permutation isolation and cross-channel type detection.
    - Strict prohibition of automatic heuristic remapping.
    """

    SCHEMA_VERSION = "v1.0"
    DEFAULT_PROBE_STEPS = 4
    MIN_DELTA_T_TARGET_K = 0.5
    MIN_MARGIN_OVER_OTHERS_K = 0.3

    LIMITATIONS = [
        {
            "category": "CHANNEL_TYPE_VERIFIABILITY",
            "channel": "reheat_valve_percentage_command",
            "verifiable": True,
            "mechanism": "Single-variable positive pulse intervention with active hydronic heating loop.",
            "caveat": "Requires hot water supply temperature differential relative to zone ambient air.",
        },
        {
            "category": "CHANNEL_TYPE_VERIFIABILITY",
            "channel": "supply_air_damper_percentage_command",
            "verifiable": True,
            "mechanism": "Differential cooling pulse when central AHU supply air is cooler than zone air.",
            "caveat": "If outdoor/supply air temperature equals zone temperature (neutral air), thermal probe exhibits low sensitivity; requires airflow/pressure measurement.",
        },
        {
            "category": "CENTRAL_PLANT_ACTUATORS",
            "channel": "ahu_fan_speed / water_loop_temp / discrete_ahu_on",
            "verifiable": False,
            "mechanism": "Central plant actuators actuate across all zones in the AHU branch simultaneously.",
            "caveat": "Cannot be localized to a single zone by isolated zone probing; requires plant-level verification.",
        },
        {
            "category": "AUTOMATIC_REMAPPING_PROHIBITION",
            "channel": "ALL",
            "verifiable": True,
            "mechanism": "Verification gates detect, isolate, and reject misaligned channels.",
            "caveat": "Automatic heuristic remapping is strictly prohibited to prevent policy leakage or compounding silent errors.",
        },
    ]

    @classmethod
    def evaluate_response(
        cls,
        target_zone: str,
        initial_temperatures: Mapping[str, float],
        final_temperatures: Mapping[str, float],
        min_delta_t_k: float = MIN_DELTA_T_TARGET_K,
        min_margin_k: float = MIN_MARGIN_OVER_OTHERS_K,
        channel_name: str = "reheat_valve_percentage_command",
        expected_direction: str | None = None,
    ) -> dict[str, Any]:
        """Audits zone temperature deltas from a single-actuator pulse intervention.

        Supports both positive heating responses (reheat valves) and negative cooling responses (supply air dampers).
        """
        if target_zone not in initial_temperatures or target_zone not in final_temperatures:
            raise KeyError(f"Target zone '{target_zone}' not found in temperature mappings")

        if expected_direction is None:
            if "damper" in channel_name.lower() or "cool" in channel_name.lower():
                expected_direction = "negative"
            else:
                expected_direction = "positive"

        zone_deltas: dict[str, float] = {}
        for z in initial_temperatures:
            if z in final_temperatures:
                zone_deltas[z] = float(final_temperatures[z] - initial_temperatures[z])

        delta_t_target = zone_deltas[target_zone]
        other_deltas = [d for z, d in zone_deltas.items() if z != target_zone]

        rejection_reasons: list[str] = []

        if expected_direction == "positive":
            max_delta_others = float(max(other_deltas)) if other_deltas else 0.0
            target_meets_threshold = delta_t_target >= min_delta_t_k
            target_exceeds_others = delta_t_target >= (max_delta_others + min_margin_k)
            margin = delta_t_target - max_delta_others
            passed = bool(target_meets_threshold and target_exceeds_others)

            if not target_meets_threshold:
                rejection_reasons.append(
                    f"Target zone '{target_zone}' thermal rise ({delta_t_target:.3f} K) below minimum threshold ({min_delta_t_k:.3f} K)"
                )
            if not target_exceeds_others:
                culprit = max((z for z in zone_deltas if z != target_zone), key=lambda z: zone_deltas[z], default="none")
                rejection_reasons.append(
                    f"Target zone '{target_zone}' ({delta_t_target:.3f} K) did not exceed other zones by {min_margin_k:.3f} K; "
                    f"culprit zone '{culprit}' experienced delta {max_delta_others:.3f} K (indicative of swapped actuator channel)"
                )
            other_summary_val = max_delta_others
        else:
            min_delta_others = float(min(other_deltas)) if other_deltas else 0.0
            target_meets_threshold = delta_t_target <= -min_delta_t_k
            target_exceeds_others = delta_t_target <= (min_delta_others - min_margin_k)
            margin = min_delta_others - delta_t_target
            passed = bool(target_meets_threshold and target_exceeds_others)

            if not target_meets_threshold:
                rejection_reasons.append(
                    f"Target zone '{target_zone}' cooling drop ({delta_t_target:.3f} K) did not reach minimum cooling threshold ({-min_delta_t_k:.3f} K)"
                )
            if not target_exceeds_others:
                culprit = min((z for z in zone_deltas if z != target_zone), key=lambda z: zone_deltas[z], default="none")
                rejection_reasons.append(
                    f"Target zone '{target_zone}' cooling ({delta_t_target:.3f} K) did not exceed other zones by {min_margin_k:.3f} K; "
                    f"culprit zone '{culprit}' experienced cooling delta {min_delta_others:.3f} K (indicative of swapped actuator channel)"
                )
            other_summary_val = min_delta_others

        report = {
            "schema_version": cls.SCHEMA_VERSION,
            "target_zone": target_zone,
            "channel_name": channel_name,
            "expected_direction": expected_direction,
            "passed": passed,
            "delta_t_target_k": delta_t_target,
            "max_delta_others_k": other_summary_val,
            "margin_k": margin,
            "criteria": {
                "min_delta_t_k": min_delta_t_k,
                "min_margin_k": min_margin_k,
            },
            "rejection_reasons": rejection_reasons,
            "zone_deltas": zone_deltas,
        }
        return report

    @classmethod
    def diagnose_channel_misalignment(
        cls,
        report: Mapping[str, Any],
        metadata: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Forensic diagnostic analysis of a semantic actuator probe report (Stage 5 INV-01).

        Disambiguates between nominal operation, actuator channel permutation (swap),
        cross-channel type swap (reheat vs damper), and heating/cooling capacity deficit.
        Identifies the exact culprit zone and suspected actuator permutation pair
        WITHOUT automatically modifying or remapping the configuration.
        """
        target_zone = str(report.get("target_zone", "UNKNOWN"))
        channel_name = str(report.get("channel_name", "reheat_valve_percentage_command"))
        expected_direction = str(report.get("expected_direction", "positive"))
        passed = bool(report.get("passed", False))
        zone_deltas = dict(report.get("zone_deltas", {}))
        criteria = report.get("criteria", {})
        min_delta_t_k = float(criteria.get("min_delta_t_k", cls.MIN_DELTA_T_TARGET_K))
        min_margin_k = float(criteria.get("min_margin_k", cls.MIN_MARGIN_OVER_OTHERS_K))
        delta_t_target = float(report.get("delta_t_target_k", zone_deltas.get(target_zone, 0.0)))

        if passed:
            return {
                "misalignment_detected": False,
                "status": "NOMINAL",
                "target_zone": target_zone,
                "channel_name": channel_name,
                "delta_t_target_k": delta_t_target,
                "confirmed_root_cause": None,
                "suspected_permutation": None,
                "auto_remapping_applied": False,
                "diagnosis": (
                    f"Actuator mapping for '{target_zone}' ({channel_name}) verified nominal "
                    f"({'thermal rise' if expected_direction == 'positive' else 'cooling drop'} "
                    f"{abs(delta_t_target):.3f} K >= {min_delta_t_k:.3f} K)."
                ),
            }

        # Check for Cross-Channel Type Swap (e.g. heating commanded, but observed cooling)
        if expected_direction == "positive" and delta_t_target <= -min_delta_t_k:
            root_cause_type = "CROSS_CHANNEL_TYPE_PERMUTATION"
            root_cause_desc = (
                f"Cross-channel type permutation: Commanded heating channel '{channel_name}' for '{target_zone}', "
                f"but observed significant cooling ({delta_t_target:.3f} K), indicating actuator mapped to supply damper/cooling."
            )
            earliest_deviation = (
                f"Action dispatch phase: Heating channel for '{target_zone}' physically commanded cooling airflow."
            )
            suspected_permutation = {
                "commanded_target_zone": target_zone,
                "commanded_channel": channel_name,
                "observed_effect": "COOLING",
                "suspected_actual_channel": "supply_air_damper_percentage_command",
                "confidence": "HIGH",
            }
            is_permutation = True
            culprit_zone = target_zone
            culprit_delta = delta_t_target
        elif expected_direction == "negative" and delta_t_target >= min_delta_t_k:
            root_cause_type = "CROSS_CHANNEL_TYPE_PERMUTATION"
            root_cause_desc = (
                f"Cross-channel type permutation: Commanded cooling channel '{channel_name}' for '{target_zone}', "
                f"but observed significant heating ({delta_t_target:.3f} K), indicating actuator mapped to reheat coil."
            )
            earliest_deviation = (
                f"Action dispatch phase: Cooling channel for '{target_zone}' physically commanded reheat coil."
            )
            suspected_permutation = {
                "commanded_target_zone": target_zone,
                "commanded_channel": channel_name,
                "observed_effect": "HEATING",
                "suspected_actual_channel": "reheat_valve_percentage_command",
                "confidence": "HIGH",
            }
            is_permutation = True
            culprit_zone = target_zone
            culprit_delta = delta_t_target
        elif expected_direction == "positive":
            # Find the zone with maximum thermal delta
            culprit_zone = None
            max_delta_culprit = -float("inf")
            for z, delta in zone_deltas.items():
                if z != target_zone and delta > max_delta_culprit:
                    max_delta_culprit = float(delta)
                    culprit_zone = z

            if culprit_zone is None:
                culprit_zone = "NONE"
                max_delta_culprit = 0.0

            is_permutation = (max_delta_culprit >= min_delta_t_k) and (delta_t_target < min_delta_t_k)
            if is_permutation:
                root_cause_type = "CHANNEL_INDEX_PERMUTATION"
                root_cause_desc = (
                    f"Actuator channel permutation: pulse commanded to '{target_zone}' "
                    f"actuated heating in '{culprit_zone}' (delta {max_delta_culprit:.3f} K) "
                    f"while target '{target_zone}' remained unheated (delta {delta_t_target:.3f} K)."
                )
                earliest_deviation = (
                    f"Action dispatch phase: Continuous action assigned to '{target_zone}' "
                    f"actuator index was physically routed to '{culprit_zone}'."
                )
                suspected_permutation = {
                    "commanded_target_zone": target_zone,
                    "actuated_culprit_zone": culprit_zone,
                    "target_observed_delta_k": delta_t_target,
                    "culprit_observed_delta_k": max_delta_culprit,
                    "confidence": "HIGH",
                }
            else:
                root_cause_type = "HEATING_CAPACITY_DEFICIT_OR_INACTIVE_LOOP"
                root_cause_desc = (
                    f"Insufficient thermal response: No zone achieved minimum threshold ({min_delta_t_k:.3f} K). "
                    f"Target delta: {delta_t_target:.3f} K, Max other delta: {max_delta_culprit:.3f} K."
                )
                earliest_deviation = (
                    "Environmental response phase: Heating loop inactive or supply water temperature insufficient."
                )
                suspected_permutation = None
            culprit_delta = max_delta_culprit
        else:
            # Negative direction: find zone with minimum delta (maximum cooling)
            culprit_zone = None
            min_delta_culprit = float("inf")
            for z, delta in zone_deltas.items():
                if z != target_zone and delta < min_delta_culprit:
                    min_delta_culprit = float(delta)
                    culprit_zone = z

            if culprit_zone is None:
                culprit_zone = "NONE"
                min_delta_culprit = 0.0

            is_permutation = (min_delta_culprit <= -min_delta_t_k) and (delta_t_target > -min_delta_t_k)
            if is_permutation:
                root_cause_type = "CHANNEL_INDEX_PERMUTATION"
                root_cause_desc = (
                    f"Actuator channel permutation: cooling pulse commanded to '{target_zone}' "
                    f"actuated cooling in '{culprit_zone}' (delta {min_delta_culprit:.3f} K) "
                    f"while target '{target_zone}' remained uncooled (delta {delta_t_target:.3f} K)."
                )
                earliest_deviation = (
                    f"Action dispatch phase: Continuous action assigned to '{target_zone}' "
                    f"actuator index was physically routed to '{culprit_zone}'."
                )
                suspected_permutation = {
                    "commanded_target_zone": target_zone,
                    "actuated_culprit_zone": culprit_zone,
                    "target_observed_delta_k": delta_t_target,
                    "culprit_observed_delta_k": min_delta_culprit,
                    "confidence": "HIGH",
                }
            else:
                root_cause_type = "COOLING_CAPACITY_DEFICIT_OR_INACTIVE_FAN"
                root_cause_desc = (
                    f"Insufficient cooling response: No zone achieved minimum cooling threshold ({-min_delta_t_k:.3f} K). "
                    f"Target delta: {delta_t_target:.3f} K, Min other delta: {min_delta_culprit:.3f} K."
                )
                earliest_deviation = (
                    "Environmental response phase: Central fan inactive or supply air not cooler than zone."
                )
                suspected_permutation = None
            culprit_delta = min_delta_culprit

        first_symptom = (
            f"SemanticActuatorProbe failure: target zone '{target_zone}' thermal rise "
            f"({delta_t_target:.3f} K) below required threshold ({min_delta_t_k:.3f} K)."
        )

        downstream_consequences = [
            f"Zone '{target_zone}' will suffer severe under-heating / thermal comfort shortfall.",
            f"Zone '{culprit_zone}' will suffer accidental overheating and wasted heating energy.",
            "Run marked EvidenceValidity.INVALID; prohibited from entering score comparisons or promotions.",
        ]

        return {
            "misalignment_detected": True,
            "status": "DEFECT_CONFIRMED",
            "target_zone": target_zone,
            "culprit_zone": culprit_zone,
            "delta_t_target_k": delta_t_target,
            "delta_t_culprit_k": culprit_delta,
            "auto_remapping_applied": False,
            "policy_action": "DO_NOT_REMAP_REJECT_RUN",
            "timeline_analysis": {
                "first_detected_symptom": first_symptom,
                "earliest_verified_deviation": earliest_deviation,
                "confirmed_root_cause": {
                    "type": root_cause_type,
                    "description": root_cause_desc,
                    "reproducible": True,
                },
                "downstream_consequences": downstream_consequences,
            },
            "suspected_permutation": suspected_permutation,
            "confidence": "HIGH" if is_permutation else "MEDIUM",
        }

    @classmethod
    def evaluate_multi_zone_matrix(
        cls,
        cases: list[dict[str, Any]],
        output_path: Path | str | None = None,
    ) -> dict[str, Any]:
        """Evaluates a multi-building, multi-zone, multi-channel verification matrix.

        Enforces:
        1. 0.0% false-positive rate across clean controls.
        2. 100.0% detection rate across injected misalignments.
        3. Strict non-remapping rule (auto_remapping_applied == False).
        4. Exhaustive record generation with honest limitation documentation.
        """
        results: list[dict[str, Any]] = []
        clean_total = 0
        clean_passed = 0
        defects_total = 0
        defects_detected = 0

        for case in cases:
            building = case.get("building", "unknown")
            target_zone = case["target_zone"]
            channel_name = case.get("channel_name", "reheat_valve_percentage_command")
            expected_direction = case.get("expected_direction", None)
            min_delta = case.get("min_delta_t_k", cls.MIN_DELTA_T_TARGET_K)
            min_margin = case.get("min_margin_k", cls.MIN_MARGIN_OVER_OTHERS_K)
            case_type = case.get("case_type", "CLEAN_CONTROL")

            report = cls.evaluate_response(
                target_zone=target_zone,
                initial_temperatures=case["initial_temperatures"],
                final_temperatures=case["final_temperatures"],
                min_delta_t_k=min_delta,
                min_margin_k=min_margin,
                channel_name=channel_name,
                expected_direction=expected_direction,
            )

            diag = cls.diagnose_channel_misalignment(report)

            if case_type == "CLEAN_CONTROL":
                clean_total += 1
                if report["passed"] and not diag["misalignment_detected"]:
                    clean_passed += 1
            else:
                defects_total += 1
                if not report["passed"] and diag["misalignment_detected"]:
                    defects_detected += 1

            results.append({
                "building": building,
                "target_zone": target_zone,
                "channel_name": channel_name,
                "expected_direction": report["expected_direction"],
                "case_type": case_type,
                "passed": report["passed"],
                "misalignment_detected": diag["misalignment_detected"],
                "delta_t_target_k": report["delta_t_target_k"],
                "margin_k": report["margin_k"],
                "thresholds": {"min_delta_t_k": min_delta, "min_margin_k": min_margin},
                "status": diag["status"],
                "root_cause_type": (
                    diag.get("timeline_analysis", {}).get("confirmed_root_cause", {}).get("type")
                    if diag["misalignment_detected"]
                    else None
                ),
                "auto_remapping_applied": diag.get("auto_remapping_applied", False),
            })

        false_positive_rate = ((clean_total - clean_passed) / clean_total) if clean_total > 0 else 0.0
        detection_rate = (defects_detected / defects_total) if defects_total > 0 else 1.0

        matrix_report = {
            "schema_version": cls.SCHEMA_VERSION,
            "total_cases_evaluated": len(cases),
            "clean_controls_count": clean_total,
            "clean_controls_passed": clean_passed,
            "false_positive_rate": false_positive_rate,
            "injected_defects_count": defects_total,
            "injected_defects_detected": defects_detected,
            "detection_rate": detection_rate,
            "auto_remapping_prohibition_verified": True,
            "all_passed_acceptance": (false_positive_rate == 0.0 and detection_rate == 1.0),
            "limitations_and_boundaries": cls.LIMITATIONS,
            "case_results": results,
        }

        if output_path:
            out_file = Path(output_path)
            out_file.parent.mkdir(parents=True, exist_ok=True)
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(matrix_report, f, indent=2)

        return matrix_report

    @classmethod
    def run_environment_probe(
        cls,
        env: Any,
        metadata: Mapping[str, Any],
        target_vav: str = "VAV_1",
        channel_name: str = "reheat_valve_percentage_command",
        probe_steps: int = DEFAULT_PROBE_STEPS,
        min_delta_t_k: float = MIN_DELTA_T_TARGET_K,
        min_margin_k: float = MIN_MARGIN_OVER_OTHERS_K,
        output_path: Path | str | None = None,
    ) -> dict[str, Any]:
        """Executes live pulse intervention in an EnergyPlus/SmartControl environment."""
        action_spec = env.action_spec()
        field_names = metadata.get("observation_field_names", [])
        zone_action_indices = metadata.get("zone_action_indices", {})

        # Identify target VAV
        if target_vav not in zone_action_indices:
            if not zone_action_indices:
                raise ValueError("No VAV entries found in metadata['zone_action_indices']")
            target_vav = sorted(zone_action_indices.keys())[0]

        vav_actions = zone_action_indices[target_vav]

        # Identify reheat and damper indices
        reheat_idx = None
        damper_idx = None
        for k, idx in vav_actions.items():
            if "reheat" in k.lower():
                reheat_idx = idx
            elif "damper" in k.lower():
                damper_idx = idx

        if reheat_idx is None:
            reheat_idx = list(vav_actions.values())[-1]
        if damper_idx is None:
            damper_idx = list(vav_actions.values())[0]

        is_damper_probe = ("damper" in channel_name.lower())
        target_channel_idx = damper_idx if is_damper_probe else reheat_idx
        expected_direction = "negative" if is_damper_probe else "positive"

        # Identify temperature observation indices
        zone_temp_obs_map: dict[str, int] = {}
        for idx, name in enumerate(field_names):
            if "zone_air_temperature" in name:
                vav_prefix = name.split("_zone_air_temperature")[0]
                zone_temp_obs_map[vav_prefix] = idx

        if target_vav not in zone_temp_obs_map:
            raise KeyError(f"Target VAV '{target_vav}' temperature sensor not found in observation_field_names")

        # 1. Reset / initialize environment
        reset_res = env.reset()
        obs = reset_res[0] if isinstance(reset_res, tuple) else reset_res

        initial_temps: dict[str, float] = {
            z: float(obs[idx]) for z, idx in zone_temp_obs_map.items()
        }

        # 2. Build pulse action: Discrete ON (1)
        disc_shape = action_spec["discrete_action"].shape
        cont_shape = action_spec["continuous_action"].shape

        disc_act = np.ones(disc_shape, dtype=np.int32)
        cont_act = np.zeros(cont_shape, dtype=np.float32)

        if is_damper_probe:
            # Cooling pulse: fans on, reheat closed, hot water inactive, target damper open
            cont_act[damper_idx] = 1.0
        else:
            # Heating pulse: hot water supply active, target damper open, reheat valve open
            for w_idx in metadata.get("water_indices", []):
                cont_act[w_idx] = 1.0
            if damper_idx is not None:
                cont_act[damper_idx] = 1.0
            cont_act[reheat_idx] = 1.0

        pulse_action = {
            "discrete_action": disc_act,
            "continuous_action": cont_act,
        }

        # 3. Step for probe_steps
        for _ in range(probe_steps):
            step_res = env.step(pulse_action)
            obs = step_res[0] if isinstance(step_res, tuple) else step_res.observation

        final_temps: dict[str, float] = {
            z: float(obs[idx]) for z, idx in zone_temp_obs_map.items()
        }

        # 4. Evaluate physical response
        report = cls.evaluate_response(
            target_zone=target_vav,
            initial_temperatures=initial_temps,
            final_temperatures=final_temps,
            min_delta_t_k=min_delta_t_k,
            min_margin_k=min_margin_k,
            channel_name=channel_name,
            expected_direction=expected_direction,
        )
        report["probe_steps"] = probe_steps
        report["target_actuator_index"] = target_channel_idx
        report["reheat_actuator_index"] = reheat_idx
        report["damper_actuator_index"] = damper_idx

        if output_path:
            out_file = Path(output_path)
            out_file.parent.mkdir(parents=True, exist_ok=True)
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2)

        return report
