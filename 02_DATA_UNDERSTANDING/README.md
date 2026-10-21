# Smart Buildings Challenge — Data Understanding (Phase 02)

Welcome to the **Data Understanding Phase** of the NeurIPS 2026 Smart Buildings Challenge repository.

This directory contains the complete knowledge base, empirical evidence, and diagnostic suite establishing the physical reality, simulation mechanics, interface contracts, and evaluation objectives of the competition.

---

## 🚀 Where to Start: The Primary Knowledge Guide

> 👉 **Start here**: **[DATA_UNDERSTANDING_GUIDE.md](file:///c:/Users/ADMIN/Desktop/smart%20building/02_DATA_UNDERSTANDING/DATA_UNDERSTANDING_GUIDE.md)**

The **Data Understanding Guide** is a comprehensive, standalone, illustrated document that explains the entire data environment from beginning to end. It eliminates the need to navigate fragmented technical reports by synthesizing our empirical research into a progressive learning journey:

- **Opening**: Overview of the challenge, simulation mechanics, and end-to-end architecture.
- **Chapter 1 (Data Origins)**: Tracing recorded weather, procedural CAD floor plans, Latin Hypercube materials, internal loads ($10\text{ W/m}^2$), and dynamic occupant sensible heat ($70\text{ W/person}$).
- **Chapter 2 (Data Structure & Access)**: Entity relationships, the Four-Tier Information Access Boundary, and proofs of closed-form interface invariants:
  $$\mathbf{D = K + 1}, \quad \mathbf{C = 3K + 2 + 2V}, \quad \mathbf{Obs = 6V + 15K + 58}$$
- **Chapter 3 (Data Quality)**: Verification of 52,560 hourly weather records (0 missing, 0 NaNs), 48 presets, and 6 CAD rasters with zero spatial defects.
- **Chapter 4 (Building Heterogeneity)**: Physical envelope parameters ($U$, $C_{\mathrm{env}}$), the **$7.4\times$ spread in thermal inertia ($\tau \in [1.94, 14.43]$)**, and AHU ceiling rules ($K = \lceil V/10 \rceil$).
- **Chapter 5 (Environmental Diversity)**: The 5 climate regimes (Fairbanks $-42.0^\circ\text{C}$ to Phoenix $+46.1^\circ\text{C}$), diurnal swings, and the non-Cartesian balanced block pairing grid ($6 \times 5 = 30$).
- **Chapter 6 (Simulator Operation & Evaluation)**: 5-minute numerical stepping loop, bitwise determinism ($0.0$ diff), lookahead pre-conditioning via `comfort_mode_soon`, and exact reconstruction of the 10-component reward ($r_t = 0.6 p_t - 0.2 c_t - 0.2 e_t$) with **$0.00\text{e}+00$ discrepancy**.
- **Chapter 7 (Problem Synthesis)**: Comprehensive mapping against Problem Research fronts R1–R5, and the Triple Transferability Barrier.
- **Chapter 8 (Synthesis & Open Frontiers)**: Verified facts, confirmed constraints, benchmark risks, and ranked open hypotheses (H1, H2, H3) heading into Phase 03.

---

## 📁 Reorganized Directory Structure

```text
02_DATA_UNDERSTANDING/
│
├── README.md                                  # You are here: Workspace entry point & directory index
├── DATA_UNDERSTANDING_GUIDE.md                # PRIMARY DELIVERABLE: Complete reader-facing illustrated guide
│
├── assets/                                    # Publication-grade quantitative charts & visuals
│   ├── figure_4_1_thermal_diversity.png       # 7.4x Thermal inertia spread and U vs C_env scatter
│   ├── figure_5_1_climate_regimes.png         # Temperature spans, diurnal swings, and degree days
│   └── figure_6_1_comfort_penalty.png         # Piecewise quadratic comfort shortfall penalty curve
│
├── evidence/                                  # Empirical evidence registers & audit ledgers
│   ├── DATA_INVENTORY.csv                     # Exhaustive inventory of 330 project files (116.97 MB)
│   ├── DATA_DICTIONARY.csv                    # Complete schema, units, ranges, and access tiers
│   ├── PROVENANCE_REGISTER.csv                # Origin, source files, and transformation pathways
│   ├── QUALITY_ISSUES.csv                     # Classified data quality issues & integrity findings
│   ├── FINDINGS_REGISTER.md                   # Formal register of Findings F-001 through F-008
│   ├── STAGE_GATE_REGISTER.md                 # Formal gate decision audits for D0–D6 (100% PASS)
│   ├── RESEARCH_QUESTION_MATRIX.md            # Mapping Problem Research R1–R5 to empirical findings
│   └── INVESTIGATION_LOG.md                   # Chronological ledger of all 14 executed steps
│
├── diagnostics/                               # Technical reproducibility suite
│   ├── scripts/                               # Rerunnable Python analysis, audit, and plotting scripts
│   ├── outputs/                               # Raw JSON audit dumps confirming all factual claims
│   ├── tests/                                 # Executable validation checks
│   └── figures/                               # Diagnostic plots
│
├── editorial/                                 # Restructuring process records & validation reports
│   ├── SOURCE_AUDIT.md                        # P0: Inventory and integrity audit of source materials
│   ├── CONTENT_AND_FINDINGS_MATRIX.md         # P1: Mapping of empirical findings to target guide
│   ├── GUIDE_CONTENT_MAP.md                   # P2: Architectural blueprint & dependency verification
│   ├── VISUAL_PLAN.md                         # P3: Visual communication strategy & figure specs
│   └── VALIDATION_REPORT.md                   # P5: Completeness, evidence, and comprehension audits
│
└── FINAL_HANDOFF.md                           # Formal Phase 02 sign-off declaration and transition guidance
```

---

## 🔍 Key Empirical Discoveries at a Glance

1. **Simulation Dynamics & Physical Limits**:
   The simulator is a 2D nodal finite-difference thermal conduction solver with **100% bitwise determinism**. Thermal forcing is driven **exclusively by dry-bulb temperature (`TempF`)**, internal equipment loads ($10.0\text{ W/m}^2$), and dynamic occupant sensible heat ($70.0\text{ W/person}$). **Solar radiation, air infiltration, humidity, and wind speed are completely unmodeled**.
2. **Interface Scaling & Invariants**:
   The observation vector, discrete action channels, and continuous setpoints follow exact mathematical invariants across all buildings:
   $$\boxed{D = K + 1}, \quad \boxed{C = 3K + 2 + 2V}, \quad \boxed{\mathrm{Obs} = 6V + 15K + 58}$$
   Observations range from 283 to 703 dimensions, necessitating modular decentralized or graph-structured policy architectures.
3. **The 10-Component Optimization Loss**:
   The competition scalar reward $r_t = 0.6 p_t - 0.2 c_t - 0.2 e_t$ was independently reconstructed from physical variables and verified against the simulator with **$0.00\text{e}+00$ discrepancy**. Comfort shortfall $p_t$ escalates **quadratically** once temperature deviation exceeds $5.0^\circ\text{C}$, punishing severe thermal drift far more heavily than minor oscillations.
4. **Thermal Inertia & Balanced Block Confounding**:
   The building population exhibits a **$7.4\times$ variation in thermal inertia $\tau$** ($1.94$ in leaky `building_train_7` to $14.43$ in massive `building_train_1`). The 30 official training scenarios follow a balanced block non-reused design ($6 \text{ buildings} \times 5 \text{ weather stations}$), confounding seasonal weather windows with building architecture.

---

## 📌 Status & Next Permitted Actions
- **Data Understanding Status**: **COMPLETE (ALL 7 GATES PASSED)**.
- **Editorial Restructuring**: **COMPLETE (STAGES P0–P5 EXECUTED)**.
- **Next Phase**: Authorized to proceed to **Phase 03 (Problem Formulation & Architecture Design)**.
