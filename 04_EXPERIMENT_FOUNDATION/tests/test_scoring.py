"""Tests for Independent Score Verification and Engineering Diagnostics."""

import sys
from pathlib import Path
import json
import pytest
import numpy as np

PHASE_ROOT = Path(__file__).resolve().parents[1]
if str(PHASE_ROOT) not in sys.path:
    sys.path.insert(0, str(PHASE_ROOT))

from evaluation.score_verification import ScoreVerifier
from evaluation.diagnostics import DiagnosticsEngine

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BASELINE_JSON_PATH = PROJECT_ROOT / "starter_kit_pinned" / "baseline_returns.json"
S0_EPISODE_DIR = (
    PROJECT_ROOT
    / "03_SOURCE_TRUTH"
    / "evidence"
    / "s0_episode"
    / "building_train_1"
    / "atlanta_2"
    / "transfer"
)


def test_score_verifier_piecewise_shortfall():
    """Shortfall f(d) must be linear in [0, 5.0] and quadratic beyond 5.0."""
    # Zero deviation
    assert ScoreVerifier.compute_comfort_shortfall(0.0) == 0.0

    # Within 5.0 band: linear d/5.0
    assert ScoreVerifier.compute_comfort_shortfall(2.5) == pytest.approx(0.5, rel=1e-6)
    assert ScoreVerifier.compute_comfort_shortfall(5.0) == pytest.approx(1.0, rel=1e-6)

    # Beyond 5.0 band: 1.0 + ((d - 5)/5)^2
    assert ScoreVerifier.compute_comfort_shortfall(10.0) == pytest.approx(2.0, rel=1e-6)
    assert ScoreVerifier.compute_comfort_shortfall(15.0) == pytest.approx(5.0, rel=1e-6)


def test_score_verifier_zero_occupancy_regret():
    """When total occupancy is zero, productivity regret must strictly be 0.0."""
    regret = ScoreVerifier.compute_productivity_regret(
        zone_deviations=[10.0, 15.0, 20.0],
        zone_occupants=[0.0, 0.0, 0.0],
    )
    assert regret == 0.0


def test_score_verifier_s0_episode_parity():
    """Reconstructs score from the 8,640-step S0 episode and verifies parity <= 1e-6."""
    rc_path = S0_EPISODE_DIR / "reward_components.csv"
    summary_path = S0_EPISODE_DIR / "summary.json"

    assert summary_path.is_file(), f"Missing {summary_path}"
    with open(summary_path, "r", encoding="utf-8") as f:
        official_summary = json.load(f)

    official_return = official_summary["total_reward"]
    assert official_summary["total_steps"] == 8640

    if rc_path.is_file():
        # Verify from reward_components.csv
        import pandas as pd
        df = pd.read_csv(rc_path)
        reward_col = "agent_reward" if "agent_reward" in df.columns else "reward"
        reconstructed_return = float(df[reward_col].sum())
        diff = abs(reconstructed_return - official_return)
        assert diff <= ScoreVerifier.PARITY_TOLERANCE, f"Return diff {diff:.2e} exceeds tolerance"


def test_diagnostics_engine_on_s0_episode():
    """Diagnostics engine must compute degree-hours, compliance %, and actuator statistics."""
    timeseries_path = S0_EPISODE_DIR / "timeseries.csv"
    if timeseries_path.is_file():
        # Build minimal trace CSV for diagnostics test
        import pandas as pd
        df = pd.read_csv(timeseries_path)
        
        # Prepare required columns
        minimal_df = pd.DataFrame({
            "step": np.arange(len(df)),
            "reward": np.zeros(len(df)),
            "mean_zone_temp": df["zone_temp_mean"] if "zone_temp_mean" in df else 22.0,
            "outdoor_temp": df["outdoor_temp"] if "outdoor_temp" in df else 15.0,
            "total_occupants": df["occupants_sum"] if "occupants_sum" in df else 10.0,
            "discrete_action_sum": np.ones(len(df), dtype=int),
        })
        temp_csv = S0_EPISODE_DIR / "diag_test_trace.csv"
        minimal_df.to_csv(temp_csv, index=False)
        try:
            diag = DiagnosticsEngine.analyze_trace(temp_csv)
            assert diag["episode_steps"] == 8640
            assert "thermal_comfort" in diag
            assert "total_degree_hours" in diag["thermal_comfort"]
            assert diag["thermal_comfort"]["comfort_compliance_pct"] >= 0.0
        finally:
            if temp_csv.is_file():
                temp_csv.unlink()


def test_score_verifier_multi_scenario_aggregation_parity():
    """Independent multi-scenario aggregation must equal official baseline sum within tolerance."""
    assert BASELINE_JSON_PATH.is_file(), f"Missing {BASELINE_JSON_PATH}"
    with open(BASELINE_JSON_PATH, "r", encoding="utf-8") as f:
        baseline_data = json.load(f)

    assert len(baseline_data) == 30, f"Expected 30 scenarios, got {len(baseline_data)}"

    policies = ["bang_bang", "fixed_setpoint", "pid", "pid_water"]
    for policy in policies:
        scenario_returns = {sc: baseline_data[sc][policy] for sc in baseline_data}
        expected_total = sum(scenario_returns.values())

        # Verify via independent ScoreVerifier
        res = ScoreVerifier.verify_multi_scenario_score(
            scenario_returns=scenario_returns,
            reported_suite_return=expected_total,
        )
        assert res["valid"], f"Multi-scenario verification failed for {policy}: {res.get('error')}"
        assert res["scenario_count"] == 30
        assert res["discrepancy"] <= ScoreVerifier.PARITY_TOLERANCE


def test_score_verifier_reward_arithmetic_on_s0_episode():
    """Validates step reward component arithmetic (0.6*regret - 0.2*energy - 0.2*carbon) on all 8640 steps."""
    rc_path = S0_EPISODE_DIR / "reward_components.csv"
    if not rc_path.is_file():
        pytest.skip(f"S0 episode reward_components.csv not found at {rc_path}")

    import pandas as pd
    df = pd.read_csv(rc_path)
    records = df.to_dict(orient="records")

    res = ScoreVerifier.verify_reward_arithmetic(records)
    assert res["valid"], f"Arithmetic verification failed: {res.get('error')}"
