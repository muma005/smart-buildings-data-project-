# Guide Content Map — Smart Buildings Data Understanding

## Executive Summary & Stage P2 Objective

This content map establishes the detailed architectural blueprint for `DATA_UNDERSTANDING_GUIDE.md`. It reorganizes the findings of the completed Data Understanding investigation into an intuitive, progressive learning journey that guides the reader from initial orientation to deep technical comprehension, without requiring them to navigate fragmented stage reports.

---

## Chapter-by-Chapter Architectural Plan

### Opening — Understanding the Data in One View
- **Chapter title**: Opening: Understanding the Data in One View
- **Central reader question**: What is this competition environment, what does the data represent, and how do the pieces fit together?
- **Concepts that must be understood first**: None (entry point). Assumes general data science literacy and familiarity with sequential decision making.
- **Findings to include**: High-level synthesis of F-001 (population), F-002/F-005 (interfaces), and F-008 (optimization objective).
- **Actual numerical results to present**: 30 official training scenarios, 6 buildings, 5 weather stations, 8,640 steps per episode (30 days at 5-minute resolution).
- **Important explanations**:
  - The challenge: controlling HVAC to balance occupant comfort (60%), energy costs (20%), and carbon emissions (20%) across unseen buildings.
  - Why this is not a static tabular dataset: it is an active simulation environment where decisions dynamically alter future states.
  - The relationship between offline configuration files, live simulation step arrays, and hidden evaluation contracts.
- **Required diagrams or figures**:
  - *Figure 0.1*: The Smart Buildings End-to-End System Diagram (Mermaid) showing external inputs, procedural buildings, simulation solver, policy interface, and evaluation pipeline.
- **Evidence references**: `00_DATA_ENVIRONMENT.md`, `FINAL_HANDOFF.md`, `training_set.yaml`.
- **Limitations to preserve**: Development data represents 6 training buildings; hidden evaluation tests held-out buildings and weather strips.
- **Connection to the next chapter**: Once the reader understands what the system is, the natural next question is: *Where did all these files and numbers come from?*

---

### Chapter 1 — Where Does the Data Come From?
- **Chapter title**: Chapter 1: Where Does the Data Come From? (Data Provenance & Origins)
- **Central reader question**: What are the true sources of the data—which parts are recorded, which are procedurally generated, and which are simulated?
- **Concepts that must be understood first**: System overview from Opening.
- **Findings to include**: F-001 (population & presets), F-003 (weather origins & dry-bulb only), F-004 (internal gains & occupant sensible heat), S-03 (procedural AHU ceiling rule), S-04 (Latin Hypercube Sampling for materials).
- **Actual numerical results to present**:
  - 11 historical weather CSV files (52,560 hourly rows from 2023).
  - Area-based internal heat generation: $10.0\text{ W/m}^2$ occupied, $2.0\text{ W/m}^2$ standby.
  - Dynamic occupant sensible heat: $70.0\text{ W/person}$ via Markov chain.
  - Latin Hypercube Sampling across 6 material properties.
- **Important explanations**:
  - The four data origin classes: Recorded (weather, tariffs, carbon), Generated (CAD floor plans, LHS materials), Simulated (temperatures, airflows, power), and Derived (comfort penalties, costs, rewards).
  - The weather pipeline: how historical hourly CSVs are sliced into 30-day presets and linearly interpolated to 5-minute intervals.
  - Crucial simplification: only `TempF` is read; solar radiation, humidity, infiltration, and wind speed are omitted in the simulator.
  - Procedural building generation: room partitioning, CAD rasterization, and AHU ceiling rule ($K = \lceil V/10 \rceil$).
- **Required diagrams or figures**:
  - *Figure 1.1*: The Four Data Origin Streams and Transformation Pathways (Mermaid flowchart).
  - *Figure 1.2*: Outdoor Forcing: Active Dry-Bulb vs Omitted Solar/Infiltration/Humidity (Mermaid diagram).
