# Smart Buildings Challenge — Source-Truth Verification & S0 Certification (Phase 03)

Welcome to the **Source-Truth Verification Phase** of the NeurIPS 2026 Smart Buildings Challenge repository.

This dedicated directory consolidates the entire audit package, executable test suite, empirical episode evidence, verified system contracts, and gate certification artifacts that closed **Gate S0 (PASS)**.

---

## 📋 Directory Contents & Navigation

```text
03_SOURCE_TRUTH/
│
├── README.md                                  # You are here: Phase 03 index & directory guide
├── Phase_03_Source_Truth.md                   # Mission brief, operational rules & gate requirements
├── SOURCE_TRUTH_AUDIT.md                      # Authoritative claim-by-claim audit matrix against pinned commit
├── VERIFIED_PROBLEM_AND_SYSTEM_CONTRACT.md    # Definitive technical contract (interfaces, physics, rewards)
├── competition-spec.yaml                      # Machine-readable formal competition specification
├── S0_EXIT_REPORT.md                          # Official Gate S0 certification and exit decision
├── TEST_RESULTS.md                            # Comprehensive test ledger (36/36 PASSED, 0 FAILED)
├── PHASE_03_EXECUTION_LOG.md                  # Chronological engineering log of all executed commands
│
├── tests/                                     # Complete 36-test executable verification suite
│   ├── audit_episode_results.py               # Reconstructs episode score from step timeseries
│   ├── independent_evaluator.py               # Standalone reward & leaderboard scoring auditor
│   ├── test_fault_injections.py               # Fault injections (shapes, NaNs/Infs, out-of-bounds, incomplete)
│   ├── test_independent_scoring_parity.py     # Independent evaluator parity against baseline returns (< 1e-6)
│   ├── test_pinned_contract.py                # Static source contract tests (the 7 previously skipped checks)
│   ├── test_reproducibility.py                # Fresh-process environment & policy determinism check
│   ├── test_runtime_interface.py              # Live runtime simulator interface and step execution
│   └── test_synthetic_reward_and_scoring.py   # Standalone known-answer synthetic arithmetic tests
│
└── evidence/
    └── s0_episode/                            # Full 30-day (8,640-step) baseline rollout evidence
        ├── run_manifest.json                  # Episode provenance, git hashes, seeds, and metadata
        └── building_train_1/
            └── atlanta_2/
                ├── comparison.json            # Bitwise parity verification vs official summary
                └── transfer/
                    ├── summary.json           # Official episode return and component breakdown
                    ├── ahu.png                # Fan and heating/cooling coil operation over 30 days
                    ├── overview.png           # Indoor temperatures vs comfort bounds & outdoor weather
                    ├── rewards.png            # Productivity regret, energy cost, and carbon penalty curves
                    ├── timeseries.csv         # 8,640-step observation & physical state trace
                    ├── reward_components.csv  # 8,640-step reward terms decomposition
                    └── ahu_log.csv            # 8,640-step airflow and coil actuation trace
```

---

## 🎯 Phase Deliverables Summary

| Deliverable | Description | Authoritative Source |
| :--- | :--- | :--- |
| **[Phase_03_Source_Truth.md](Phase_03_Source_Truth.md)** | Core execution order, requirements, non-negotiable rules, and gate criteria. | Project Roadmap |
| **[SOURCE_TRUTH_AUDIT.md](SOURCE_TRUTH_AUDIT.md)** | Authoritative claim-by-claim audit matrix against official starter-kit commit `95cea5b`. | Pinned starter kit & repo |
| **[VERIFIED_PROBLEM_AND_SYSTEM_CONTRACT.md](VERIFIED_PROBLEM_AND_SYSTEM_CONTRACT.md)** | Human-readable system contract establishing exact action spaces, observation shapes, physical dynamics, and reward arithmetic. | Audited simulator code |
| **[competition-spec.yaml](competition-spec.yaml)** | Validated YAML specification encoding building schedules, tariff curves, emission intensities, action bounds, and evaluation parameters. | Verified configuration |
| **[S0_EXIT_REPORT.md](S0_EXIT_REPORT.md)** | Formal gate review documenting exit criteria, residual risks, and the **CERTIFIED: PASS** verdict. | Phase 03 sign-off |
| **[TEST_RESULTS.md](TEST_RESULTS.md)** | Complete pass/fail ledger of all 36 tests across static contract, synthetic arithmetic, live runtime, fault injection, and scoring parity. | Pytest test runner |
| **[PHASE_03_EXECUTION_LOG.md](PHASE_03_EXECUTION_LOG.md)** | Complete chronological engineering log capturing timestamps, exit codes, and outputs for all Phase 03 commands. | Execution trace |
| **[tests/](tests/)** | Standalone test suite executing 36 independent checks against the pinned simulator and synthetic baselines. | Python test suite |
| **[evidence/s0_episode/](evidence/s0_episode/)** | Empirical evidence from complete 8,640-step episode rollout reconciling independent vs official return with $0.00\text{e}+00$ discrepancy. | Simulator rollout |

---

## 🔬 Core Verified Invariants

1. **Pinned Repository Commit**: Verified against authoritative upstream commit `95cea5b1c57b5291f44baf0283e0a081d53f5b16`.
2. **Metadata Transparency**: `floor_plan.npy` and `zone_map.npy` are explicitly supplied in building metadata at environment reset, confirming full spatial topology availability.
3. **Closed-Form Dimension Invariants**:
   - Discrete Actions: $D = K + 1$ (AHU switches + boiler supply switch)
   - Continuous Actions: $C = 3K + 2 + 2V$ (fan speeds, supply air temps, cooling setpoints, pump speeds, loop temps, zone cooling/heating setpoints)
   - Observations: $\mathrm{Obs} = 6V + 15K + 58$
4. **Action Midpoint Centering**: Continuous 0.0 corresponds to actuator range midpoint, not OFF.
5. **Reward Formulation**: Dynamic occupancy normalization (productivity regret divides by $\sum N_{\text{occ}}$, yielding 0.0 when unoccupied); electricity ($80\text{ kW/AHU}$) and gas ($205\text{ kW/AHU}$) reference rates act as linear scoring denominators.
6. **Bitwise Determinism**: Fresh-process simulation and policy execution are 100% deterministic ($0.0$ state discrepancy).
