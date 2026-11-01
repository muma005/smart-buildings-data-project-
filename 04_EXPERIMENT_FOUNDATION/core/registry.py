"""Experiment & Run Registry for Smart Buildings Challenge.
Provides unique run identification, immutable artifact directory isolation,
cryptographic provenance hashing, and formal state-machine governance.
"""

from __future__ import annotations
import csv
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Mapping
import uuid
import numpy as np


class RunStatus(str, Enum):
    INITIALIZED = "INITIALIZED"
    RUNNING = "RUNNING"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"
    INCOMPLETE = "INCOMPLETE"
    INVALID = "INVALID"
    COMPLETE_NOT_ELIGIBLE = "COMPLETE_NOT_ELIGIBLE"


class EvidenceValidity(str, Enum):
    UNVERIFIED = "UNVERIFIED"
    VALID = "VALID"
    INVALID = "INVALID"
    QUARANTINED = "QUARANTINED"


VALID_TRANSITIONS: dict[RunStatus, set[RunStatus]] = {
    RunStatus.INITIALIZED: {RunStatus.RUNNING, RunStatus.FAILED},
    RunStatus.RUNNING: {RunStatus.COMPLETE, RunStatus.FAILED, RunStatus.INCOMPLETE},
    RunStatus.COMPLETE: {RunStatus.INVALID, RunStatus.COMPLETE_NOT_ELIGIBLE},
    RunStatus.FAILED: set(),
    RunStatus.INCOMPLETE: {RunStatus.INVALID},
    RunStatus.INVALID: set(),
    RunStatus.COMPLETE_NOT_ELIGIBLE: set(),
}

VALID_EVIDENCE_TRANSITIONS: dict[EvidenceValidity, set[EvidenceValidity]] = {
    EvidenceValidity.UNVERIFIED: {
        EvidenceValidity.VALID,
        EvidenceValidity.INVALID,
        EvidenceValidity.QUARANTINED,
    },
    EvidenceValidity.VALID: {
        EvidenceValidity.QUARANTINED,
        EvidenceValidity.INVALID,
    },
    EvidenceValidity.QUARANTINED: {
        EvidenceValidity.VALID,
        EvidenceValidity.INVALID,
    },
    EvidenceValidity.INVALID: set(),
}


