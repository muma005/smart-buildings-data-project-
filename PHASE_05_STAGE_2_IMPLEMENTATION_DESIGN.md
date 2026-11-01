# Phase 05 — Stage 2B: Final Black Box Implementation Blueprint
**Project:** Smart Buildings Challenge — NeurIPS 2026  
**Document:** `PHASE_05_STAGE_2_IMPLEMENTATION_DESIGN.md`  
**Revision:** Stage 2B Architectural Blueprint (Incorporating Stage 2 Design Review)  
**Status:** DESIGN & INSPECTION ONLY (Zero Code Modifications)  
**Active Project Repository Commit:** `00c911a270af3bdbc52dc1e16c9d3e6c139cb175` (`00c911a`)  
**Pinned Official Starter-Kit Commit:** `95cea5b1c57b5291f44baf0283e0a081d53f5b16` (`95cea5b`)  
**Design Date:** 2026-10-31  

---

## Document Revision History

| Revision | Date | Author / Reviewer | Scope & Key Modifications |
| :--- | :--- | :--- | :--- |
| **v1.0 (Stage 2)** | 2026-10-31 | Initial Architecture | Initial Black Box design based on Stage 1 Gap Map. Introduced dual-tier storage (`trace.csv` + `transitions.npz`), basic lineage fields, and initial Red Team mapping. |
| **v2.0 (Stage 2B)** | 2026-10-31 | Stage 2 Review & Blueprint | **Major Architectural Corrections Incorporated:**<br>1. *Crash-Resilient Persistence:* Replaced end-of-episode monolithic NPZ dumping with durable atomic daily chunking (288 steps/chunk, `.tmp` staging, `os.fsync`, atomic publication).<br>2. *Schema Dimensionality Truth:* Corrected hardcoded `(352,)` / `(92,)` assumptions; empirically verified that building observation dimensions vary from 283 to 703 and continuous action dimensions vary from 71 to 199 across the 6 benchmark buildings.<br>3. *Decoupled State Machine:* Separated physical execution status (`RunStatus`) from scientific eligibility (`EvidenceValidity`) so historical runs preserve execution facts even when quarantined.<br>4. *Multi-Node Transitive Lineage:* Replaced scalar parent IDs with a typed dependency graph supporting baseline, policy, checkpoint, and comparison report cascades without indiscriminate over-invalidation.<br>5. *Four-Ring Information Leakage Protection:* Upgraded F3 defense from static AST checks to a 4-ring layered model (structural boundary, AST analysis, read-only runtime immutability, empirical probes).<br>6. *Controlled Interventional Semantic Probes:* Replaced passive correlation with single-variable actuator pulse interventions to isolate causal thermal responses.<br>7. *Storage & Overhead Targets:* Formulated uncompressed vs. compressed storage budgets per building and defined empirical benchmark protocols. |

---

## 1. Executive Summary and Design Decisions

The objective of the **Experiment Black Box and Evidence System** is to make experiments in the Smart Buildings Challenge independently inspectable, mathematically reproducible, diagnosable upon failure, and protected against invalidation cascade errors.

Following the comprehensive audit in Stage 1 and the critical design review of the initial Stage 2 proposal, this blueprint resolves six fundamental architectural challenges:

1. **Failure-Resilient Chunked Transition Persistence:** High-frequency step transitions are persisted via incremental, durable daily chunks (288 steps per batch, matching the 24-hour simulation cycle). Chunks are written to temporary staging files, synchronized to disk with `os.fsync()`, and atomically renamed. Process crashes preserve all completed chunks on disk without silent truncation or corrupted archives.
2. **Dynamic Scenario-Aware Schema Modeling:** Building feature dimensions are not static. Empirical inspection of all 6 competition buildings confirmed that observation dimensions range from 283 to 703, continuous actions from 71 to 199, discrete actions from 4 to 10, and thermal zones from 30 to 85. The Black Box binds directly to `env.observation_space`, `env.action_spec()`, and `metadata["observation_field_names"]`, eliminating hardcoded dimension assumptions.
3. **Decoupled Execution Status and Evidence Validity:** Historical simulation outcomes (`execution_status`: `COMPLETE`, `FAILED`, `INCOMPLETE`) are permanently decoupled from governance determinations (`evidence_validity`: `UNVERIFIED`, `VALID`, `INVALID`, `QUARANTINED`). A run that finished 8,640 steps remains historically `COMPLETE` even if an upstream baseline defect later marks its comparative conclusions `QUARANTINED`.
4. **Typed Transitive Lineage Graph:** A directed acyclic dependency graph tracks relationships (`baseline_comparator`, `policy_artifact`, `environment_config`, `training_checkpoint`, `comparison_report`). Invalidation cascades trace downstream dependents selectively, revoking comparison validity while preserving independent diagnostic utility.
5. **Layered Information-Leakage Defense:** Protection against prohibited access (e.g. reading future weather or simulator internals) is enforced across four distinct rings: restricted input boundaries, static AST import parsing, runtime array immutability (`flags.writeable = False`), and controlled Red Team leakage probes.
6. **Controlled Interventional Probes for Actuator Semantics:** Passive trajectory cross-correlation cannot distinguish direct HVAC reheating from inter-zone conductive heat transfer. Semantic mapping verification employs controlled, single-actuator pulse perturbations to prove causal zone-to-actuator alignment.

---

## 2. Verified Current Architecture

### 2.1 Pinned Commit & Working Tree Verification

* **Project Repository Commit:** `00c911a270af3bdbc52dc1e16c9d3e6c139cb175` (`00c911a` on branch `main`).
* **Authoritative Starter-Kit Commit:** `95cea5b1c57b5291f44baf0283e0a081d53f5b16` (`95cea5b`).
* **Working Tree Status:** Clean; zero uncommitted modifications in source or test trees.
* **Test Suite Baseline:** 46 passing tests in `04_EXPERIMENT_FOUNDATION/tests` (0 failures, 0 skipped, runtime 166.92s).

