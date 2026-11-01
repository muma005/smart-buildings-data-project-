# Phase 05 — Stage 1: Implementation Audit and Gap Map
**Project:** Smart Buildings Challenge — NeurIPS 2026  
**Document:** PHASE_05_IMPLEMENTATION_GAP_MAP.md  
**Audit Date:** 2026-10-31  
**Audit Scope:** Read-only architectural inspection, evidence verification, and capability gap analysis for Phase 05 (Red Team and Failure Engineering).  
**Baseline Git Commit:** `00c911a270af3bdbc52dc1e16c9d3e6c139cb175` (`00c911a`)  

---

## 1. Executive Summary

This document presents a comprehensive, read-only implementation audit of the Smart Buildings Challenge experimentation foundation. The mission of Phase 05 is to establish an **Experiment Black Box & Evidence System** and an active **Red Team & Failure Engineering Authority** capable of detecting planted faults, isolating root causes, tracing affected lineages, quarantining invalid conclusions, and verifying repairs.

### Current State of Phase 05 Readiness
The project enters Phase 05 with a certified **Phase 04 foundation** (46 passing tests, 0 failures, 0 skips). The core architecture provides solid foundations in cryptographic state-machine management, independent mathematical reward verification, and suite-level governance. However, the system currently lacks true **black-box observability**, **semantic interface diagnostics**, **automated comparison orchestration**, and **lineage-based quarantine**.

