# Phase 05: Black Box and Failure Engineering

## Overview
Phase 05 establishes the complete Black Box and Failure Engineering infrastructure for the NeurIPS 2026 Smart Buildings Challenge. It ensures every experiment rollout is:
1. **Fully Observable:** High-frequency step transitions, dynamic multi-building observation vectors, unclipped vs. executed actions, and accurate physical reward components.
2. **Crash-Resilient:** Durable daily chunks (288 steps/chunk) synchronized to disk and atomically published with cryptographic checksums.
3. **Independently Verifiable:** Mathematical reward reconstruction and tensor audits without relying on recorder assertions.
4. **Reproducible:** Complete frozen artifacts vault (`artifact_manifest.json`) capturing policy code, local workspace dependencies, and model weights.
5. **Lineage-Governed:** Decoupled execution status (`RunStatus`) and scientific validity (`EvidenceValidity`) with transitive quarantine cascades.
6. **Hardened against Leakage:** Layered multi-ring defenses stopping prohibited simulator access, stack crawling, and private scenario data reading.

---

## Directory Structure

```text
05_FAILURE_ENGINEERING/
│
├── README.md
├── PHASE_05_IMPLEMENTATION_PLAN.md
│
├── tests/
│   ├── crash_worker.py
│   ├── test_gate_01_reward_and_schema.py
│   ├── test_gate_02_crash_resilience.py
│   ├── test_gate_03_independent_verification.py
│   ├── test_gate_04_artifact_preservation.py
│   ├── test_gate_05_state_and_lineage.py
│   ├── test_gate_06_leakage_and_semantics.py
│   ├── test_gate_07_end_to_end_acceptance.py
│   ├── test_stage_4_campaign.py
│   ├── test_wp1_actuator_verification.py
│   ├── test_wp2_leakage_hardening.py
│   ├── test_wp3_genuine_crash_recovery.py
│   ├── test_wp4_release_lifecycle.py
│   ├── test_stage_5_wp1_diagnosis.py
│   ├── test_stage_5_wp2_lineage.py
│   ├── test_stage_5_wp3_repairs.py
│   ├── test_stage_5_wp4_verification.py
│   └── test_stage_5_wp5_certification.py
│
└── evidence/
    ├── gate_01/
    │   └── GATE_01_EXIT_REPORT.md
    ├── gate_02/
    │   └── GATE_02_EXIT_REPORT.md
    ├── gate_03/
    │   └── GATE_03_EXIT_REPORT.md
    ├── gate_04/
    │   └── GATE_04_EXIT_REPORT.md
    ├── gate_05/
    │   └── GATE_05_EXIT_REPORT.md
    ├── gate_06/
    │   └── GATE_06_EXIT_REPORT.md
    ├── gate_07/
    │   └── GATE_07_ACCEPTANCE_REPORT.md
    │
    ├── stage_4/
    │   ├── attack_runs/
    │   ├── clean_controls/
    │   ├── closure_wp1_actuator/
    │   │   ├── WP1_ACTUATOR_SEMANTIC_REPORT.md
    │   │   └── wp1_summary.json
    │   ├── closure_wp2_leakage/
    │   │   ├── POLICY_LEAKAGE_THREAT_MODEL.md
    │   │   ├── WP2_LEAKAGE_HARDENING_REPORT.md
    │   │   └── wp2_summary.json
    │   ├── closure_wp3_crash/
    │   │   ├── WP3_CRASH_RECOVERY_REPORT.md
    │   │   └── wp3_summary.json
    │   ├── closure_wp4_release/
    │   │   ├── WP4_RELEASE_LIFECYCLE_REPORT.md
    │   │   └── wp4_summary.json
    │   ├── ORIGINAL_CAMPAIGN_PROVENANCE.json
    │   └── PHASE_05_STAGE_4_ATTACK_AND_EVIDENCE.md
    │
    └── stage_5/
        ├── investigations/
        │   ├── inv_01_record.json
        │   ├── inv_02_record.json
        │   ├── inv_03_impact_record.json
        │   ├── WP1_FORENSIC_DIAGNOSIS_REPORT.md
        │   └── WP2_LINEAGE_IMPACT_REPORT.md
        ├── repair_verification/
        │   ├── rep_01_record.json
        │   ├── rep_02_record.json
        │   ├── rep_03_record.json
        │   ├── verification_record.json
        │   ├── WP3_CONTROLLED_REPAIRS_REPORT.md
        │   └── WP4_INDEPENDENT_VERIFICATION_REPORT.md
        ├── PHASE_05_STAGE_5_CERTIFICATION.md
        └── PHASE_05_SYSTEM_CERTIFICATION.json
```

---

## Stages Breakdown

* **Stage 1 & 2:** Architecture design, gap mapping, and technical specifications (`PHASE_05_STAGE_2_IMPLEMENTATION_DESIGN.md`).
* **Stage 3 (Gates 1–7):** Core implementation across 7 sequential gates, tested and verified with 107 passing tests.
* **Stage 4:** Controlled Red Team attack runs, fault-injection rollouts, and diagnostic evidence gathering (`evidence/stage_4/`). Completed original 15-attack / 3-control campaign, followed by Work Package 0 independent audit and 4 closure work packages (WP1 Actuators, WP2 Leakage, WP3 Genuine Crash Recovery, WP4 Release Lifecycle) with 100% pass across 24 closure tests while preserving 100% of original campaign evidence.
* **Stage 5:** Forensic investigations, root-cause analyses, repair verification, and final system certification (`evidence/stage_5/`).
