"""Engineering Diagnostics Engine for Smart Buildings Challenge.
Computes deep physical diagnostic metrics (thermal comfort degree-hours,
energy subsystem breakdowns, carbon intensity, actuator duty cycle) from traces.
"""

from __future__ import annotations
from pathlib import Path
from typing import Any
import pandas as pd
import numpy as np


class DiagnosticsEngine:
    """Analyzes episode traces to generate multi-dimensional engineering diagnostics."""

    @classmethod
    def analyze_trace(cls, trace_path: Path | str) -> dict[str, Any]:
        """Loads trace CSV and computes physical diagnostics."""
        path = Path(trace_path)
        if not path.is_file():
            raise FileNotFoundError(f"Missing trace for diagnostics: {path}")

        df = pd.read_csv(path)
        steps = len(df)
        if steps == 0:
            return {"error": "Trace is empty"}

        # Thermal comfort analysis (assuming 20°C - 24°C nominal comfort band during occupied periods)
        mean_temps = df["mean_zone_temp"].values
        occupants = df["total_occupants"].values
        occupied_mask = occupants > 0.0
        occupied_steps = int(np.sum(occupied_mask))

        # Degree-hours (each step is 5 minutes = 5/60 hours)
        step_hours = 5.0 / 60.0
        cold_deviations = np.maximum(0.0, 20.0 - mean_temps)
        hot_deviations = np.maximum(0.0, mean_temps - 24.0)

        cold_degree_hours = float(np.sum(cold_deviations[occupied_mask] * step_hours)) if occupied_steps > 0 else 0.0
        hot_degree_hours = float(np.sum(hot_deviations[occupied_mask] * step_hours)) if occupied_steps > 0 else 0.0
        total_degree_hours = cold_degree_hours + hot_degree_hours

        # Comfort compliance percentage during occupied periods
        in_band_mask = occupied_mask & (mean_temps >= 20.0) & (mean_temps <= 24.0)
        comfort_compliance_pct = (
            float(np.sum(in_band_mask) / occupied_steps * 100.0)
            if occupied_steps > 0
            else 100.0
        )

        # Actuator switching frequency
        discrete_actions = df["discrete_action_sum"].values
        switches = int(np.sum(np.diff(discrete_actions) != 0)) if len(discrete_actions) > 1 else 0

        # Reward component integrals
        prod_regret_sum = float(df["productivity_regret"].sum()) if "productivity_regret" in df else 0.0
        energy_cost_sum = float(df["energy_cost"].sum()) if "energy_cost" in df else 0.0
        carbon_penalty_sum = float(df["carbon_penalty"].sum()) if "carbon_penalty" in df else 0.0
        total_return = float(df["reward"].sum())

        return {
            "episode_steps": steps,
            "occupied_hours": occupied_steps * step_hours,
            "thermal_comfort": {
                "cold_degree_hours": cold_degree_hours,
                "hot_degree_hours": hot_degree_hours,
                "total_degree_hours": total_degree_hours,
                "comfort_compliance_pct": comfort_compliance_pct,
                "min_zone_temp": float(np.min(mean_temps)),
                "max_zone_temp": float(np.max(mean_temps)),
                "mean_zone_temp": float(np.mean(mean_temps)),
            },
            "actuation": {
                "discrete_switch_count": switches,
                "switch_frequency_per_day": float(switches / (steps * step_hours / 24.0)) if steps > 0 else 0.0,
            },
            "reward_breakdown": {
                "productivity_regret_total": prod_regret_sum,
                "energy_cost_total": energy_cost_sum,
                "carbon_penalty_total": carbon_penalty_sum,
                "total_return": total_return,
            },
        }
