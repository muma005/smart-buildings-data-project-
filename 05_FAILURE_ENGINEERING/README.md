# Phase 05: Black Box and Failure Engineering

## Overview
Phase 05 establishes the complete Black Box and Failure Engineering infrastructure for the NeurIPS 2026 Smart Buildings Challenge. It ensures every experiment rollout is:
1. **Fully Observable:** High-frequency step transitions, dynamic multi-building observation vectors, unclipped vs. executed actions, and accurate physical reward components.
2. **Crash-Resilient:** Durable daily chunks (288 steps/chunk) synchronized to disk and atomically published with cryptographic checksums.
3. **Independently Verifiable:** Mathematical reward reconstruction and tensor audits without relying on recorder assertions.
4. **Reproducible:** Complete frozen artifacts vault (`artifact_manifest.json`) capturing policy code, local workspace dependencies, and model weights.
5. **Lineage-Governed:** Decoupled execution status (`RunStatus`) and scientific validity (`EvidenceValidity`) with transitive quarantine cascades.
6. **Hardened against Leakage:** Layered multi-ring defenses stopping prohibited simulator access, stack crawling, and private scenario data reading.

## Directory Structure
* `evidence/`: Artifacts, traces, and verification logs for each implementation gate (`gate_01` through `gate_07`).
* `tests/`: Targeted pytest test suites verifying each gate and Red Team failure mode.
* `PHASE_05_IMPLEMENTATION_PLAN.md`: Detailed progress log across the 7 implementation gates.
