# Gate 2 Exit Evidence: Crash-Resilient Incremental Chunk Persistence

## Overview
* **Status:** PASS
* **Date:** 2026-11-01
* **Active Git Commit:** `00c911a270af3bdbc52dc1e16c9d3e6c139cb175`
* **Test Suite:** `05_FAILURE_ENGINEERING/tests/test_gate_02_crash_resilience.py`
* **Results:** 7 passed in 41.75s (100% pass rate).
* **Regression Suite:** 16 passed, 0 failed in 459.28s across Gate 1, `test_runner.py`, and `test_scoring.py`.

---

## 1. Verified Implementation Changes

### A. Incremental Chunk Persistence (`TraceRecorder`)
* **Daily Chunk Sizing:** Transitions are buffered in memory and flushed to disk in discrete diurnal chunks (`chunk_size = 288` steps, matching one diurnal simulation day).
* **High-Dimensional Tensor Capture:** Each chunk (`chunk_0000.npz`, `chunk_0001.npz`, ...) captures:
  * `step_indices`: `(N,)` `int64`
  * `observations`: `(N, D_obs)` `float32`
  * `raw_continuous_actions`: `(N, D_cont)` `float32`
  * `executed_continuous_actions`: `(N, D_cont)` `float32`
  * `discrete_actions`: `(N, D_disc)` `int32`
  * `zone_temperatures`: `(N, N_zones)` `float32`
* **Atomic Publication Protocol:**
  1. Staged write to temporary file: `chunks/chunk_000k.npz.tmp` via `np.savez_compressed`.
  2. Forced disk persistence: `f.flush()` and `os.fsync(f.fileno())` to guarantee physical storage.
  3. Atomic rename: `tmp_path.replace(final_path)` prevents any partial writes from being recognized.
  4. Journaling: computes SHA-256 hash and appends entry to `chunks_manifest.json` with fsync.
* **Fail-Fast Error Containment:** Any disk I/O, serialization, or filesystem exception immediately raises `EvidenceCaptureError`. `SimulationRunner` catches this, halts execution, sets `RunStatus.FAILED`, and records the traceback in the manifest.

### B. Post-Crash Recovery Scanner (`ExperimentRegistry`)
* **`recover_interrupted_run(run_dir)`:**
  * Detects runs in `RUNNING` status interrupted by unhandled process termination, signals, or OOM crashes.
  * Cleans up orphaned `.tmp` files (`chunks/*.tmp`, `chunks_manifest.json.tmp`) to eliminate partial corrupted artifacts.
  * Scans and verifies intact `chunk_*.npz` files, computing SHA-256 hashes and validating zip integrity with `np.load`.
  * Reconciles `chunks_manifest.json` with surviving chunks.
  * Inspects streaming `trace.csv` to calculate the exact data loss boundary.
  * Transitions run status to `RunStatus.INCOMPLETE` (with explicit data loss window metadata).
  * **Strict Guarantee:** An interrupted run is **NEVER** marked as `COMPLETE` or eligible for comparison/promotion.
* **`recover_interrupted_runs(base_dir)`:** Scans an entire runs directory and safely recovers all interrupted sessions in batch.

### C. Multi-Chunk Reassembly & Verification (`TraceRecorder.load_chunks`)
* Concatenates all committed chunks into unified episode tensors.
* Verifies SHA-256 hash of each chunk file against `chunks_manifest.json` prior to decompression, detecting file tampering or corruption.

### D. End-to-End Runner Integration (`SimulationRunner`)
* Captures policy input observation, raw continuous action, executed action, and per-zone temperatures at each simulation step.
* Dynamically supports custom `chunk_size` (defaults to 288).
* Records chunk counts and `chunks_manifest_sha256` in both `summary.json` and `run_manifest.json`.

---

## 2. Test Execution Evidence

```
05_FAILURE_ENGINEERING/tests/test_gate_02_crash_resilience.py::test_durable_chunk_buffering_and_manifest PASSED [ 14%]
05_FAILURE_ENGINEERING/tests/test_gate_02_crash_resilience.py::test_chunk_loading_and_multi_dim_tensor_integrity PASSED [ 28%]
05_FAILURE_ENGINEERING/tests/test_gate_02_crash_resilience.py::test_crash_resilience_preserves_committed_day1_chunk PASSED [ 42%]
05_FAILURE_ENGINEERING/tests/test_gate_02_crash_resilience.py::test_recovery_cleans_orphaned_tmp_files PASSED [ 57%]
05_FAILURE_ENGINEERING/tests/test_gate_02_crash_resilience.py::test_recovered_run_never_marked_complete PASSED [ 71%]
05_FAILURE_ENGINEERING/tests/test_gate_02_crash_resilience.py::test_storage_write_failure_raises_evidence_capture_error PASSED [ 85%]
05_FAILURE_ENGINEERING/tests/test_gate_02_crash_resilience.py::test_end_to_end_simulation_runner_chunking_integration PASSED [100%]
```

---

## 3. Regression Baseline Verification

Executed 16 tests across Gate 1 and Phase 04 foundation suites:
* `05_FAILURE_ENGINEERING/tests/test_gate_01_reward_and_schema.py`: 6 passed.
* `04_EXPERIMENT_FOUNDATION/tests/test_runner.py`: 4 passed.
* `04_EXPERIMENT_FOUNDATION/tests/test_scoring.py`: 6 passed.

**Total:** 16 passed, 0 failed in 459.28s. Zero regressions detected.
