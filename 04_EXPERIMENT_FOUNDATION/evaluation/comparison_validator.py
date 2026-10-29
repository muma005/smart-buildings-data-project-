"""Candidate Comparison Validator for Smart Buildings Challenge.
Automates evaluation governance: strictly validates compatibility between
candidate policies and baselines, rejecting mismatched suites or incomplete runs.
"""

from __future__ import annotations
from typing import Any, Mapping


class ComparisonValidator:
    """Enforces the Candidate Comparison Contract."""

    @classmethod
    def validate_comparison(
        cls,
        candidate_eval: Mapping[str, Any],
        baseline_eval: Mapping[str, Any],
    ) -> dict[str, Any]:
        """Validates whether two policy evaluations can be legitimately compared."""
        rejection_reasons: list[str] = []

        # 1. Check suite identity and version
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

        # 2. Check evaluator version
        cand_eval_ver = candidate_eval.get("evaluator_version")
        base_eval_ver = baseline_eval.get("evaluator_version")
        if cand_eval_ver != base_eval_ver:
            rejection_reasons.append(
                f"Evaluator version mismatch: Candidate evaluated with '{cand_eval_ver}', Baseline with '{base_eval_ver}'"
            )

        # 3. Check scenario coverage
        cand_scenarios = set(candidate_eval.get("scenario_returns", {}).keys())
        base_scenarios = set(baseline_eval.get("scenario_returns", {}).keys())
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

        # 4. Check validity flags
        if not candidate_eval.get("all_episodes_valid", False):
            rejection_reasons.append("Candidate evaluation contains invalid or truncated episodes")
        if not baseline_eval.get("all_episodes_valid", False):
            rejection_reasons.append("Baseline evaluation contains invalid or truncated episodes")

        is_valid = len(rejection_reasons) == 0

        # Compute comparison metrics if valid
        cand_score = candidate_eval.get("total_suite_return", 0.0)
        base_score = baseline_eval.get("total_suite_return", 0.0)
        score_delta = cand_score - base_score if is_valid else None

        scenario_deltas = {}
        if is_valid:
            cand_returns = candidate_eval.get("scenario_returns", {})
            base_returns = baseline_eval.get("scenario_returns", {})
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