- **Evidence references**: `01_DATA_PROVENANCE.md`, `PROVENANCE_REGISTER.csv`, `d1_provenance_trace.json`.
- **Limitations to preserve**: Omission of solar and humidity simplifies real-world thermodynamics but standardizes the benchmark.
- **Connection to the next chapter**: Having understood where the data originates, the reader is ready to examine *how that data is structured, formatted, and exposed to the control policy*.

---

### Chapter 2 — Understanding the Data Itself
- **Chapter title**: Chapter 2: Understanding the Data Itself (Structure, Semantics, and Information Boundaries)
- **Central reader question**: How are buildings, weather, actions, and observations structured, and what information can the policy legally access?
- **Concepts that must be understood first**: Data origin streams (Chapter 1) and physical HVAC equipment definitions (AHU, VAV, boiler).
- **Findings to include**: F-002 & F-005 (closed-form invariants $D=K+1$, $C=3K+2+2V$, $\text{Obs}=6V+15K+58$), S-01 (4-tier access boundary), S-02 (`comfort_mode_soon` 2-hour lookahead).
- **Actual numerical results to present**:
  - Building dimensions across the 6 training buildings: $K \in [3, 9]$, $V \in [30, 85]$, $\text{Obs} \in [283, 703]$, $C \in [71, 199]$, $D \in [4, 10]$.
  - Complete worked breakdown of `building_train_1` ($K=4, V=39 \implies D=5, C=92, \text{Obs}=352$).
  - Breakdown of the 58 constant features (24 hod, 24 dow, 7 HWS, 2 comfort flags, 1 total occupancy).
- **Important explanations**:
  - Entity-Relationship model: how Scenarios bind Buildings, Weather Presets, and Tariff Schedules.
  - The Four-Tier Information Access Boundary:
    - Tier A: Live step observation (sensory feedback).
    - Tier B: Static participant metadata (`ahu_zone_assignments`, action spec).
    - Tier C: Hidden simulator state (wall grid cells, individual zone occupancy).
    - Tier D: Hidden scenario config (true material properties, CAD arrays, future weather).
  - Interface Invariants: mathematical proofs of $D$, $C$, and $\mathrm{Obs}$.
  - Temporal semantics: 5-minute stepping, 8,640 steps per episode, pre-action observation semantics.
- **Required diagrams or figures**:
  - *Figure 2.1*: Entity-Relationship Topology of the Smart Buildings Benchmark (Mermaid ER diagram).
  - *Figure 2.2*: The Four-Tier Information Access Boundary (Mermaid container diagram).
  - *Figure 2.3*: Observation Vector Structural Anatomy ($6V + 15K + 58$) (Detailed block layout).
- **Evidence references**: `02_DATA_STRUCTURE_AND_SEMANTICS.md`, `DATA_DICTIONARY.csv`, `d2_building_schemas.json`.
- **Limitations to preserve**: Policy cannot read future weather or internal wall temperatures; must rely strictly on Tier A and Tier B.
- **Connection to the next chapter**: With the data structures and interface contracts defined, the reader must know: *Can we actually trust these files and numbers to be clean, continuous, and bug-free?*

---

### Chapter 3 — Can We Trust the Data?
- **Chapter title**: Chapter 3: Can We Trust the Data? (Quality, Integrity, and Empirical Validation)
- **Central reader question**: Is the data reliable, are there missing values or corrupted rasters, and what quirks must we accommodate?
- **Concepts that must be understood first**: File types and schemas from Chapter 2.
- **Findings to include**: F-006 (0 missing, 0 NaNs, 100% monotonic, 0 CAD defects), S-03 (procedural checks), audit of 36 material parameters.
- **Actual numerical results to present**:
  - 52,560 hourly weather timestamps checked: 0 duplicates, 0 gaps, 0 nonfinite floats.
  - 48 weather presets checked: 100% fit within historical 2023 dates (day 1 to day 365).
  - 6 CAD rasters ($70 \times 70$ cells): 100% boundary isolation; 0 room cells leaking into outside space.
  - 36 material parameters: 100% conform to theoretical LHS bounds.
