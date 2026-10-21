# Visual Plan & Communication Strategy — Smart Buildings Data Understanding

## Executive Summary & Stage P3 Objective

This document defines the comprehensive visual communication strategy for `DATA_UNDERSTANDING_GUIDE.md`. Its goal is to make the complex mechanisms, physical models, data structures, and evaluation metrics of the Smart Buildings Challenge immediately clear through purposeful diagrams, data-backed charts, and structured visual explanations.

Every planned visual answers a specific reader question, reduces cognitive load, adheres to strict scientific accuracy standards, and is directly grounded in verified empirical evidence.

---

## 1. Master Visual Element Inventory

| Visual ID | Type | Target Chapter | Descriptive Title | Central Reader Question Answered | Underlying Evidence / Data Source |
|---|---|---|---|---|---|
| **Fig 0.1** | Mermaid Flowchart | Opening | End-to-End System Architecture: From Offline Configs to Evaluation Score | How do external inputs, procedural buildings, the simulation engine, the control policy, and the evaluation score fit together? | `00_DATA_ENVIRONMENT.md`, `FINAL_HANDOFF.md` |
| **Fig 1.1** | Mermaid Flowchart | Chapter 1 | The Four Data Origin Streams and Transformation Pathways | Which data elements are recorded, procedurally generated, simulated, or derived? | `PROVENANCE_REGISTER.csv`, `01_DATA_PROVENANCE.md` |
| **Fig 1.2** | Mermaid Flowchart | Chapter 1 | External Meteorological Forcing: Active vs. Omitted Mechanisms | What environmental factors actually drive the simulator, and what real-world mechanisms are omitted? | `weather_controller.py`, `d1_provenance_trace.json` |
| **Fig 2.1** | Mermaid ER Diagram | Chapter 2 | Entity-Relationship Topology of the Competition Data Model | How do Scenarios, Buildings, Weather Presets, Tariff Schedules, and Zones interconnect? | `02_DATA_STRUCTURE_AND_SEMANTICS.md`, `training_set.yaml` |
| **Fig 2.2** | Mermaid Container | Chapter 2 | The Four-Tier Policy Information Access Boundary | What information can the submitted control policy legally see, and what remains strictly hidden? | `environment.py`, `02_DATA_STRUCTURE_AND_SEMANTICS.md` |
| **Fig 2.3** | Mermaid / Table Layout | Chapter 2 | Observation Vector Anatomy ($6V + 15K + 58$) | How is the 1D observation vector assembled, and why does its dimension change across buildings? | `d2_building_schemas.json`, `d2_schema_and_invariants.py` |
| **Fig 4.1** | Matplotlib PNG Asset | Chapter 4 | Building Thermal Inertia Spectrum and Envelope Characteristics | How diverse are the 6 training buildings in thermal responsiveness, facade insulation, and heat capacity? | `d4_diversity_metrics.json`, `assets/figure_4_1_thermal_diversity.png` |
| **Fig 4.2** | Mermaid Flowchart | Chapter 4 | HVAC Zoning Hierarchy and Procedural Ceiling Grouping ($K = \lceil V/10 \rceil$) | How are thermal zones physically partitioned and assigned to central Air Handling Units? | `building_train_*.yaml`, `d4_diversity_metrics.json` |
| **Fig 5.1** | Matplotlib PNG Asset | Chapter 5 | Meteorological Temperature Spans and Thermodynamic Demands Across 5 Climates | What temperature ranges, diurnal swings, and heating/cooling degree days characterize each climate regime? | `d4_diversity_metrics.json`, `assets/figure_5_1_climate_regimes.png` |
| **Fig 5.2** | Markdown Grid Matrix | Chapter 5 | The Balanced-Block Scenario Pairing Grid ($6 \times 5 = 30$) with Calendar Windows | Which building is paired with which 30-day weather strip, and why are comparisons confounded? | `training_set.yaml`, `d0_manifest_audit.json` |
| **Fig 6.1** | Mermaid Sequence | Chapter 6 | Simulator 5-Minute Stepping Sequence and Numerical Integration Loop | What exact sequence of operations occurs during each 5-minute timestep in the environment? | `hybrid_action_environment.py`, `05_SIMULATOR_BEHAVIOUR_AND_EVALUATION.md` |
| **Fig 6.2** | Mermaid Flowchart | Chapter 6 | The 10-Component Competition Reward Function Decomposition | How are comfort shortfall, electricity cost, gas expenditure, and grid carbon combined into the scalar reward? | `d5_reward_reconstruction.json`, `setpoint_energy_carbon_regret.py` |
| **Fig 6.3** | Matplotlib PNG Asset | Chapter 6 | Piecewise Quadratic Comfort Shortfall Penalty Function $f(d)$ | How does occupant discomfort scale with temperature violation distance, and where is the quadratic cliff? | `d5_reward_reconstruction.json`, `assets/figure_6_1_comfort_penalty.png` |
| **Fig 6.4** | Mermaid Flowchart | Chapter 6 | Dynamic Pre-Conditioning Timeline via the 2-Hour `comfort_mode_soon` Lookahead | How can a policy leverage lookahead flags to overcome building thermal lag before occupancy? | `environment.py`, `05_SIMULATOR_BEHAVIOUR_AND_EVALUATION.md` |
| **Fig 7.1** | Mermaid Flowchart | Chapter 7 | The Triple Transferability Barrier (Dimensional, Thermal, and Climatic) | What structural, physical, and meteorological hurdles prevent simple controllers from transferring? | `06_DATA_UNDERSTANDING_SYNTHESIS.md`, Problem Research R5 |
| **Fig 8.1** | Mermaid Flowchart | Chapter 8 | Integrated Conceptual Architecture: The Data-to-Policy Optimization System | What is the final, unified understanding of the Smart Buildings Challenge data environment? | `06_DATA_UNDERSTANDING_SYNTHESIS.md`, `FINAL_HANDOFF.md` |

