# Smart Buildings Research & Control Platform

**Implementation blueprint | Version 2.0 | 22 October 2026**  
**Status:** Approved design direction; implementation and individual competition-contract claims remain subject to their specified evidence gates.  
**Supersedes:** *Kaggle Research Platform — Implementation Reference v1.0* (21 October 2026). Original retained for decision history.

> **Operating promise.** A control idea may fail. The platform must make invalid information access, incorrect execution, false evaluation, cascading defects, fragile generalization, and unsafe promotion difficult to hide. Failures are reproduced and isolated; invalid evidence is quarantined. No internal protocol can guarantee hidden-test success.

## How to read and use this blueprint

This is a **how-to-build and how-to-operate reference**, not a claim that its components are already implemented. Start with the source-truth gate and minimum viable vertical slice (§§2, 15). The independent Evaluation Authority decides what a result demonstrates; the Red Team challenges claims; Failure Engineering detects, contains, isolates, and closes defects. Implement only the next gated capability, not an elaborate platform upfront.

**Terminology:** *verified* = supported by checked artifact/test; *proposed* = agreed design not yet implemented; *provisional* = competition-specific statement still requiring version-specific verification; *blocked* = cannot proceed safely. An artifact hash establishes identity, not semantic correctness.

## Contents

1. [What changed and what stays](#1-what-changed-and-what-stays)  
2. [Mission and competition contract](#2-mission-and-competition-contract)  
3. [Architecture and authority boundaries](#3-architecture-and-authority-boundaries)  
4. [Project workspace and canonical records](#4-project-workspace-and-canonical-records)  
5. [Source-truth and specification integrity](#5-source-truth-and-specification-integrity)  
6. [Environment partitioning and evaluation governance](#6-environment-partitioning-and-evaluation-governance)  
7. [Trusted experiment and observability foundation](#7-trusted-experiment-and-observability-foundation)  
8. [Official scoring and independent success measurement](#8-official-scoring-and-independent-success-measurement)  
9. [Independent Red Team](#9-independent-red-team)  
10. [Failure Engineering System](#10-failure-engineering-system)  
11. [Experiment engine and controller-development lifecycle](#11-experiment-engine-and-controller-development-lifecycle)  
12. [Candidate portfolio and optional policy combinations](#12-candidate-portfolio-and-optional-policy-combinations)  
13. [Resource management, lineage, and recovery](#13-resource-management-lineage-and-recovery)  
14. [Release and submission engineering](#14-release-and-submission-engineering)  
15. [Implementation roadmap and acceptance gates](#15-implementation-roadmap-and-acceptance-gates)  
16. [Operating workflows and incident examples](#16-operating-workflows-and-incident-examples)  
17. [Decision policy, risks, and deferred capabilities](#17-decision-policy-risks-and-deferred-capabilities)  
[Appendices](#appendices)

---

## 1. What changed and what stays

The original blueprint's non-negotiable ideas—immutable evidence, independent evaluation, protected audit, red-team falsification, reproducibility, lineage, rollback, and certified fallback—remain. Its default assumption of a static Kaggle predictor does not.

| v1.0 element | v2.0 decision and reason |
|---|---|
| Model returns independent row predictions | **Replace:** participant submits one Python **control policy**; the simulator supplies observations and receives decisions repeatedly. |
| Rows, folds, OOF predictions | **Replace as the default:** full scenario episodes, building/configuration identities, weather-strip lineage, separate development/selection/protected suites. OOF applies only if a specific later modeling method actually needs it. |
| Input CSV / submission-file schema checks | **Replace:** constructor and `get_action(obs)` contract, metadata/field mapping, hybrid-action bounds, native-unit translation, runtime and clean-artifact tests. |
| Validation scalar or public LB score as primary evidence | **Expand:** independent official score **plus** per-scenario distribution, component diagnostics, operating failures, matched comparisons, and uncertainty at environment level. |
| Generic ML Red Team | **Rework:** source truth, policy information access, temporal leakage, building/weather memorization, action semantics, closed-loop drift, evaluator and release integrity. |
| Defects tracked within general lineage | **Elevate:** separate **Failure Engineering System (FES)** with detection, incident severity, trace/replay, fault isolation, blast-radius quarantine, repair and permanent regression checks. |
| Experiment registry, research journal, candidate portfolio | **Retain and adapt:** ideas → experiments → runs → approved policy candidates → optional policy combinations → releases. |
| Ensemble lab automatically in roadmap | **Defer as conditional:** policy combinations only when their state/action semantics and independent added value are established. |
| Original heavy platform rollout | **Retain vertical-slice principle:** build one end-to-end trusted loop first, then add controls in gated order. |

**Non-negotiable separation:** scientific failure (valid experiment, idea did not work) ≠ system failure (defect invalidates inference) ≠ operational failure (valid policy behaves badly under specified conditions) ≠ uncertainty (insufficient evidence). Do not relabel one as another to simplify reporting.

## 2. Mission and competition contract

### 2.1 The actual object we are building

The organizers provide a simulated commercial building population, historical weather inputs, HVAC physics, a participant policy interface, and an evaluator. **Our deliverable is a Python HVAC control policy**, potentially containing learned components, analytic logic, or both. It takes the building's permitted metadata at initialization, receives a live observation at each five-minute step, and returns HVAC commands. The submitted policy must work on new building instances and weather strips without a manually customized target-building version.

![Closed-loop control and evaluation.](assets/01_closed_loop.png)

The policy changes later observations through its earlier actions. Consequently, episodes—not individual observation rows—are the meaningful units of outcome. The simulator's internal state may be useful to authorized *diagnostic instrumentation*, but is not automatically lawful input to the deployed policy.

### 2.2 Verified starter-kit anchors; pin the version before use

The official starter-kit README and inspected code currently specify the following. Every build must pin and independently recheck its **local repository revision**, dependencies, competition rules, and generated environment; the version here is explanatory, not permission to skip the gate.

| Contract item | Current documented/inspected behaviour | Verification owner |
|---|---|---|
| Participant API | `TransferPolicy(building_meta_data, action_spec)`; `get_action(obs)` returns a dict with `continuous_action`, `discrete_action` | Source-Truth Authority |
| Hybrid action shapes | For `K` AHUs and `V` VAV/zone boxes: discrete `K+1`, continuous `3K+2+2V` | Interface tests for every shipped building and new test building |
| Action units | Continuous normalized `[-1,1]`, discrete `{0,1}`; use supplied index and normalization metadata rather than positional guesses | Action golden fixtures |
| Observation | Building-dependent field vector; derive indices from participant-facing field names; no station/building-ID label supplied as a policy feature | Metadata/schema inspection |
| Static metadata | Includes action indices, observation field names, AHU-zone assignment, `floor_plan`, `zone_map`, schedule and normalization metadata (when available in loaded scenario) | Inspect `evaluate.py::create_building_meta_data` |
| Time horizon | Five-minute decisions; full 30-day episode = 8,640 steps; no arbitrary shortened-episode comparison to official full score | Evaluator tests |
| Shipped development set | Manifest pairs six building instances with five weather-source families, giving 30 distinct scenarios; strips differ rather than being identical per station | Manifest audit |
| Policy evaluation | Per-step weighted comfort, cost and carbon; rewards nonpositive under valid operation; scenario results receive equal weight in final loss | Independent scorer |
| Important device semantics | Zero continuous action means physical midpoint, not off; actual AHU supply air is limited by its mixed-air temperature; ventilation floors enforced | End-to-end actuator probes |

**Do not infer hidden evaluation station novelty or exact climate distribution beyond the official contract.** A previously unused time strip and an entirely new station are different claims. The documented held-out buildings are generated from the same generator/ranges, but the six shipped buildings do not fully describe joint parameter coverage.

### 2.3 The corrected-source requirement

The uploaded Data Understanding Guide is useful orientation, **not an unquestionable source of implementation truth**. The pre-development audit must reconcile material conflicts before accepting the guide as a specification. Known examples already requiring correction or version-scoped clarification:

- The guide labels `floor_plan` and `zone_map` as strictly inaccessible, while the inspected `create_building_meta_data()` includes them in participant-facing metadata.
- The guide expresses comfort regret as occupancy divided by a fixed `125`; the inspected reward function normalizes by **actual total occupancy** when positive, and uses zero when unoccupied.
- The guide states exterior conductivity sampling up to `0.45 W/(m·K)`; the inspected `materials.py` declares `0.15–0.55` for the current revision.
- The guide contains a fixed observation-size decomposition that must be rederived from the actual `observation_field_names`, not promoted from prose alone; the official policy stub lists, for example, 271 observation values for one shipped building.
- Comfort schedules, action saturation/rejection behaviour, metadata availability and published scores must be tested against the pinned local source, not hardcoded from an earlier narrative.

Create a **source-truth discrepancy register**: statement → guide location → official code/test → version → affected downstream decisions → correction owner → revalidation status. Treat contaminated prior conclusions as provisional until repaired.

## 3. Architecture and authority boundaries

![Platform authorities and evidence flow.](assets/02_authorities.png)

| Authority / component | Owns | Must not do |
|---|---|---|
| Competition & Source-Truth Authority | Pin source, maintain `competition-spec.yaml`, implementation tests, open assumptions and change decisions | Accept documentation prose over contrary executable source without escalation |
| Trusted Runner / Registry | Immutable experiment identity, inputs, execution, trace, artifacts, environment and policy hashes | Silently overwrite runs or return an incomplete result as valid |
| Controller Development | Hypotheses, implementation, training, and proposed repairs | Edit protected evaluation definitions or certify own release |
| Evaluation Authority | Partition manifests, official-independent scorer, baseline comparisons, accepted uncertainty reporting | Tune policy; move audit cases into development without versioned decision |
| Independent Red Team | Threat model, falsification tests, leakage/generalization/release findings | Treat every symptom as proven root cause |
| Failure Engineering | Detection, incident containment, reproducible traces, fault localization, blast-radius review, permanent regression tests | Mark a repair independently verified based only on developer's assertion |
| Release Authority / human decision owner | Evidence review, approved candidate, fallback and exact final artifact | Promote a candidate with unresolved blocking integrity defects |
| Control Center | Views of authoritative registry, gates, incidents and lineage | Become a parallel editable source of truth |

**Access implementation:** separate policy sandbox from diagnostic harness; make protected manifests, scores and scenario-specific configs unavailable to development by default. Use role controls and audited access rather than relying only on agent instructions. The policy's `get_action` must not receive a true hidden state, future weather strip, unexposed reward, or evaluation-file access.

### 3.1 Evidence moves, authority does not

The modeler registers a hypothesis and executes through the trusted runner. The independent scorer evaluates compatible, complete run outputs. The Red Team challenges the resulting claim. Failure Engineering inspects defects when detected. Release Authority promotes only evidence-certified candidates. The research journal explains what was actually learned; it does not override test records.

## 4. Project workspace and canonical records

Recommended minimum stack: Git and dependency lock; Python modules, pytest and configuration validation; small SQLite registry and immutable run directories; CLI-first execution; MLflow optional for display/artifact search. Jupyter is for investigation, never the authoritative inference path. Avoid mandatory remote workers, microservices or dashboards before a vertical slice works.

```text
smart-buildings-project/
  competition/      competition-spec.yaml  source_truth_discrepancies.md  decisions/
  research/         problem/  data_understanding/  ideas/  journal/
  controller/       transfer_policy.py  modules/  checkpoints/
  platform/         runner/  metadata/  traces/  lineage/  registry/
  evaluation/       scorer/  protocols/  suites/  metrics/  reports/
  red_team/         threat_model/  probes/  reports/
  failure_engineering/
                    contracts/  detectors/  incidents/  regression/  runbooks/
  configs/          experiments/  baselines/  releases/
  tests/            unit/  interface/  integration/  known_answer/  mutation/
  runs/             RUN-ID/ (immutable)
  candidates/       POLICY-ID/ (approved packages only)
  releases/         REL-ID/  fallback/
  docs/             architecture/  operations/  decision_records/
```

| Object | Required identity and dependencies |
|---|---|
| `SPEC-ID` | Source revision, official contract revision, tested metric, access policy, open assumptions |
| `SUITE-ID` / `EVAL-ID` | Scenario partition manifest hash, generator batch, seed set, weather interval/source, official scorer version, audit-access rules |
| `IDEA-ID` | Hypothesis, scientific mechanism, comparator, risk and stage |
| `EXP-ID` | Idea ID, controlled change, held constants, protocol, budget, precommitted decision rule |
| `RUN-ID` | Exact resolved config; code, simulator, model, scenario and dependencies hashes; trace/result IDs |
| `POLICY-ID` | Approved implementation/checkpoint bundle, constructor/action interface, supported suite versions |
| `INC-ID` | Incident, affected runs, earliest known deviation, hypotheses, confirmation, quarantine and closure |
| `REL-ID` | Approved POLICY-ID, artifact checksum, clean process test, rules check, rollback/fallback pointer |

Run statuses and promotion statuses are distinct (§17). A changed policy, suite, contract or reward implementation creates a new identity. Historical artifacts are never mutated in place.

## 5. Source-truth and specification integrity

**Gate zero, before serious controller work.** Independently inspect the local official README, manifest, starter policy, scenario generator, metadata constructor, environment `step`, action conversion, reward computation, baseline definitions and leaderboard aggregation. Record exact commit, dirty tree diff, dependency lock and dated official-rule links.

**Minimum executable known-answer fixtures:** (1) count/validate manifest pairs and full horizon; (2) enumerate schema/metadata and action indices on every shipped building; (3) test normalized action to native value, including zero midpoint and physical floors; (4) check valid/invalid action handling; (5) calculate reference reward components for hand-constructed within-band, mild and >5 K violations, unoccupied and energy examples; (6) match the official evaluator's aggregation; (7) inspect no-unpermitted-field behaviour in participant sandbox.

**Correction procedure:** open discrepancy → pin both versions → reproduce conflict → identify authoritative source for current release → correct spec/docs/tests → identify affected designs and past results through lineage → rerun affected gates. Human approval required for changes in official interpretation, metric implementation or protected-data access. A previously marked “verified” guide is subject to the same audit as any other artifact.

**Gate S0 PASS:** executable contract fixtures and a minimal valid full-episode policy run pass; no unresolved discrepancy affects policy access, action semantics or score correctness. Otherwise block optimization; continue only safe source investigation.

## 6. Environment partitioning and evaluation governance

### 6.1 The unit of separation

Never randomly divide five-minute rows of one episode into independent train/test observations. Preserve the lineage of **entire building configurations, generation batches, weather intervals, and complete episodes**. Different episodes from the same building are correlated; different strips from the same station can overlap in time unless proved otherwise. Six shipped buildings are six distinct physical configurations—not thirty independent buildings.

![Environment separation and audit firewall.](assets/03_suites.png)

| Suite | Purpose and access |
|---|---|
| `DEV` | Visible to controller development. Shipped scenarios and/or explicitly allocated generated scenarios; debug, train, tune. |
| `SELECT` | Fixed, versioned model-selection scenarios. Reuse is permitted but all attempts count; it is not an unbiased final audit. |
| `GENERALIZATION` | Red-Team-controlled independently generated new buildings with distinct weather strips; limited aggregate feedback by predeclared milestone. |
| `STRESS` | Legitimate hard regimes and intentionally perturbed diagnostic cases; label in-family vs OOD. No false claim that stress score equals expected hidden score. |
| `SEALED_RELEASE` | Locked newly generated scenarios for frozen candidate, no iteration or manual per-scenario tuning. If used to redesign, retire and replace with a new sealed set. |

Prepare the partition manifest and access rules **before experiments**. Use configuration-content hashes, generation-batch identifiers, provenance, source station and temporal intervals to reject overlaps or near-duplicate identities. Each generated building's effective material draw may depend on batch size; a seed alone is insufficient provenance. Keep the official 30-scenario manifest intact as a reproducible reference suite, and log any reuse as development exposure.

### 6.2 What we test

- **Familiar:** known building/known development strip, verifies operating competence, not transfer.
- **Weather transfer:** seen building/new nonoverlapping strip; distinguish strip novelty from new station family.
- **Building transfer:** unseen configuration with controlled weather-source-family comparisons, maintaining distinct intervals.
- **Joint transfer (primary):** unseen building + unseen strip, closest internal counterpart to hidden scenario novelty.
- **Stress/OOD:** justified extremes of materials, topology, weather, initial state and constraints; report separately rather than blending into official-equivalent scores.
- **Structural metamorphic checks:** consistent zone/AHU relabeling plus corresponding metadata and action map updates; inappropriate sensitivity reveals index shortcuts.

Where possible, use matched-policy tests: same scenario hash, initialization, seeds, full horizon and scorer. Group reports by building and station/source for *diagnosis*, while preserving equal per-scenario weights for the official metric. Do not infer causal building effects from different seasonal strips merely sharing a station label.

**Gate E1 PASS:** manifests versioned, no prohibited overlap, development can run with no read access to sealed configs/results, tests detect planted overlap, and approved validation protocol is frozen. Any change requires a decision record and a new EVAL-ID.

## 7. Trusted experiment and observability foundation

### 7.1 Preflight → execute → postflight

**Preflight:** validate pinned spec and suite; hashes; resolved config; metadata/field map; action shapes/dtypes/ranges; policy constructor; dependencies; access permissions; resource budget; expected horizon; output destination. Disallow uncontrolled reads of internal simulator or forecast files in the participant sandbox.

**Execute:** create immutable `RUN-ID`; initialize a fresh policy per scenario; capture pre-action observation, policy-interpreted fields (when instrumented), raw decision, validation result, native action, realized actuator feedback, timestamp, post-step observation, reward and diagnostic components. Use stable zone and AHU identifiers, not only positional offsets. The diagnostic harness may record internal thermal state in a separate privileged channel; the policy may not consume it.

**Postflight:** require exactly 8,640 rewards for an official-equivalent episode; finite outputs and complete logs; saved/checkpointed artifact reload; fresh-process parity; independent score reconstruction; immutable summary and known gate results. A shorter diagnostic run is **not** promoted as a comparable official episode. Avoid silently capping or replacing penalties.

![Per-step trace required for isolation.](assets/04_trace.png)

### 7.2 Minimum run evidence package

```text
runs/RUN-0041/
  manifest.json             # code/policy/simulator/config/suite hash, source, seed, hardware
  resolved_config.yaml
  preflight.json
  trace.parquet             # policy-visible observations/actions and timestamps; versioned schema
  privileged_trace.parquet  # optional diagnostic-only simulator state; access controlled
  timeseries.csv            # zone temperature/occupancy/step reward
  reward_components.csv
  ahu_log.csv
  score.json                # independently calculated official-equivalent metrics
  diagnostics.json          # comfort, severity, actions, capacity/stability indicators
  check_results.json        # PASS/FAIL/INCONCLUSIVE/NOT_APPLICABLE/NOT_TESTED
  red_team_report.json
  incident_refs.json
  decision.json
```

Record command, start/end timestamps, complete stderr/exit code, wall time, memory, policy and results checksum. Instrumentation must not alter policy observations or change the physical sequence under test. Test instrumentation parity with and without extended logging.

### 7.3 Reproducibility and known-fault testing

Identical scenario/policy/seed repeats should match within predeclared tolerances; do not infer population-level uncertainty from repeated deterministic replay. Test reloading artifacts in a fresh process and compare actions/trajectories. Use golden fixtures for swapped observation indices, mismatched units, invalid discrete values, zero-as-off misunderstanding, wrong reward occupancy divisor, shortened episodes, duplicate scenario aliases and metadata mismatch. Mutation-test detectors: plant a defect in **isolated copies**, require expected alarm and correct subsystem localization. Never mutate authoritative source or contaminate protected suites.

**Gate T1 PASS:** one complete trusted run is reproducible and traceable end-to-end; known wrong input/action/metric faults are detected; registry prevents overwrites; scorer runs independently; saved artifact reloads without notebook state.

## 8. Official scoring and independent success measurement

### 8.1 One score, correctly reproduced

For scenario `s`, `T_s = 8,640` and per-step reward `r_(s,t)`, compute:

`mean_reward_s = (1 / T_s) Σ_t r_(s,t)`  
`L_official = (1 / N) Σ_s |mean_reward_s|`  **(lower is better; equal scenario weight)**.

For the documented nonpositive reward, this measures mean per-step loss. The reward components are comfort/productivity regret (weight 0.6), normalized energy cost (0.2), and normalized carbon emissions (0.2). Reference power rates of **80 kW per AHU for electricity and 205 kW per AHU for gas** are *normalization denominators*, not power caps; actual normalized charges can exceed one. The comfort function uses actual zone occupancy weighting and unbounded shortfall beyond a 5 K deviation, as confirmed by the current reward implementation. Do **not** substitute the guide's incorrect fixed occupancy divisor or invented normalization clipping.

Use the official scorer as a regression oracle, but retain a separately maintained implementation with known-answer edge cases and cross-checks. Stop if the two disagree materially. Baseline returns are comparators, **not** terms in the competition metric; include the official four reference controllers when validly available. `all_off` is a stress/reference behaviour, not an adequate sole comparator.

### 8.2 Internal report: four distinct claims

| Dimension | Mandatory measures; interpretation |
|---|---|
| **Validity** | Fully completed run; contract, data access, field mapping, score parity, valid actions, loadable artifact. Missing checks ≠ pass. |
| **Official performance** | Exact official-equivalent `L`; full scenario values and run/suite versions; paired deltas against appropriate baselines. |
| **Operating quality** | Comfort loss, occupied-zone violation fraction and duration, >5 K excursions and severity, zone-level tails, electrical/gas use/cost, carbon, action rejection, saturation, persistent oscillation and recovery only when meaningfully defined. |
| **Generalization & uncertainty** | DEV→joint-transfer gap; worst scenario and P90; scenario-level win rate; by-building and by-weather diagnostic slices; variation over independently generated building/strip clusters and training seeds. |

**Do not pool 8,640 correlated steps and pretend they are independent buildings.** Bootstrap or hierarchical intervals, where justified, should respect building and weather/source clusters and explicitly show sample sizes. The official 30-scenario mean is a score; it is not a confidence guarantee over an unknown hidden population.

### 8.3 Matched evaluation and precommitted decisions

Controller A and B receive identical scenario configurations, weather, initialization, horizon and evaluation version. Record per-scenario `Δ_s = L_A,s − L_B,s`; positive favours B. Show the mean, spread, tail and where gains/regressions concentrate. Define decision criteria **before** results: meaningful effect size, noninferiority/worst-case limits, critical comfort/validity failures, compute budget and stopping rule. Derive numeric limits from verified baselines and actual operating requirements; do not invent universal thresholds after seeing a favored candidate. A high mean improvement cannot waive a blocking defect or a deliberately predeclared critical-tail gate.

### 8.4 Success ladder

`EXECUTABLE → OPERATIONALLY COMPETENT → COMPETITIVE → GENERALIZABLE → RELEASE-VERIFIED`. Passing one level is necessary but not sufficient for the next. An internal success statement names the suite, comparison, effect, risk, uncertainty and tests actually performed. It does not promise hidden evaluation success.

**Gate E2 PASS:** known-answer scorer matches official outputs; full 8,640-step enforcement; report contains validity, official performance, diagnostics and environment-level uncertainty; matched comparison and one planted metric error have been tested.

## 9. Independent Red Team

**Purpose:** try to falsify the controller's reliability claims, independently of the development agent. Red Team owns attack specs and evidence, while Failure Engineering owns causal diagnosis and repair verification. A failed attack result is a symptom until isolated.

| Attack family | Examples of executable tests | Required discriminator |
|---|---|---|
| Source/information | Attempt access to simulator internals, inaccessible future strip, evaluation-only values; enforce restricted policy sandbox | Source-permitted access versus invalid privileged access |
| Time/trajectory leakage | Verify policy decision at `t` sees only current/prior observations and allowed init metadata; detect post-action data misalignment | Shift/replay point with fixed allowed prefix |
| Environment memorization | New building configurations and nonoverlap weather windows; renamed config/zone IDs; remove scenario-ID shortcuts | Matched known vs joint-transfer suite, stable semantics under relabeling |
| Interface/actuator | Zone/AHU permutations consistent with metadata; action index/type/normalization probes | Compare intended native action and realized equipment feedback |
| Closed-loop | Full-episode drift, delayed failures, hard climates, high shared demand, different legitimate initial states | Isolate policy behaviour from genuine equipment constraints |
| Objective/evaluation | Reward-component recomputation; worst-zone and scenario tails; unintended metric shortcuts | Audit with independent official-equivalent implementation |
| Artifact/release | Clean process without notebooks, hidden-only files, implicit caches; runtime and dependency limits | Compare archived candidate's exact actions to release build |
| Detector quality | Planted fault and false-positive checks in isolated diagnostic fixtures | Show intended alarm fires and correct boundary is indicated |

**Audit levels:** FAST for every serious run (access, action, score, trace); FULL for promotion milestones (joint transfer, robustness, causal probes, uncertainty); RELEASE for exact frozen artifact and sealed suite. Every check declares applicability, preconditions, expected signal, limitations, outcome (`PASS`, `FAIL`, `NOT_APPLICABLE`, `INCONCLUSIVE`, `NOT_TESTED`), severity and an investigation pointer.

The Red Team does **not** demand every physically impossible scenario be comfortable. Separate policy fault, simulator defect, and valid but difficult environmental constraint. Avoid retrofitting thresholds to make a preferred candidate pass.

## 10. Failure Engineering System

### 10.1 Mission and interfaces

Failure Engineering (FES) is not merely a bug tracker. It is an **operational detection, isolation, containment, diagnosis, repair-verification and recurrence-prevention system**. Evaluation says *whether an outcome is good*; Red Team challenges *whether a claim is trustworthy*; FES explains *where the first verified deviation originated* and *whether the repair removes that cause without creating another failure*. FES cannot certify its own repair; independent gate owner signs closure.

![Failure cascade and root-cause boundary.](assets/05_cascade.png)

### 10.2 Fault-domain contracts

| Boundary | Input contract and independent assertion | Failure examples |
|---|---|---|
| `F0` Source specification | Pinned competition rules, code revision, evaluator and participant-access contract | Guide contradicts metadata/reward source |
| `F1` Scenario provenance | Config, source weather/interval, generator batch, seeds, hashes | Duplicate environment in protected suite; wrong weather strip |
| `F2` Observation interpretation | Field names, normalization, units, time, ID mapping agree with raw policy observation | Zone temperature read from wrong index |
| `F3` Controller decision | Deterministic or seeded logic produces shaped finite outputs from permitted inputs | Invalid shape, inappropriate internal mode, unauthorized lookup |
| `F4` Action validation/translation | Correct discrete value and native setpoint for actual actuator, floors and saturation | Water setpoint sent into air-pressure slot |
| `F5` Physical realization | Simulator applies allowed command and records realized response; distinguish model's physics from a software defect | Actuator ineffective due to mixed-air limit or equipment capacity |
| `F6` Reward | Same occupancy, comfort piecewise curve, fuel cost/carbon and denominator as official source | Wrong fixed occupancy normalization |
| `F7` Aggregation/reporting | Full horizon and correct equal-scenario loss; no missing/duplicated records | Short episode falsely compared to official full score |
| `F8` Transfer/evaluation | Protected partitions, matched settings and sound inferential claims | Familiar-building gains collapse on unseen buildings |
| `F9` Release/infrastructure | Exact archived policy, dependencies, runtime and access work in clean sandbox | Package imports development-only file |

A suspected domain is a **hypothesis**, not a root-cause finding. Instrument step and cross-boundary contracts separately; build tiny known-answer fixtures for each boundary.

### 10.3 Severity and containment

| Severity | Trigger | Required response |
|---|---|---|
| `P0 INTEGRITY` | Unauthorized information, invalid official score, incorrect source contract, contaminated suite or corrupted provenance | Block promotion; quarantine affected lineage; investigate affected historical conclusions |
| `P1 CRITICAL OPERATIONAL` | Repeated invalid actions/execution failure, or predeclared severe control failure under applicable conditions | Reject candidate from promotion; preserve complete incident trace and isolate |
| `P2 REGRESSION` | Verified deterioration or unexplained meaningful behavioural anomaly | Investigate before promotion |
| `P3 DIAGNOSTIC` | Noncritical observability/reporting problem without proven score contamination | Track and fix; upgrade severity if evidence changes |

**Do not classify a physical limitation as a software bug without evidence.** Do not write “zero detected failures” when the detector did not run. When a source/evaluator fault has already affected results, mark affected runs `QUARANTINED` immediately; never silently replace or delete them.

### 10.4 Seven-stage incident procedure

1. **Capture/contain.** Assign `INC-ID`, freeze raw run, failing timestamp/symptom and hashes; suspend promotion and determine obvious dependent artifacts.
2. **Reproduce.** Replay exact policy, scenario, prefix, init, seed and scorer. If nonreproducible, compare environment, instrumentation and stochastic sources; record uncertainty.
3. **Find earliest verified deviation.** Trace observation → interpreted fields → raw action → mapped/native action → realized equipment → state trajectory → reward. Search before the visible failure to account for thermal lag.
4. **Localize boundary.** Apply contract fixtures to the smallest plausible F0–F9 subsystem; check adjacent boundaries and temporal meaning.
5. **Discriminate hypotheses.** Predeclare competing explanations and smallest controlled tests; maintain identical environment and action prefix when feasible. Avoid treating unmatched weather windows as causal evidence.
6. **Repair narrowly.** Developer makes isolated versioned change, plus minimal new permanent test. Do not edit original run or protected evaluation definition to make result pass.
7. **Verify/close independently.** Old revision reproduces fault; new revision passes original incident; affected unit/integration/episode, transfer and regression tests pass; blast radius re-evaluated; approved verifier signs closure.

Incident record must have `observed_symptom`, `first_detected_step`, `earliest_verified_deviation`, `reproducibility`, `competing_hypotheses`, `suspected_boundary`, `confirmed_root_cause` (optional until proven), diagnostic evidence, affected run/policy/release IDs, quarantine, repair commit, regression test, independent verifier, closure status. `UNRESOLVED` is a legitimate final diagnostic state and cannot be silently promoted to `CONFIRMED`.

### 10.5 Replay and instrumentation constraints

Every per-step trace captures the raw policy-visible observation, field mapping, requested action, validation/normalization result, realized actuator feedback, post-step observation, reward-component attribution, scenario clock and stable equipment IDs. Diagnostic state snapshots, if used, are **privileged and physically separated** from the controller's runtime. An identical-seed replay is a reproducibility test; a causal counterfactual requires a controlled single-factor change and careful treatment of hidden state and random streams. If state checkpointing is unavailable, reconstruct the verified common trajectory prefix.

### 10.6 Blast radius and regression gate

Maintain a lineage DAG:

`SPEC → data/scenario → SUITE → experiment → RUN → POLICY → combination → RELEASE`.

A confirmed upstream defect triggers automatic query of downstream nodes, temporary certification suspension, re-run decision, a corrected new version and audit trail. Git rollback alone cannot restore external artifacts or erase a prior invalid conclusion. A material controller repair must re-evaluate full episodes and relevant protected suites. If its result led developers to tune against a sealed audit, retire that audit for future independent certification.

**Required mutation demonstration:** inject, in isolated copies, swapped observation indices, wrong normalization/divisor, zone-ID/action permutation, a forbidden future-data read, a shortened-episode scorer and a missing artifact. Detector must fire with useful evidence and lead to the correct boundary. Also test one nondefect physical saturation case for false-positive resistance.

**FES Gate F1 PASS:** trace completeness, injected-fault detection, incident reproduction/localization, quarantine of derived artifacts and independent regression closure are demonstrated end-to-end. FES is not verified solely because its healthy-case tests pass.

## 11. Experiment engine and controller-development lifecycle

Preserve distinct objects: idea = hypothesis; experiment = planned discriminating comparison; run = immutable execution; policy candidate = independently approved artifact; release = exact submission package. Register claims with their tested scope.

**Experiment plan template:** research mechanism; target failure/opportunity; baseline; one intended change; held-constant variables; suites and audit access; expected diagnostic signature; official and auxiliary metrics; minimum meaningful effect and critical-tail guards; compute cap; stopping policy; full-trial trigger; known limitations. Keep research and implementation conclusions separate.

**Lifecycle:** `BACKLOG → READY → FEASIBILITY → SCREENING → FULL_TRIAL → AUDIT → DECISION` with outcomes `PROMOTE`, `ITERATE` (new linked experiment), `PARK`, or `REJECT TESTED CLAIM`. A system defect diverts affected runs into FES/quarantine; a controller that validly loses is a tested scientific outcome, not a platform error.

- **Feasibility:** constructor, valid actions, shape across differing buildings, fast known-answer tests.
- **Screening:** bounded diagnostic scenarios and short runs to reject clear implementation failure; **no short-run official score claims**. Preserve ideas whose value plausibly depends on full thermal settling or rare climates.
- **Full trial:** identical full-horizon matched suite, training-seed repetitions when applicable, breakdowns and independent score.
- **Candidate audit:** protected joint-transfer evaluation; Red Team/FES review; compare performance, robustness, compute and reproducibility.

Record all candidates tried, failed branches, changes in suite and all public leaderboard peeks. Commit experimentation budgets in advance and reserve capacity for both exploration and repairs; the v1.0 50/30/20 allocation is a planning heuristic, **not** an immutable rule for this new problem.

## 12. Candidate portfolio and optional policy combinations

Maintain `champion`, `challengers`, `diversity/alternatives`, `specialist hypotheses`, `archive`, and certified `fallback` as **versioned control-policy artifacts**. Portfolio promotion considers official matched performance, transfer, per-zone/condition failure tails, inference overhead, release complexity and evidence validity. Archive does not equal deletion.

Combining policies is **optional**, not a mandatory OOF-blending phase. If considered, define lawful composition of complete hybrid actions, equipment coordination and policy state. A specialist selector may use only inference-time metadata and observations, never scenario/hidden-label identity. Test its failure modes and end-to-end result independently; do not assume mixing two valid individual action vectors yields a valid or effective policy. Traditional OOF stacking is relevant only if an actual supervised meta-learning design justifies it and its data availability rules are independently certified.

## 13. Resource management, lineage, and recovery

Track scenario×policy execution duration, memory, disk, training/runtime budgets, completed steps, restartability and artifact size. Prioritize minimum evidence to disambiguate a hypothesis, but reserve budget for full-horizon and sealed tests. A five-minute × 8,640-step × many-scenario simulator is materially different from a single CSV fit; use scenario manifests and run queues to make cost visible before dispatch.

Cache deterministic scenario construction and results only when source/config/batch/seed, action policy and permissions are compatible; never allow cached outputs to bridge a protected boundary. Detect duplicate `code+config+scenario+seed+scorer` runs by canonical hash. Preserve `baseline_returns.json` with source revision, but treat it as a comparator requiring version/episode compatibility, not unquestionable current truth.

On interrupted or OOM work: preserve partial log and status (`SYSTEM_INTERRUPTION` or `INCOMPLETE`); never infer scientific outcome from it. Backup registry, code, generated config snapshots, policy weights, evaluation suites, traces, incidents and releases; test restore. Protect secrets, isolate untrusted model files, and never log hidden/protected inputs into development-readable traces.

## 14. Release and submission engineering

Keep an early **certified fallback policy**—a correctly packaged baseline that satisfies the actual participant interface and executes a full episode—even if it is not competitive. The shipped zero-action starter is useful for interface smoke testing but is not automatically an adequate performance fallback.

**Release checklist (frozen exact artifact):**

1. Resolve all blocking source-truth, leakage, interface, reward, FES and audit findings. Human approves POLICY-ID and EVAL-ID.
2. Freeze code/checkpoint/config/dependencies; compute hashes; include only files allowed by competition rules.
3. Load the artifact in a fresh clean process or Kaggle-equivalent runtime, without notebook global state or access to development scenario names, privileged data or hidden audit results.
4. Initialize against multiple buildings of different `K` and `V`; inspect metadata and action-index interpretation, normalization, dtype/ranges, and no access to prohibited information.
5. Run full-horizon official-equivalent scenarios; independent scorer and operating diagnostics agree; satisfy resource/runtime rules; archive the exact policy package and logs.
6. Conduct rare sealed release-audit evaluation under frozen decision criteria. If results influence a material redesign, retire this sealed suite and use a new audit set for later release certification.
7. Preserve certified fallback and rollback instructions. Record final submitted file/kernel revision, checksum, submission receipt and any public score only as one additional noisy observation, not a tuning oracle.

Failure to reproduce the archived policy's outputs in a fresh environment blocks release regardless of headline score. A passing local shadow test cannot reproduce the unknown hidden-test distribution.

## 15. Implementation roadmap and acceptance gates

The platform is built in **vertical slices**, not by creating all folders at once. Each gate has an executable demonstration and evidence location.

| Phase | Build now | Exit demonstration / owner |
|---|---|---|
| `S0` Source truth | Pinned competition spec, discrepancy register, minimal official policy fixture, reward oracle | Source-truth tests pass; guide conflicts resolved or clearly blocked; human sign-off |
| `T1` Trusted core | Registry, immutable manifests, policy runner, trace, known-action fixtures | Replay a full run, prevent overwrite, verify clean artifact reload |
| `E1` Suite governance | DEV/SELECT/GENERALIZATION/STRESS/SEALED manifests, hashes, permissions | Plant overlapping build/strip; detector blocks; sealed access denied to developer |
| `E2` Independent measurement | Official scorer clone, reward fixture, component/tail metrics, matched comparison | Official score matches reference; 8,640-step enforcement; bad metric injection caught |
| `F1` FES MVP | F0–F9 contracts, instrumentation, incident store, reproduction, mutation tests, quarantine | Inject fault, isolate correct boundary, trace affected lineage and independently verify repair |
| `R1` Red Team MVP | FAST/FULL/RELEASE audits, access/temporal/generalization attacks | Detect planted leakage and ID/action permutation; report applicability honestly |
| `X1` Experiment engine | Idea/experiment/run links, queue and research journal | Hypothesis → two fair full runs → independent compare → preserved decision |
| `C1` Candidate arena | Policy portfolio, comparison and promotion authority | Invalid high score rejected; valid candidate promoted with full evidence and fallback |
| `L1` Lineage/operations | DAG, compute accounting, disaster recovery | Upstream defect quarantines descendants; restore a run from durable archive |
| `REL` Release | Clean-process policy packaging, locked artifact and submission checklist | Exact certified artifact passes and fallback remains available |

**Critical dependencies:** `S0` precedes strategy assumptions; `T1` and `E1/E2` precede performance claims; `F1` and `R1` precede champion certification; `REL` depends on all blocking gates. Partial work can continue within unaffected, explicitly marked boundaries; do not conceal blocked gates by asserting overall completion.

![Required experiment and certification path.](assets/06_roadmap.png)

## 16. Operating workflows and incident examples

### A. Ordinary hypothesis: change to controller behaviour

Register IDEA → precommit comparator, unchanged conditions and test suite → FAST feasibility and bounded screening → full matched run(s) → score and diagnostic reconciliation → Red Team audit and FES incident checks → promotion/iterate/park/reject with exact tested scope. If a defect appears, quarantine the scientific comparison until corrected and rerun; do not write “model failed” for a broken experiment.

### B. A score improves but joint-transfer performance deteriorates

Freeze both run manifests. Compare matched scenario deltas, distribution tails, building/strip coverage, official scorer parity and training exposure. Identify whether the issue is memorized environment, wrong metadata mapping, climate interaction, genuine control limitation or evaluation error. A DEV win alone cannot overrule protected generalization. Correct cause → new experiment, not ad hoc selective threshold change.

### C. Severe morning discomfort in one building

Capture zone/event and preceding several hours. Check raw zone temp and metadata mapping (F2), requested reheat/air/water action (F3–F4), realized equipment and capacity/temperature constraints (F5), occupancy/schedule (F0–F2), and independent comfort penalty (F6–F7). Test competing explanations on the same scenario/prefix. A recommendation to “preheat earlier” is a proposed remedy, **not** a root-cause diagnosis.

### D. Guide specification error discovered during implementation

Create `INC-SPEC` with guide claim, exact code discrepancy and source revision. Stop affected architectural/evaluation conclusions; query downstream design/experiment lineage. Correct spec, fixtures and documentation. Run source-truth tests and revalidate affected candidates; retain original evidence and resolution history.

### E. Release crashes in clean runtime

Mark candidate `BLOCKED`, retain fallback, save exception/trace and environment difference. Isolate F9 dependencies/imports and forbidden file reads, reproduce in clean process, repair narrow dependency and rerun interface, artifact and full-episode checks. A successful local notebook run is not release certification.

## 17. Decision policy, risks, and deferred capabilities

### 17.1 Outcome and gate taxonomy

| Scientific / execution state | Meaning |
|---|---|
| `VERIFIED_IMPROVEMENT` | Valid run, predeclared comparison supports improvement on specified scope |
| `VERIFIED_EXPERIMENTAL_FAILURE` | Valid controlled test, hypothesis not supported within tested conditions |
| `VALID_OPERATIONAL_FAILURE` | Correctly executed controller performs poorly or breaches declared operational criteria; root cause may remain open |
| `SYSTEM_FAILURE` | Integrity, execution, source, pipeline or scoring defect invalidates inference |
| `QUARANTINED` | Result or descendant potentially contaminated; not eligible for promotion |
| `INCONCLUSIVE` | Evidence insufficient for decisive claim |
| `UNVERIFIED` | Required checks absent or not executed |

Promotion is separate: `ELIGIBLE`, `INVESTIGATE`, `BLOCKED`; incident closure is separately `OPEN`, `CONTAINED`, `REPRODUCED`, `ROOT_CAUSE_CONFIRMED`, `REPAIR_UNDER_TEST`, `VERIFIED_CLOSED`, `UNRESOLVED`.

### 17.2 Human-controlled material changes

Require dated decision record and independent review for competition-rule interpretation, reward/metric changes, evaluation/suite redesign, protected audit access, champion promotion, irreversible deletion, rule-sensitive external input, and final submission. Capture alternatives, expected blast radius, evidence and rollback plan. The platform can automate checks; the human remains accountable for authority-sensitive actions.

### 17.3 Risks and hard limits

| Risk | Countermeasure and honest limitation |
|---|---|
| Unknown hidden population | Joint-transfer and cluster-aware tests; cannot certify unseen outcomes or new weather stations not documented |
| Repeated holdout tuning | Limited planned milestones and sealed release suite; retire a revealed suite after it changes design |
| False confidence from deterministic replay | Treat repeat match as execution validity, not population uncertainty |
| Mistaken guide/specification | Source-truth audit; versioned errata and incident blast-radius revalidation |
| Overgeneralized safety assumptions | Define simulator-specific objective and actual HVAC constraints; do not imply external occupant safety certification |
| Overengineering | Build source truth → trusted runner → evaluation → FES/Red Team → development loop before dashboards |
| Adversarial test false positives | Physically meaningful perturbations, known-fault injection and nondefect controls |
| Resource exhaustion | Costed full-horizon runs, staged screening with explicit uncertainty and reserve for final tests |
| Ensemble complexity | Only build policy combinations when evidence justifies coordination, risk and maintenance cost |
| Public leaderboard pursuit | Archive interactions; no automatic retuning from one public score |

**Deferred by default:** generic OOF library, leaderboard-optimizing automatic agent loops, mandatory GNN/Transformer/controller architecture, heavy UI, microservices and distributed execution. They can be introduced via tested hypotheses and decision records, never mistaken for necessary starting components.

---

## Appendices

### A. Minimum experiment specification

```yaml
experiment_id: EXP-0041
idea_id: IDEA-017
hypothesis: "State the physical/control mechanism and predicted observable effect"
control_change: "One intended change"
comparator_policy_id: POLICY-BASELINE-01
held_constant: [scenario_suite, simulator_revision, horizon, scorer_version]
eval_protocol_id: EVAL-V1
scenario_suite_ids: [DEV-V1, SELECT-V1]
primary_metric: official_equal_scenario_mean_abs_step_reward
secondary_metrics: [comfort_tail, energy_cost, carbon, invalid_actions]
minimum_meaningful_effect: "precommitted with evidence"
critical_failure_rule: "precommitted, source-consistent"
compute_budget: "finite and approved"
stopping_rule: "explicit; diagnostic screen is not official score"
required_audits: [FAST, FES_CHECK]
```

### B. Minimum incident specification

```yaml
incident_id: INC-0012
severity: P0_INTEGRITY
status: OPEN
affected_run_ids: []
symptom: "Incorrect normalized comfort regret"
first_detected_step: null
earliest_verified_deviation: null
reproducibility: NOT_YET_TESTED
suspected_boundaries: [F6]
competing_hypotheses: []
confirmed_root_cause: null
supporting_trace_ids: []
quarantined_descendants: []
containment_action: "Block affected score claims"
repair_commit: null
permanent_regression_test: null
independent_verifier: null
closure_evidence: null
```

### C. Command-level desired interface (specification; not claimed implemented)

```bash
lab spec verify --competition competition/competition-spec.yaml
lab suite verify --manifest evaluation/suites/GENERALIZATION-V1.yaml
lab policy smoke --policy POLICY-003 --scenario building_train_1/atlanta_2
lab run --config configs/experiments/EXP-0041.yaml
lab score --run RUN-0041 --protocol EVAL-V1
lab compare --runs RUN-0041 RUN-0042 --suite SELECT-V1
lab redteam audit --policy POLICY-003 --level full
lab failure open --run RUN-0041 --symptom "..."
lab failure replay --incident INC-0012
lab lineage affected --artifact SPEC-V1
lab release verify --candidate POLICY-003 --suite SEALED-RELEASE-V1
```

### D. Source of truth and reference register

- **Prior document:** *Kaggle Research Platform — Implementation Reference v1.0*, 21 October 2026 (superseded generic predictor assumptions; retained for original decisions).
- **Project research:** `Smart_Buildings_Problem_Research_R1-R5.md` (physical and operational rationale).
- **Data guide:** `DATA_UNDERSTANDING_GUIDE.md` (orientation and investigation outputs; conflicts require source audit before being binding).
- **Official public kit:** <https://github.com/smart-buildings-2026/starter-kit>; key paths `README.md`, `smart_buildings/training_set.yaml`, `smart_buildings/evaluate.py`, `smart_buildings/baselines/transfer_policy.py`, `smart_buildings/smart_control/reward/setpoint_energy_carbon_regret.py`, `smart_buildings/smart_control/reward/base_setpoint_energy_carbon_reward.py`, `smart_buildings/smart_control/utils/materials.py`.
- **Competition rules:** <https://smart-buildings-2026.github.io/competition/competition.html> and <https://www.kaggle.com/competitions/neurips-2026-smart-buildings/>. Verify currently effective rules and local checkout at S0.

**Document-control rule:** Whenever a decision changes, revise this blueprint, its `competition-spec.yaml`, architecture-decision record, contract fixtures, implementation backlog and affected gates together. Distinguish proposed, implemented, verified and deferred. Never represent the design itself as working software.

**Final rule: promote verified evidence, not attractive scores; preserve tested failures as knowledge and quarantine invalid evidence.**
