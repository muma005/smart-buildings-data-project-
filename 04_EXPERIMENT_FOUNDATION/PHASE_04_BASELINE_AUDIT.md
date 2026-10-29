# Phase 04 — Baseline Audit: Existing Work & Implementation Inventory

**Project:** Smart Buildings Challenge — NeurIPS 2026  
**Phase:** 04 — Minimum Trusted Experiment Foundation & Evaluation Governance  
**Date:** 2026-10-29  
**Status:** COMPLETE (Baseline Established)  

---

## 1. Executive Summary

Phase 03 verified the ground-truth competition contract, certified Gate S0 (**PASS**), unblocked all 7 previously skipped tests, achieved a 36/36 passing test suite, executed a full 8,640-step episode on `building_train_1 / atlanta_2`, and proved scoring parity against the official evaluator to `0.00e+00` discrepancy.

Before designing or implementing Phase 04 components, this audit inventories existing code, data, and test assets to determine:
1. What already exists and can be directly reused.
2. What requires repair, adaptation, or hardening.
3. What is genuinely missing and must be newly implemented.

---

## 2. Environment & Tooling Inventory

| Component | Verified Specification | Status |
| :--- | :--- | :--- |
| **Operating System** | Windows 10 (10.0.21996) 64-bit AMD64 | Ready |
| **Python Runtime** | Python 3.12.13 (in `.venv`) | Ready |
| **Pinned Starter Kit** | Git commit `95cea5b1c57b5291f44baf0283e0a081d53f5b16` | Pinned & Verified |
| **Core Libraries** | `pytest` 9.1.1, `numpy` 2.5.4, `pandas` 3.0.6, `pyyaml` 6.0.3, `gin-config` | Operational |
| **Workspace Git Head** | `ac3b531` (`main`), clean working tree | Synced |

---

## 3. Capability Inventory & Reuse Plan

| Required Capability | Existing Implementation & Location | Working Evidence | Deficiencies / Missing Behavior | Action Decision | Acceptance Test |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Simulator Loading & Stepping** | `smart_buildings.evaluate.load_hybrid_environment` | Executed 8,640 steps in Phase 03; `test_runtime_interface.py` passes | Ad-hoc script execution; lacks standardized experiment configuration & lifecycle management | **REUSE & WRAP** into `core/runner.py` | Complete 5-step test episode and 8,640-step trace |
| **Policy Interface & Validation** | `smart_buildings.evaluate.initialize_policy`, `validate_action` | `TransferPolicy` stepped across 8,640 steps without validation errors | Validation occurs only at gym step; no policy hashing, error trapping, or runtime contract adapter | **IMPLEMENT** `core/policy_adapter.py` | Rejects malformed actions, NaNs, and provides sha256 artifact hashing |
| **Independent Scoring Engine** | `03_SOURCE_TRUTH/tests/independent_evaluator.py` | `0.00e+00` return diff against `summary.json`; matches `baseline_returns.json` | Standalone script; lacks modular separation of diagnostics, score verification, and trace streaming | **REUSE & ENHANCE** into `evaluation/score_verification.py` and `core/evaluator.py` | Known-answer synthetic tests and episode parity |
| **Trace & Episode Recording** | Ad-hoc file generation in `smart_buildings/evaluate.py` (`metrics_path`) | Generates `timeseries.csv`, `reward_components.csv`, `summary.json` | Dumps raw simulator state; no immutable schema, no validation of missing/corrupt rows, high storage overhead | **IMPLEMENT** `core/trace_recorder.py` | Streaming recorder with schema validation, zero data loss, and integrity checks |
| **Experiment Registry & State Management** | None (Ad-hoc folder creation `results/s0_episode`) | None | No unique run IDs; no state machine (`RUNNING`, `COMPLETE`, `FAILED`, etc.); allows accidental overwrite | **IMPLEMENT** `core/registry.py` | Rejects duplicate IDs, handles interrupted runs, validates artifact hashes |
| **Evaluation Governance & Suites** | `starter_kit_pinned/baseline_returns.json` (30 scenarios) | Baseline returns verified in Phase 03 | No formal YAML suite definition; no concept of DEV vs SELECT vs STRESS roles; no leakage guards | **IMPLEMENT** `suites/official_suite.yaml` and `EVALUATION_GOVERNANCE.md` | Suite manifest parser & overlap validator |
| **Candidate Comparison Validator** | None | None | Nothing prevents comparing runs from different suites, partial runs, or different scoring definitions | **IMPLEMENT** `evaluation/comparison_validator.py` | Rejects mismatched suites, missing episodes, or unequal aggregation |
| **Diagnostics & Failure Engineering** | Basic penalty metrics in `independent_evaluator.py` | Synthetic tests in Phase 03 | No degree-hour thermal comfort metrics; no HVAC subsystem energy breakdown (fan vs chiller vs boiler) | **IMPLEMENT** `evaluation/diagnostics.py` and `tests/test_failure_detection.py` | Detects all 12 injected failure modes |

---

## 4. Phase 03 Critical Findings Carryover

1. **Information Boundary**: `floor_plan.npy` and `zone_map.npy` are explicitly supplied in building metadata. The `policy_adapter` must package these cleanly to policies.
2. **Action Centering**: Continuous action $0.0$ is the range midpoint. The adapter must never treat $0.0$ as "off".
3. **Reward Invariant**: Productivity regret is divided by dynamic occupancy ($\sum N_{\text{occ}}$), strictly $0.0$ when unoccupied.
4. **Schedule Invariant**: Comfort hours are strictly 06:00 to 19:00 with a 1-hour early warning flag (`comfort_mode_soon = True` at 05:00).
5. **Determinism**: The simulator is 100% deterministic under identical seeds and action sequences.

---

## 5. Exit Condition Assessment

- [x] Workspace structure and Git status verified clean.
- [x] Pinned commit verified and accessible.
- [x] Reusable assets from Phase 03 identified (`independent_evaluator.py`, verified formulas, 8,640-step rollout trace).
- [x] Missing capabilities isolated into concrete Phase 04 components.
- [x] Acceptance criteria defined for every component.

**Stage 0 Verdict: PASS**. Proceed to Stage 1 (Full Architecture Design).
