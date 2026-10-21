# SMART BUILDINGS CHALLENGE

Problem Establishment  |  Version 0.1  |  21 October 2026

Purpose: establish what the competition asks, why it is difficult, and what remains to be investigated. No modeling strategy is proposed.

## 1  Context and central problem

HVAC operation must maintain acceptable indoor conditions while consuming energy, incurring electricity and gas costs, and contributing carbon emissions. Building-control policies can perform well in familiar environments but deteriorate when transferred to unseen buildings or operating conditions.

The competition focuses on transferability: building size, layout, weather, material properties, and HVAC systems may differ between development and evaluation.

```text
PHYSICAL AND OPERATING VARIATION
Building size  •  Layout  •  Weather  •  Materials  •  HVAC systems
                             ↓
             A policy developed on simulated buildings
                             ↓
             Previously unseen building–weather combinations
                             ↓
             Comfort  +  Energy cost  +  Carbon emissions
```

## 2  Exact competition task

Develop a control policy using simulated buildings. The policy is evaluated across held-out building–weather scenarios and is intended to adapt to a new building with minimal configuration. It makes sequential control decisions; the precise observation and action interfaces still require verification.

## 3  How performance is evaluated

| Evaluation element | Specified rule |
|---|---|
| Step length | 5 minutes; the first step counts |
| Scenario duration | 8,640 steps = 30 days |
| Per-step reward | Non-positive: occupant comfort penalty, energy cost, and carbon emissions |
| Comfort penalty | Zero inside comfort band; linear up to 5 K outside; quadratic and unbounded beyond 5 K |
| Comfort aggregation | Weighted by zone occupancy, not floor area; weights fixed across submissions |
| Episode return | Sum of all step rewards |
| Scenario value | Episode return ÷ 8,640 |
| Leaderboard metric | Mean absolute error of scenario mean rewards against zero; lower is better |
| Final test set | 6 unseen buildings × 5 unseen weather stations = 30 equally weighted scenarios |
| Simulator | Deterministic for identical policy and scenario; each pair run once |

Because each step reward is ≤ 0, the target of zero is ideal. The leaderboard score is the average magnitude of the mean per-step penalty. The reward and score equations were lost in the supplied paste; verify exact coefficients and expression from the official specification before treating this as a finalized competition contract.

```text
ONE SCENARIO: 8,640 consecutive five-minute decisions (30 days)
Step rewards → episode return R = Σ rₜ → scenario mean R / 8,640
                             ↓
             30 scenarios (6 buildings × 5 weather stations)
                             ↓
Equal-weight mean absolute distance of scenario means from 0 → LOWER IS BETTER
```

## 4  Why this problem is difficult

| Difficulty | Meaning |
|---|---|
| Cross-building heterogeneity | Physical systems and operating conditions differ. |
| Transferability | Success on development environments need not carry over to unseen combinations. |
| Competing objectives | Comfort, monetary cost and carbon impact contribute to the reward. |
| Severe discomfort | Beyond 5 K outside the comfort band, quadratic penalty can dominate an episode. |
| Sequential operation | Every decision contributes to a 30-day operating trajectory. |

## 5  Problem statement

Building HVAC control requires balancing occupant thermal comfort, energy expenditure, and associated carbon emissions over time. Policies developed for particular buildings can lose performance when deployed in buildings with different physical properties, layouts, HVAC configurations, and weather conditions. The Smart Buildings Challenge asks for a policy that transfers across previously unseen building–weather combinations with minimal configuration, minimizing the combined competition-defined penalties over each 30-day evaluation episode.

## 6  Established facts and unresolved questions

| Established from provided overview | Requires verification / investigation |
|---|---|
| Objective, general transfer setting and heterogeneity | Exact reward equation and coefficients |
| 5-minute steps and 30-day episode | Available observations and permitted actions |
| 30 equally weighted unseen scenarios | Simulator mechanics and operating constraints |
| Deterministic same-policy/same-scenario result | Development building and weather coverage |
| Comfort penalty shape and occupancy weighting | Submission interface, dependencies, execution limits, full rules |

## 7  Research sequence — no solution design yet

```text
0. PROBLEM ESTABLISHMENT  (this document)
                 ↓
1. DOMAIN RESEARCH: thermodynamics, comfort, HVAC, weather and transferability
                 ↓
2. ENVIRONMENT RESEARCH: simulator, interfaces, dynamics, constraints, official rules
                 ↓
3. DATA UNDERSTANDING: sources, distributions, quality, relationships, coverage and limits
                 ↓
4. PROBLEM SYNTHESIS: supported facts, uncertainty, key difficulties
                 ↓
5. STRATEGY FORMULATION: only after prior stages are complete
```

## 8  Competition milestones

13 Oct 2026 — Start  |  13 Nov 2026 — Round-one paper  |  13 Dec 2026 — NeurIPS workshop  |  3 Jan 2027 — Entry and merger deadlines  |  15 Jan 2027 — Final submission. Listed deadlines are 11:59 PM UTC unless otherwise noted, subject to organizer updates. Paper prizes evaluate quality, novelty and writing clarity separately from leaderboard ranking.

Stage gate: before proceeding, recover the original mathematical formulas and confirm the official competition specification. Do not infer missing details or select a modeling approach during problem establishment.




### Problem Research — Understanding the Challenge (R1–R5)

https://github.com/muma005/smart-buildings-data-project-/blob/main/Smart_Buildings_Problem_Research_R1-R5.md

The Smart Buildings Challenge requires a single HVAC control policy to operate effectively across previously unseen buildings and weather conditions while balancing occupant comfort, energy expenditure and carbon emissions. The central difficulty is that buildings differ physically and mechanically: the same operating decision can produce entirely different outcomes depending on the building and its environment.

This research investigates the underlying mechanisms responsible for that difficulty through five connected areas:

- **R1 — Building Behaviour:** Establishes how buildings respond to heating, cooling and environmental conditions, examining heat transfer, construction materials, internal heat gains, thermal storage and the delayed effects of HVAC operation.
- **R2 — Operating Objectives:** Examines how the competition measures success, including occupancy-weighted comfort, severe temperature-violation penalties, electricity and gas expenditure, carbon emissions, and the interactions between these objectives.
- **R3 — Heterogeneity:** Investigates how differences in building size, layout, weather, materials and HVAC configurations change thermal behaviour, equipment requirements and operating outcomes.
- **R4 — Control Problem:** Establishes what information a policy actually receives, what equipment it can control, the physical constraints governing those decisions, and how each action influences subsequent building conditions.
- **R5 — Transferability:** Brings these findings together to explain why operating behaviour that succeeds in one building may fail elsewhere, supported by scientific evidence on cross-building generalization and documented transfer-failure mechanisms.

**Its role in the project**

The competition's underlying problem is achieving reliable control across changing physical systems, not merely obtaining a good score on the supplied development scenarios.

This research establishes the causal understanding needed to investigate that problem intelligently. It identifies which building characteristics, physical responses, operating constraints and failure mechanisms matter, and translates them into specific questions for examining the competition simulator and data.

It therefore provides the foundation for determining **what we need to measure, what differences we need to explain, and what evidence is required to establish genuine cross-building generalization**—before selecting a modeling approach or designing experiments.

The accompanying document contains the detailed investigations, scientific evidence, equations, explanatory diagrams, competition-specific findings and unresolved questions.
