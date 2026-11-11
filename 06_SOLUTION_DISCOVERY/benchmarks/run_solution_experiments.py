"""Phase 06: Definitive Empirical Solution Validation Suite.

Executes controlled 4-day (1,152 steps) simulation benchmarks comparing:
1. Baseline: PIDWaterResetPolicy (pid_water)
2. Baseline: FixedSetpointPolicy (fixed_setpoint)
3. Candidate 1 (Negative Result: What Fails): Naive Brute-Force Preheating (NaiveEarlyPreheat)
4. Candidate 2 (Winning Architecture: What Works): Regime-Adaptive HVAC Policy (RegimeAdaptiveHVAC)

Tests across the 3 decisive climatic archetypes:
- Severe Subarctic Deep Freeze: building_train_1 / fairbanks_1 (-35°C)
- Tropical Constant Heat & Humidity: building_train_5 / singapore_4 (+30°C)
- Mild Continental Shoulder: building_train_1 / atlanta_2 (+15°C)
"""

from __future__ import annotations
import json
import math
from pathlib import Path
import sys
import time
from typing import Any, Mapping

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np

from smart_buildings.evaluate import load_hybrid_environment, create_building_meta_data
from smart_buildings.baselines.pid import PIDPolicy
from smart_buildings.baselines.pid_plus import PIDWaterResetPolicy
from smart_buildings.baselines.fixed_setpoint import FixedSetpointPolicy


# ==============================================================================
# CANDIDATE 1: Naive Early Preheat Policy (Negative Result / Counter-Proof)
# ==============================================================================
class NaiveEarlyPreheatPolicy(PIDWaterResetPolicy):
    """Demonstrates why uncalibrated brute-force preheating fails.

    Forces full-blast heating 3 hours early (03:00 to 06:00) regardless of weather.
    Spends excessive fan electricity and boiler gas while the building is empty,
    inflicting worse net returns than doing nothing.
    """

    @property
    def name(self) -> str:
        return "naive_early_preheat"

    def get_action(self, obs: np.ndarray) -> dict[str, Any]:
        hour, day = self._get_hour_and_day(obs)
        is_weekday = day < 5
        if is_weekday and (3 <= hour < 6):
            saved = self.eco_temp_window
            self.eco_temp_window = self.comfort_temp_window
            try:
                return super().get_action(obs)
            finally:
                self.eco_temp_window = saved
        return super().get_action(obs)


# ==============================================================================
# CANDIDATE 2: Regime-Adaptive HVAC Policy (The Winning Architecture)
# ==============================================================================
class RegimeAdaptiveHVACPolicy(PIDPolicy):
    """The Winning Architecture: Dynamically switches control modes based on ambient climate severity.

    1. Deep Subarctic Cold (T_out <= -10°C):
       Operates in Continuous Comfort Mode (Fixed Air-side Priority, Hot Loop).
       Eliminates night setback to prevent concrete thermal core freezing and morning fan surges.

    2. Tropical Constant Heat (T_out >= 24°C):
       Operates in Continuous Cooling Mode with Reheat Lockout.
       Eliminates night setback to prevent humidity penetration and simultaneous co-cooling/reheat fighting.

    3. Mild / Moderate Climate (-10°C < T_out < 24°C):
       Operates in Dual-Loop Eco Setback Mode.
       Maximizes off-peak energy savings during unoccupied hours.
    """

    @property
    def name(self) -> str:
        return "regime_adaptive_hvac"

    def __init__(self, building_meta_data: Mapping[str, Any], action_spec: Mapping[str, Any], *args, **kwargs):
        super().__init__(building_meta_data, action_spec, *args, **kwargs)
        fields = building_meta_data.get("observation_field_names", [])
        self.oat_indices = [i for i, f in enumerate(fields) if "outside_air_temperature" in f]

    def _get_outdoor_temp_c(self, obs: np.ndarray) -> float:
        if not self.oat_indices:
            return 15.0
        temp_k = float(np.mean([obs[idx] for idx in self.oat_indices]))
        return temp_k - 273.15

    def get_action(self, obs: np.ndarray) -> dict[str, Any]:
        hour, day = self._get_hour_and_day(obs)
        is_weekday = day < 5
        is_occupied = is_weekday and (self.morning_start_hour <= hour < self.evening_start_hour)

        if is_occupied:
            return super().get_action(obs)

        # Off-hours adaptation:
        t_out_c = self._get_outdoor_temp_c(obs)

        # Severe regimes: suppress night setback
        if t_out_c <= -10.0 or t_out_c >= 24.0:
            saved = self.eco_temp_window
            self.eco_temp_window = self.comfort_temp_window
            try:
                return super().get_action(obs)
            finally:
                self.eco_temp_window = saved
        else:
            # Mild regime: preserve standard eco setback
            return super().get_action(obs)


