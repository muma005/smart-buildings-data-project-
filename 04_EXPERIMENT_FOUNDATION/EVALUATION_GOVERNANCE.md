# Phase 04 — Evaluation Governance & Comparison Safeguards

**Project:** Smart Buildings Challenge — NeurIPS 2026  
**Document:** EVALUATION_GOVERNANCE.md  
**Status:** OFFICIAL GOVERNANCE CONTRACT  

---

## 1. Mission & Governance Principles

Evaluation governance establishes the rules, scenario roles, and automated checks that protect our experimentation from:
1. **Contamination & Data Leakage**: Presenting public training scenarios as "held-out" or "unseen" test sets.
2. **Incompatible Comparisons**: Comparing a candidate policy on 1 scenario against a baseline on 30 scenarios, or comparing across different suite versions.
3. **Incomplete Runs**: Accepting aborted or truncated runs as valid policy performance.
4. **Metric Drift**: Comparing policies evaluated with different reward functions or evaluator versions.

---

## 2. The Five Evaluation Roles

Every scenario in an evaluation suite is assigned an explicit, provenance-tracked role:

| Role | Purpose | Permitted Use | Overlap & Contamination Rules |
| :--- | :--- | :--- | :--- |
| **`DEV`** | Fast iteration, debugging, unit tests | Rapid prototyping, gradient debugging, sanity checks | May freely overlap with other suites; never cited as leaderboard evidence. |
| **`SELECT`** | Benchmark candidate comparison | Final policy ranking and submission selection | Pinned to the official 30-scenario reference suite (`suites/official_suite.yaml`). |
| **`GENERALIZATION`** | Out-of-distribution transfer assessment | Evaluating policy transfer across unseen weather/building pairings | Generated with novel random seeds; strictly held out during routine tuning. |
| **`STRESS`** | Extreme climate edge cases | Robustness analysis under extreme freeze or heat | Fairbanks-1 and Phoenix-5 scenarios; used to diagnose catastrophic comfort cliffs. |
| **`SEALED RELEASE`** | Hidden competition evaluation | Final competition submission ranking | Held exclusively by Kaggle/judges; strictly inaccessible locally. |

> [!IMPORTANT]
> **No Synthetic Holdout Claims**: Renaming a public scenario does not make it unseen. Any scenario derived from the 6 training buildings and 5 weather files is public training data.

---

## 3. The Candidate Comparison Contract

To compare Policy $A$ (Candidate) against Policy $B$ (Baseline), the comparison must pass the automated **`ComparisonValidator`**. A comparison is **REJECTED** if any of the following conditions fail:

1. **Exact Suite Match**: Both policies must be evaluated on the exact same suite name and version (e.g. `official_reference_suite v1.0.0`).
2. **Complete Coverage**: The number of evaluated scenarios must exactly match `expected_scenario_count` (e.g. 30/30). A 29-scenario run cannot be compared against a 30-scenario run.
3. **Complete Episode Length**: Every episode in the suite must complete all required steps ($8,640$ steps). Truncated runs are marked `INVALID`.
4. **Identical Evaluator Version**: Both evaluations must be conducted by the certified `ScoreVerifier` engine under the same metric version.
5. **Preservation of Per-Scenario Traces**: Aggregates alone are insufficient; individual returns for all scenarios must be preserved and inspectable.

---

## 4. Comparison Decision Protocol

When comparing a candidate policy $C$ against baseline $B$ on the `SELECT` suite:
- **Leaderboard Score**: $S = \sum_{i=1}^{30} R_i$ (higher is better; closest to $0.0$ wins).
- **Certified Improvement**:
  $$S(C) > S(B) \quad \text{AND} \quad \text{Violations}(C) \le \text{Violations}(B)$$
- If $S(C) > S(B)$ but $C$ causes catastrophic comfort violations ($> 5.0^\circ\text{C}$ drift) in any single scenario, the candidate is flagged **HIGH RISK** and rejected from submission.
