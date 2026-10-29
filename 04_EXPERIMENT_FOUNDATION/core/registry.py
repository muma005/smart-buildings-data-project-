"""Experiment & Run Registry for Smart Buildings Challenge.
Provides unique run identification, immutable artifact directory isolation,
cryptographic provenance hashing, and formal state-machine governance.
"""

from __future__ import annotations
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping
import uuid


class RunStatus(str, Enum):
    INITIALIZED = "INITIALIZED"
    RUNNING = "RUNNING"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"
    INCOMPLETE = "INCOMPLETE"
    INVALID = "INVALID"
    COMPLETE_NOT_ELIGIBLE = "COMPLETE_NOT_ELIGIBLE"


VALID_TRANSITIONS: dict[RunStatus, set[RunStatus]] = {
    RunStatus.INITIALIZED: {RunStatus.RUNNING, RunStatus.FAILED},
    RunStatus.RUNNING: {RunStatus.COMPLETE, RunStatus.FAILED, RunStatus.INCOMPLETE},
    RunStatus.COMPLETE: {RunStatus.INVALID, RunStatus.COMPLETE_NOT_ELIGIBLE},
    RunStatus.FAILED: set(),
    RunStatus.INCOMPLETE: {RunStatus.INVALID},
    RunStatus.INVALID: set(),
    RunStatus.COMPLETE_NOT_ELIGIBLE: set(),
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
    ) -> tuple[str, Path]:
        """Initializes a new immutable run directory and manifest."""
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
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "status": RunStatus.INITIALIZED.value,
            "expected_steps": expected_steps,
            "actual_steps": 0,
            "hashes": {
                "config_sha256": config_hash,
                "policy_sha256": policy_hash,
                "trace_sha256": None,
            },
            "artifacts": {
                "run_dir": str(run_dir),
                "trace_path": None,
                "summary_path": None,
                "evaluation_path": None,
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
        manifest["updated_at_utc"] = datetime.now(timezone.utc).isoformat()

        if actual_steps is not None:
            manifest["actual_steps"] = actual_steps
        if trace_hash is not None:
            manifest["hashes"]["trace_sha256"] = trace_hash
        if error_message:
            manifest["errors"].append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": error_message,
            })
        if artifacts_update:
            manifest["artifacts"].update(artifacts_update)

        self._save_manifest(run_dir, manifest)
        return manifest

    def load_manifest(self, run_dir: Path | str) -> dict[str, Any]:
        """Loads and returns run_manifest.json."""
        manifest_path = Path(run_dir) / "run_manifest.json"
        if not manifest_path.is_file():
            raise FileNotFoundError(f"Missing run manifest: {manifest_path}")
        with open(manifest_path, "r", encoding="utf-8") as f:
            return json.load(f)

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
