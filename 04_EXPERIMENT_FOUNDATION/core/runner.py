"""Simulation Runner for Smart Buildings Challenge.
Executes policy-in-the-loop simulation runs against the hybrid building environment,
streaming transition traces and managing run lifecycle transitions.
"""

from __future__ import annotations
import hashlib
import json
from pathlib import Path
import traceback
from typing import Any, Mapping, Type
import numpy as np

from smart_buildings.evaluate import (
    load_hybrid_environment,
    create_building_meta_data,
)

from .policy_adapter import PolicyAdapter
from .trace_recorder import TraceRecorder
from .registry import ExperimentRegistry, RunStatus


class SimulationRunner:
    """Orchestrates end-to-end policy execution against a simulation scenario."""

    def __init__(self, registry: ExperimentRegistry | None = None):
        self.registry = registry or ExperimentRegistry()

    @staticmethod
    def _hash_file(path: Path) -> str:
        if path.is_file():
            return hashlib.sha256(path.read_bytes()).hexdigest()
        return "UNKNOWN_HASH"

    def execute_episode(
        self,
        experiment_id: str,
        policy_class: Type[Any],
        scenario_dir: Path | str,
        max_steps: int = 8640,
        policy_params: Mapping[str, Any] | None = None,
        custom_run_metadata: Mapping[str, Any] | None = None,
    ) -> tuple[str, Path, dict[str, Any]]:
        """Executes a single policy episode and commits evidence to the registry."""
        scenario_path = Path(scenario_dir)
        gin_path = scenario_path / "config.gin"
        if not gin_path.is_file():
            raise FileNotFoundError(f"Missing scenario config: {gin_path}")

        scenario_id = f"{scenario_path.parent.name}/{scenario_path.name}"
        config_hash = self._hash_file(gin_path)
        policy_hash = PolicyAdapter._compute_source_hash(policy_class)

        run_id, run_dir = self.registry.create_run(
            experiment_id=experiment_id,
            policy_name=policy_class.__name__,
            scenario_id=scenario_id,
            config_hash=config_hash,
            policy_hash=policy_hash,
            expected_steps=max_steps,
            metadata=custom_run_metadata,
        )

        try:
            self.registry.update_status(run_dir, RunStatus.RUNNING)

            # Load environment
            env = load_hybrid_environment(gin_path)
            env.metrics_path = None  # We record traces independently
            metadata = create_building_meta_data(env, scenario_path)
            action_spec = env.action_spec()

            adapter = PolicyAdapter(
                policy_class=policy_class,
                action_spec=action_spec,
                metadata=metadata,
                policy_params=policy_params,
            )

            # Start trace recording
            with TraceRecorder(run_dir, prefix="trace") as recorder:
                reset_res = env.reset()
                obs = reset_res[0] if isinstance(reset_res, tuple) else reset_res
                step_idx = 0
                terminated = False
                truncated = False

                zone_indices = metadata.get("zone_temp_indices", [])

                while not (terminated or truncated) and step_idx < max_steps:
                    action = adapter.get_action(obs)
                    step_res = env.step(action)
                    if isinstance(step_res, tuple) and len(step_res) == 5:
                        obs, reward, terminated, truncated, info = step_res
                    elif isinstance(step_res, tuple) and len(step_res) == 4:
                        obs, reward, terminated, info = step_res
                        truncated = False
                    else:
                        obs = step_res
                        reward = 0.0
                        terminated = False
                        truncated = False

                    reward_val = float(reward) if reward is not None else 0.0

                    # Extract physical states safely
                    if len(zone_indices) > 0 and isinstance(obs, np.ndarray) and len(obs) > max(zone_indices):
                        mean_temp = float(np.mean(obs[zone_indices]))
                    else:
                        mean_temp = 22.0

                    outdoor_temp = 15.0
                    occupants = 10.0

                    # Extract reward breakdown if available on env
                    prod_regret = getattr(env, "_productivity_regret", 0.0)
                    energy_cost = getattr(env, "_energy_cost", 0.0)
                    carbon_penalty = getattr(env, "_carbon_penalty", 0.0)

                    recorder.record_step(
                        step_idx=step_idx,
                        reward=reward_val,
                        productivity_regret=prod_regret,
                        energy_cost=energy_cost,
                        carbon_penalty=carbon_penalty,
                        mean_zone_temp=mean_temp,
                        outdoor_temp=outdoor_temp,
                        total_occupants=occupants,
                        discrete_action=action["discrete_action"],
                        continuous_action=action["continuous_action"],
                    )
                    step_idx += 1

                trace_meta = recorder.close()

            # Save summary.json
            summary = {
                "run_id": run_id,
                "scenario_id": scenario_id,
                "policy": policy_class.__name__,
                "steps_completed": step_idx,
                "cumulative_reward": trace_meta["cumulative_reward"],
                "trace_sha256": trace_meta["sha256"],
            }
            summary_path = run_dir / "summary.json"
            with open(summary_path, "w", encoding="utf-8") as f:
                json.dump(summary, f, indent=2)

            # Determine final status
            if step_idx < max_steps:
                manifest = self.registry.update_status(
                    run_dir=run_dir,
                    new_status=RunStatus.INCOMPLETE,
                    actual_steps=step_idx,
                    trace_hash=trace_meta["sha256"],
                    error_message=f"Episode stopped prematurely at {step_idx}/{max_steps} steps",
                    artifacts_update={
                        "trace_path": trace_meta["trace_path"],
                        "summary_path": str(summary_path),
                    },
                )
            else:
                manifest = self.registry.update_status(
                    run_dir=run_dir,
                    new_status=RunStatus.COMPLETE,
                    actual_steps=step_idx,
                    trace_hash=trace_meta["sha256"],
                    artifacts_update={
                        "trace_path": trace_meta["trace_path"],
                        "summary_path": str(summary_path),
                    },
                )

            return run_id, run_dir, manifest

        except Exception as e:
            err_msg = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
            manifest = self.registry.update_status(
                run_dir=run_dir,
                new_status=RunStatus.FAILED,
                error_message=err_msg,
            )
            raise e
