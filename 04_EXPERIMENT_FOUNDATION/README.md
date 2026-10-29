# Smart Buildings Challenge — Minimum Trusted Experiment Foundation & Governance (Phase 04)

Welcome to the **Experiment Foundation & Evaluation Governance Phase** of the NeurIPS 2026 Smart Buildings Challenge repository.

This dedicated directory contains the complete infrastructure, core execution engines, independent score verifiers, evaluation governance manifests, and certified run evidence that closed **Gate S1 (PASS)**.

---

## 📋 Directory Contents & Navigation

```text
04_EXPERIMENT_FOUNDATION/
│
├── README.md                                  # You are here: Phase 04 index & navigation guide
├── PHASE_04_BASELINE_AUDIT.md                 # Inventory of existing code, data, and reuse plan
├── EXPERIMENT_SYSTEM_DESIGN.md                # System architecture, lifecycle state machine & contracts
├── EVALUATION_GOVERNANCE.md                   # Scenario roles, comparison safeguards & contamination rules
├── PHASE_04_TEST_RESULTS.md                   # Test ledger for all 22 tests (100% PASS)
├── PHASE_04_EXIT_REPORT.md                    # Gate S1 certification decision & EXP-001 recommendation
├── PHASE_04_POST_CERTIFICATION_AUDIT.md       # Audit resolving comfort diagnostics, replay, & safeguards
│
├── core/                                      # Core execution and management engines
│   ├── runner.py                              # Simulation runner executing policy episodes
│   ├── policy_adapter.py                      # Wraps policies, validates shapes, hashes source
│   ├── trace_recorder.py                      # Streams transitions step-by-step with checksums
│   ├── registry.py                            # Immutable run registry and state machine
│   ├── evaluator.py                           # Coordinates score verification & diagnostics
│   └── run_vertical_slice.py                  # Integration certification script
│
├── evaluation/                                # Independent evaluation & governance tools
│   ├── score_verification.py                  # Reconstructs scores from traces to 0.00e+00 error
│   ├── diagnostics.py                         # Computes thermal comfort degree-hours & energy breakdown
│   └── comparison_validator.py                # Enforces the Candidate Comparison Contract
│
├── suites/                                    # Versioned evaluation suites
│   ├── official_suite.yaml                    # Full 30-scenario reference suite (role SELECT)
│   └── additional_suites/
│       ├── dev_smoke.yaml                     # 1-scenario unit test suite (role DEV)
│       └── stress_extremes.yaml               # 2-scenario climate edge cases (role STRESS)
│
├── experiments/                               # Experiment definitions and immutable run records
│   ├── experiment_definitions/
│   │   └── exp_000_vertical_slice.yaml        # Formal vertical slice experiment declaration
│   └── runs/
│       └── RUN_EXP-000_vertical_slice_certified/
│           ├── run_manifest.json              # Cryptographic hashes, status, and metadata
│           ├── trace.csv                      # Replay-grade 8,640-step transition trace
│           ├── summary.json                   # Official return and step statistics
│           └── evaluation.json                # Independent scoring audit & diagnostics
│
└── tests/                                     # Comprehensive 22-test automated verification suite
    ├── test_runner.py                         # Tests policy adapter, trace recorder, registry & runner
    ├── test_scoring.py                        # Tests piecewise shortfall, occupancy, and parity
    ├── test_reproducibility.py                # Tests fresh-process simulation determinism
    ├── test_failure_detection.py              # Tests all 12 critical defect modes
    └── test_evaluation_governance.py          # Tests suite integrity and comparison rules
```

---

## 🎯 Phase Deliverables Summary

| Deliverable | Description | Authoritative Source |
| :--- | :--- | :--- |
| **[PHASE_04_BASELINE_AUDIT.md](PHASE_04_BASELINE_AUDIT.md)** | Baseline audit of existing workspace capabilities, simulator interfaces, and reuse plan. | Workspace inspection |
| **[EXPERIMENT_SYSTEM_DESIGN.md](EXPERIMENT_SYSTEM_DESIGN.md)** | Full architectural specification detailing the 6 core responsibilities, lifecycle state machine, and data schemas. | Architecture design |
| **[EVALUATION_GOVERNANCE.md](EVALUATION_GOVERNANCE.md)** | Policy comparison contract, scenario roles (DEV, SELECT, GENERALIZATION, STRESS, SEALED RELEASE), and leakage rules. | Governance standard |
| **[PHASE_04_TEST_RESULTS.md](PHASE_04_TEST_RESULTS.md)** | Full ledger of the 22 automated tests covering runner, scoring, reproducibility, governance, and failure injection. | Pytest test runner |
| **[PHASE_04_EXIT_REPORT.md](PHASE_04_EXIT_REPORT.md)** | Formal Gate S1 certification sign-off, remaining risks, and concrete proposal for Experiment EXP-001. | Gate S1 sign-off |
| **[suites/official_suite.yaml](suites/official_suite.yaml)** | Validated YAML specification of the 30 official competition scenarios. | Pinned starter kit |
| **[core/](core/)** | Reusable, modular engines for running, recording, hashing, and managing policy simulation experiments. | Implemented software |
| **[evaluation/](evaluation/)** | Standalone tools for score verification, physical diagnostics, and comparison validation. | Implemented software |
| **[experiments/runs/](experiments/runs/)** | Immutable directory storing certified 8,640-step run evidence. | Execution evidence |

---

## 🔬 Core System Certifications

1. **Replay-Grade Traceability**: Every run is assigned a unique ID, stamped with SHA-256 hashes of config, policy, and trace, and tracked via an immutable state machine.
2. **Dual-Scoring Parity**: Independent score reconstruction achieves strict **`0.00e+00` error** against official summary returns.
3. **Bitwise Determinism**: Fresh-process policy reload and simulation stepping yield identical observations, actions, and rewards ($0.0$ variance).
4. **Comparison Integrity**: Automated validator rejects candidate comparisons if suites differ, episode counts are incomplete, or runs contain errors.
5. **Defect Rejection**: Injected fault harness successfully traps all 12 defect modes including malformed shapes, NaNs/Infs, out-of-range actions, non-monotonic steps, missing files, and duplicate directories.