- **Important explanations**:
  - The quality audit methodology: automated stress testing across temporal, spatial, and mechanical domains.
  - Why the weather feed is rock-solid: linear interpolation will never fail or produce NaNs.
  - Classification of quirks vs defects:
    - Benign quirks: unused weather columns (`Humidity`, `WindspeedKmph`), 18 unreferenced weather presets.
    - Structural constraints: fixed 5-min step, no early episode termination.
    - Zero blocking defects.
- **Required diagrams or figures**:
  - *Table 3.1*: Comprehensive Data Quality Audit Summary across all 6 validation dimensions.
  - *Figure 3.1*: Spatial Cell Separation Validation in CAD Floor Plans (Wall vs Room vs Outside).
- **Evidence references**: `03_DATA_QUALITY_REPORT.md`, `QUALITY_ISSUES.csv`, `d3_quality_report.json`.
- **Limitations to preserve**: Perfect historical quality does not guarantee unseen weather will have zero sensor noise; controllers should maintain defensive input bounds.
- **Connection to the next chapter**: Having confirmed that the data is trustworthy, we now explore the physical world it represents: *How do the buildings in the population actually differ?*

---

### Chapter 4 — Understanding the Building Population
- **Chapter title**: Chapter 4: Understanding the Building Population (Architectural, Physical & HVAC Diversity)
- **Central reader question**: How diverse are the supplied buildings in size, layout, construction materials, and thermal responsiveness?
- **Concepts that must be understood first**: Building geometry, zoning, and material properties from Chapters 1 & 2.
- **Findings to include**: F-007 (thermal inertia $\tau$ spans $7.4\times$), S-03 (AHU clustering $9.0\text{--}10.0$ zones/AHU), S-04 (facade $U$ and envelope heat capacity $C_{\mathrm{env}}$).
- **Actual numerical results to present**:
  - Floor areas: $1{,}508\text{ m}^2$ (`building_train_8`) to $3{,}471\text{ m}^2$ (`building_train_2`) $\to 2.3\times$ spread.
  - Zones: $V=30$ to $V=85$ ($2.8\times$).
  - AHUs: $K=3$ to $K=9$ ($3.0\times$).
  - Facade $U$-values: $1.179$ to $2.077\text{ W}/(\text{m}^2\text{K})$ ($1.76\times$).
  - Envelope volumetric heat capacity: $0.403$ to $1.871\text{ MJ}/(\text{m}^3\text{K})$ ($4.64\times$).
  - Relative thermal inertia index $\tau$: $1.94$ (`building_train_7`) to $14.43$ (`building_train_1`) $\to \mathbf{7.4\times\text{ variation}}$.
- **Important explanations**:
  - Architectural diversity: footprint, aspect ratio, interior room layouts, multi-floor zoning.
  - Physical thermal diversity: how material conductivity, density, and wall thickness combine into overall envelope insulation ($U$) and thermal mass ($C_{\mathrm{env}}$).
  - The Physical Meaning of $\tau$: why a low-$\tau$ building loses heat rapidly and reacts quickly to HVAC, while a high-$\tau$ building stores massive heat and responds slowly.
  - HVAC mechanical topology: why zones per AHU is tightly clustered ($9.0\text{--}10.0$) due to procedural design rules.
- **Required diagrams or figures**:
  - *Figure 4.1*: Building Physical Comparison Matrix (Area, Zones, AHUs, Facade $U$, Envelope $C$, Thermal Inertia $\tau$).
  - *Figure 4.2*: The Thermal Inertia Spectrum ($\tau \in [1.94, 14.43]$) (Visual scale showing fast/leaky vs slow/massive buildings).
- **Evidence references**: `04_COVERAGE_AND_LIMITATIONS.md`, `d4_diversity_metrics.json`.
- **Limitations to preserve**: All 6 training buildings are single-floor commercial layouts (height 3.5 m); multi-floor vertical heat stacking is unmodeled.
- **Connection to the next chapter**: Buildings do not exist in a vacuum; they interact with the exterior environment. We next examine: *What environmental conditions do these buildings face?*

