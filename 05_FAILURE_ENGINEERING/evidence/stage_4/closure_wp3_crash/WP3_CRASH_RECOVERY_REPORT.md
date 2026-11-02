# Work Package 3 (WP3) - Genuine Crash Recovery Verification Report

## Executive Summary

- **Objective**: Validate the robustness of experiment state persistence and recovery under genuine, abrupt OS process termination (`proc.kill()` / Windows `TerminateProcess`).
- **Points Tested**: 5 distinct synchronization points (P1 to P5).
- **Verdict**: ALL PASSED.
- **Foundation Changes Required**: 0 (Existing foundation passed all points).

## Synchronization Points Results

| Point | Description | Injected Fault | System Response | Verdict |
|---|---|---|---|---|
| **P1** | Mid-chunk write interruption | Subprocess killed while writing chunk_0001.npz.tmp | Status=INCOMPLETE, Validity=INVALID | **PASS** |
| **P2** | Post-rename pre-manifest interruption | Subprocess killed after chunk_0001.npz rename, before chunks_manifest.json update | Status=INCOMPLETE, Validity=INVALID | **PASS** |
| **P3** | Mid-manifest replacement interruption | Subprocess killed while writing chunks_manifest.json.tmp | Status=INCOMPLETE, Validity=INVALID | **PASS** |
| **P4** | Uncommitted memory buffer interruption | Subprocess killed with 62 uncommitted steps in RAM buffer | Status=INCOMPLETE, Validity=INVALID | **PASS** |
| **P5** | Recovery interruption and idempotence | Subprocess killed mid-recovery; parent recovered and verified idempotence and eligibility rejection | Status=INCOMPLETE, Validity=INVALID | **PASS** |

## Key Invariants Verified

1. **Zero Data Loss of Committed Chunks**: All atomically renamed `.npz` chunks survived uncorrupted and were validated with SHA-256.
2. **Orphan .tmp Purging**: Partial `.tmp` chunks and `.json.tmp` manifests are cleanly unlinked by `recover_interrupted_run()`.
3. **Orphan Published Chunk Reconciliation (P2)**: Chunks committed to disk before manifest updates are detected, verified, and reconciled into `chunks_manifest.json` without discarding valid data.
4. **Strict Fail-Closed State Machine**: Interrupted runs strictly transition to `status = INCOMPLETE` and `evidence_validity = INVALID`. They are NEVER marked `COMPLETE`.
5. **Data Loss Window Accountability (P4)**: Memory steps lost during process termination are precisely documented in `metadata.data_loss_window` comparing durable chunk steps with streaming CSV rows.
6. **Recovery Idempotence (P5)**: Re-executing recovery after crash or sequentially produces identical, non-corrupted state.
7. **Downstream Governance Safety**: Recovered runs are irrevocably rejected by `ScoreVerifier` and `ComparisonValidator`.