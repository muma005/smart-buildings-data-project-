# Content & Findings Matrix — Smart Buildings Data Understanding

## Executive Summary & Stage P1 Objective

This matrix reconciles, consolidates, and maps all substantive empirical findings from the completed Data Understanding investigation into the target chapters of `DATA_UNDERSTANDING_GUIDE.md`.

It resolves duplication across investigation stages (e.g., unifying weather data origins, representation, quality, diversity, and simulation impact into coherent sections), addresses potential discrepancies in definitions or scopes, and establishes the required visual and explanatory treatments for each finding.

---

## 1. Consolidated Findings & Mapping Table

| Finding ID | Core Empirical Finding | Supporting Evidence | Confidence Status | Related Research | Explanation Required for Reader | Proposed Guide Chapter | Visual Requirement | Material Limitations | Editorial Action |
|---|---|---|:---:|:---:|---|---|---|---|---|
| **F-001** | Shipped development set contains exactly 30 scenarios across 6 buildings and 5 weather stations in a non-reused balanced block design. 18 presets (including Minneapolis) are unreferenced. | `training_set.yaml`, `d0_manifest_audit.json` | VERIFIED | R3, R5 | Explain why the dataset is a balanced block ($6 \times 5 = 30$) rather than a full grid ($6 \times 40 = 240$), and how unseen test scenarios will likely follow the same pairing topology. | Chapter 1 & Chapter 5 | Development Scenario Pairing Matrix (Table/Diagram) | Shipped presets allow generating custom scenarios, but the official benchmark is strictly 30. | Retain as foundational context. Unify pairing discussion in Ch 1 & Ch 5. |
| **F-002** | Action space dimensions follow closed-form relations: $D = K + 1$ (discrete) and $C = 3K + 2 + 2V$ (continuous). | `hybrid_action_environment.py`, `d0_smoke_test.json`, `d2_building_schemas.json` | VERIFIED | R4 | Explain what actuators these numbers physically correspond to (AHU fans, dampers, boiler stages, reheat valves) and why action dimensionality varies with building size. | Chapter 2 | HVAC Actuator & Action Mapping Flowchart | Holds for the standard hybrid Gymnasium environment wrapper. | Retain; explain physical meaning before presenting formulas. |
| **F-003** | Only `TempF` drives external thermal forcing in the simulator. Solar radiation, envelope air infiltration, humidity, and wind speed are omitted or static. | `weather_controller.py`, `d1_provenance_trace.json` | VERIFIED | R1, R3 | Explain that the simulator evaluates pure thermal conduction driven by dry-bulb temperature; controllers need not estimate solar gains or latent cooling loads. | Chapter 1 & Chapter 5 | External Thermal Forcing Diagram (Active vs Omitted) | Real-world buildings experience large solar and latent loads; this is a simulator simplification. | Retain; highlight as a major physical domain constraint. |
| **F-004** | Simulator actively injects area-based internal loads ($10.0\text{ W/m}^2$, $2.0\text{ W/m}^2$ standby) and occupant sensible heat ($70.0\text{ W/person}$) into zone air nodes. | `simulator_flexible_floor_plan.py`, `d1_provenance_trace.json` | VERIFIED | R1, R2 | Explain that indoor temperatures are actively perturbed by occupants and equipment, coupling the occupancy schedule to thermal load and comfort penalty. | Chapter 1 & Chapter 6 | Zone Internal Heat Balance Diagram | Occupant sensible heat is fixed at 70 W; latent heat is omitted since humidity is unmodeled. | Retain; connect to pre-cooling and daily load profiling. |
| **F-005** | Observation dimensionality follows the exact closed-form relation: $\mathrm{Obs} = 6V + 15K + 58$ across all 6 buildings in the distribution. | `d2_schema_and_invariants.py`, `d2_building_schemas.json` | VERIFIED | R4, R5 | Break down the 58 constant features (Fourier time encodings, plant states, comfort flags, occupancy) and modular per-AHU (15) and per-VAV (6) feature groups. | Chapter 2 | Observation Vector Decomposition Diagram | Holds for the single-timeseries observation reducer. | Retain; use to motivate why fixed-size neural networks cannot transfer. |
| **F-006** | Weather records (52,560 hourly rows) and building CAD rasters exhibit zero missing values, zero NaNs, strict monotonicity, and zero spatial defects. | `d3_data_quality_audit.py`, `d3_quality_report.json`, `QUALITY_ISSUES.csv` | VERIFIED | R1, R4 | Reassure reader that the data pipeline is robust and controllers will not fail due to NaNs or coordinate misalignments during evaluation. | Chapter 3 | Data Quality Verification Dashboard (Table) | Historical data from 2023; future unseen weather will follow identical formats. | Retain; present as evidence of pipeline dependability. |
| **F-007** | Thermal inertia index $\tau$ spans $7.4\times$ ($1.94$ to $14.43$); paired seasonal weather windows are non-overlapping across buildings. | `d4_coverage_and_diversity.py`, `d4_diversity_metrics.json` | VERIFIED | R1, R3, R5 | Explain why building response speed varies drastically, why a single fixed setpoint policy fails, and how balanced-block pairing confounds building comparisons. | Chapter 4 & Chapter 5 | Thermal Inertia $\tau$ Spectrum Chart & Confounding Diagram | $\tau$ is derived from physical material and geometry properties; operational $\tau$ also depends on internal gains. | Retain; central finding explaining cross-building transfer difficulty. |
| **F-008** | Simulator is 100% bitwise deterministic; reconstructed 10-component reward function reconciles to environment output with $0.00\text{e}+00$ discrepancy. | `d5_simulation_and_reward_audit.py`, `d5_reward_reconstruction.json` | VERIFIED | R2, R4 | Detail all 10 reward components: piecewise quadratic comfort penalty $f(d)$, occupancy scaling ($O_{\mathrm{norm}}=125$), utility costs, carbon factors, and $K$-dependent normalizers. | Chapter 6 | 10-Component Reward Reconstruction Flowchart | Capacity denominators ($80\text{ kW}$, $205\text{ kW}$) scale with $K$, not floor area. | Retain; complete mathematical exposition of the optimization loss. |
| **S-01** | Four-tier information access boundary strictly limits what the policy can access during hidden evaluation. | `environment.py`, `02_DATA_STRUCTURE_AND_SEMANTICS.md` | VERIFIED | R4 | Distinguish Tier A (live observation) and Tier B (static metadata) from Tier C (hidden simulation state) and Tier D (hidden scenario parameters). | Chapter 2 | Four-Tier Information Access Boundary Diagram | Policy cannot cheat by reading internal grid temperatures or future weather. | Retain; critical operational constraint for participants. |
| **S-02** | The `comfort_mode_soon` signal triggers exactly 2 hours before scheduled comfort occupancy. | `environment.py`, `d5_reward_reconstruction.json` | VERIFIED | R1, R4 | Explain how this lookahead signal enables pre-heating and pre-cooling to overcome thermal lag without incurring quadratic morning penalties. | Chapter 2 & Chapter 6 | Pre-Conditioning Timeline Diagram | Fixed at 2 hours across all buildings regardless of whether $\tau$ is 1.94 or 14.43. | Retain; essential operational mechanism. |
| **S-03** | HVAC zoning follows a strict ceiling rule: $K = \lceil V / 10 \rceil$, yielding $9.0$ to $10.0$ zones per AHU across all buildings. | `building_train_*.yaml`, `d4_diversity_metrics.json` | VERIFIED | R3, R4 | Explain how AHU grouping is procedurally assigned and how VAV boxes are clustered by spatial floor plan proximity. | Chapter 4 | AHU-to-Zone Topology Diagram | Reflects realistic commercial building HVAC design practices. | Retain; key structural invariant for modular controller design. |
| **S-04** | Envelope material properties vary independently via Latin Hypercube Sampling across 6 parameters, yielding facade $U \in [1.18, 2.08]$ and heat capacity $C \in [0.40, 1.87]$. | `materials.py`, `d1_provenance_trace.json`, `d4_diversity_metrics.json` | VERIFIED | R1, R3 | Explain how thermal conductivity, thickness, density, and specific heat combine into overall facade insulation and structural thermal storage. | Chapter 1 & Chapter 4 | Material Property Distribution Chart | 6 continuous parameters sampled uniformly via LHS. | Retain; grounds physical thermal differences in architectural engineering. |
| **S-05** | Actuator response introduces significant physical latency (45–120 min) and coupled equipment trade-offs (fan static power cubic in airflow; reheat boiler loop coupling). | `05_SIMULATOR_BEHAVIOUR_AND_EVALUATION.md`, `simulator_flexible_floor_plan.py` | SUPPORTED INFERENCE | R1, R4 | Explain why operating decisions have delayed consequences and why opening dampers increases electrical fan consumption. | Chapter 6 | Actuator Coupling & Latency Interaction Map | Derived from physical equations implemented in the simulator. | Retain; core operational dynamics. |
| **S-06** | Climatic regimes exhibit distinct failure signatures: Fairbanks (boiler saturation & freeze down), Phoenix (chiller saturation & TOU peak tariff), Denver (actuator fighting), Singapore (mild cooling). | `05_SIMULATOR_BEHAVIOUR_AND_EVALUATION.md`, `d4_diversity_metrics.json` | VERIFIED | R1, R2, R5 | Walk through how controllers fail in each climate and why a uniform policy without climate awareness degrades. | Chapter 5 & Chapter 6 | Climatic Failure Mode Comparison Matrix | Observed during baseline rollouts across extreme regimes. | Retain; directly addresses cross-climate transferability. |
| **S-07** | Three ranked hypotheses remain for subsequent phases: H1 (modular vs GNN transfer), H2 (online thermal inertia estimation), H3 (subarctic night setback vs float). | `06_DATA_UNDERSTANDING_SYNTHESIS.md` | PROVISIONAL | R5 | Articulate the key open scientific questions that Data Understanding establishes for Phase 03 modeling. | Chapter 8 | Synthesis & Future Hypotheses Summary | Requires empirical policy training and testing in Phase 03. | Retain; guides seamless transition to next phase. |

