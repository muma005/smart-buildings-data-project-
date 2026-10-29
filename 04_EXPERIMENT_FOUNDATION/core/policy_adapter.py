"""Policy Adapter for Smart Buildings Challenge.
Encapsulates policy lifecycle, input/output contract enforcement,
cryptographic hashing, and error isolation.
"""

from __future__ import annotations
import hashlib
import inspect
from pathlib import Path
from typing import Any, Mapping, Type
import numpy as np


class PolicyAdapter:
    """Wraps a building control policy, enforcing runtime contracts and integrity checks."""

    def __init__(
        self,
        policy_class: Type[Any],
        action_spec: Mapping[str, Any],
        metadata: Mapping[str, Any],
        policy_params: Mapping[str, Any] | None = None,
    ):
        self.policy_class = policy_class
        self.action_spec = action_spec
        self.metadata = metadata
        self.policy_params = policy_params or {}

        # Compute cryptographic hash of the policy source
        self.source_hash = self._compute_source_hash(policy_class)

        # Expected shapes from action_spec
        self.discrete_shape = action_spec["discrete_action"].shape
        self.continuous_shape = action_spec["continuous_action"].shape

        # Instantiate policy instance matching official initialize_policy
        try:
            self.policy_instance = policy_class(metadata, action_spec, **self.policy_params)
        except TypeError:
            try:
                self.policy_instance = policy_class(metadata, action_spec)
            except TypeError:
                try:
                    self.policy_instance = policy_class(metadata)
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
        if hasattr(self.policy_instance, "get_action"):
            raw_action = self.policy_instance.get_action(observation)
        elif hasattr(self.policy_instance, "step"):
            raw_action = self.policy_instance.step(observation)
        elif callable(self.policy_instance):
            raw_action = self.policy_instance(observation)
        else:
            raise TypeError("Policy instance must implement get_action(obs), step(obs), or be callable")

        if not isinstance(raw_action, dict):
            raise TypeError(f"Policy returned {type(raw_action)}, expected dict with 'discrete_action' and 'continuous_action'")

        if "discrete_action" not in raw_action or "continuous_action" not in raw_action:
            raise KeyError("Action dict must contain both 'discrete_action' and 'continuous_action' keys")

        discrete = np.asarray(raw_action["discrete_action"], dtype=np.int32)
        continuous = np.asarray(raw_action["continuous_action"], dtype=np.float32)

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

        return {
            "discrete_action": discrete,
            "continuous_action": continuous_clipped,
        }
