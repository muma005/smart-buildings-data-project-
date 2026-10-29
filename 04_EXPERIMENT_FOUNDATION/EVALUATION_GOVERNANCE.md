# Phase 04 — Evaluation Governance & Comparison Safeguards

**Project:** Smart Buildings Challenge — NeurIPS 2026  
**Document:** EVALUATION_GOVERNANCE.md  
**Status:** OFFICIAL GOVERNANCE CONTRACT & CERTIFIED AUDIT  
**Evaluation Engines:** [`SuiteValidator`](file:///04_EXPERIMENT_FOUNDATION/evaluation/comparison_validator.py#L14-L260), [`ComparisonValidator`](file:///04_EXPERIMENT_FOUNDATION/evaluation/comparison_validator.py#L262-L400), [`ScoreVerifier`](file:///04_EXPERIMENT_FOUNDATION/evaluation/score_verification.py#L14-L240)  

---

## 1. Baseline Audit: E1/E2 Requirement-to-Evidence Matrix

| Requirement | Existing Implementation | Evidence Inspected | Status | Operational Action Taken |
| :--- | :--- | :--- | :--- | :--- |
| **1. Suite Identity & Versioning** | [`suites/official_suite.yaml`](file:///04_EXPERIMENT_FOUNDATION/suites/official_suite.yaml) | Suite manifests, commit pin `95cea5b` | **PASS** | Validated via `SuiteValidator.validate_suite_manifest` schema checks. |
| **2. Scenario Provenance & Membership** | `suites/official_suite.yaml`, `training_scenarios/` | Exact 30-scenario cross-match against disk & `baseline_returns.json` | **PASS** | Catalog validation rejects unknown scenario IDs and detects duplicate scenarios. |
| **3. Prohibited Overlap Detection** | [`SuiteValidator.check_suite_overlap`](file:///04_EXPERIMENT_FOUNDATION/evaluation/comparison_validator.py#L155-L235) | Automated partition tests (`test_evaluation_governance.py`) | **PASS** | Enforces `ALLOWED`, `DISALLOWED`, and `UNKNOWN` overlap policies. |
| **4. Matched Comparison Enforcement** | [`ComparisonValidator.validate_comparison`](file:///04_EXPERIMENT_FOUNDATION/evaluation/comparison_validator.py#L262-L400) | Contract validator (`test_failure_detection.py`) | **PASS** | Validates exact suite, version, evaluator, step count (8,640), and unverified score rejection. |
| **5. Independent Score Reconstruction** | [`ScoreVerifier`](file:///04_EXPERIMENT_FOUNDATION/evaluation/score_verification.py#L14-L240) | Zero-dependency auditor on S0 episode | **PASS** | Reconstructs episode return to $0.00\times 10^0$ error; component arithmetic to $1.08\times 10^{-7}$. |
| **6. Official Score Parity & Aggregation** | `starter_kit_pinned/evaluate.py`, `baseline_returns.json` | 4 competition baselines $\times$ 30 scenarios | **PASS** | Certified equal-weighted sum-of-returns multi-scenario aggregation. |
| **7. Corrupt Artifact Rejection** | [`tests/test_failure_detection.py`](file:///04_EXPERIMENT_FOUNDATION/tests/test_failure_detection.py) | 25 red-team injected defect tests | **PASS** | Rejection verified for all 25 specific defect modes. |
| **8. End-to-End Governance Enforcement** | `core/runner.py`, `core/registry.py`, `core/evaluator.py` | Certified vertical-slice run + pytest suite | **PASS** | Automated workflow prevents incomplete/unverified runs from qualifying as comparisons. |

---

## 2. The Five Evaluation Roles & Operational Consequences

Every scenario in an evaluation suite is assigned an explicit, provenance-tracked role:

| Role | Purpose | Permitted Use | Overlap & Partition Policy | Operational Enforcement |
| :--- | :--- | :--- | :--- | :--- |
| **`DEV`** | Fast iteration, debugging, smoke tests | Rapid prototyping, gradient debugging, sanity checks | **ALLOWED** to overlap with any suite; never cited as leaderboard evidence. | `check_role_eligibility` rejects any attempt to use `DEV` for submission selection. |
| **`SELECT`** | Benchmark candidate comparison | Final policy ranking and submission selection | Pinned to the official 30-scenario reference suite (`suites/official_suite.yaml`). | Authoritative baseline comparison suite; requires all 30 scenarios at 8,640 steps. |
| **`GENERALIZATION`** | Out-of-distribution transfer assessment | Evaluating policy transfer across unseen weather/building pairings | **DISALLOWED** exact scenario overlap with `SELECT`; requires explicit transfer provenance. | Rejects public training building/weather reuse when claiming out-of-distribution transfer. |
| **`STRESS`** | Extreme climate edge cases | Robustness analysis under extreme freeze or heat | Permitted extreme scenarios (`fairbanks_1`, `phoenix_5`) to audit comfort cliffs. | Rejects missing provenance; audits thermal catastrophic drift ($> 5.0^\circ\text{C}$). |
| **`SEALED RELEASE`** | Hidden competition evaluation | Final competition submission ranking | Held exclusively by Kaggle/judges; strictly inaccessible locally. | Software validation strictly **REJECTS** any local suite declaring `SEALED RELEASE` on public training buildings. |

---

## 3. Real Limits of Protection: Software Enforcement vs. Operational Security

> [!WARNING]
> **Boundary of Software Validation**: Software validators alone cannot prevent a developer from inspecting public scenarios or manually overriding local Python code.
> 
> The system enforces the strongest justified controls possible within the local execution environment:
> 1. **Public Training Set Boundary**: We explicitly recognize that all 6 training buildings (`building_train_1` to `8`) and 5 weather presets are public training data. Renaming or repackaging them as "sealed" or "unseen" is automatically rejected with an explicit contamination error.
> 2. **Immutability via Hash Freezing**: Policy snapshots (`policy_snapshot.py`) and configuration manifests are frozen with SHA-256 digests. Any post-run modification invalidates the comparison contract.
> 3. **True Sealed Evaluation Boundary**: Genuine blind evaluation is only achieved via Kaggle's automated hidden test harness. Local experiments are designated `SELECT` benchmarks or `DEV` smoke tests.

---

## 4. The Candidate Comparison Contract (E2)

To compare Policy $A$ (Candidate) against Policy $B$ (Baseline), the comparison must pass the automated **[`ComparisonValidator`](file:///04_EXPERIMENT_FOUNDATION/evaluation/comparison_validator.py)**. A comparison is **REJECTED** if any of the following conditions fail:

1. **Exact Suite Match**: Both policies must be evaluated on the exact same suite name and version (e.g. `official_reference_suite v1.0.0`).
2. **Complete Coverage**: The number of evaluated scenarios must exactly match `expected_scenario_count` (30/30 for official suite). Partial runs cannot be compared.
3. **Complete Episode Length**: Every episode in the suite must complete all required steps ($8,640$ steps). Truncated runs are marked `INVALID`.
4. **Identical Evaluator & Simulator Versions**: Both evaluations must be conducted by the certified `ScoreVerifier` engine under compatible versions.
5. **No Duplicate Scenario Results**: Neither candidate nor baseline may submit duplicate scenario results to manipulate aggregates.
6. **Integrity of Trace Artifacts**: Traces must exist, contain valid headers (`step`, `reward`), and have verified SHA-256 manifest hashes.
7. **Execution Status Invariant**: Runs marked `COMPLETE` that suffered truncation or aborts are automatically rejected.
8. **Independent Score Verification**: Evaluations containing unverified or uncertified scores are rejected from comparison.
9. **Multi-Scenario Sum Consistency**: Total suite return must strictly equal the sum of scenario returns within tolerance ($1.0 \times 10^{-6}$).

---

## 5. Official Metric & Score Reconstruction Proof

### Step Reward Arithmetic
The official per-step agent reward defined in the pinned competition environment is:
$$R_t = w_p \cdot \text{regret}_t - w_e \cdot \text{energy\_cost}_t - w_c \cdot \text{carbon\_emission}_t$$
where default weights are $w_p = 0.6$, $w_e = 0.2$, $w_c = 0.2$, $\text{regret}_t \le 0$ is normalized occupant productivity regret, and energy and carbon are non-negative cost penalties subtracted from the return.
- **Verification Evidence**: Across all 8,640 steps of the S0 episode, the independently reconstructed step rewards match the recorded `agent_reward` to a maximum discrepancy of $1.08 \times 10^{-7}$ (well below $1.0 \times 10^{-6}$).

### Multi-Scenario Aggregation
The official competition leaderboard metric aggregates scenario returns via equal-weighted summation:
$$S = \sum_{s=1}^{30} R_s$$
- **Verification Evidence**: Tested against official `baseline_returns.json` across all 30 scenarios for all four official baseline controllers (`bang_bang`, `fixed_setpoint`, `pid`, `pid_water`), confirming exact numerical parity within $1.0 \times 10^{-6}$.
