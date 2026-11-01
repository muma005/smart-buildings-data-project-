"""Trace Recorder for Smart Buildings Challenge.
Captures replay-grade transition traces step-by-step with schema validation,
sequence monotonicity enforcement, and cryptographic checksumming.
Includes durable incremental chunk persistence with staged atomic writes.
"""

from __future__ import annotations
import csv
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping, Sequence
import numpy as np


class EvidenceCaptureError(RuntimeError):
    """Raised when critical evidence cannot be captured or serialized."""
    pass


class TraceRecorder:
    """Streams and records episode step transitions with integrity validation and durable chunking."""

    def __init__(
        self,
        output_dir: Path | str,
        prefix: str = "trace",
        chunk_size: int = 288,
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.prefix = prefix
        self.chunk_size = chunk_size
        self.trace_file = self.output_dir / f"{prefix}.csv"
        self.chunks_dir = self.output_dir / "chunks"
        self.chunks_dir.mkdir(parents=True, exist_ok=True)
        self.chunks_manifest_file = self.output_dir / "chunks_manifest.json"

        self.step_count = 0
        self.records: list[dict[str, Any]] = []
        self._csv_writer = None
        self._file_handle = None

        # Chunk buffer for multi-dimensional arrays
        self.current_chunk_idx = 0
        self._buffer: dict[str, list[Any]] = {
            "step_indices": [],
            "observations": [],
            "raw_continuous_actions": [],
            "executed_continuous_actions": [],
            "discrete_actions": [],
            "zone_temperatures": [],
        }
        self.chunk_records: list[dict[str, Any]] = []

    def __enter__(self):
        self._file_handle = open(self.trace_file, "w", newline="", encoding="utf-8")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._file_handle:
            self._file_handle.close()
            self._file_handle = None

    def _reset_buffer(self):
        self._buffer = {
            "step_indices": [],
            "observations": [],
            "raw_continuous_actions": [],
            "executed_continuous_actions": [],
            "discrete_actions": [],
            "zone_temperatures": [],
        }

    def record_step(
        self,
        step_idx: int,
        reward: float,
        productivity_regret: float,
        energy_cost: float,
        carbon_penalty: float,
        mean_zone_temp: float,
        outdoor_temp: float,
        total_occupants: float,
        discrete_action: Sequence[int] | np.ndarray,
        continuous_action: Sequence[float] | np.ndarray,
        raw_continuous_action: Sequence[float] | np.ndarray | None = None,
        observation: np.ndarray | None = None,
        zone_temperatures: Sequence[float] | np.ndarray | None = None,
        was_clipped: bool = False,
        latency_ms: float = 0.0,
        metadata: Mapping[str, Any] | None = None,
    ):
        """Records a single step transition with strict monotonicity verification and chunk buffering."""
        if step_idx != self.step_count:
            raise ValueError(
                f"Step sequence discontinuity: expected step {self.step_count}, got {step_idx}"
            )

        row = {
            "step": step_idx,
            "reward": float(reward),
            "productivity_regret": float(productivity_regret),
            "energy_cost": float(energy_cost),
            "carbon_penalty": float(carbon_penalty),
            "mean_zone_temp": float(mean_zone_temp),
            "outdoor_temp": float(outdoor_temp),
            "total_occupants": float(total_occupants),
            "discrete_action_sum": int(np.sum(discrete_action)),
            "continuous_action_mean": float(np.mean(continuous_action)),
            "was_clipped": int(was_clipped),
            "latency_ms": float(latency_ms),
        }
        if metadata:
            for k, v in metadata.items():
                if isinstance(v, (int, float, str, bool)):
                    row[k] = v

        try:
            if self._file_handle is None and not self.trace_file.exists():
                self._file_handle = open(self.trace_file, "w", newline="", encoding="utf-8")

            if self._csv_writer is None and self._file_handle is not None:
                self._csv_writer = csv.DictWriter(self._file_handle, fieldnames=list(row.keys()))
                self._csv_writer.writeheader()

            if self._csv_writer is not None:
                self._csv_writer.writerow(row)
                self._file_handle.flush()
        except Exception as e:
            raise EvidenceCaptureError(f"Failed to stream step {step_idx} to trace.csv: {e}") from e

        self.records.append(row)

        # Buffer tensors for durable binary chunks
        self._buffer["step_indices"].append(step_idx)
        self._buffer["observations"].append(
            np.array(observation, copy=True) if observation is not None else np.array([])
        )
        self._buffer["raw_continuous_actions"].append(
            np.array(raw_continuous_action, copy=True)
            if raw_continuous_action is not None
            else np.array(continuous_action, copy=True)
        )
        self._buffer["executed_continuous_actions"].append(np.array(continuous_action, copy=True))
        self._buffer["discrete_actions"].append(np.array(discrete_action, copy=True))
        self._buffer["zone_temperatures"].append(
            np.array(zone_temperatures, copy=True) if zone_temperatures is not None else np.array([])
        )

        self.step_count += 1

        # Check if diurnal/daily chunk size reached
        if len(self._buffer["step_indices"]) >= self.chunk_size:
            self._publish_chunk(self.current_chunk_idx, is_final=False)
            self.current_chunk_idx += 1
            self._reset_buffer()

    def _publish_chunk(self, chunk_idx: int, is_final: bool = False) -> dict[str, Any]:
        """Atomically publishes in-memory buffered transitions to a durable .npz file."""
        if not self._buffer["step_indices"]:
            return {}

        chunk_filename = f"chunk_{chunk_idx:04d}.npz"
        final_path = self.chunks_dir / chunk_filename
        tmp_path = self.chunks_dir / f"{chunk_filename}.tmp"

        start_step = int(self._buffer["step_indices"][0])
        end_step = int(self._buffer["step_indices"][-1])
        num_steps = len(self._buffer["step_indices"])

        try:
            # Package chunk data
            chunk_data = {
                "step_indices": np.array(self._buffer["step_indices"], dtype=np.int64),
                "observations": np.array(self._buffer["observations"]),
                "raw_continuous_actions": np.array(self._buffer["raw_continuous_actions"]),
                "executed_continuous_actions": np.array(self._buffer["executed_continuous_actions"]),
                "discrete_actions": np.array(self._buffer["discrete_actions"]),
                "zone_temperatures": np.array(self._buffer["zone_temperatures"]),
            }

            # 1. Staged write to temporary file
            with open(tmp_path, "wb") as f:
                np.savez_compressed(f, **chunk_data)
                # 2. OS-level persistence
                f.flush()
                os.fsync(f.fileno())

            # 3. Atomic rename
            tmp_path.replace(final_path)

            # 4. SHA-256 hash
            file_bytes = final_path.read_bytes()
            chunk_sha256 = hashlib.sha256(file_bytes).hexdigest()

            record = {
                "chunk_index": chunk_idx,
                "start_step": start_step,
                "end_step": end_step,
                "num_steps": num_steps,
                "sha256": chunk_sha256,
                "file_name": chunk_filename,
                "is_final": is_final,
                "committed_at": datetime.now(timezone.utc).isoformat(),
            }
            self.chunk_records.append(record)
            self._write_chunks_manifest()
            return record

        except Exception as e:
            if tmp_path.exists():
                try:
                    tmp_path.unlink()
                except Exception:
                    pass
            raise EvidenceCaptureError(
                f"Failed to publish chunk {chunk_idx} ({chunk_filename}): {e}"
            ) from e

    def _write_chunks_manifest(self) -> str:
        """Atomically serializes chunks_manifest.json with fsync."""
        manifest_data = {
            "total_chunks": len(self.chunk_records),
            "chunk_size": self.chunk_size,
            "chunks": self.chunk_records,
            "updated_at_utc": datetime.now(timezone.utc).isoformat(),
        }
        tmp_manifest = self.chunks_manifest_file.with_suffix(".json.tmp")
        try:
            with open(tmp_manifest, "w", encoding="utf-8") as f:
                json.dump(manifest_data, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            tmp_manifest.replace(self.chunks_manifest_file)
            manifest_bytes = self.chunks_manifest_file.read_bytes()
            return hashlib.sha256(manifest_bytes).hexdigest()
        except Exception as e:
            if tmp_manifest.exists():
                try:
                    tmp_manifest.unlink()
                except Exception:
                    pass
            raise EvidenceCaptureError(
                f"Failed to write chunks manifest ({self.chunks_manifest_file}): {e}"
            ) from e

    def close(self) -> dict[str, Any]:
        """Finalizes the trace file and chunks, returning summary metadata and cryptographic hashes."""
        if self._file_handle is not None:
            self._file_handle.close()
            self._file_handle = None

        # Flush any remaining uncommitted steps in buffer
        if self._buffer["step_indices"]:
            self._publish_chunk(self.current_chunk_idx, is_final=True)
            self.current_chunk_idx += 1
            self._reset_buffer()

        chunks_manifest_sha256 = ""
        if self.chunks_manifest_file.is_file():
            manifest_bytes = self.chunks_manifest_file.read_bytes()
            chunks_manifest_sha256 = hashlib.sha256(manifest_bytes).hexdigest()
        else:
            chunks_manifest_sha256 = self._write_chunks_manifest()

        file_bytes = self.trace_file.read_bytes() if self.trace_file.is_file() else b""
        sha256_hash = hashlib.sha256(file_bytes).hexdigest()

        return {
            "total_steps": self.step_count,
            "trace_path": str(self.trace_file),
            "file_size_bytes": len(file_bytes),
            "sha256": sha256_hash,
            "cumulative_reward": sum(r["reward"] for r in self.records),
            "total_chunks": len(self.chunk_records),
            "chunks_dir": str(self.chunks_dir),
            "chunks_manifest_path": str(self.chunks_manifest_file),
            "chunks_manifest_sha256": chunks_manifest_sha256,
        }

    @staticmethod
    def load_chunks(run_dir: Path | str) -> dict[str, np.ndarray]:
        """Loads and concatenates all committed chunks from run_dir into full episode arrays with integrity checks."""
        run_dir = Path(run_dir)
        chunks_dir = run_dir / "chunks"
        chunks_manifest_path = run_dir / "chunks_manifest.json"
        if not chunks_manifest_path.is_file():
            raise FileNotFoundError(f"Missing chunks manifest: {chunks_manifest_path}")

        with open(chunks_manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        chunk_records = manifest.get("chunks", [])
        if not chunk_records:
            return {}

        arrays: dict[str, list[np.ndarray]] = {
            "step_indices": [],
            "observations": [],
            "raw_continuous_actions": [],
            "executed_continuous_actions": [],
            "discrete_actions": [],
            "zone_temperatures": [],
        }

        for record in chunk_records:
            file_path = chunks_dir / record["file_name"]
            if not file_path.is_file():
                raise FileNotFoundError(f"Missing chunk file recorded in manifest: {file_path}")

            # Verify SHA-256 integrity
            actual_sha = hashlib.sha256(file_path.read_bytes()).hexdigest()
            if actual_sha != record["sha256"]:
                raise EvidenceCaptureError(
                    f"Chunk file checksum mismatch for {record['file_name']}: "
                    f"expected {record['sha256']}, got {actual_sha}"
                )

            with np.load(file_path) as data:
                for k in arrays:
                    if k in data:
                        arrays[k].append(data[k])

        concatenated = {}
        for k, v in arrays.items():
            if v:
                concatenated[k] = np.concatenate(v, axis=0)
            else:
                concatenated[k] = np.array([])
        return concatenated