### 2.2 Execution Flow and Verified Defect Locations

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    CURRENT WORKSPACE EXECUTION PIPELINE                     │
│                                                                             │
│ 1. Run Registration: ExperimentRegistry.create_run()                        │
│    ├── Generates RUN_<exp_id>_<scenario>_<timestamp>_<uuid>                 │
│    ├── Writes run_manifest.json (status: INITIALIZED)                       │
│    └── Computes policy_sha256 & config_sha256                               │
│                               │                                             │
│                               ▼                                             │
│ 2. Simulation Setup: SimulationRunner.execute_episode()                     │
│    ├── Transitions status to RUNNING                                        │
│    ├── Loads env via smart_buildings.evaluate.load_hybrid_environment()     │
│    ├── Extracts metadata via create_building_meta_data(env, gin_path)       │
│    └── Instantiates PolicyAdapter(policy_class, action_spec, metadata)      │
│        [GAP: Only root policy file hashed; local dependencies omitted]      │
│                               │                                             │
│                               ▼                                             │
│ 3. Step Loop (up to 8,640 steps @ 5-minute intervals = 30 days):            │
│    ├── PolicyAdapter.get_action(obs): clips continuous setpoints [-1, 1]    │
│    │   [GAP: Discards unclipped raw action; no observation checks]          │
│    ├── env.step(action): advances EnergyPlus simulation                     │
│    ├── Runner extracts reward components:                                   │
│    │   prod_regret = getattr(env, "_productivity_regret", 0.0)             │
│    │   energy_cost = getattr(env, "_energy_cost", 0.0)                      │
│    │   carbon_penalty = getattr(env, "_carbon_penalty", 0.0)                │
│    │   [VERIFIED DEFECT: Attributes do not exist on env; ALWAYS yields 0.0] │
│    └── TraceRecorder.record_step(): writes row to trace.csv                 │
│        [GAP: Discards full obs vector; saves only action sum & mean]        │
│                               │                                             │
│                               ▼                                             │
│ 4. Episode Completion:                                                      │
│    ├── TraceRecorder.close(): computes trace_sha256                         │
│    ├── Writes summary.json (cumulative reward, step count)                  │
│    └── Registry.update_status(COMPLETE or INCOMPLETE)                       │
│        [GAP: Crash before step 8,640 leaves no tensor evidence on disk]     │
│                               │                                             │
│                               ▼                                             │
│ 5. Post-Run Evaluation: RunEvaluator.evaluate_run()                         │
│    ├── ScoreVerifier.verify_trace_and_score(): audits CSV reward column     │
│    ├── DiagnosticsEngine.analyze_trace(): computes degree-hours & comfort   │
│    └── Writes evaluation.json                                               │
│                               │                                             │
│                               ▼                                             │
│ 6. Comparison Governance: ComparisonValidator.validate_comparison()         │
│    [GAP: Tested only with synthetic fixtures; no multi-scenario orchestrator]│
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Evidence Contract

The Black Box records an immutable, cryptographically verifiable audit trail spanning eight distinct lifecycle events:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            EVIDENCE CONTRACT                                │
│                                                                             │
│ [1. INITIALIZATION] ──> run_manifest.json + artifact_manifest.json          │
│ [2. POLICY INPUT]   ──> observations (durable chunks: chunks/chunk_*.npz)   │
│ [3. DECISION]       ──> raw_continuous_actions (chunks/chunk_*.npz)         │
│ [4. EXECUTION]      ──> executed_continuous_actions (chunks/chunk_*.npz)    │
│ [5. TRANSITION]     ──> reward components & zone temps (trace.csv + chunks) │
│ [6. COMPLETION]     ──> summary.json + chunks_manifest.json                 │
│ [7. EVALUATION]     ──> evaluation.json + comparison_report.json            │
│ [8. PROMOTION]      ──> promotion_manifest.json                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Stage 1: Experiment Initialization (`EXPERIMENT_INITIALIZED`)
* **Capturing Component:** `ExperimentRegistry` & `SimulationRunner`.
* **Output Files:** `run_manifest.json` and `artifact_manifest.json`.
* **Required Fields:**
  * `run_id`: `str` (`RUN_<exp_id>_<scenario>_<timestamp>_<uuid>`).
  * `experiment_id`: `str`.
  * `scenario_id`: `str` (`<building>/<weather>`).
  * `suite_id`: `str` (e.g. `official_suite`).
  * `suite_version`: `str` (`1.0`).
  * `project_git_commit`: `str` (`00c911a270af3bdbc52dc1e16c9d3e6c139cb175`).
  * `starter_kit_commit`: `str` (`95cea5b1c57b5291f44baf0283e0a081d53f5b16`).
  * `python_version`: `str` (`sys.version.split()[0]`).
  * `platform`: `str` (`sys.platform`).
  * `random_seed`: `int | None`.
  * `execution_status`: `RunStatus.INITIALIZED`.
  * `evidence_validity`: `EvidenceValidity.UNVERIFIED`.
  * `schema_version`: `"v2.0"`.
  * `feature_dimensions`: `{"obs_dim": int, "cont_dim": int, "disc_dim": int, "n_zones": int}`.
  * `dependencies`: List of typed dependency objects (see Section 7).

### Stage 2: Policy Input (`POLICY_INPUT_OBSERVED`)
* **Capturing Component:** `SimulationRunner` & `TraceRecorder`.
* **Storage Location:** `trace.csv` (step index and ISO timestamp) and `chunks/chunk_*.npz` (full array).
* **Data Structure:** NumPy array `obs_t` of shape `(obs_dim,)`, dtype `float32`.
* **Contract Checks:** Shape must strictly match `env.observation_space.shape`; all elements must be finite (no NaNs, no Infs).

### Stage 3: Policy Decision (`POLICY_DECISION_GENERATED`)
* **Capturing Component:** `PolicyAdapter`.
* **Storage Location:** In-memory decision container forwarded to `TraceRecorder`; stored in `chunks/chunk_*.npz`.
* **Data Structure:**
  * `raw_continuous_action`: `np.ndarray` of shape `(cont_dim,)`, dtype `float32`.
  * `raw_discrete_action`: `np.ndarray` of shape `(disc_dim,)`, dtype `int32`.
  * `policy_latency_ms`: `float`.
* **Contract Checks:** Shape matches action spec prior to clipping or projection.

### Stage 4: Action Execution (`ACTION_EXECUTED`)
* **Capturing Component:** `PolicyAdapter` & `TraceRecorder`.
* **Storage Location:** `trace.csv` (summary statistics) and `chunks/chunk_*.npz` (exact arrays).
* **Data Structure:**
  * `executed_continuous_action`: `np.ndarray` of shape `(cont_dim,)`, dtype `float32`, bounded $[-1.0, 1.0]$.
  * `executed_discrete_action`: `np.ndarray` of shape `(disc_dim,)`, dtype `int32`.
  * `was_clipped`: `bool`.
  * `max_clip_delta`: `float` ($\max_i |a_{\text{raw}, i} - a_{\text{exec}, i}|$).

### Stage 5: Simulator Transition (`SIMULATOR_TRANSITION_COMPLETED`)
* **Capturing Component:** `SimulationRunner` & `TraceRecorder`.
* **Storage Location:** Columnar entries in `trace.csv` and multi-dimensional arrays in `chunks/chunk_*.npz`.
* **Data Structure:**
  * `reward`: `float` (scalar step reward from `env.step()`).
  * `normalized_productivity_regret`: `float` ($\le 0.0$).
  * `normalized_energy_cost`: `float` ($\ge 0.0$).
  * `normalized_carbon_emission`: `float` ($\ge 0.0$).
  * `total_occupancy`: `float`.
  * `zone_air_temperatures`: `np.ndarray` of shape `(n_zones,)`, dtype `float32` (Kelvin and converted Celsius).
  * `outdoor_temperature`: `float`.

### Stage 6: Episode Completion (`EPISODE_COMPLETED`)
* **Capturing Component:** `SimulationRunner` & `ExperimentRegistry`.
* **Storage Location:** `summary.json`, `chunks_manifest.json`, and updated `run_manifest.json`.
* **Required Fields:**
  * `actual_steps`: `int` (must equal `expected_steps` = 8,640 for `COMPLETE`).
  * `execution_status`: `RunStatus.COMPLETE` (or `INCOMPLETE` / `FAILED`).
  * `cumulative_reward`: `float`.
  * `trace_csv_sha256`: `str`.
  * `chunks_manifest_sha256`: `str`.