---

### Chapter 5 — Understanding the Environmental Conditions
- **Chapter title**: Chapter 5: Understanding the Environmental Conditions (Meteorological Regimes, Seasonal Windows & Confounding)
- **Central reader question**: What climate regimes are represented, what temporal dynamics do they exhibit, and how are weather strips paired with buildings?
- **Concepts that must be understood first**: Weather data origins (Chapter 1) and dry-bulb forcing (Chapter 1).
- **Findings to include**: F-001 (balanced block pairing), F-007 (experimental confounding), S-06 (5 climatic regimes).
- **Actual numerical results to present**:
  - Fairbanks: Subarctic extreme cold (min $-42.0^\circ\text{C}$, Heating Degree Days $\text{HDD} = 580.2$, Cooling Degree Days $\text{CDD} = 0.0$).
  - Phoenix: Desert extreme heat (max $+46.1^\circ\text{C}$, $\text{HDD} = 0.0$, $\text{CDD} = 305.9$).
  - Denver: High-altitude temperate diurnal (swing $14.3^\circ\text{C}$, $\text{HDD} = 77.4$, $\text{CDD} = 81.6$).
  - Atlanta: Humid subtropical dual-mode ($\text{HDD} = 52.8$, $\text{CDD} = 84.1$).
  - Singapore: Equatorial constant heat (mean $27.9^\circ\text{C}$, diurnal swing $5.3^\circ\text{C}$, $\text{HDD} = 0.0$, $\text{CDD} = 237.5$).
- **Important explanations**:
  - The 5 Climatic Regimes: detailed characterization of thermodynamic demands (continuous heating vs continuous cooling vs diurnal switching).
  - The Balanced Block Non-Cartesian Pairing:
    - Why the training set contains 30 scenarios ($6 \times 5$) rather than 240 ($6 \times 40$).
    - Each building gets a distinct, non-overlapping 30-day time window for each station.
  - Experimental Confounding: why comparing raw scores of Building 1 vs Building 2 on "Atlanta" is confounded by seasonal weather shifts (March early spring vs May late spring).
- **Required diagrams or figures**:
  - *Figure 5.1*: The 5 Competition Climatic Regimes (Temperature range, Diurnal swing, HDD/CDD quadrant diagram).
  - *Figure 5.2*: The Balanced Block Scenario Pairing Matrix ($6 \text{ Buildings} \times 5 \text{ Weather Stations}$ with calendar date windows).
- **Evidence references**: `04_COVERAGE_AND_LIMITATIONS.md`, `d4_diversity_metrics.json`, `training_set.yaml`.
- **Limitations to preserve**: Only 5 weather stations in training; held-out evaluation will introduce new geographical stations.
- **Connection to the next chapter**: Now that we understand the buildings and the weather, we bring them together inside the physics engine: *What actually happens during a simulation step?*

---

### Chapter 6 — What Actually Happens Inside the Simulator?
- **Chapter title**: Chapter 6: What Actually Happens Inside the Simulator? (Step Execution, Dynamics, and Evaluation Truth)
- **Central reader question**: How does the simulator step forward in time, how do physical temperatures evolve, and how is the policy evaluated and rewarded?
- **Concepts that must be understood first**: Observation/action spaces (Chapter 2), building physics (Chapter 4), weather forcing (Chapter 5).
- **Findings to include**: F-008 (bitwise determinism & 10-component reward reconciliation), S-02 (lookahead pre-conditioning), S-05 (actuator coupling & latency).
- **Actual numerical results to present**:
  - Bitwise determinism proof: $\max \Delta_{\mathrm{obs}} = 0.0$, $\max \Delta_{\mathrm{reward}} = 0.0$.
  - 10-component reward weights: Productivity shortfall ($0.60$), Energy cost ($0.20$), Carbon emissions ($0.20$).
  - Exact reconciliation error over 576 steps: **$0.00\text{e}+00$**.
  - Plant reference capacities: Electricity $80{,}000 \cdot K\text{ W}$, Gas $205{,}000 \cdot K\text{ W}$.
  - Comfort band: $[21.0^\circ\text{C}, 24.0^\circ\text{C}]$ ($[294.15\text{ K}, 297.15\text{ K}]$); quadratic threshold at $5.0^\circ\text{C}$ violation ($< 16^\circ\text{C}$ or $> 29^\circ\text{C}$).
