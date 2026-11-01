"""Evaluation Governance and Comparison Validator for Smart Buildings Challenge.
Automates evaluation governance:
- Enforces environment partitioning, suite schemas, role boundaries, and overlap rules (E1).
- Strictly validates matched comparisons between candidate policies and baselines (E2).
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Mapping, Sequence
import yaml


class SuiteValidator:
    """Enforces evaluation environment governance, role boundaries, and overlap rules (E1)."""

    ALLOWED_ROLES = {"DEV", "SELECT", "GENERALIZATION", "STRESS", "SEALED RELEASE"}

    # Authoritative 6 public training buildings from the pinned competition starter kit
    PUBLIC_TRAINING_BUILDINGS = {
        "building_train_1",
        "building_train_2",
        "building_train_4",
        "building_train_5",
        "building_train_7",
        "building_train_8",
    }

    # Authoritative 5 public weather locations
    PUBLIC_WEATHER_PREFIXES = {"atlanta", "denver", "fairbanks", "phoenix", "singapore"}

    @classmethod
    def load_suite(cls, manifest_source: dict[str, Any] | Path | str) -> dict[str, Any]:
        """Loads a suite manifest from a dict, file path, or YAML string."""
        if isinstance(manifest_source, dict):
            return manifest_source
        p = Path(manifest_source)
        if p.is_file():
            with open(p, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        try:
            parsed = yaml.safe_load(str(manifest_source))
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass
        raise ValueError(f"Invalid suite manifest source: {manifest_source}")

    @classmethod
    def validate_suite_manifest(
        cls,
        manifest_source: dict[str, Any] | Path | str,
        known_scenarios: set[str] | Sequence[str] | None = None,
    ) -> dict[str, Any]:
        """Validates suite schema, required fields, duplicates, role validity, and provenance."""
        try:
            data = cls.load_suite(manifest_source)
        except Exception as e:
            return {
                "valid": False,
                "rejection_reasons": [f"Failed to load suite manifest: {str(e)}"],
            }

        reasons: list[str] = []

        # 1. Required top-level keys
        required_keys = [
            "suite_name",
            "version",
            "role",
            "expected_scenario_count",
            "steps_per_episode",
            "commit_pinned",
            "scenarios",
        ]
        for k in required_keys:
            if k not in data or data[k] is None:
                reasons.append(f"Missing required suite attribute: '{k}'")

        # 2. Role validation
        role = data.get("role")
        if role not in cls.ALLOWED_ROLES:
            reasons.append(
                f"Invalid suite role: '{role}'. Must be one of {sorted(cls.ALLOWED_ROLES)}"
            )

        # 3. Scenarios validation
        scenarios = data.get("scenarios", [])
        if not isinstance(scenarios, list):
            reasons.append("'scenarios' must be a list")
            scenarios = []

        expected_count = data.get("expected_scenario_count")
        if expected_count is not None and len(scenarios) != expected_count:
            reasons.append(
                f"Scenario count mismatch: manifest declares expected_scenario_count={expected_count}, "
                f"but lists {len(scenarios)} scenarios"
            )

        scenario_ids: list[str] = []
        seen_ids: set[str] = set()
        buildings: set[str] = set()
        weathers: set[str] = set()

        for idx, sc in enumerate(scenarios):
            if not isinstance(sc, dict):
                reasons.append(f"Scenario at index {idx} is not a dictionary")
                continue
            sc_id = sc.get("id")
            if not sc_id:
                reasons.append(f"Scenario at index {idx} is missing required 'id'")
                continue

            # Duplicate check inside suite (Defect 1)
            if sc_id in seen_ids:
                reasons.append(f"Duplicate scenario inside suite: '{sc_id}'")
            seen_ids.add(sc_id)
            scenario_ids.append(sc_id)

            bldg = sc.get("building")
            wthr = sc.get("weather")
            if not bldg:
                reasons.append(f"Scenario '{sc_id}' missing 'building'")
            else:
                buildings.add(bldg)
            if not wthr:
                reasons.append(f"Scenario '{sc_id}' missing 'weather'")
            else:
                weathers.add(wthr)

            # Unknown scenario ID check (Defect 2)
            if known_scenarios is not None:
                known_set = set(known_scenarios)
                if sc_id not in known_set and "generator_provenance" not in sc:
                    reasons.append(
                        f"Unknown scenario identifier: '{sc_id}' not found in known catalog "
                        "and lacks generator_provenance"
                    )

        # 4. Provenance validation (Defect 3)
        if not data.get("commit_pinned") and not data.get("generator_provenance"):
            reasons.append("Missing required provenance: suite must specify commit_pinned or generator_provenance")

        # 5. Public benchmark falsely declared sealed or independent (Defect 9)
        if role == "SEALED RELEASE":
            public_overlap = buildings.intersection(cls.PUBLIC_TRAINING_BUILDINGS)
            if public_overlap:
                reasons.append(
                    "Public benchmark falsely declared sealed: suite claims role 'SEALED RELEASE' "
                    f"but contains public training buildings {sorted(public_overlap)}"
                )

        # Contamination check: GENERALIZATION suite consisting solely of public training buildings without transfer metadata
        if role == "GENERALIZATION" and not data.get("transfer_provenance"):
            if buildings.issubset(cls.PUBLIC_TRAINING_BUILDINGS) and len(buildings) > 0:
                reasons.append(
                    "Contamination: GENERALIZATION suite consists solely of public training buildings "
                    "without declaring transfer_provenance"
                )

        return {
            "valid": len(reasons) == 0,
            "rejection_reasons": reasons,
            "suite_name": data.get("suite_name"),
            "version": data.get("version"),
            "role": role,
            "scenario_ids": scenario_ids,
            "buildings": buildings,
            "weathers": weathers,
        }

    @classmethod
    def check_suite_overlap(
        cls,
        suite_a_src: dict[str, Any] | Path | str,
        suite_b_src: dict[str, Any] | Path | str,
    ) -> dict[str, Any]:
        """Enforces partition rules and distinguishes ALLOWED vs DISALLOWED vs UNKNOWN overlap (E1)."""
        suite_a = cls.load_suite(suite_a_src)
        suite_b = cls.load_suite(suite_b_src)

        role_a = suite_a.get("role")
        role_b = suite_b.get("role")

        def extract_meta(suite):
            scs = suite.get("scenarios", [])
            ids = {s.get("id") for s in scs if isinstance(s, dict) and s.get("id")}
            bldgs = {s.get("building") for s in scs if isinstance(s, dict) and s.get("building")}
            weathers = {s.get("weather") for s in scs if isinstance(s, dict) and s.get("weather")}
            pairs = {
                (s.get("building"), s.get("weather"))
                for s in scs
                if isinstance(s, dict) and s.get("building") and s.get("weather")
            }
            return ids, bldgs, weathers, pairs

        ids_a, bldgs_a, weathers_a, pairs_a = extract_meta(suite_a)
        ids_b, bldgs_b, weathers_b, pairs_b = extract_meta(suite_b)

        exact_overlap = sorted(list(ids_a.intersection(ids_b)))
        building_overlap = sorted(list(bldgs_a.intersection(bldgs_b)))
        weather_overlap = sorted(list(weathers_a.intersection(weathers_b)))
        pair_overlap = sorted([f"{b}/{w}" for b, w in pairs_a.intersection(pairs_b)])

        rejection_reasons: list[str] = []
        status = "ALLOWED"

        # Check unknown provenance first
        if not suite_a.get("commit_pinned") or not suite_b.get("commit_pinned"):
            status = "UNKNOWN"
            rejection_reasons.append("Unknown overlap: missing commit_pinned prevents verifiable partition audit")
            return {
                "status": status,
                "allowed": False,
                "exact_scenario_overlap": exact_overlap,
                "building_overlap": building_overlap,
                "weather_overlap": weather_overlap,
                "pair_overlap": pair_overlap,
                "rejection_reasons": rejection_reasons,
            }

        # Policy checks
        # 1. DEV suite: freely permitted to overlap with SELECT/STRESS for fast testing
        if role_a == "DEV" or role_b == "DEV":
            status = "ALLOWED"
            return {
                "status": status,
                "allowed": True,
                "exact_scenario_overlap": exact_overlap,
                "building_overlap": building_overlap,
                "weather_overlap": weather_overlap,
                "pair_overlap": pair_overlap,
                "rejection_reasons": [],
            }

        # 2. SEALED RELEASE overlap check (Defect 5 / Defect 9)
        if role_a == "SEALED RELEASE" or role_b == "SEALED RELEASE":
            if exact_overlap or building_overlap or weather_overlap:
                status = "DISALLOWED"
                rejection_reasons.append(
                    "Prohibited overlap with protected SEALED RELEASE set: local scenarios overlap with sealed set"
                )

        # 3. GENERALIZATION vs SELECT overlap check (Defect 5, 6, 7)
        roles = {role_a, role_b}
        if "GENERALIZATION" in roles and "SELECT" in roles:
            # Check exact scenario overlap (Defect 5)
            if exact_overlap:
                status = "DISALLOWED"
                rejection_reasons.append(
                    f"Prohibited exact scenario overlap between SELECT and GENERALIZATION: {exact_overlap}"
                )

            # Check prohibited building overlap if declared out-of-distribution buildings (Defect 6)
            gen_suite = suite_a if role_a == "GENERALIZATION" else suite_b
            if gen_suite.get("holdout_dimension") == "BUILDING" and building_overlap:
                status = "DISALLOWED"
                rejection_reasons.append(
                    f"Prohibited building overlap in building-generalization evaluation: {building_overlap}"
                )

            # Check prohibited weather overlap if declared out-of-distribution weather (Defect 7)
            if gen_suite.get("holdout_dimension") == "WEATHER" and weather_overlap:
                status = "DISALLOWED"
                rejection_reasons.append(
                    f"Prohibited weather overlap in weather-generalization evaluation: {weather_overlap}"
                )

        is_allowed = (status == "ALLOWED") and (len(rejection_reasons) == 0)
        return {
            "status": status if not rejection_reasons else "DISALLOWED",
            "allowed": is_allowed,
            "exact_scenario_overlap": exact_overlap,
            "building_overlap": building_overlap,
            "weather_overlap": weather_overlap,
            "pair_overlap": pair_overlap,
            "rejection_reasons": rejection_reasons,
        }

    @classmethod
    def validate_suite_version_consistency(
        cls,
        old_manifest_src: dict[str, Any] | Path | str,
        new_manifest_src: dict[str, Any] | Path | str,
    ) -> dict[str, Any]:
        """Detects undeclared suite-membership changes without version increment (Defect 4)."""
        old_data = cls.load_suite(old_manifest_src)
        new_data = cls.load_suite(new_manifest_src)

        old_ver = old_data.get("version")
        new_ver = new_data.get("version")

        old_scs = sorted([s.get("id") for s in old_data.get("scenarios", []) if isinstance(s, dict)])
        new_scs = sorted([s.get("id") for s in new_data.get("scenarios", []) if isinstance(s, dict)])

        if old_ver == new_ver and old_scs != new_scs:
            return {
                "valid": False,
                "error": (
                    f"Undeclared suite-membership change: scenario membership changed from {old_scs} "
                    f"to {new_scs} while remaining at version '{old_ver}'"
                ),
            }
        return {"valid": True, "error": None}

    @classmethod
    def check_role_eligibility(
        cls,
        manifest_src: dict[str, Any] | Path | str,
        intended_use: str,
    ) -> dict[str, Any]:
        """Enforces that suite roles match their operational consequences (Defect 8)."""
        data = cls.load_suite(manifest_src)
        role = data.get("role")
        suite_name = data.get("suite_name")

        if intended_use == "CANDIDATE_SELECTION" and role != "SELECT":
            return {
                "eligible": False,
                "error": (
                    f"Incorrect suite role for candidate selection: suite '{suite_name}' has role '{role}'. "
                    "Only 'SELECT' suites (such as official_reference_suite) can be used for candidate selection or submission."
                ),
            }

        if intended_use == "GENERALIZATION_CLAIM" and role != "GENERALIZATION":
            return {
                "eligible": False,
                "error": (
                    f"Incorrect suite role for generalization claim: suite '{suite_name}' has role '{role}'. "
                    "Only 'GENERALIZATION' suites can support generalization claims."
                ),
            }

        return {"eligible": True, "error": None}


class ComparisonValidator:
    """Enforces the Candidate Comparison Contract (E2)."""

    PARITY_TOLERANCE = 1.0e-6

    @classmethod
    def validate_comparison(
        cls,
        candidate_eval: Mapping[str, Any],
        baseline_eval: Mapping[str, Any],
    ) -> dict[str, Any]:
        """Validates whether two policy evaluations can be legitimately compared."""
        rejection_reasons: list[str] = []

        # 1. Check suite identity and version (Defect 10)
        cand_suite = candidate_eval.get("suite_name")
        base_suite = baseline_eval.get("suite_name")
        cand_ver = candidate_eval.get("suite_version")
        base_ver = baseline_eval.get("suite_version")

        if cand_suite != base_suite:
            rejection_reasons.append(
                f"Suite mismatch: Candidate ran on '{cand_suite}', Baseline ran on '{base_suite}'"
            )
        if cand_ver != base_ver:
            rejection_reasons.append(
                f"Suite version mismatch: Candidate ran on v'{cand_ver}', Baseline ran on v'{base_ver}'"
            )

        # 2. Check evaluator and simulator versions (Defect 14)
        cand_eval_ver = candidate_eval.get("evaluator_version")
        base_eval_ver = baseline_eval.get("evaluator_version")
        if cand_eval_ver != base_eval_ver:
            rejection_reasons.append(
                f"Evaluator version mismatch: Candidate evaluated with '{cand_eval_ver}', Baseline with '{base_eval_ver}'"
            )

        cand_sim_ver = candidate_eval.get("simulator_version")
        base_sim_ver = baseline_eval.get("simulator_version")
        if cand_sim_ver is not None and base_sim_ver is not None and cand_sim_ver != base_sim_ver:
            rejection_reasons.append(
                f"Simulator version mismatch: Candidate ran on '{cand_sim_ver}', Baseline on '{base_sim_ver}'"
            )

        # 3. Check scenario coverage and duplicate scenario results (Defect 11, Defect 12)
        cand_raw_keys = list(candidate_eval.get("scenario_returns", {}).keys())
        base_raw_keys = list(baseline_eval.get("scenario_returns", {}).keys())

        if candidate_eval.get("has_duplicate_scenarios") or len(cand_raw_keys) != len(set(cand_raw_keys)):
            rejection_reasons.append("Candidate evaluation contains duplicate scenario results")
        if baseline_eval.get("has_duplicate_scenarios") or len(base_raw_keys) != len(set(base_raw_keys)):
            rejection_reasons.append("Baseline evaluation contains duplicate scenario results")

        cand_scenarios = set(cand_raw_keys)
        base_scenarios = set(base_raw_keys)
        expected_count = candidate_eval.get("expected_scenario_count")

        if expected_count is not None and len(cand_scenarios) != expected_count:
            rejection_reasons.append(
                f"Candidate incomplete: evaluated {len(cand_scenarios)}/{expected_count} scenarios"
            )
        if expected_count is not None and len(base_scenarios) != expected_count:
            rejection_reasons.append(
                f"Baseline incomplete: evaluated {len(base_scenarios)}/{expected_count} scenarios"
            )

        if cand_scenarios != base_scenarios:
            missing_in_cand = base_scenarios - cand_scenarios
            missing_in_base = cand_scenarios - base_scenarios
            if missing_in_cand:
                rejection_reasons.append(f"Candidate missing scenarios: {sorted(list(missing_in_cand))}")
            if missing_in_base:
                rejection_reasons.append(f"Baseline missing scenarios: {sorted(list(missing_in_base))}")

        # 4. Check episode step completeness / truncation (Defect 13)
        expected_steps = candidate_eval.get("steps_per_episode", 8640)
        cand_steps = candidate_eval.get("scenario_steps", {})
        base_steps = baseline_eval.get("scenario_steps", {})
        for sc, st in cand_steps.items():
            if st < expected_steps:
                rejection_reasons.append(f"Candidate episode truncated for scenario '{sc}': {st}/{expected_steps} steps")
        for sc, st in base_steps.items():
            if st < expected_steps:
                rejection_reasons.append(f"Baseline episode truncated for scenario '{sc}': {st}/{expected_steps} steps")

        # 5. Check missing or corrupted trace artifacts (Defect 15)
        if candidate_eval.get("trace_corrupted") or candidate_eval.get("trace_missing"):
            rejection_reasons.append("Candidate evaluation has missing or corrupted trace artifacts")
        if baseline_eval.get("trace_corrupted") or baseline_eval.get("trace_missing"):
            rejection_reasons.append("Baseline evaluation has missing or corrupted trace artifacts")

        # 6. Check run manifest hash match (Defect 16)
        if candidate_eval.get("artifact_hash_verified") is False:
            rejection_reasons.append("Candidate run manifest hash does not match artifact SHA-256")
        if baseline_eval.get("artifact_hash_verified") is False:
            rejection_reasons.append("Baseline run manifest hash does not match artifact SHA-256")

        # 7. Check execution status vs completion (Defect 17)
        cand_status = candidate_eval.get("status")
        base_status = baseline_eval.get("status")
        if cand_status == "COMPLETE" and (candidate_eval.get("is_incomplete", False) or (expected_count and len(cand_scenarios) < expected_count)):
            rejection_reasons.append("Candidate claims status COMPLETE despite incomplete execution")
        if base_status == "COMPLETE" and (baseline_eval.get("is_incomplete", False) or (expected_count and len(base_scenarios) < expected_count)):
            rejection_reasons.append("Baseline claims status COMPLETE despite incomplete execution")

        # 8. Check unverified scores (Defect 18)
        if candidate_eval.get("scores_independently_verified") is False:
            rejection_reasons.append("Candidate evaluation contains unverified scores")
        if baseline_eval.get("scores_independently_verified") is False:
            rejection_reasons.append("Baseline evaluation contains unverified scores")

        # 9. Check validity flags
        if not candidate_eval.get("all_episodes_valid", True):
            rejection_reasons.append("Candidate evaluation contains invalid or truncated episodes")
        if not baseline_eval.get("all_episodes_valid", True):
            rejection_reasons.append("Baseline evaluation contains invalid or truncated episodes")

        # 9b. Check evidence validity and quarantine status
        cand_validity = candidate_eval.get("evidence_validity")
        base_validity = baseline_eval.get("evidence_validity")

        if not cand_validity and candidate_eval.get("run_dir"):
            try:
                c_mf = Path(candidate_eval["run_dir"]) / "run_manifest.json"
                if c_mf.is_file():
                    with open(c_mf, "r", encoding="utf-8") as f:
                        cand_validity = json.load(f).get("evidence_validity")
            except Exception:
                pass

        if not base_validity and baseline_eval.get("run_dir"):
            try:
                b_mf = Path(baseline_eval["run_dir"]) / "run_manifest.json"
                if b_mf.is_file():
                    with open(b_mf, "r", encoding="utf-8") as f:
                        base_validity = json.load(f).get("evidence_validity")
            except Exception:
                pass

        if cand_validity == "QUARANTINED" or candidate_eval.get("is_quarantined") or candidate_eval.get("quarantined"):
            rejection_reasons.append("Candidate evidence validity is QUARANTINED: cannot be used in comparison")
        elif cand_validity == "INVALID":
            rejection_reasons.append("Candidate evidence validity is INVALID: cannot be used in comparison")

        if base_validity == "QUARANTINED" or baseline_eval.get("is_quarantined") or baseline_eval.get("quarantined"):
            rejection_reasons.append("Baseline evidence validity is QUARANTINED: cannot be used in comparison")
        elif base_validity == "INVALID":
            rejection_reasons.append("Baseline evidence validity is INVALID: cannot be used in comparison")

        # 10. Multi-scenario score sum consistency
        cand_returns = candidate_eval.get("scenario_returns", {})
        cand_total = candidate_eval.get("total_suite_return")
        if cand_total is not None and cand_returns:
            sum_cand = sum(cand_returns.values())
            if abs(cand_total - sum_cand) > cls.PARITY_TOLERANCE:
                rejection_reasons.append(
                    f"Candidate total_suite_return ({cand_total:.4f}) does not match sum of scenario returns ({sum_cand:.4f})"
                )

        base_returns = baseline_eval.get("scenario_returns", {})
        base_total = baseline_eval.get("total_suite_return")
        if base_total is not None and base_returns:
            sum_base = sum(base_returns.values())
            if abs(base_total - sum_base) > cls.PARITY_TOLERANCE:
                rejection_reasons.append(
                    f"Baseline total_suite_return ({base_total:.4f}) does not match sum of scenario returns ({sum_base:.4f})"
                )

        is_valid = len(rejection_reasons) == 0

        # Compute comparison metrics if valid
        cand_score = cand_total if cand_total is not None else (sum(cand_returns.values()) if cand_returns else 0.0)
        base_score = base_total if base_total is not None else (sum(base_returns.values()) if base_returns else 0.0)
        score_delta = cand_score - base_score if is_valid else None

        scenario_deltas = {}
        if is_valid:
            for sc in cand_scenarios:
                scenario_deltas[sc] = cand_returns[sc] - base_returns[sc]

        return {
            "valid_comparison": is_valid,
            "rejection_reasons": rejection_reasons,
            "candidate_score": cand_score,
            "baseline_score": base_score,
            "score_delta": score_delta,
            "candidate_is_improvement": (score_delta > 0.0) if score_delta is not None else None,
            "scenario_deltas": scenario_deltas,
        }
