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
    """Performs and evaluates single-variable pulse interventions on HVAC actuators."""

    SCHEMA_VERSION = "v1.0"
    DEFAULT_PROBE_STEPS = 4
    MIN_DELTA_T_TARGET_K = 0.5
    MIN_MARGIN_OVER_OTHERS_K = 0.3

    @classmethod
    def evaluate_response(
        cls,
        target_zone: str,
        initial_temperatures: Mapping[str, float],
        final_temperatures: Mapping[str, float],
        min_delta_t_k: float = MIN_DELTA_T_TARGET_K,
        min_margin_k: float = MIN_MARGIN_OVER_OTHERS_K,
    ) -> dict[str, Any]:
        """Audits zone temperature deltas from a single-actuator pulse intervention."""
        if target_zone not in initial_temperatures or target_zone not in final_temperatures:
            raise KeyError(f"Target zone '{target_zone}' not found in temperature mappings")

        zone_deltas: dict[str, float] = {}
        for z in initial_temperatures:
            if z in final_temperatures:
                zone_deltas[z] = float(final_temperatures[z] - initial_temperatures[z])

        delta_t_target = zone_deltas[target_zone]
        other_deltas = [d for z, d in zone_deltas.items() if z != target_zone]
        max_delta_others = float(max(other_deltas)) if other_deltas else 0.0

        target_meets_threshold = delta_t_target >= min_delta_t_k
        target_exceeds_others = delta_t_target >= (max_delta_others + min_margin_k)
        passed = bool(target_meets_threshold and target_exceeds_others)

        # Detect defect modes (e.g. swapped actuator channels)
        rejection_reasons: list[str] = []
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

        report = {
            "schema_version": cls.SCHEMA_VERSION,
            "target_zone": target_zone,
            "passed": passed,
            "delta_t_target_k": delta_t_target,
            "max_delta_others_k": max_delta_others,
            "margin_k": delta_t_target - max_delta_others,
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
        and heating capacity deficit. Identifies the exact culprit zone and suspected
        actuator permutation pair without automatically modifying the configuration.
        """
        target_zone = str(report.get("target_zone", "UNKNOWN"))
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
                "delta_t_target_k": delta_t_target,
                "confirmed_root_cause": None,
                "suspected_permutation": None,
                "diagnosis": f"Actuator mapping for '{target_zone}' verified nominal (thermal rise {delta_t_target:.3f} K >= {min_delta_t_k:.3f} K).",
            }

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

        # Differentiate between channel permutation (swap) and general heating deficit
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
            "delta_t_culprit_k": max_delta_culprit,
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
    def run_environment_probe(
        cls,
        env: Any,
        metadata: Mapping[str, Any],
        target_vav: str = "VAV_1",
        probe_steps: int = DEFAULT_PROBE_STEPS,
        min_delta_t_k: float = MIN_DELTA_T_TARGET_K,
        min_margin_k: float = MIN_MARGIN_OVER_OTHERS_K,
        output_path: Path | str | None = None,
    ) -> dict[str, Any]:
        """Executes live pulse intervention in an EnergyPlus/SmartControl environment."""
        action_spec = env.action_spec()
        field_names = metadata.get("observation_field_names", [])
        zone_action_indices = metadata.get("zone_action_indices", {})

        # Identify reheat actuator index for target_vav
        if target_vav not in zone_action_indices:
            if not zone_action_indices:
                raise ValueError("No VAV entries found in metadata['zone_action_indices']")
            target_vav = sorted(zone_action_indices.keys())[0]

        vav_actions = zone_action_indices[target_vav]
        reheat_idx = None
        for k, idx in vav_actions.items():
            if "reheat" in k.lower():
                reheat_idx = idx
                break
        if reheat_idx is None:
            reheat_idx = list(vav_actions.values())[-1]

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

        # 2. Build pulse action: Discrete ON (1), hot water supply active, target damper open & reheat pulse
        disc_shape = action_spec["discrete_action"].shape
        cont_shape = action_spec["continuous_action"].shape

        disc_act = np.ones(disc_shape, dtype=np.int32)
        cont_act = np.zeros(cont_shape, dtype=np.float32)

        # Supply hot water if building declares water loop indices
        for w_idx in metadata.get("water_indices", []):
            cont_act[w_idx] = 1.0

        # Ensure airflow across target reheat coil by opening its supply damper
        target_damper = vav_actions.get("supply_air_damper_percentage_command")
        if target_damper is not None:
            cont_act[target_damper] = 1.0

        # Pulse target reheat valve
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
        )
        report["probe_steps"] = probe_steps
        report["reheat_actuator_index"] = reheat_idx

        if output_path:
            out_file = Path(output_path)
            out_file.parent.mkdir(parents=True, exist_ok=True)
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2)

        return report