- **Important explanations**:
  - The Step Execution Sequence (walkthrough of the 5-minute loop from action to observation).
  - Physical thermal lag: why zone temperature lags supply air by 45 to 120 minutes.
  - Pre-conditioning via `comfort_mode_soon`: how activating pre-heating/pre-cooling 2 hours ahead avoids the morning pull-down discomfort penalty.
  - Actuator coupling: fan electrical power scaling cubically with static pressure/airflow; reheat coil hydronic draw on boiler loop.
  - Complete Mathematical Decomposition of the Reward Equation:
    - Piecewise quadratic comfort shortfall $f(d)$ and occupant weighting $O_{\mathrm{norm}} = 125.0$.
    - Tariff-scaled electricity and gas expenditure normalized by $K$-scaled plant references.
    - Grid-intensity carbon emissions normalized by $K$-scaled plant references.
- **Required diagrams or figures**:
  - *Figure 6.1*: Simulator Step Execution Sequence Diagram (Mermaid sequence diagram).
  - *Figure 6.2*: The 10-Component Competition Reward Reconstruction Architecture (Mermaid flowchart).
  - *Figure 6.3*: The Piecewise Quadratic Comfort Shortfall Penalty Curve ($f(d)$ vs deviation $d$).
- **Evidence references**: `05_SIMULATOR_BEHAVIOUR_AND_EVALUATION.md`, `d5_reward_reconstruction.json`.
- **Limitations to preserve**: Normalization references scale with AHU count $K$, not building floor area.
- **Connection to the next chapter**: Having mastered the simulator mechanics and evaluation loss, we now ask: *What does all this empirical evidence mean for the scientific problem we set out to solve?*

---

### Chapter 7 — What Does the Data Reveal About Our Original Problem?
- **Chapter title**: Chapter 7: What Does the Data Reveal About Our Original Problem? (Connecting Data Understanding to Research Fronts R1–R5)
- **Central reader question**: How does the empirical data support, refine, or challenge our foundational understanding of the Smart Buildings Challenge?
- **Concepts that must be understood first**: All previous chapters (synthesis chapter).
- **Findings to include**: Comprehensive mapping of F-001 through F-008 and S-01 through S-07 to R1–R5.
- **Actual numerical results to present**: Consolidated synthesis table summarizing physical, operational, and transferability findings.
- **Important explanations**:
  - **R1 (Building Behaviour)**: Confirmed nodal conduction, wall thermal storage, and internal loads; identified total absence of solar radiation, infiltration, and humidity.
  - **R2 (Operating Objectives)**: Unveiled the exact optimization loss; revealed that the quadratic comfort penalty makes thermal drift catastrophic compared to energy savings.
  - **R3 (Heterogeneity)**: Quantified the true physical variation ($7.4\times$ inertia spread) and the procedural regularity ($9\text{--}10$ zones/AHU); exposed the balanced-block confounding.
  - **R4 (The Control Problem)**: Reconstructed the exact closed-form interface invariants; established the strict 4-tier information access boundary; proved 100% determinism.
  - **R5 (Transferability)**: Identified the triple barrier to transfer: (1) variable input/output dimensions, (2) radical thermal inertia discrepancies, and (3) divergent climatic failure modes.
- **Required diagrams or figures**:
  - *Table 7.1*: Comprehensive Research-to-Data Evidence Matrix (R1 through R5).
  - *Figure 7.1*: The Triple Transferability Barrier (Dimensional, Thermal, and Climatic).
