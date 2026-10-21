# Findings Register — Smart Buildings Challenge Data Understanding

Every substantive finding entered into this register follows the mandatory charter format:
- Finding ID
- Investigation stage
- Research question
- Observation
- Supporting evidence
- Interpretation
- Relevance to R1–R5
- Limitations / alternative explanations
- Confidence status
- Implications for subsequent investigation

---

## Registered Findings

### Finding F-001: Shipped Scenario Population & Discrete Pairing Topology
- **Finding ID**: F-001
- **Investigation stage**: D0
- **Research question**: What is the authoritative population of buildings, weather strips, and scenarios in the competition distribution?
- **Observation**: The official development set defined in `smart_buildings/training_set.yaml` contains exactly 30 scenarios formed from 6 unique buildings and 30 unique weather strips across 5 weather stations (Atlanta, Denver, Fairbanks, Phoenix, Singapore). Each building is paired with exactly 1 unique 30-day weather strip per station. Buildings are numbered non-consecutively (`building_train_1`, `2`, `4`, `5`, `7`, `8`); buildings 3 and 6 do not exist in the distribution. Furthermore, 18 additional weather presets (including all 8 presets for Minneapolis) are shipped as generator inputs but are not part of `training_set.yaml`.
- **Supporting evidence**:
  - `smart_buildings/training_set.yaml`
  - Automated audit: `02_DATA_UNDERSTANDING/diagnostics/scripts/d0_verify_manifest.py`
  - Audit output: `02_DATA_UNDERSTANDING/diagnostics/outputs/d0_manifest_audit.json`
  - Directory inspection of `smart_buildings/buildings/` and `smart_buildings/weather/`
- **Interpretation**: The development set is deliberately structured as a non-reused, balanced block design ($6 \times 5 = 30$), not a full Cartesian cross-product ($6 \times 40 = 240$). Unseen test scenarios will likely follow a similar balanced structure with held-out buildings and weather strips.
- **Relevance to R1–R5**: Directly impacts R3 (Heterogeneity) and R5 (Transferability). Cross-building comparisons cannot assume identical weather forcing because no two buildings share the same 30-day weather strip.
- **Limitations / alternative explanations**: Organizers provide `run_scenario_generator.py` allowing generation of arbitrary pairings, but `training_set.yaml` is the authoritative competition development benchmark.
- **Confidence status**: VERIFIED
- **Implications for subsequent investigation**: In D4 and D5, analyses must respect these specific pairings and not conflate weather differences with building physical differences.

---

### Finding F-007: 7.4x Thermal Inertia Variation and Experimental Confounding
- **Finding ID**: F-007
- **Investigation stage**: D4
- **Research question**: What is the extent of physical thermal variation across the building population, and how does the experimental pairing affect cross-building comparisons?
- **Observation**: 
  1. The derived thermal inertia index ($\tau \propto C_{\mathrm{env}} / U$) spans over $7.4\times$ across the 6 training buildings, ranging from $\tau = 1.94$ in `building_train_7` (fast, leaky) to $\tau = 14.43$ in `building_train_1` (massive, well-insulated).
  2. The 30 development scenarios in `smart_buildings/training_set.yaml` implement a non-reused, balanced block design where each building encounters a distinct 30-day time window for each station.
- **Supporting evidence**:
  - `02_DATA_UNDERSTANDING/diagnostics/scripts/d4_coverage_and_diversity.py`
  - Output: `02_DATA_UNDERSTANDING/diagnostics/outputs/d4_diversity_metrics.json`
  - `smart_buildings/training_set.yaml`
- **Interpretation**: A single control policy must accommodate buildings that lose heat at vastly different rates. Furthermore, raw score differences between two buildings on the same nominal station (e.g. Building 1 vs Building 2 on "Atlanta") are confounded by differing seasonal weather windows (March vs April) and cannot be interpreted as purely architectural performance.
- **Relevance to R1–R5**: Directly links R1 (Building Behaviour), R3 (Heterogeneity), and R5 (Transferability).
- **Limitations / alternative explanations**: Unseen evaluation scenarios will also pair 6 held-out buildings with 5 held-out weather stations.
- **Confidence status**: VERIFIED
- **Implications for subsequent investigation**: Evaluation aggregation must evaluate performance across all 5 climatic regimes, rather than optimizing for a single building or season.