---

## 2. Discrepancy & Duplication Reconciliation Record

### 1. Weather Data Treatment (D1, D2, D3, D4, D5)
- **Investigation Perspective**: D1 investigated origin/conversions; D2 investigated schemas; D3 investigated file integrity; D4 investigated climatic diversity; D5 investigated impact on stepping.
- **Editorial Synthesis**: In the guide, weather is introduced in Chapter 1 (origin, 2023 historical records, linear interpolation), detailed in Chapter 2 (units, frequency, Tier A representation), validated in Chapter 3 (100% clean, 0 missing rows), analyzed in Chapter 5 (the 5 climatic regimes, diurnal swings, HDD/CDD, pairing with buildings), and stepped in Chapter 6 (ambient forcing during simulation). This eliminates repetitive context setting while maintaining logical progression.

### 2. Action and Observation Space Invariants (D0, D2)
- **Discrepancy Check**: D0 noted $D=5, C=92$ for `building_train_1`; D2 formalized the general formulas $D = K + 1$, $C = 3K + 2 + 2V$, and $\text{Obs} = 6V + 15K + 58$.
- **Reconciliation**: Present the general closed-form formulas in Chapter 2 as verified invariants, and use `building_train_1` ($K=4, V=39$) as the concrete, step-by-step worked example.

