# Gate 1 Exit Evidence: Reward and Schema Correctness

## Overview
* **Status:** PASS
* **Date:** 2026-11-01
* **Active Git Commit:** `00c911a270af3bdbc52dc1e16c9d3e6c139cb175`
* **Test Suite:** `05_FAILURE_ENGINEERING/tests/test_gate_01_reward_and_schema.py`
* **Results:** 6 passed in 275.79s (100% pass rate).

---

## 1. Verified Implementation Changes

### A. Official Interface Connection
* Replaced flawed private attribute access (`getattr(env, "_productivity_regret", 0.0)`) with the verified official protobuf method `env.get_reward_info_and_response()`.
* Extracted true components from `RewardResponse`:
  * `normalized_productivity_regret`
  * `normalized_energy_cost`
  * `normalized_carbon_emission`
  * `total_occupancy`
  * `agent_reward_value`

### B. Fail-Fast Evidence Integrity Protection
* If `reward_response` is `None` or malformed, `SimulationRunner` raises `EvidenceCaptureError`. Zero is never silently substituted for missing evidence.
* On Step 0, an explicit arithmetic check asserts:
  $$|R_0 - (0.6 \cdot \text{regret}_0 - 0.2 \cdot \text{energy}_0 - 0.2 \cdot \text{carbon}_0)| \le 1.0 \times 10^{-6}$$
  Any deviation immediately aborts the run and transitions it to `RunStatus.FAILED`.

### C. Decision & Clipping Provenance
* `PolicyAdapter` preserves:
  * `raw_continuous_action` (unclipped policy output)
  * `executed_continuous_action` (clipped $[-1, 1]$ setpoints)
  * `was_clipped` (boolean flag)
  * `max_clip_delta` ($\max |a_{\text{raw}} - a_{\text{exec}}|$)
  * `latency_ms` (policy execution time)
* Read-only protection: `obs.flags.writeable = False` is enforced before passing observation vectors to policies, stopping in-place tensor tampering.

### D. Dynamic Multi-Building Schemas
* Tested and proven across buildings with radically different dimensions:
  * `building_train_1`: `(352,)` observation, `(92,)` continuous actions, `(5,)` discrete actions.
  * `building_train_2`: `(703,)` observation, `(199,)` continuous actions, `(10,)` discrete actions.
* Zero hardcoded dimensions in the pipeline.

---

## 2. Test Execution Evidence

```
05_FAILURE_ENGINEERING/tests/test_gate_01_reward_and_schema.py::test_gate_01_reward_components_captured_and_nonzero_when_operating PASSED [ 16%]
05_FAILURE_ENGINEERING/tests/test_gate_01_reward_and_schema.py::test_gate_01_reconstructed_reward_parity PASSED [ 33%]
05_FAILURE_ENGINEERING/tests/test_gate_01_reward_and_schema.py::test_gate_01_missing_reward_raises_evidence_capture_error PASSED [ 50%]
05_FAILURE_ENGINEERING/tests/test_gate_01_reward_and_schema.py::test_gate_01_divergent_step0_reward_raises_evidence_capture_error PASSED [ 66%]
05_FAILURE_ENGINEERING/tests/test_gate_01_reward_and_schema.py::test_gate_01_dynamic_schema_multi_building PASSED [ 83%]
05_FAILURE_ENGINEERING/tests/test_gate_01_reward_and_schema.py::test_gate_01_raw_vs_executed_action_and_clipping PASSED [100%]
```

---

## 3. Regression Baseline Verification
* `04_EXPERIMENT_FOUNDATION/tests/test_runner.py`: 4 passed.
* `04_EXPERIMENT_FOUNDATION/tests/test_scoring.py`: 6 passed.
* Zero existing functionality broken.
