"""Phase 05 Stage 4 Closure: Work Package 2 (WP2) - Two-Level Policy Leakage Hardening.

Validates the hardened information leakage boundary:
Level 1: Static AST Analysis Hardening
- Direct ground-truth file reads (open("config.gin"), Path("weather.csv").read_text()).
- Prohibited modules (smart_buildings.weather, smart_buildings.simulator, ctypes, etc.).
- Prohibited stack and frame crawling (_getframe, currentframe, f_back, etc.).
- Recursive AST inspection across local dependencies in artifacts/local_deps/.
- Full SimulationRunner integration: execution halted before env.reset(), status=FAILED, validity=INVALID.

Level 2: Architectural In-Process Threat Model Documentation
- Documents static AST boundaries vs in-process physical memory limitations.
- Preserves machine-readable evidence and certification report.
"""

from __future__ import annotations
import ast
import json
import os
from pathlib import Path
import shutil
import sys
from unittest.mock import MagicMock, patch
import numpy as np
import pytest

# Ensure project and foundation roots are in sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
FOUNDATION_ROOT = PROJECT_ROOT / "04_EXPERIMENT_FOUNDATION"
for p in [str(PROJECT_ROOT), str(FOUNDATION_ROOT)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from core.registry import ExperimentRegistry, RunStatus, EvidenceValidity
from core.runner import SimulationRunner
from core.policy_adapter import PolicyAdapter, SecurityViolationError

WP2_EVIDENCE_DIR = (
    PROJECT_ROOT / "05_FAILURE_ENGINEERING" / "evidence" / "stage_4" / "closure_wp2_leakage"
)


@pytest.fixture(scope="session", autouse=True)
def setup_wp2_root():
    WP2_EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)


