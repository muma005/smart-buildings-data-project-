"""Simulation Runner for Smart Buildings Challenge.
Executes policy-in-the-loop simulation runs against the hybrid building environment,
streaming transition traces and managing run lifecycle transitions.
"""

from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import importlib
import inspect
import json
import os
from pathlib import Path
import shutil
import sys
import traceback
from typing import Any, Mapping, Type
import numpy as np

from smart_buildings.evaluate import (
    load_hybrid_environment,
    create_building_meta_data,
)

from .policy_adapter import PolicyAdapter
from .trace_recorder import TraceRecorder, EvidenceCaptureError
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

    def _preserve_artifacts(
        self,
        run_dir: Path,
        policy_class: Type[Any],
        gin_path: Path,
        policy_params: Mapping[str, Any] | None = None,
    ) -> tuple[Path, str]:
        """Constructs run_dir/artifacts/ vault, freezes policy source and local dependencies,

        and generates artifact_manifest.json with cryptographic hashes.
        """
        artifacts_dir = run_dir / "artifacts"
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        local_deps_dir = artifacts_dir / "local_deps"
        local_deps_dir.mkdir(parents=True, exist_ok=True)

        artifact_records: list[dict[str, Any]] = []

        # 1. Freeze Scenario Config
        config_dest = artifacts_dir / "config.gin"
        shutil.copy2(gin_path, config_dest)
        config_sha = self._hash_file(config_dest)
        artifact_records.append({
            "role": "scenario_config",
            "source_path": str(gin_path),
            "stored_path": "artifacts/config.gin",
            "sha256": config_sha,
        })

        # 2. Freeze Policy Entrypoint Source
        try:
            policy_src = inspect.getsourcefile(policy_class)
        except Exception:
            policy_src = None

        if policy_src and Path(policy_src).is_file():
            policy_src_path = Path(policy_src).resolve()
            policy_dest = artifacts_dir / policy_src_path.name
            shutil.copy2(policy_src_path, policy_dest)
            policy_sha = self._hash_file(policy_dest)
            artifact_records.append({
                "role": "policy_entrypoint",
                "entrypoint_class": policy_class.__name__,
                "source_path": str(policy_src_path),
                "stored_path": f"artifacts/{policy_src_path.name}",
                "sha256": policy_sha,
            })
        else:
            policy_dest = artifacts_dir / f"{policy_class.__name__}.py"
            try:
                src_code = inspect.getsource(policy_class)
                policy_dest.write_text(src_code, encoding="utf-8")
                policy_sha = self._hash_file(policy_dest)
                artifact_records.append({
                    "role": "policy_entrypoint",
                    "entrypoint_class": policy_class.__name__,
                    "source_path": f"<dynamic:{policy_class.__name__}>",
                    "stored_path": f"artifacts/{policy_dest.name}",
                    "sha256": policy_sha,
                })
            except Exception:
                pass

        # 3. Freeze Local Dependencies from sys.modules
        project_root = Path(__file__).resolve().parents[2]
        for name, mod in list(sys.modules.items()):
            if mod is None:
                continue
            f = getattr(mod, "__file__", None)
            if not f or not f.endswith(".py"):
                continue
            mod_path = Path(f).resolve()
            try:
                rel = mod_path.relative_to(project_root)
            except ValueError:
                continue

            rel_str = str(rel).replace("\\", "/")
            if any(rel_str.startswith(skip) for skip in [".venv", ".git", "experiments", "05_FAILURE_ENGINEERING/evidence"]):
                continue

            dep_dest = local_deps_dir / rel
            dep_dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(mod_path, dep_dest)
            dep_sha = self._hash_file(dep_dest)
            artifact_records.append({
                "role": "local_dependency",
                "module_name": name,
                "source_path": str(mod_path),
                "stored_path": f"artifacts/local_deps/{rel_str}",
                "sha256": dep_sha,
            })

        # 4. Freeze Model Weights if specified
        if policy_params:
            for k in ["weights_path", "model_path", "checkpoint_path"]:
                val = policy_params.get(k)
                if val and Path(val).is_file():
                    w_path = Path(val).resolve()
                    w_dest = artifacts_dir / w_path.name
                    shutil.copy2(w_path, w_dest)
                    w_sha = self._hash_file(w_dest)
                    artifact_records.append({
                        "role": "model_weights",
                        "source_path": str(w_path),
                        "stored_path": f"artifacts/{w_path.name}",
                        "sha256": w_sha,
                    })

        # 5. Capture Runtime Package Versions
        runtime_packages = {}
        for pkg_name in ["numpy", "pandas", "scipy", "gymnasium", "gin"]:
            try:
                mod = importlib.import_module(pkg_name)
                runtime_packages[pkg_name] = getattr(mod, "__version__", "unknown")
            except Exception:
                pass

        # 6. Write artifact_manifest.json with fsync
        artifact_manifest_data = {
            "project_git_commit": self.registry.get_project_git_commit(),
            "starter_kit_commit": self.registry.get_starter_kit_commit(),
            "python_version": sys.version.split()[0],
            "platform": sys.platform,
            "runtime_packages": runtime_packages,
            "artifacts": artifact_records,
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
        }

        artifact_manifest_file = run_dir / "artifact_manifest.json"
        tmp_manifest = artifact_manifest_file.with_suffix(".json.tmp")
        with open(tmp_manifest, "w", encoding="utf-8") as f:
            json.dump(artifact_manifest_data, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        tmp_manifest.replace(artifact_manifest_file)
        manifest_sha = self._hash_file(artifact_manifest_file)

        return artifact_manifest_file, manifest_sha

    def execute_episode(
        self,
        experiment_id: str,
        policy_class: Type[Any],
        scenario_dir: Path | str,
        max_steps: int = 8640,
        chunk_size: int = 288,
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

            # Preserve artifacts vault before simulation start
            artifact_manifest_file, artifact_manifest_sha = self._preserve_artifacts(
                run_dir=run_dir,
                policy_class=policy_class,
                gin_path=gin_path,
                policy_params=policy_params,
            )

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
            with TraceRecorder(run_dir, prefix="trace", chunk_size=chunk_size) as recorder:
                reset_res = env.reset()
                obs = reset_res[0] if isinstance(reset_res, tuple) else reset_res
                step_idx = 0
                terminated = False
                truncated = False

                zone_indices = metadata.get("zone_temp_indices", [])

                while not (terminated or truncated) and step_idx < max_steps:
                    step_obs = obs
                    action = adapter.get_action(step_obs)
                    step_res = env.step(action)
                    if isinstance(step_res, tuple) and len(step_res) == 5:
                        next_obs, reward, terminated, truncated, info = step_res
                    elif isinstance(step_res, tuple) and len(step_res) == 4:
                        next_obs, reward, terminated, info = step_res
                        truncated = False
                    else:
                        next_obs = step_res
                        reward = 0.0
                        terminated = False
                        truncated = False

                    reward_val = float(reward) if reward is not None else 0.0

                    # Extract physical states safely
                    if len(zone_indices) > 0 and isinstance(next_obs, np.ndarray) and len(next_obs) > max(zone_indices):
                        mean_temp = float(np.mean(next_obs[zone_indices]))
                        zone_temps = next_obs[zone_indices]
                    else:
                        mean_temp = 22.0
                        zone_temps = np.array([])

                    outdoor_temp = 15.0
                    occupants = 10.0

                    # Extract reward breakdown using official get_reward_info_and_response()
                    if hasattr(env, "get_reward_info_and_response"):
                        reward_tuple = env.get_reward_info_and_response()
                        if reward_tuple is None or len(reward_tuple) != 2 or reward_tuple[1] is None:
                            raise EvidenceCaptureError(
                                f"Environment failed to return RewardResponse at step {step_idx}. "
                                "Aborting run to prevent silent zero substitution."
                            )
                        reward_info, reward_response = reward_tuple
                        prod_regret = float(reward_response.normalized_productivity_regret)
                        energy_cost = float(reward_response.normalized_energy_cost)
                        carbon_penalty = float(reward_response.normalized_carbon_emission)
                        occupants = float(reward_response.total_occupancy)
                        agent_reward = float(reward_response.agent_reward_value)

                        # Step 0 reward arithmetic consistency check against official equation
                        if step_idx == 0:
                            pw = float(getattr(reward_response, "productivity_weight", 0.6))
                            ew = float(getattr(reward_response, "energy_cost_weight", 0.2))
                            cw = float(getattr(reward_response, "carbon_emission_weight", 0.2))
                            reconstructed = pw * prod_regret - ew * energy_cost - cw * carbon_penalty
                            if abs(agent_reward - reconstructed) > 1e-6:
                                raise EvidenceCaptureError(
                                    f"Step 0 reward arithmetic divergence: agent_reward={agent_reward}, "
                                    f"reconstructed={reconstructed}, diff={abs(agent_reward - reconstructed):.8e}"
                                )
                    else:
                        raise EvidenceCaptureError(
                            "Environment does not implement get_reward_info_and_response(). "
                            "Cannot capture verified physical reward components."
                        )

                    # Extract decision metadata from adapter
                    was_clipped = adapter.last_decision.get("was_clipped", False)
                    latency_ms = adapter.last_decision.get("latency_ms", 0.0)
                    raw_cont = adapter.last_decision.get("raw_continuous_action")

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
                        raw_continuous_action=raw_cont,
                        observation=step_obs,
                        zone_temperatures=zone_temps,
                        was_clipped=was_clipped,
                        latency_ms=latency_ms,
                    )
                    obs = next_obs
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
                "chunks_committed": trace_meta.get("total_chunks", 0),
                "chunks_manifest_sha256": trace_meta.get("chunks_manifest_sha256", ""),
                "artifact_manifest_sha256": artifact_manifest_sha,
            }
            summary_path = run_dir / "summary.json"
            with open(summary_path, "w", encoding="utf-8") as f:
                json.dump(summary, f, indent=2)

            # Determine final status
            artifacts_data = {
                "trace_path": trace_meta["trace_path"],
                "summary_path": str(summary_path),
                "chunks_dir": trace_meta.get("chunks_dir", ""),
                "chunks_manifest_path": trace_meta.get("chunks_manifest_path", ""),
                "artifacts_vault_dir": str(run_dir / "artifacts"),
                "artifact_manifest_path": str(artifact_manifest_file),
            }
            if step_idx < max_steps:
                manifest = self.registry.update_status(
                    run_dir=run_dir,
                    new_status=RunStatus.INCOMPLETE,
                    actual_steps=step_idx,
                    trace_hash=trace_meta["sha256"],
                    chunks_manifest_hash=trace_meta.get("chunks_manifest_sha256"),
                    artifact_manifest_hash=artifact_manifest_sha,
                    error_message=f"Episode stopped prematurely at {step_idx}/{max_steps} steps",
                    artifacts_update=artifacts_data,
                )
            else:
                manifest = self.registry.update_status(
                    run_dir=run_dir,
                    new_status=RunStatus.COMPLETE,
                    actual_steps=step_idx,
                    trace_hash=trace_meta["sha256"],
                    chunks_manifest_hash=trace_meta.get("chunks_manifest_sha256"),
                    artifact_manifest_hash=artifact_manifest_sha,
                    artifacts_update=artifacts_data,
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
