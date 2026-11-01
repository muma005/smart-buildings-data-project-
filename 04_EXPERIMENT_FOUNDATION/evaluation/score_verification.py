"""Score Verification and Independent Auditor for Smart Buildings Challenge.
Reconstructs the competition metric and reward calculations from recorded episode data
without delegating to the official scoring function, certifying parity within 1e-6.
"""

from __future__ import annotations
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence
import pandas as pd
import numpy as np


class ScoreVerifier:
    """Independent auditor for verifying episode returns and leaderboard scores."""

    DEFAULT_W_PROD = 0.6
    DEFAULT_W_ENERGY = 0.2
    DEFAULT_W_CARBON = 0.2
    COMFORT_WINDOW_K = 5.0
    PARITY_TOLERANCE = 1.0e-6

    @classmethod
    def compute_comfort_shortfall(cls, deviation_k: float, w: float = 5.0) -> float:
        """Piecewise linear/quadratic shortfall f(d)."""
        d = max(0.0, float(deviation_k))
        if d <= w:
            return d / w
        return 1.0 + ((d - w) / w) ** 2

    @classmethod
    def compute_productivity_regret(
        cls, zone_deviations: Sequence[float], zone_occupants: Sequence[float]
    ) -> float:
        """Productivity regret in [-1.0, 0.0] normalized by total active occupants."""
        total_occ = sum(zone_occupants)
        if total_occ == 0.0:
            return 0.0

        total_regret = sum(
            occ * cls.compute_comfort_shortfall(dev, cls.COMFORT_WINDOW_K)
            for dev, occ in zip(zone_deviations, zone_occupants)
        )
        return -min(1.0, total_regret / total_occ)

    @classmethod
    def compute_step_reward(
        cls,
        productivity_regret: float,
        energy_cost: float,
        carbon_emission: float,
        w_p: float = DEFAULT_W_PROD,
        w_e: float = DEFAULT_W_ENERGY,
        w_c: float = DEFAULT_W_CARBON,
    ) -> float:
        """Independent reconstruction of per-step agent reward.
        
        Official starter kit formula:
        agent_reward = w_p * regret - w_e * energy_cost - w_c * carbon_emission
        where regret <= 0, and energy_cost and carbon_emission are non-negative penalties.
        """
        return float(w_p * productivity_regret - w_e * energy_cost - w_c * carbon_emission)

    @classmethod
    def verify_reward_arithmetic(
        cls,
        step_records: Sequence[Mapping[str, float]],
        w_p: float = DEFAULT_W_PROD,
        w_e: float = DEFAULT_W_ENERGY,
        w_c: float = DEFAULT_W_CARBON,
    ) -> dict[str, Any]:
        """Validates step-reward arithmetic against individual component costs (Defect 19)."""
        for idx, rec in enumerate(step_records):
            regret = rec.get("normalized_productivity_regret", rec.get("productivity_regret", 0.0))
            energy = rec.get("normalized_energy_cost", rec.get("energy_cost", 0.0))
            carbon = rec.get("normalized_carbon_emission", rec.get("carbon_emission", rec.get("carbon_penalty", 0.0)))

            expected = cls.compute_step_reward(regret, energy, carbon, w_p=w_p, w_e=w_e, w_c=w_c)
            actual = rec.get("agent_reward", rec.get("reward"))

            if actual is None:
                return {
                    "valid": False,
                    "error": f"Missing reward value in record at step {idx}",
                }

            discrepancy = abs(float(actual) - expected)
            if discrepancy > cls.PARITY_TOLERANCE:
                return {
                    "valid": False,
                    "error": (
                        f"Step-reward arithmetic mismatch at step {idx}: expected {expected:.6f}, "
                        f"got {float(actual):.6f} (discrepancy {discrepancy:.2e} > tolerance {cls.PARITY_TOLERANCE:.2e})"
                    ),
                    "step": idx,
                    "discrepancy": discrepancy,
                }

        return {"valid": True, "error": None}

    @classmethod
    def verify_episode_aggregation(
        cls,
        step_rewards: Sequence[float],
        reported_return: float,
    ) -> dict[str, Any]:
        """Verifies that an episode return is the exact sum of step rewards (Defect 20)."""
        reconstructed = float(sum(step_rewards))
        discrepancy = abs(reconstructed - float(reported_return))
        passed = discrepancy <= cls.PARITY_TOLERANCE
        return {
            "valid": passed,
            "reconstructed_return": reconstructed,
            "reported_return": reported_return,
            "discrepancy": discrepancy,
            "error": None if passed else (
                f"Episode aggregation mismatch: reconstructed return ({reconstructed:.6f}) "
                f"differs from reported return ({float(reported_return):.6f}) by {discrepancy:.2e}"
            ),
        }

    @classmethod
    def verify_multi_scenario_score(
        cls,
        scenario_returns: Mapping[str, float],
        reported_suite_return: float | None = None,
    ) -> dict[str, Any]:
        """Verifies multi-scenario score aggregation under official rules (equal weight sum) (Defect 21)."""
        if not scenario_returns:
            return {
                "valid": False,
                "error": "No scenario returns provided for multi-scenario aggregation",
                "total_suite_return": 0.0,
            }

        total_return = float(sum(scenario_returns.values()))
        discrepancy = 0.0
        passed = True

        if reported_suite_return is not None:
            discrepancy = abs(total_return - float(reported_suite_return))
            passed = discrepancy <= cls.PARITY_TOLERANCE

        return {
            "valid": passed,
            "scenario_count": len(scenario_returns),
            "total_suite_return": total_return,
            "discrepancy": discrepancy,
            "error": None if passed else (
                f"Multi-scenario aggregation mismatch: reconstructed sum ({total_return:.6f}) "
                f"differs from reported suite return ({float(reported_suite_return):.6f}) by {discrepancy:.2e}"
            ),
        }

    @classmethod
    def verify_trace_and_score(
        cls,
        trace_path: Path | str,
        expected_steps: int = 8640,
        expected_return: float | None = None,
    ) -> dict[str, Any]:
        """Loads trace, performs structural checks, and calculates independent score."""
        path = Path(trace_path)
        if not path.is_file():
            return {
                "valid": False,
                "error": f"Trace file does not exist: {path}",
                "reconstructed_return": None,
            }

        try:
            df = pd.read_csv(path)
        except Exception as e:
            return {
                "valid": False,
                "error": f"Corrupted trace data: failed to parse CSV: {str(e)}",
                "reconstructed_return": None,
            }

        if "step" not in df.columns or "reward" not in df.columns:
            return {
                "valid": False,
                "error": "Corrupted trace data: missing required columns ('step', 'reward')",
                "reconstructed_return": None,
            }

        actual_steps = len(df)
        if actual_steps != expected_steps:
            return {
                "valid": False,
                "error": f"Step count mismatch: got {actual_steps}, expected {expected_steps}",
                "reconstructed_return": None,
                "actual_steps": actual_steps,
            }

        # Monotonicity check
        try:
            step_indices = pd.to_numeric(df["step"], errors="raise").values
        except Exception as e:
            return {
                "valid": False,
                "error": f"Corrupted trace data: non-integer step indices: {str(e)}",
                "reconstructed_return": None,
            }

        if not (step_indices == np.arange(actual_steps)).all():
            return {
                "valid": False,
                "error": "Step indices are non-monotonic or contain gaps/duplicates",
                "reconstructed_return": None,
            }

        # Non-numeric or non-finite reward check
        try:
            reward_vals = pd.to_numeric(df["reward"], errors="raise").values
        except Exception as e:
            return {
                "valid": False,
                "error": f"Corrupted trace data: non-numeric reward values: {str(e)}",
                "reconstructed_return": None,
            }

        if not np.all(np.isfinite(reward_vals)):
            return {
                "valid": False,
                "error": "Trace contains non-finite (NaN / Inf) rewards",
                "reconstructed_return": None,
            }

        reconstructed_return = float(np.sum(reward_vals))

        parity_passed = True
        discrepancy = 0.0
        if expected_return is not None:
            discrepancy = abs(reconstructed_return - expected_return)
            parity_passed = discrepancy <= cls.PARITY_TOLERANCE

        return {
            "valid": parity_passed,
            "actual_steps": actual_steps,
            "reconstructed_return": reconstructed_return,
            "discrepancy": discrepancy,
            "parity_passed": parity_passed,
            "error": None if parity_passed else (
                f"Discrepancy {discrepancy:.2e} exceeds tolerance {cls.PARITY_TOLERANCE:.2e}"
            ),
        }

    @classmethod
    def verify_run_integrity(
        cls,
        run_dir: Path | str,
        expected_steps: int | None = None,
        expected_dims: Mapping[str, int] | None = None,
        enforce_complete: bool = True,
        save_evaluation: bool = False,
    ) -> dict[str, Any]:
        """Performs rigorous independent post-run audit of evidence completeness,

        provenance, chunk continuity, multi-dimensional tensor validity, and score arithmetic parity.
        """
        run_dir = Path(run_dir)
        errors: list[str] = []
        checks: dict[str, bool] = {
            "manifest_exists": False,
            "manifest_valid": False,
            "summary_exists": False,
            "trace_exists": False,
            "trace_hash_valid": False,
            "chunks_manifest_exists": False,
            "chunks_manifest_hash_valid": False,
            "chunks_dir_exists": False,
            "chunk_continuity_valid": False,
            "chunk_hashes_valid": False,
            "tensor_shapes_valid": False,
            "finite_values_valid": False,
            "reward_arithmetic_valid": False,
            "return_parity_valid": False,
            "step_count_parity_valid": False,
            "artifact_manifest_exists": False,
            "artifact_manifest_hash_valid": False,
            "artifacts_vault_valid": False,
        }
        details: dict[str, Any] = {
            "run_dir": str(run_dir),
            "errors": errors,
        }

        # 1. Run Manifest Audit
        manifest_path = run_dir / "run_manifest.json"
        manifest_data: dict[str, Any] = {}
        if not manifest_path.is_file():
            errors.append(f"Missing run manifest: {manifest_path}")
        else:
            checks["manifest_exists"] = True
            try:
                with open(manifest_path, "r", encoding="utf-8") as f:
                    manifest_data = json.load(f)
                checks["manifest_valid"] = True
            except Exception as e:
                errors.append(f"Corrupted run manifest: {e}")

        run_id = manifest_data.get("run_id", "UNKNOWN")
        status = manifest_data.get("status", "UNKNOWN")
        exp_steps = expected_steps or manifest_data.get("expected_steps", 8640)
        manifest_actual_steps = manifest_data.get("actual_steps")
        manifest_hashes = manifest_data.get("hashes", {})
        details["run_id"] = run_id
        details["status"] = status
        details["expected_steps"] = exp_steps

        if enforce_complete and status != "COMPLETE":
            errors.append(f"Run status is '{status}', expected 'COMPLETE'")

        # 2. Summary Audit
        summary_path = run_dir / "summary.json"
        summary_data: dict[str, Any] = {}
        reported_return = None
        summary_steps = None
        if not summary_path.is_file():
            errors.append(f"Missing summary file: {summary_path}")
        else:
            checks["summary_exists"] = True
            try:
                with open(summary_path, "r", encoding="utf-8") as f:
                    summary_data = json.load(f)
                reported_return = summary_data.get("cumulative_reward")
                summary_steps = summary_data.get("steps_completed")
                details["reported_return"] = reported_return
                details["summary_steps"] = summary_steps
            except Exception as e:
                errors.append(f"Corrupted summary.json: {e}")

        # 3. Trace CSV Audit
        trace_path = run_dir / "trace.csv"
        trace_steps = None
        reconstructed_return = None
        if not trace_path.is_file():
            errors.append(f"Missing trace CSV: {trace_path}")
        else:
            checks["trace_exists"] = True
            # Check SHA-256
            actual_trace_sha = hashlib.sha256(trace_path.read_bytes()).hexdigest()
            expected_trace_sha = manifest_hashes.get("trace_sha256")
            if expected_trace_sha:
                if actual_trace_sha != expected_trace_sha:
                    errors.append(
                        f"trace.csv SHA-256 mismatch: disk={actual_trace_sha}, manifest={expected_trace_sha}"
                    )
                else:
                    checks["trace_hash_valid"] = True
            else:
                checks["trace_hash_valid"] = True

            # Parse and audit rows
            try:
                df = pd.read_csv(trace_path)
                trace_steps = len(df)
                details["trace_steps"] = trace_steps

                req_cols = ["step", "reward", "productivity_regret", "energy_cost", "carbon_penalty"]
                missing_cols = [c for c in req_cols if c not in df.columns]
                if missing_cols:
                    errors.append(f"trace.csv missing required columns: {missing_cols}")
                else:
                    # Step sequence monotonicity
                    steps_arr = pd.to_numeric(df["step"], errors="coerce").values
                    if np.any(np.isnan(steps_arr)) or not np.array_equal(steps_arr, np.arange(trace_steps)):
                        errors.append("trace.csv step sequence contains gaps, duplicates, or non-integers")

                    # Reward values finite
                    rewards_arr = pd.to_numeric(df["reward"], errors="coerce").values
                    if not np.all(np.isfinite(rewards_arr)):
                        errors.append("trace.csv contains non-finite (NaN/Inf) reward values")
                    else:
                        reconstructed_return = float(np.sum(rewards_arr))
                        details["reconstructed_return"] = reconstructed_return

                        # Arithmetic audit: R = 0.6*regret - 0.2*energy - 0.2*carbon
                        regret_arr = pd.to_numeric(df["productivity_regret"], errors="coerce").values
                        energy_arr = pd.to_numeric(df["energy_cost"], errors="coerce").values
                        carbon_arr = pd.to_numeric(df["carbon_penalty"], errors="coerce").values

                        w_p = cls.DEFAULT_W_PROD
                        w_e = cls.DEFAULT_W_ENERGY
                        w_c = cls.DEFAULT_W_CARBON
                        expected_rewards = w_p * regret_arr - w_e * energy_arr - w_c * carbon_arr
                        discrepancies = np.abs(rewards_arr - expected_rewards)
                        max_disc = float(np.max(discrepancies)) if len(discrepancies) > 0 else 0.0
                        details["max_reward_discrepancy"] = max_disc
                        if max_disc > cls.PARITY_TOLERANCE:
                            errors.append(
                                f"trace.csv step reward arithmetic discrepancy {max_disc:.2e} exceeds tolerance {cls.PARITY_TOLERANCE:.2e}"
                            )
                        else:
                            checks["reward_arithmetic_valid"] = True

                        # Return parity check
                        if reported_return is not None:
                            ret_disc = abs(reconstructed_return - float(reported_return))
                            details["return_discrepancy"] = ret_disc
                            if ret_disc > cls.PARITY_TOLERANCE:
                                errors.append(
                                    f"Return parity mismatch: trace sum ({reconstructed_return:.6f}) differs from summary ({float(reported_return):.6f}) by {ret_disc:.2e}"
                                )
                            else:
                                checks["return_parity_valid"] = True
            except Exception as e:
                errors.append(f"Failed to audit trace.csv: {e}")

        # 4. Chunks Manifest & Binary Chunk Files Audit
        chunks_manifest_path = run_dir / "chunks_manifest.json"
        chunks_manifest_data: dict[str, Any] = {}
        total_chunk_steps = 0
        if not chunks_manifest_path.is_file():
            errors.append(f"Missing chunks manifest: {chunks_manifest_path}")
        else:
            checks["chunks_manifest_exists"] = True
            actual_chunks_manifest_sha = hashlib.sha256(chunks_manifest_path.read_bytes()).hexdigest()
            expected_chunks_manifest_sha = manifest_hashes.get("chunks_manifest_sha256")
            if expected_chunks_manifest_sha:
                if actual_chunks_manifest_sha != expected_chunks_manifest_sha:
                    errors.append(
                        f"chunks_manifest.json SHA-256 mismatch: disk={actual_chunks_manifest_sha}, manifest={expected_chunks_manifest_sha}"
                    )
                else:
                    checks["chunks_manifest_hash_valid"] = True
            else:
                checks["chunks_manifest_hash_valid"] = True

            try:
                with open(chunks_manifest_path, "r", encoding="utf-8") as f:
                    chunks_manifest_data = json.load(f)
            except Exception as e:
                errors.append(f"Corrupted chunks_manifest.json: {e}")

        chunks_dir = run_dir / "chunks"
        chunk_records = chunks_manifest_data.get("chunks", [])
        details["total_chunks"] = len(chunk_records)

        if not chunks_dir.is_dir():
            errors.append(f"Missing chunks directory: {chunks_dir}")
        else:
            checks["chunks_dir_exists"] = True

        if checks["chunks_manifest_exists"] and checks["chunks_dir_exists"]:
            continuity_errors = []
            hash_errors = []
            expected_step = 0

            for i, chunk_info in enumerate(chunk_records):
                idx = chunk_info.get("chunk_index")
                start_s = chunk_info.get("start_step")
                end_s = chunk_info.get("end_step")
                num_s = chunk_info.get("num_steps", 0)
                sha = chunk_info.get("sha256")
                fname = chunk_info.get("file_name", f"chunk_{i:04d}.npz")

                if idx != i:
                    continuity_errors.append(f"Chunk record {i} has unexpected chunk_index {idx}")
                if start_s != expected_step:
                    continuity_errors.append(
                        f"Chunk {i} step discontinuity: expected start_step {expected_step}, got {start_s}"
                    )
                if end_s != start_s + num_s - 1:
                    continuity_errors.append(
                        f"Chunk {i} step count inconsistency: {start_s}..{end_s} is not {num_s} steps"
                    )
                expected_step = end_s + 1
                total_chunk_steps += num_s

                # Check file existence and SHA-256
                c_path = chunks_dir / fname
                if not c_path.is_file():
                    hash_errors.append(f"Missing chunk file on disk: {fname}")
                else:
                    actual_sha = hashlib.sha256(c_path.read_bytes()).hexdigest()
                    if actual_sha != sha:
                        hash_errors.append(
                            f"Chunk {i} ({fname}) SHA-256 mismatch: disk={actual_sha}, manifest={sha}"
                        )

            if continuity_errors:
                errors.extend(continuity_errors)
            else:
                checks["chunk_continuity_valid"] = True

            if hash_errors:
                errors.extend(hash_errors)
            else:
                checks["chunk_hashes_valid"] = True

            details["total_chunk_steps"] = total_chunk_steps

            # 5. Multi-Dimensional Tensor Integrity & Finite Value Audit
            if checks["chunk_hashes_valid"] and len(chunk_records) > 0:
                tensor_errors = []
                finite_errors = []
                observed_dims: dict[str, int] = {}
                tensor_keys = [
                    "step_indices",
                    "observations",
                    "raw_continuous_actions",
                    "executed_continuous_actions",
                    "discrete_actions",
                    "zone_temperatures",
                ]

                for i, chunk_info in enumerate(chunk_records):
                    c_path = chunks_dir / chunk_info["file_name"]
                    try:
                        with np.load(c_path) as data:
                            for key in tensor_keys:
                                if key not in data:
                                    tensor_errors.append(f"Chunk {i} missing tensor key '{key}'")
                                    continue
                                arr = data[key]
                                if not np.all(np.isfinite(arr)):
                                    finite_errors.append(f"Chunk {i} tensor '{key}' contains non-finite (NaN/Inf) values")
                                if arr.ndim > 1:
                                    dim = arr.shape[1]
                                    if key not in observed_dims:
                                        observed_dims[key] = dim
                                    elif observed_dims[key] != dim:
                                        tensor_errors.append(
                                            f"Chunk {i} tensor '{key}' dimension changed from {observed_dims[key]} to {dim}"
                                        )
                    except Exception as e:
                        tensor_errors.append(f"Failed to read chunk {i} ({chunk_info['file_name']}): {e}")

                details["tensor_dimensions"] = observed_dims

                if expected_dims:
                    for k, expected_dim in expected_dims.items():
                        if k in observed_dims and observed_dims[k] != expected_dim:
                            tensor_errors.append(
                                f"Dimension mismatch for '{k}': expected {expected_dim}, got {observed_dims[k]}"
                            )

                if tensor_errors:
                    errors.extend(tensor_errors)
                else:
                    checks["tensor_shapes_valid"] = True

                if finite_errors:
                    errors.extend(finite_errors)
                else:
                    checks["finite_values_valid"] = True

        # 6. Cross-Artifact Step Count Parity Audit
        if trace_steps is not None and total_chunk_steps > 0:
            if trace_steps != total_chunk_steps:
                errors.append(
                    f"Step count mismatch between trace.csv ({trace_steps}) and chunks ({total_chunk_steps})"
                )
            elif summary_steps is not None and summary_steps != trace_steps:
                errors.append(
                    f"Step count mismatch between trace.csv ({trace_steps}) and summary.json ({summary_steps})"
                )
            elif manifest_actual_steps is not None and manifest_actual_steps != trace_steps:
                errors.append(
                    f"Step count mismatch between trace.csv ({trace_steps}) and run_manifest.json ({manifest_actual_steps})"
                )
            elif enforce_complete and trace_steps != exp_steps:
                errors.append(
                    f"Episode step count incomplete: got {trace_steps}, expected {exp_steps}"
                )
            else:
                checks["step_count_parity_valid"] = True

        # 7. Artifact Vault & Commit Provenance Audit
        artifact_manifest_path = run_dir / "artifact_manifest.json"
        if artifact_manifest_path.is_file():
            checks["artifact_manifest_exists"] = True
            actual_artifact_sha = hashlib.sha256(artifact_manifest_path.read_bytes()).hexdigest()
            expected_artifact_sha = manifest_hashes.get("artifact_manifest_sha256")
            if expected_artifact_sha:
                if actual_artifact_sha != expected_artifact_sha:
                    errors.append(
                        f"artifact_manifest.json SHA-256 mismatch: disk={actual_artifact_sha}, manifest={expected_artifact_sha}"
                    )
                else:
                    checks["artifact_manifest_hash_valid"] = True
            else:
                checks["artifact_manifest_hash_valid"] = True

            try:
                with open(artifact_manifest_path, "r", encoding="utf-8") as f:
                    art_data = json.load(f)

                proj_commit = art_data.get("project_git_commit")
                sk_commit = art_data.get("starter_kit_commit")
                if proj_commit and sk_commit and proj_commit == sk_commit:
                    errors.append("project_git_commit and starter_kit_commit must not be identical")

                # Verify each stored artifact file exists on disk and its SHA-256 matches
                artifact_file_errors = []
                for art in art_data.get("artifacts", []):
                    stored_rel = art.get("stored_path")
                    if stored_rel:
                        sp = run_dir / stored_rel
                        if not sp.is_file():
                            artifact_file_errors.append(f"Missing preserved artifact file: {stored_rel}")
                        else:
                            file_sha = hashlib.sha256(sp.read_bytes()).hexdigest()
                            if file_sha != art.get("sha256"):
                                artifact_file_errors.append(
                                    f"Preserved artifact checksum mismatch for {stored_rel}: "
                                    f"disk={file_sha}, recorded={art.get('sha256')}"
                                )
                if artifact_file_errors:
                    errors.extend(artifact_file_errors)
                else:
                    checks["artifacts_vault_valid"] = True
            except Exception as e:
                errors.append(f"Corrupted artifact_manifest.json: {e}")

        overall_valid = (len(errors) == 0)

        result = {
            "valid": overall_valid,
            "run_id": run_id,
            "status": status,
            "checks": checks,
            "details": details,
            "errors": errors,
        }

        if save_evaluation:
            eval_path = run_dir / "evaluation.json"
            try:
                with open(eval_path, "w", encoding="utf-8") as f:
                    json.dump(result, f, indent=2)
            except Exception:
                pass

        return result