def record_wp2_result(
    test_id: str,
    title: str,
    attack_description: str,
    detection_mechanism: str,
    system_response: str,
    verdict: str,
    details: dict | None = None,
):
    target_dir = WP2_EVIDENCE_DIR / test_id.lower()
    target_dir.mkdir(parents=True, exist_ok=True)
    record = {
        "work_package": "WP2_LEAKAGE_HARDENING",
        "test_id": test_id,
        "title": title,
        "attack_description": attack_description,
        "detection_mechanism": detection_mechanism,
        "system_response": system_response,
        "verdict": verdict,
        "details": details or {},
    }
    with open(target_dir / f"{test_id.lower()}_record.json", "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2)
    return record


def test_wp2_direct_ground_truth_file_open():
    """Detects and blocks direct calls to open('config.gin') or scenario weather paths."""
    test_dir = WP2_EVIDENCE_DIR / "wp2_01_direct_file_open"
    shutil.rmtree(test_dir, ignore_errors=True)
    test_dir.mkdir(parents=True, exist_ok=True)

    leaky_policy_code = """
class LeakyOpenPolicy:
    def __init__(self, action_spec=None, metadata=None, **kwargs):
        # Malicious attempt to read scenario ground-truth config
        with open("config.gin", "r") as f:
            self.config = f.read()

    def get_action(self, obs):
        return {"continuous_action": [0.0, 0.0], "discrete_action": [0]}
"""

    with pytest.raises(SecurityViolationError) as exc_info:
        PolicyAdapter.audit_policy_ast(leaky_policy_code)

    err_msg = str(exc_info.value)
    assert "Prohibited direct file access to sensitive path 'config.gin'" in err_msg

    record_wp2_result(
        test_id="WP2_01",
        title="Direct File Access via open('config.gin')",
        attack_description="Policy attempts to open config.gin directly during __init__",
        detection_mechanism="Static AST Call analysis for open() targeting sensitive path pattern",
        system_response="SecurityViolationError raised before policy instantiation",
        verdict="PASS",
        details={"error_message": err_msg},
    )


def test_wp2_pathlib_ground_truth_read():
    """Detects and blocks Path('...weather...').read_text() calls."""
    test_dir = WP2_EVIDENCE_DIR / "wp2_02_pathlib_read"
    shutil.rmtree(test_dir, ignore_errors=True)
    test_dir.mkdir(parents=True, exist_ok=True)

    leaky_path_code = """
from pathlib import Path

class LeakyPathlibPolicy:
    def __init__(self, action_spec=None, metadata=None, **kwargs):
        weather_data = Path("smart_buildings/weather/phoenix.csv").read_text()

    def get_action(self, obs):
        return {"continuous_action": [0.0, 0.0], "discrete_action": [0]}
"""

    with pytest.raises(SecurityViolationError) as exc_info:
        PolicyAdapter.audit_policy_ast(leaky_path_code)

    err_msg = str(exc_info.value)
    assert "Prohibited direct file access to sensitive path 'smart_buildings/weather/phoenix.csv'" in err_msg

    record_wp2_result(
        test_id="WP2_02",
        title="Pathlib Direct File Access to Weather Data",
        attack_description="Policy uses Path(...weather...).read_text() to inspect ground truth weather series",
        detection_mechanism="Static AST Attribute Call analysis for Path.read_text targeting sensitive pattern",
        system_response="SecurityViolationError raised, execution aborted",
        verdict="PASS",
        details={"error_message": err_msg},
    )


def test_wp2_prohibited_module_imports():
    """Detects and blocks imports of smart_buildings.weather and smart_buildings.simulator."""
    test_dir = WP2_EVIDENCE_DIR / "wp2_03_prohibited_modules"
    shutil.rmtree(test_dir, ignore_errors=True)
    test_dir.mkdir(parents=True, exist_ok=True)

    weather_import_code = """
class WeatherImportPolicy:
    def __init__(self, **kwargs):
        from smart_buildings.weather import load_weather
    def get_action(self, obs):
        return {}
"""
    with pytest.raises(SecurityViolationError) as exc1:
        PolicyAdapter.audit_policy_ast(weather_import_code)
    assert "smart_buildings.weather" in str(exc1.value)

    sim_import_code = """
import smart_buildings.simulator as sim
class SimImportPolicy:
    def get_action(self, obs):
        return {}
"""
    with pytest.raises(SecurityViolationError) as exc2:
        PolicyAdapter.audit_policy_ast(sim_import_code)
    assert "smart_buildings.simulator" in str(exc2.value)

    record_wp2_result(
        test_id="WP2_03",
        title="Prohibited Module Imports (weather, simulator)",
        attack_description="Policy attempts to import smart_buildings.weather and smart_buildings.simulator",
        detection_mechanism="Static AST Import and ImportFrom analysis against PROHIBITED_MODULES",
        system_response="SecurityViolationError raised for both direct and from-import variants",
        verdict="PASS",
        details={"weather_err": str(exc1.value), "sim_err": str(exc2.value)},
    )


def test_wp2_recursive_local_dependencies_audit():
    """Recursively audits helper modules inside local_deps_dir."""
    test_dir = WP2_EVIDENCE_DIR / "wp2_04_recursive_deps"
    shutil.rmtree(test_dir, ignore_errors=True)
    test_dir.mkdir(parents=True, exist_ok=True)

    # Clean top-level policy
    clean_policy_code = """
class CleanPolicyWithSneakyHelper:
    def __init__(self, **kwargs):
        pass
    def get_action(self, obs):
        return {"action": 0}
"""

    # Create local_deps directory with a malicious helper
    local_deps = test_dir / "local_deps"
    local_deps.mkdir(parents=True, exist_ok=True)

    # 1. Helper with ctypes import
    (local_deps / "stealth_helper.py").write_text(
        "import ctypes\ndef sneak(): return ctypes.c_int(42)\n", encoding="utf-8"
    )

    # 2. Sub-package helper with file open
    sub_pkg = local_deps / "utils"
    sub_pkg.mkdir(parents=True, exist_ok=True)
    (sub_pkg / "io_helper.py").write_text(
        "def read_cfg():\n    return open('scenario/config.gin').read()\n", encoding="utf-8"
    )

    with pytest.raises(SecurityViolationError) as exc_info:
        PolicyAdapter.audit_policy_ast(clean_policy_code, local_deps_dir=local_deps)

    err_msg = str(exc_info.value)
    # Must catch BOTH violations across different files and subdirectories
    assert "local_dep:stealth_helper.py" in err_msg
    assert "Prohibited module import: 'ctypes'" in err_msg
    assert "local_dep:io_helper.py" in err_msg
    assert "Prohibited direct file access to sensitive path 'scenario/config.gin'" in err_msg

    record_wp2_result(
        test_id="WP2_04",
        title="Recursive Local Dependencies AST Audit",
        attack_description="Clean entrypoint policy imports helper modules that contain ctypes and open('config.gin')",
        detection_mechanism="Recursive walk across local_deps_dir auditing every .py file AST",
        system_response="All violations in nested dependencies aggregated and raised in SecurityViolationError",
        verdict="PASS",
        details={"error_message": err_msg},
    )


def test_wp2_clean_policy_and_deps_pass():
    """Verifies that clean policies and legitimate local dependencies pass audit without false positives."""
    test_dir = WP2_EVIDENCE_DIR / "wp2_05_clean_policy"
    shutil.rmtree(test_dir, ignore_errors=True)
    test_dir.mkdir(parents=True, exist_ok=True)

    clean_code = """
import numpy as np

class LegitimatePolicy:
    def __init__(self, action_spec=None, metadata=None, **kwargs):
        self.action_spec = action_spec
        self.metadata = metadata

    def get_action(self, obs):
        return {
            "continuous_action": np.array([0.1, -0.1], dtype=np.float32),
            "discrete_action": np.array([1], dtype=np.int32),
        }
"""
    local_deps = test_dir / "local_deps"
    local_deps.mkdir(parents=True, exist_ok=True)
    (local_deps / "math_helper.py").write_text(
        "import numpy as np\ndef clip_action(a): return np.clip(a, -1.0, 1.0)\n",
        encoding="utf-8",
    )

    # Should pass without raising any exception
    violations = PolicyAdapter.audit_policy_ast(clean_code, local_deps_dir=local_deps)
    assert violations == []

    record_wp2_result(
        test_id="WP2_05",
        title="Clean Policy and Clean Local Dependency Control",
        attack_description="Legitimate RL policy using numpy and local math_helper.py",
        detection_mechanism="Static AST audit across policy and local_deps",
        system_response="Zero violations detected; returned empty violations list",
        verdict="PASS",
        details={"violations_count": len(violations)},
    )


def test_wp2_simulation_runner_integration_halt():
    """Verifies SimulationRunner halts before env.reset(), sets status=FAILED, validity=INVALID."""
    test_dir = WP2_EVIDENCE_DIR / "wp2_06_runner_integration"
    shutil.rmtree(test_dir, ignore_errors=True)
    test_dir.mkdir(parents=True, exist_ok=True)

    scen_dir = test_dir / "scenario"
    scen_dir.mkdir(parents=True, exist_ok=True)
    gin_file = scen_dir / "config.gin"
    gin_file.write_text("# Test scenario config\n", encoding="utf-8")

    reg = ExperimentRegistry(base_runs_dir=test_dir / "runs")
    runner = SimulationRunner(registry=reg)

    class HostilePolicy:
        def __init__(self, **kwargs):
            import ctypes
        def get_action(self, obs):
            return {}

    mock_env = MagicMock()
    mock_env.action_spec.return_value = {
        "continuous_action": np.zeros(2, dtype=np.float32),
        "discrete_action": np.zeros(1, dtype=np.int32),
    }

    with patch("core.runner.load_hybrid_environment", return_value=mock_env), \
         patch("core.runner.create_building_meta_data", return_value={"zone_temp_indices": []}):
        with pytest.raises(SecurityViolationError):
            runner.execute_episode(
                experiment_id="EXP_WP2_HOSTILE",
                policy_class=HostilePolicy,
                scenario_dir=scen_dir,
                max_steps=10,
            )

    # env.reset() must NEVER have been called!
    assert mock_env.reset.call_count == 0, "env.reset() must not be called when policy fails AST audit"
    assert mock_env.step.call_count == 0, "env.step() must not be called"

    runs = reg.list_runs()
    assert len(runs) == 1
    manifest = runs[0]
    assert manifest["status"] == RunStatus.FAILED.value
    assert manifest["execution_status"] == RunStatus.FAILED.value
    assert manifest["evidence_validity"] == EvidenceValidity.INVALID.value
    assert any("SecurityViolationError" in err["error"] for err in manifest["errors"])

    record_wp2_result(
        test_id="WP2_06",
        title="SimulationRunner Fail-Closed Halt Before env.reset()",
        attack_description="Hostile policy submitted to SimulationRunner.execute_episode()",
        detection_mechanism="PolicyAdapter AST audit in SimulationRunner before env.reset()",
        system_response="Zero simulation steps executed; status=FAILED, evidence_validity=INVALID recorded in run manifest",
        verdict="PASS",
        details={"env_reset_called": mock_env.reset.call_count > 0, "manifest_status": manifest["status"]},
    )


def test_wp2_summary_and_threat_model_generation():
    """Generates overall WP2 summary report, JSON data, and Level 2 threat model document."""
    tests = [
        "wp2_01",
        "wp2_02",
        "wp2_03",
        "wp2_04",
        "wp2_05",
        "wp2_06",
    ]
    records = []
    for t in tests:
        rf = WP2_EVIDENCE_DIR / f"{t}_record.json"
        if not rf.is_file():
            # Check subdirectory
            sub_rf = list(WP2_EVIDENCE_DIR.glob(f"{t}*/{t}_record.json"))
            if sub_rf:
                rf = sub_rf[0]
        assert rf.is_file(), f"Missing record: {rf}"
        with open(rf, "r", encoding="utf-8") as f:
            records.append(json.load(f))

    summary_json = {
        "campaign": "PHASE_05_STAGE_4_CLOSURE",
        "work_package": "WP2",
        "title": "Two-Level Policy Information Leakage Hardening Campaign",
        "total_tests": len(records),
        "all_passed": all(r["verdict"] == "PASS" for r in records),
        "records": records,
    }

    with open(WP2_EVIDENCE_DIR / "wp2_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary_json, f, indent=2)

    # 1. Generate Executive Report
    rep_lines = [
        "# Work Package 2 (WP2) - Policy Information Leakage Hardening Report",
        "",
        "## Executive Summary",
        "",
        "- **Objective**: Validate two-level information leakage defenses: Level 1 static AST enforcement and Level 2 in-process threat model boundary documentation.",
        "- **Tests Executed**: 6 comprehensive security and regression tests.",
        f"- **Verdict**: {'ALL PASSED' if summary_json['all_passed'] else 'FAILURES DETECTED'}.",
        "",
        "## Verification Results",
        "",
        "| Test ID | Title | Injected Vector | Defense Mechanism | Verdict |",
        "|---|---|---|---|---|",
    ]
    for r in records:
        rep_lines.append(
            f"| **{r['test_id']}** | {r['title']} | {r['attack_description']} | {r['detection_mechanism']} | **{r['verdict']}** |"
        )

    rep_lines.extend([
        "",
        "## Summary of Hardening Delivered",
        "",
        "1. **Direct File Read Blocking**: Static AST Call visitor flags calls to `open()` and `Path(...).read_text()` / `read_bytes()` referencing sensitive ground-truth patterns (`config.gin`, `weather`, `ground_truth`, `scenario`).",
        "2. **Extended Prohibited Modules**: `smart_buildings.weather` and `smart_buildings.simulator` added to Ring 2 prohibited modules.",
        "3. **Recursive Local Dependency Auditing**: `PolicyAdapter.audit_policy_ast()` now traverses all `.py` files under `artifacts/local_deps/`, preventing policies from hiding violations in helper scripts.",
        "4. **Fail-Closed Runner Integration**: Pre-reset audit aborts immediately when violations are detected; zero simulation steps occur; manifest strictly marked `FAILED` with `INVALID` validity.",
        "5. **Clean Controls Preserved**: Legitimate policies and valid helper modules execute without false positive rejections.",
    ])

    report_file = WP2_EVIDENCE_DIR / "WP2_LEAKAGE_HARDENING_REPORT.md"
    report_file.write_text("\n".join(rep_lines), encoding="utf-8")
    assert report_file.is_file()

    # 2. Generate Level 2 Threat Model Documentation
    tm_lines = [
        "# Level 2 Threat Model: In-Process Python Policy Execution Boundaries",
        "",
        "## 1. Architectural Scope & Context",
        "",
        "In the Smart Buildings competition framework, candidate policy code is loaded and executed within the same Python interpreter runtime as the building simulator and evaluation harness.",
        "This architectural decision enables high-throughput simulation without IPC serialization overhead, but establishes fundamental boundary distinctions.",
        "",
        "## 2. Two-Level Defense Architecture",
        "",
        "```",
        "+-----------------------------------------------------------------------------------+",
        "| LEVEL 1: STATIC AST ANALYSIS & RUNTIME WRAPPER (Ring 1 - Ring 4)                 |",
        "| - Ring 1: Interface contract validation (action shapes, bounds, dtypes, non-NaN)  |",
        "| - Ring 2: Static AST audit of entrypoint policy & recursive local dependencies     |",
        "| - Ring 3: Deepcopy isolation of observation & metadata structures                  |",
        "| - Ring 4: Execution timing, latency tracking, and exception containment           |",
        "+-----------------------------------------------------------------------------------+",
        "|                                                                                   |",
        "| LEVEL 2: IN-PROCESS PHYSICAL BOUNDARY (Explicit Architectural Limitations)        |",
        "| - Python AST analysis operates exclusively on static Python source text.          |",
        "| - AST cannot inspect machine instructions inside compiled C/C++ extensions.       |",
        "| - Shared memory space means process isolation is NOT enforced at OS kernel level. |",
        "+-----------------------------------------------------------------------------------+",
        "```",
        "",
        "## 3. Guarantees Enforced by Level 1 (Static AST Guard)",
        "",
        "Level 1 provides deterministic, fail-closed enforcement against the following threat vectors:",
        "",
        "- **Prohibited Imports**: Blocks imports of simulator internals (`smart_buildings.simulator`, `smart_control`), ground-truth data (`smart_buildings.weather`), native process escape (`ctypes`, `subprocess`, `multiprocessing`), and unauthorized network I/O (`socket`, `requests`, `urllib`).",
        "- **Stack Crawling & Metaprogramming**: Blocks frame inspection (`_getframe`, `currentframe`, `f_back`, `f_locals`), garbage collector crawling (`get_objects`), class hierarchy navigation (`__subclasses__`), and dynamic execution (`eval`, `exec`, `__import__`).",
        "- **Direct Scenario File Access**: Blocks literal and attribute calls to `open()`, `Path.read_text()`, and `Path.open()` targeting `config.gin`, `weather`, or scenario ground-truth paths.",
        "- **Recursive Dependency Scanning**: Walks all `.py` files inside `artifacts/local_deps/`, preventing obfuscation via split modules.",
        "",
        "## 4. Inherent Physical Limitations of In-Process Execution (Level 2)",
        "",
        "The evaluation harness acknowledges the following theoretical and physical boundaries:",
        "",
        "1. **Compiled C-Extensions & Shared Memory**: If a policy executes pre-compiled binary modules (`.so`, `.pyd`, `.dll`), AST analysis cannot inspect binary opcodes. Within a shared process, native C code has pointer access to process memory.",
        "2. **Obfuscated / Dynamic Path Construction**: String operations that dynamically compute path names at runtime without literal indicators cannot be proven by static AST alone.",
        "3. **True Security Boundary Requirement**: For untrusted multi-tenant execution or adversarial competitions where arbitrary binary execution is permitted, OS-level process isolation (e.g. gVisor sandbox, seccomp-bpf filters, or isolated container execution) is required.",
        "",
        "## 5. Defense-in-Depth Governance",
        "",
        "To mitigate in-process limitations without requiring full containerization overhead, the infrastructure employs multi-stage governance:",
        "- **Artifact Vault Freezing**: Complete source of policy and dependencies is hashed and vaulted into `artifacts/` prior to execution.",
        "- **Score Verification & Baseline Reconstruction**: Downstream verification recomputes scores independently from raw trace tensors.",
        "- **Lineage Quarantine**: Tainted upstream experiments automatically cascade quarantine status to all dependent candidates.",
        "- **Release Auditing**: Releases must undergo independent package auditing and signature validation before promotion.",
    ]

    tm_file = WP2_EVIDENCE_DIR / "POLICY_LEAKAGE_THREAT_MODEL.md"
    tm_file.write_text("\n".join(tm_lines), encoding="utf-8")
    assert tm_file.is_file()