### Strongest Existing Capabilities (VERIFIED)
1. **Mathematical Scoring Parity & Independence:** [`ScoreVerifier`](file:///04_EXPERIMENT_FOUNDATION/evaluation/score_verification.py#L14) independently reconstructs per-step rewards from raw physical components ($R_t = 0.6\cdot\text{regret}_t - 0.2\cdot\text{energy\_cost}_t - 0.2\cdot\text{carbon\_emission}_t$) with maximum discrepancy $1.08 \times 10^{-7}$ ($\le 1.0 \times 10^{-6}$ tolerance), and matches official 8,640-step episode returns to bitwise precision ($0.00 \times 10^0$).
2. **Comparison Contract Enforcement:** [`ComparisonValidator`](file:///04_EXPERIMENT_FOUNDATION/evaluation/comparison_validator.py#L337) strictly rejects comparisons with suite mismatches, version discrepancies, missing scenarios (e.g. 29/30), truncated episodes ($< 8,640$ steps), unverified scores, duplicate scenario results, or artifact SHA-256 hash mismatches.
3. **Environment Governance & Partition Classification:** [`SuiteValidator`](file:///04_EXPERIMENT_FOUNDATION/evaluation/comparison_validator.py#L13) programmatically validates suite schemas, checks scenario IDs against the 30-scenario official catalog, enforces `ALLOWED` overlap (`DEV` vs `SELECT`), and rejects `DISALLOWED` overlaps or public training sets falsely declared `SEALED RELEASE`.
4. **State-Machine Lifecycle & Overwrite Protection:** [`ExperimentRegistry`](file:///04_EXPERIMENT_FOUNDATION/core/registry.py#L37) assigns unique timestamped UUID run IDs, strictly blocks directory overwrites via `FileExistsError`, and enforces monotonic transitions across 7 explicit states (`INITIALIZED`, `RUNNING`, `COMPLETE`, `FAILED`, `INCOMPLETE`, `INVALID`, `COMPLETE_NOT_ELIGIBLE`).
5. **Fresh-Process Determinism:** Independent fresh-process simulations produce identical observations, actions, and rewards ($0.0$ variance).

### Most Critical Gaps Identified (To Resolve in Phase 05)
1. **Information Loss in Transition Traces (Black Box Gap):** [`TraceRecorder`](file:///04_EXPERIMENT_FOUNDATION/core/trace_recorder.py#L58-L69) discards raw multi-dimensional continuous and discrete action vectors, storing only scalar summaries (`discrete_action_sum`, `continuous_action_mean`). Furthermore, observation vectors are discarded entirely (storing only `mean_zone_temp`). An episode cannot be reconstructed bit-for-bit from `trace.csv` alone.
2. **Silent Zero-Default in SimulationRunner Reward Breakdown:** In [`SimulationRunner.execute_episode`](file:///04_EXPERIMENT_FOUNDATION/core/runner.py#L117-L119), reward components are extracted via `getattr(env, "_productivity_regret", 0.0)`. The environment has no such attributes; reward breakdown is only available via `env.get_reward_info_and_response()`. Consequently, runs executed by `SimulationRunner` log `0.0` for all component penalties in `trace.csv`.
3. **Policy Source Snapshot Omission in Routine Execution:** While the reference vertical slice ([`run_vertical_slice.py`](file:///04_EXPERIMENT_FOUNDATION/core/run_vertical_slice.py#L79)) explicitly wrote `policy_snapshot.py`, [`SimulationRunner.execute_episode`](file:///04_EXPERIMENT_FOUNDATION/core/runner.py#L55) only records the SHA-256 hash in `run_manifest.json` and does not save the actual source code snapshot into `run_dir`.
4. **Blindness to Semantic Mapping Errors (Red Team F1 Gap):** [`PolicyAdapter`](file:///04_EXPERIMENT_FOUNDATION/core/policy_adapter.py#L81-L98) checks array shapes and $[-1.0, 1.0]$ bounds, but possesses zero semantic probes or actuator sensitivity assertions. Swapping two zone setpoints or permuting observation features passes through all existing validation undetected.
5. **Absence of an Automated End-to-End Campaign Orchestrator:** [`ComparisonValidator.validate_comparison`](file:///04_EXPERIMENT_FOUNDATION/evaluation/comparison_validator.py#L343) is currently tested exclusively with synthetic dictionaries in unit tests. No automated harness exists to inspect 30 run directories from `ExperimentRegistry`, verify their individual traces, aggregate them into a candidate evaluation manifest, and evaluate them against baseline benchmarks.
6. **Absence of Dependency Lineage & Quarantine Invalidation:** Manifests do not track parent-child experiment lineage, training checkpoints, or downstream comparison IDs. If an upstream baseline or reward component is discovered to be defective, the system cannot automatically locate all dependent runs or cascade an `INVALID` quarantine status.

---

## 2. Verified Starting State

### 2.1 Repository Metadata
- **Repository Root:** `C:/Users/ADMIN/Desktop/smart building`
- **Current Branch:** `main`
- **Active Git Commit:** `00c911a270af3bdbc52dc1e16c9d3e6c139cb175`
- **Commit Subject:** `feat(phase-04): certify E1/E2 evaluation governance with 25 red-team defect modes and 46 passing tests`
- **Working Tree Status:** Clean (`nothing to commit, working tree clean`).
- **Remote Synchronization:** Up to date with `origin/main`.
- **Pinned Official Starter Kit:** Commit `95cea5b1c57b5291f44baf0283e0a081d53f5b16` located at `starter_kit_pinned/`.

### 2.2 Directory Layout
```
C:/Users/ADMIN/Desktop/smart building/
├── .git/
├── .venv/                              (Python 3.12.13 virtual environment)
├── 02_DATA_UNDERSTANDING/              (Phase 02 EDA and data exploration)
├── 03_SOURCE_TRUTH/                    (Phase 03 simulator verification & S0 episode evidence)
├── 04_EXPERIMENT_FOUNDATION/           (Phase 04 experimentation & governance foundation)
│   ├── core/                           (runner, adapter, recorder, registry, evaluator)
│   ├── evaluation/                     (score verification, diagnostics, comparison validator)
│   ├── experiments/                    (experiment definitions & run evidence directories)
│   ├── suites/                         (official_suite.yaml, dev_smoke.yaml, stress_extremes.yaml)
│   └── tests/                          (46 automated pytest regression and red-team tests)
├── kaggle_evaluation/                  (Kaggle competition gateway code)
├── smart_buildings/                    (Local package containing environments and baselines)
├── starter_kit_pinned/                 (Authoritative pinned competition starter kit)
├── README.md
└── Smart_Buildings_Updated_Project_Roadmap.md
```

### 2.3 Test Suite Reproduction
Executed safe, non-destructive test execution:
- **Command:** `.venv\Scripts\pytest 04_EXPERIMENT_FOUNDATION/tests -v`
- **Exit Code:** `0`
- **Summary:** **46 PASSED, 0 FAILED, 0 SKIPPED, 4 WARNINGS** in 166.92s
- **Warnings:** 4 `Pandas4Warning` instances regarding deprecated `pd.Timestamp.utcnow()` inside pinned `environment.py` (external dependency).
- **Result Verification:** Exactly matches the Phase 04 certification claims.

---

## 3. Comprehensive Component Audit

| Component | File / Location | Actual Implemented Behavior | What It Does NOT Establish | Status |
| :--- | :--- | :--- | :--- | :---: |
| **Experiment Registry** | [`core/registry.py`](file:///04_EXPERIMENT_FOUNDATION/core/registry.py#L37) | Generates unique run IDs; creates isolated directories; writes `run_manifest.json`; enforces monotonic state transitions across 7 states; prevents directory overwrites. | Does not track experiment parent-child lineage, policy training checkpoints, or downstream comparison IDs. Cannot cascade invalidation. | **PARTIAL** |
| **Simulation Runner** | [`core/runner.py`](file:///04_EXPERIMENT_FOUNDATION/core/runner.py#L24) | Executes policy-in-the-loop Gymnasium rollouts; streams trace; saves `summary.json`; transitions status to `COMPLETE`, `INCOMPLETE`, or `FAILED`. | Uses `getattr` fallback for reward components, yielding `0.0`. Discards full observation and action arrays. Does not copy `policy_snapshot.py` to run folder. | **PARTIAL** |
| **Policy Adapter** | [`core/policy_adapter.py`](file:///04_EXPERIMENT_FOUNDATION/core/policy_adapter.py#L14) | Computes source SHA-256 hash; instantiates policy with positional/keyword fallback; enforces discrete/continuous shapes; clips continuous actions to $[-1.0, 1.0]$. | Does not validate observation schema. Discards unclipped raw action. Does not measure latency. Cannot detect semantic mapping/swapping errors. | **PARTIAL** |
| **Trace Recorder** | [`core/trace_recorder.py`](file:///04_EXPERIMENT_FOUNDATION/core/trace_recorder.py#L15) | Streams step transitions to CSV; enforces step index monotonicity ($0, 1, 2\dots$); flushes on each step; computes file SHA-256 on close. | Discards raw observation vectors and full action vectors (only records action sum/mean). Discards termination/truncation booleans. | **PARTIAL** |
| **Run Evaluator** | [`core/evaluator.py`](file:///04_EXPERIMENT_FOUNDATION/core/evaluator.py#L19) | Coordinates `ScoreVerifier` and `DiagnosticsEngine` on a single run directory; outputs `evaluation.json`. | Only operates on a single scenario run. Has no logic to audit or aggregate multi-scenario campaign suites. | **PARTIAL** |
| **Score Verifier** | [`evaluation/score_verification.py`](file:///04_EXPERIMENT_FOUNDATION/evaluation/score_verification.py#L14) | Zero-dependency independent mathematical auditor; verifies piecewise comfort shortfall, zero-occupancy cancellation, step arithmetic, episode sums, and multi-scenario parity. | When traces lack component breakdowns (as produced by `runner.py`), step arithmetic verification cannot execute. Requires `reward_components.csv`. | **VERIFIED** |
| **Diagnostics Engine** | [`evaluation/diagnostics.py`](file:///04_EXPERIMENT_FOUNDATION/evaluation/diagnostics.py#L13) | Computes occupied degree-hours, comfort compliance %, min/max/mean zone temps, discrete actuator switching frequency. | Requires multi-zone temperatures; if trace only has scalar `mean_zone_temp`, zone-specific comfort degradation is obscured. | **VERIFIED** |
| **Suite Validator** | [`evaluation/comparison_validator.py`](file:///04_EXPERIMENT_FOUNDATION/evaluation/comparison_validator.py#L13) | Enforces suite schemas, checks 30 official scenarios, verifies provenance, enforces `ALLOWED` (`DEV` vs `SELECT`) and `DISALLOWED` overlaps, blocks fake sealed sets. | Validates static YAML files; does not inspect running code for runtime data leakage during rollouts. | **VERIFIED** |
| **Comparison Validator** | [`evaluation/comparison_validator.py`](file:///04_EXPERIMENT_FOUNDATION/evaluation/comparison_validator.py#L337) | Enforces Candidate Comparison Contract: checks suite match, version match, 30 scenarios, 8640 steps, unverified score rejection, trace hashes. | Only invoked in unit tests with mock dictionaries. Not connected to a batch CLI or automated multi-run comparison workflow. | **PARTIAL** |
| **Suite Manifests** | [`suites/`](file:///04_EXPERIMENT_FOUNDATION/suites/) | Authoritative YAML manifests for `official_suite` (30 scenarios, `SELECT`), `dev_smoke` (`DEV`), and `stress_extremes` (`STRESS`). | Manifests exist, but no automated test checks whether newly created custom suites meet schema rules unless manually tested. | **VERIFIED** |

---

## 4. Experiment Black Box Coverage Map

The Experiment Black Box must preserve replay-grade evidence across all 10 critical experiment boundaries:

| System Boundary | Required Evidence | Existing Implementation | Capture Mode | Critical Gap |
| :--- | :--- | :--- | :--- | :--- |
| **1. Experiment Creation** | Hypothesis, target metric, comparator baseline, formal success criteria. | [`exp_000_vertical_slice.yaml`](file:///04_EXPERIMENT_FOUNDATION/experiments/experiment_definitions/exp_000_vertical_slice.yaml) contains `hypothesis`, `policy`, `suite_id`. | Manual YAML definition | Lacks formal machine-readable success criteria schema and hypothesis registry. |
| **2. Environment Setup** | Scenario ID, config hash, simulator git commit, python environment dependencies, seed. | `scenario_id` and `config_sha256` recorded in `run_manifest.json`. | Automatic in `runner.py` | Simulator git commit, random seed, and dependency hashes (`uv.lock`/`environment.yml`) are not saved in manifest. |
| **3. Policy Input** | Full observation vector, observation feature schema, normalized/unnormalized state. | Passed to policy in `runner.py`; scalar `mean_zone_temp` stored in trace. | Partially captured | **Full observation vector is discarded.** Observation schema is never validated. |
| **4. Policy Decision** | Policy identity, source code snapshot, raw unclipped continuous/discrete output, latency. | `policy_name` and `policy_sha256` in manifest. `policy_snapshot.py` only in `run_vertical_slice.py`. | Partially captured | **Raw unclipped action is discarded.** Policy latency is not timed. `policy_snapshot.py` missing in `runner.py`. |
| **5. Action Execution** | Executed action vector, clipped setpoints, actuator indices. | Scalar summaries (`discrete_action_sum`, `continuous_action_mean`) in trace. | Summarized only | **Full action arrays are discarded.** Cannot inspect individual zone damper or reheat commands. |
| **6. Simulator Transition** | Next observation, reward, raw physical components (kW, kg CO2, K deviations), termination flags. | `reward` recorded in `trace.csv`. `env.step()` outputs processed. | Partially captured | `runner.py` failed to extract reward components via `get_reward_info_and_response()`, writing `0.0`. Next observation discarded. |
| **7. Evaluation** | Reconstructed return, parity error, comfort compliance, degree-hours, actuator switching. | `evaluation.json` generated by `RunEvaluator` with `ScoreVerifier` and `DiagnosticsEngine`. | Automatic in `evaluator.py` | Complete for single runs; multi-scenario suite evaluation is not automated. |
| **8. Comparison** | Matched suite identity, 30 scenario returns, step counts, score delta, rejection reasons. | `ComparisonValidator.validate_comparison` enforces all contract criteria. | Synthetic unit tests only | **No automated campaign harness.** Comparison validator is not wired to real run manifests. |
| **9. Interpretation** | Hypothesis verdict (supported/refuted), physical comfort risks, operational recommendations. | Basic metrics in `summary.json` and `evaluation.json`. | Partially captured | No structured conclusion artifact or risk assessment file linked to run lineage. |
| **10. Promotion / Release** | Release bundle, policy artifact, dependencies, validation certificate, target scenario list. | `RunStatus.COMPLETE_NOT_ELIGIBLE` and `SuiteValidator.check_role_eligibility`. | Manual policy | No release packaging engine, dependency lock verifier, or containerized submission check. |

---

## 5. Audit of the Five Initial Red Team Attacks

| Attack ID & Name | Existing Safeguard & Code Location | Connected to Real Workflow? | Existing Test Coverage | What It Can Detect | What It Can Miss | Missing Capability for Phase 05 |
| :--- | :--- | :---: | :---: | :--- | :--- | :--- |
| **F1. Observation or Actuator Mapping Error** | Shape and finite validation in [`PolicyAdapter.get_action`](file:///04_EXPERIMENT_FOUNDATION/core/policy_adapter.py#L81-L98). | **YES** (runs every step) | `test_fault_invalid_action_shape`, `test_fault_nan_action`. | Wrong dimensions, NaNs, infinities, out-of-range floats. | **Semantic mapping errors!** Swapping zone 1 with zone 2, or flipping temperature and occupancy features. | Semantic interface contracts, actuator perturbation response probes, metadata index verification. |
| **F2. Incorrect Reward Calculation** | Independent reconstruction in [`ScoreVerifier`](file:///04_EXPERIMENT_FOUNDATION/evaluation/score_verification.py#L55-L120). | **PARTIAL** (in tests and S0 evaluation) | `test_defect_19_incorrect_step_reward_arithmetic`, `test_defect_25_official_vs_independent_score_mismatch`. | Flipped cost signs, wrong component weights, aggregation errors, arithmetic deviations $> 10^{-6}$. | If traces lack component columns (as in current `runner.py`), arithmetic check cannot run. Upstream simulator scale shifts. | Automated component logging in `runner.py`; automated cascade invalidation of downstream runs. |
| **F3. Forbidden Information or Leakage** | Suite partition checking in [`SuiteValidator.check_suite_overlap`](file:///04_EXPERIMENT_FOUNDATION/evaluation/comparison_validator.py#L172). | **PARTIAL** (manifest audit only) | `test_defect_05_prohibited_exact_scenario_overlap`, `test_defect_09_public_benchmark_falsely_declared_sealed`. | Dataset-level overlap between `SELECT` and `GENERALIZATION`; public sets declared sealed. | **Runtime state leakage!** A policy inspecting `env.building`, querying future weather from disk, or using privileged simulator attributes. | Policy execution sandboxing, observation-only interface enforcement, prohibition of simulator inspection. |
| **F4. Incomplete Rollout Reported as Complete** | Step count check in `runner.py`, `ScoreVerifier`, and `ComparisonValidator`. | **YES** (enforced across 3 layers) | `test_fault_08_step_count_mismatch`, `test_defect_13_truncated_episode`, `test_defect_17_claims_complete_despite_incomplete`. | Truncated episodes ($< 8,640$ steps), status mismatches, trace step count deviations. | Runs padded with zero-action / zero-reward dummy rows after a simulator freeze or crash. | Trajectory transition activity checks; non-zero physical state dynamics verification. |
| **F5. Missing Deployment Artifact** | Manifest hash checking in `registry.py` and `ComparisonValidator`. | **PARTIAL** (checks trace/summary hashes) | `test_defect_15_missing_or_corrupted_trace`, `test_defect_16_manifest_hash_mismatch`. | Missing `trace.csv`, modified trace content post-run. | Missing dependencies, missing model weights, missing inference entrypoint in deployment package. | Packaging verifier; isolated container dry-run verification for deployment release bundles. |

---

## 6. Failure Engineering Readiness Audit

```
┌────────────────────────────────────────────────────────────────────────┐
│                     FAILURE ENGINEERING LIFECYCLE                      │
│                                                                        │
│   1. DETECT ──> 2. PRESERVE ──> 3. LOCATE DEVIATION                    │
│      [PARTIAL]     [PARTIAL]         [MISSING]                         │
│                                          │                             │
│                                          ▼                             │
│   6. RE-EVALUATE <── 5. REPAIR & VERIFY <── 4. ISOLATE LINEAGE         │
│      [MISSING]           [PARTIAL]              [MISSING]              │
└────────────────────────────────────────────────────────────────────────┘
```

1. **Detect (PARTIAL):** 
   - *Strengths:* Invariant detection works well for non-monotonic steps, non-finite values, step count mismatches, and suite manifest violations.
   - *Gaps:* Cannot detect physical trajectory anomalies, actuator deadbands, or semantic observation corruptions.
2. **Reproduce and Preserve (PARTIAL):**
   - *Strengths:* Frozen `policy_snapshot.py` in certified runs allows bitwise deterministic replay.
   - *Gaps:* `SimulationRunner` does not automatically freeze `policy_snapshot.py` during normal execution; random seeds and dependency versions are not logged in `run_manifest.json`.
3. **Locate Earliest Verified Deviation (MISSING):**
   - *Strengths:* `ScoreVerifier` reports the first step index of non-monotonic or non-finite records.
   - *Gaps:* No tooling exists to compare two simulation traces and identify the exact time step where candidate and baseline trajectories first diverged (e.g. damper stuck at step 142).
4. **Isolate Cause and Affected Lineage (MISSING):**
   - *Strengths:* `RunStatus` tracks run-level status.
   - *Gaps:* No lineage graph. If an upstream baseline is found to have had an incorrect configuration, there is no mechanism to query which candidate comparisons depended on that baseline.
5. **Repair and Independently Verify (PARTIAL):**
   - *Strengths:* Pytest framework provides an effective harness for regression tests.
   - *Gaps:* No formal quarantine status transition for families of experiments; repairing a bug requires manual test authoring without a standardized failure reproduction template.
6. **Re-evaluate Affected Conclusions (MISSING):**
   - *Strengths:* None.
   - *Gaps:* No automated re-evaluation runner that consumes an updated component, finds quarantined runs, re-executes or re-scores them, and issues an updated comparison verdict.

---

## 7. Critical Gaps and Prioritized Risks

### Priority 1: Critical (Must Resolve Before High-Volume Experiments)
1. **Trace Information Density & Observability:**
   - *Risk:* Current `trace.csv` stores only scalar aggregates of actions and zone temperatures, and drops observations entirely. If an experiment exhibits unexpected behavior or fails, the black box lacks sufficient evidence to diagnose why.
   - *Required Fix:* Enhance `TraceRecorder` to record full discrete action vectors, full continuous action vectors, full multi-zone temperatures, and reward components. Provide an optional structured observation log.
2. **Reward Component Extraction in SimulationRunner:**
   - *Risk:* In `runner.py`, `getattr(env, "_productivity_regret", 0.0)` silently writes `0.0` for all component penalties, corrupting diagnostic integrals and preventing independent reward arithmetic audits.
   - *Required Fix:* Update `runner.py` to call `env.get_reward_info_and_response()` and log true components.
3. **Policy Source Snapshotting in Runner:**
   - *Risk:* Normal runs do not save `policy_snapshot.py` in `run_dir`, breaking fresh-process reproducibility if the policy file is edited later.
   - *Required Fix:* Ensure `SimulationRunner` copies the policy source file directly into `run_dir/policy_snapshot.py` on initialization.

### Priority 2: High (Required for Trustworthy Red Team & Governance)
4. **Semantic Interface Probes (Red Team F1):**
   - *Risk:* Swapped actuator indices or permuted observation features pass through existing validators without error.
   - *Required Fix:* Implement semantic invariant checks and a diagnostic perturbation probe in `PolicyAdapter` that verifies actuator mapping against building metadata.
5. **Automated Multi-Scenario Comparison Campaign Orchestrator:**
   - *Risk:* Comparison validation is only tested on synthetic mocks; developers must manually assemble comparison dictionaries.
   - *Required Fix:* Implement a `CampaignEvaluator` that scans 30 scenario run directories for a policy, executes `RunEvaluator` on each, aggregates the official competition metric, and executes `ComparisonValidator.validate_comparison` against baseline runs.

### Priority 3: Medium (Process Boundaries and Operational Safeguards)
6. **Lineage Tracking and Quarantine Mechanism:**
   - *Risk:* Upstream errors cannot be traced to dependent comparisons; quarantined runs cannot be programmatically flagged.
   - *Required Fix:* Add `parent_run_id`, `baseline_run_id`, and `git_commit` fields to `run_manifest.json`, and implement an invalidation cascade helper in `ExperimentRegistry`.
7. **Runtime Policy Sandboxing (Red Team F3):**
   - *Risk:* Policies can theoretically inspect simulator internals or access disk.
   - *Process Boundary:* Local Python code cannot be completely sandboxed without severe container overhead. We must explicitly document this boundary and implement AST static analysis to reject policies importing simulator internals.

---

## 8. Minimum Implementation Sequence for Phase 05

The following 4-step sequence addresses all critical gaps without rebuilding existing working modules:

```
┌────────────────────────────────────────────────────────────────────────┐
│                     PHASE 05 IMPLEMENTATION PLAN                       │
│                                                                        │
│   Stage 2: Trace & Runner Enhancement (Black Box Upgrade)              │
│     ├── Fix reward component extraction (get_reward_info_and_response) │
│     ├── Save full action arrays & multi-zone temps in TraceRecorder    │
│     └── Automatically freeze policy_snapshot.py in SimulationRunner    │
│                                           │                            │
│                                           ▼                            │
│   Stage 3: Semantic Interface & Red Team Probes (F1 - F5 Coverage)     │
│     ├── Add semantic actuator mapping assertions to PolicyAdapter (F1) │
│     ├── Implement AST policy static checker for leakage (F3)           │
│     └── Add trace activity invariant check for frozen rollouts (F4)    │
│                                           │                            │
│                                           ▼                            │
│   Stage 4: Automated Campaign Orchestrator & Lineage Tracking          │
│     ├── Build CampaignRunner to execute/evaluate full 30-scenario sets │
│     ├── Connect real run manifests to ComparisonValidator              │
│     └── Add parent-child lineage & quarantine cascade to Registry      │
│                                           │                            │
│                                           ▼                            │
│   Stage 5: Red-Team Fault Injection Certification & Exit Report        │
│     └── Execute isolated F1-F5 attack suites & certify F1/R1 gate      │
└────────────────────────────────────────────────────────────────────────┘
```

1. **Stage 2: Black Box Trace & Runner Upgrade:**
   - *Action:* Modify [`core/runner.py`](file:///04_EXPERIMENT_FOUNDATION/core/runner.py) to extract reward components via `env.get_reward_info_and_response()` and copy `policy_snapshot.py` to `run_dir`.
   - *Action:* Update [`core/trace_recorder.py`](file:///04_EXPERIMENT_FOUNDATION/core/trace_recorder.py) to serialize full discrete and continuous action arrays and all zone temperatures.
   - *Verification:* Execute a 5-step run and verify all components, actions, and snapshot exist in the run directory.
2. **Stage 3: Semantic Interface & Red-Team Fault Detection (F1–F5):**
   - *Action:* Extend [`core/policy_adapter.py`](file:///04_EXPERIMENT_FOUNDATION/core/policy_adapter.py) with semantic index mapping validation (F1) and AST import inspection to prevent simulator attribute leakage (F3).
   - *Verification:* Add negative tests injecting swapped actuator mappings and illegal imports; verify immediate rejection.
3. **Stage 4: Automated Campaign Orchestration & Lineage Management:**
   - *Action:* Implement `CampaignEvaluator` in `04_EXPERIMENT_FOUNDATION/core/` to automate 30-scenario batch evaluations and comparison generation.
   - *Action:* Add lineage tracking (`parent_run_id`, `lineage_tags`) and a `quarantine_run()` method to `ExperimentRegistry`.
   - *Verification:* Run a mock 30-scenario comparison and trigger a quarantine cascade.
4. **Stage 5: Red Team & Failure Engineering Certification:**
   - *Action:* Execute all five fault injections (F1–F5) in isolated test environments, verify evidence preservation and quarantine, and document results in `PHASE_05_TEST_RESULTS.md`.

---

## 9. What Should NOT Be Rebuilt

To maintain architectural stability and avoid scope creep, the following components must be **preserved without architectural redesign**:
1. **`core/registry.py` State Machine:** The 7-state lifecycle, UUID naming convention, and directory overwrite protection are sound and certified. Only incremental lineage metadata fields should be added.
2. **`evaluation/score_verification.py`:** The independent scoring engine and mathematical formulas ($R_t = 0.6\cdot\text{regret} - 0.2\cdot\text{energy} - 0.2\cdot\text{carbon}$) are certified to $1.08 \times 10^{-7}$ precision. Do not alter this verified calculation.
3. **`evaluation/diagnostics.py`:** The degree-hour integrals, comfort compliance calculations, and actuator switching frequencies are verified and physically consistent.
4. **`evaluation/comparison_validator.py` (`SuiteValidator` & `ComparisonValidator`):** The comparison contract and suite partition rules work flawlessly. They only need to be connected to the batch campaign orchestrator.
5. **Existing 46 Regression Tests:** All existing tests in `04_EXPERIMENT_FOUNDATION/tests/` must remain untouched and passing.

---

## 10. Recommended Next Stage

### Recommendation: Proceed to Phase 05 — Stage 2 (Black Box Trace & Runner Upgrade)
The current audit establishes that the Phase 04 foundation is solid, but before launching Red Team attacks (F1–F5) or running baseline campaigns, we must upgrade the **Black Box & Evidence System** (fixing component extraction in `runner.py`, capturing full action/temperature vectors in `trace.csv`, and freezing `policy_snapshot.py`).

Once Stage 2 is complete, the Black Box will capture replay-grade evidence at every boundary, providing the necessary foundation for the Red Team fault injections in Stage 3.