### 3. Normalization Capacities and Weights (D1, D5)
- **Discrepancy Check**: Some early documentation references fixed building-wide normalizers, whereas the audited simulator implements $K$-dependent normalizers: $P_{\mathrm{elec,ref}} = 80{,}000 \cdot K\text{ W}$ and $P_{\mathrm{gas,ref}} = 205{,}000 \cdot K\text{ W}$.
- **Reconciliation**: Chapter 6 explicitly explains the $K$-dependent capacity scaling confirmed by the D5 reward audit and `d5_reward_reconstruction.json`.

---

## 3. P1 Completion Gate Review

```text
STAGE: P1 (FINDINGS EXTRACTION & RECONCILIATION)
STATUS: PASS

Completion Checklist:
- [x] All 8 formal registered findings (F-001 through F-008) extracted and mapped
- [x] 7 secondary substantive findings (S-01 through S-07) extracted and mapped
- [x] Full provenance and supporting artifacts identified for each finding
- [x] Cross-stage duplication (weather, schemas, rewards) reconciled into progressive chapters
- [x] Contradictions and discrepancies investigated and reconciled against code/data truth
- [x] Every finding assigned to a specific chapter in DATA_UNDERSTANDING_GUIDE.md
- [x] Visual requirements and material limitations specified for all findings

Conclusion: Knowledge extraction and reconciliation is 100% complete and validated.
Next Action: Proceed to Stage P2 (Knowledge Reorganization & Content Mapping).
```
