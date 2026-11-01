# Gate 4 Exit Evidence: Artifact Preservation and Reproducibility

## Overview
* **Status:** PASS
* **Date:** 2026-11-01
* **Active Git Commit:** `00c911a270af3bdbc52dc1e16c9d3e6c139cb175`
* **Test Suite:** `05_FAILURE_ENGINEERING/tests/test_gate_04_artifact_preservation.py`
* **Results:** 4 passed in 104.91s (100% pass rate).
* **Regression Suite:** 18 passed, 0 failed in 67.22s across Gate 3, `test_scoring.py`, and `test_runner.py`.

---

## 1. Verified Implementation Changes

### A. Immutable Artifacts Vault (`run_dir/artifacts/`)
Prior to simulation execution, [`SimulationRunner._preserve_artifacts()`](file:///04_EXPERIMENT_FOUNDATION/core/runner.py#L42-L180) creates a dedicated vault preserving all necessary execution assets:
* **Scenario Configuration:** Freezes `config.gin` to `artifacts/config.gin` with SHA-256 calculation.
* **Policy Entrypoint Snapshot:** Inspects policy source via `inspect.getsourcefile(policy_class)` (or `inspect.getsource`) and copies the code to `artifacts/<policy_name>.py`.
* **Local Dependency Snapshotting (`local_deps/`):** Scans `sys.modules` for all active workspace project modules (excluding virtualenv, site-packages, git internals, and prior run logs) and replicates their directory structure inside `artifacts/local_deps/`.
* **Model Weights Snapshotting:** If neural network weights, checkpoints, or model files are specified in `policy_params`, they are automatically staged and checksummed into `artifacts/`.
* **Runtime Package Environment Tracking:** Captures active package versions for `numpy`, `pandas`, `scipy`, `gymnasium`, and `gin-config`.

### B. Artifact Manifest with Separated Commit Provenance (`artifact_manifest.json`)
Writes `run_dir/artifact_manifest.json` with `os.fsync`, logging:
* `project_git_commit`: Root project repository HEAD commit (`00c911a270af3bdbc52dc1e16c9d3e6c139cb175`).
* `starter_kit_commit`: Pinned starter kit HEAD commit (`95cea5b1c57b5291f44baf0283e0a081d53f5b16`).
* **Strict Invariant:** `project_git_commit != starter_kit_commit` is strictly asserted.
* Checksum registry of all preserved files (`role`, `source_path`, `stored_path`, `sha256`).
* Stored in `run_manifest.json` as `hashes.artifact_manifest_sha256` and referenced in `summary.json`.

### C. Policy Replay from Frozen Snapshot ([`policy_adapter.py`](file:///04_EXPERIMENT_FOUNDATION/core/policy_adapter.py))
Implemented [`PolicyAdapter.load_policy_from_artifacts(run_dir)`](file:///04_EXPERIMENT_FOUNDATION/core/policy_adapter.py#L125-L185):
* Parses `artifact_manifest.json` and verifies the SHA-256 of the stored policy file against recorded manifest hashes before execution.
* Prepends `artifacts/local_deps` and `artifacts` to `sys.path`.
* Dynamically imports the frozen module via `importlib.util.spec_from_file_location`.
* Enables historical rollouts to be replayed with bitwise determinism even after project code undergoes subsequent refactoring.

### D. Independent Artifact Vault Audit ([`score_verification.py`](file:///04_EXPERIMENT_FOUNDATION/evaluation/score_verification.py))
Extended `ScoreVerifier.verify_run_integrity` to verify that all files recorded in `artifact_manifest.json` exist on disk, their SHA-256 hashes match, and the two git commits are distinct.

---

## 2. Test Execution Evidence

```
05_FAILURE_ENGINEERING/tests/test_gate_04_artifact_preservation.py::test_gate_04_vault_creation_and_artifact_manifest PASSED [ 25%]
05_FAILURE_ENGINEERING/tests/test_gate_04_artifact_preservation.py::test_gate_04_policy_replay_from_frozen_artifacts PASSED [ 50%]
05_FAILURE_ENGINEERING/tests/test_gate_04_artifact_preservation.py::test_gate_04_tampered_artifact_rejected PASSED [ 75%]
05_FAILURE_ENGINEERING/tests/test_gate_04_artifact_preservation.py::test_gate_04_identical_commits_rejected PASSED [100%]
```

---

## 3. Regression Baseline Verification

Executed 18 tests across Gate 3 and Phase 04 foundation suites:
* `05_FAILURE_ENGINEERING/tests/test_gate_03_independent_verification.py`: 8 passed.
* `04_EXPERIMENT_FOUNDATION/tests/test_scoring.py`: 6 passed.
* `04_EXPERIMENT_FOUNDATION/tests/test_runner.py`: 4 passed.

**Total:** 18 passed, 0 failed in 67.22s. Zero regressions detected.
