"""Trace Recorder for Smart Buildings Challenge.
Captures replay-grade transition traces step-by-step with schema validation,
sequence monotonicity enforcement, and cryptographic checksumming.
"""

from __future__ import annotations
import csv
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence
import numpy as np


class TraceRecorder:
    """Streams and records episode step transitions with integrity validation."""

    def __init__(self, output_dir: Path | str, prefix: str = "trace"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.prefix = prefix
        self.trace_file = self.output_dir / f"{prefix}.csv"

        self.step_count = 0
        self.records: list[dict[str, Any]] = []
        self._csv_writer = None
        self._file_handle = None

    def __enter__(self):
        self._file_handle = open(self.trace_file, "w", newline="", encoding="utf-8")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._file_handle:
            self._file_handle.close()
            self._file_handle = None

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
        metadata: Mapping[str, Any] | None = None,
    ):
        """Records a single step transition with strict monotonicity verification."""
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
        }
        if metadata:
            for k, v in metadata.items():
                if isinstance(v, (int, float, str, bool)):
                    row[k] = v

        if self._csv_writer is None and self._file_handle is not None:
            self._csv_writer = csv.DictWriter(self._file_handle, fieldnames=list(row.keys()))
            self._csv_writer.writeheader()

        if self._csv_writer is not None:
            self._csv_writer.writerow(row)
            self._file_handle.flush()

        self.records.append(row)
        self.step_count += 1

    def close(self) -> dict[str, Any]:
        """Finalizes the trace file and returns summary metadata including cryptographic hash."""
        if self._file_handle is not None:
            self._file_handle.close()
            self._file_handle = None

        file_bytes = self.trace_file.read_bytes() if self.trace_file.is_file() else b""
        sha256_hash = hashlib.sha256(file_bytes).hexdigest()

        return {
            "total_steps": self.step_count,
            "trace_path": str(self.trace_file),
            "file_size_bytes": len(file_bytes),
            "sha256": sha256_hash,
            "cumulative_reward": sum(r["reward"] for r in self.records),
        }