---

## 2. Explanation Design & Cognitive Load Reduction Patterns

To ensure maximum clarity and readability across `DATA_UNDERSTANDING_GUIDE.md`, each section follows five strict pedagogical rules:

1. **The Lead-In Question**:
   Every subsection begins with the natural question a data scientist would ask (e.g., *"Why does opening a zone VAV damper increase electrical power consumption?"*), establishing immediate context before presenting technical mechanisms.
2. **Plain-Language Intuition Before Formal Mathematics**:
   Every equation (such as $\mathrm{Obs} = 6V + 15K + 58$ or $r_t = 0.6 p_t - 0.2 c_t - 0.2 e_t$) is preceded by an explanation of its physical meaning, followed by a variable-by-variable definition, and concluded with a concrete worked example using real numbers from `building_train_1`.
3. **Paired Visuals and Interpretations**:
   No diagram or figure is left to "speak for itself." Every visual is accompanied by an explicit, numbered caption and a short paragraph highlighting the specific relationship or insight the reader should extract.
4. **Concrete Worked Examples at Conceptual Bridges**:
   At key transition points—such as moving from static building geometry to dynamic 5-minute stepping—the text steps through a specific zone (`zone_0` in `building_train_1`), showing the actual temperature ($295.15\text{ K}$), the setpoint band ($[294.15, 297.15]\text{ K}$), the damper fraction ($0.45$), and the resulting reward contribution ($0.0$).
5. **Clear Separation of Facts, Constraints, and Unknowns**:
   The text rigorously maintains the epistemic distinction between verified simulation facts, fixed operational constraints, and unresolved research hypotheses.

---

## 3. P3 Completion Gate Review

```text
STAGE: P3 (EXPLANATION & VISUAL DESIGN)
STATUS: PASS

Completion Checklist:
- [x] Complete inventory of 16 planned visuals (Mermaid diagrams, quantitative PNGs, and tables)
- [x] All 3 quantitative PNG figures generated and verified in 02_DATA_UNDERSTANDING/assets/
- [x] Every visual mapped to a specific reader question and underlying evidence file
- [x] Cognitive load reduction patterns established (lead-in questions, worked examples, paired interpretations)
- [x] Zero fabricated data; all quantitative assets use verified JSON audit outputs

Conclusion: Visual communication strategy and assets are complete and verified.
Next Action: Proceed to Stage P4 (Construct the Main Guide & Directory Restructuring).
```
