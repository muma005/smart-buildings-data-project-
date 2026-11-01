# Phase 05: Implementation Plan & Progress Tracking

## Architecture Reference
* **Design Blueprint:** `PHASE_05_STAGE_2_IMPLEMENTATION_DESIGN.md` (Stage 2B)
* **Gap Analysis:** `PHASE_05_IMPLEMENTATION_GAP_MAP.md`
* **Project Commit Baseline:** `00c911a270af3bdbc52dc1e16c9d3e6c139cb175`
* **Pinned Starter-Kit Commit:** `95cea5b1c57b5291f44baf0283e0a081d53f5b16`
* **Baseline Test Results:** 46 passed, 0 failed, 4 warnings in 185.12s.

## Implementation Gates Tracking

| Gate | Title | Focus Area | Status | Target Files |
| :--- | :--- | :--- | :---: | :--- |
| **Gate 1** | **Reward and Schema Correctness** | Fix `env.get_reward_info_and_response()`, Step 0 parity check, dynamic schemas across buildings, raw vs. executed actions, non-zero component verification. | **COMPLETED (PASS)** | `04_EXPERIMENT_FOUNDATION/core/runner.py`<br>`04_EXPERIMENT_FOUNDATION/core/policy_adapter.py`<br>`04_EXPERIMENT_FOUNDATION/core/trace_recorder.py` |
| **Gate 2** | **Crash-Resilient Persistence** | Incremental 288-step daily chunking, atomic `.tmp` staging, `os.fsync`, atomic publication, recovery of orphan chunks, `chunks_manifest.json`. | **COMPLETED (PASS)** | `04_EXPERIMENT_FOUNDATION/core/trace_recorder.py`<br>`04_EXPERIMENT_FOUNDATION/core/runner.py`<br>`04_EXPERIMENT_FOUNDATION/core/registry.py` |
| **Gate 3** | **Independent Evidence Verification** | Check chunk hashes, step ordering, tensor dimensions, finite values, independent score arithmetic reconstruction. | **COMPLETED (PASS)** | `04_EXPERIMENT_FOUNDATION/evaluation/score_verification.py`<br>`04_EXPERIMENT_FOUNDATION/core/evaluator.py` |
| **Gate 4** | **Artifact Preservation** | `run_dir/artifacts/` vault, local dependency resolution from `sys.modules`, `artifact_manifest.json`, separate git commits. | **COMPLETED (PASS)** | `04_EXPERIMENT_FOUNDATION/core/runner.py`<br>`04_EXPERIMENT_FOUNDATION/core/registry.py`<br>`04_EXPERIMENT_FOUNDATION/core/policy_adapter.py` |
| **Gate 5** | **State and Lineage Governance** | Decouple `RunStatus` (execution) and `EvidenceValidity` (governance), typed DAG lineage, transitive quarantine cascade. | **COMPLETED (PASS)** | `04_EXPERIMENT_FOUNDATION/core/registry.py`<br>`04_EXPERIMENT_FOUNDATION/evaluation/comparison_validator.py`<br>`04_EXPERIMENT_FOUNDATION/core/evaluator.py` |
| **Gate 6** | **Leakage & Semantic Diagnostics** | 4-ring leakage protection (read-only buffers, AST parser), controlled single-variable pulse intervention probe. | **COMPLETED (PASS)** | `04_EXPERIMENT_FOUNDATION/core/policy_adapter.py`<br>`04_EXPERIMENT_FOUNDATION/evaluation/semantic_probe.py` |
| **Gate 7** | **End-to-End Acceptance** | 19 acceptance criteria tests across all failure injection modes (F1–F5). | **COMPLETED (PASS)** | `04_EXPERIMENT_FOUNDATION/evaluation/standalone_audit.py`<br>`05_FAILURE_ENGINEERING/tests/test_gate_07_end_to_end_acceptance.py` |
