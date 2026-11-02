# Phase 05 Stage 5 — Work Package 1: Forensic Investigation & Diagnosis Report

## Executive Summary
* **Work Package:** WP1 — Failure Reconstruction and Diagnosis
* **Status:** COMPLETED & VERIFIED (PASS)
* **Targets Investigated:**
  - `INV-01`: Multi-Building Actuator Channel Permutation Isolation
  - `INV-02`: Process Crash Recovery & Data-Loss Window Quantification
* **Investigation Records:**
  - [`inv_01_record.json`](file:///C:/Users/ADMIN/Desktop/smart building/05_FAILURE_ENGINEERING/evidence/stage_5/investigations/inv_01_record.json)
  - [`inv_02_record.json`](file:///C:/Users/ADMIN/Desktop/smart building/05_FAILURE_ENGINEERING/evidence/stage_5/investigations/inv_02_record.json)

---

## 1. INV-01: Actuator Channel Permutation Isolation Results

* **Diagnostic Capability Added:** `SemanticActuatorProbe.diagnose_channel_misalignment()`
* **Validation across Facilities:**
  1. **`building_train_1` (Small facility, 3 zones):**
     - Target zone `VAV_1` commanded; observed thermal delta: `+0.050 K` (< 0.200 K).
     - Culprit zone `VAV_2` uncommanded; observed thermal delta: `+0.900 K`.
     - *Diagnosed Root Cause:* `CHANNEL_INDEX_PERMUTATION` (Confidence: HIGH).
     - *Isolated Permutation:* `{"commanded_target_zone": "VAV_1", "actuated_culprit_zone": "VAV_2"}`.
  2. **`building_train_2` (Large commercial facility, 85 zones):**
     - Target zone `VAV_1` commanded; observed thermal delta: `+0.030 K` (< 0.200 K).
     - Culprit zone `VAV_10` uncommanded; observed thermal delta: `+1.200 K`.
     - *Diagnosed Root Cause:* `CHANNEL_INDEX_PERMUTATION` (Confidence: HIGH).
     - *Isolated Permutation:* `{"commanded_target_zone": "VAV_1", "actuated_culprit_zone": "VAV_10"}`.
  3. **Nominal Clean Controls:**
     - Thermal rise `+0.549 K` cleanly diagnosed as `NOMINAL` with zero false-positive swap alarms.

---

## 2. INV-02: Crash Timeline Reconstruction & Data-Loss Quantification

* **Diagnostic Capability Added:** `ForensicInvestigator.reconstruct_crash_timeline()`
* **Validation across WP3 Genuine Process Kill Points:**
  - **P1 (Mid-chunk write):** Detected orphan `.tmp` chunk; verified durable chunk 0 retained; earliest verified deviation isolated at step 288.
  - **P4 (Uncommitted RAM buffer):**
    - Streaming CSV recorded 350 steps.
    - Durable chunks committed 288 steps.
    - *Data-loss window quantified:* Exactly steps `[288, 350)` (62 steps discarded from volatile memory).
    - *Evaluation leakage check:* `evaluation_leakage_prevented = True` (marked `INVALID`/`INCOMPLETE`; zero uncommitted steps leaked into comparison or leaderboards).
  - **P5 (Recovery Idempotence):** Verified fail-closed comparison blocking (`valid_comparison = False`).

---

## Conclusion
WP1 establishes the forensic infrastructure to move from binary failure alarms to root-cause diagnoses and quantified impact windows without modifying the underlying simulation or compromising evidence immutability.