- **Finding ID**: F-006
- **Investigation stage**: D3
- **Research question**: Are the competition weather recordings and spatial arrays sufficiently clean, continuous, and trustworthy for evaluation?
- **Observation**: Comprehensive testing of all 11 weather CSV files (representing 52,560 hourly records) revealed exactly 0 missing values, 0 nonfinite floats, 0 duplicate timestamps, and 100% strictly monotonic hourly increments. Furthermore, all 48 shipped weather presets define 30-day horizons that fall strictly within their respective annual files, guaranteeing that linear interpolation will never fail or extrapolate.
- **Supporting evidence**:
  - `02_DATA_UNDERSTANDING/diagnostics/scripts/d3_data_quality_audit.py`
  - Output: `02_DATA_UNDERSTANDING/diagnostics/outputs/d3_quality_report.json`
  - `02_DATA_UNDERSTANDING/evidence/QUALITY_ISSUES.csv`
- **Interpretation**: The meteorological data pipeline is highly reliable; controllers will not suffer from data feed crashes, NaN propagation, or timestamp discontinuities during simulation.
- **Relevance to R1–R5**: Directly supports R1 (Building Behaviour) and R4 (Control Problem).
- **Limitations / alternative explanations**: Relies on 2023 historical data; future unseen weather strips will also be drawn from historical weather files.
- **Confidence status**: VERIFIED
- **Implications for subsequent investigation**: No defensive data imputation or missing-value handling is required for weather inputs.

- **Finding ID**: F-005
- **Investigation stage**: D2
- **Research question**: What mathematical formula determines the observation vector dimensionality across arbitrary buildings?
- **Observation**: Analysis across all 6 shipped buildings reveals that observation dimensionality is governed by the exact closed-form relation:
  $$\mathrm{Obs} = 6V + 15K + 58$$
  where $V$ is the number of thermal zones/VAVs and $K$ is the number of AHUs. This formula predicts the exact observation vector length without a single exception across all 6 buildings:
  - `building_train_8`: $K=3, V=30 \to \mathrm{Obs} = 283$ (100% match)
  - `building_train_7`: $K=4, V=36 \to \mathrm{Obs} = 334$ (100% match)
  - `building_train_1`: $K=4, V=39 \to \mathrm{Obs} = 352$ (100% match)
  - `building_train_4`: $K=6, V=54 \to \mathrm{Obs} = 472$ (100% match)
  - `building_train_5`: $K=8, V=79 \to \mathrm{Obs} = 652$ (100% match)
  - `building_train_2`: $K=9, V=85 \to \mathrm{Obs} = 703$ (100% match)
- **Supporting evidence**:
  - `02_DATA_UNDERSTANDING/diagnostics/scripts/d2_schema_and_invariants.py`
  - Output: `02_DATA_UNDERSTANDING/diagnostics/outputs/d2_building_schemas.json`
  - Observation feature name inspection script
- **Interpretation**: The 58 constant features consist of: 24 `hod` Fourier terms, 24 `dow` Fourier terms, 7 Hot Water System plant features, `comfort_mode_now` (1), `comfort_mode_soon` (1), and building total `num_occupants` (1). Each AHU adds 15 features, and each zone/VAV adds 6 features.
- **Relevance to R1–R5**: Directly impacts R4 (The Control Problem) and R5 (Transferability). Proves that observation spaces vary dramatically in length (from 283 to 703 features in training), requiring any transfer policy to handle variable-length inputs dynamically rather than relying on fixed-dimension dense layers.
- **Limitations / alternative explanations**: Holds for the standard Gymnasium single-timeseries observation reducer; other reducers (e.g. histogram reducers) would have different constant terms.
- **Confidence status**: VERIFIED
- **Implications for subsequent investigation**: Graph neural networks, transformer tokenizers, or modular per-zone/per-AHU sub-controllers are naturally indicated by this modular $6V + 15K + 58$ structure.