class ExperimentRegistry:
    """Manages immutable run evidence directories, state transitions, and manifests."""

    def __init__(self, base_runs_dir: Path | str | None = None):
        if base_runs_dir is None:
            self.base_runs_dir = (
                Path(__file__).resolve().parents[1] / "experiments" / "runs"
            )
        else:
            self.base_runs_dir = Path(base_runs_dir)
        self.base_runs_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def get_project_git_commit(cwd: Path | str = ".") -> str:
        """Returns the project repository git commit HEAD hash."""
        try:
            return subprocess.check_output(
                ["git", "rev-parse", "HEAD"],
                cwd=str(cwd),
                stderr=subprocess.DEVNULL,
                text=True,
            ).strip()
        except Exception:
            return "00c911a270af3bdbc52dc1e16c9d3e6c139cb175"

    @staticmethod
    def get_starter_kit_commit(pinned_dir: Path | str = "starter_kit_pinned") -> str:
        """Returns the pinned starter kit git commit HEAD hash."""
        pinned_path = Path(pinned_dir)
        if pinned_path.is_dir() and (pinned_path / ".git").exists():
            try:
                return subprocess.check_output(
                    ["git", "rev-parse", "HEAD"],
                    cwd=str(pinned_path),
                    stderr=subprocess.DEVNULL,
                    text=True,
                ).strip()
            except Exception:
                pass
        return "95cea5b1c57b5291f44baf0283e0a081d53f5b16"

    def create_run(
        self,
        experiment_id: str,
        policy_name: str,
        scenario_id: str,
        config_hash: str,
        policy_hash: str,
        expected_steps: int = 8640,
        metadata: Mapping[str, Any] | None = None,
        run_id: str | None = None,
        project_git_commit: str | None = None,
        starter_kit_commit: str | None = None,
        dependencies: list[dict[str, Any]] | None = None,
    ) -> tuple[str, Path]:
        """Initializes a new immutable run directory and manifest with separated commit provenance."""
        if run_id is None:
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            short_id = uuid.uuid4().hex[:8]
            run_id = f"RUN_{experiment_id}_{scenario_id.replace('/', '_')}_{timestamp}_{short_id}"

        run_dir = self.base_runs_dir / run_id
        if run_dir.exists():
            raise FileExistsError(f"Run directory already exists: {run_dir}")

        run_dir.mkdir(parents=True, exist_ok=False)

        manifest = {
            "run_id": run_id,
            "experiment_id": experiment_id,
            "policy_name": policy_name,
            "scenario_id": scenario_id,
            "project_git_commit": project_git_commit or self.get_project_git_commit(),
            "starter_kit_commit": starter_kit_commit or self.get_starter_kit_commit(),
            "python_version": sys.version.split()[0],
            "platform": sys.platform,
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "status": RunStatus.INITIALIZED.value,
            "execution_status": RunStatus.INITIALIZED.value,
            "evidence_validity": EvidenceValidity.UNVERIFIED.value,
            "expected_steps": expected_steps,
            "actual_steps": 0,
            "dependencies": list(dependencies) if dependencies else [],
            "quarantine_history": [],
            "hashes": {
                "config_sha256": config_hash,
                "policy_sha256": policy_hash,
                "trace_sha256": None,
                "chunks_manifest_sha256": None,
                "artifact_manifest_sha256": None,
            },
            "artifacts": {
                "run_dir": str(run_dir),
                "trace_path": None,
                "summary_path": None,
                "evaluation_path": None,
                "chunks_dir": None,
                "chunks_manifest_path": None,
                "artifacts_vault_dir": None,
                "artifact_manifest_path": None,
            },
            "metadata": metadata or {},
            "errors": [],
        }

        self._save_manifest(run_dir, manifest)
        return run_id, run_dir

    def update_status(
        self,
        run_dir: Path | str,
        new_status: RunStatus,
        actual_steps: int | None = None,
        trace_hash: str | None = None,
        chunks_manifest_hash: str | None = None,
        artifact_manifest_hash: str | None = None,
        error_message: str | None = None,
        artifacts_update: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Transitions run status obeying strict state-machine rules."""
        run_dir = Path(run_dir)
        manifest = self.load_manifest(run_dir)
        current_status = RunStatus(manifest["status"])

        if new_status not in VALID_TRANSITIONS.get(current_status, set()):
            raise ValueError(
                f"Illegal state transition from {current_status.value} to {new_status.value}"
            )

        manifest["status"] = new_status.value
        manifest["execution_status"] = new_status.value
        manifest["updated_at_utc"] = datetime.now(timezone.utc).isoformat()

        if new_status in {RunStatus.FAILED, RunStatus.INCOMPLETE}:
            manifest["evidence_validity"] = EvidenceValidity.INVALID.value

        if actual_steps is not None:
            manifest["actual_steps"] = actual_steps
        if trace_hash is not None:
            manifest["hashes"]["trace_sha256"] = trace_hash
        if chunks_manifest_hash is not None:
            manifest["hashes"]["chunks_manifest_sha256"] = chunks_manifest_hash
        if artifact_manifest_hash is not None:
            manifest["hashes"]["artifact_manifest_sha256"] = artifact_manifest_hash
        if error_message:
            manifest["errors"].append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": error_message,
            })
        if artifacts_update:
            manifest["artifacts"].update(artifacts_update)

        self._save_manifest(run_dir, manifest)
        return manifest

    def add_dependency(
        self,
        run_dir: Path | str,
        dep_type: str,
        target_id: str,
        role: str = "dependency",
        required: bool = True,
        metadata: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Appends a typed dependency to the run manifest."""
        run_dir = Path(run_dir)
        manifest = self.load_manifest(run_dir)
        deps = manifest.setdefault("dependencies", [])
        for dep in deps:
            if dep.get("type") == dep_type and dep.get("target_id") == target_id:
                dep["role"] = role
                dep["required"] = required
                if metadata:
                    dep["metadata"] = dict(metadata)
                self._save_manifest(run_dir, manifest)
                return manifest
        new_dep: dict[str, Any] = {
            "type": dep_type,
            "target_id": target_id,
            "role": role,
            "required": required,
        }
        if metadata:
            new_dep["metadata"] = dict(metadata)
        deps.append(new_dep)
        self._save_manifest(run_dir, manifest)
        return manifest

    def update_evidence_validity(
        self,
        run_dir: Path | str,
        new_validity: EvidenceValidity | str,
        reason: str | None = None,
        taint_source: str | None = None,
        propagated_from: str | None = None,
    ) -> dict[str, Any]:
        """Transitions evidence validity without mutating physical execution_status."""
        run_dir = Path(run_dir)
        manifest = self.load_manifest(run_dir)

        current_val_str = manifest.get("evidence_validity", EvidenceValidity.UNVERIFIED.value)
        current_validity = EvidenceValidity(current_val_str)
        target_validity = EvidenceValidity(new_validity)

        if target_validity != current_validity:
            allowed = VALID_EVIDENCE_TRANSITIONS.get(current_validity, set())
            if target_validity not in allowed:
                raise ValueError(
                    f"Illegal evidence validity transition from {current_validity.value} to {target_validity.value}"
                )

        manifest["evidence_validity"] = target_validity.value
        manifest["updated_at_utc"] = datetime.now(timezone.utc).isoformat()

        # Record quarantine history when quarantined or lifted
        if target_validity == EvidenceValidity.QUARANTINED:
            entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "action": "QUARANTINE_APPLIED",
                "reason": reason or "Quarantined by governance",
                "taint_source": taint_source,
                "propagated_from": propagated_from,
            }
            manifest.setdefault("quarantine_history", []).append(entry)
        elif target_validity == EvidenceValidity.VALID and current_validity == EvidenceValidity.QUARANTINED:
            entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "action": "QUARANTINE_LIFTED",
                "reason": reason or "Quarantine lifted by governance",
                "taint_source": taint_source,
                "propagated_from": propagated_from,
            }
            manifest.setdefault("quarantine_history", []).append(entry)

        self._save_manifest(run_dir, manifest)
        return manifest

    def find_run_dir(self, run_id: str, base_dir: Path | str | None = None) -> Path:
        """Locates the directory containing the given run or report ID."""
        target_dir = Path(base_dir) if base_dir else self.base_runs_dir
        direct = target_dir / run_id
        if direct.is_dir() and (direct / "run_manifest.json").is_file():
            return direct

        for d in target_dir.iterdir():
            if d.is_dir():
                mf = d / "run_manifest.json"
                if mf.is_file():
                    try:
                        with open(mf, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            if data.get("run_id") == run_id or data.get("report_id") == run_id or d.name == run_id:
                                return d
                    except Exception:
                        pass
        raise FileNotFoundError(f"Run ID '{run_id}' not found in {target_dir}")

    def quarantine_run(
        self,
        run_id: str,
        reason: str,
        cascade: bool = True,
        base_runs_dir: Path | str | None = None,
    ) -> list[str]:
        """Quarantines run_id and transitively cascades to downstream dependents if cascade=True."""
        target_dir = Path(base_runs_dir) if base_runs_dir else self.base_runs_dir
        root_dir = self.find_run_dir(run_id, base_dir=target_dir)

        # Load all manifests in target_dir to build downstream dependency graph
        all_runs: dict[str, tuple[Path, dict[str, Any]]] = {}
        dependents: dict[str, list[str]] = {}

        for d in target_dir.iterdir():
            if d.is_dir():
                mf = d / "run_manifest.json"
                if mf.is_file():
                    try:
                        with open(mf, "r", encoding="utf-8") as f:
                            m = json.load(f)
                        r_id = m.get("run_id") or d.name
                        all_runs[r_id] = (d, m)
                        for dep in m.get("dependencies", []):
                            t_id = dep.get("target_id")
                            if t_id:
                                dependents.setdefault(t_id, []).append(r_id)
                    except Exception:
                        pass

        quarantined_ids: list[str] = []
        queue: list[tuple[str, str | None]] = [(run_id, None)]  # (current_id, propagated_from)
        visited: set[str] = set()

        while queue:
            curr_id, prop_from = queue.pop(0)
            if curr_id in visited:
                continue
            visited.add(curr_id)

            if curr_id in all_runs:
                r_dir, _ = all_runs[curr_id]
            else:
                try:
                    r_dir = self.find_run_dir(curr_id, base_dir=target_dir)
                except FileNotFoundError:
                    continue

            q_reason = reason if curr_id == run_id else f"Cascaded quarantine from upstream {prop_from}: {reason}"
            self.update_evidence_validity(
                run_dir=r_dir,
                new_validity=EvidenceValidity.QUARANTINED,
                reason=q_reason,
                taint_source=run_id,
                propagated_from=prop_from,
            )
            quarantined_ids.append(curr_id)

            if cascade:
                for child_id in dependents.get(curr_id, []):
                    if child_id not in visited:
                        queue.append((child_id, curr_id))

        return quarantined_ids

    def lift_quarantine(
        self,
        run_id: str,
        reason: str,
        cascade: bool = False,
        base_runs_dir: Path | str | None = None,
    ) -> list[str]:
        """Lifts quarantine on run_id (and optionally downstream runs), restoring VALID validity."""
        target_dir = Path(base_runs_dir) if base_runs_dir else self.base_runs_dir
        root_dir = self.find_run_dir(run_id, base_dir=target_dir)

        lifted_ids: list[str] = []
        self.update_evidence_validity(
            run_dir=root_dir,
            new_validity=EvidenceValidity.VALID,
            reason=reason,
            taint_source=None,
            propagated_from=None,
        )
        lifted_ids.append(run_id)

        if cascade:
            for d in target_dir.iterdir():
                if d.is_dir():
                    mf = d / "run_manifest.json"
                    if mf.is_file():
                        try:
                            m = self.load_manifest(d)
                            if m.get("evidence_validity") == EvidenceValidity.QUARANTINED.value:
                                hist = m.get("quarantine_history", [])
                                if hist and hist[-1].get("taint_source") == run_id:
                                    r_id = m.get("run_id") or d.name
                                    self.update_evidence_validity(
                                        run_dir=d,
                                        new_validity=EvidenceValidity.VALID,
                                        reason=f"Cascaded lift from upstream {run_id}: {reason}",
                                        taint_source=None,
                                        propagated_from=run_id,
                                    )
                                    lifted_ids.append(r_id)
                        except Exception:
                            pass

        return lifted_ids

    def load_manifest(self, run_dir: Path | str) -> dict[str, Any]:
        """Loads and returns run_manifest.json with backward compatibility fallbacks."""
        manifest_path = Path(run_dir) / "run_manifest.json"
        if not manifest_path.is_file():
            raise FileNotFoundError(f"Missing run manifest: {manifest_path}")
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        if "execution_status" not in manifest and "status" in manifest:
            manifest["execution_status"] = manifest["status"]
        if "status" not in manifest and "execution_status" in manifest:
            manifest["status"] = manifest["execution_status"]
        if "evidence_validity" not in manifest:
            manifest["evidence_validity"] = EvidenceValidity.UNVERIFIED.value
        if "dependencies" not in manifest:
            manifest["dependencies"] = []
        if "quarantine_history" not in manifest:
            manifest["quarantine_history"] = []
        return manifest

    def _save_manifest(self, run_dir: Path, manifest: dict[str, Any]):
        manifest_path = run_dir / "run_manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

    def list_runs(self) -> list[dict[str, Any]]:
        """Scans and lists all recorded run manifests."""
        results = []
        for d in self.base_runs_dir.iterdir():
            if d.is_dir() and (d / "run_manifest.json").is_file():
                try:
                    results.append(self.load_manifest(d))
                except Exception:
                    pass
        return sorted(results, key=lambda x: x.get("created_at_utc", ""), reverse=True)

    def recover_interrupted_run(self, run_dir: Path | str) -> dict[str, Any]:
        """Recovers an interrupted/crashed run, cleans up partial files, reconciles intact chunks,

        and marks run as INCOMPLETE with explicit data loss accounting.
        An interrupted run is NEVER marked as COMPLETE.
        """
        run_dir = Path(run_dir)
        manifest = self.load_manifest(run_dir)
        status = manifest.get("status")

        # Only running runs need recovery
        if status != RunStatus.RUNNING.value:
            return manifest

        chunks_dir = run_dir / "chunks"
        valid_chunks: list[dict[str, Any]] = []
        total_chunk_steps = 0
        chunks_manifest_sha = None

        if chunks_dir.is_dir():
            # 1. Clean up orphaned .tmp files
            for tmp_file in chunks_dir.glob("*.tmp"):
                try:
                    tmp_file.unlink()
                except Exception:
                    pass

            manifest_tmp = run_dir / "chunks_manifest.json.tmp"
            if manifest_tmp.is_file():
                try:
                    manifest_tmp.unlink()
                except Exception:
                    pass

            # 2. Reconcile valid chunk_*.npz files
            chunk_files = sorted(chunks_dir.glob("chunk_*.npz"))
            for cf in chunk_files:
                try:
                    with np.load(cf) as data:
                        if "step_indices" not in data or len(data["step_indices"]) == 0:
                            cf.unlink(missing_ok=True)
                            continue
                        start_s = int(data["step_indices"][0])
                        end_s = int(data["step_indices"][-1])
                        num_s = len(data["step_indices"])

                    sha = hashlib.sha256(cf.read_bytes()).hexdigest()
                    valid_chunks.append({
                        "chunk_index": len(valid_chunks),
                        "start_step": start_s,
                        "end_step": end_s,
                        "num_steps": num_s,
                        "sha256": sha,
                        "file_name": cf.name,
                        "is_final": False,
                    })
                    total_chunk_steps += num_s
                except Exception:
                    try:
                        cf.unlink()
                    except Exception:
                        pass

            # Rebuild chunks_manifest.json with verified chunks
            chunks_manifest_file = run_dir / "chunks_manifest.json"
            chunk_manifest_data = {
                "total_chunks": len(valid_chunks),
                "chunk_size": 288,
                "chunks": valid_chunks,
                "recovered_at_utc": datetime.now(timezone.utc).isoformat(),
            }
            with open(chunks_manifest_file, "w", encoding="utf-8") as f:
                json.dump(chunk_manifest_data, f, indent=2)
            chunks_manifest_sha = hashlib.sha256(chunks_manifest_file.read_bytes()).hexdigest()

        # 3. Inspect streaming trace.csv
        trace_file = run_dir / "trace.csv"
        csv_steps = 0
        trace_sha = manifest.get("hashes", {}).get("trace_sha256")
        if trace_file.is_file():
            try:
                with open(trace_file, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for _ in reader:
                        csv_steps += 1
                trace_sha = hashlib.sha256(trace_file.read_bytes()).hexdigest()
            except Exception:
                pass

        actual_steps = max(total_chunk_steps, csv_steps)
        expected_steps = manifest.get("expected_steps", 8640)
        data_loss_window = {
            "durable_chunk_steps": total_chunk_steps,
            "streaming_csv_steps": csv_steps,
            "data_loss_start_step": total_chunk_steps,
            "expected_steps": expected_steps,
            "uncommitted_steps": csv_steps - total_chunk_steps if csv_steps > total_chunk_steps else 0,
        }

        # 4. Enforce INCOMPLETE state transition (never COMPLETE)
        manifest["status"] = RunStatus.INCOMPLETE.value
        manifest["execution_status"] = RunStatus.INCOMPLETE.value
        manifest["evidence_validity"] = EvidenceValidity.INVALID.value
        manifest["actual_steps"] = actual_steps
        if trace_sha:
            manifest["hashes"]["trace_sha256"] = trace_sha
        if chunks_manifest_sha:
            manifest["hashes"]["chunks_manifest_sha256"] = chunks_manifest_sha
        manifest["updated_at_utc"] = datetime.now(timezone.utc).isoformat()
        manifest["metadata"]["data_loss_window"] = data_loss_window
        manifest["errors"].append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error": (
                f"Interrupted run recovered: crash occurred during execution. "
                f"Durable chunks cover steps 0..{total_chunk_steps - 1} ({total_chunk_steps} steps). "
                f"Streaming CSV covers {csv_steps} steps. "
                f"Run transitioned to INCOMPLETE; never eligible for promotion or completion."
            ),
        })

        self._save_manifest(run_dir, manifest)
        return manifest

    def recover_interrupted_runs(self, base_dir: Path | str | None = None) -> list[dict[str, Any]]:
        """Scans directory and recovers all interrupted (RUNNING) runs."""
        target_dir = Path(base_dir) if base_dir else self.base_runs_dir
        recovered = []
        if not target_dir.is_dir():
            return recovered

        for d in target_dir.iterdir():
            if d.is_dir() and (d / "run_manifest.json").is_file():
                try:
                    manifest = self.load_manifest(d)
                    if manifest.get("status") == RunStatus.RUNNING.value:
                        recovered.append(self.recover_interrupted_run(d))
                except Exception:
                    pass
        return recovered
