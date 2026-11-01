"""Gate 6 Test Suite: Information Leakage Protection and Semantic Diagnostics.
Validates:
1. Four-Ring defense architecture in PolicyAdapter:
   - Ring 1: Strict input boundary.
   - Ring 2: Static AST import and stack-inspection blocking (AC 15).
   - Ring 3: Runtime memory immutability (obs.flags.writeable = False).
   - Ring 4: Empirical Red Team probes (AC 15 & AC 16).
2. Interventional semantic actuator probe for physical causality and swap detection (AC 16).
3. End-to-end runner containment: rogue policies transition run to FAILED and INVALID.
"""

from __future__ import annotations
import json
from pathlib import Path
import sys
import numpy as np
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
FOUNDATION_ROOT = PROJECT_ROOT / "04_EXPERIMENT_FOUNDATION"
if str(FOUNDATION_ROOT) not in sys.path:
    sys.path.insert(0, str(FOUNDATION_ROOT))

from core.policy_adapter import PolicyAdapter, SecurityViolationError
from core.runner import SimulationRunner
from core.registry import ExperimentRegistry, RunStatus
from evaluation.semantic_probe import SemanticActuatorProbe


@pytest.fixture
def dummy_specs():
    action_spec = {
        "discrete_action": np.zeros(5, dtype=np.int32),
        "continuous_action": np.zeros(92, dtype=np.float32),
    }
    metadata = {
        "observation_field_names": ["zone_1_air_temperature", "zone_2_air_temperature"],
        "zone_action_indices": {"VAV_1": {"damper": 0, "reheat": 1}},
    }
    return action_spec, metadata


# ==============================================================================
# Ring 2 & Ring 4: Static AST Leakage & Call Stack Probes (AC 15)
# ==============================================================================

def test_ast_rejects_simulator_import(dummy_specs):
    """AC 15: Policy attempting to import simulator is rejected during initialization."""
    action_spec, metadata = dummy_specs

    class RogueSimulatorImportPolicy:
        def __init__(self, metadata=None, action_spec=None):
            import smart_buildings.smart_control.simulator  # Prohibited!
        def get_action(self, obs):
            return {"discrete_action": np.zeros(5, dtype=np.int32), "continuous_action": np.zeros(92, dtype=np.float32)}

    with pytest.raises(SecurityViolationError, match="Prohibited module import.*smart_buildings.smart_control"):
        PolicyAdapter(RogueSimulatorImportPolicy, action_spec, metadata)


def test_ast_rejects_ctypes_and_subprocess(dummy_specs):
    """Policy attempting to import ctypes or subprocess is rejected."""
    action_spec, metadata = dummy_specs

    class RogueCtypesPolicy:
        def __init__(self, metadata=None, action_spec=None):
            import ctypes  # Prohibited!
        def get_action(self, obs):
            return {"discrete_action": np.zeros(5, dtype=np.int32), "continuous_action": np.zeros(92, dtype=np.float32)}

    with pytest.raises(SecurityViolationError, match="Prohibited module import.*ctypes"):
        PolicyAdapter(RogueCtypesPolicy, action_spec, metadata)


def test_ast_rejects_stack_crawl_inspection(dummy_specs):
    """AC 15: Policy attempting to inspect inspect.currentframe().f_back or sys._getframe is rejected."""
    action_spec, metadata = dummy_specs

    class StackCrawlerInspectPolicy:
        def get_action(self, obs):
            import inspect  # Prohibited!
            f = inspect.currentframe().f_back
            return {"discrete_action": np.zeros(5, dtype=np.int32), "continuous_action": np.zeros(92, dtype=np.float32)}

    with pytest.raises(SecurityViolationError, match="Prohibited module import.*inspect"):
        PolicyAdapter(StackCrawlerInspectPolicy, action_spec, metadata)

    class StackCrawlerFramePolicy:
        def get_action(self, obs):
            f = sys._getframe(1)  # Prohibited attribute access!
            return {"discrete_action": np.zeros(5, dtype=np.int32), "continuous_action": np.zeros(92, dtype=np.float32)}

    with pytest.raises(SecurityViolationError, match="Prohibited attribute access.*_getframe"):
        PolicyAdapter(StackCrawlerFramePolicy, action_spec, metadata)


def test_ast_rejects_dynamic_eval(dummy_specs):
    """Policy attempting dynamic eval() or exec() is rejected."""
    action_spec, metadata = dummy_specs

    class RogueEvalPolicy:
        def get_action(self, obs):
            eval("1 + 1")  # Prohibited dynamic call
            return {"discrete_action": np.zeros(5, dtype=np.int32), "continuous_action": np.zeros(92, dtype=np.float32)}

    with pytest.raises(SecurityViolationError, match="Prohibited dynamic call.*eval"):
        PolicyAdapter(RogueEvalPolicy, action_spec, metadata)


def test_runner_containment_of_rogue_policy(tmp_path: Path):
    """AC 15 Proof: SimulationRunner marks run as FAILED and INVALID when rogue policy raises SecurityViolationError."""
    runs_dir = tmp_path / "runs"
    registry = ExperimentRegistry(base_runs_dir=runs_dir)
    runner = SimulationRunner(registry=registry)

    class MaliciousPolicy:
        def __init__(self, metadata=None, action_spec=None):
            import subprocess  # Prohibited!
        def get_action(self, obs):
            return {}

    scenario_dir = Path(__file__).resolve().parents[2] / "smart_buildings" / "training_scenarios" / "building_train_1" / "atlanta_2"

    with pytest.raises(SecurityViolationError):
        runner.execute_episode(
            policy_class=MaliciousPolicy,
            scenario_dir=scenario_dir,
            experiment_id="EXP_SECURITY",
            max_steps=10,
        )

    # Verify run manifest was transitioned to FAILED and INVALID
    runs = registry.list_runs()
    assert len(runs) == 1
    m = runs[0]
    assert m["status"] == "FAILED"
    assert m["execution_status"] == "FAILED"
    assert m["evidence_validity"] == "INVALID"
    assert any("SecurityViolationError" in err["error"] for err in m["errors"])


