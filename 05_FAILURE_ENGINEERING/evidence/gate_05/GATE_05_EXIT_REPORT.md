# Gate 5 Exit Evidence: State and Lineage Governance

## Overview
* **Status:** PASS
* **Date:** 2026-11-01
* **Active Git Commit:** `00c911a270af3bdbc52dc1e16c9d3e6c139cb175`
* **Test Suite:** `05_FAILURE_ENGINEERING/tests/test_gate_05_state_and_lineage.py`
* **Results:** 7 passed in 4.09s (100% pass rate).
* **Regression Suite:** 72 passed, 0 failed in 252.93s across Gates 2–5 and Phase 04 Foundation. Zero regressions detected.

---

## 1. Verified Implementation Changes

### A. Decoupled Two-Tier Governance State Machine ([`registry.py`](file:///04_EXPERIMENT_FOUNDATION/core/registry.py#L20-L40))
Decoupled physical execution outcome (`RunStatus`) from scientific evidence validity (`EvidenceValidity`):
* `RunStatus`: `INITIALIZED`, `RUNNING`, `COMPLETE`, `INCOMPLETE`, `FAILED`, `COMPLETE_NOT_ELIGIBLE`.
* `EvidenceValidity`: `UNVERIFIED`, `VALID`, `INVALID`, `QUARANTINED`.
* Implemented `VALID_EVIDENCE_TRANSITIONS` state table:
  * `UNVERIFIED` $\to$ `{VALID, INVALID, QUARANTINED}`
  * `VALID` $\to$ `{QUARANTINED, INVALID}`
  * `QUARANTINED` $\to$ `{VALID, INVALID}`
  * `INVALID` $\to$ $\emptyset$ (terminal state; illegal transitions raise `ValueError`).
* **Decoupled Status Preservation (Acceptance Criteria 10):** Quarantining a completed run sets `evidence_validity = QUARANTINED` while permanently leaving `execution_status = COMPLETE`. The physical fact of completion is never rewritten.

### B. Typed Dependency Graph ([`registry.py`](file:///04_EXPERIMENT_FOUNDATION/core/registry.py#L190-L225))
* Added typed dependencies list to `create_run` and implemented [`ExperimentRegistry.add_dependency()`](file:///04_EXPERIMENT_FOUNDATION/core/registry.py#L190-L225):
  * Typed fields: `type` (e.g. `baseline_comparator`, `policy_artifact`, `environment_config`), `target_id`, `role`, `required`, and optional `metadata`.
  * Idempotent attachment preventing duplicate dependency entries.

### C. Multi-Node Transitive Lineage & Quarantine Propagation ([`registry.py`](file:///04_EXPERIMENT_FOUNDATION/core/registry.py#L280-L365))
* Implemented [`ExperimentRegistry.quarantine_run(run_id, reason, cascade=True)`](file:///04_EXPERIMENT_FOUNDATION/core/registry.py#L280-L345):
  * Discovers all downstream dependents in the experiment DAG via breadth-first traversal.
  * Transitively cascades `evidence_validity = QUARANTINED` to direct and indirect dependents (e.g. Candidate B and Comparison Report D when Baseline A is quarantined; **Acceptance Criteria 11**).
  * Appends structured entries to `quarantine_history` recording `timestamp`, `action: QUARANTINE_APPLIED`, `taint_source`, and `propagated_from`.
  * Strictly preserves isolation of independent runs (e.g. Candidate F evaluated against Baseline Z remains `VALID`; **Acceptance Criteria 12**).
* Implemented [`ExperimentRegistry.lift_quarantine(run_id, reason, cascade=False)`](file:///04_EXPERIMENT_FOUNDATION/core/registry.py#L346-L380):
  * Restores `evidence_validity = VALID` and appends `QUARANTINE_LIFTED` with audit justification to `quarantine_history`.

### D. Governance Comparison Rejection ([`comparison_validator.py`](file:///04_EXPERIMENT_FOUNDATION/evaluation/comparison_validator.py#L455-L485))
* Updated [`ComparisonValidator.validate_comparison()`](file:///04_EXPERIMENT_FOUNDATION/evaluation/comparison_validator.py#L455-L485):
  * Directly verifies `evidence_validity` on candidate and baseline evaluation structures, as well as on disk via `run_dir/run_manifest.json`.
  * Strictly rejects comparisons involving quarantined or invalid runs with informative rejection messages.
  * Guarantees that defective upstream runs cannot corrupt comparison reports or leaderboard rankings.

### E. Evaluator Evidence Governance ([`evaluator.py`](file:///04_EXPERIMENT_FOUNDATION/core/evaluator.py#L50-L75))
* Updated [`RunEvaluator.evaluate_run()`](file:///04_EXPERIMENT_FOUNDATION/core/evaluator.py#L50-L75):
  * Upon completing independent integrity and score audits, updates `evidence_validity` in `run_manifest.json` from `UNVERIFIED` to `VALID` (if integrity checks pass) or `INVALID` (if integrity checks fail).
  * Logs `"evidence_validity"` in `evaluation.json`.

---

## 2. Test Execution Evidence

```
05_FAILURE_ENGINEERING/tests/test_gate_05_state_and_lineage.py::test_decoupled_status_preservation PASSED [ 14%]
05_FAILURE_ENGINEERING/tests/test_gate_05_state_and_lineage.py::test_transitive_lineage_and_containment PASSED [ 28%]
05_FAILURE_ENGINEERING/tests/test_gate_05_state_and_lineage.py::test_comparison_rejection_on_quarantined_and_invalid PASSED [ 42%]
05_FAILURE_ENGINEERING/tests/test_gate_05_state_and_lineage.py::test_comparison_rejection_via_run_manifest PASSED [ 57%]
05_FAILURE_ENGINEERING/tests/test_gate_05_state_and_lineage.py::test_quarantine_lifting PASSED [ 71%]
05_FAILURE_ENGINEERING/tests/test_gate_05_state_and_lineage.py::test_invalid_state_transition_rejection PASSED [ 85%]
05_FAILURE_ENGINEERING/tests/test_gate_05_state_and_lineage.py::test_typed_dependencies_management PASSED [100%]
```

---

## 3. Regression Baseline Verification

Executed 72 tests across Gates 2–5 and Phase 04 foundation suites:
* `05_FAILURE_ENGINEERING/tests/test_gate_05_state_and_lineage.py`: 7 passed.
* `05_FAILURE_ENGINEERING/tests/test_gate_04_artifact_preservation.py`: 4 passed.
* `05_FAILURE_ENGINEERING/tests/test_gate_03_independent_verification.py`: 8 passed.
* `05_FAILURE_ENGINEERING/tests/test_gate_02_crash_resilience.py`: 7 passed.
* `04_EXPERIMENT_FOUNDATION/tests/`: 46 passed.

**Total:** 72 passed, 0 failed in 252.93s. Zero regressions detected.
