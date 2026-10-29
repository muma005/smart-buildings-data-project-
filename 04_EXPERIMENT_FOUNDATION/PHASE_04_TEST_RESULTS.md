# Phase 04 — Test Results Ledger: Minimum Trusted Experiment Foundation & Evaluation Governance (E1/E2)

**Project:** Smart Buildings Challenge — NeurIPS 2026  
**Phase:** 04 — Minimum Trusted Experiment Foundation & Evaluation Governance  
**Date:** 2026-10-29  
**Execution Command:** `.venv\Scripts\pytest 04_EXPERIMENT_FOUNDATION/tests -v`  
**Test Suite Status:** **46 PASSED, 0 FAILED, 0 SKIPPED (100% Pass Rate)**  
**Execution Time:** 93.42s (including full EnergyPlus physics rollouts)  

---

## 1. Executive Summary

The Phase 04 E1/E2 test suite certifies that our experimentation system rigorously enforces environment partitioning, matched comparison contracts, independent score reconstruction, and red-team fault detection.

The test suite covers:
1. **Environment Governance & Partitioning (13 tests)**: Automated validation of suite manifests, catalog checking against all 30 official training scenarios, allowed overlap between `DEV` and `SELECT`, and detection of Defect Modes 01 through 09.
2. **Matched Comparisons & Injected Defects (22 tests)**: Automated enforcement of the Candidate Comparison Contract, detection of Defect Modes 10 through 18, independent scoring defect modes 19 through 25, low-level policy adapter shape/finite checks, directory overwrite protection, and registry state machine transitions.
3. **Reproducibility & Fresh-Process Determinism (1 test)**: Proves bitwise simulation and policy determinism ($0.0$ variance in observations, actions, and rewards across independent fresh-process runs).
4. **Core Runner & Adapter Lifecycle (4 tests)**: Proves policy adapter contract enforcement, source SHA-256 hashing, trace recorder monotonicity, registry state machine rules, and end-to-end multi-step simulation execution.
5. **Independent Scoring & Multi-Scenario Parity (6 tests)**: Proves piecewise quadratic shortfall arithmetic, zero-occupancy regret cancellation, floating-point parity ($\le 1.0\times 10^{-6}$) against official 8,640-step episode returns, physical diagnostic calculations, multi-scenario equal-weighted aggregation parity across all 4 competition baselines, and step-reward component arithmetic ($R = 0.6\cdot\text{regret} - 0.2\cdot\text{energy} - 0.2\cdot\text{carbon}$) across all 8,640 steps of the S0 episode.

---

## 2. Comprehensive Test Execution Ledger (46 Tests)

