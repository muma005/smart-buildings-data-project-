"""Crash Worker Subprocess for WP3 Genuine Crash Recovery Testing.

Executes real TraceRecorder and ExperimentRegistry workflows in an isolated OS process.
Simulates genuine, abrupt crashes at 5 precise synchronization points (P1 to P5)
by signaling the parent process via synchronization flags and awaiting termination.
"""

from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import sys
import time
import numpy as np

# Ensure project and foundation roots are in sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[1]
FOUNDATION_ROOT = PROJECT_ROOT / "04_EXPERIMENT_FOUNDATION"

for p in [str(PROJECT_ROOT), str(FOUNDATION_ROOT)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from core.registry import ExperimentRegistry, RunStatus
from core.trace_recorder import TraceRecorder


def record_dummy_step(recorder: TraceRecorder, step_idx: int):
    """Feeds a realistic transition step into TraceRecorder."""
    recorder.record_step(
        step_idx=step_idx,
        reward=-0.05,
        productivity_regret=0.01,
        energy_cost=0.04,
        carbon_penalty=0.00,
        mean_zone_temp=294.15,
        outdoor_temp=285.0,
        total_occupants=12.0,
        discrete_action=np.array([1, 0, 1], dtype=np.int32),
        continuous_action=np.array([0.5, -0.2], dtype=np.float32),
        raw_continuous_action=np.array([0.5, -0.2], dtype=np.float32),
        observation=np.ones(10, dtype=np.float32) * 294.0,
        zone_temperatures=np.ones(3, dtype=np.float32) * 294.15,
        was_clipped=False,
        latency_ms=1.5,
    )


def run_p1(run_dir: Path, sync_dir: Path, chunk_size: int):
    """P1: Interruption mid-chunk write (orphaned partial .tmp chunk file)."""
    recorder = TraceRecorder(output_dir=run_dir, chunk_size=chunk_size)
    orig_publish = recorder._publish_chunk

    def hooked_publish_chunk(chunk_idx: int, is_final: bool = False):
        if chunk_idx == 1:
            chunk_filename = f"chunk_{chunk_idx:04d}.npz"
            tmp_path = recorder.chunks_dir / f"{chunk_filename}.tmp"
            # Write partial uncommitted temporary chunk bytes
            with open(tmp_path, "wb") as f:
                f.write(b"PARTIAL_UNCOMMITTED_CHUNK_BYTES_AT_CRASH_P1")
                f.flush()
                os.fsync(f.fileno())

            # Signal parent that P1 condition is reached
            (sync_dir / "p1_ready.flag").write_text("ready", encoding="utf-8")
            # Wait for parent to kill this process
            while True:
                time.sleep(0.05)
        return orig_publish(chunk_idx, is_final=is_final)

    recorder._publish_chunk = hooked_publish_chunk

    # Record chunk 0 (0..chunk_size - 1) and chunk 1 to trigger publish of chunk 1
    for s in range(chunk_size * 2):
        record_dummy_step(recorder, s)


def run_p2(run_dir: Path, sync_dir: Path, chunk_size: int):
    """P2: Interruption after chunk rename, before manifest update (orphan valid .npz)."""
    recorder = TraceRecorder(output_dir=run_dir, chunk_size=chunk_size)
    orig_write_manifest = recorder._write_chunks_manifest

    def hooked_write_manifest():
        # Hooked during manifest write for chunk 1:
        # At this point, chunk_0001.npz has already been renamed to final_path,
        # but chunks_manifest.json has not yet been written/updated for chunk 1!
        if len(recorder.chunk_records) >= 2:
            (sync_dir / "p2_ready.flag").write_text("ready", encoding="utf-8")
            while True:
                time.sleep(0.05)
        return orig_write_manifest()

    recorder._write_chunks_manifest = hooked_write_manifest

    # Record chunk 0 and chunk 1
    for s in range(chunk_size * 2):
        record_dummy_step(recorder, s)


def run_p3(run_dir: Path, sync_dir: Path, chunk_size: int):
    """P3: Interruption mid-manifest replacement (orphaned manifest .json.tmp)."""
    recorder = TraceRecorder(output_dir=run_dir, chunk_size=chunk_size)
    orig_write_manifest = recorder._write_chunks_manifest

    def hooked_write_manifest():
        # During manifest write for chunk 1, create .json.tmp and halt before rename
        if len(recorder.chunk_records) >= 2:
            tmp_manifest = recorder.chunks_manifest_file.with_suffix(".json.tmp")
            with open(tmp_manifest, "w", encoding="utf-8") as f:
                json.dump({"partial_manifest": True, "status": "INCOMPLETE_WRITE"}, f)
                f.flush()
                os.fsync(f.fileno())

            (sync_dir / "p3_ready.flag").write_text("ready", encoding="utf-8")
            while True:
                time.sleep(0.05)
        return orig_write_manifest()

    recorder._write_chunks_manifest = hooked_write_manifest

    # Record chunk 0 and chunk 1
    for s in range(chunk_size * 2):
        record_dummy_step(recorder, s)


def run_p4(run_dir: Path, sync_dir: Path, chunk_size: int, extra_steps: int = 62):
    """P4: Interruption after manifest commitment, with uncommitted memory buffer."""
    recorder = TraceRecorder(output_dir=run_dir, chunk_size=chunk_size)

    # Record chunk 0 (committed) + extra_steps (uncommitted in memory, streamed to trace.csv)
    total_steps = chunk_size + extra_steps
    for s in range(total_steps):
        record_dummy_step(recorder, s)

    (sync_dir / "p4_ready.flag").write_text("ready", encoding="utf-8")
    while True:
        time.sleep(0.05)


def run_p5(run_dir: Path, sync_dir: Path):
    """P5: Interruption mid-recovery and recovery idempotence check."""
    reg = ExperimentRegistry(base_runs_dir=run_dir.parent)
    orig_save = reg._save_manifest

    def hooked_save_manifest(r_dir: Path, manifest: dict):
        # Halt right before saving final manifest
        (sync_dir / "p5_ready.flag").write_text("ready", encoding="utf-8")
        while True:
            time.sleep(0.05)

    reg._save_manifest = hooked_save_manifest
    reg.recover_interrupted_run(run_dir)


def main():
    parser = argparse.ArgumentParser(description="Crash worker process for WP3")
    parser.add_argument("--point", required=True, choices=["P1", "P2", "P3", "P4", "P5"])
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--sync-dir", required=True, type=Path)
    parser.add_argument("--chunk-size", default=288, type=int)
    args = parser.parse_args()

    args.run_dir.mkdir(parents=True, exist_ok=True)
    args.sync_dir.mkdir(parents=True, exist_ok=True)

    if args.point == "P1":
        run_p1(args.run_dir, args.sync_dir, args.chunk_size)
    elif args.point == "P2":
        run_p2(args.run_dir, args.sync_dir, args.chunk_size)
    elif args.point == "P3":
        run_p3(args.run_dir, args.sync_dir, args.chunk_size)
    elif args.point == "P4":
        run_p4(args.run_dir, args.sync_dir, args.chunk_size)
    elif args.point == "P5":
        run_p5(args.run_dir, args.sync_dir)


if __name__ == "__main__":
    main()