### Stage 7: Evaluation & Comparison (`RUN_EVALUATED` & `COMPARISON_PERFORMED`)
* **Capturing Component:** `RunEvaluator` & `ComparisonValidator`.
* **Storage Location:** `evaluation.json` and `campaigns/<campaign_id>/comparison_report.json`.
* **Required Fields:**
  * Independent score reconstruction delta ($\Delta \le 1.0 \times 10^{-6}$).
  * Physical comfort diagnostics (degree-hours, occupied compliance %).
  * `evidence_validity`: `EvidenceValidity.VALID` (or `INVALID`).
  * Candidate vs. baseline comparison metrics.

### Stage 8: Candidate Audit & Promotion (`CANDIDATE_AUDITED`)
* **Capturing Component:** Competition Governance Auditor.
* **Storage Location:** `promotions/<timestamp>_promotion.json`.
* **Required Fields:** Holdout suite eligibility check, comfort drift constraint verification ($< 5.0\text{ K}$ max drift), frozen dependency bundle, release submission package.

---

## 4. Corrected Trace Storage and Crash Recovery Design

### 4.1 Root Cause of Current Zero-Default Defect
In [`04_EXPERIMENT_FOUNDATION/core/runner.py`](file:///04_EXPERIMENT_FOUNDATION/core/runner.py#L117), the code attempts:
```python
prod_regret = getattr(env, "_productivity_regret", 0.0)
energy_cost = getattr(env, "_energy_cost", 0.0)
carbon_penalty = getattr(env, "_carbon_penalty", 0.0)
```
These private attributes do not exist on `HybridActionEnvironment` or `Environment`. As a result, Python silently fell back to `0.0` for all 8,640 steps of every rollout.

### 4.2 Authoritative Reward Component Extraction
Re-inspection of the official starter kit confirms that `HybridActionEnvironment` inherits from `Environment`, which implements `get_reward_info_and_response() -> tuple[RewardInfo, RewardResponse]`. In fact, `Environment._get_reward()` calls this method directly during `env.step()`.

The exact, non-destructive extraction logic to be implemented in `SimulationRunner` is:
```python
# Immediately after step_res = env.step(action):
obs, reward, terminated, truncated, info = step_res

# Query official protobuf reward response
reward_info, reward_response = env.get_reward_info_and_response()

if reward_response is None:
    raise EvidenceCaptureError(
        f"Environment returned None for RewardResponse at step {step_idx}. "
        "Halting simulation to prevent corrupted evidence capture."
    )

prod_regret = float(reward_response.normalized_productivity_regret)  # <= 0.0
energy_cost = float(reward_response.normalized_energy_cost)          # >= 0.0
carbon_penalty = float(reward_response.normalized_carbon_emission)   # >= 0.0
agent_reward = float(reward_response.agent_reward_value)
occupants = float(reward_response.total_occupancy)

# Hard invariant check on Step 0:
expected_r = (
    reward_response.productivity_weight * prod_regret
    - reward_response.energy_cost_weight * energy_cost
    - reward_response.carbon_emission_weight * carbon_penalty
)
if abs(agent_reward - expected_r) > 1e-6:
    raise EvidenceCaptureError(
        f"Step 0 reward arithmetic divergence: agent_reward={agent_reward}, "
        f"reconstructed={expected_r}, diff={abs(agent_reward - expected_r)}"
    )
```

### 4.3 Crash-Resilient Incremental Chunk Storage Architecture

Accumulating all 8,640 transitions in memory and serializing a single `.npz` archive upon episode completion is fundamentally vulnerable: any mid-episode process crash (OOM killer, power failure, OS signal) destroys the detailed transition evidence.

We replace the monolithic dump with a **Durable Incremental Daily Chunk Architecture**:

```
run_directory/
├── run_manifest.json          (Provenance, hashes, state machine, lineage)
├── artifact_manifest.json     (Frozen policy, local dependencies, weights)
├── summary.json               (High-level score and termination summary)
├── evaluation.json            (Independent audit verification & diagnostics)
├── trace.csv                  (Human-readable streaming CSV, flushed per-step)
├── chunks_manifest.json       (Cryptographic registry of all committed chunks)
└── chunks/                    (Durable incremental binary archives)
    ├── chunk_0000.npz         (Steps 0 to 287   - Day 1)
    ├── chunk_0001.npz         (Steps 288 to 575 - Day 2)
    ├── ...
    └── chunk_0029.npz         (Steps 8352 to 8639 - Day 30)
```

#### Chunk Sizing Evaluation & Trade-off Analysis
* **Episode Horizon:** 8,640 steps (30 days $\times$ 24 hours $\times$ 12 steps/hour).
* **Chunk Size Decision:** `chunk_size = 288` steps (exactly 1 simulation day).
* **Rationale:**
  * 288 steps matches the diurnal HVAC thermal and occupancy cycle.
  * Exactly 30 chunks per completed episode ($30 \times 288 = 8,640$).
  * Uncompressed chunk size is modest ($\approx 0.65\text{ MB}$ for Building 1; $\approx 1.3\text{ MB}$ for Building 2).
  * Disk serialization occurs once every 288 steps (roughly every 5–10 seconds of simulation wall-clock time), minimizing disk I/O contention.

#### Durability and Atomic Publication Protocol
To guarantee that no partially written, truncated, or corrupted chunk is ever recognized as valid evidence:
1. **In-Memory Buffering:** `TraceRecorder` buffers transitions for the current day ($t \in [k \cdot 288, (k+1) \cdot 288 - 1]$).
2. **Staged Binary Write:** At step $t = (k+1) \cdot 288 - 1$, write the chunk to a temporary file:
   `chunks/chunk_000k.npz.tmp`
3. **OS-Level Persistence:** Flush the Python stream and call `os.fsync(fd)` on the temporary file to force physical write to non-volatile storage.
4. **Atomic Rename:** Atomically rename `chunk_000k.npz.tmp` to `chunk_000k.npz`. In Windows and POSIX, file renames within the same filesystem volume are atomic operations.
5. **Journaling in `chunks_manifest.json`:** Compute the SHA-256 of `chunk_000k.npz` and append an entry to `chunks_manifest.json`:
   ```json
   {
     "chunk_index": 0,
     "start_step": 0,
     "end_step": 287,
     "num_steps": 288,
     "sha256": "4a5b6c...",
     "committed_at": "2026-10-31T22:35:10.123456Z"
   }
   ```
6. **Recorder Failure Containment:** If any disk write, flush, fsync, or rename raises an exception, the recorder immediately raises `EvidenceCaptureError`. `SimulationRunner` catches this, immediately terminates the simulation, transitions `execution_status = FAILED`, sets `evidence_validity = INVALID`, and logs the error. The simulator is never permitted to continue running if the black-box recorder has failed.

#### Recovery & Incomplete Rollout Identification
* If a process crashes at step 4,210 (Day 15, step 178 of that day):
  * Chunks 0 through 13 (covering steps $0 \dots 4031$) are fully durable and verified in `chunks_manifest.json`.
  * The uncommitted partial chunk for Day 15 is either in memory (lost) or present as an orphaned `.tmp` file.
  * `trace.csv` contains streaming lines up to step 4,210.
  * On post-crash recovery, `ExperimentRegistry.recover_interrupted_runs()` identifies that `run_manifest.json` is still `RUNNING`, marks `execution_status = INCOMPLETE`, sets `actual_steps = 4032` (or 4210 from CSV), deletes any leftover `.tmp` files, and sets `evidence_validity = INVALID`.
  * The run can never be misidentified as `COMPLETE`.

---

## 5. Artifact Preservation and Reproducibility

### 5.1 Three Rigorous Degrees of Reproducibility

The Black Box explicitly distinguishes between three degrees of experiment reproducibility:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       REPRODUCIBILITY TAXONOMY                              │
│                                                                             │
│ Level 1: Diagnostic Inspectability (Static)                                 │
│ └── Complete post-hoc inspection of all inputs, decisions, transitions,     │
│     and rewards without executing any code. Supported by trace.csv and      │
│     chunks/*.npz.                                                           │
│                                                                             │
│ Level 2: Deterministic Replay (Dynamic)                                     │
│ └── Re-executing policy_snapshot.py in the same virtual environment with     │
│     pinned random seed produces bitwise identical actions and scores        │
│     (variance = 0.0).                                                       │
│                                                                             │
│ Level 3: Compatible Environment Re-execution (Long-Term)                    │
│ └── Reconstructing and running the policy months later on a new machine      │
│     using preserved source dependencies, lockfiles, and starter-kit commits. │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 5.2 Minimal Complete Artifact Manifest (`artifact_manifest.json`)
Copying a single `policy_snapshot.py` is insufficient if the policy imports helper modules, loads neural network weights, or depends on specific configuration parameters.

Before episode execution, `SimulationRunner` constructs `run_dir/artifacts/` and populates `artifact_manifest.json`:

```json
{
  "project_git_commit": "00c911a270af3bdbc52dc1e16c9d3e6c139cb175",
  "starter_kit_commit": "95cea5b1c57b5291f44baf0283e0a081d53f5b16",
  "python_version": "3.12.13",
  "runtime_packages": {
    "numpy": "1.26.4",
    "pandas": "2.2.2",
    "scipy": "1.13.1",
    "gymnasium": "0.29.1",
    "gin-config": "0.5.0"
  },
  "artifacts": [
    {
      "role": "policy_entrypoint",
      "source_path": "smart_buildings/baselines/transfer_policy.py",
      "stored_path": "artifacts/transfer_policy.py",
      "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    },
    {
      "role": "scenario_config",
      "source_path": "smart_buildings/training_scenarios/building_train_1/atlanta_2/config.gin",
      "stored_path": "artifacts/config.gin",
      "sha256": "7a8b9c..."
    },
    {
      "role": "model_weights",
      "source_path": null,
      "stored_path": null,
      "sha256": null
    }
  ]
}
```

* **Local Dependency Resolution:** The runner inspects `sys.modules` for any module whose file path resides within the local workspace repository (excluding third-party site-packages) and copies it into `run_dir/artifacts/local_deps/`.
* **Immutability Assurance:** `artifact_manifest.json` records SHA-256 hashes of every stored file. Any subsequent tampering or refactoring of the repository code leaves the historical run fully executable from its frozen snapshot.

---

## 6. Execution Status versus Evidence Validity

Historical execution facts must never be destroyed or rewritten by subsequent governance actions. If a run ran 8,640 steps, it is an immutable historical fact that it executed to completion. If its upstream baseline is later found to have had an incorrect weather schedule, the run did not "fail" execution—rather, its comparative scientific eligibility is quarantined.

We formalize two completely separate state machines:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      TWO-TIER GOVERNANCE STATE MODEL                        │
│                                                                             │
│  1. Physical Execution Status (RunStatus)                                   │
│                                                                             │
│        INITIALIZED ──> RUNNING ──┬──> COMPLETE                              │
│                                  ├──> INCOMPLETE                            │
│                                  └──> FAILED                                │
│                                                                             │
│  2. Scientific Evidence Validity (EvidenceValidity)                         │
│                                                                             │
│        UNVERIFIED  ──┬──> VALID ──┬──> QUARANTINED                          │
│                      │            └──> INVALID                              │
│                      └──> INVALID                                           │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 6.1 State Definitions

#### Physical Execution Status (`RunStatus`)
1. **`INITIALIZED`**: Directory created, manifest written, simulation not yet started.
2. **`RUNNING`**: Active step execution in progress.
3. **`COMPLETE`**: Clean termination after completing all 8,640 scheduled steps.
4. **`INCOMPLETE`**: Simulation stopped cleanly but before step 8,640 (e.g. timeout, intentional early stop).
5. **`FAILED`**: Unhandled exception, process crash, or evidence recorder failure.
6. **`COMPLETE_NOT_ELIGIBLE`**: Completed 8,640 steps, but executed on an exploratory or dev suite rather than a candidate selection suite.

#### Evidence Validity & Eligibility (`EvidenceValidity`)
1. **`UNVERIFIED`**: Default initial state prior to independent audit.
2. **`VALID`**: Passed all cryptographic hash checks, tensor dimension audits, finite value checks, and score arithmetic verifications. Eligible for comparison and leaderboard ranking.
3. **`INVALID`**: Corrupted file headers, NaN/Inf values, step index discontinuity, or reward arithmetic failure. Permanently ineligible for comparison.
4. **`QUARANTINED`**: The run executed cleanly (`COMPLETE`), but an upstream dependency (baseline run, scenario config, or evaluator code) was subsequently found defective.

### 6.2 State Transition Matrix and Quarantine Cascade
* A run with `execution_status == COMPLETE` can transition between `VALID` and `QUARANTINED` without mutating `execution_status`.
* When a run is quarantined, its `quarantine_history` array is appended:
  ```json
  "quarantine_history": [
    {
      "timestamp": "2026-10-31T22:40:00Z",
      "action": "QUARANTINE_APPLIED",
      "reason": "Upstream baseline RUN_BASE_001 invalidated due to corrupted weather series",
      "taint_source": "RUN_BASE_001",
      "propagated_from": "COMP_REP_001"
    }
  ]
  ```
* **Restoration of Eligibility:** If the upstream defect is investigated and formally cleared (or the run is re-evaluated against a corrected baseline), `evidence_validity` can be updated back to `VALID` with an explanatory entry appended to `quarantine_history`.

---

## 7. Transitive Dependency Lineage

### 7.1 Typed Dependency Graph Data Model
A flat `parent_run_id` cannot capture complex experiment relationships. In `run_manifest.json`, we introduce a structured `dependencies` graph:

```json
"dependencies": [
  {
    "type": "baseline_comparator",
    "target_id": "RUN_BASE_fixed_setpoint_building_train_1_atlanta_2",
    "role": "control_group",
    "required": true
  },
  {
    "type": "policy_artifact",
    "target_id": "POLICY_transfer_v1_sha256_e3b0c44...",
    "role": "controller_implementation",
    "required": true
  },
  {
    "type": "environment_config",
    "target_id": "GIN_building_train_1_atlanta_2_sha256_7a8b...",
    "role": "scenario_definition",
    "required": true
  },
  {
    "type": "training_checkpoint",
    "target_id": "CKPT_ppo_step_500000",
    "role": "model_weights",
    "required": false
  }
]
```

In `comparison_report.json`:
```json
"dependencies": [
  {"type": "candidate_run", "target_id": "RUN_CANDIDATE_B", "required": true},
  {"type": "baseline_run", "target_id": "RUN_BASELINE_A", "required": true}
]
```

### 7.2 Downstream Traversal & Selective Quarantine Propagation

Consider the canonical dependency chain:
$$\text{Baseline A} \longrightarrow \text{Candidate B} \longrightarrow \text{Candidate C} \longrightarrow \text{Comparison D} \longrightarrow \text{Conclusion E}$$

When **Baseline A** is found defective and quarantined via `ExperimentRegistry.quarantine_run(run_id="Baseline_A", reason=...)`:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     SELECTIVE PROPAGATION LOGIC                             │
│                                                                             │
│  Baseline A [QUARANTINED]                                                   │
│      │                                                                      │
│      ├──> Candidate B: Raw data remains historically intact. Standalone     │
│      │    comfort metrics remain VALID. Relative comparison to A is revoked.│
│      │                                                                      │
│      ├──> Candidate C: If C only used B's architectural idea, C remains     │
│      │    VALID. If C used weights initialized from B, flagged for REVIEW.  │
│      │                                                                      │
│      ├──> Comparison D: Directly compares B against A.                      │
│      │    Strictly invalidated ──> [QUARANTINED].                           │
│      │                                                                      │
│      └──> Conclusion E: Leaderboard claim citing Comparison D.              │
│           Strictly revoked ──> [REVOKED_UPSTREAM_DEFECT].                   │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Propagation Rules
1. **Rule 1 (Comparative Dependence):** Any comparison report or promotion decision that directly takes the quarantined artifact as a comparator input is immediately marked `QUARANTINED`.
2. **Rule 2 (Standalone Execution Data):** The physical rollout of Candidate B remains valid for non-comparative purposes (e.g. diagnosing how many kWh were consumed, checking whether temperatures stayed inside the deadband). Its `execution_status` remains `COMPLETE`.
3. **Rule 3 (No Historical Rewriting):** Manifests, traces, and comparison reports are never deleted from disk. Their eligibility status is revoked, ensuring complete auditability.
4. **Rule 4 (Containment):** Unrelated runs (e.g. Candidate F evaluated against Baseline Z) are completely unaffected.

---

## 8. Independent Evidence Verification

The evidence recorder must never certify its own data. Verification is performed by `ScoreVerifier` and `DiagnosticsEngine`, operating as an independent audit engine.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      INDEPENDENT VERIFICATION PIPELINE                      │
│                                                                             │
│  run_dir Evidence ──> [ ScoreVerifier.verify_run_integrity(run_dir) ]       │
│                             │                                               │
│       ├── 1. Provenance Audit: project_commit != starter_kit_commit         │
│       ├── 2. Artifact Audit: SHA-256 of all files match manifest            │
│       ├── 3. Chunk Continuity: chunks 0..N exist, monotonic steps           │
│       ├── 4. Dimension Audit: obs & actions match building metadata         │
│       ├── 5. Finite Value Audit: 0 NaNs, 0 Infs across all tensors          │
│       ├── 6. Component Audit: prod_regret, energy, carbon != 0.0            │
│       ├── 7. Arithmetic Audit: R = 0.6*regret - 0.2*energy - 0.2*carbon     │
│       └── 8. Parity Audit: sum(step_reward) == cumulative_reward to 1e-6    │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 8.1 Verification Checks by Phase

| Check Phase | Timing | Audit Target | Failure Condition | Action on Failure |
| :--- | :--- | :--- | :--- | :--- |
| **Runtime Check** | Step 0 | Component parity | $|R_0 - (0.6 \cdot r_0 - 0.2 \cdot e_0 - 0.2 \cdot c_0)| > 10^{-6}$ | Halt run; `FAILED` |
| **Runtime Check** | Each Step | Array bounds & finite values | Any NaN/Inf in action or observation | Halt run; `FAILED` |
| **Runtime Check** | Chunk Commit | Staged chunk write | Hash mismatch or rename failure | Halt run; `FAILED` |
| **Post-Run Audit** | Post-Run | Artifact hashes | `sha256(file) != manifest.hashes[file]` | Set `INVALID` |
| **Post-Run Audit** | Post-Run | Chunk sequence continuity | Missing chunk, gap in step index, duplicate chunk | Set `INVALID` |
| **Post-Run Audit** | Post-Run | Tensor dimensions | `obs.shape != (N, obs_dim)` or `act.shape != (N, cont_dim)` | Set `INVALID` |
| **Post-Run Audit** | Post-Run | Reward arithmetic | Step discrepancy $> 10^{-6}$ on any of 8,640 steps | Set `INVALID` |
| **Post-Run Audit** | Post-Run | Return parity | $|\sum R_t - \text{summary.cumulative\_reward}| > 10^{-6}$ | Set `INVALID` |
| **Post-Run Audit** | Post-Run | Finalization evidence | Missing `summary.json` or `chunks_manifest.json` | Set `INCOMPLETE` |

---

## 9. Layered Information-Leakage Protection

AST analysis of policy source code is necessary but insufficient on its own (policies could access globals, inspect runtime stack frames, or modify observation buffers in-place). We implement a **Four-Ring Defense Model**:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                   FOUR-RING LEAKAGE DEFENSE ARCHITECTURE                    │
│                                                                             │
│  [ Ring 1: Strict Input Boundary ]                                          │
│  └── Policy receives ONLY obs array and sanitized metadata. env is private. │
│                                                                             │
│  [ Ring 2: Static AST & Dependency Inspection ]                             │
│  └── Parse policy AST; reject smart_control.simulator, ctypes, inspect.     │
│                                                                             │
│  [ Ring 3: Runtime Memory Immutability ]                                    │
│  └── Set obs.flags.writeable = False; deepcopy metadata.                    │
│                                                                             │
│  [ Ring 4: Empirical Red Team Probes ]                                      │
│  └── Execute deliberate leakage attacks (stack crawl, weather file read).    │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Ring 1: Strict Input Boundary
* `SimulationRunner` holds the `env` instance strictly in local scope; it is never passed to `PolicyAdapter` or `policy_instance`.
* The policy's `get_action(obs)` method receives only the NumPy observation vector.
* `metadata` passed during initialization contains only public scenario parameters (schedules, zone indices, dimensions); all environment pointers are excluded.

### Ring 2: Static AST & Dependency Inspection
* Prior to instantiating the policy, `PolicyAdapter` parses the AST of `policy_snapshot.py` and all local dependency modules.
* Disallowed AST nodes and imports:
  * Prohibited modules: `smart_buildings.smart_control`, `smart_buildings.evaluate`, `ctypes`, `subprocess`, `multiprocessing`.
  * Prohibited attributes: `sys._getframe`, `gc.get_objects`.
  * Prohibited file I/O: Open calls targeting scenario directories or weather CSVs.
* Any violation triggers an immediate rejection during initialization (`INITIALIZED -> FAILED`).

### Ring 3: Runtime Memory Immutability
* **Read-Only Observation Vectors:** Before passing `obs` to `policy.get_action(obs)`, `PolicyAdapter` sets:
  ```python
  obs.flags.writeable = False
  ```
  This prevents malicious or buggy policies from altering observation tensors in-place to tamper with subsequent recorder logging.
* **Metadata Immutability:** `metadata` dictionary is deep-copied or wrapped in `types.MappingProxyType` to prevent in-place mutation.

### Ring 4: Empirical Leakage Probes (Red Team F3)
* Controlled unit tests deliberately attempt to bypass the sandbox (e.g. attempting to crawl `inspect.currentframe().f_back` to access `env`).
* The test verifies that the runner detects or blocks the vector and aborts the run.

---

## 10. Controlled Semantic Mapping Probes

### 10.1 The Semantic Problem: Why Trajectory Correlation Fails
In a building with 39 to 85 zones, adjacent zones share thermal boundaries. If Zone 1 reheat is commanded to maximum, heat slowly conducts through interior drywall into Zone 2. Passive observational trajectories will show positive correlation between Zone 1 setpoints and Zone 2 temperatures. Passive correlation cannot prove that Zone 1 setpoint controls Zone 1!

### 10.2 Authoritative Interface Sources
The authoritative ground truth for feature and actuator indexing is established by:
1. `metadata["observation_field_names"]`: Canonical mapping of each index $i \in [0 \dots D_{\text{obs}}-1]$ to its physical measurement name (e.g. `"ahs_ahu_1_supply_air_temperature"`, `"zone_1_air_temperature"`).
2. `metadata["zone_temp_indices"]`: Exact observation indices corresponding to zone air temperatures.
3. `metadata["zone_action_indices"]`: Dictionary mapping each VAV ID (`"VAV_1"`, `"VAV_2"`, ...) to its continuous action vector indices `[damper_index, reheat_index]`.
4. `env.action_fields_map`: Authoritative bidict mapping `(device_code, setpoint_name)` to continuous/discrete vector indices.

### 10.3 Controlled Interventional Actuator Probe
To verify actuator semantic mapping with mathematical certainty, the platform defines a **Single-Variable Pulse Intervention Protocol**:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                 CONTROLLED INTERVENTIONAL ACTUATOR PROBE                    │
│                                                                             │
│ 1. Initialize scenario to frozen initial condition.                         │
│ 2. Command all actuators to neutral baseline values.                        │
│ 3. Apply a step pulse perturbation ONLY to actuator channel k:              │
│    Command VAV_1 reheat setpoint to +1.0 (maximum heating).                 │
│    Hold all other 91 continuous actuators strictly constant at -1.0.        │
│ 4. Step the simulator for T_probe = 4 steps (20 minutes).                   │
│ 5. Measure physical response:                                               │
│    ΔT_zone_1 = T_zone_1(t=4) - T_zone_1(t=0)                               │
│    ΔT_zone_j = T_zone_j(t=4) - T_zone_j(t=0) for all j != 1                │
│ 6. Verification Criterion:                                                  │
│    ΔT_zone_1 > 0.5 K AND ΔT_zone_1 > max_{j != 1} (ΔT_zone_j) + 0.3 K      │
└─────────────────────────────────────────────────────────────────────────────┘
```

* **Outcome:** If Zone 2 experiences the immediate temperature rise while Zone 1 remains cold, the actuator channels are proven to be swapped (Red Team F1 detection).
* **Versioning:** Results are stored in `semantic_probe_report.json` (schema `v1.0`).

---

## 11. Storage and Performance Benchmark Plan

### 11.1 Empirical Dimension Matrix Across Competition Buildings

Inspection of actual `config.gin` and building models across the official benchmark suite reveals the true diversity of dimensions:

| Building Name | Discrete Actions ($D_{\text{disc}}$) | Continuous Actions ($D_{\text{cont}}$) | Observation Vector ($D_{\text{obs}}$) | Thermal Zones ($N_{\text{zones}}$) | Bytes per Step (Uncompressed) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `building_train_8` (Smallest) | 4 | 71 | 283 | 30 | 1,836 B |
| `building_train_7` | 5 | 86 | 334 | 36 | 2,188 B |
| `building_train_1` (Reference) | 5 | 92 | 352 | 39 | 2,320 B |
| `building_train_4` | 7 | 128 | 472 | 54 | 3,144 B |
| `building_train_5` | 9 | 184 | 652 | 79 | 4,356 B |
| `building_train_2` (Largest) | 10 | 199 | 703 | 85 | 4,784 B |

*(Per-step byte calculation: $[D_{\text{obs}} + 2 \cdot D_{\text{cont}} + D_{\text{disc}} + N_{\text{zones}}] \times 4\text{ bytes}$. Continuous actions are counted twice to record both unclipped raw actions and executed clipped actions).*

### 11.2 Storage Calculations & Estimates
* **Uncompressed Storage per 8,640-Step Episode:**
  * Smallest (`building_train_8`): $8,640 \times 1,836\text{ B} = 15,863,040\text{ B} \approx \mathbf{15.13\text{ MB}}$.
  * Reference (`building_train_1`): $8,640 \times 2,320\text{ B} = 20,044,800\text{ B} \approx \mathbf{19.12\text{ MB}}$.
  * Largest (`building_train_2`): $8,640 \times 4,784\text{ B} = 41,333,760\text{ B} \approx \mathbf{39.42\text{ MB}}$.
  * Weighted average across 30 scenarios: $\approx \mathbf{24.2\text{ MB}}$ uncompressed per episode.
* **Compressed Storage Estimates (`chunks/*.npz`):**
  * *Notice: Compression ratios are estimated based on HVAC data characteristics (repetitive diurnal patterns, nocturnal setbacks, constant setpoints). Actual values will be measured in the benchmark protocol below.*
  * Estimated compression ratio: $4.0\times - 6.5\times$.
  * Estimated compressed size per episode: $\approx \mathbf{3.7 - 6.0\text{ MB}}$.
* **Campaign Storage Estimates (30 Scenarios):**
  * Total uncompressed: $\approx \mathbf{725\text{ MB}}$.
  * Total compressed: $\approx \mathbf{110 - 180\text{ MB}}$.
* **Duplication between `trace.csv` and `chunks/*.npz`:**
  * `trace.csv` stores 15 summary columns ($\approx 850\text{ KB}$ per episode). It records scalar sums and means, not the raw multi-dimensional vectors. Vector data is stored exclusively in `chunks/*.npz`.

### 11.3 Performance Benchmark Protocol
During Stage 3 Task 1, we will execute an automated benchmark script (`benchmark_storage_performance.py`) measuring:
1. **Serialization Latency:** Time required to execute `np.savez_compressed` and `os.fsync` per 288-step chunk.
   * *Proposed Engineering Threshold:* $< 50\text{ ms}$ per daily chunk.
2. **Total Runtime Overhead:** Percentage execution time added by Black Box instrumentation over uninstrumented rollouts.
   * *Proposed Engineering Threshold:* $< 3.0\%$ total wall-clock simulation overhead.
3. **Peak Memory Consumption:** Additional RAM retained by in-memory chunk buffers.
   * *Proposed Engineering Threshold:* $< 30\text{ MB}$ peak memory.

---

## 12. Red Team Readiness Mapping

| Attack ID & Name | Required Black Box Capability | Primary Detection Mechanism | Independent Verification Mechanism | Evidence Preserved for Diagnosis | Quarantine & Lineage Implications |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **F1: Semantic Mapping Error** (e.g. Swapped zone setpoints) | Full continuous action array `(N, D_cont)` and zone temperatures `(N, n_zones)`. | `PolicyAdapter` metadata validation and single-variable pulse probe. | `DiagnosticsEngine` interventional thermal response audit. | Command vs. response trajectories in `chunks/*.npz`; `semantic_probe_report.json`. | Run marked `INVALID`. Any candidate using this policy mapping is quarantined. |
| **F2: Reward Calculation Error** (e.g. Inverted penalty sign) | Full step-level component capture (`normalized_productivity_regret`, energy, carbon). | Runtime step 0 parity check in `SimulationRunner`. | `ScoreVerifier.verify_reward_arithmetic` across all 8,640 steps. | Columnar components in `trace.csv`; discrepancy report isolating step and component. | Run marked `INVALID`. Any comparison report referencing the run is quarantined. |
| **F3: Information Leakage** (e.g. Reading future weather / simulator) | Static AST analysis, read-only buffer enforcement, input boundary. | AST import parser in `PolicyAdapter` and restricted scope in runner. | `SuiteValidator` holdout overlap audit; empirical Red Team leakage probes. | `artifact_manifest.json` with frozen policy source code and dependency hashes. | Run marked `FAILED` at initialization. Entire policy family quarantined. |
| **F4: Incomplete Rollout Claimed Complete** (e.g. 8,639 steps) | Monotonic step indexing, chunk manifest line count, atomic finalization. | `SimulationRunner` step count guard. | `ScoreVerifier.verify_trace_and_score` and chunk manifest validator. | `chunks_manifest.json` showing incomplete daily chunk; `actual_steps < 8640`. | Run permanently assigned `INCOMPLETE` and `INVALID`. Excluded from comparisons. |
| **F5: Missing Deployment Artifact** (e.g. Missing weights or config) | Complete artifact bundle in `run_dir/artifacts/` and manifest hash seal. | Pre-execution artifact validator in `SimulationRunner`. | `ComparisonValidator` packaging and cryptographic integrity audit. | `artifact_manifest.json` indicating missing file path or SHA-256 mismatch. | Run marked `FAILED` prior to step 0. Disallowed from leaderboard promotion. |

---

## 13. Exact Implementation Map

| Target File | Current Behavior | Proposed Behavior | Evidence Produced | Dependencies | Tests | Priority |
| :--- | :--- | :--- | :--- | :--- | :--- | :---: |
| [`04_EXPERIMENT_FOUNDATION/core/runner.py`](file:///04_EXPERIMENT_FOUNDATION/core/runner.py#L117) | Calls `getattr(env, "_productivity_regret", 0.0)`, silently yielding `0.0`. | Call `env.get_reward_info_and_response()`, verify step 0 arithmetic, raise exception if `None`. | True physical components in trace; step 0 parity check. | None | `test_reward_extraction` | **CRITICAL** |
| [`04_EXPERIMENT_FOUNDATION/core/runner.py`](file:///04_EXPERIMENT_FOUNDATION/core/runner.py#L55) | Only hashes policy file; does not snapshot artifacts. | Build `artifacts/` folder, copy policy + local deps, generate `artifact_manifest.json`. | `artifact_manifest.json` + physical frozen `.py` files. | None | `test_artifact_preservation` | **CRITICAL** |
| [`04_EXPERIMENT_FOUNDATION/core/trace_recorder.py`](file:///04_EXPERIMENT_FOUNDATION/core/trace_recorder.py#L58) | Flushes scalar CSV; discards full observation vectors. | Implement 288-step daily chunking, atomic `.tmp` rename, `os.fsync`, and `chunks_manifest.json`. | `chunks/chunk_*.npz` + `chunks_manifest.json`. | Dynamic schemas | `test_chunked_persistence` | **CRITICAL** |
| [`04_EXPERIMENT_FOUNDATION/core/policy_adapter.py`](file:///04_EXPERIMENT_FOUNDATION/core/policy_adapter.py#L81) | Discards raw unclipped actions; no observation bounds check. | Store `raw_continuous_action`, measure latency ms, set `obs.flags.writeable = False`. | Raw vs. executed actions in chunks; latency stats. | None | `test_adapter_action_capture` | **HIGH** |
| [`04_EXPERIMENT_FOUNDATION/core/policy_adapter.py`](file:///04_EXPERIMENT_FOUNDATION/core/policy_adapter.py#L49) | No static inspection of policy imports. | Parse policy AST; reject forbidden imports (`smart_control.simulator`, `ctypes`). | AST rejection log in manifest. | None | `test_static_leakage_guard` | **HIGH** |
| [`04_EXPERIMENT_FOUNDATION/core/registry.py`](file:///04_EXPERIMENT_FOUNDATION/core/registry.py#L16) | Conflates execution status with validity in `RunStatus`. | Decouple `RunStatus` and `EvidenceValidity`; add `quarantine_run()` cascade. | `evidence_validity` field & `quarantine_history` log. | None | `test_quarantine_cascade` | **HIGH** |
| [`04_EXPERIMENT_FOUNDATION/evaluation/score_verification.py`](file:///04_EXPERIMENT_FOUNDATION/evaluation/score_verification.py#L45) | Only checks CSV reward sum; does not check chunk continuity. | Audit `chunks_manifest.json`, verify array shapes against metadata, check 0 NaNs/Infs. | Comprehensive integrity section in `evaluation.json`. | Trace recorder | `test_independent_integrity` | **HIGH** |
| `04_EXPERIMENT_FOUNDATION/core/campaign_evaluator.py` | Does not exist; comparisons run only via synthetic unit mocks. | Batch orchestrator aggregating 30 scenario runs into `comparison_report.json`. | `campaigns/<id>/comparison_report.json`. | Runner, Registry | `test_campaign_orchestration` | **MEDIUM** |

---

## 14. Dependency-Aware Implementation Sequence

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                   STAGE 3 IMPLEMENTATION SEQUENCE & GATES                   │
│                                                                             │
│   Gate 1: Reward & Schema Correctness (runner.py)                           │
│   ├── Step 1.1: Fix get_reward_info_and_response() extraction               │
│   ├── Step 1.2: Add step 0 arithmetic assertion                             │
│   └── Verification: 5-step test proves non-zero reward components           │
│           │                                                                 │
│           ▼                                                                 │
│   Gate 2: Durable Incremental Chunk Persistence (trace_recorder.py)         │
│   ├── Step 2.1: Implement 288-step daily chunk buffer                       │
│   ├── Step 2.2: Implement atomic .tmp staging, os.fsync, and rename         │
│   ├── Step 2.3: Generate chunks_manifest.json with SHA-256 hashes           │
│   └── Verification: Simulated crash at step 350 preserves Day 1 chunk       │
│           │                                                                 │
│           ▼                                                                 │
│   Gate 3: Artifact Preservation (runner.py & registry.py)                   │
│   ├── Step 3.1: Copy policy and workspace dependencies to artifacts/        │
│   ├── Step 3.2: Write artifact_manifest.json with git commits and hashes    │
│   └── Verification: Replay succeeds using only artifacts/ directory         │
│           │                                                                 │
│           ▼                                                                 │
│   Gate 4: Decoupled State Machine & Lineage (registry.py)                   │
│   ├── Step 4.1: Separate RunStatus and EvidenceValidity enums               │
│   ├── Step 4.2: Add typed dependencies array to manifest schema             │
│   ├── Step 4.3: Implement quarantine_run() downstream cascade               │
│   └── Verification: Quarantining baseline revokes comparison report         │
│           │                                                                 │
│           ▼                                                                 │
│   Gate 5: Leakage & Semantic Probes (policy_adapter.py)                     │
│   ├── Step 5.1: Set obs.flags.writeable = False                             │
│   ├── Step 5.2: Implement AST import parser for prohibited modules          │
│   └── Verification: Red Team F1 and F3 probes trigger clean rejections      │
│           │                                                                 │
│           ▼                                                                 │
│   Gate 6: Independent Verification Engine (score_verification.py)           │
│   ├── Step 6.1: Audit chunk manifest continuity and SHA-256 hashes          │
│   ├── Step 6.2: Validate dynamic array dimensions and finite values         │
│   └── Verification: All 19 acceptance criteria pass; 46 legacy tests green  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 15. Acceptance Criteria for Future Implementation

The implementation in Stage 3 must pass the following 19 concrete acceptance tests:

1. **Complete Diagnostic Evidence Generation:** A completed 8,640-step episode produces `trace.csv`, 30 daily chunks (`chunk_0000.npz` to `chunk_0029.npz`), `chunks_manifest.json`, `run_manifest.json`, `artifact_manifest.json`, `summary.json`, and `evaluation.json`.
   * *Proof:* Assert all files exist and are non-empty.
2. **Transition Recovery:** Selecting any arbitrary step $t \in [0, 8639]$ from the corresponding chunk recovers the exact unreduced observation vector, raw action, executed action, and zone temperature vector.
   * *Proof:* Assert array shapes match building metadata and values equal recorded step state.
3. **Reward Component Capture:** `trace.csv` records non-zero values for `productivity_regret`, `energy_cost`, and `carbon_penalty`.
   * *Proof:* Assert `abs(df["productivity_regret"].sum()) > 0.0`.
4. **Independent Reward Reconstruction:** `ScoreVerifier.verify_reward_arithmetic` validates that for all 8,640 steps:
   $$|R_t - (0.6 \cdot \text{regret}_t - 0.2 \cdot \text{energy}_t - 0.2 \cdot \text{carbon}_t)| \le 1.0 \times 10^{-6}$$
   * *Proof:* Assert discrepancy array maximum $\le 10^{-6}$.
5. **Rejection of Missing Reward Info:** If the environment returns `None` for `RewardResponse`, `SimulationRunner` raises `EvidenceCaptureError` rather than defaulting to `0.0`.
   * *Proof:* Test fixture injecting `None` raises error and halts.
6. **Crash-Resilient Chunk Persistence:** Simulating a process kill at step 400 leaves Day 1 (`chunk_0000.npz`, steps $0 \dots 287$) fully readable, uncorrupted, and verified on disk.
   * *Proof:* Load `chunk_0000.npz` with `np.load()`; assert length equals 288.
7. **Exclusion of Incomplete Final Batch:** After an interrupted run, orphaned `.tmp` chunks are excluded from `chunks_manifest.json`.
   * *Proof:* Assert `chunks_manifest.json` contains only fully committed chunks.
8. **Artifact Preservation & Frozen Execution:** A completed run contains `run_dir/artifacts/` preserving the policy source and local dependencies. Executing the policy from `artifacts/` reproduces the historical rollout.
   * *Proof:* Import policy directly from `artifacts/` in a fresh subprocess; verify identical output.
9. **Separate Commit Provenance:** `run_manifest.json` and `artifact_manifest.json` record `project_git_commit` (`00c911a...`) and `starter_kit_commit` (`95cea5b...`) in separate fields.
   * *Proof:* Assert `manifest["project_git_commit"] != manifest["starter_kit_commit"]`.
10. **Decoupled Status Preservation:** Quarantining a completed run updates `evidence_validity = QUARANTINED` while leaving `execution_status = COMPLETE`.
    * *Proof:* Assert `manifest["execution_status"] == "COMPLETE"` and `manifest["evidence_validity"] == "QUARANTINED"`.
11. **Transitive Lineage Traversal:** Invoking `quarantine_run("Baseline_A")` automatically identifies and quarantines Candidate B and Comparison Report D.
    * *Proof:* Assert downstream manifests in `experiments/runs/` reflect `QUARANTINED` status.
12. **Containment of Unrelated Results:** An unrelated run (Candidate F evaluated against Baseline Z) is unaffected by the quarantine of Baseline A.
    * *Proof:* Assert Candidate F retains `evidence_validity == "VALID"`.
13. **Clean Control Invariance:** The existing certified reference run (`RUN_EXP-000_vertical_slice_certified`) continues to pass all audits.
    * *Proof:* Run `pytest 04_EXPERIMENT_FOUNDATION/tests`; all 46 existing tests pass.
14. **Chunk Anomaly Detection:** Corrupting, deleting, duplicating, or reordering a chunk in `chunks/` causes `ScoreVerifier` to flag the run as `INVALID`.
    * *Proof:* Test fixtures for corrupted header, missing chunk, and duplicated chunk raise validation failures.
15. **Empirical Leakage Rejection (Red Team F3):** A policy attempting to import `smart_buildings.smart_control.simulator` or inspect `inspect.currentframe().f_back` is rejected during initialization.
    * *Proof:* `PolicyAdapter` raises `SecurityViolationError`; run marked `FAILED`.
16. **Interventional Semantic Probe (Red Team F1):** A controlled single-actuator pulse on VAV 1 reheat causes a measured thermal rise in Zone 1 ($\Delta T > 0.5\text{ K}$) and confirms actuator mapping.
    * *Proof:* Assert `semantic_probe_report.json` passes threshold criteria.
17. **Storage Failure Detection:** Simulating a disk write failure during chunk commit raises `EvidenceCaptureError` and marks the run `FAILED` immediately.
    * *Proof:* Mocking `os.fsync` to raise `OSError` halts runner and prevents `COMPLETE` status.
18. **Measured Performance Overhead:** Automated benchmark script verifies serialization latency $< 50\text{ ms}$ per chunk and total simulation overhead $< 3.0\%$.
    * *Proof:* Assert benchmark log metrics fall within specified budgets.
19. **Independent Investigator Explainability:** A standalone inspection script given only `run_dir` can reconstruct the full episode timeline, comfort violations, energy costs, and policy setpoints without referencing outside code.
    * *Proof:* Run standalone audit script on `run_dir`; output complete diagnostic summary.

---

## 16. Remaining Limitations and Unresolved Decisions

1. **Process Sandboxing Boundary:** On local developer machines, pure Python execution cannot completely guarantee isolation against low-level C-extension exploits or compiled binary tampering. Ring 1 (strict boundary), Ring 2 (AST parsing), and Ring 3 (read-only arrays) provide robust operational isolation for competition policy development, but final untrusted evaluation relies on Kaggle's remote containerized environment.
2. **Chunk Size Tuning:** `chunk_size = 288` (1 day) is the recommended default. For shorter diagnostic runs (e.g. 5-step smoke tests), the recorder flushes a final partial chunk upon normal termination.

---

## 17. Recommended First Implementation Task

Proceed directly to **Phase 05 — Stage 3: Task 1 (Core Pipeline & Reward Extraction Upgrade)**:
1. In [`04_EXPERIMENT_FOUNDATION/core/runner.py`](file:///04_EXPERIMENT_FOUNDATION/core/runner.py):
   * Replace `getattr(env, "_productivity_regret", 0.0)` with `env.get_reward_info_and_response()`.
   * Add step 0 arithmetic consistency assertion.
   * Implement `run_dir/artifacts/` creation and `artifact_manifest.json` generation.
2. In [`04_EXPERIMENT_FOUNDATION/core/trace_recorder.py`](file:///04_EXPERIMENT_FOUNDATION/core/trace_recorder.py):
   * Implement 288-step daily chunking with atomic staging (`.tmp`), `os.fsync`, and atomic rename.
   * Output `chunks/chunk_000k.npz` and `chunks_manifest.json`.
3. Verify with a 5-step test episode to confirm non-zero reward components and chunk creation.
