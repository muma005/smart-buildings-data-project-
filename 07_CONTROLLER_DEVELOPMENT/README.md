# Phase 07: Controller Development & Empirical Trials

**Project:** Smart Buildings Challenge — NeurIPS 2026  
**Phase:** 07 — Controller Development & Empirical Trials  
**Status:** IN PROGRESS  
**Exit Gate:** `Gate C1` (Candidate Arena & Promotion Authority)  
**Authority Reference:** [`Smart_Buildings_Research_Platform_Blueprint_v2.md`](../Smart_Buildings_Research_Platform_Blueprint_v2.md) (Sections 11–15)

---

## 1. Phase Objective

Phase 07 synthesizes, refines, and benchmarks a production-grade, competition-compliant control policy: **`RegimeAdaptiveHVACPolicy`**, based on the physical discoveries validated during Phase 06 live simulation trials.

The objective is to establish an independently verified candidate controller that beats the official starter baseline (`pid_water`, Total Return $-14{,}033.42$, MAE $0.05414$) across all 30 official development scenarios, satisfying Gate `C1` criteria.

---

## 2. Directory Structure

```
07_CONTROLLER_DEVELOPMENT/
├── README.md                             # This phase guide
├── PHASE_07_IMPLEMENTATION_PLAN.md       # Master 4-sprint implementation plan
├── policies/                             # Production controller implementations
│   └── regime_adaptive_hvac.py           # Core RegimeAdaptiveHVACPolicy implementation
├── tests/                                # Automated testing ladder
│   ├── test_tier1_interfaces.py          # Tier 1 smoke tests across all 6 buildings
│   └── test_tier2_diagnostics.py         # Tier 2 multi-day diagnostic verification
├── benchmarks/                           # Benchmark runner scripts and manifests
├── evidence/                             # Replay traces, diagnostics, and manifests
└── PHASE_07_BENCHMARK_REPORT.md          # 30-scenario matched benchmark results
```

---

## 3. Four-Sprint Roadmap

| Sprint | Focus & Scope | Target Files | Status |
| :---: | :--- | :--- | :---: |
| **Sprint 1** | **Production Policy & Tier 1 Tests** | `policies/regime_adaptive_hvac.py`<br>`tests/test_tier1_interfaces.py` | PENDING |
| **Sprint 2** | **Tier 2 Diagnostic Screenings** | Multi-day runs on Fairbanks, Singapore, Atlanta, Denver | PENDING |
| **Sprint 3** | **Component Refinements** | Preconditioning ramps, fan pressure trim, anti-windup | PENDING |
| **Sprint 4** | **Full 30-Scenario Matched Benchmark** | 30 full 30-day episodes, `PHASE_07_BENCHMARK_REPORT.md` | PENDING |