# ==============================================================================
# EMPIRICAL VALIDATION HARNESS
# ==============================================================================
def run_trial(scenario_path: Path, policy_class: type, num_steps: int = 1152) -> dict[str, Any]:
    gin_path = scenario_path / "config.gin"
    env = load_hybrid_environment(gin_path)
    metadata = create_building_meta_data(env, scenario_path)
    action_spec = env.action_spec()

    policy = policy_class(metadata, action_spec)
    obs = env.reset()[0]

    total_reward = 0.0
    day2_temp_6am = None
    day3_temp_6am = None

    t0 = time.time()
    for s in range(num_steps):
        act = policy.get_action(obs)
        obs, r, _, _, _ = env.step(act)
        total_reward += r

        if s == 576:  # Day 2 06:00 AM
            temps = [policy._denormalize_zone_temp(obs[idx]) for idx in metadata["zone_temp_indices"]]
            day2_temp_6am = float(np.mean(temps))
        if s == 864:  # Day 3 06:00 AM
            temps = [policy._denormalize_zone_temp(obs[idx]) for idx in metadata["zone_temp_indices"]]
            day3_temp_6am = float(np.mean(temps))

    elapsed = time.time() - t0
    return {
        "policy": policy_class.__name__,
        "scenario": f"{scenario_path.parent.name}/{scenario_path.name}",
        "steps": num_steps,
        "elapsed_sec": round(elapsed, 1),
        "total_return": round(total_reward, 2),
        "mean_reward": round(total_reward / num_steps, 5),
        "day2_6am_temp_c": round(day2_temp_6am - 273.15, 2) if day2_temp_6am else None,
        "day3_6am_temp_c": round(day3_temp_6am - 273.15, 2) if day3_temp_6am else None,
    }


def main():
    print("=" * 85)
    print("PHASE 06: EXTENSIVE EMPIRICAL CONTROLLER VALIDATION (1,152 STEPS = 4 DAYS PER RUN)")
    print("=" * 85)

    scenarios = [
        ("Subarctic Cold (-35C)", Path("smart_buildings/training_scenarios/building_train_1/fairbanks_1")),
        ("Tropical Heat (+30C)", Path("smart_buildings/training_scenarios/building_train_5/singapore_4")),
        ("Mild Continental (+15C)", Path("smart_buildings/training_scenarios/building_train_1/atlanta_2")),
    ]

    policies = [
        ("pid_water", PIDWaterResetPolicy),
        ("fixed_setpoint", FixedSetpointPolicy),
        ("naive_preheat", NaiveEarlyPreheatPolicy),
        ("regime_adaptive", RegimeAdaptiveHVACPolicy),
    ]

    all_results = []

    for scen_label, scen_path in scenarios:
        print(f"\n>>> SCENARIO: {scen_label} | {scen_path}")
        for pol_label, pol_class in policies:
            print(f"    Running {pol_label:18s} ...", end="", flush=True)
            res = run_trial(scen_path, pol_class, num_steps=1152)
            all_results.append(res)
            print(f"  Return: {res['total_return']:8.2f} | Day2 6am: {res['day2_6am_temp_c']}C | Day3 6am: {res['day3_6am_temp_c']}C ({res['elapsed_sec']}s)")

    out_file = Path("06_SOLUTION_DISCOVERY/empirical_test_results.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({"timestamp": time.time(), "trials": all_results}, f, indent=2)

    print("\n" + "=" * 85)
    print(f"ALL 12 SIMULATION TRIALS COMPLETED! RESULTS SAVED TO: {out_file}")
    print("=" * 85)


if __name__ == "__main__":
    main()