- **Evidence references**: `06_DATA_UNDERSTANDING_SYNTHESIS.md`, `RESEARCH_QUESTION_MATRIX.md`, `FINDINGS_REGISTER.md`.
- **Limitations to preserve**: Training data alone cannot prove whether a policy will transfer to unseen buildings; it establishes the necessary conditions for transferability.
- **Connection to the next chapter**: Finally, we consolidate our knowledge into definitive truths and open frontiers: *What do we know with certainty, and what remains to be investigated in modeling?*

---

### Chapter 8 — What Do We Know, and What Remains Unknown?
- **Chapter title**: Chapter 8: What Do We Know, and What Remains Unknown? (Synthesis, Limitations & Open Frontiers)
- **Central reader question**: What are the verified facts, the confirmed constraints, the benchmark risks, and the ranked open hypotheses heading into solution development?
- **Concepts that must be understood first**: Full synthesis from Chapter 7.
- **Findings to include**: Consolidated register of verified facts, catalog of confirmed constraints and quirks, ranked hypotheses H1, H2, H3.
- **Actual numerical results to present**: Summary matrix of population limits, access tiers, and evaluation constants.
- **Important explanations**:
  - What is definitively known and verified (8 core findings, closed-form equations, exact reward math).
  - Confirmed constraints that solution design must obey (Tier A/B access only, variable dimensions, fixed 5-min step, no early termination).
  - Evaluation and benchmark risks (overfitting to 30 pairings, quadratic comfort cliff).
  - Ranked open research hypotheses for Phase 03:
    - *H1*: Modular decentralized agents vs Graph Neural Networks for cross-building transfer.
    - *H2*: Online identification of thermal inertia $\tau$ from initial step responses to tune pre-conditioning onset.
    - *H3*: Night setback vs night floating in extreme subarctic climates.
  - Integrated conceptual map closing the Data Understanding phase.
- **Required diagrams or figures**:
  - *Figure 8.1*: The Integrated Conceptual Map of the Smart Buildings Data Environment (Final comprehensive Mermaid architecture).
- **Evidence references**: `06_DATA_UNDERSTANDING_SYNTHESIS.md`, `FINAL_HANDOFF.md`.
- **Limitations to preserve**: Offline data understanding is complete; policy training and hypothesis testing belong to Phase 03.
- **Connection to subsequent phases**: Explicit transition guidance authorizing Problem Formulation and Architecture Design.

---

## 2. Sequence Coherence & Dependency Verification

| Chapter | Dependent On | Forward Dependencies? | Validation Status |
|---|---|:---:|:---:|
| **Opening** | General domain literacy | None | PASS |
| **Chapter 1 (Origins)** | Opening overview | None | PASS |
| **Chapter 2 (Structure & Access)** | Origins (Ch 1) | None | PASS |
| **Chapter 3 (Quality & Trust)** | Files & Schemas (Ch 2) | None | PASS |
| **Chapter 4 (Buildings)** | Geometry & Materials (Ch 1, 2) | None | PASS |
| **Chapter 5 (Weather)** | Weather origins (Ch 1), Data quality (Ch 3) | None | PASS |
| **Chapter 6 (Simulator)** | Schemas (Ch 2), Buildings (Ch 4), Weather (Ch 5) | None | PASS |
| **Chapter 7 (Problem Synthesis)** | All preceding chapters | None | PASS |
| **Chapter 8 (Synthesis & Limits)** | Problem synthesis (Ch 7) | None | PASS |

---

## 3. P2 Completion Gate Review

```text
STAGE: P2 (KNOWLEDGE REORGANIZATION & CONTENT MAPPING)
STATUS: PASS

Completion Checklist:
- [x] All 8 chapters and opening designed around progressive reader understanding
- [x] Every substantive finding from P1 assigned an appropriate chapter location
- [x] All required numerical results, physical explanations, and evidence references specified
- [x] Dependency order verified: zero forward dependencies between chapters
- [x] Clear central reader questions established for every chapter
- [x] Duplication consolidated and technical completeness strictly preserved

Conclusion: The architectural plan is fully defined and ready for visual design.
Next Action: Proceed to Stage P3 (Explanation & Visual Design).
```
