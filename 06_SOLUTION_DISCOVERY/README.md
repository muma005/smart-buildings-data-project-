# Phase 06: Solution Discovery & Strategy

**Project:** Smart Buildings Challenge — NeurIPS 2026  
**Phase:** 06 — Solution Discovery & Strategy  
**Status:** CLOSED & CERTIFIED (PASS)  
**Exit Gate:** `Gate X1` (Experiment Engine & Strategy Readiness)  
**Authority Reference:** [`Smart_Buildings_Research_Platform_Blueprint_v2.md`](../Smart_Buildings_Research_Platform_Blueprint_v2.md) (Sections 11–15)

---

## 1. Executive Mission

Phase 06 bridges certified experimental infrastructure (Phases 03–05) and empirical controller development (Phase 07). Rather than prematurely selecting popular neural or reinforcement learning architectures, Phase 06 systematically derives candidate control strategies directly from the 7 physical control difficulties established in Problem Research (R1–R5) and Data Understanding (Phase 02).

### The 7 Core Physical Difficulties
1. **Thermal Inertia Spread:** $\tau$ spans $1.94\text{ h}$ (fast/leaky `bldg_7`) to $14.43\text{ h}$ (slow/massive `bldg_1`).
2. **Structural Heterogeneity:** Input observations ($352 \to 703$) and action dimensions ($92 \to 199$) vary across 30 to 85 zones and 4 to 9 AHUs.
3. **Partial Observability:** Internal wall and floor-slab thermal storage is hidden from direct observation.
4. **Shared Equipment Coupling:** Zones compete for shared AHU airflow and central hot-water loop supply.
5. **Delayed Consequences:** Significant thermal lag (45–120 min) between valve actuation and room air temperature response.
6. **Quadratic Comfort Cliff:** Discomfort beyond $5.0\text{ K}$ error triggers an unbounded quadratic penalty ($1 + ((d-5)/5)^2$).
7. **Zero-Shot Generalization:** The single submitted policy must operate across 6 hidden buildings and 5 hidden weather stations.

---

## 2. Directory Structure

```
06_SOLUTION_DISCOVERY/
├── README.md                                 # This directory guide
├── PHASE_06_IMPLEMENTATION_PLAN.md           # Master Phase 06 plan and milestone gates
├── BASELINE_CHARACTERIZATION_REPORT.md       # WP1: Dissection of starter baselines
├── baseline_deficit_matrix.json             # WP1: Machine-readable 30-scenario deficit data
├── SOLUTION_INVESTIGATION_AGENDA.md          # WP2: Taxonomy of candidate solution families
├── HYPOTHESIS_REGISTER.md                    # WP3: Falsifiable hypotheses (H-01 to H-05)
├── hypotheses.json                           # WP3: Machine-readable hypothesis specifications
├── EMPIRICAL_SOLUTION_EVALUATION_REPORT.md   # Live 12-trial empirical test report
├── empirical_test_results.json               # Machine-readable 12-trial simulation results
├── PHASE_06_EXIT_REPORT.md                   # WP5: Gate X1 formal certification signoff
├── benchmarks/                               # Diagnostic scripts and simulation engines
│   ├── audit_baselines.py
│   └── run_solution_experiments.py
├── taxonomies/                               # WP2: Architectural candidate specifications
└── experiments/                              # WP4: Precommitted experiment plans
    └── EXP-001_ADAPTIVE_PRECONDITIONING_PLAN.md
```

---

## 3. Work Package Roadmap

| Work Package | Title | Focus & Scope | Status | Deliverables |
| :---: | :--- | :--- | :---: | :--- |
| **WP1** | **Baseline Characterization & Deficit Audit** | Forensic audit of 4 starter baselines across all 30 scenarios in `baseline_returns.json`. | **CERTIFIED** | [`BASELINE_CHARACTERIZATION_REPORT.md`](BASELINE_CHARACTERIZATION_REPORT.md)<br>[`baseline_deficit_matrix.json`](baseline_deficit_matrix.json) |
| **WP2** | **Solution Architecture Taxonomy** | Map physical problems to 5 candidate engineering solution families. | **CERTIFIED** | [`SOLUTION_INVESTIGATION_AGENDA.md`](SOLUTION_INVESTIGATION_AGENDA.md) |
| **WP3** | **Falsifiable Hypothesis Register** | Formulate testable hypotheses (H-01 to H-05) with quantitative criteria. | **CERTIFIED** | [`HYPOTHESIS_REGISTER.md`](HYPOTHESIS_REGISTER.md)<br>[`hypotheses.json`](hypotheses.json) |
| **WP4** | **First Experiment Plan & Live Trials** | Author precommitted EXP-001 plan and execute 12 live empirical simulation trials. | **CERTIFIED** | [`experiments/EXP-001_ADAPTIVE_PRECONDITIONING_PLAN.md`](experiments/EXP-001_ADAPTIVE_PRECONDITIONING_PLAN.md)<br>[`EMPIRICAL_SOLUTION_EVALUATION_REPORT.md`](EMPIRICAL_SOLUTION_EVALUATION_REPORT.md)<br>[`empirical_test_results.json`](empirical_test_results.json) |
| **WP5** | **Phase 06 Synthesis & Gate X1 Signoff** | Independent audit against Blueprint Section 11/15; Phase 07 handoff. | **CERTIFIED** | [`PHASE_06_EXIT_REPORT.md`](PHASE_06_EXIT_REPORT.md) |

---

## 4. Key Scientific Breakthroughs

1. **Benchmark Target Floor:** `pid_water` is established as the official baseline comparator with a Total Return of **$-14{,}033.42$** and mean MAE of **$0.05414$** across the 30 scenarios.
2. **Thermal Inertia Inversion:** High-inertia buildings ($\tau > 9\text{h}$, `building_train_1`) take 3–5 hours to warm up under reactive feedback, losing to static `fixed_setpoint` by $+115.37$ points per scenario.
3. **Tropical Singapore Failure:** In 100% of Singapore scenarios, `fixed_setpoint` crushes `pid_water` (up to $+731.64$ point deficit in `building_train_5/singapore_4`) due to unconditioned night humidity and morning coil/reheat fighting.
4. **Hierarchical Solution:** The optimal controller architecture integrates Adaptive Pre-Conditioning (RAPC) at the top, Coordinated Economizing (CEMFC) at the plant level, and Modular Decentralized VAV Control (MDVC) with Anti-Windup Comfort Enforcers at the zone level.
5. **Phase 07 Readiness:** `EXP-001` is precommitted with a strict 3-tier testing ladder (Feasibility $< 60\text{s}$, Screening $< 20\text{m}$, Full Trial $< 14\text{h}$), guaranteeing zero wasted compute.