- **Finding ID**: F-003
- **Investigation stage**: D1
- **Research question**: Which environmental quantities from the weather data files actually drive the thermal simulation, and which are omitted?
- **Observation**: Weather CSV files provide 7 meteorological columns (`TempC`, `TempF`, `DewPointC`, `WindspeedKmph`, `Humidity`, `StationName`, `Location`). However, source inspection and execution tracing prove that ONLY `TempF` is consumed by the evaluated simulator. `DewPointC` is unread; `Humidity` is loaded into pandas but `get_current_humidity` is never called by any simulation component; `WindspeedKmph` is ignored because external convection is modeled using a static scenario-level constant (e.g. 19.1 W/(m²·K)); solar radiation and envelope air infiltration are completely omitted from the simulator.
- **Supporting evidence**:
  - Source: `smart_buildings/smart_control/simulator/weather_controller.py` (lines 322–328)
  - Execution trace: `02_DATA_UNDERSTANDING/diagnostics/scripts/d1_trace_lineage.py`
  - Output: `02_DATA_UNDERSTANDING/diagnostics/outputs/d1_provenance_trace.json`
- **Interpretation**: Real-world building thermodynamics are heavily influenced by solar irradiance (fenestration gains) and wind-induced infiltration. In this benchmark, ambient dry-bulb temperature is the sole external thermodynamic forcing disturbance.
- **Relevance to R1–R5**: Directly addresses R1 (Building Behaviour) and R3 (Heterogeneity). Models need not attempt to estimate solar position or latent cooling loads from humidity.
- **Limitations / alternative explanations**: Simplifies the physical modeling domain, ensuring all participants operate under identical pure thermal-conduction assumptions.
- **Confidence status**: VERIFIED
- **Implications for subsequent investigation**: Weather analysis in D4 should focus exclusively on outdoor temperature distributions and temporal dynamics.

---

### Finding F-004: Presence of Area-Based Internal Gains and Occupant Sensible Heat
- **Finding ID**: F-004
- **Investigation stage**: D1
- **Research question**: Are internal heat gains and occupant thermal emissions physically represented in the simulator?
- **Observation**: The simulator includes both: (1) an area-based internal gain model configured at 10.0 W/m² with a 0.2 standby fraction during non-comfort hours, and (2) a dynamic occupant sensible heat model injecting 70.0 W sensible thermal power per person into the specific zone occupied according to the Markov arrival/departure chain.
- **Supporting evidence**:
  - Source: `smart_buildings/smart_control/simulator/simulator_flexible_floor_plan.py` (lines 93–96, 446–482)
  - Diagnostic trace: `02_DATA_UNDERSTANDING/diagnostics/outputs/d1_provenance_trace.json`
- **Interpretation**: Thermal loads are not solely driven by envelope loss to outdoor air; occupancy actively perturbs zone air temperatures during occupied daytime periods, directly coupling the occupancy schedule to both thermal dynamics (R1) and comfort weighting (R2).
- **Relevance to R1–R5**: Directly links R1 (Building Behaviour) to R2 (Operating Objectives).
- **Limitations / alternative explanations**: Sensible heat is fixed at 70 W/person; latent heat (moisture) is omitted since humidity is not modeled.
- **Confidence status**: VERIFIED
- **Implications for subsequent investigation**: Control policies must account for internal daytime heat accumulation when scheduling pre-cooling or heating.

- **Finding ID**: F-002
- **Investigation stage**: D0
- **Research question**: Do the mathematical relationships governing action dimensions hold in the instantiated simulation environment?
- **Observation**: For `building_train_1` ($K=4$ AHUs, $V=39$ zones/VAVs), the environment exposes exactly $D = 5$ discrete actions and $C = 92$ continuous actions, perfectly verifying the structural invariants:
  $$D = K + 1 = 4 + 1 = 5$$
  $$C = 3K + 2 + 2V = 3(4) + 2 + 2(39) = 12 + 2 + 78 = 92$$