# ==============================================================================
# Ring 3: Runtime Memory Immutability
# ==============================================================================

def test_observation_memory_immutability(dummy_specs):
    """Ring 3: Policy mutating obs raises ValueError: assignment destination is read-only."""
    action_spec, metadata = dummy_specs

    class ObservationMutatorPolicy:
        def get_action(self, obs):
            obs[0] = 999.0  # Attempt in-place write!
            return {"discrete_action": np.zeros(5, dtype=np.int32), "continuous_action": np.zeros(92, dtype=np.float32)}

    adapter = PolicyAdapter(ObservationMutatorPolicy, action_spec, metadata)
    obs = np.array([293.15, 294.15], dtype=np.float32)

    with pytest.raises(ValueError, match="read-only"):
        adapter.get_action(obs)

    # Verify caller's array was protected
    assert obs[0] == pytest.approx(293.15)


def test_metadata_immutability(dummy_specs):
    """Ring 3: Policy modifying metadata receives deep-copied version without tainting caller."""
    action_spec, metadata = dummy_specs

    class MetadataMutatorPolicy:
        def __init__(self, metadata, action_spec):
            metadata["zone_action_indices"]["VAV_1"]["reheat"] = 999  # Attempt caller mutation

        def get_action(self, obs):
            return {"discrete_action": np.zeros(5, dtype=np.int32), "continuous_action": np.zeros(92, dtype=np.float32)}

    adapter = PolicyAdapter(MetadataMutatorPolicy, action_spec, metadata)
    # Caller's original metadata dict remains untainted
    assert metadata["zone_action_indices"]["VAV_1"]["reheat"] == 1


# ==============================================================================
# Ring 4: Controlled Interventional Semantic Actuator Probe (AC 16)
# ==============================================================================

def test_semantic_actuator_probe_valid_response():
    """AC 16: Interventional pulse causing ΔT > 0.5 K and margin > 0.3 K passes."""
    initial_temps = {
        "VAV_1": 293.0,
        "VAV_2": 293.0,
        "VAV_3": 293.0,
    }
    final_temps = {
        "VAV_1": 293.80,  # ΔT = +0.80 K (meets > 0.5 K)
        "VAV_2": 293.05,  # ΔT = +0.05 K (margin = 0.75 K > 0.3 K)
        "VAV_3": 293.02,  # ΔT = +0.02 K
    }

    report = SemanticActuatorProbe.evaluate_response(
        target_zone="VAV_1",
        initial_temperatures=initial_temps,
        final_temperatures=final_temps,
    )

    assert report["schema_version"] == "v1.0"
    assert report["target_zone"] == "VAV_1"
    assert report["passed"] is True
    assert report["delta_t_target_k"] == pytest.approx(0.80)
    assert report["margin_k"] == pytest.approx(0.75)
    assert len(report["rejection_reasons"]) == 0


def test_semantic_actuator_probe_detects_swapped_actuator():
    """AC 16 (Red Team F1): Actuator channel swapped between VAV_1 and VAV_2 is cleanly detected."""
    # When pulsing VAV_1's mapped channel, VAV_2 heats up instead of VAV_1!
    initial_temps = {
        "VAV_1": 293.0,
        "VAV_2": 293.0,
        "VAV_3": 293.0,
    }
    final_temps = {
        "VAV_1": 293.05,  # ΔT = +0.05 K (target fails to heat up)
        "VAV_2": 293.75,  # ΔT = +0.75 K (culprit zone heats up instead!)
        "VAV_3": 293.02,  # ΔT = +0.02 K
    }

    report = SemanticActuatorProbe.evaluate_response(
        target_zone="VAV_1",
        initial_temperatures=initial_temps,
        final_temperatures=final_temps,
    )

    assert report["passed"] is False
    assert report["delta_t_target_k"] == pytest.approx(0.05)
    assert report["max_delta_others_k"] == pytest.approx(0.75)
    assert any("swapped actuator channel" in r for r in report["rejection_reasons"])
    assert any("below minimum threshold" in r for r in report["rejection_reasons"])


def test_semantic_actuator_probe_live_environment(tmp_path: Path):
    """AC 16 End-to-End: Executes 4-step pulse intervention on real simulator and writes semantic_probe_report.json."""
    from smart_buildings.evaluate import load_hybrid_environment, create_building_meta_data
    scenario_dir = PROJECT_ROOT / "smart_buildings" / "training_scenarios" / "building_train_1" / "atlanta_2"
    gin_path = scenario_dir / "config.gin"
    env = load_hybrid_environment(gin_path)
    env.metrics_path = None
    meta = create_building_meta_data(env, scenario_dir)

    out_report = tmp_path / "semantic_probe_report.json"
    report = SemanticActuatorProbe.run_environment_probe(
        env=env,
        metadata=meta,
        target_vav="VAV_1",
        probe_steps=4,
        output_path=out_report,
    )

    assert out_report.is_file()
    assert report["schema_version"] == "v1.0"
    assert report["target_zone"] == "VAV_1"
    assert "delta_t_target_k" in report
    assert "zone_deltas" in report
    assert len(report["zone_deltas"]) > 0
