# TEST RESULTS LEDGER — PHASE 03 SOURCE TRUTH VERIFICATION

**Environment:** Windows 11 (AMD64), Python 3.12.13  
**Official Starter-Kit Commit:** `95cea5b1c57b5291f44baf0283e0a081d53f5b16`  
**Total Tests in Suite:** 36  
**Status:** **36 PASSED, 0 FAILED, 0 SKIPPED (100% PASS RATE)**  
**Execution Command:** `python -m pytest SOURCE_TRUTH_TESTS -v`  
**Execution Time:** 61.16s  

---

## 1. Pinned Source Contract Tests (7 Checks — Previously Skipped)

| Test ID | Purpose | Evidence Type | Status | Tolerances / Notes |
|---|---|---|:---:|---|
| `test_st01_transfer_policy_interface` | Verifies `TransferPolicy` class methods (`__init__`, `get_action`) and hybrid action shape doc | Source Static | **PASS** | `continuous: 3K+2+2V`, `discrete: K+1` |
| `test_st02_floor_plan_and_zone_map_metadata` | Verifies `floor_plan` and `zone_map` are loaded into `building_meta_data` | Source Static | **PASS** | Exact key membership in `evaluate.py` |
| `test_st03_material_generator_parameter_ranges` | Verifies Latin hypercube sampling and log-scale distributions in `materials.py` | Source Static | **PASS** | Exterior conductivity (0.15–0.55 log), density (350–2400 log) |
| `test_st04_manifest_30_pairs_uniqueness` | Verifies `training_set.yaml` has exactly 30 unique pairs across 6 buildings and 5 stations | Source Static | **PASS** | Exact 30/30 count, 0 duplicate strips |
| `test_st05_default_comfort_schedule` | Verifies default schedule in `config.gin` is 06:00 to 19:00 | Source Static | **PASS** | `morning_start_hour=6`, `evening_start_hour=19` |
| `test_st06_reward_source_occupancy_and_rates` | Verifies dynamic occupancy normalization and uncapped reference rates in `setpoint_energy_carbon_regret.py` | Source Static | **PASS** | Zero occupancy gives 0 regret; no `/125` constant |
| `test_st07_score_leaderboard_constants_and_metric` | Verifies `score_leaderboard.py` enforces 8,640 steps and flat scenario MAE metric | Source Static | **PASS** | `BASELINE_STEPS = 8640`, equal weighting |

---

## 2. Standalone Reward Arithmetic Tests (7 Checks)

| Test ID | Purpose | Evidence Type | Status | Tolerances / Notes |
|---|---|---|:---:|---|
| `test_rew_01_comfort_inside_band` | Deviation = 0 K inside comfort band yields 0.0 shortfall and 0.0 regret | Unit (Synthetic) | **PASS** | Exact float 0.0 |
| `test_rew_02_zero_occupancy_yields_zero_regret` | Total occupancy = 0 occupants strictly produces 0.0 comfort regret | Unit (Synthetic) | **PASS** | Exact float 0.0 |
| `test_rew_03_true_occupancy_weighting` | 10 occupants at shortfall 0.5 and 90 at 0.0 yields exactly -0.05 regret | Unit (Synthetic) | **PASS** | Rel tol $10^{-6}$ |
| `test_rew_04_linear_quadratic_comfort_boundary` | 5 K boundary: $f(4)=0.8$, $f(5)=1.0$, $f(6)=1.04$, $f(10)=2.0$ | Unit (Synthetic) | **PASS** | Rel tol $10^{-6}$ |
| `test_rew_05_alternative_productivity_bounds` | Linear invariance under non-zero productivity minimums | Unit (Synthetic) | **PASS** | Rel tol $10^{-6}$ |
| `test_rew_06_weighted_reward_combination` | Exact 0.6 / 0.2 / 0.2 normalization combination arithmetic | Unit (Synthetic) | **PASS** | Rel tol $10^{-6}$ |
| `test_rew_07_rejection_of_invalid_occupancy` | Validator catches and rejects negative occupancy counts | Unit (Synthetic) | **PASS** | Exception raised as expected |

---

## 3. Standalone Scenario Scoring Tests (6 Checks)