- **Supporting evidence**:
  - `02_DATA_UNDERSTANDING/diagnostics/scripts/d0_smoke_test.py`
  - Output: `02_DATA_UNDERSTANDING/diagnostics/outputs/d0_smoke_test.json`
  - Source: `smart_buildings/smart_control/environment/hybrid_action_environment.py` (lines 111–130)
- **Interpretation**: Discrete actions correspond to on/off binary commands for each AHU plus the central Hot Water System (HWS). Continuous actions correspond to:
  - 3 per AHU (supply air temp, static pressure, recirculation fraction)
  - 2 for HWS (water temp, water differential pressure)
  - 2 per VAV zone (damper fraction, reheat water valve)
- **Relevance to R1–R5**: Directly links to R4 (The Control Problem) and R3 (Heterogeneity). Confirms that action space dimensionality changes dynamically with building scale ($K$ and $V$).
- **Limitations / alternative explanations**: Verified directly on `building_train_1`; must verify across all 6 shipped buildings in D2.
- **Confidence status**: VERIFIED
- **Implications for subsequent investigation**: D2 schema inspection must verify whether this formula holds identically across all remaining 5 buildings.

---

### Finding F-008: Deterministic Simulation and Exact 10-Component Reward Reconstruction
- **Finding ID**: F-008
- **Investigation stage**: D5
- **Research question**: Is the simulation environment strictly deterministic, and can the official multi-objective reward function be independently reconstructed from raw physical variables to exact numerical precision?
- **Observation**:
  1. The simulation environment demonstrates 100% bitwise determinism across independent rollouts initialized with identical configurations and seeds ($\Delta_{\mathrm{obs}}^{\max} = 0.0$, $\Delta_{\mathrm{reward}}^{\max} = 0.0$).
  2. All 10 components of the official reward function:
     $$r_t = 0.6 \cdot p_t - 0.2 \cdot c_t - 0.2 \cdot e_t$$
     including the piecewise quadratic comfort shortfall $f(d)$, occupancy scaling ($O_{\mathrm{norm}} = 125.0$), electricity and natural gas cost tariffs, grid carbon factors, and $K$-dependent plant reference normalizations ($P_{\mathrm{elec,ref}} = 80{,}000 \cdot K$, $P_{\mathrm{gas,ref}} = 205{,}000 \cdot K$), were reconstructed independently and matched against the simulator output across 576 continuous simulation steps with a maximum discrepancy of exactly $0.00\text{e}+00$.
- **Supporting evidence**:
  - `02_DATA_UNDERSTANDING/diagnostics/scripts/d5_simulation_and_reward_audit.py`
  - Output: `02_DATA_UNDERSTANDING/diagnostics/outputs/d5_reward_reconstruction.json`
  - Report: `02_DATA_UNDERSTANDING/05_SIMULATOR_BEHAVIOUR_AND_EVALUATION.md`
- **Interpretation**: The optimization landscape is fully transparent, closed-form, and mathematically sound. No hidden random noise or uncalibrated reward shaping terms exist. Comfort shortfall penalties escalate quadratically once zone deviation exceeds $5.0^\circ\text{C}$, penalizing severe thermal drifts far more harshly than minor setpoint errors.
- **Relevance to R1–R5**: Directly resolves R2 (Operating Objectives) and R4 (The Control Problem).
- **Limitations / alternative explanations**: The normalization constants $P_{\mathrm{elec,ref}}$ and $P_{\mathrm{gas,ref}}$ scale strictly with AHU count $K$, not floor area or zone count $V$.
- **Confidence status**: VERIFIED
- **Implications for subsequent investigation**: Provides an exact, verified loss/reward function for offline evaluation, policy gradient calculation, and model-predictive control cost formulation.
