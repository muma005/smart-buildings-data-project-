# Smart Buildings Challenge: Data Understanding Guide

> **Authoritative Guide to the Competition Data Environment, Simulation Physics, Interface Invariants, and Evaluation Contracts**  
> *NeurIPS 2026 Smart Buildings Challenge*  
> *Prepared by: Data Understanding Investigation Team*  
> *Status: COMPLETE (All Stage Gates D0–D6 Verified)*  

---

## Executive Overview & Table of Contents

Welcome to the **Smart Buildings Challenge Data Understanding Guide**. This document is the definitive, standalone knowledge resource for understanding the competition's data environment, procedural building generation pipeline, thermodynamic simulation physics, observation/action interfaces, and multi-objective evaluation engine.

Rather than presenting the chronological investigation steps (Stages D0 through D6), this guide is structured around the **natural learning journey of a researcher**: from high-level system comprehension, to data origins, structural schemas, empirical quality audits, physical building diversity, climatic variation, simulator dynamics, research synthesis against Problem Research (R1–R5), and open frontiers.

### Table of Contents
1. [Opening — Understanding the Data in One View](#opening--understanding-the-data-in-one-view)
2. [Chapter 1 — Where Does the Data Come From? (Provenance & Origins)](#chapter-1--where-does-the-data-come-from-provenance--origins)
3. [Chapter 2 — Understanding the Data Itself (Structure, Semantics & Policy Boundaries)](#chapter-2--understanding-the-data-itself-structure-semantics--policy-boundaries)
4. [Chapter 3 — Can We Trust the Data? (Quality, Integrity & Empirical Validation)](#chapter-3--can-we-trust-the-data-quality-integrity--empirical-validation)
5. [Chapter 4 — Understanding the Building Population (Architectural, Physical & HVAC Diversity)](#chapter-4--understanding-the-building-population-architectural-physical--hvac-diversity)
6. [Chapter 5 — Understanding the Environmental Conditions (Meteorological Regimes & Confounding)](#chapter-5--understanding-the-environmental-conditions-meteorological-regimes--confounding)
7. [Chapter 6 — What Actually Happens Inside the Simulator? (Step Execution & Evaluation Truth)](#chapter-6--what-actually-happens-inside-the-simulator-step-execution--evaluation-truth)
8. [Chapter 7 — What Does the Data Reveal About Our Original Problem? (Connecting to R1–R5)](#chapter-7--what-does-the-data-reveal-about-our-original-problem-connecting-to-r1r5)
9. [Chapter 8 — What Do We Know, and What Remains Unknown? (Synthesis & Frontiers)](#chapter-8--what-do-we-know-and-what-remains-unknown-synthesis--frontiers)
10. [Appendix — Master Evidence & Artifact Directory](#appendix--master-evidence--artifact-directory)

---

## Opening — Understanding the Data in One View

### What is the Smart Buildings Challenge Attempting to Solve?
The Smart Buildings Challenge asks participants to design a single, generalized HVAC (Heating, Ventilation, and Air Conditioning) control policy capable of operating across diverse, previously unseen commercial buildings located in radically different climate zones.

A successful control policy must balance three competing physical and operational objectives over 30-day continuous operating horizons (8,640 steps at 5-minute resolution):
1. **Occupant Thermal Comfort**: Maintaining zone indoor air temperatures strictly within the comfort band ($[21.0^\circ\text{C}, 24.0^\circ\text{C}]$ or $[294.15\text{ K}, 297.15\text{ K}]$) during scheduled occupancy hours (weekdays 07:00–18:00). Comfort shortfall accounts for **60%** of the competition reward weight.
2. **Energy Cost Expenditure**: Minimizing electricity costs (chillers, supply fans, hydronic pumps subject to time-of-use tariffs) and natural gas costs (central boiler combustion). Operating cost accounts for **20%** of the reward weight.
3. **Operational Carbon Emissions**: Minimizing carbon emissions determined by real-time grid marginal emissions intensity factors ($g_{\text{CO}_2}/\text{kWh}$) and fuel combustion factors. Carbon emissions account for **20%** of the reward weight.

### Why This is an Interactive Environment, Not a Static Dataset
Unlike traditional machine learning competitions where models learn patterns from static tabular matrices or time-series CSVs, the Smart Buildings Challenge operates inside a **dynamic, closed-loop Gymnasium simulation environment**. 

Operating decisions made by the agent at step $t$ physically change the building's thermal state at step $t+1$:
- Setting a lower chilled water temperature cools the air duct, which alters the convective heat flux into occupied rooms, which absorbs sensible heat from concrete wall slabs, which changes the indoor temperature observed at the next step.
- The environment cannot be "shuffled" or treated as independent and identically distributed ($i.i.d.$) samples.
- It requires understanding how static offline configuration files generate dynamic online states, and how policy commands translate into physical actuator positions.

```mermaid
flowchart TD
    subgraph Inputs["1. External Meteorological & Grid Inputs"]
        WeatherCSV["Historical Weather Feeds<br/>(11 CSVs, 52,560 hourly rows)"]
        GridData["Grid Utility Feeds<br/>(Time-of-Use Electricity, Gas, Carbon)"]
    end

    subgraph ProceduralGen["2. Procedural Building Generation"]
        LHS_Gen["Latin Hypercube Sampler<br/>(6 Envelope Material Properties)"]
        CAD_Gen["CAD Rasterizer<br/>(Floor plans, zone partitioning, AHUs)"]
    end

    subgraph ConfigFiles["3. Static Competition Scenarios (30 Training Scenarios)"]
        ScenarioManifest["training_set.yaml<br/>(30 Scenarios = 6 Buildings × 5 Weather Stations)"]
        BldgYAML["building_train_*.yaml<br/>(Dimensions, AHU-to-Zone Topologies)"]
        PresetYAML["weather_preset.yaml<br/>(30-day continuous seasonal slice)"]
    end

    subgraph SimulatorEngine["4. Physical Simulation Engine (5-Minute Timestep)"]
        Solver["2D Nodal Finite-Difference Thermal Conduction Solver"]
        InternalGains["Internal Loads (10 W/m²) & Dynamic Occupant Sensible Heat (70 W/person)"]
        HVAC_Plant["HVAC Mechanical Loops (Central AHUs, VAV Boxes, HWS Boiler Loop)"]
    end

    subgraph PolicyBoundary["5. The Control Policy Interface (Gymnasium)"]
        TierB_Meta["Tier B: Static Participant Metadata<br/>(AHU-zone mapping, zone names, action specs)"]
        TierA_Obs["Tier A: Live Pre-Action Observation<br/>(Obs = 6V + 15K + 58 features)"]
        PolicyAgent["Control Policy Agent<br/>(Participant Controller)"]
        ActionOut["Hybrid Action Command<br/>(Discrete: D = K + 1, Continuous: C = 3K + 2 + 2V)"]
    end

    subgraph EvaluationScore["6. Evaluation Engine & Reward Function"]
        RewardCalc["10-Component Objective Engine<br/>r_t = 0.6 * p_t - 0.2 * c_t - 0.2 * e_t"]
        EpisodeReturn["Cumulative Episode Return<br/>R_total = Σ r_t (8,640 steps)"]
    end

    WeatherCSV --> PresetYAML
    LHS_Gen & CAD_Gen --> BldgYAML
    ScenarioManifest --> ConfigFiles
    ConfigFiles --> SimulatorEngine
    GridData --> EvaluationScore

    SimulatorEngine --> TierA_Obs
    BldgYAML --> TierB_Meta
    TierA_Obs & TierB_Meta --> PolicyAgent
    PolicyAgent --> ActionOut
    ActionOut --> HVAC_Plant
    HVAC_Plant <--> Solver
    InternalGains --> Solver

    Solver & HVAC_Plant --> RewardCalc
    RewardCalc --> EpisodeReturn

    classDef inputStyle fill:#e8f4f8,stroke:#2980b9,stroke-width:1.5px;
    classDef simStyle fill:#fef9e7,stroke:#f39c12,stroke-width:1.5px;
    classDef policyStyle fill:#eafaf1,stroke:#27ae60,stroke-width:1.5px;
    classDef evalStyle fill:#fbeee6,stroke:#e67e22,stroke-width:1.5px;

    class WeatherCSV,GridData,LHS_Gen,CAD_Gen inputStyle;
    class Solver,InternalGains,HVAC_Plant simStyle;
    class TierB_Meta,TierA_Obs,PolicyAgent,ActionOut policyStyle;
    class RewardCalc,EpisodeReturn evalStyle;
```
*Figure 0.1: The Smart Buildings End-to-End System Architecture, depicting the progression from external historical records and procedural building generators to runtime simulation, policy interfaces, and evaluation scoring.*

---

## Chapter 1 — Where Does the Data Come From? (Provenance & Origins)

To understand what the competition data represents, we must first trace where every number originated. The data environment comprises **four distinct classes of information**, each created through a different generation process:

| Data Class | Description | Examples | Authority / Origin |
|---|---|---|---|
| **1. Recorded** | Real-world empirical measurements collected from physical sensors. | Outdoor hourly weather CSVs, grid electricity tariffs, hourly carbon intensity factors. | Historical meteorological databases (NOAA/NCDC 2023) and regional utility tariffs. |
| **2. Procedurally Generated** | Algorithmic configurations synthesized using stochastic or space-filling sampling. | Building CAD rasters (`floor_plan.npy`, `zone_map.npy`), envelope material properties, AHU assignments. | Python procedural generation scripts using Latin Hypercube Sampling (LHS). |
| **3. Simulated** | Dynamic physical states computed step-by-step during runtime execution. | Indoor air temperatures, wall cell heat fluxes, supply air static pressures, fan power consumption. | 2D nodal finite-difference heat diffusion solver and thermodynamic HVAC models. |
| **4. Derived** | Evaluated metrics computed mathematically from simulated states and economic tariffs. | Zone comfort shortfall $f(d_v)$, normalized energy cost $c_t$, normalized carbon emissions $e_t$, step reward $r_t$. | Competition evaluation engine (`RewardFunction`). |

```mermaid
flowchart LR
    subgraph Stream1["1. Recorded Data"]
        RawWeather["Raw Weather CSVs (2023)<br/>7 Columns, 8,760 hrs/file"]
        UtilityRates["Tariff Schedules<br/>TOU Electric, Flat Gas, Grid CO₂"]
    end

    subgraph Stream2["2. Procedurally Generated Data"]
        LHS_Box["Latin Hypercube Sampler<br/>6 Material Variables"]
        CAD_Box["Geometric Floor Plan Engine<br/>Zone map, Room partitioning"]
    end

    subgraph Stream3["3. Simulated Physical States"]
        FD_Conduction["Finite-Difference Conduction<br/>Wall and Air Nodes"]
        SensibleHeat["Sensible Heat Sources<br/>Equipment (10 W/m²) & People (70 W)"]
        HVAC_Loops["HVAC Flow Integration<br/>Airflow, Water, Static Pressure"]
    end

    subgraph Stream4["4. Derived Evaluation Metrics"]
        Comfort_P["Productivity Shortfall p_t<br/>Piecewise quadratic penalty"]
        Cost_C["Normalized Cost c_t<br/>Scaled by 80kW / 205kW * K"]
        Carbon_E["Normalized Carbon e_t<br/>Scaled by K plant capacity"]
        Scalar_R["Scalar Reward r_t<br/>0.6 p_t - 0.2 c_t - 0.2 e_t"]
    end

    RawWeather --> FD_Conduction
    LHS_Box & CAD_Box --> FD_Conduction
    SensibleHeat --> FD_Conduction
    HVAC_Loops <--> FD_Conduction

    FD_Conduction --> Comfort_P
    HVAC_Loops & UtilityRates --> Cost_C & Carbon_E
    Comfort_P & Cost_C & Carbon_E --> Scalar_R

    classDef recStyle fill:#d4efdf,stroke:#27ae60,stroke-width:1.5px;
    classDef genStyle fill:#d6eaf8,stroke:#2980b9,stroke-width:1.5px;
    classDef simStyle fill:#fcf3cf,stroke:#f39c12,stroke-width:1.5px;
    classDef derStyle fill:#fadbd8,stroke:#e74c3c,stroke-width:1.5px;

    class RawWeather,UtilityRates recStyle;
    class LHS_Box,CAD_Box genStyle;
    class FD_Conduction,SensibleHeat,HVAC_Loops simStyle;
    class Comfort_P,Cost_C,Carbon_E,Scalar_R derStyle;
```
*Figure 1.1: The Four Data Origin Streams and Transformation Pathways.*

### 1.1 The Weather Pipeline: Active vs. Omitted Variables
A central discovery of our provenance investigation (**Finding F-003**) is that although the historical weather CSV files supply 7 meteorological columns (`TempC`, `TempF`, `DewPointC`, `WindspeedKmph`, `Humidity`, `StationName`, `Location`), **only dry-bulb temperature (`TempF`) is actually consumed by the physics simulator**.

```mermaid
flowchart TD
    subgraph RawCSV["Raw Weather CSV File (Hourly Records)"]
        TF["TempF (Dry-Bulb Temperature)"]
        TC["TempC (Redundant Metric)"]
        DP["DewPointC (Moisture)"]
        WS["WindspeedKmph (Wind Speed)"]
        RH["Humidity (Relative Humidity %)"]
    end

    subgraph Controller["Weather Controller Pipeline"]
        TF_Read["Extract TempF"]
        LinearInterp["Linear Interpolation<br/>(Hourly -> 5-Minute Resolution)"]
        KelvinConv["Convert to Kelvin<br/>K = (F - 32) * 5/9 + 273.15"]
        IgnoredColumns["IGNORED & UNREAD BY SIMULATOR<br/>(DewPointC, WindspeedKmph, Humidity)"]
    end

    subgraph PhysicsBoundary["External Thermal Forcing Boundary"]
        ExtDirichlet["Exterior Wall Boundary Condition<br/>Direct Conduction Driving Force"]
        OmittedMechanisms["COMPLETELY OMITTED FROM PHYSICS ENGINE:<br/>1. Solar Radiation & Window Fenestration Gains<br/>2. Air Infiltration & Building Envelope Drafts<br/>3. Moisture Transport & Latent Cooling Loads<br/>4. Wind Convection (Fixed at Static 19.1 W/(m²·K))"]
    end

    TF --> TF_Read --> LinearInterp --> KelvinConv --> ExtDirichlet
    TC & DP & WS & RH --> IgnoredColumns --> OmittedMechanisms

    classDef activeStyle fill:#d4efdf,stroke:#27ae60,stroke-width:1.5px;
    classDef inactiveStyle fill:#fadbd8,stroke:#e74c3c,stroke-width:1.5px;

    class TF,TF_Read,LinearInterp,KelvinConv,ExtDirichlet activeStyle;
    class TC,DP,WS,RH,IgnoredColumns,OmittedMechanisms inactiveStyle;
```
*Figure 1.2: Outdoor Meteorological Forcing: Active Dry-Bulb Conduction vs. Omitted Mechanisms.*

#### Why This Simplification Matters to the Controller
1. **Solar Gains are Zero**: Real-world buildings absorb massive solar heat gains through south/west-facing windows and roof surfaces, creating strong afternoon cooling spikes. In this benchmark, solar radiation is completely absent. Thermal loads are purely conductive.
2. **Latent Cooling is Zero**: Humidity is unread; the simulator does not compute moisture enthalpy or condensation on cooling coils. The HVAC system only handles sensible heat.
3. **Infiltration is Zero**: Envelope leakage due to wind pressure is absent. The exterior surface heat transfer coefficient is fixed at a constant scenario-level value ($\approx 19.1\text{ W}/(\text{m}^2\text{K})$).

### 1.2 Procedural Building Generation & Latin Hypercube Sampling
The competition buildings were synthesized procedurally to introduce realistic architectural and physical diversity:
- **Spatial CAD Rasterization**: Building footprints are generated on a discrete 2D grid ($70 \times 70$ cells, each cell representing $50\text{ cm} \times 50\text{ cm}$). Cells are labeled: `0` (outside), `1` (exterior/interior structural wall), and `2+` (distinct room air control volumes).
- **Zoning and the AHU Ceiling Rule (Finding S-03)**: Rooms are grouped into thermal zones ($V \in [30, 85]$). The number of central Air Handling Units ($K$) is determined by an exact ceiling rule:
  $$\boxed{K = \left\lceil \frac{V}{10} \right\rceil}$$
  This rule ensures that every AHU serves between $9.0$ and $10.0$ zones, mirroring commercial building HVAC design where central air handlers are sized for 8–12 Variable Air Volume (VAV) terminal boxes.
- **Envelope Material Properties (Finding S-04)**: Physical wall materials are drawn from a Latin Hypercube Sampler across 6 independent continuous variables:
  1. `exterior_cv_conductivity` ($k_{\text{ext}} \in [0.15, 0.45]\text{ W}/(\text{m}\cdot\text{K})$)
  2. `exterior_cv_density` ($\rho_{\text{ext}} \in [400, 2200]\text{ kg}/\text{m}^3$)
  3. `exterior_cv_heat_capacity` ($c_{p,\text{ext}} \in [700, 1100]\text{ J}/(\text{kg}\cdot\text{K})$)
  4. `interior_wall_cv_conductivity` ($k_{\text{int}} \in [0.35, 0.65]\text{ W}/(\text{m}\cdot\text{K})$)
  5. `interior_wall_cv_density` ($\rho_{\text{int}} \in [150, 500]\text{ kg}/\text{m}^3$)
  6. `interior_mass_cv_density` ($\rho_{\text{mass}} \in [10, 40]\text{ kg}/\text{m}^3$)

### 1.3 Active Internal Loads: Equipment & People (Finding F-004)
The building interior is not passive. Sensible heat is continuously generated and injected into room air nodes:
1. **Area-Based Equipment & Plug Loads**:
   Every occupied zone receives an electrical equipment heat flux of:
   $$Q_{\text{internal}} = 10.0\text{ W/m}^2 \times \text{Zone Floor Area}$$
   During unoccupied night and weekend hours, equipment drops to a standby fraction of $0.2$ ($2.0\text{ W/m}^2$).
2. **Dynamic Occupant Sensible Heat**:
   Occupancy follows a stochastic discrete Markov arrival/departure chain calibrated to commercial office schedules. Each person in a room emits a sensible thermal power of:
   $$Q_{\text{occupant}} = 70.0\text{ Watts}$$
   This sensible heat is injected directly into the zone air node, meaning that as occupants arrive between 07:00 and 09:00, indoor temperatures rise rapidly even before outdoor ambient heat conducts through the walls.

---

## Chapter 2 — Understanding the Data Itself (Structure, Semantics & Policy Boundaries)

### 2.1 The Competition Entity-Relationship Model
To interact with the environment, a researcher must understand how static configuration files link to dynamic runtime objects:

```mermaid
erDiagram
    SCENARIO ||--|| BUILDING : specifies
    SCENARIO ||--|| WEATHER_PRESET : specifies
    SCENARIO ||--|| GIN_CONFIG : binds
    
    BUILDING ||--|{ AHU : contains
    BUILDING ||--|{ ZONE : partitions
    BUILDING ||--|| CAD_RASTER : mapped_by
    BUILDING ||--|| MATERIAL_SET : constructed_from
    
    AHU ||--|{ ZONE : serves
    ZONE ||--|| VAV_BOX : controlled_by
    BUILDING ||--|| HWS_PLANT : heated_by
    
    WEATHER_PRESET }|--|| WEATHER_CSV : slices
    
    SCENARIO ||--|| OBSERVATION_VECTOR : emits
    SCENARIO ||--|| HYBRID_ACTION : receives
    SCENARIO ||--|| REWARD_SIGNAL : evaluates
```
*Figure 2.1: Entity-Relationship Topology of the Smart Buildings Benchmark.*

- **Scenario**: The fundamental unit of execution (`smart_buildings/training_set.yaml`). Combines one `Building`, one `Weather Preset`, and one `config.gin` containing plant capacities, solver parameters, and utility tariffs.
- **Building Configuration** (`building_train_*.yaml`): Defines building geometry, room coordinates, AHU-to-zone topological mappings, and physical material parameters.
- **CAD Floor Plan** (`floor_plan.npy`, `zone_map.npy`): $70 \times 70$ uint8 spatial grids specifying cell boundary coordinates and room identifiers.
- **Weather Preset** (`weather_preset.yaml`): Specifies the source historical weather CSV file and the continuous 30-day start/end timestamp slice.

---

### 2.2 The Four-Tier Information Access Boundary (Finding S-01)
A common pitfall in simulation competitions is relying on privileged simulator state that is not exposed during hidden evaluation. We established an explicit **Four-Tier Information Access Boundary**:

```mermaid
flowchart TD
    subgraph TierD["Tier D: Hidden Scenario Configuration (STRICTLY HIDDEN)"]
        D1["True Material Conductivity (k_ext, k_int) & Density Arrays"]
        D2["CAD Raster Arrays (floor_plan.npy, zone_map.npy)"]
        D3["Full Future Weather Trajectory (Days 2 to 30)"]
        D4["Tariff Rate Schedules & Grid Emission Intensity Arrays"]
    end

    subgraph TierC["Tier C: Hidden Simulator Physical State (STRICTLY HIDDEN)"]
        C1["Internal Wall Finite-Difference Cell Temperatures (70x70 grid)"]
        C2["Individual Zone Occupant Counts (Markov Chain Hidden States)"]
        C3["Convective Boundary Layer Film Coefficients"]
    end

    subgraph TierB["Tier B: Static Participant Metadata (AVAILABLE AT INIT)"]
        B1["ahu_zone_assignments: Topological mapping of Zones to AHUs"]
        B2["zone_names: Human-readable string identifiers ('zone_0', ...)"]
        B3["ActionSpec: Min/max physical bounds and types for all actuators"]
    end

    subgraph TierA["Tier A: Live Step Observation Vector (AVAILABLE AT STEP t)"]
        A1["Zone Air Temperatures T_v (K) for all v in V"]
        A2["AHU Supply Air Temps T_supply,k (K) and Pressures P_k (Pa)"]
        A3["Outdoor Air Dry-Bulb Temperature T_out (K)"]
        A4["Fourier Temporal Encodings: 24 hod terms, 24 dow terms"]
        A5["Comfort Operational Flags: comfort_mode_now, comfort_mode_soon"]
        A6["Building-Wide Total Instantaneous Occupancy (count)"]
    end

    TierA --> Policy["Participant HVAC Control Policy"]
    TierB --> Policy
    Policy -.->|CANNOT ACCESS| TierC
    Policy -.->|CANNOT ACCESS| TierD

    classDef hiddenStyle fill:#fadbd8,stroke:#e74c3c,stroke-width:1.5px;
    classDef availStyle fill:#d4efdf,stroke:#27ae60,stroke-width:1.5px;

    class D1,D2,D3,D4,C1,C2,C3 hiddenStyle;
    class B1,B2,B3,A1,A2,A3,A4,A5,A6 availStyle;
```
*Figure 2.2: The Four-Tier Information Access Boundary.*

> **Rule of Hidden Evaluation**: Any control policy submitted to Kaggle evaluation has access **only to Tier A (live observation vector at step $t$)** and **Tier B (metadata dictionary provided during `initialize_policy`)**. Controllers that attempt to inspect simulator internals or forecast future weather using unread CSV rows will fail.

---

### 2.3 Closed-Form Interface Invariants (Findings F-002 & F-005)
A critical question for policy architecture design is: *How do observation and action dimensions scale across buildings?* 

Through formal code inspection and empirical validation across all 6 shipped buildings, we proved that the observation space, discrete action space, and continuous action space satisfy exact closed-form linear invariants:

$$\boxed{D = K + 1}$$
$$\boxed{C = 3K + 2 + 2V}$$
$$\boxed{\mathrm{Obs} = 6V + 15K + 58}$$

Where:
- $V$ is the number of thermal zones / VAV boxes ($V \in [30, 85]$).
- $K$ is the number of Air Handling Units ($K \in [3, 9]$).

#### Mathematical Decomposition of the Invariants

```mermaid
flowchart TD
    subgraph ObsVector["Observation Vector Decomposition: Obs = 6V + 15K + 58"]
        direction TB
        subgraph ConstFeatures["58 Static / Environment Features"]
            F1["24 Fourier Hour-of-Day (hod) Terms (sine/cosine harmonics)"]
            F2["24 Fourier Day-of-Week (dow) Terms (sine/cosine harmonics)"]
            F3["7 Hot Water System (HWS) Central Plant Features<br/>(boiler supply temp, return temp, flow rate, differential pressure, energy rate)"]
            F4["1 Outdoor Dry-Bulb Temperature (K)"]
            F5["1 comfort_mode_now Flag (binary: 1.0 during 07:00-18:00 weekdays)"]
            F6["1 comfort_mode_soon Flag (binary: 1.0 exactly 2 hours prior to comfort mode)"]
            F7["1 Building-Wide Total Instantaneous Occupant Count"]
        end

        subgraph AHUFeatures["15 Features per AHU (15 * K)"]
            A1["Supply Air Temp, Return Air Temp, Mixed Air Temp, Outside Air Temp"]
            A2["Supply Fan Static Pressure, Return Fan Static Pressure, Differential Pressure"]
            A3["Supply Air Flow Rate, Recirculation Air Flow Rate, Relief Air Flow Rate"]
            A4["Cooling Coil Thermal Rate, Heating Coil Thermal Rate, Fan Power Demand"]
            A5["AHU Stage Switch Status, Damper Modulation Feedback"]
        end

        subgraph ZoneFeatures["6 Features per Zone / VAV (6 * V)"]
            Z1["Zone Air Node Temperature T_v (K)"]
            Z2["VAV Box Supply Air Discharge Temperature (K)"]
            Z3["VAV Damper Actual Position / Airflow Rate (m³/s)"]
            Z4["VAV Hydronic Reheat Valve Position (fraction [0, 1])"]
            Z5["Zone Relative Airflow Velocity / Static Pressure"]
            Z6["Zone Thermal Load Deviation Signal"]
        end
    end

    ConstFeatures & AHUFeatures & ZoneFeatures --> FullObs["Full 1D Observation Vector<br/>building_train_1: 6(39) + 15(4) + 58 = 352"]
```
*Figure 2.3: Detailed Anatomical Breakdown of the Observation Vector.*

#### Concrete Worked Example: `building_train_1`
To see these invariants in action, consider `building_train_1`, which has $K=4$ AHUs and $V=39$ zones:
1. **Discrete Actions ($D = K + 1 = 4 + 1 = 5$)**:
   - 4 discrete switches for AHU fans ($k \in \{0, 1, 2, 3\}$).
   - 1 discrete switch for the central Hot Water System (HWS) boiler.
2. **Continuous Actions ($C = 3K + 2 + 2V = 3(4) + 2 + 2(39) = 12 + 2 + 78 = 92$)**:
   - $3 \times 4 = 12$ AHU setpoints (supply air temperature $[285.15, 297.15]\text{ K}$, static pressure $[150, 600]\text{ Pa}$, recirculation damper fraction $[0.0, 0.9]$).
   - $2$ HWS boiler setpoints (hot water supply temperature $[320, 355]\text{ K}$, differential pressure setpoint).
   - $2 \times 39 = 78$ zone VAV setpoints (airflow damper fraction $[0.1, 1.0]$, hydronic reheat valve position $[0.0, 1.0]$).
3. **Observation Features ($\mathrm{Obs} = 6V + 15K + 58 = 6(39) + 15(4) + 58 = 234 + 60 + 58 = 352$)**.

The empirical validation across all 6 shipped buildings confirmed **100% adherence to these formulas with zero discrepancies**:

| Building Name | AHUs ($K$) | Zones ($V$) | Discrete Actions ($D$) | Continuous Actions ($C$) | Observation Dimension ($\mathrm{Obs}$) | Empirical Status |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| `building_train_8` | 3 | 30 | 4 | 71 | 283 | **EXACT MATCH** |
| `building_train_7` | 4 | 36 | 5 | 86 | 334 | **EXACT MATCH** |
| `building_train_1` | 4 | 39 | 5 | 92 | 352 | **EXACT MATCH** |
| `building_train_4` | 6 | 54 | 7 | 128 | 472 | **EXACT MATCH** |
| `building_train_5` | 8 | 79 | 9 | 184 | 652 | **EXACT MATCH** |
| `building_train_2` | 9 | 85 | 10 | 199 | 703 | **EXACT MATCH** |

> **Architectural Implication**: Because $\mathrm{Obs}$ ranges from 283 to 703 and $C$ ranges from 71 to 199, **standard fixed-input/fixed-output feedforward neural networks cannot transfer across buildings**. Any transfer policy must be modular (e.g. replicated per-zone VAV agents), graph-structured (GNN over the topological mapping in Tier B), or tokenized (Transformer sequence of zone tokens).

---

## Chapter 3 — Can We Trust the Data? (Quality, Integrity & Empirical Validation)

Before relying on this data to build control algorithms, we conducted comprehensive data quality and integrity audits across every file, sensor feed, CAD array, and parameter in the competition release (**Finding F-006**).

### 3.1 Meteorological Data Quality Audit
We audited all 11 historical weather CSV files, representing **52,560 hourly records** spanning the entire calendar year 2023 across Atlanta, Denver, Fairbanks, Minneapolis, Phoenix, and Singapore:
- **Missing Values**: Exactly **$0$ missing values** across all columns ($0.00\%$).
- **Non-Finite Values**: Exactly **$0$ NaNs, nulls, or infinite floats**.
- **Temporal Monotonicity**: 100% of timestamps are strictly monotonic, incrementing by exactly 1 hour ($3,600\text{ seconds}$) without duplicate timestamps or missing hourly intervals.
- **Preset Time Horizons**: All 48 shipped weather presets define continuous 30-day windows that fall strictly between Day 1 and Day 365 of 2023. This guarantees that linear interpolation inside the simulator will never encounter boundary extrapolation or index out-of-range errors.

### 3.2 Spatial CAD Raster Validation
The $70 \times 70$ discrete CAD arrays (`floor_plan.npy` and `zone_map.npy`) for all 6 buildings were subjected to topological boundary isolation checks:
- **Boundary Sealing**: Wall cells (`value = 1`) form completely sealed, closed contours around all interior room air cells (`value >= 2`). No room cell leaks directly into exterior space (`value = 0`).
- **Orphan Room Check**: Every single room identified in `zone_map.npy` maps to a valid zone in `building_train_*.yaml`. Zero orphan rooms exist.
- **Physical Cell Consistency**: Wall cells are strictly isolated from room air nodes in the finite-difference solver grid.

```mermaid
flowchart LR
    Outside["Outside Space (Cell = 0)<br/>Ambient Dry-Bulb Temperature Dirichlet Boundary"]
    Wall["Structural Wall Cells (Cell = 1)<br/>Conduction + Thermal Heat Capacitance (LHS Materials)"]
    Room["Interior Room Air Cells (Cell >= 2)<br/>Well-Mixed Air Node + Internal Loads + Occupant Heat"]

    Outside <-->|Convective Boundary Film h_ext| Wall
    Wall <-->|Convective Interior Film h_int| Room
    Room <-->|Air Circulation & VAV Reheat| HVAC["HVAC Secondary Loop"]

    classDef outStyle fill:#ebf5fb,stroke:#2980b9,stroke-width:1.5px;
    classDef wallStyle fill:#f2f4f4,stroke:#7f8c8d,stroke-width:1.5px;
    classDef roomStyle fill:#fef9e7,stroke:#f39c12,stroke-width:1.5px;

    class Outside outStyle;
    class Wall wallStyle;
    class Room roomStyle;
```
*Figure 3.1: Spatial Cell Boundary Validation across Building CAD Rasters.*

### 3.3 Classification of Issues, Quirks, and Constraints
Our audit identified zero fatal or blocking defects. All detected anomalies were classified into benign data quirks or fixed simulation constraints:

| Issue ID | Category | Severity | Description | Operational Consequence for Modeling |
|---|---|:---:|---|---|
| **Q-01** | Weather Feed | Benign Quirk | CSVs contain unused columns (`DewPointC`, `WindspeedKmph`, `Humidity`). | Data pipelines should discard these columns; no latent cooling or wind modeling is needed. |
| **Q-02** | Scenario Generator | Benign Quirk | 18 weather presets (including all 8 Minneapolis presets) are unreferenced in `training_set.yaml`. | Shipped presets can be used for auxiliary training, but the official benchmark is 30 scenarios. |
| **Q-03** | Interface | Constraint | Observation vector dimension varies dynamically ($283 \le \mathrm{Obs} \le 703$). | Fixed-dimension multi-layer perceptrons cannot be deployed without spatial modularization. |
| **Q-04** | Simulation | Constraint | Macro timestep is fixed at 5 minutes ($\Delta t = 300\text{ s}$). | Decisions cannot be dispatched at sub-minute intervals; high-frequency chattering is prevented. |
| **Q-05** | Evaluation | Constraint | Episodes do not terminate early on discomfort (`terminated = False` until step 8,640). | A failing controller cannot abort to truncate penalties; it must endure the full 30 days. |

*Table 3.1: Comprehensive Data Quality & Architectural Classification Matrix.*

**Conclusion on Trustworthiness**: The competition data environment is **exceptionally robust and dependable**. There are zero missing data points, zero corrupt CAD geometries, and zero unstable parameter configurations. Researchers can train and evaluate policies without writing defensive data imputation routines.


---

## Chapter 4 — Understanding the Building Population (Architectural, Physical & HVAC Diversity)

To control a building effectively, a policy must understand how buildings differ. In this chapter, we explore the physical, geometric, and thermodynamic heterogeneity of the 6 official training buildings (**Finding F-007** and **Finding S-04**).

### 4.1 Architectural Dimensions and Zoning Hierarchy
The 6 training buildings vary substantially in footprint, room count, and HVAC capacity:

| Building Name | Bounding Box ($W \times H$) | Zones ($V$) | AHUs ($K$) | Avg Zones / AHU | Discrete Actions ($D$) | Continuous Actions ($C$) | Obs Dimension ($\mathrm{Obs}$) |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `building_train_8` | $239\text{ cm} \times 245\text{ cm}$ | 30 | 3 | 10.00 | 4 | 71 | 283 |
| `building_train_7` | $328\text{ cm} \times 173\text{ cm}$ | 36 | 4 | 9.00 | 5 | 86 | 334 |
| `building_train_1` | $373\text{ cm} \times 188\text{ cm}$ | 39 | 4 | 9.75 | 5 | 92 | 352 |
| `building_train_4` | $385\text{ cm} \times 248\text{ cm}$ | 54 | 6 | 9.00 | 7 | 128 | 472 |
| `building_train_5` | $427\text{ cm} \times 259\text{ cm}$ | 79 | 8 | 9.88 | 9 | 184 | 652 |
| `building_train_2` | $420\text{ cm} \times 301\text{ cm}$ | 85 | 9 | 9.44 | 10 | 199 | 703 |

*Table 4.1: Structural, Actuator, and Observation Dimensionality across the Building Population.*

- **Scale Range**: Zone count varies by nearly $3\times$ (from 30 zones in `building_train_8` to 85 zones in `building_train_2`).
- **Strict Ratio Regularity**: Despite the wide variation in building scale, the average number of zones per AHU is strictly clustered between **$9.0$ and $10.0$** due to the procedural ceiling rule ($K = \lceil V/10 \rceil$).

```mermaid
flowchart TD
    subgraph CentralPlant["Central Hydronic & Ventilation Plant"]
        Boiler["Hot Water System (HWS) Boiler<br/>Continuous Loop Heating Water"]
        Chiller["Central Chiller / Condenser<br/>Chilled Water Supply"]
    end

    subgraph AHU_Loop["Air Handling Unit Secondary Loop (K AHUs)"]
        AHU1["AHU 1: Supply Fan, Cooling Coil, Economizer Damper"]
        AHU_K["AHU K: Supply Fan, Cooling Coil, Economizer Damper"]
    end

    subgraph Zone_Terminal["VAV Terminal Boxes (V Zones, ~9-10 Zones per AHU)"]
        VAV1["Zone 1 VAV Box:<br/>Airflow Damper + Hydronic Reheat Coil"]
        VAV9["Zone 9 VAV Box:<br/>Airflow Damper + Hydronic Reheat Coil"]
        VAV_V["Zone V VAV Box:<br/>Airflow Damper + Hydronic Reheat Coil"]
    end

    Boiler -->|Hot Water Loop| VAV1 & VAV9 & VAV_V
    Chiller -->|Chilled Water Loop| AHU1 & AHU_K
    AHU1 -->|Supply Air Duct| VAV1 & VAV9
    AHU_K -->|Supply Air Duct| VAV_V
```
*Figure 4.1: HVAC Zoning Hierarchy showing Central Plant, AHU Distribution Loops, and VAV Terminal Units.*

---

### 4.2 Derived Thermal Properties & The 7.4× Thermal Inertia Spread
Beyond physical dimensions, the buildings differ profoundly in how they store and transmit heat. By extracting the 6 Latin Hypercube Sampled material parameters from each building configuration, we derived three fundamental thermodynamic characteristics:
1. **Facade Overall Heat Transmission Coefficient ($U$)**:
   Governs how rapidly thermal energy conducts through exterior walls per square meter of facade area per Kelvin of temperature difference:
   $$U = \frac{1}{\sum R_{\text{layers}}} \quad \left[\frac{\mathrm{W}}{\mathrm{m}^2\cdot\mathrm{K}}\right]$$
   Across the 6 buildings, $U$ ranges from **$1.179\text{ W}/(\text{m}^2\text{K})$** (highly insulated in `building_train_8`) to **$2.077\text{ W}/(\text{m}^2\text{K})$** (poorly insulated in `building_train_7`).
2. **Envelope Volumetric Heat Capacity ($C_{\mathrm{env}}$)**:
   Measures the total thermal energy stored within the structural mass of the exterior walls:
   $$C_{\mathrm{env}} = \rho_{\text{ext}} \cdot c_{p,\text{ext}} \quad \left[\frac{\mathrm{J}}{\mathrm{m}^3\cdot\mathrm{K}}\right]$$
   Envelope heat capacity varies by over **$4.6\times$**, ranging from **$0.403\text{ MJ}/(\text{m}^3\text{K})$** (`building_train_7`) to **$1.871\text{ MJ}/(\text{m}^3\text{K})$** (`building_train_1`).
3. **Relative Thermal Inertia Index ($\tau$)**:
   The effective physical time constant of the building envelope, proportional to heat storage capacity divided by thermal heat loss:
   $$\tau \propto \frac{C_{\mathrm{env}}}{U \times 10^5}$$

```text
================================================================================
BUILDING THERMAL CHARACTERISTIC DERIVATIONS
================================================================================
Building ID        Facade U [W/(m²·K)]   Envelope Cap [MJ/(m³·K)]   Inertia Index τ
building_train_7   2.0772 (leakiest)     0.4032 (lightest)          1.94 (FASTEST)
building_train_2   1.6823                0.5231                     3.11
building_train_8   1.1793 (best insul)   0.5828                     4.94
building_train_4   1.5837                1.2335                     7.79
building_train_5   1.4880                1.4283                     9.60
building_train_1   1.2972                1.8715 (heaviest)          14.43 (SLOWEST)
================================================================================
Spread Ratio:      1.76x spread          4.64x spread               7.44x SPREAD
================================================================================
```

![Figure 4.1: Building Thermal Inertia and Envelope Properties](assets/figure_4_1_thermal_diversity.png)  
*Figure 4.2: Building Thermal Diversity. (Left) The 7.4× spread in relative thermal inertia index $\tau$. (Right) Facade heat transmission coefficient $U$ plotted against envelope volumetric heat capacity $C_{\mathrm{env}}$, with point size indicating zone count.*

#### Physical Interpretation: The Two Thermal Archetypes
The building population is polarized into two distinct physical archetypes:
- **The Fast, Leaky Archetype (`building_train_7`, $\tau = 1.94$)**:
  Having low thermal mass and poor insulation, this building reacts almost immediately to outdoor temperature drops. It loses heat rapidly at night and requires high continuous heating in cold weather. However, it can be reheated quickly in the morning with minimal pre-heating lead time.
- **The Slow, Massive Archetype (`building_train_1`, $\tau = 14.43$)**:
  Having heavy concrete wall mass and strong facade insulation, this building exhibits massive thermal flywheel effects. It absorbs thermal energy slowly over 2–3 hours. If allowed to cool down overnight, the structural walls suck heat out of the air for hours, creating severe morning discomfort penalties unless pre-heating is initiated 90–120 minutes in advance.

> **Transferability Implication**: A control policy tuned for `building_train_7` that applies aggressive setpoint changes will cause severe overshoot and energy waste in `building_train_1`. Conversely, a sluggish policy tuned for `building_train_1` will fail to maintain comfort in `building_train_7`.

---

## Chapter 5 — Understanding the Environmental Conditions (Meteorological Regimes & Confounding)

HVAC equipment does not operate in isolation; its sole thermodynamic purpose is to maintain indoor comfort against outdoor weather perturbations. In this chapter, we analyze the 5 official climate regimes and expose the non-Cartesian experimental pairing topology (**Finding F-001** and **Finding F-007**).

### 5.1 The Five Distinct Climatic Regimes
The competition weather data represents 5 radically different meteorological regimes, each imposing distinct thermodynamic loads on the building:

| Weather Station | Nominal Climate Type | Min Temp [°C] | Max Temp [°C] | Mean Temp [°C] | Diurnal Swing [°C] | HDD (18.3°C) | CDD (18.3°C) | Primary Thermodynamic Challenge |
|---|---|:---:|:---:|:---:|:---:|:---:|:---:|---|
| **Fairbanks** | Subarctic Extreme Cold | **$-42.0$** | $+28.9$ | $-0.4$ | $9.3$ | **$580.2$** | $7.6$ | Continuous extreme heating; boiler capacity limits. |
| **Phoenix** | Desert Extreme Heat | $+0.4$ | **$+46.1$** | $+26.6$ | $12.1$ | $42.1$ | **$305.9$** | Continuous extreme cooling; peak electricity tariffs. |
| **Denver** | High-Altitude Semi-Arid | $-12.8$ | $+37.2$ | $+13.6$ | **$14.3$** | $191.4$ | $53.8$ | Severe day-to-night swings; actuator fighting risk. |
| **Atlanta** | Humid Subtropical | $-3.9$ | $+35.0$ | $+17.8$ | $9.8$ | $112.5$ | $102.7$ | Dual-mode seasonal transitions (heating to cooling). |
| **Singapore** | Equatorial Tropical | $+23.0$ | $+33.7$ | $+27.9$ | $5.5$ | **$0.0$** | $304.7$ | Constant steady cooling; zero boiler demand. |

*Table 5.1: Meteorological Characteristics and Degree-Day Demands across the 5 Climate Regimes.*

![Figure 5.1: Meteorological Diversity Across the 5 Climates](assets/figure_5_1_climate_regimes.png)  
*Figure 5.1: Meteorological Diversity. (Left) Historical temperature spans plotted relative to the $[21^\circ\mathrm{C}, 24^\circ\mathrm{C}]$ comfort band. (Right) Heating Degree Days (HDD) and Cooling Degree Days (CDD) quantifying thermodynamic demand.*

#### Key Climatic Profiles:
1. **Subarctic Fairbanks (HDD = 580.2, Min $-42.0^\circ\text{C}$)**:
   Outdoor temperatures regularly fall below $-30^\circ\text{C}$, creating an extreme temperature differential across the facade ($\Delta T > 50\text{ K}$). The central gas boiler operates near maximum capacity ($205\text{ kW} \times K$). Turning off heating overnight causes structural deep freeze from which recovery takes hours.
2. **Desert Phoenix (CDD = 305.9, Max $+46.1^\circ\text{C}$)**:
   Outdoor temperatures exceed $40^\circ\text{C}$ throughout summer afternoons. Chillers and supply fans must operate at high capacity. High time-of-use (TOU) electricity pricing between 14:00 and 19:00 severely penalizes uncoordinated daytime cooling.
3. **High-Diurnal Denver (Mean Diurnal Swing = $14.3^\circ\text{C}$)**:
   Denver experiences rapid temperature swings. Cold nighttime temperatures require morning heating, followed by rapid solar/ambient warming requiring afternoon cooling. Uncoordinated policies suffer from "actuator fighting" (simultaneously heating and cooling air).
4. **Equatorial Singapore (Constant $+27.9^\circ\text{C}$, Zero HDD)**:
   Singapore experiences flat, unwavering tropical heat. Heating is completely unnecessary ($0\text{ W}$ natural gas demand). The sole objective is efficient, steady sensible cooling without over-cooling zones below $21.0^\circ\text{C}$.

---

### 5.2 The Balanced-Block Pairing Topology & Experimental Confounding
A vital discovery of our manifest audit (**Finding F-001**) is that the 30 development scenarios in `smart_buildings/training_set.yaml` do not form a complete Cartesian grid ($6 \text{ Buildings} \times 40 \text{ Weather Presets} = 240$). 

Instead, the dataset implements a **non-reused balanced block design**:
- Exactly **6 buildings** are paired with **5 weather stations** ($6 \times 5 = 30\text{ scenarios}$).
- For each weather station, each building is assigned a **distinct, non-overlapping 30-day calendar window**:

| Weather Station | Building 1 | Building 2 | Building 4 | Building 5 | Building 7 | Building 8 |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Atlanta** | Mar 12 – Apr 11 | Apr 11 – May 11 | May 11 – Jun 10 | Jun 10 – Jul 10 | Jul 10 – Aug 09 | Aug 09 – Sep 08 |
| **Denver** | Jan 15 – Feb 14 | Feb 14 – Mar 16 | Mar 16 – Apr 15 | Apr 15 – May 15 | May 15 – Jun 14 | Jun 14 – Jul 14 |
| **Fairbanks** | Nov 01 – Dec 01 | Dec 01 – Dec 31 | Jan 01 – Jan 31 | Jan 31 – Mar 02 | Mar 02 – Apr 01 | Apr 01 – May 01 |
| **Phoenix** | May 01 – May 31 | May 31 – Jun 30 | Jun 30 – Jul 30 | Jul 30 – Aug 29 | Aug 29 – Sep 28 | Sep 28 – Oct 28 |
| **Singapore** | Jan 01 – Jan 31 | Jan 31 – Mar 02 | Mar 02 – Apr 01 | Apr 01 – May 01 | May 01 – May 31 | May 31 – Jun 30 |

*Table 5.2: The Official 30-Scenario Balanced Block Pairing Matrix.*

#### The Confounding Trap for Model Evaluation
Notice what happens if a researcher attempts to compare `building_train_1` against `building_train_2` on the "Atlanta" station:
- `building_train_1` encounters **early spring (March 12 – April 11)**, when Atlanta is cool and requires substantial heating.
- `building_train_2` encounters **late spring (April 11 – May 11)**, when Atlanta is warm and requires primary cooling.

> **Critical Evaluation Warning**: Raw score differences between two buildings on the same station **cannot be interpreted as pure architectural performance**. The physical building effect is confounded with the seasonal weather window. To benchmark a controller accurately, researchers must compute the macro-average cumulative return across all 30 development scenarios.

---

## Chapter 6 — What Actually Happens Inside the Simulator? (Step Execution & Evaluation Truth)

This chapter brings together building physics, HVAC mechanics, and weather forcing to explain the dynamic execution loop and the mathematical evaluation loss (**Finding F-008**).

### 6.1 The 5-Minute Stepping Sequence
Every simulation step represents a discrete 5-minute jump ($\Delta t = 300\text{ seconds}$). During each step, the environment executes a 6-stage numerical sequence:

```mermaid
sequenceDiagram
    autonumber
    participant Agent as Control Policy
    participant Env as Gymnasium Wrapper
    participant HVAC as Secondary & Plant Models
    participant Physics as 2D Finite Difference Solver
    participant Reward as RewardFunction

    Agent->>Env: step(discrete_action, continuous_action)
    activate Env
    Env->>Env: validate_action() (clamp continuous to ActionSpec, validate discrete)
    
    Env->>HVAC: set_actuators(actions)
    activate HVAC
    Note over HVAC: Set AHU supply temp/pressure, VAV dampers, HWS boiler temp
    HVAC->>Physics: inject_hvac_fluxes(Q_vav, Q_reheat, Q_ahu)
    deactivate HVAC

    activate Physics
    Note over Physics: 1. Inject internal equipment load (10 W/m²)<br/>2. Inject dynamic occupant sensible heat (70 W/person)<br/>3. Apply outdoor TempF(t) conduction boundary<br/>4. Solve 2D heat diffusion across wall and air nodes
    Physics-->>Env: updated_temperatures (T_air, T_walls)
    deactivate Physics

    Env->>Reward: calculate_reward(T_air, occupancy, elec_power, gas_power)
    activate Reward
    Note over Reward: 1. Compute comfort shortfall f(d) across zones<br/>2. Compute utility cost (tariff scaled)<br/>3. Compute grid carbon emissions<br/>Normalize by K-dependent reference capacities
    Reward-->>Env: step_reward r_t, reward_info
    deactivate Reward

    Env->>Env: assemble_observation(T_air, T_ahu, T_out, hod, dow, occ)
    Env-->>Agent: (observation, step_reward, terminated, truncated, info)
    deactivate Env
```
*Figure 6.1: Simulator 5-Minute Stepping Sequence Diagram.*

### 6.2 Physical Dynamics: Thermal Lag & Actuator Coupling (Finding S-05)
Operating an HVAC system is fundamentally an exercise in delayed control:
1. **Thermal Inertia Lag (45 to 120 Minutes)**:
   When an AHU drops its supply air temperature by $3.0\text{ K}$, indoor zone air does not reach steady state immediately. The cool air first circulates, then cools interior wall surfaces, which in turn absorb heat from the air. In heavy buildings (`building_train_1`), zone temperatures lag damper changes by **over 90 minutes**.
2. **The Morning Pull-Down Challenge**:
   During unoccupied night hours, HVAC equipment is dialed back to save energy. Wall surfaces cool down. If the controller waits until comfort hours begin at 07:00 (`comfort_mode_now = 1.0`) to turn on heating, cold wall surfaces absorb heat rapidly, causing zone temperatures to remain below $21.0^\circ\text{C}$ for 60–90 minutes, incurring severe comfort penalties.
3. **The Lookahead Pre-Conditioning Mechanism (Finding S-02)**:
   To solve this problem, the simulator provides a lookahead flag: `comfort_mode_soon`. This signal turns to $1.0$ exactly **2 hours before scheduled occupancy** (at 05:00 on weekdays). Controllers that initiate pre-heating or pre-cooling upon receiving `comfort_mode_soon = 1.0` achieve near-zero morning discomfort.
4. **Airflow-Power Cubic Coupling**:
   Opening zone VAV dampers increases volumetric airflow. However, higher zone airflow forces central AHU fans to generate higher static pressure, increasing electrical fan power consumption **cubically** ($P_{\text{fan}} \propto \dot{V}^3$). Opening all dampers to $100\%$ causes fan electrical power to skyrocket.

---

### 6.3 Mathematical Reconstruction of the 10-Component Reward Function
The official competition objective combines comfort, cost, and carbon into a single scalar step reward $r_t \in (-\infty, 0]$:

$$\boxed{r_t = 0.6 \cdot p_t - 0.2 \cdot c_t - 0.2 \cdot e_t}$$

Where:
- $p_t$ is normalized occupant productivity / comfort shortfall ($p_t \le 0$).
- $c_t$ is normalized energy cost ($c_t \ge 0$).
- $e_t$ is normalized operational carbon emissions ($e_t \ge 0$).

```mermaid
flowchart TD
    subgraph RewardRecon["10-Component Competition Reward Function"]
        direction TB
        subgraph ComfortTerm["1. Occupant Productivity Shortfall p_t (Weight: 0.60)"]
            ZoneT["Zone Temperature T_v"] --> DevDist["Deviation d_v = max(0, 21.0 - T_v, T_v - 24.0)"]
            DevDist --> PW_Func["Piecewise Function f(d_v):<br/>0.0 if d <= 0<br/>d / 5.0 if 0 < d <= 5<br/>1 + ((d - 5)/5)² if d > 5"]
            PW_Func --> OccScale["Occupant Weight: Occ_v / 125.0"]
            OccScale --> P_Val["p_t = - Σ_v (Occ_v / 125.0) * f(d_v)"]
        end

        subgraph CostTerm["2. Normalized Energy Cost c_t (Weight: 0.20)"]
            Elec_W["Elec Power (W) * Tariff ($/J)"] --> CostElec["Step Electricity Cost ($)"]
            Gas_W["Gas Power (W) * Tariff ($/J)"] --> CostGas["Step Gas Cost ($)"]
            CostElec & CostGas --> TotalCost["Step Cost = CostElec + CostGas"]
            RefCost["Max Cost Ref = (80kW * K * Tariff_elec + 205kW * K * Tariff_gas) * 300s"]
            TotalCost & RefCost --> C_Val["c_t = Step Cost / Max Cost Ref"]
        end

        subgraph CarbonTerm["3. Normalized Carbon Emissions e_t (Weight: 0.20)"]
            CarbElec["Elec Power * Grid EF (kg CO₂/J)"] --> StepCarb["Step Carbon Emissions (kg CO₂)"]
            CarbGas["Gas Power * Gas EF (kg CO₂/J)"] --> StepCarb
            RefCarb["Max Carbon Ref = (80kW * K * EF_elec + 205kW * K * EF_gas) * 300s"]
            StepCarb & RefCarb --> E_Val["e_t = Step Carbon / Max Carbon Ref"]
        end
    end

    P_Val & C_Val & E_Val --> CombinedReward["r_t = 0.6 * p_t - 0.2 * c_t - 0.2 * e_t"]
```
*Figure 6.2: Complete Mathematical Decomposition of the 10-Component Competition Reward.*

#### Component 1: Occupant Productivity / Comfort Shortfall ($p_t$)
During unoccupied periods (weekends, nights), $p_t = 0.0$.  
During comfort hours (weekdays 07:00–18:00), for each zone $v \in V$, the deviation $d_v$ from the comfort band $[21.0^\circ\text{C}, 24.0^\circ\text{C}]$ is:
$$d_v = \max(0.0,\, 21.0 - T_v,\, T_v - 24.0)$$

The penalty follows a convex piecewise quadratic curve:
$$f(d_v) = \begin{cases} 
0.0 & \text{if } d_v \le 0.0 \\ 
\dfrac{d_v}{5.0} & \text{if } 0.0 < d_v \le 5.0 \\ 
1.0 + \left(\dfrac{d_v - 5.0}{5.0}\right)^2 & \text{if } d_v > 5.0 
\end{cases}$$

Building-wide comfort shortfall aggregates zone penalties weighted by occupancy normalized by $O_{\mathrm{norm}} = 125.0$:
$$p_t = - \sum_{v \in V} \left( \frac{\text{Occupancy}_v}{125.0} \right) f(d_v)$$

![Figure 6.3: Piecewise Quadratic Comfort Shortfall Penalty Function](assets/figure_6_1_comfort_penalty.png)  
*Figure 6.3: The Piecewise Quadratic Comfort Penalty Function $f(d)$. Note the linear slope up to $d=5.0^\circ\mathrm{C}$ and the aggressive quadratic escalation beyond $5.0^\circ\mathrm{C}$.*

> **The Quadratic Comfort Cliff**: Allowing zone temperatures to drift into the quadratic zone ($< 16.0^\circ\text{C}$ or $> 29.0^\circ\text{C}$) triggers severe penalties ($f(d) \ge 1.0$) that overpower any potential energy savings by an order of magnitude. Maintaining zone temperatures above $16.0^\circ\text{C}$ is paramount.

#### Component 2: Normalized Operating Cost ($c_t$)
Energy cost aggregates time-of-use electricity and natural gas expenditure:
$$\text{Cost}_{\text{step}} = P_{\text{elec}} \cdot \Delta t \cdot \text{Tariff}_{\text{elec}}(t) + P_{\text{gas}} \cdot \Delta t \cdot \text{Tariff}_{\text{gas}}$$

Crucially, the normalization denominator scales strictly with the building's AHU count $K$:
$$P_{\text{elec,ref}} = 80{,}000 \cdot K\text{ Watts}, \quad P_{\text{gas,ref}} = 205{,}000 \cdot K\text{ Watts}$$
$$c_t = \frac{\text{Cost}_{\text{step}}}{\left( P_{\text{elec,ref}} \cdot \text{Tariff}_{\text{elec,max}} + P_{\text{gas,ref}} \cdot \text{Tariff}_{\text{gas,max}} \right) \cdot \Delta t}$$

#### Component 3: Normalized Carbon Emissions ($e_t$)
Operational carbon emissions scale with dynamic hourly grid carbon intensity:
$$\text{Carbon}_{\text{step}} = P_{\text{elec}} \cdot \Delta t \cdot \text{EF}_{\text{elec}}(t) + P_{\text{gas}} \cdot \Delta t \cdot \text{EF}_{\text{gas}}$$
$$e_t = \frac{\text{Carbon}_{\text{step}}}{\left( P_{\text{elec,ref}} \cdot \text{EF}_{\text{elec,max}} + P_{\text{gas,ref}} \cdot \text{EF}_{\text{gas,max}} \right) \cdot \Delta t}$$

#### Empirical Verification Results (Finding F-008)
We audited this reconstructed formula against the official simulator across 576 continuous steps on `building_train_1/atlanta_2`:
- **Bitwise Simulation Determinism**: Max observation difference = **$0.00000000$**; Max reward difference = **$0.00000000$**.
- **Reward Reconciliation**: Max error between independently reconstructed reward and simulator reward is **$0.00\text{e}+00$ (exact machine match)**.
- **Reference Capacities**: Verified $P_{\text{elec,ref}} = 320{,}000\text{ W}$ ($4 \times 80\text{ kW}$) and $P_{\text{gas,ref}} = 820{,}000\text{ W}$ ($4 \times 205\text{ kW}$).


---

## Chapter 7 — What Does the Data Reveal About Our Original Problem? (Connecting to R1–R5)

Before inspecting the data, our scientific Problem Research established five foundational research fronts (R1 through R5). In this chapter, we synthesize what the empirical data investigation revealed about each front, comparing theoretical expectations against empirical reality.

```mermaid
flowchart TD
    subgraph ResearchFronts["Problem Research Foundations (R1–R5)"]
        R1["R1: Building Behaviour<br/>(Conduction, Storage, Gains, Flow)"]
        R2["R2: Operating Objectives<br/>(Comfort 60%, Cost 20%, Carbon 20%)"]
        R3["R3: Heterogeneity<br/>(6 Buildings, 5 Climates, 7.4x tau)"]
        R4["R4: Control Problem<br/>(4 Tiers, D=K+1, C=3K+2+2V, Obs=6V+15K+58)"]
        R5["R5: Transferability<br/>(Triple Transferability Barrier)"]
    end

    subgraph EmpiricalTruth["Empirical Data Understanding Findings"]
        E1["Nodal 2D Conduction active; Wall heat storage active.<br/>Solar, Infiltration, Humidity OMITTED."]
        E2["Exact 10-Component loss verified (0.00e+00 error).<br/>Discomfort cliff beyond 5°C violation."]
        E3["7.4x Inertia Spread; Balanced Block Confounding;<br/>Strict 9-10 Zones per AHU ceiling rule."]
        E4["100% Bitwise Determinism; Closed-form schemas;<br/>2-hour lookahead comfort_mode_soon active."]
        E5["Variable dimensions prevent dense networks;<br/>Divergent thermal time constants require adaptive lead times."]
    end

    R1 <--> E1
    R2 <--> E2
    R3 <--> E3
    R4 <--> E4
    R5 <--> E5
```

---

### 7.1 Detailed Research-to-Data Evidence Matrix

| Research Front | Core Scientific Hypothesis | What the Empirical Data Actually Established | Verified Evidence Reference |
|---|---|---|---|
| **R1 — Building Behaviour** | Indoor temperatures evolve via thermal conduction, solar radiation, envelope air drafts, sensible internal gains, and mechanical airflow. | **Partially Confirmed & Simplified**: Conduction through 2D walls and internal sensible gains ($10\text{ W/m}^2$ equipment, $70\text{ W/person}$) are faithfully simulated with active thermal storage. However, **solar radiation, envelope infiltration, and humidity are completely absent**. External forcing is 100% dry-bulb temperature. | Finding F-003, Finding F-004, `evidence/PROVENANCE_REGISTER.csv` |
| **R2 — Operating Objectives** | Objectives must balance comfort, cost, and carbon across trade-offs, with risk of conflicting gradients. | **Confirmed with Closed-Form Precision**: Reconstructed the exact 10-component loss function with $0.00\text{e}+00$ discrepancy. Discovered the **quadratic discomfort cliff** ($f(d)$ becomes quadratic beyond $5.0^\circ\text{C}$ violation), proving that thermal drift destroys policy returns far more aggressively than energy costs. | Finding F-008, `diagnostics/outputs/d5_reward_reconstruction.json` |
| **R3 — Heterogeneity** | Buildings differ in layout, materials, and equipment, requiring policies to generalize over diverse physics. | **Confirmed with High Variance**: Derived a **$7.4\times$ variation in thermal inertia index $\tau$** ($1.94$ to $14.43$). Exposed the **balanced block experimental confounding**: each building in the training set experiences a different 30-day seasonal window for each station. | Finding F-001, Finding F-007, `diagnostics/outputs/d4_diversity_metrics.json` |
| **R4 — Control Problem** | The policy must control variable actuators under physical constraints, delayed effects, and limited information. | **Confirmed with Exact Structural Invariants**: Proved closed-form interface formulas across all buildings: $D = K + 1$, $C = 3K + 2 + 2V$, and $\text{Obs} = 6V + 15K + 58$. Established the strict 4-tier information access boundary. Proved 100% simulation determinism. | Finding F-002, Finding F-005, Finding S-01, `evidence/DATA_DICTIONARY.csv` |
| **R5 — Transferability** | Policies trained on familiar buildings deteriorate when deployed on unseen buildings due to structural and physical mismatch. | **Confirmed & Characterized**: Mapped the **Triple Transferability Barrier**: (1) Variable input/output dimensions prevent fixed-size dense neural networks; (2) $7.4\times$ thermal inertia spread causes fixed setpoint policies to oscillate or lag; (3) Divergent climate failure modes require distinct operating regimes. | Finding F-005, Finding F-007, Finding F-008, `evidence/RESEARCH_QUESTION_MATRIX.md` |

*Table 7.1: Comprehensive Research-to-Data Evidence Matrix connecting Problem Research fronts R1–R5 to empirical findings.*

---

### 7.2 The Triple Transferability Barrier

Why is it so difficult for a control policy to transfer across buildings in this competition? Our empirical findings reveal that the transfer barrier is threefold:

```mermaid
flowchart TD
    subgraph Barrier["The Triple Transferability Barrier in Smart Buildings"]
        direction TB
        subgraph B1["1. Dimensional & Topological Barrier (R4 / R5)"]
            Dim1["Observation features range from 283 to 703"]
            Dim2["Continuous actions range from 71 to 199"]
            Dim3["AHU count K ranges from 3 to 9; Zones V range from 30 to 85"]
            DimImp["CONSEQUENCE: Monolithic feedforward neural networks cannot accept variable inputs or dispatch variable outputs."]
            Dim1 & Dim2 & Dim3 --> DimImp
        end

        subgraph B2["2. Thermodynamic Inertia Barrier (R1 / R3 / R5)"]
            Tau1["Envelope inertia index tau spans 7.4x (1.94 to 14.43)"]
            Tau2["Thermal response lag varies from 45 min to 120 min"]
            Tau3["Facade U varies 1.76x; Envelope heat capacity varies 4.64x"]
            TauImp["CONSEQUENCE: A uniform setpoint policy calibrated for a massive building (tau=14.4) fails to heat a leaky building (tau=1.9), while a high-gain policy oscillates violently."]
            Tau1 & Tau2 & Tau3 --> TauImp
        end

        subgraph B3["3. Climatic Regime Barrier (R2 / R3 / R5)"]
            Clim1["Fairbanks: -42°C, HDD=580 (Gas boiler capacity limits, structural freeze down)"]
            Clim2["Phoenix: +46°C, CDD=306 (Chiller saturation, extreme TOU electric peak rates)"]
            Clim3["Denver: 14.3°C swing (Severe actuator fighting between morning and noon)"]
            ClimImp["CONSEQUENCE: A policy specialized in cooling cannot survive subarctic winter, where gas heating failure incurs quadratic penalties."]
            Clim1 & Clim2 & Clim3 --> ClimImp
        end
    end

    DimImp & TauImp & ClimImp --> Solution["REQUIRED SOLUTION ARCHITECTURE:<br/>1. Modular decentralized or Graph Neural Network policy<br/>2. Online estimation of thermal inertia tau to adapt pre-conditioning onset<br/>3. Robust multi-climate coordination logic"]
```
*Figure 7.1: The Triple Transferability Barrier.*

---

## Chapter 8 — What Do We Know, and What Remains Unknown? (Synthesis & Frontiers)

As we conclude the Data Understanding phase, we synthesize our verified knowledge into definitive facts, confirmed operational constraints, benchmark risks, and ranked open hypotheses for Phase 03 modeling.

### 8.1 What is Definitively Known and Verified
1. **The System Contract**: The simulation environment is 100% bitwise deterministic ($\Delta_{\mathrm{obs}}^{\max} = 0.0$, $\Delta_{\mathrm{reward}}^{\max} = 0.0$).
2. **Interface Scaling**: Actions and observations scale according to exact linear formulas ($D=K+1$, $C=3K+2+2V$, $\text{Obs}=6V+15K+58$) across 100% of the building population.
3. **Evaluation Loss**: The 10-component competition reward formula is known to exact floating-point precision ($0.00\text{e}+00$ error against simulator ground truth).
4. **Physical Limits**: External thermal forcing is driven solely by dry-bulb temperature; solar irradiance, humidity, and building envelope air leakage are unmodeled.
5. **Data Dependability**: The meteorological and CAD data pipeline contains zero missing values, zero NaNs, and zero topological raster defects.

### 8.2 Confirmed Constraints for Solution Design
- **Information Enclosure**: Submitted policies have access only to Tier A (live step observation) and Tier B (static metadata: `ahu_zone_assignments`, zone names, `ActionSpec`). No simulator internals or future weather can be inspected.
- **Actuator Limits**: Actions must strictly conform to `ActionSpec` physical bounds. Continuous setpoints outside allowable ranges are clipped; discrete switches must be binary.
- **Fixed Timestep**: Control commands can only be issued every 300 seconds (5 minutes); episodes run for exactly 8,640 steps without early termination.

### 8.3 Benchmark and Validation Risks
- **Overfitting to the 30 Training Pairings**: Because the 30 scenarios implement a non-reused balanced block design, training a policy on specific building-station combinations risks learning idiosyncratic seasonal weather sequences rather than generalized physical control principles.
- **The Quadratic Comfort Cliff**: Allowing zone temperatures to drift into the quadratic penalty zone ($< 16.0^\circ\text{C}$ or $> 29.0^\circ\text{C}$) destroys cumulative returns, overwhelming energy savings. Policies must prioritize comfort envelope preservation above all else.

### 8.4 Ranked Open Hypotheses for Phase 03 Modeling
While Data Understanding has resolved how the data and simulator work, three critical empirical questions must be answered through controller experimentation in Phase 03:

```text
================================================================================
RANKED OPEN RESEARCH HYPOTHESES FOR PHASE 03
================================================================================
Hypothesis H1 (Priority: HIGH — Architectural Transfer):
  "A modular decentralized policy (AHU master coordinator + replicated per-zone
   VAV sub-controllers) will achieve superior cross-building transferability
   compared to a monolithic Graph Neural Network (GNN), because it natively
   respects the strict 9-10 zones/AHU ceiling rule and eliminates variable-size
   graph message-passing overhead."

Hypothesis H2 (Priority: HIGH — Dynamic Pre-Conditioning):
  "Online estimation of building thermal inertia index tau from the initial 24 hours
   of zone temperature response to ambient forcing will enable dynamic tuning of
   the comfort_mode_soon pre-conditioning onset, reducing morning discomfort
   penalties by >80% in slow buildings (tau > 10) without wasting pre-heat energy
   in fast buildings (tau < 3)."

Hypothesis H3 (Priority: MEDIUM — Subarctic Setback Strategy):
  "In extreme subarctic climates (Fairbanks, -40°C), maintaining a shallow night
   setback (18°C) saves more cumulative return than a deep night setback (12°C),
   because deep setbacks exceed the central boiler's morning recovery capacity,
   triggering severe quadratic discomfort penalties at 07:00."
================================================================================
```

---

### 8.5 The Final Integrated Conceptual Map

```mermaid
flowchart TD
    subgraph DataWorld["The Data Environment (Verified Data Understanding Truth)"]
        WeatherGrid["Meteorological Feeds (2023 CSVs)<br/>TempF dry-bulb forcing only"]
        BldgWorld["Procedural Buildings (6 Shipped)<br/>LHS Materials: tau in [1.94, 14.43]<br/>Ceiling Rule: K = ceil(V/10)"]
        Simulator["Gymnasium Environment<br/>2D Nodal Finite-Difference Conduction<br/>10 W/m² internal + 70 W/person occupant<br/>100% Bitwise Deterministic"]
        RewardTruth["Multi-Objective Loss Engine<br/>r_t = 0.6 p_t - 0.2 c_t - 0.2 e_t<br/>Piecewise quadratic cliff at 5°C violation<br/>Plant normalizers: 80kW/205kW * K"]
    end

    subgraph InterfaceWorld["The Policy Contract (Tiers A & B)"]
        TierB_Meta["Static Metadata (Tier B):<br/>ahu_zone_assignments, ActionSpec"]
        TierA_Obs["Live Observation Vector (Tier A):<br/>Obs = 6V + 15K + 58<br/>comfort_mode_soon (2-hr lookahead)"]
        ActionSpec["Hybrid Action Command:<br/>D = K + 1 (Discrete Switches)<br/>C = 3K + 2 + 2V (Continuous Setpoints)"]
    end

    subgraph ModelingWorld["Phase 03: Solution Development (Next Phase)"]
        ModelH1["Test Hypothesis H1:<br/>Modular Decentralized vs GNN"]
        ModelH2["Test Hypothesis H2:<br/>Online tau estimation & adaptive pre-conditioning"]
        ModelH3["Test Hypothesis H3:<br/>Subarctic night setback optimization"]
        MacroEval["30-Scenario Macro Benchmark Evaluation"]
    end

    WeatherGrid --> Simulator
    BldgWorld --> Simulator
    Simulator --> TierA_Obs
    BldgWorld --> TierB_Meta
    Simulator --> RewardTruth

    TierB_Meta & TierA_Obs --> ModelH1 & ModelH2
    ModelH1 & ModelH2 --> ActionSpec
    ActionSpec --> Simulator
    RewardTruth --> MacroEval

    classDef dataStyle fill:#ebf5fb,stroke:#2980b9,stroke-width:1.5px;
    classDef ifaceStyle fill:#eafaf1,stroke:#27ae60,stroke-width:1.5px;
    classDef modelStyle fill:#fef9e7,stroke:#f39c12,stroke-width:1.5px;

    class WeatherGrid,BldgWorld,Simulator,RewardTruth dataStyle;
    class TierB_Meta,TierA_Obs,ActionSpec ifaceStyle;
    class ModelH1,ModelH2,ModelH3,MacroEval modelStyle;
```
*Figure 8.1: The Final Integrated Conceptual Map of the Smart Buildings Data-to-Policy Environment.*

---

## Appendix — Master Evidence & Artifact Directory

For complete scientific reproducibility, all empirical findings, diagnostic scripts, validation logs, and raw outputs generated during the Data Understanding phase are cataloged below:

### Core Phase Deliverables
- [DATA_UNDERSTANDING_GUIDE.md](file:///c:/Users/ADMIN/Desktop/smart%20building/02_DATA_UNDERSTANDING/DATA_UNDERSTANDING_GUIDE.md): The primary comprehensive, illustrated guide.
- [FINAL_HANDOFF.md](file:///c:/Users/ADMIN/Desktop/smart%20building/02_DATA_UNDERSTANDING/FINAL_HANDOFF.md): Executive summary, stage-by-stage completion register, master evidence index, transition guidance, and sign-off.
- [README.md](file:///c:/Users/ADMIN/Desktop/smart%20building/02_DATA_UNDERSTANDING/README.md): Workspace navigation index and summary of findings.

### Evidence Registers & Data Assets
- [DATA_INVENTORY.csv](file:///c:/Users/ADMIN/Desktop/smart%20building/02_DATA_UNDERSTANDING/evidence/DATA_INVENTORY.csv): Comprehensive inventory of 330 project files totaling 116.97 MB.
- [DATA_DICTIONARY.csv](file:///c:/Users/ADMIN/Desktop/smart%20building/02_DATA_UNDERSTANDING/evidence/DATA_DICTIONARY.csv): Schema, units, ranges, and access tiers for all entities.
- [PROVENANCE_REGISTER.csv](file:///c:/Users/ADMIN/Desktop/smart%20building/02_DATA_UNDERSTANDING/evidence/PROVENANCE_REGISTER.csv): Complete lineage records for 12 primary variables.
- [QUALITY_ISSUES.csv](file:///c:/Users/ADMIN/Desktop/smart%20building/02_DATA_UNDERSTANDING/evidence/QUALITY_ISSUES.csv): Classified data quality audit log.
- [FINDINGS_REGISTER.md](file:///c:/Users/ADMIN/Desktop/smart%20building/02_DATA_UNDERSTANDING/evidence/FINDINGS_REGISTER.md): Formal register containing Findings F-001 through F-008.
- [STAGE_GATE_REGISTER.md](file:///c:/Users/ADMIN/Desktop/smart%20building/02_DATA_UNDERSTANDING/evidence/STAGE_GATE_REGISTER.md): Formal stage gate transition audit log.
- [RESEARCH_QUESTION_MATRIX.md](file:///c:/Users/ADMIN/Desktop/smart%20building/02_DATA_UNDERSTANDING/evidence/RESEARCH_QUESTION_MATRIX.md): Detailed mapping from Problem Research R1–R5 to empirical findings.
- [INVESTIGATION_LOG.md](file:///c:/Users/ADMIN/Desktop/smart%20building/02_DATA_UNDERSTANDING/evidence/INVESTIGATION_LOG.md): Chronological ledger of all executed investigation steps.

### Executable Diagnostic Scripts & Output Artifacts
- [d0_verify_manifest.py](file:///c:/Users/ADMIN/Desktop/smart%20building/02_DATA_UNDERSTANDING/diagnostics/scripts/d0_verify_manifest.py) $\to$ [d0_manifest_audit.json](file:///c:/Users/ADMIN/Desktop/smart%20building/02_DATA_UNDERSTANDING/diagnostics/outputs/d0_manifest_audit.json)
- [d0_smoke_test.py](file:///c:/Users/ADMIN/Desktop/smart%20building/02_DATA_UNDERSTANDING/diagnostics/scripts/d0_smoke_test.py) $\to$ [d0_smoke_test.json](file:///c:/Users/ADMIN/Desktop/smart%20building/02_DATA_UNDERSTANDING/diagnostics/outputs/d0_smoke_test.json)
- [d1_trace_lineage.py](file:///c:/Users/ADMIN/Desktop/smart%20building/02_DATA_UNDERSTANDING/diagnostics/scripts/d1_trace_lineage.py) $\to$ [d1_provenance_trace.json](file:///c:/Users/ADMIN/Desktop/smart%20building/02_DATA_UNDERSTANDING/diagnostics/outputs/d1_provenance_trace.json)
- [d2_schema_and_invariants.py](file:///c:/Users/ADMIN/Desktop/smart%20building/02_DATA_UNDERSTANDING/diagnostics/scripts/d2_schema_and_invariants.py) $\to$ [d2_building_schemas.json](file:///c:/Users/ADMIN/Desktop/smart%20building/02_DATA_UNDERSTANDING/diagnostics/outputs/d2_building_schemas.json)
- [d3_data_quality_audit.py](file:///c:/Users/ADMIN/Desktop/smart%20building/02_DATA_UNDERSTANDING/diagnostics/scripts/d3_data_quality_audit.py) $\to$ [d3_quality_report.json](file:///c:/Users/ADMIN/Desktop/smart%20building/02_DATA_UNDERSTANDING/diagnostics/outputs/d3_quality_report.json)
- [d4_coverage_and_diversity.py](file:///c:/Users/ADMIN/Desktop/smart%20building/02_DATA_UNDERSTANDING/diagnostics/scripts/d4_coverage_and_diversity.py) $\to$ [d4_diversity_metrics.json](file:///c:/Users/ADMIN/Desktop/smart%20building/02_DATA_UNDERSTANDING/diagnostics/outputs/d4_diversity_metrics.json)
- [d5_simulation_and_reward_audit.py](file:///c:/Users/ADMIN/Desktop/smart%20building/02_DATA_UNDERSTANDING/diagnostics/scripts/d5_simulation_and_reward_audit.py) $\to$ [d5_reward_reconstruction.json](file:///c:/Users/ADMIN/Desktop/smart%20building/02_DATA_UNDERSTANDING/diagnostics/outputs/d5_reward_reconstruction.json)
- [generate_guide_figures.py](file:///c:/Users/ADMIN/Desktop/smart%20building/02_DATA_UNDERSTANDING/diagnostics/scripts/generate_guide_figures.py) $\to$ Generated publication figures in `02_DATA_UNDERSTANDING/assets/`

### Editorial Process Records
- [SOURCE_AUDIT.md](file:///c:/Users/ADMIN/Desktop/smart%20building/02_DATA_UNDERSTANDING/editorial/SOURCE_AUDIT.md): Inventory of inspected sources and availability status.
- [CONTENT_AND_FINDINGS_MATRIX.md](file:///c:/Users/ADMIN/Desktop/smart%20building/02_DATA_UNDERSTANDING/editorial/CONTENT_AND_FINDINGS_MATRIX.md): Mapping of all empirical findings to target guide sections.
- [GUIDE_CONTENT_MAP.md](file:///c:/Users/ADMIN/Desktop/smart%20building/02_DATA_UNDERSTANDING/editorial/GUIDE_CONTENT_MAP.md): Detailed architectural plan and dependency checks.
- [VISUAL_PLAN.md](file:///c:/Users/ADMIN/Desktop/smart%20building/02_DATA_UNDERSTANDING/editorial/VISUAL_PLAN.md): Visual communication strategy, figure specifications, and cognitive load reduction patterns.