| Test ID | Purpose | Evidence Type | Status | Tolerances / Notes |
|---|---|---|:---:|---|
| `test_score_01_equal_scenario_weighting` | Scenarios equally weighted regardless of building size or climate | Unit (Synthetic) | **PASS** | Rel tol $10^{-6}$ |
| `test_score_02_absolute_loss_arithmetic` | Scenario loss calculation $L_s = \vert \bar{r}_s - 0 \vert$ | Unit (Synthetic) | **PASS** | Rel tol $10^{-6}$ |
| `test_score_03_rejection_of_short_episodes` | Non-8640 step episodes cannot be scored against benchmark | Unit (Synthetic) | **PASS** | `ValueError` raised |
| `test_score_04_rejection_of_mismatched_scenario_sets` | Rejection of empty or invalid scenario collections | Unit (Synthetic) | **PASS** | `ValueError` raised |
| `test_score_05_nonfinite_reward_detection` | Rejection of NaN or Inf values in evaluation returns | Unit (Synthetic) | **PASS** | `ValueError` raised |
| `test_score_06_rejection_of_incorrect_aggregation` | Grouped weather means or step-weighted averages violate metric | Unit (Synthetic) | **PASS** | Verified divergence from equal mean |

---

## 4. Simulator Runtime & Policy Interface Tests (4 Checks)

| Test ID | Purpose | Evidence Type | Status | Tolerances / Notes |
|---|---|---|:---:|---|
| `test_runtime_metadata_structure` | Real loaded scenario exposes all 21 metadata keys including floor plans | Simulator Integration | **PASS** | Tested on `building_train_1/atlanta_2` |
| `test_runtime_observation_spec` | Observation shape matches $6V + 15K + 58 = 352$ and reset is finite | Simulator Integration | **PASS** | Shape `(352,)`, all values finite |
| `test_runtime_action_spec_and_validation` | Action specs match `continuous: (92,)` Box and `discrete: (5,)` Box | Simulator Integration | **PASS** | Bounds `[-1.0, 1.0]` and `{0, 1}` |
| `test_runtime_policy_step_lifecycle` | `TransferPolicy` steps live simulator and returns non-positive reward | Simulator Integration | **PASS** | Finite reward $\le 0.0$, no crash |

---

## 5. Fault-Injection Tests (6 Checks)

| Test ID | Purpose | Evidence Type | Status | Tolerances / Notes |
|---|---|---|:---:|---|
| `test_fault_01_invalid_continuous_action_shape` | Rejection of continuous vector with wrong dimension (e.g. 90 vs 92) | Fault Injection | **PASS** | `ValueError` caught |
| `test_fault_02_invalid_discrete_action_shape` | Rejection of discrete vector with wrong dimension (e.g. 6 vs 5) | Fault Injection | **PASS** | `ValueError` caught |
| `test_fault_03_non_finite_action_detection` | Independent guard rejects NaN and Inf continuous setpoints | Fault Injection | **PASS** | `ValueError` caught |
| `test_fault_04_out_of_bounds_continuous_action` | Independent guard rejects out-of-range setpoints ($> 1.0$ or $< -1.0$) | Fault Injection | **PASS** | `ValueError` caught |
| `test_fault_05_incorrect_scoring_arithmetic_detection` | Auditor detects signed means or incorrect scenario divisors | Fault Injection | **PASS** | Divergence verified |
| `test_fault_06_incomplete_scenario_rejection` | Independent scorer rejects 29/30 scenarios | Fault Injection | **PASS** | `RuntimeError` caught |

---

## 6. Independent Scoring Parity Tests (6 Checks)

| Test ID | Purpose | Evidence Type | Status | Tolerances / Notes |
|---|---|---|:---:|---|
| `test_parity_official_baselines_count` | Verifies `baseline_returns.json` contains exactly 30 scenarios | Parity Audit | **PASS** | Exactly 30 scenarios |
| `test_parity_independent_scorer[bang_bang]` | Independent evaluation parity on `bang_bang` baseline returns | Scoring Parity | **PASS** | Discrepancy $< 10^{-12}$ |
| `test_parity_independent_scorer[fixed_setpoint]` | Independent evaluation parity on `fixed_setpoint` baseline returns | Scoring Parity | **PASS** | Discrepancy $< 10^{-12}$ |
| `test_parity_independent_scorer[pid]` | Independent evaluation parity on `pid` baseline returns | Scoring Parity | **PASS** | Discrepancy $< 10^{-12}$ |
| `test_parity_independent_scorer[pid_water]` | Independent evaluation parity on `pid_water` baseline returns | Scoring Parity | **PASS** | Discrepancy $< 10^{-12}$ |
| `test_parity_incomplete_detection` | Rejects incomplete baseline subsets | Scoring Parity | **PASS** | `RuntimeError` caught |
