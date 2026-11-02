"""Policy Adapter for Smart Buildings Challenge.
Encapsulates policy lifecycle, input/output contract enforcement,
cryptographic hashing, and error isolation.
"""

from __future__ import annotations
import ast
import copy
import hashlib
import importlib.util
import inspect
import json
from pathlib import Path
import sys
import textwrap
import time
from typing import Any, Mapping, Type
import numpy as np


class SecurityViolationError(Exception):
    """Raised when a policy violates information leakage boundaries or security sandbox."""
    pass


class PolicyAdapter:
    """Wraps a building control policy, enforcing runtime contracts, security sandboxing, and integrity checks."""

    PROHIBITED_MODULES = {
        "smart_buildings.smart_control",
        "smart_control",
        "smart_buildings.evaluate",
        "smart_buildings.weather",
        "smart_buildings.simulator",
        "ctypes",
        "subprocess",
        "multiprocessing",
        "inspect",
        "socket",
        "urllib",
        "requests",
        "http",
    }

    PROHIBITED_ATTRIBUTES = {
        "_getframe",
        "currentframe",
        "f_back",
        "f_locals",
        "f_globals",
        "get_objects",
        "__subclasses__",
    }

    PROHIBITED_CALLS = {
        "eval",
        "exec",
        "__import__",
    }

    SENSITIVE_PATH_PATTERNS = {
        "config.gin",
        ".gin",
        "weather",
        "ground_truth",
        "smart_buildings",
    }

    @classmethod
    def _audit_ast_tree(cls, tree: ast.AST, label: str) -> list[str]:
        """Walks an AST tree and collects all sandbox and leakage violations."""
        violations: list[str] = []
        for node in ast.walk(tree):
            # Check static imports: import x
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.name
                    for p in cls.PROHIBITED_MODULES:
                        if name == p or name.startswith(p + "."):
                            violations.append(
                                f"Prohibited module import: '{name}' in {label} (line {node.lineno})"
                            )

            # Check from-imports: from x import y
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                for p in cls.PROHIBITED_MODULES:
                    if mod == p or mod.startswith(p + "."):
                        violations.append(
                            f"Prohibited module import: '{mod}' in {label} (line {node.lineno})"
                        )
                for alias in node.names:
                    name = alias.name
                    for p in cls.PROHIBITED_MODULES:
                        if name == p or name.startswith(p + "."):
                            violations.append(
                                f"Prohibited module symbol import: '{name}' in {label} (line {node.lineno})"
                            )

            # Check attribute access: obj.attr
            elif isinstance(node, ast.Attribute):
                if node.attr in cls.PROHIBITED_ATTRIBUTES:
                    violations.append(
                        f"Prohibited attribute access: '{node.attr}' in {label} (line {node.lineno})"
                    )

            # Check bare function / symbol names
            elif isinstance(node, ast.Name):
                if node.id in cls.PROHIBITED_ATTRIBUTES:
                    violations.append(
                        f"Prohibited symbol usage: '{node.id}' in {label} (line {node.lineno})"
                    )

            # Check dynamic execution calls and direct ground-truth file reads
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in cls.PROHIBITED_CALLS:
                        violations.append(
                            f"Prohibited dynamic call: '{node.func.id}()' in {label} (line {node.lineno})"
                        )
                    elif node.func.id == "open":
                        for arg in node.args:
                            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                                val = arg.value.lower()
                                if any(p in val for p in cls.SENSITIVE_PATH_PATTERNS):
                                    violations.append(
                                        f"Prohibited direct file access to sensitive path '{arg.value}' in {label} (line {node.lineno})"
                                    )
                elif isinstance(node.func, ast.Attribute):
                    if node.func.attr == "getattr" and len(node.args) >= 2:
                        second_arg = node.args[1]
                        if isinstance(second_arg, ast.Constant) and str(second_arg.value) in cls.PROHIBITED_ATTRIBUTES:
                            violations.append(
                                f"Prohibited getattr access: '{second_arg.value}' in {label} (line {node.lineno})"
                            )
                    elif node.func.attr in {"read_text", "read_bytes", "open"}:
                        for arg in node.args:
                            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                                val = arg.value.lower()
                                if any(p in val for p in cls.SENSITIVE_PATH_PATTERNS):
                                    violations.append(
                                        f"Prohibited direct file access to sensitive path '{arg.value}' in {label} (line {node.lineno})"
                                    )
                        if isinstance(node.func.value, ast.Call):
                            for call_arg in node.func.value.args:
                                if isinstance(call_arg, ast.Constant) and isinstance(call_arg.value, str):
                                    val = call_arg.value.lower()
                                    if any(p in val for p in cls.SENSITIVE_PATH_PATTERNS):
                                        violations.append(
                                            f"Prohibited direct file access to sensitive path '{call_arg.value}' in {label} (line {node.lineno})"
                                        )

        return violations

    @classmethod
    def audit_policy_ast(
        cls,
        policy_source: str | Path | Type[Any],
        local_deps_dir: Path | str | None = None,
    ) -> list[str]:
        """Parses AST and validates against information-leakage and sandbox boundary violations (Ring 2).

        Performs recursive static AST audits across the entrypoint policy and all local dependencies.
        """
        source_code: str
        label = "policy_entrypoint"
        if isinstance(policy_source, str) and not Path(policy_source).is_file():
            source_code = policy_source
        elif isinstance(policy_source, (str, Path)) and Path(policy_source).is_file():
            p = Path(policy_source)
            label = p.name
            source_code = p.read_text(encoding="utf-8")
        elif isinstance(policy_source, type):
            label = policy_source.__name__
            try:
                source_code = inspect.getsource(policy_source)
            except Exception:
                return []
        else:
            return []

        dedented_source = textwrap.dedent(source_code)
        try:
            tree = ast.parse(dedented_source)
        except SyntaxError as e:
            raise SecurityViolationError(f"Policy syntax error during security audit: {e}")

        violations: list[str] = cls._audit_ast_tree(tree, label)

        # Recursive audit of local dependencies in local_deps_dir (excluding simulator/foundation system files)
        if local_deps_dir:
            ld_path = Path(local_deps_dir)
            if ld_path.is_dir():
                for dep_file in sorted(ld_path.rglob("*.py")):
                    try:
                        rel = dep_file.relative_to(ld_path)
                        # Skip underlying simulator and framework/test modules frozen from sys.modules
                        if rel.parts and (rel.parts[0] in {"smart_buildings", "04_EXPERIMENT_FOUNDATION", "05_FAILURE_ENGINEERING"} or any(p in {"tests", "test"} for p in rel.parts)):
                            continue
                        dep_text = dep_file.read_text(encoding="utf-8")
                        dep_tree = ast.parse(textwrap.dedent(dep_text))
                        violations.extend(cls._audit_ast_tree(dep_tree, f"local_dep:{dep_file.name}"))
                    except SyntaxError as e:
                        violations.append(f"Syntax error in local dependency '{dep_file.name}': {e}")

        if violations:
            raise SecurityViolationError(
                f"Security sandbox violation detected in policy:\n - " + "\n - ".join(violations)
            )

        return violations

    def __init__(
        self,
        policy_class: Type[Any],
        action_spec: Mapping[str, Any],
        metadata: Mapping[str, Any],
        policy_params: Mapping[str, Any] | None = None,
        local_deps_dir: Path | str | None = None,
    ):
        # Ring 2: Static AST audit before instantiating policy
        self.audit_policy_ast(policy_class, local_deps_dir=local_deps_dir)

        self.policy_class = policy_class
        self.action_spec = action_spec
        # Ring 3: Metadata immutability via deepcopy
        self.metadata = copy.deepcopy(metadata)
        self.policy_params = policy_params or {}
        self.last_decision: dict[str, Any] = {}

        # Compute cryptographic hash of the policy source
        self.source_hash = self._compute_source_hash(policy_class)

        # Expected shapes from action_spec
        self.discrete_shape = action_spec["discrete_action"].shape
        self.continuous_shape = action_spec["continuous_action"].shape

        # Ring 1: Strict input boundary - Instantiate policy matching official initialize_policy
        try:
            self.policy_instance = policy_class(self.metadata, action_spec, **self.policy_params)
        except TypeError:
            try:
                self.policy_instance = policy_class(self.metadata, action_spec)
            except TypeError:
                try:
                    self.policy_instance = policy_class(self.metadata)
                except TypeError:
                    self.policy_instance = policy_class()

    @staticmethod
    def _compute_source_hash(policy_class: Type[Any]) -> str:
        """Returns SHA-256 hash of the policy source file."""
        try:
            source_file = inspect.getfile(policy_class)
            path = Path(source_file)
            if path.is_file():
                return hashlib.sha256(path.read_bytes()).hexdigest()
        except Exception:
            pass
        # Fallback to module name hash
        return hashlib.sha256(f"{policy_class.__module__}.{policy_class.__name__}".encode()).hexdigest()

    def get_action(self, observation: Any) -> dict[str, np.ndarray]:
        """Queries policy for an action and rigorously validates its format and values."""
        # Enforce read-only observation to prevent in-place memory tampering
        if isinstance(observation, np.ndarray):
            try:
                observation.flags.writeable = False
            except ValueError:
                pass

        t0 = time.perf_counter()
        if hasattr(self.policy_instance, "get_action"):
            raw_action = self.policy_instance.get_action(observation)
        elif hasattr(self.policy_instance, "step"):
            raw_action = self.policy_instance.step(observation)
        elif callable(self.policy_instance):
            raw_action = self.policy_instance(observation)
        else:
            raise TypeError("Policy instance must implement get_action(obs), step(obs), or be callable")
        latency_ms = (time.perf_counter() - t0) * 1000.0

        if not isinstance(raw_action, dict):
            raise TypeError(f"Policy returned {type(raw_action)}, expected dict with 'discrete_action' and 'continuous_action'")

        if "discrete_action" not in raw_action or "continuous_action" not in raw_action:
            raise KeyError("Action dict must contain both 'discrete_action' and 'continuous_action' keys")

        discrete = np.asarray(raw_action["discrete_action"], dtype=np.int32)
        continuous = np.asarray(raw_action["continuous_action"], dtype=np.float32)
        raw_continuous = continuous.copy()
        raw_discrete = discrete.copy()

        # Validate shapes
        if discrete.shape != self.discrete_shape:
            raise ValueError(f"discrete_action shape mismatch: got {discrete.shape}, expected {self.discrete_shape}")
        if continuous.shape != self.continuous_shape:
            raise ValueError(f"continuous_action shape mismatch: got {continuous.shape}, expected {self.continuous_shape}")

        # Validate finiteness
        if not np.all(np.isfinite(discrete)):
            raise ValueError("discrete_action contains non-finite (NaN / Inf) values")
        if not np.all(np.isfinite(continuous)):
            raise ValueError("continuous_action contains non-finite (NaN / Inf) values")

        # Validate continuous range [-1.0, 1.0] with clipping protection
        continuous_clipped = np.clip(continuous, -1.0, 1.0)
        was_clipped = bool(not np.array_equal(raw_continuous, continuous_clipped))
        max_clip_delta = float(np.max(np.abs(raw_continuous - continuous_clipped))) if len(raw_continuous) > 0 else 0.0

        self.last_decision = {
            "raw_continuous_action": raw_continuous,
            "executed_continuous_action": continuous_clipped,
            "raw_discrete_action": raw_discrete,
            "executed_discrete_action": discrete,
            "was_clipped": was_clipped,
            "max_clip_delta": max_clip_delta,
            "latency_ms": latency_ms,
        }

        return {
            "discrete_action": discrete,
            "continuous_action": continuous_clipped,
        }

    @classmethod
    def load_policy_from_artifacts(cls, run_dir: Path | str) -> tuple[Type[Any], Mapping[str, Any]]:
        """Loads and returns the frozen policy class from run_dir/artifacts/ with local dependency isolation."""
        run_dir = Path(run_dir)
        manifest_path = run_dir / "artifact_manifest.json"
        if not manifest_path.is_file():
            raise FileNotFoundError(f"Missing artifact manifest: {manifest_path}")

        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        artifacts = manifest.get("artifacts", [])
        entrypoint_record = next((a for a in artifacts if a.get("role") == "policy_entrypoint"), None)
        if not entrypoint_record:
            raise ValueError("No policy_entrypoint found in artifact_manifest.json")

        entry_rel = entrypoint_record["stored_path"]
        entry_file = run_dir / entry_rel
        if not entry_file.is_file():
            raise FileNotFoundError(f"Missing stored policy entrypoint: {entry_file}")

        # Verify integrity of entrypoint file
        actual_sha = hashlib.sha256(entry_file.read_bytes()).hexdigest()
        if actual_sha != entrypoint_record.get("sha256"):
            raise ValueError(
                f"Artifact checksum mismatch for {entry_file.name}: "
                f"expected {entrypoint_record.get('sha256')}, got {actual_sha}"
            )

        # Ring 2: Audit AST of frozen artifact before importing
        cls.audit_policy_ast(entry_file)

        # Prepend local_deps and artifacts to sys.path for isolated resolution
        artifacts_dir = run_dir / "artifacts"
        local_deps_dir = artifacts_dir / "local_deps"
        if local_deps_dir.is_dir() and str(local_deps_dir) not in sys.path:
            sys.path.insert(0, str(local_deps_dir))
        if str(artifacts_dir) not in sys.path:
            sys.path.insert(0, str(artifacts_dir))

        module_name = f"_frozen_policy_{run_dir.name}_{entry_file.stem}"
        spec = importlib.util.spec_from_file_location(module_name, entry_file)
        if spec is None or spec.loader is None:
            raise ImportError(f"Could not load module spec for {entry_file}")

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)

        class_name = entrypoint_record.get("entrypoint_class")
        if not class_name or not hasattr(module, class_name):
            for attr in dir(module):
                val = getattr(module, attr)
                if isinstance(val, type) and hasattr(val, "step"):
                    class_name = attr
                    break

        if not class_name or not hasattr(module, class_name):
            raise AttributeError(f"Could not find policy class '{class_name}' in {entry_file}")

        loaded_policy_class = getattr(module, class_name)
        return loaded_policy_class, manifest
