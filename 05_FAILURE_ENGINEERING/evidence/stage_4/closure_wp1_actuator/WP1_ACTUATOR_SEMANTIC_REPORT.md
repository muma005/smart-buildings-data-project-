# Work Package 1 (WP1) - Multi-Building Actuator Semantic Verification Report

## Executive Summary

- **Objective**: Validate physical causality between actuator control channels and thermal zone observations using single-variable pulse interventions across differing building topologies (`building_train_1` vs `building_train_2`).
- **Buildings Tested**: `building_train_1` (3 zones, compact) and `building_train_2` (85 zones, 9 AHUs, complex hydronic loop).
- **Verdict**: ALL 4 SCENARIOS VERIFIED.

## Test Results

| Scenario | Target Zone | Expected Outcome | Observed Delta T | Observed Margin | Verdict |
|---|---|---|---|---|---|
| **building_train_1 Clean Pulse Control** | VAV_1 | Healthy Thermal Dominance | 0.549 K | 0.078 K | **PASS** |
| **building_train_1 Swapped Channel Detection** | VAV_1 | Detection of Swapped Channel | 0.050 K | -0.850 K | **PASS** |
| **building_train_2 Clean Pulse Control** | VAV_1 | Healthy Thermal Dominance | 1.175 K | 0.187 K | **PASS** |
| **building_train_2 Swapped Channel Detection** | VAV_1 | Detection of Swapped Channel | 0.030 K | -1.170 K | **PASS** |

## Key Verification Takeaways

1. **Topology Awareness**: Semantic pulse interventions must account for building-specific hydronic loops (`water_indices`) and zone supply air dampers (`supply_air_damper_percentage_command`). In complex buildings like `building_train_2`, reheat coils cannot warm zones unless the central hot water loop is active and zone dampers allow airflow.
2. **Dominant Thermal Signature**: On clean controls for both buildings, single-variable pulse intervention drives a dominant local temperature rise exceeding 0.2 K with a positive margin over all other zones.
3. **Culprit Zone Identification**: When actuator channels are crossed or swapped, the probe cleanly identifies the exact culprit zone that absorbed the thermal energy and rejects the mapping.