| Test ID | Test Function | Test Module | Result | Injected Defect / Verified Behavior |
| :--- | :--- | :--- | :---: | :--- |
| **GOV-01** | `test_official_suite_manifest_integrity` | `test_evaluation_governance.py` | **PASS** | Validates official suite (30 scenarios, role `SELECT`, 8640 steps, pinned commit `95cea5b`). |
| **GOV-02** | `test_suite_validator_official_suite_passes` | `test_evaluation_governance.py` | **PASS** | `SuiteValidator` validates official suite schema, 6 buildings, 30 scenarios without warnings. |
| **GOV-03** | `test_additional_suites_integrity` | `test_evaluation_governance.py` | **PASS** | Validates `dev_smoke` (role `DEV`, 1 scenario) and `stress_extremes` (role `STRESS`, 2 scenarios). |
| **GOV-04** | `test_allowed_overlap_between_dev_and_select` | `test_evaluation_governance.py` | **PASS** | `SuiteValidator` confirms `DEV` suite overlap with `SELECT` is explicitly `ALLOWED`. |
| **DEF-01** | `test_defect_01_duplicate_scenario_inside_suite` | `test_evaluation_governance.py` | **PASS** | **Defect 1**: Rejects suite manifest containing duplicate scenario IDs. |
| **DEF-02** | `test_defect_02_unknown_scenario_identifier` | `test_evaluation_governance.py` | **PASS** | **Defect 2**: Rejects unknown scenario IDs lacking generator provenance. |
| **DEF-03** | `test_defect_03_missing_required_provenance` | `test_evaluation_governance.py` | **PASS** | **Defect 3**: Rejects suite lacking `commit_pinned` or `generator_provenance`. |
| **DEF-04** | `test_defect_04_undeclared_suite_membership_change` | `test_evaluation_governance.py` | **PASS** | **Defect 4**: Rejects scenario membership change without version increment. |
| **DEF-05** | `test_defect_05_prohibited_exact_scenario_overlap` | `test_evaluation_governance.py` | **PASS** | **Defect 5**: Rejects exact scenario overlap between `SELECT` and `GENERALIZATION`. |
| **DEF-06** | `test_defect_06_prohibited_building_overlap` | `test_evaluation_governance.py` | **PASS** | **Defect 6**: Rejects building overlap in building-transfer generalization evaluation. |
| **DEF-07** | `test_defect_07_prohibited_weather_overlap` | `test_evaluation_governance.py` | **PASS** | **Defect 7**: Rejects climate overlap in weather-transfer generalization evaluation. |
| **DEF-08** | `test_defect_08_incorrect_suite_role_or_use` | `test_evaluation_governance.py` | **PASS** | **Defect 8**: Rejects using non-`SELECT` suites (`DEV`, `STRESS`) for candidate selection. |
| **DEF-09** | `test_defect_09_public_benchmark_falsely_declared_sealed` | `test_evaluation_governance.py` | **PASS** | **Defect 9**: Rejects claiming role `SEALED RELEASE` on public training buildings. |
| **INV-01** | `test_fault_invalid_action_shape` | `test_failure_detection.py` | **PASS** | PolicyAdapter rejects malformed continuous action shape with `ValueError`. |
| **INV-02** | `test_fault_nan_action` | `test_failure_detection.py` | **PASS** | PolicyAdapter rejects non-finite (NaN / Inf) action values. |
| **INV-03** | `test_fault_out_of_range_action_clipping` | `test_failure_detection.py` | **PASS** | PolicyAdapter clips continuous actions to $[-1.0, 1.0]$ bounds. |
| **INV-04** | `test_fault_prevent_run_directory_overwrite` | `test_failure_detection.py` | **PASS** | ExperimentRegistry raises `FileExistsError` on duplicate run directory attempts. |
| **INV-05** | `test_fault_illegal_state_transition` | `test_failure_detection.py` | **PASS** | ExperimentRegistry rejects illegal transitions (e.g. `FAILED` -> `COMPLETE`). |
| **CMP-01** | `test_positive_matched_comparison_passes` | `test_failure_detection.py` | **PASS** | Positive control: valid matched comparison passes with exact score delta (+600.0). |
| **DEF-10** | `test_defect_10_different_suite_versions` | `test_failure_detection.py` | **PASS** | **Defect 10**: Rejects candidate vs baseline evaluated on different suite versions. |
| **DEF-11** | `test_defect_11_missing_scenario_in_complete_evaluation` | `test_failure_detection.py` | **PASS** | **Defect 11**: Rejects evaluation missing even 1 scenario (29/30). |
| **DEF-12** | `test_defect_12_duplicate_scenario_result` | `test_failure_detection.py` | **PASS** | **Defect 12**: Rejects candidate evaluation with duplicate scenario results. |
| **DEF-13** | `test_defect_13_truncated_episode` | `test_failure_detection.py` | **PASS** | **Defect 13**: Rejects evaluation where any scenario episode ran $< 8,640$ steps. |
| **DEF-14** | `test_defect_14_different_simulator_or_evaluator_version` | `test_failure_detection.py` | **PASS** | **Defect 14**: Rejects mismatched simulator (`v1` vs `v2`) or evaluator (`1.0` vs `2.0`). |
| **DEF-15** | `test_defect_15_missing_or_corrupted_trace` | `test_failure_detection.py` | **PASS** | **Defect 15**: Rejects evaluations with missing or corrupted trace files. |
| **DEF-16** | `test_defect_16_manifest_hash_mismatch` | `test_failure_detection.py` | **PASS** | **Defect 16**: Rejects comparison when artifact hash does not match run manifest. |
| **DEF-17** | `test_defect_17_claims_complete_despite_incomplete` | `test_failure_detection.py` | **PASS** | **Defect 17**: Rejects run marked `COMPLETE` that suffered incomplete execution. |
| **DEF-18** | `test_defect_18_unverified_scores_rejected` | `test_failure_detection.py` | **PASS** | **Defect 18**: Rejects comparison if scores were not independently verified. |
| **DEF-19** | `test_defect_19_incorrect_step_reward_arithmetic` | `test_failure_detection.py` | **PASS** | **Defect 19**: Rejects step reward arithmetic where cost signs/weights are corrupted. |
| **DEF-20** | `test_defect_20_incorrect_episode_aggregation` | `test_failure_detection.py` | **PASS** | **Defect 20**: Rejects episode return that differs from sum of step rewards. |
| **DEF-21** | `test_defect_21_incorrect_multi_scenario_aggregation` | `test_failure_detection.py` | **PASS** | **Defect 21**: Rejects total suite return that differs from sum of scenario returns. |
| **DEF-22** | `test_defect_22_nan_or_infinite_reward` | `test_failure_detection.py` | **PASS** | **Defect 22**: Rejects traces containing NaN or Inf rewards. |
| **DEF-23** | `test_defect_23_missing_or_duplicated_step` | `test_failure_detection.py` | **PASS** | **Defect 23**: Rejects non-monotonic, duplicate, or missing step numbers in trace. |
| **DEF-24** | `test_defect_24_corrupted_trace_data` | `test_failure_detection.py` | **PASS** | **Defect 24**: Rejects unparseable CSV lines or missing required column headers. |
| **DEF-25** | `test_defect_25_official_vs_independent_score_mismatch` | `test_failure_detection.py` | **PASS** | **Defect 25**: Rejects runs where official summary differs from independent return $> 10^{-6}$. |
| **REP-01** | `test_reproducibility_identical_traces` | `test_reproducibility.py` | **PASS** | Independent fresh-process simulation runs produce bitwise identical observations, actions, and rewards. |
| **RUN-01** | `test_policy_adapter_contract` | `test_runner.py` | **PASS** | PolicyAdapter computes valid 64-char SHA-256 and returns compliant actions. |
| **RUN-02** | `test_trace_recorder_monotonicity` | `test_runner.py` | **PASS** | TraceRecorder enforces step sequence monotonicity and raises on step discontinuities. |
| **RUN-03** | `test_registry_lifecycle_and_invariants` | `test_runner.py` | **PASS** | ExperimentRegistry assigns unique run IDs and enforces `INITIALIZED` -> `RUNNING` -> `COMPLETE`. |
| **RUN-04** | `test_simulation_runner_short_episode` | `test_runner.py` | **PASS** | SimulationRunner executes policy episode, streams trace, and writes manifest. |
| **SCR-01** | `test_score_verifier_piecewise_shortfall` | `test_scoring.py` | **PASS** | Proves linear shortfall in $[0, 5.0\text{ K}]$ and quadratic escalation beyond $5.0\text{ K}$. |
| **SCR-02** | `test_score_verifier_zero_occupancy_regret` | `test_scoring.py` | **PASS** | Proves productivity regret strictly drops to $0.0$ when total occupancy is zero. |
| **SCR-03** | `test_score_verifier_s0_episode_parity` | `test_scoring.py` | **PASS** | Reconstructed return from full 8,640-step episode matches official summary to $\le 1.0\times 10^{-6}$. |
| **SCR-04** | `test_diagnostics_engine_on_s0_episode` | `test_scoring.py` | **PASS** | DiagnosticsEngine computes thermal degree-hours, compliance %, and actuator switching statistics. |
| **SCR-05** | `test_score_verifier_multi_scenario_aggregation_parity` | `test_scoring.py` | **PASS** | Confirms equal-weighted sum-of-returns parity against `baseline_returns.json` for 4 baselines. |
| **SCR-06** | `test_score_verifier_reward_arithmetic_on_s0_episode` | `test_scoring.py` | **PASS** | Confirms step reward formula ($0.6\cdot\text{regret} - 0.2\cdot\text{energy} - 0.2\cdot\text{carbon}$) on all 8640 steps (diff $\le 1.08\times 10^{-7}$). |

---

## 3. Red-Team Verification Summary

All 25 required red-team defect modes have automated negative tests demonstrating explicit rejection, paired with positive controls proving valid experiments are accepted:

- **Environment Governance (Defects 01–09)**: 9/9 Rejections Proven.
- **Matched Comparisons (Defects 10–18)**: 9/9 Rejections Proven.
- **Independent Scoring (Defects 19–25)**: 7/7 Rejections Proven.
- **Total Defect Modes Verified**: **25 / 25 (100% Coverage)**.
